import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { RunSummaryEntry } from "@/types/run_history";
import { FAILURE_CATEGORY_LABEL_ZH } from "@/types/run_history";

// Workbench 60-day extension #3 · 2026-04-26 — /workbench/today.
//
// Cross-case "today's runs" dashboard: aggregates the newest 50 runs
// across every case bucket under reports/*/runs/ into a single newest-
// first feed grouped by date. Answers "what did I run today across the
// whole project?" in one glance, instead of drilling into each case's
// /run-history individually.
//
// Reuses RunSummaryEntry from M3 — same row shape as the per-case
// history table — and adds a `case` column so cross-case rows are
// disambiguated.

const RECENT_LIMIT = 50;

export function WorkbenchTodayPage() {
  const recentQuery = useQuery({
    queryKey: ["workbenchRecent", RECENT_LIMIT],
    queryFn: () => api.listRecentRuns(RECENT_LIMIT),
  });

  if (recentQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading recent runs…</p></Section>;
  }
  if (recentQuery.isError || !recentQuery.data) {
    const msg =
      recentQuery.error instanceof ApiError
        ? `${recentQuery.error.status}: ${recentQuery.error.message}`
        : String(recentQuery.error);
    return (
      <Section><p className="text-sm text-contract-fail">Failed to load: {msg}</p></Section>
    );
  }

  const runs = recentQuery.data.runs;
  const groups = groupByLocalDate(runs);
  const passN = runs.filter((r) => r.success).length;
  const failN = runs.length - passN;

  return (
    <Section>
      <header className="mb-6">
        <div className="text-[11px] uppercase tracking-wider text-surface-500">
          <Link to="/workbench" className="hover:text-surface-300">Workbench</Link>
          <span className="mx-1.5">/</span>
          <span>today</span>
        </div>
        <div className="mt-1 flex items-baseline justify-between">
          <h1 className="text-2xl font-semibold text-surface-100">Recent runs · all cases</h1>
          <Link
            to="/workbench"
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1 text-xs text-surface-300 transition hover:bg-surface-800"
          >
            ← Case picker
          </Link>
        </div>
        <p className="mt-1 text-[12px] text-surface-400">
          Newest {runs.length} of all runs under <code>reports/*/runs/</code>.
          {runs.length > 0 && (
            <>
              {" · "}
              <span className="text-contract-pass">{passN} pass</span>
              {" · "}
              <span className="text-contract-fail">{failN} fail</span>
            </>
          )}
        </p>
      </header>

      {runs.length === 0 ? (
        <div className="rounded-md border border-dashed border-surface-700 p-8 text-center">
          <p className="text-sm text-surface-400">
            No runs yet across any case. Pick a case and run one.
          </p>
          <Link
            to="/workbench"
            className="mt-2 inline-block text-sm text-emerald-400 hover:text-emerald-300"
          >
            Open the case picker →
          </Link>
        </div>
      ) : (
        groups.map(({ date, items }) => (
          <DateGroup key={date} date={date} items={items} />
        ))
      )}
    </Section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-6xl px-8 py-8">{children}</section>;
}

function DateGroup({ date, items }: { date: string; items: RunSummaryEntry[] }) {
  return (
    <div className="mt-6">
      <h2 className="mb-2 text-[11px] uppercase tracking-wider text-surface-500">
        {date} · {items.length} run{items.length === 1 ? "" : "s"}
      </h2>
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-surface-800 text-[10px] uppercase tracking-wider text-surface-500">
            <th className="px-3 py-2 text-left">time</th>
            <th className="px-3 py-2 text-left">case</th>
            <th className="px-3 py-2 text-left">params</th>
            <th className="px-3 py-2 text-right">duration</th>
            <th className="px-3 py-2 text-left">verdict</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <RunRow key={`${r.case_id}/${r.run_id}`} r={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RunRow({ r }: { r: RunSummaryEntry }) {
  const detailHref = `/workbench/case/${encodeURIComponent(r.case_id)}/run/${encodeURIComponent(r.run_id)}`;
  return (
    <tr className="border-b border-surface-900 transition hover:bg-surface-900/40">
      <td className="px-3 py-2 align-top">
        <Link
          to={detailHref}
          className="font-mono text-[12px] text-surface-100 hover:text-emerald-300"
        >
          {formatTime(r.started_at)}
        </Link>
        <div className="mt-0.5 font-mono text-[10px] text-surface-500">{r.run_id}</div>
      </td>
      <td className="px-3 py-2 align-top">
        <Link
          to={`/workbench/case/${encodeURIComponent(r.case_id)}/runs`}
          className="font-mono text-[11px] text-surface-300 hover:text-emerald-300"
        >
          {r.case_id}
        </Link>
      </td>
      <td className="px-3 py-2 align-top">
        <ParamsExcerpt excerpt={r.task_spec_excerpt} />
      </td>
      <td className="px-3 py-2 text-right align-top font-mono text-[12px] text-surface-300">
        {formatDuration(r.duration_s)}
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
        {!r.success && r.failure_category && (
          <span
            title={r.failure_category}
            className="ml-2 rounded-sm border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-amber-300"
          >
            {FAILURE_CATEGORY_LABEL_ZH[r.failure_category]}
          </span>
        )}
      </td>
    </tr>
  );
}

function ParamsExcerpt({ excerpt }: { excerpt: Record<string, unknown> }) {
  const ordered = ["Re", "Ra", "Re_tau", "Ma"];
  const items: { k: string; v: string }[] = [];
  for (const k of ordered) {
    if (k in excerpt && excerpt[k] !== null && excerpt[k] !== undefined) {
      items.push({ k, v: String(excerpt[k]) });
    }
  }
  if (items.length === 0) return <span className="font-mono text-[11px] text-surface-500">—</span>;
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

function groupByLocalDate(
  runs: RunSummaryEntry[],
): { date: string; items: RunSummaryEntry[] }[] {
  // Group by local-tz date for the user's mental model — "today's runs"
  // means runs that happened on today's calendar locally, not UTC.
  const groups = new Map<string, RunSummaryEntry[]>();
  for (const r of runs) {
    const d = new Date(r.started_at);
    const key = isNaN(d.getTime())
      ? "(unparseable timestamp)"
      : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const bucket = groups.get(key) ?? [];
    bucket.push(r);
    groups.set(key, bucket);
  }
  // Insertion order tracks first-occurrence order in the newest-first
  // input, so the iterator is already newest-date-first.
  return Array.from(groups.entries()).map(([date, items]) => ({ date, items }));
}

function formatTime(iso: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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
