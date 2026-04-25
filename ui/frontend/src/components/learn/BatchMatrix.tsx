// BatchMatrix · Stage 5 GoldOps MVP — system-pulse view of all 10 cases
// × 4 mesh densities. Per Codex industrial-workbench meeting 2026-04-25
// + roadmap S5 (workbench_rollout_roadmap.md).
//
// Data: GET /api/batch-matrix returns 40 cells of (case_id, density_id,
// verdict, deviation_pct). Composed server-side from existing
// build_validation_report per (case, density) pair.
//
// UX rules:
// - Cells are clickable → navigate to /learn/cases/{id}?run={density_id}
//   so the student can drill from the system view into a specific
//   measurement.
// - Color encodes verdict (green PASS / amber HAZARD / red FAIL /
//   gray UNKNOWN). Magnitude of |deviation_pct| modulates saturation
//   so the user can see "barely PASS" vs "deeply PASS" at a glance.
// - Convergence pattern reads left-to-right within each row — F F H H
//   is "got there with refinement" while F F F F is "still not there".

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type {
  BatchMatrix as BatchMatrixData,
  MatrixCell,
  MatrixRow,
} from "@/types/batch_matrix";
import type { ContractStatus } from "@/types/validation";

const VERDICT_BG: Record<ContractStatus, string> = {
  PASS: "bg-emerald-700",
  HAZARD: "bg-amber-600",
  FAIL: "bg-rose-700",
  UNKNOWN: "bg-surface-700",
};

const VERDICT_TEXT: Record<ContractStatus, string> = {
  PASS: "text-emerald-100",
  HAZARD: "text-amber-100",
  FAIL: "text-rose-100",
  UNKNOWN: "text-surface-300",
};

const VERDICT_GLYPH: Record<ContractStatus, string> = {
  PASS: "✓",
  HAZARD: "◐",
  FAIL: "✗",
  UNKNOWN: "?",
};

