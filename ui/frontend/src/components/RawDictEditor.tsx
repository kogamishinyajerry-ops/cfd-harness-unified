// DEC-V61-102 M-RESCUE Phase 2 · RawDictEditor
//
// Engineer escape hatch when AI-authored OpenFOAM dicts need manual
// correction. Lists allowlisted paths (system/controlDict, fvSchemes,
// fvSolution, momentumTransport, physicalProperties, decomposeParDict,
// constant/g) as a tab list, loads the active path's content into a
// CodeMirror editor, saves via POST /cases/{id}/dicts/{path} with
// etag-based race protection.
//
// Round-trip contract (DEC §Wire shapes):
//   GET     → { content, source: "ai"|"user", etag, edited_at }
//   POST    → { new_etag, source: "user", warnings }
//     409   → etag_mismatch (file changed since last GET)
//     422   → validation_failed (FoamFile header / brace balance / required keys)
//             OR symlink_escape (planted .case_lock)
//
// Save semantics: every successful POST records source=user in the
// case manifest so subsequent setup_*_bc runs preserve the edit.
// Toggling "Reset to AI default" is OUT OF SCOPE for Phase 2 (would
// require a separate DELETE/PATCH endpoint we haven't shipped).

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import CodeMirror from "@uiw/react-codemirror";

import { api, ApiError } from "@/api/client";
import type {
  RawDictAllowlistEntry,
  RawDictGet,
} from "@/types/case_dicts";

interface Props {
  caseId: string;
  /** Subset of allowlisted paths to expose as tabs. If omitted, the
   *  full allowlist from GET /api/cases/{id}/dicts is shown. Step 3
   *  passes only the BC-relevant paths; Step 4 will pass the solver
   *  control set. */
  allowedPaths?: ReadonlyArray<string>;
}

// Codex Phase-2 round-2 MED closure: sessionStorage persistence for
// the editor buffer. Step navigation (Step 3 → Step 2 → Step 3)
// unmounts the whole task panel including this component, so a
// component-local useState would silently discard unsaved content.
// We persist on every keystroke and restore on mount; sessionStorage
// (not localStorage) so closing the tab is still an intentional
// discard. Key includes caseId + path to scope the cache correctly.
//
// Codex Phase-2 round-3 MED closure: persist BOTH content AND etag
// as a JSON envelope. On restore the etag stays at the value it had
// when the draft was authored; the server-side fresh-GET etag is NOT
// adopted automatically. That preserves the conflict-protection
// contract: if AI re-authored the file while the engineer was away,
// a save POST sends the (now-stale) etag → server returns 409 →
// engineer sees the conflict prompt instead of silently overwriting
// the newer server content.
const PERSISTENCE_PREFIX = "dec-v61-102:dict-buffer";

interface PersistedDraft {
  content: string;
  /** etag at the moment the draft was authored. Null if the file did
   *  not exist server-side at that time. */
  etag: string | null;
}

function persistenceKey(caseId: string, relativePath: string): string {
  return `${PERSISTENCE_PREFIX}:${caseId}:${relativePath}`;
}

function readPersisted(
  caseId: string,
  relativePath: string,
): PersistedDraft | null {
  try {
    const raw = sessionStorage.getItem(persistenceKey(caseId, relativePath));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.content !== "string") return null;
    return {
      content: parsed.content,
      etag: typeof parsed.etag === "string" ? parsed.etag : null,
    };
  } catch {
    // sessionStorage can throw under privacy modes / disabled storage,
    // or JSON.parse can throw on legacy plain-string entries from the
    // round-2 schema. Treat both as "no persisted draft".
    return null;
  }
}

function writePersisted(
  caseId: string,
  relativePath: string,
  content: string,
  etag: string | null,
): void {
  try {
    sessionStorage.setItem(
      persistenceKey(caseId, relativePath),
      JSON.stringify({ content, etag } satisfies PersistedDraft),
    );
  } catch {
    // Quota exceeded / disabled — fall back to in-memory only.
  }
}

function clearPersisted(caseId: string, relativePath: string): void {
  try {
    sessionStorage.removeItem(persistenceKey(caseId, relativePath));
  } catch {
    // Same as above.
  }
}

interface SaveStatus {
  kind: "idle" | "saving" | "saved" | "error";
  message?: string;
  warnings?: string[];
  /** Populated on 409 etag mismatch — frontend can offer "force overwrite". */
  conflictRefresh?: { current_etag: string };
  /** Populated on 422 validation_failed — frontend can offer "force=1 bypass". */
  validationIssues?: { severity: string; message: string }[];
}

