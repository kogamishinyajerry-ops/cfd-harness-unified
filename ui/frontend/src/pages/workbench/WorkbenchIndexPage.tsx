import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { CaseIndexEntry } from "@/types/validation";

// Workbench 60-day extension · 2026-04-26 — /workbench landing index.
//
// Surfaces the 10 whitelist cases as a card grid so users can land on
// /workbench, pick one, and discover the closed loop without having to
// know the case_id URL fragment by hand. Each card links to the three
// per-case workbench surfaces: edit params, run history, and the most
// recent run detail. Reuses the existing api.listCases() response —
// no new backend endpoint, line-A only.

export function WorkbenchIndexPage() {
  const casesQuery = useQuery({
    queryKey: ["workbenchIndexCases"],
    queryFn: () => api.listCases(),
  });

  if (casesQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading cases…</p></Section>;
  }
  if (casesQuery.isError || !casesQuery.data) {
    const msg =
      casesQuery.error instanceof ApiError
        ? `${casesQuery.error.status}: ${casesQuery.error.message}`
        : String(casesQuery.error);
    return (
      <Section>
        <p className="text-sm text-contract-fail">Failed to load cases: {msg}</p>
      </Section>
    );
  }

  const cases = casesQuery.data;

  return (
    <Section>
      <header className="mb-6">
        <div className="flex items-baseline justify-between">
          <h1 className="text-2xl font-semibold text-surface-100">Workbench</h1>
          <div className="flex items-center gap-2">
            <Link
              to="/workbench/import"
              className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1 text-xs text-surface-200 transition hover:bg-surface-800"
            >
              Import STL →
            </Link>
            <Link
              to="/workbench/today"
              className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
            >
              Today's runs →
            </Link>
          </div>
        </div>
        <p className="mt-1 text-[13px] text-surface-400">
          Pick a case to edit parameters and run a real Docker + OpenFOAM
          execution. Every run is persisted under
          <code className="mx-1 rounded-sm bg-surface-900 px-1 py-0.5 font-mono text-[11px]">
            reports/{`{case_id}`}/runs/{`{run_id}`}/
          </code>
          as an audit trail.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {cases.map((c) => (
          <CaseCard key={c.case_id} c={c} />
        ))}
      </div>
    </Section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-6xl px-8 py-8">{children}</section>;
}

function CaseCard({ c }: { c: CaseIndexEntry }) {
  const editHref = `/workbench/case/${encodeURIComponent(c.case_id)}/edit`;
  const runsHref = `/workbench/case/${encodeURIComponent(c.case_id)}/runs`;
  return (
    <div className="flex flex-col rounded-md border border-surface-800 bg-surface-900/40 p-4 transition hover:border-surface-700">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-surface-100">{c.name}</h3>
          <p className="mt-0.5 font-mono text-[11px] text-surface-500">{c.case_id}</p>
        </div>
        <ContractChip status={c.contract_status} />
      </div>

      <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-[11px]">
        <dt className="font-mono text-surface-500">flow</dt>
        <dd className="font-mono text-surface-300">{c.flow_type}</dd>
        <dt className="font-mono text-surface-500">geometry</dt>
        <dd className="font-mono text-surface-300">{c.geometry_type}</dd>
        <dt className="font-mono text-surface-500">turbulence</dt>
        <dd className="font-mono text-surface-300">{c.turbulence_model}</dd>
      </dl>

      <div className="mt-auto flex items-center justify-between pt-4">
        <span className="text-[10px] text-surface-500">
          {c.run_summary?.total ?? 0} historical run{(c.run_summary?.total ?? 0) === 1 ? "" : "s"}
        </span>
        <div className="flex gap-2">
          <Link
            to={runsHref}
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
          >
            Runs
          </Link>
          <Link
            to={editHref}
            className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
          >
            Edit & run →
          </Link>
        </div>
      </div>
    </div>
  );
}

function ContractChip({ status }: { status: string }) {
  // The contract_status values are PASS / PASS_WITH_DEVIATIONS / FAIL /
  // INCOMPATIBLE / etc. — colour-tone by family without hard-coding the
  // full enum, so additions on the backend don't silently render plain.
  const tone = status.startsWith("PASS")
    ? "border-contract-pass/40 bg-contract-pass/10 text-contract-pass"
    : status === "FAIL" || status === "INCOMPATIBLE"
      ? "border-contract-fail/40 bg-contract-fail/10 text-contract-fail"
      : "border-amber-500/40 bg-amber-500/10 text-amber-300";
  return (
    <span
      className={`whitespace-nowrap rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${tone}`}
    >
      {status}
    </span>
  );
}