export function BatchMatrix() {
  const { data, error, isLoading } = useQuery<BatchMatrixData>({
    queryKey: ["batch-matrix"],
    queryFn: () => api.getBatchMatrix(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="h-[360px] animate-pulse rounded-md border border-surface-800 bg-surface-900/40" />
    );
  }
  if (error || !data) {
    return (
      <div className="rounded-md border border-amber-700/60 bg-amber-950/30 p-4 text-[12px] text-amber-200">
        ⚠ batch matrix 加载失败：{error instanceof Error ? error.message : "unknown"}
      </div>
    );
  }

  return (
    <section className="rounded-lg border border-surface-800 bg-surface-950/40 p-5">
      <Header data={data} />
      <Grid data={data} />
      <Footer data={data} />
    </section>
  );
}

// --- Header --------------------------------------------------------------

function Header({ data }: { data: BatchMatrixData }) {
  const { counts, n_cases, n_densities } = data;
  return (
    <div className="mb-4">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <h2 className="card-title">系统脉搏 · 10 case × 4 mesh density</h2>
          <p className="mt-1 text-[12px] text-surface-500">
            harness 在 {n_cases * n_densities} 个 (案例 × 网格) cell 上跑过
            comparator；下面是当前所有 fixture 对照黄金标准的 verdict 分布。
          </p>
        </div>
        <span className="mono text-[10px] uppercase tracking-wider text-surface-600">
          batch-matrix · v1
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
        <CountChip label="PASS" n={counts.PASS} verdict="PASS" />
        <CountChip label="HAZARD" n={counts.HAZARD} verdict="HAZARD" />
        <CountChip label="FAIL" n={counts.FAIL} verdict="FAIL" />
        <CountChip label="UNKNOWN" n={counts.UNKNOWN} verdict="UNKNOWN" />
        <span className="ml-auto mono text-[10px] text-surface-600">
          {counts.total} cells · {n_cases} cases × {n_densities} densities
        </span>
      </div>
    </div>
  );
}

function CountChip({ label, n, verdict }: { label: string; n: number; verdict: ContractStatus }) {
  if (n === 0) return null;
  return (
    <span
      className={`mono rounded-sm border border-transparent px-1.5 py-0.5 ${VERDICT_BG[verdict]} ${VERDICT_TEXT[verdict]}`}
    >
      {VERDICT_GLYPH[verdict]} {n} {label}
    </span>
  );
}

// --- Grid ---------------------------------------------------------------

function Grid({ data }: { data: BatchMatrixData }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-y-1 text-[12px]">
        <thead>
          <tr>
            <th className="sticky left-0 bg-surface-950/40 px-2 pb-2 text-left font-normal text-surface-500">
              case
            </th>
            {data.densities.map((d) => (
              <th
                key={d}
                className="px-1 pb-2 text-center font-normal text-surface-500"
              >
                <span className="mono text-[11px] text-surface-400">{d.replace("mesh_", "n=")}</span>
              </th>
            ))}
            <th className="px-2 pb-2 text-left font-normal text-surface-500">
              row trend
            </th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <Row key={row.case_id} row={row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ row }: { row: MatrixRow }) {
  const trend = describeTrend(row.cells);
  return (
    <tr>
      <td className="sticky left-0 max-w-[220px] bg-surface-950/40 py-1 pl-2 pr-3 align-middle">
        <Link
          to={`/learn/cases/${encodeURIComponent(row.case_id)}`}
          className="block text-surface-200 hover:text-sky-300"
        >
          <span className="truncate">{row.display_name_zh ?? row.display_name}</span>
          {!row.has_workbench_basics && (
            <span className="ml-1 mono text-[10px] text-surface-600">(no workbench)</span>
          )}
        </Link>
        {row.canonical_ref && (
          <p className="mt-0.5 text-[10px] text-surface-500">{row.canonical_ref}</p>
        )}
      </td>
      {row.cells.map((cell) => (
        <td key={cell.density_id} className="px-1 align-middle">
          <Cell cell={cell} caseId={row.case_id} />
        </td>
      ))}
      <td className="py-1 pl-3 align-middle">
        <span className="mono text-[11px] text-surface-400">{trend}</span>
      </td>
    </tr>
  );
}

function Cell({ cell, caseId }: { cell: MatrixCell; caseId: string }) {
  const dev = cell.deviation_pct;
  const devText =
    dev != null && Number.isFinite(dev)
      ? `${dev >= 0 ? "+" : ""}${dev.toFixed(1)}%`
      : "—";
  const tooltip = `${cell.density_id} · ${cell.verdict} · dev ${devText}`;

  return (
    <Link
      to={`/learn/cases/${encodeURIComponent(caseId)}?tab=mesh&run=${encodeURIComponent(cell.density_id)}`}
      title={tooltip}
      className={`mono mx-auto flex h-9 w-full max-w-[80px] items-center justify-center rounded border border-transparent transition-opacity hover:opacity-90 ${VERDICT_BG[cell.verdict]} ${VERDICT_TEXT[cell.verdict]}`}
    >
      <span className="text-[10px] leading-none">
        <span className="font-medium">{VERDICT_GLYPH[cell.verdict]}</span>
        <span className="ml-1">{devText}</span>
      </span>
    </Link>
  );
}

// --- Trend label --------------------------------------------------------
// "F F H H" → "FAIL → HAZARD (refinement helped)". Pattern recognition
// is the value-add over the raw 4 cells.

function describeTrend(cells: MatrixCell[]): string {
  if (cells.length === 0) return "—";
  const first = cells[0].verdict;
  const last = cells[cells.length - 1].verdict;
  const rank: Record<ContractStatus, number> = {
    FAIL: 0,
    UNKNOWN: 1,
    HAZARD: 2,
    PASS: 3,
  };
  const delta = rank[last] - rank[first];
  if (delta > 0) return `↗ ${first} → ${last}`;
  if (delta < 0) return `↘ ${first} → ${last}`;
  return `→ all ${first}`;
}

// --- Footer -------------------------------------------------------------

function Footer({ data }: { data: BatchMatrixData }) {
  const monotonic = data.rows.filter((r) => {
    const verdicts = r.cells.map((c) => c.verdict);
    const rank: Record<ContractStatus, number> = {
      FAIL: 0,
      UNKNOWN: 1,
      HAZARD: 2,
      PASS: 3,
    };
    for (let i = 1; i < verdicts.length; i++) {
      if (rank[verdicts[i]] < rank[verdicts[i - 1]]) return false;
    }
    return rank[verdicts[verdicts.length - 1]] > rank[verdicts[0]];
  }).length;

  return (
    <div className="mt-4 border-t border-surface-800 pt-3 text-[11px] leading-relaxed text-surface-500">
      <p>
        <strong className="text-surface-400">读图守则：</strong>
        每行从左到右是 mesh_20 / mesh_40 / mesh_80 / mesh_160 的 verdict。
        随网格加密，单调改善的行 ({monotonic}/{data.rows.length}) 表明 case 是
        网格收敛敏感 — 这正是 CFD 验证想看的形态。
        点 cell 跳到该 case 的对应 mesh 报告。
      </p>
    </div>
  );
}
