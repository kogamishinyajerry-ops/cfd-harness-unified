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
  const [buffer, setBuffer] = useState<string>("");
  const [bufferEtag, setBufferEtag] = useState<string | null>(null);
  const [status, setStatus] = useState<SaveStatus>({ kind: "idle" });

  useEffect(() => {
    // Reset buffer on path change OR when a fresh GET arrives.
    if (detail.data) {
      setBuffer(detail.data.content);
      setBufferEtag(detail.data.etag);
      setStatus({ kind: "idle" });
    } else if (activePath && activeEntry && !activeEntry.exists) {
      setBuffer("");
      setBufferEtag(null);
      setStatus({ kind: "idle" });
    }
  }, [detail.data, activePath, activeEntry]);

  const isDirty = useMemo(() => {
    if (!detail.data) return buffer.length > 0;
    return buffer !== detail.data.content;
  }, [buffer, detail.data]);

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
        // Invalidate so the tab list re-fetches the source/etag flag.
        qc.invalidateQueries({ queryKey: ["case-dicts-list", caseId] });
        qc.invalidateQueries({ queryKey: ["case-dict", caseId, activePath] });
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
            <div className="raw-dict-loading">Loading content…</div>
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
              disabled={!isDirty || status.kind === "saving"}
              onClick={() => save()}
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
