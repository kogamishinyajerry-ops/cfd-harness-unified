import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { RunDetail } from "@/types/run_history";
import { FAILURE_CATEGORY_LABEL_ZH } from "@/types/run_history";

// Workbench 60-day extension · 2026-04-26 — /workbench/case/:caseId/compare?a=...&b=...
//
// Side-by-side comparison of two runs of the same case. Read-only; reads
// from /api/cases/:caseId/run-history/:runId twice in parallel. The natural
// follow-up to RunDetailPage: "I just ran Re=400, how does that compare to
// my earlier Re=100?" Picks up the run IDs from the query string so the
// surface is bookmarkable / shareable.

export function RunComparePage() {
  const { caseId = "" } = useParams<{ caseId: string }>();
  const [params] = useSearchParams();
  const aId = params.get("a") ?? "";
  const bId = params.get("b") ?? "";

  const aQuery = useQuery({
    queryKey: ["workbenchRunDetail", caseId, aId],
    queryFn: () => api.getRunDetail(caseId, aId),
    enabled: Boolean(caseId) && Boolean(aId),
  });
  const bQuery = useQuery({
    queryKey: ["workbenchRunDetail", caseId, bId],
    queryFn: () => api.getRunDetail(caseId, bId),
    enabled: Boolean(caseId) && Boolean(bId),
  });

  if (!caseId || !aId || !bId) {
    return (
      <Section>
        <p className="text-sm text-contract-fail">
          missing path/query params — expected /workbench/case/:caseId/compare?a=runIdA&amp;b=runIdB
        </p>
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/runs`}
          className="mt-2 inline-block text-sm text-emerald-400 hover:text-emerald-300"
        >
          ← Back to run history
        </Link>
      </Section>
    );
  }
  if (aQuery.isLoading || bQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading both runs…</p></Section>;
  }
  for (const q of [aQuery, bQuery]) {
    if (q.isError || !q.data) {
      const msg =
        q.error instanceof ApiError ? `${q.error.status}: ${q.error.message}` : String(q.error);
      return (
        <Section>
          <p className="text-sm text-contract-fail">Failed to load one of the runs: {msg}</p>
        </Section>
      );
    }
  }

  const a = aQuery.data!;
  const b = bQuery.data!;

  return (
    <Section>
      <header className="mb-6">
        <div className="text-[11px] uppercase tracking-wider text-surface-500">
          <Link to="/learn" className="hover:text-surface-300">Learn</Link>
          <span className="mx-1.5">/</span>
          <Link to={`/learn/cases/${caseId}`} className="hover:text-surface-300">{caseId}</Link>
          <span className="mx-1.5">/</span>
          <Link
            to={`/workbench/case/${encodeURIComponent(caseId)}/runs`}
            className="hover:text-surface-300"
          >
            runs
          </Link>
          <span className="mx-1.5">/</span>
          <span>compare</span>
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-surface-100">Compare runs · {caseId}</h1>
        <p className="mt-1 text-[12px] text-surface-400">
          Two-up overlay of two runs from <code>reports/{caseId}/runs/</code>.
          A is on the left, B on the right; numeric deltas are B − A.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4">
        <RunHeaderCard label="A" run={a} />
        <RunHeaderCard label="B" run={b} />
      </div>

      <Block title="Task spec — diff">
        <TaskSpecDiff a={a.task_spec} b={b.task_spec} />
      </Block>

      <Block title="Key quantities — overlay (B − A)">
        <KeyQuantitiesOverlay a={a.key_quantities} b={b.key_quantities} />
      </Block>

      <Block title="Residuals — overlay (ratio B / A)">
        <ResidualsOverlay a={a.residuals} b={b.residuals} />
      </Block>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/run/${encodeURIComponent(aId)}`}
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
        >
          ← Run A detail
        </Link>
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/run/${encodeURIComponent(bId)}`}
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
        >
          Run B detail →
        </Link>
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/runs`}
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
        >
          Back to run history
        </Link>
      </div>
    </Section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-6xl px-8 py-8">{children}</section>;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-6 rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <h3 className="mb-2 text-[11px] uppercase tracking-wider text-surface-400">{title}</h3>
      {children}
    </div>
  );
}

function RunHeaderCard({ label, run }: { label: string; run: RunDetail }) {
  const tone = run.success
    ? "border-contract-pass/40 bg-contract-pass/5 text-contract-pass"
    : "border-contract-fail/40 bg-contract-fail/5 text-contract-fail";
  return (
    <div className={`rounded-md border p-4 ${tone}`}>
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wider opacity-70">run {label}</span>
        <span className="font-mono text-[10px] opacity-70">{run.run_id}</span>
      </div>
      <div className="mt-1 text-base font-semibold">
        {run.success ? "PASS" : "FAIL"} · exit_code={run.exit_code} · {run.duration_s.toFixed(1)}s
      </div>
      <div className="mt-1 text-[12px] opacity-90">{run.verdict_summary}</div>
      {!run.success && run.failure_category && (
        <div className="mt-2 text-[11px] opacity-80">
          category: <code className="font-mono">{run.failure_category}</code>
          <span className="ml-2">{FAILURE_CATEGORY_LABEL_ZH[run.failure_category]}</span>
        </div>
      )}
    </div>
  );
}

