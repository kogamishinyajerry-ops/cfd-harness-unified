import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import CodeMirror from "@uiw/react-codemirror";
import { yaml as yamlLang } from "@codemirror/lang-yaml";
import jsYaml from "js-yaml";

import { api, ApiError } from "@/api/client";
import type { CaseYamlPayload, CaseYamlLintResult } from "@/types/editor";

// Phase 1 — Case Editor. CodeMirror 6 w/ @codemirror/lang-yaml for
// highlighting, js-yaml for synchronous client-side lint (debounced),
// backend PUT /api/cases/{id}/yaml for durable save. Saves land in
// ui/backend/user_drafts/{id}.yaml — NEVER knowledge/whitelist.yaml
// (hard-floor-1 / hard-floor-2 per DEC-V61-002).

function clientLint(yaml_text: string): CaseYamlLintResult {
  try {
    const parsed = jsYaml.load(yaml_text);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {
        ok: false,
        errors: ["Top-level must be a mapping (dict)."],
        warnings: [],
      };
    }
    const warnings: string[] = [];
    const required = ["id", "name", "flow_type", "geometry_type", "turbulence_model"];
    const obj = parsed as Record<string, unknown>;
    for (const k of required) {
      if (!(k in obj)) warnings.push(`Missing recommended field: '${k}'`);
    }
    return { ok: true, errors: [], warnings };
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : String(exc);
    return { ok: false, errors: [message], warnings: [] };
  }
}

