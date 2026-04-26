import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";

// M3 · Workbench Closed-Loop main-line — /workbench/case/:caseId/runs
//
// Newest-first table of past runs for a single case. Each row links to its
// detail page (/workbench/case/:caseId/run/:runId). Read-only; no buttons
// to delete a run from this surface — runs are filesystem-backed under
// reports/{case_id}/runs/{run_id}/ and intentionally permanent so the user
// has an audit trail of every Re/Ra/etc. they tried.

export function RunHistoryPage() {
  const { caseId = "" } = useParams<{ caseId: string }>();
  const runsQuery = useQuery({
    queryKey: ["workbenchRuns", caseId],
    queryFn: () => api.listRuns(caseId),
    enabled: Boolean(caseId),
  });

  if (!caseId) {
    return (
      <Section>
        <p className="text-sm text-contract-fail">missing :caseId path param</p>
      </Section>
    );
  }
  if (runsQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading run history…</p></Section>;
  }
  if (runsQuery.isError || !runsQuery.data) {
    const msg =
      runsQuery.error instanceof ApiError
        ? `${runsQuery.error.status}: ${runsQuery.error.message}`
        : String(runsQuery.error);
    return (
      <Section>
        <p className="text-sm text-contract-fail">Failed to load runs: {msg}</p>
      </Section>
    );
  }

  const runs = runsQuery.data.runs;

  return (
    <Section>
      <header className="mb-6">
        <div className="text-[11px] uppercase tracking-wider text-surface-500">
          <Link to="/learn" className="hover:text-surface-300">Learn</Link>
          <span className="mx-1.5">/</span>
          <Link to={`/learn/cases/${caseId}`} className="hover:text-surface-300">{caseId}</Link>
          <span className="mx-1.5">/</span>
          <span>runs</span>
        </div>
        <div className="mt-1 flex items-baseline justify-between">
          <h1 className="text-2xl font-semibold text-surface-100">Runs · {caseId}</h1>
          <Link
            to={`/workbench/case/${encodeURIComponent(caseId)}/edit`}
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1 text-xs text-surface-300 transition hover:bg-surface-800"
          >
            + New run
          </Link>
        </div>
        <p className="mt-1 text-[12px] text-surface-400">
          Read-only audit trail of every real-solver execution.
          Each row is one entry under <code>reports/{caseId}/runs/</code>.
        </p>
      </header>

      {runs.length === 0 ? (
        <div className="rounded-md border border-dashed border-surface-700 p-8 text-center">
          <p className="text-sm text-surface-400">No runs yet for this case.</p>
          <Link
            to={`/workbench/case/${encodeURIComponent(caseId)}/edit`}
            className="mt-2 inline-block text-sm text-emerald-400 hover:text-emerald-300"
          >
            Open the param editor →
          </Link>
        </div>
      ) : (
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-surface-800 text-[11px] uppercase tracking-wider text-surface-500">
              <th className="px-3 py-2 text-left">started</th>
              <th className="px-3 py-2 text-left">params</th>
              <th className="px-3 py-2 text-right">duration</th>
              <th className="px-3 py-2 text-right">exit</th>
              <th className="px-3 py-2 text-left">verdict</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr
                key={r.run_id}
                className="group border-b border-surface-900 transition hover:bg-surface-900/40"
              >
                <td className="px-3 py-2 align-top">
                  <Link
                    to={`/workbench/case/${encodeURIComponent(caseId)}/run/${encodeURIComponent(r.run_id)}`}
                    className="font-mono text-[12px] text-surface-100 hover:text-emerald-300"
                  >
                    {formatStartedAt(r.started_at)}
                  </Link>
                  <div className="mt-0.5 font-mono text-[10px] text-surface-500">{r.run_id}</div>
                </td>
                <td className="px-3 py-2 align-top">
                  <ParamsExcerpt excerpt={r.task_spec_excerpt} />
                </td>
                <td className="px-3 py-2 text-right align-top font-mono text-[12px] text-surface-300">
                  {formatDuration(r.duration_s)}
                </td>
                <td className="px-3 py-2 text-right align-top font-mono text-[12px]">
                  <code
                    className={
                      r.success
                        ? "text-contract-pass"
                        : r.exit_code === 137
                          ? "text-amber-400"
                          : "text-contract-fail"
                    }
                  >
                    {r.exit_code}
                  </code>
                </td>
                <td className="px-3 py-2 align-top text-[12px] text-surface-300">
                  <span
                    className={
                      r.success
                        ? "rounded-sm bg-contract-pass/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-contract-pass"
                        : "rounded-sm bg-contract-fail/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-contract-fail"
                    }
                  >
                    {r.success ? "ok" : "fail"}
                  </span>
                  <span className="ml-2 text-surface-400">{r.verdict_summary}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-6xl px-8 py-8">{children}</section>;
}

function ParamsExcerpt({ excerpt }: { excerpt: Record<string, unknown> }) {
  // Show only the most useful keys, in stable order.
  const ordered = ["Re", "Ra", "Re_tau", "Ma"];
  const items: { k: string; v: string }[] = [];
  for (const k of ordered) {
    if (k in excerpt && excerpt[k] !== null && excerpt[k] !== undefined) {
      items.push({ k, v: String(excerpt[k]) });
    }
  }
  if (items.length === 0) {
    return <span className="font-mono text-[11px] text-surface-500">—</span>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map(({ k, v }) => (
        <span
          key={k}
          className="rounded-sm border border-surface-800 bg-surface-900 px-1.5 py-0.5 font-mono text-[11px] text-surface-300"
        >
          {k}={v}
        </span>
      ))}
    </div>
  );
}

function formatStartedAt(iso: string): string {
  if (!iso) return "—";
  // ISO-8601 → human readable local time. Keep it terse, the run_id row
  // below it is the unique identifier.
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function formatDuration(s: number): string {
  if (!s || s < 0) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const r = (s - m * 60).toFixed(0);
  return `${m}m ${r}s`;
}