export function RawDictEditor({ caseId, allowedPaths }: Props) {
  const qc = useQueryClient();

  // 1. Path list (tabs).
  const list = useQuery<RawDictAllowlistEntry[]>({
    queryKey: ["case-dicts-list", caseId],
    queryFn: () => api.listRawDicts(caseId),
    staleTime: 30_000,
  });

  const visiblePaths = useMemo<RawDictAllowlistEntry[]>(() => {
    const all = list.data ?? [];
    if (!allowedPaths) return all;
    const filter = new Set(allowedPaths);
    return all.filter((e) => filter.has(e.path));
  }, [list.data, allowedPaths]);

  // 2. Active path selector.
  const [activePath, setActivePath] = useState<string | null>(null);
  useEffect(() => {
    if (!activePath && visiblePaths.length > 0) {
      setActivePath(visiblePaths[0].path);
    }
  }, [activePath, visiblePaths]);

  // 3. Active file content (only when path picked AND file exists).
  const activeEntry = visiblePaths.find((e) => e.path === activePath);
  const detail = useQuery<RawDictGet>({
    queryKey: ["case-dict", caseId, activePath],
    queryFn: () => api.getRawDict(caseId, activePath as string),
    enabled: !!activePath && !!activeEntry?.exists,
    staleTime: 0,
  });

  // 4. Local editor buffer + dirty tracking.
  //
  // Codex Phase-2 P1 closure: the buffer is cleared IMMEDIATELY on
  // path change (no longer shows the previous tab's content while
  // the new GET is in flight) and stays empty until ``detail.data``
  // arrives. The save button is also gated on ``detail.data`` for
  // existing files, so a user cannot type and save before the etag
  // round-trip has completed — the backend's race-protection contract
  // (compare expected_etag with current_etag) is unconditionally
  // honored from the first POST.
  const [buffer, setBuffer] = useState<string>("");
  const [bufferEtag, setBufferEtag] = useState<string | null>(null);
  const [status, setStatus] = useState<SaveStatus>({ kind: "idle" });

  // Clear buffer the moment the user picks a different tab, so the
  // editor never displays stale-under-new-path content. If a persisted
  // draft exists for the new path, seed BOTH buffer AND bufferEtag
  // from the persisted envelope (Codex round-3 MED closure: keep the
  // etag at the value it had when the draft was authored, so a later
  // save surfaces 409 if the server has moved on).
  useEffect(() => {
    if (!activePath) {
      setBuffer("");
      setBufferEtag(null);
      setStatus({ kind: "idle" });
      return;
    }
    const persisted = readPersisted(caseId, activePath);
    setBuffer(persisted?.content ?? "");
    setBufferEtag(persisted?.etag ?? null);
    setStatus({ kind: "idle" });
  }, [activePath, caseId]);

  // Once a fresh GET arrives, populate from server UNLESS the user
  // has a persisted draft for this path (their unsaved work wins
  // until they explicitly save or discard).
  //
  // Two guards on detail.data (Codex round-3):
  //   (1) case_id guard: useQuery may surface data from the PREVIOUS
  //       case's query while the new case's GET is in flight. The
  //       Step 3 shell stays mounted across caseId changes, so the
  //       path can be identical but the content belongs to a different
  //       case.
  //   (2) path guard: same shape, applied within a single case during
  //       tab switches.
  //
  // When a persisted draft EXISTS, we deliberately do NOT overwrite
  // bufferEtag with the fresh server etag — keeping the persisted
  // (older) etag is what makes save surface 409 if AI re-authored
  // the file while the engineer was away.
  useEffect(() => {
    if (!detail.data || !activePath) return;
    if (detail.data.case_id !== caseId) return;
    if (detail.data.path !== activePath) return;
    const persisted = readPersisted(caseId, activePath);
    if (persisted === null) {
      setBuffer(detail.data.content);
      setBufferEtag(detail.data.etag);
    }
    // If persisted exists: keep buffer + bufferEtag as restored.
  }, [detail.data, activePath, caseId]);

  // Persist every keystroke. Strict gates (Codex rounds 2-3):
  //   (a) Only persist once detail.data has loaded for the active
  //       case+path — otherwise an empty buffer in the post-clear/
  //       pre-populate gap would be written to sessionStorage.
  //   (b) Skip persistence when buffer matches server content
  //       (no unsaved changes worth restoring).
  //   (c) Persist the bufferEtag (the etag at the time the draft
  //       was AUTHORED), not the latest server etag. This preserves
  //       conflict protection across remounts: if the server moves
  //       on, save will hit 409.
  useEffect(() => {
    if (!activePath || !detail.data) return;
    if (detail.data.case_id !== caseId) return;
    if (detail.data.path !== activePath) return;
    if (buffer === detail.data.content) {
      clearPersisted(caseId, activePath);
      return;
    }
    writePersisted(caseId, activePath, buffer, bufferEtag);
  }, [buffer, bufferEtag, detail.data, activePath, caseId]);

  // For existing files, the save button must wait until the GET
  // returns the current etag — otherwise a POST without expected_etag
  // would skip race protection. For never-authored paths, save is
  // available immediately (no etag to honor).
  const isExistingFileLoading = !!activeEntry?.exists && !detail.data;

  const isDirty = useMemo(() => {
    if (!detail.data) {
      // For not-yet-existing paths the user can author from scratch.
      return !activeEntry?.exists && buffer.length > 0;
    }
    return buffer !== detail.data.content;
  }, [buffer, detail.data, activeEntry]);

  // 5. Save handler. Honors etag for race protection; on 409 surfaces
  //    a refresh prompt; on 422 surfaces validation issues with optional
  //    force-bypass.
  const save = useCallback(
    async (opts?: { force?: boolean }) => {
      if (!activePath) return;
      setStatus({ kind: "saving" });
      try {
        const resp = await api.postRawDict(
          caseId,
          activePath,
          {
            content: buffer,
            ...(bufferEtag ? { expected_etag: bufferEtag } : {}),
          },
          opts,
        );
        setBufferEtag(resp.new_etag);
        setStatus({
          kind: "saved",
          message: `Saved · source=user · etag=${resp.new_etag.slice(0, 8)}`,
          warnings: resp.warnings.map((w) => `${w.severity}: ${w.message}`),
        });
        // Optimistically update the query cache so detail.data
        // immediately reflects the new server state. Without this,
        // the persist useEffect would race the cache invalidation:
        // it sees buffer != stale-detail.data.content and rewrites
        // sessionStorage right after we cleared it (Codex round-3
        // edge case from the "clears persisted draft on save" test).
        qc.setQueryData(["case-dict", caseId, activePath], {
          case_id: caseId,
          path: activePath,
          content: buffer,
          source: "user" as const,
          etag: resp.new_etag,
          edited_at: new Date().toISOString(),
        });
        // Save succeeded — clear the persisted draft so a future
        // remount picks up the server content rather than the (now
        // stale-but-saved) draft.
        clearPersisted(caseId, activePath);
        // Invalidate the LIST query so source/etag badges refresh.
        // (We don't invalidate the per-path detail query because we
        // just optimistically populated it; an invalidate here would
        // trigger an immediate refetch and could briefly show a
        // loading flicker.)
        qc.invalidateQueries({ queryKey: ["case-dicts-list", caseId] });
      } catch (exc) {
        if (exc instanceof ApiError && exc.status === 409) {
          const d = (exc.detail ?? {}) as {
            failing_check?: string;
            current_etag?: string;
          };
          setStatus({
            kind: "error",
            message:
              "File changed on disk since you opened it (concurrent AI overwrite or another tab). " +
              "Refresh to merge before retry.",
            conflictRefresh: d.current_etag
              ? { current_etag: d.current_etag }
              : undefined,
          });
        } else if (exc instanceof ApiError && exc.status === 422) {
          const d = (exc.detail ?? {}) as {
            failing_check?: string;
            issues?: { severity: string; message: string }[];
            hint?: string;
          };
          if (d.failing_check === "symlink_escape") {
            setStatus({
              kind: "error",
              message:
                "Refusing to write — the case directory has an unexpected " +
                "symlink at .case_lock. Inspect the directory before retry.",
            });
          } else {
            setStatus({
              kind: "error",
              message: d.hint ?? "Validation failed.",
              validationIssues: d.issues,
            });
          }
        } else {
          setStatus({
            kind: "error",
            message:
              exc instanceof Error
                ? exc.message
                : "Save failed for an unknown reason",
          });
        }
      }
    },
    [activePath, buffer, bufferEtag, caseId, qc],
  );

  const refreshFromServer = useCallback(() => {
    if (!activePath) return;
    // Discarding local changes also clears the persisted draft so a
    // remount doesn't resurrect the discarded edits.
    clearPersisted(caseId, activePath);
    qc.invalidateQueries({ queryKey: ["case-dict", caseId, activePath] });
    qc.invalidateQueries({ queryKey: ["case-dicts-list", caseId] });
    setStatus({ kind: "idle" });
  }, [activePath, caseId, qc]);

  if (list.isLoading) {
    return <div className="raw-dict-editor loading">Loading dict list…</div>;
  }
  if (list.isError) {
    return (
      <div className="raw-dict-editor error">
        Could not load dict list: {(list.error as Error)?.message ?? "unknown"}
      </div>
    );
  }
  if (visiblePaths.length === 0) {
    return (
      <div className="raw-dict-editor empty">
        No editable dict paths for this step.
      </div>
    );
  }

  return (
    <div className="raw-dict-editor">
      <div className="raw-dict-tabs" role="tablist">
        {visiblePaths.map((entry) => {
          const active = entry.path === activePath;
          const sourceBadge =
            entry.source === "user" ? "👤 user" : "🤖 ai";
          return (
            <button
              key={entry.path}
              type="button"
              role="tab"
              aria-selected={active}
              className={
                "raw-dict-tab" +
                (active ? " active" : "") +
                (entry.exists ? " exists" : " missing") +
                ` source-${entry.source}`
              }
              onClick={() => setActivePath(entry.path)}
            >
              <span className="raw-dict-tab-path">{entry.path}</span>
              <span className="raw-dict-tab-meta">
                {entry.exists ? sourceBadge : "—"}
              </span>
            </button>
          );
        })}
      </div>

      {activePath && (
        <div className="raw-dict-pane">
          <header className="raw-dict-header">
            <h4>{activePath}</h4>
            {detail.data && (
              <span className="raw-dict-meta">
                source={detail.data.source}
                {detail.data.edited_at && ` · edited ${detail.data.edited_at}`}
                {bufferEtag && ` · etag=${bufferEtag.slice(0, 8)}`}
              </span>
            )}
            {!activeEntry?.exists && (
              <span className="raw-dict-meta missing">
                File not authored yet — save will create it.
              </span>
            )}
          </header>

          {detail.isFetching && (
            <div className="raw-dict-loading" data-testid="raw-dict-loading">
              Loading content…
            </div>
          )}
          {detail.isError && (
            <div
              className="raw-dict-status error"
              role="alert"
              data-testid="raw-dict-load-error"
            >
              Could not load file:{" "}
              {(detail.error as Error)?.message ?? "unknown error"}
            </div>
          )}

          <CodeMirror
            value={buffer}
            height="320px"
            theme="light"
            onChange={(value) => setBuffer(value)}
            basicSetup={{
              lineNumbers: true,
              foldGutter: true,
              highlightActiveLine: true,
            }}
          />

          <div className="raw-dict-actions">
            <button
              type="button"
              className="raw-dict-save"
              data-testid="raw-dict-save"
              disabled={
                !isDirty ||
                status.kind === "saving" ||
                isExistingFileLoading
              }
              onClick={() => save()}
              title={
                isExistingFileLoading
                  ? "Waiting for the current file etag — save unlocks once the file is loaded so race protection is preserved."
                  : undefined
              }
            >
              {status.kind === "saving" ? "Saving…" : "Save (record as user override)"}
            </button>
            <button
              type="button"
              className="raw-dict-refresh"
              onClick={refreshFromServer}
              disabled={status.kind === "saving"}
            >
              Discard local changes
            </button>
            {status.validationIssues && (
              <button
                type="button"
                className="raw-dict-force"
                onClick={() => save({ force: true })}
                title="Bypass content validation; the edit is still recorded as source=user with force_bypass=true in the audit history."
              >
                Force save (bypass validation)
              </button>
            )}
          </div>

          {status.kind === "saved" && (
            <div className="raw-dict-status saved" role="status">
              {status.message}
              {status.warnings && status.warnings.length > 0 && (
                <ul className="raw-dict-warnings">
                  {status.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {status.kind === "error" && (
            <div className="raw-dict-status error" role="alert">
              {status.message}
              {status.validationIssues && (
                <ul className="raw-dict-issues">
                  {status.validationIssues.map((issue, i) => (
                    <li key={i} className={`severity-${issue.severity}`}>
                      [{issue.severity}] {issue.message}
                    </li>
                  ))}
                </ul>
              )}
              {status.conflictRefresh && (
                <button
                  type="button"
                  className="raw-dict-refresh-conflict"
                  onClick={refreshFromServer}
                >
                  Refresh from server
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
