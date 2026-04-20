import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import { PassFailChip } from "@/components/PassFailChip";

// Phase 4 — Project Dashboard (Screen 1). Aggregates 10-case matrix,
// gate queue, decision timeline, project-level summary counters.

function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/50 p-4">
      <p className="text-[10px] uppercase tracking-wider text-surface-500">{label}</p>
      <p className="mt-0.5 text-2xl font-semibold text-surface-100">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-surface-400">{hint}</p>}
    </div>
  );
}

export function DashboardPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.getDashboard,
  });

  if (isLoading) return <section className="px-8 py-10 text-surface-300">Loading dashboard…</section>;
  if (isError || !data) {
    const msg = error instanceof ApiError ? `${error.status}: ${error.message}` : String(error);
    return (
      <section className="px-8 py-10 text-sm text-contract-fail">Failed to load dashboard: {msg}</section>
    );
  }

  const {
    cases,
    gate_queue,
    timeline,
    summary,
    current_phase,
    autonomous_governance_counter,
  } = data;

  return (
    <section className="p-8 space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-surface-100">Project Dashboard</h1>
        <p className="mt-1 text-sm text-surface-400">
          One-glance view of the 10-case V&amp;V matrix, external gate queue, and decision timeline.
        </p>
        {current_phase && (
          <p className="mt-2 text-[11px] text-surface-500">
            current_phase: <strong className="font-mono text-surface-200">{current_phase}</strong>
            {autonomous_governance_counter !== null && (
              <span className="ml-3">autonomous_governance: <strong className="font-mono text-surface-200">{autonomous_governance_counter}/10</strong></span>
            )}
          </p>
        )}
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Cases" value={summary.total_cases ?? 0} hint="whitelist.yaml" />
        <StatCard label="PASS / HAZARD / FAIL" value={`${summary.pass_cases}·${summary.hazard_cases}·${summary.fail_cases}`} hint="per contract status" />
        <StatCard label="Open Gates" value={summary.open_gates ?? 0} hint={`${summary.closed_gates ?? 0} closed`} />
        <StatCard label="Decisions" value={timeline.length} hint={`${summary.accepted_decisions ?? 0} accepted · ${summary.closed_decisions ?? 0} closed`} />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-surface-100">Case matrix</h2>
        <div className="overflow-x-auto rounded-md border border-surface-800 bg-surface-900/30">
          <table className="w-full min-w-[800px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-surface-800 bg-surface-950/40 text-left text-[10px] uppercase tracking-wider text-surface-500">
                <th className="px-4 py-2">Case</th>
                <th className="px-4 py-2">Flow</th>
                <th className="px-4 py-2">Turbulence</th>
                <th className="px-4 py-2">Gold</th>
                <th className="px-4 py-2">Measurement</th>
                <th className="px-4 py-2">Contract</th>
                <th className="px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.case_id} className="border-b border-surface-800/50 hover:bg-surface-900/40">
                  <td className="px-4 py-2.5 text-surface-100">{c.name}</td>
                  <td className="px-4 py-2.5 text-surface-400">{c.flow_type}</td>
                  <td className="px-4 py-2.5 text-surface-400">{c.turbulence_model}</td>
                  <td className="px-4 py-2.5">
                    {c.has_gold_standard ? (
                      <span className="text-contract-pass">✓</span>
                    ) : (
                      <span className="text-surface-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {c.has_measurement ? (
                      <span className="text-contract-pass">✓</span>
                    ) : (
                      <span className="text-surface-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5"><PassFailChip status={c.contract_status} /></td>
                  <td className="px-4 py-2.5 text-[11px] text-surface-400">
                    <Link to={`/cases/${c.case_id}/report`} className="mr-2 hover:text-surface-100 underline-offset-2 hover:underline">Report</Link>
                    <Link to={`/cases/${c.case_id}/edit`} className="mr-2 hover:text-surface-100 underline-offset-2 hover:underline">Edit</Link>
                    <Link to={`/runs/${c.case_id}`} className="hover:text-surface-100 underline-offset-2 hover:underline">Run</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
        <div>
          <h2 className="mb-3 text-sm font-semibold text-surface-100">External Gate Queue</h2>
          <ul className="space-y-2">
            {gate_queue.map((g) => (
              <li
                key={g.qid}
                className="rounded-md border border-surface-800 bg-surface-900/40 p-3 text-[12.5px]"
              >
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className={`inline-block h-1.5 w-1.5 rounded-full ${g.state === "OPEN" ? "bg-contract-hazard" : "bg-contract-pass"}`}
                  />
                  <strong className="font-mono text-surface-100">{g.qid}</strong>
                  <span className="ml-auto text-[10px] uppercase tracking-wider text-surface-500">{g.state}</span>
                </div>
                <p className="mt-1 text-surface-200">{g.title}</p>
                {g.summary && <p className="mt-1 text-[11px] text-surface-500">{g.summary}</p>}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold text-surface-100">Decision timeline</h2>
          <ol className="space-y-2 border-l border-surface-800 pl-4">
            {timeline.map((t) => (
              <li key={t.decision_id + t.date} className="relative text-[12.5px]">
                <span aria-hidden className="absolute -left-[21px] top-1.5 inline-block h-2 w-2 rounded-full bg-surface-700" />
                <div className="flex items-baseline gap-2">
                  <time className="font-mono text-[10px] text-surface-500">{t.date}</time>
                  <strong className="font-mono text-surface-100">{t.decision_id}</strong>
                  {t.autonomous && (
                    <span className="rounded-sm bg-surface-800 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-surface-400">autonomous</span>
                  )}
                  <span className="ml-auto text-[10px] text-surface-500">{t.column}</span>
                </div>
                <p className="mt-0.5 text-surface-200">{t.title}</p>
                {(t.notion_url || t.github_pr_url) && (
                  <div className="mt-0.5 flex gap-2 text-[10px] text-surface-400">
                    {t.notion_url && (
                      <a href={t.notion_url} target="_blank" rel="noreferrer noopener" className="hover:text-surface-200 underline-offset-2 hover:underline">Notion ↗</a>
                    )}
                    {t.github_pr_url && (
                      <a href={t.github_pr_url} target="_blank" rel="noreferrer noopener" className="hover:text-surface-200 underline-offset-2 hover:underline">PR ↗</a>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
