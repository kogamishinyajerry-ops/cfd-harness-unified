// Phase 5 · Screen 6 · Audit Package Builder
// DEC-V61-018 · PR-5d (+ PR-5d.1 Codex follow-up)
//
// Per-case "Build audit package" trigger → POST to backend → display
// bundle_id, download links for manifest / zip / html / pdf / sig, the
// internal V&V evidence-summary mapping, and the signature hex.
//
// Note: the evidence-summary table is NOT a faithful FDA/ASME V&V40
// template — it's a product-specific summary of which manifest fields
// cover which V&V concerns. Labelling was corrected in PR-5d.1 to avoid
// implying FDA coverage the artifact does not provide.
//
// Non-goals for PR-5d:
// - Async progress streaming (SSE) — deferred to PR-5e.
// - Bundle history list — each build is independent; operator can keep
//   downloads locally if they need a trail.
// - Batch export across cases — Phase 6 per DEC-V61-002.

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type { AuditPackageBuildResponse } from "@/types/audit_package";
import type { CaseIndexEntry } from "@/types/validation";

export function AuditPackagePage() {
  const { data: cases } = useQuery<CaseIndexEntry[]>({
    queryKey: ["cases"],
    queryFn: api.listCases,
  });

  const [caseId, setCaseId] = useState<string>("");
  const [runId, setRunId] = useState<string>("mock-run-1");

  const buildMutation = useMutation<AuditPackageBuildResponse, Error, void>({
    mutationFn: () => api.buildAuditPackage(caseId, runId),
  });

  const result = buildMutation.data;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
          Phase 5 · Screen 6
        </p>
        <h1 className="text-2xl font-semibold text-surface-100">
          Audit Package Builder
        </h1>
        <p className="mt-1 text-sm text-surface-400">
          One-click export of a signed V&amp;V evidence bundle. Each bundle
          pins git commit SHAs so the reviewer can reconstruct the exact
          repo state that produced the signature. The internal evidence
          summary below is a product-specific mapping — it is not a
          substitute for a formal FDA/ASME V&amp;V40 credibility template.
        </p>
      </header>

      {/* Build trigger card */}
      <div className="card p-4 space-y-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_auto]">
          <label className="block text-sm">
            <span className="mb-1 block text-xs uppercase tracking-wider text-surface-400">
              Case
            </span>
            <select
              className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1.5 text-sm text-surface-100"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
            >
              <option value="">— select a case —</option>
              {(cases ?? []).map((c) => (
                <option key={c.case_id} value={c.case_id}>
                  {c.name} ({c.case_id})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-xs uppercase tracking-wider text-surface-400">
              Run ID
            </span>
            <input
              type="text"
              className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1.5 text-sm text-surface-100"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="e.g. mock-run-1 or a real solver run id"
            />
          </label>
          <div className="flex items-end">
            <button
              className="w-full rounded-sm bg-accent-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 md:w-auto"
              onClick={() => buildMutation.mutate()}
              disabled={!caseId || !runId || buildMutation.isPending}
            >
              {buildMutation.isPending ? "Building…" : "Build audit package"}
            </button>
          </div>
        </div>

        {buildMutation.isError && (
          <div className="rounded-sm border border-contract-fail/40 bg-contract-fail/10 p-3 text-sm text-contract-fail">
            Build failed: {(buildMutation.error as Error).message}
          </div>
        )}
      </div>

      {/* Result card */}
      {result && <BuildResult result={result} />}
    </div>
  );
}

function BuildResult({ result }: { result: AuditPackageBuildResponse }) {
  const verdictClass =
    result.comparator_verdict === "PASS"
      ? "text-contract-pass"
      : result.comparator_verdict === "FAIL"
        ? "text-contract-fail"
        : result.comparator_verdict === "HAZARD"
          ? "text-contract-hazard"
          : "text-surface-400";

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="card p-4">
        <div className="mb-2 text-xs uppercase tracking-wider text-surface-400">
          Bundle summary
        </div>
        <div className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
          <KV k="Manifest ID" v={<code className="mono">{result.manifest_id}</code>} />
          <KV k="Bundle ID" v={<code className="mono">{result.bundle_id}</code>} />
          <KV k="Generated at" v={result.generated_at} />
          <KV
            k="Verdict"
            v={
              <span className={`font-semibold ${verdictClass}`}>
                {result.comparator_verdict ?? "—"}
              </span>
            }
          />
          <KV
            k="Git HEAD"
            v={
              result.git_repo_commit_sha ? (
                <code className="mono text-[11px]">{result.git_repo_commit_sha}</code>
              ) : (
                <span className="text-surface-500">(not in a git repo)</span>
              )
            }
          />
          <KV
            k="Signature (HMAC-SHA256)"
            v={<code className="mono text-[11px]">{result.signature_hex}</code>}
          />
        </div>
      </div>

      {/* Downloads */}
      <div className="card p-4">
        <div className="mb-3 text-xs uppercase tracking-wider text-surface-400">
          Downloads
        </div>
        <ul className="space-y-1 text-sm">
          <DLink label="manifest.json" href={result.downloads.manifest_json} />
          <DLink label="bundle.zip (byte-reproducible)" href={result.downloads.bundle_zip} />
          <DLink label="bundle.html (reviewer-friendly)" href={result.downloads.bundle_html} />
          {result.downloads.bundle_pdf ? (
            <DLink label="bundle.pdf (printable)" href={result.downloads.bundle_pdf} />
          ) : (
            <li className="text-xs text-surface-500">
              PDF unavailable on this host.
              {result.pdf_error && <span className="ml-1">{result.pdf_error}</span>}
            </li>
          )}
          <DLink label="bundle.sig (HMAC sidecar)" href={result.downloads.bundle_sig} />
        </ul>
      </div>

      {/* Internal V&V evidence summary (PR-5d.1 — renamed per Codex MEDIUM) */}
      <div className="card p-4">
        <div className="mb-1 text-xs uppercase tracking-wider text-surface-400">
          Internal V&amp;V evidence summary
        </div>
        <p className="mb-3 text-[11px] text-surface-500">
          Not a substitute for a formal FDA/ASME V&amp;V40 template.
          Fields scoped to run artifacts (run.inputs, run.outputs.*,
          measurement.*) are empty in skeleton bundles.
        </p>
        <table className="w-full text-sm">
          <thead className="text-left text-[10px] uppercase tracking-wider text-surface-400">
            <tr>
              <th className="px-2 py-1 font-medium">Area</th>
              <th className="px-2 py-1 font-medium">Manifest fields</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-700">
            {result.evidence_summary.map((item) => (
              <tr key={item.area}>
                <td className="px-2 py-2 align-top">
                  <div className="text-surface-100">{item.area}</div>
                  <div className="text-xs text-surface-400">
                    {item.description}
                  </div>
                </td>
                <td className="px-2 py-2 align-top">
                  <div className="flex flex-wrap gap-1">
                    {item.manifest_fields.map((f) => (
                      <code
                        key={f}
                        className="mono rounded-sm bg-surface-800 px-1.5 py-0.5 text-[11px] text-surface-200"
                      >
                        {f}
                      </code>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="w-44 shrink-0 text-xs uppercase tracking-wider text-surface-400">
        {k}
      </span>
      <span className="flex-1 break-all text-surface-100">{v}</span>
    </div>
  );
}

function DLink({ label, href }: { label: string; href: string }) {
  return (
    <li>
      <a
        className="text-accent-400 hover:text-accent-300 hover:underline"
        href={href}
        download
      >
        {label}
      </a>
    </li>
  );
}