function TaskSpecDiff({
  a,
  b,
}: {
  a: Record<string, unknown>;
  b: Record<string, unknown>;
}) {
  const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort();
  const rows = keys
    .map((k) => ({ k, a: a[k], b: b[k] }))
    .filter((r) => !shallowEqual(r.a, r.b));
  if (rows.length === 0) {
    return (
      <p className="text-xs text-surface-500">
        — no differences in task spec; both runs used the same parameters —
      </p>
    );
  }
  return (
    <table className="w-full border-collapse text-[12px]">
      <thead>
        <tr className="border-b border-surface-800 text-[10px] uppercase tracking-wider text-surface-500">
          <th className="px-2 py-1 text-left">key</th>
          <th className="px-2 py-1 text-left">A</th>
          <th className="px-2 py-1 text-left">B</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ k, a: va, b: vb }) => (
          <tr key={k} className="border-b border-surface-900">
            <td className="px-2 py-1 font-mono text-surface-400">{k}</td>
            <td className="px-2 py-1 font-mono text-surface-200">{display(va)}</td>
            <td className="px-2 py-1 font-mono text-emerald-300">{display(vb)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function KeyQuantitiesOverlay({
  a,
  b,
}: {
  a: Record<string, unknown>;
  b: Record<string, unknown>;
}) {
  const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort();
  if (keys.length === 0) {
    return <p className="text-xs text-surface-500">— neither run extracted key quantities —</p>;
  }
  return (
    <table className="w-full border-collapse text-[12px]">
      <thead>
        <tr className="border-b border-surface-800 text-[10px] uppercase tracking-wider text-surface-500">
          <th className="px-2 py-1 text-left">quantity</th>
          <th className="px-2 py-1 text-right">A</th>
          <th className="px-2 py-1 text-right">B</th>
          <th className="px-2 py-1 text-right">B − A</th>
          <th className="px-2 py-1 text-right">rel%</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((k) => {
          const va = a[k];
          const vb = b[k];
          const numA = pickNumber(va);
          const numB = pickNumber(vb);
          const delta = numA !== null && numB !== null ? numB - numA : null;
          const rel = delta !== null && numA !== null && numA !== 0 ? (delta / numA) * 100 : null;
          return (
            <tr key={k} className="border-b border-surface-900">
              <td className="px-2 py-1 font-mono text-surface-400">{k}</td>
              <td className="px-2 py-1 text-right font-mono text-surface-200">{display(va)}</td>
              <td className="px-2 py-1 text-right font-mono text-surface-200">{display(vb)}</td>
              <td className="px-2 py-1 text-right font-mono text-surface-300">
                {delta === null ? "—" : signed(delta)}
              </td>
              <td
                className={`px-2 py-1 text-right font-mono ${
                  rel === null
                    ? "text-surface-500"
                    : Math.abs(rel) < 1
                      ? "text-contract-pass"
                      : Math.abs(rel) < 10
                        ? "text-amber-300"
                        : "text-contract-fail"
                }`}
              >
                {rel === null ? "—" : `${signed(rel, 2)}%`}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function ResidualsOverlay({
  a,
  b,
}: {
  a: Record<string, number>;
  b: Record<string, number>;
}) {
  const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort();
  if (keys.length === 0) {
    return <p className="text-xs text-surface-500">— neither run reported residuals —</p>;
  }
  return (
    <table className="w-full border-collapse text-[12px]">
      <thead>
        <tr className="border-b border-surface-800 text-[10px] uppercase tracking-wider text-surface-500">
          <th className="px-2 py-1 text-left">field</th>
          <th className="px-2 py-1 text-right">A</th>
          <th className="px-2 py-1 text-right">B</th>
          <th className="px-2 py-1 text-right">B / A</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((k) => {
          const va = typeof a[k] === "number" ? a[k] : null;
          const vb = typeof b[k] === "number" ? b[k] : null;
          const ratio = va !== null && vb !== null && va !== 0 ? vb / va : null;
          return (
            <tr key={k} className="border-b border-surface-900">
              <td className="px-2 py-1 font-mono text-surface-400">{k}</td>
              <td className="px-2 py-1 text-right font-mono text-surface-200">
                {va === null ? "—" : va.toExponential(2)}
              </td>
              <td className="px-2 py-1 text-right font-mono text-surface-200">
                {vb === null ? "—" : vb.toExponential(2)}
              </td>
              <td className="px-2 py-1 text-right font-mono text-surface-300">
                {ratio === null ? "—" : ratio.toExponential(2)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function display(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toString();
  if (typeof v === "string") return v;
  if (Array.isArray(v)) {
    if (v.every((x) => typeof x === "number")) {
      const nums = v as number[];
      const min = Math.min(...nums);
      const max = Math.max(...nums);
      return `[${nums.length}] ${min.toExponential(2)} … ${max.toExponential(2)}`;
    }
    return `[${v.length} items]`;
  }
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function pickNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  return null;
}

function signed(n: number, digits = 4): string {
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}`;
}

function shallowEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (typeof a === "number" && typeof b === "number") return a === b;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((x, i) => shallowEqual(x, b[i]));
  }
  return JSON.stringify(a) === JSON.stringify(b);
}