export function CaseEditorPage() {
  const { caseId = "" } = useParams<{ caseId: string }>();
  const qc = useQueryClient();
  const sourceQuery = useQuery({
    queryKey: ["caseYaml", caseId],
    queryFn: () => api.getCaseYaml(caseId),
    enabled: Boolean(caseId),
  });

  const [buffer, setBuffer] = useState<string | null>(null);
  const [lint, setLint] = useState<CaseYamlLintResult>({ ok: true, errors: [], warnings: [] });
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    if (sourceQuery.data && buffer === null) {
      setBuffer(sourceQuery.data.yaml_text);
    }
  }, [sourceQuery.data, buffer]);

  useEffect(() => {
    if (buffer === null) return;
    const t = window.setTimeout(() => setLint(clientLint(buffer)), 180);
    return () => window.clearTimeout(t);
  }, [buffer]);

  const saveMutation = useMutation({
    mutationFn: (payload: CaseYamlPayload) => api.putCaseYaml(payload),
    onSuccess: (data) => {
      setStatus(
        data.saved
          ? `saved draft → ${data.draft_path}`
          : `rejected: ${data.lint.errors.join("; ")}`,
      );
      if (data.saved) qc.invalidateQueries({ queryKey: ["caseYaml", caseId] });
    },
    onError: (err) => {
      setStatus(err instanceof ApiError ? `HTTP ${err.status}: ${err.message}` : String(err));
    },
  });

  const revertMutation = useMutation({
    mutationFn: () => api.revertCaseYaml(caseId),
    onSuccess: (data) => {
      setBuffer(data.yaml_text);
      setStatus(`reverted — source now '${data.origin}'`);
      qc.invalidateQueries({ queryKey: ["caseYaml", caseId] });
    },
    onError: (err) => {
      setStatus(err instanceof ApiError ? `HTTP ${err.status}: ${err.message}` : String(err));
    },
  });

  const isDirty = useMemo(() => {
    return Boolean(sourceQuery.data && buffer !== null && buffer !== sourceQuery.data.yaml_text);
  }, [buffer, sourceQuery.data]);

  const origin = sourceQuery.data?.origin ?? "loading";

  if (sourceQuery.isLoading) {
    return (
      <section className="px-8 py-10 text-surface-300">Loading case YAML…</section>
    );
  }
  if (sourceQuery.isError) {
    const err = sourceQuery.error;
    const msg = err instanceof ApiError ? `${err.status}: ${err.message}` : String(err);
    return (
      <section className="px-8 py-10">
        <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 px-4 py-3 text-sm text-contract-fail">
          Failed to load case YAML: {msg}
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col h-full">
      <header className="border-b border-surface-800 bg-surface-900/40 px-8 py-4">
        <div className="text-[11px] uppercase tracking-wider text-surface-500">
          <Link to="/cases" className="hover:text-surface-300">Cases</Link>
          <span className="mx-1.5">/</span>
          <span>{caseId}</span>
          <span className="mx-1.5">/</span>
          <span>editor</span>
        </div>
        <h1 className="mt-1 text-xl font-semibold text-surface-100">Case Editor · {caseId}</h1>
        <div className="mt-2 flex items-center gap-4 text-[11px] text-surface-400">
          <span>
            source origin: <strong className="font-mono text-surface-200">{origin}</strong>
          </span>
          {sourceQuery.data?.draft_path && (
            <span>
              draft: <code className="text-surface-300">{sourceQuery.data.draft_path}</code>
            </span>
          )}
          <span>
            dirty: <strong className={isDirty ? "text-contract-hazard" : "text-contract-pass"}>{isDirty ? "yes" : "no"}</strong>
          </span>
          <span>
            lint: <strong className={lint.ok ? "text-contract-pass" : "text-contract-fail"}>
              {lint.ok ? "ok" : `${lint.errors.length} error${lint.errors.length === 1 ? "" : "s"}`}
            </strong>
            {lint.ok && lint.warnings.length > 0 && (
              <span className="ml-1.5 text-contract-hazard">· {lint.warnings.length} warning{lint.warnings.length === 1 ? "" : "s"}</span>
            )}
          </span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-auto">
          <CodeMirror
            value={buffer ?? ""}
            height="100%"
            theme="dark"
            extensions={[yamlLang()]}
            basicSetup={{ lineNumbers: true, foldGutter: true, highlightActiveLine: true }}
            onChange={(val) => setBuffer(val)}
            className="text-[12.5px]"
          />
        </div>
        <aside className="w-80 shrink-0 border-l border-surface-800 bg-surface-900/40 overflow-y-auto">
          <div className="p-4 space-y-3">
            <div className="flex gap-2">
              <button
                type="button"
                disabled={!isDirty || !lint.ok || saveMutation.isPending}
                onClick={() => buffer !== null && saveMutation.mutate({
                  case_id: caseId,
                  yaml_text: buffer,
                  origin: "draft",
                  draft_path: null,
                })}
                className="flex-1 rounded-sm bg-contract-pass/80 px-3 py-1.5 text-sm font-medium text-surface-950 transition hover:bg-contract-pass disabled:bg-surface-800 disabled:text-surface-500"
              >
                {saveMutation.isPending ? "Saving…" : "Save draft"}
              </button>
              <button
                type="button"
                disabled={revertMutation.isPending || origin !== "draft"}
                onClick={() => revertMutation.mutate()}
                className="rounded-sm border border-surface-700 bg-surface-800/50 px-3 py-1.5 text-sm text-surface-300 transition hover:bg-surface-800 disabled:opacity-40"
              >
                Revert
              </button>
            </div>
            {status && (
              <p className="text-[11px] font-mono text-surface-300 break-all">{status}</p>
            )}
            <div>
              <h3 className="text-[11px] uppercase tracking-wider text-surface-400">Lint errors</h3>
              {lint.errors.length === 0 ? (
                <p className="mt-1 text-xs text-surface-500">— none —</p>
              ) : (
                <ul className="mt-1 space-y-1 text-xs text-contract-fail">
                  {lint.errors.map((e, i) => (
                    <li key={i} className="break-words rounded-sm bg-contract-fail/10 px-2 py-1 font-mono">{e}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="text-[11px] uppercase tracking-wider text-surface-400">Lint warnings</h3>
              {lint.warnings.length === 0 ? (
                <p className="mt-1 text-xs text-surface-500">— none —</p>
              ) : (
                <ul className="mt-1 space-y-1 text-xs text-contract-hazard">
                  {lint.warnings.map((w, i) => (
                    <li key={i} className="break-words rounded-sm bg-contract-hazard/10 px-2 py-1">{w}</li>
                  ))}
                </ul>
              )}
            </div>
            <div className="rounded-md border border-surface-800 bg-surface-950/40 p-3 text-[11px] text-surface-400">
              <p className="font-semibold text-surface-300">禁区 guard</p>
              <p className="mt-1">
                Drafts land in <code className="text-surface-300">ui/backend/user_drafts/</code>.
                <br />Never overwrites <code>knowledge/whitelist.yaml</code> or
                <code className="ml-1">knowledge/gold_standards/**</code>.
                Promotion requires external Gate review (Phase 5).
              </p>
            </div>
            <div className="flex gap-2 pt-2">
              <Link
                to={`/cases/${caseId}/report`}
                className="flex-1 rounded-sm border border-surface-700 bg-surface-800/40 px-3 py-1.5 text-center text-xs text-surface-300 transition hover:bg-surface-800"
              >
                View report →
              </Link>
              <Link
                to={`/runs/${caseId}`}
                className="flex-1 rounded-sm border border-surface-700 bg-surface-800/40 px-3 py-1.5 text-center text-xs text-surface-300 transition hover:bg-surface-800"
              >
                Open run monitor →
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
