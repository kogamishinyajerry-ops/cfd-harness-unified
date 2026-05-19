/**
 * V4 · KPI strip · 96px · per UI-SPEC §2.4 · Phase B real backend wiring.
 *
 * Numbers (≥28px tabular-num semibold) bind per-mode to real backend data:
 *   - geometry: WorkbenchBasics.patches/materials/dimension/characteristic_length
 *   - mesh:     MeshMetrics.densities · GCI · QC band
 *   - physics:  basics.materials.length · solver.steady_state · BC count
 *   - boundary: patch counts by role
 *   - solver:   RunDetail.residuals + key_quantities + duration
 *   - post:     RunDetail.key_quantities + success
 *   - doe:      stub (no DOE backend yet)
 *
 * Graceful: when caseId is null OR backend missing, falls back to em-dash
 * placeholder so the visual frame is preserved.
 */
import { useV4WorkbenchContext } from "../hooks/useV4WorkbenchContext";
import {
  convergenceGaugeFromSeries,
  useResidualSeries,
} from "../hooks/useResidualSeries";
import type { V4Context } from "../hooks/useV4WorkbenchContext";
import type { Patch } from "@/types/workbench_basics";
import type { ResidualSeriesPayload } from "@/types/residual_series";
import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

interface KpiChip {
  value: string;
  label: string;
  unit?: string;
  delta?: string;
  deltaTone?: "healthy" | "warn" | "crit";
}

const DASH: KpiChip[] = [
  { value: "—", label: "等待算例" },
  { value: "—", label: "等待算例" },
  { value: "—", label: "等待算例" },
  { value: "—", label: "等待算例" },
];

function fmt(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1000) return n.toExponential(2);
  return Number(n).toFixed(digits);
}

function fmtSci(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toExponential(2);
}

/** Count patches by role (handles unknown roles as "other"). */
function countPatchesByRole(patches: Patch[] | undefined): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const p of patches ?? []) {
    const k = String(p.role);
    counts[k] = (counts[k] ?? 0) + 1;
  }
  return counts;
}

/** Numeric-only filter for key_quantities · drops arrays/strings/null
 *  so a vector like `u_centerline: [0.0063, 0.0915, ...]` never lands
 *  in a 30px tabular-num KPI chip (Codex R3 Typography finding). */
function scalarKqEntries(
  kq: Record<string, unknown> | null | undefined,
): [string, number][] {
  if (!kq) return [];
  return Object.entries(kq).filter(
    ([, v]) => typeof v === "number" && Number.isFinite(v),
  ) as [string, number][];
}

function latestResidual(
  payload: ResidualSeriesPayload | null | undefined,
  name: string,
): number | null {
  const pts = payload?.series?.[name];
  if (!pts || pts.length === 0) return null;
  const last = pts[pts.length - 1];
  return Number.isFinite(last?.y) ? last.y : null;
}

function chipsFor(
  step: V4PipelineStepId,
  ctx: V4Context,
  residualPayload: ResidualSeriesPayload | null,
): KpiChip[] {
  // No case selected · empty-state placeholder
  if (!ctx.caseId) return DASH;

  const basics = ctx.basics;
  const mesh = ctx.meshMetrics;
  const detail = ctx.runDetail;
  // Post mode prefers the latest *successful* run so a failed-tail
  // history doesn't show empty residuals / arrays as KPIs.
  // Matches ModeRendererPost behaviour for consistency.
  const postDetail = ctx.successfulRunDetail ?? ctx.runDetail;

  switch (step) {
    case "import": {
      const dim = basics?.dimension;
      const cl = basics?.geometry?.characteristic_length;
      return [
        { value: String(dim ?? "—"), label: "维度", unit: "D" },
        {
          value: cl?.value != null ? fmt(cl.value, 3) : "—",
          label: cl?.name ?? "特征长度",
          unit: cl?.unit,
        },
        {
          value: String(basics?.patches?.length ?? "—"),
          label: "边界面",
        },
        {
          value: ctx.latestRun ? String(ctx.latestRun.exit_code) : "—",
          label: "最近退出码",
        },
      ];
    }

    case "geometry": {
      const cl = basics?.geometry?.characteristic_length;
      return [
        { value: String(basics?.patches?.length ?? "—"), label: "边界面" },
        { value: String(basics?.dimension ?? "—"), label: "维度", unit: "D" },
        {
          value: cl?.value != null ? fmt(cl.value, 3) : "—",
          label: cl?.name ?? "特征长度",
          unit: cl?.unit,
        },
        {
          value: String(basics?.materials?.length ?? "—"),
          label: "材料",
        },
      ];
    }

    case "mesh": {
      const lastDensity = mesh?.densities?.[mesh.densities.length - 1];
      const gci = mesh?.gci?.gci_32_pct;
      const pObs = mesh?.gci?.p_obs;
      return [
        {
          value: lastDensity?.n_cells_1d
            ? String(lastDensity.n_cells_1d)
            : "—",
          label: "最细网格", unit: "n",
        },
        {
          value: String(mesh?.densities?.length ?? "—"),
          label: "网格层级",
        },
        {
          value: gci != null ? fmt(gci, 3) : "—",
          label: "GCI₃₂", unit: "%",
        },
        {
          value: pObs != null ? fmt(pObs, 2) : "—",
          label: "p_obs",
        },
      ];
    }

    case "physics": {
      const solverName = basics?.solver?.display_zh ?? basics?.solver?.name ?? "—";
      return [
        { value: String(basics?.materials?.length ?? "—"), label: "材料" },
        {
          value: String(basics?.boundary_conditions?.length ?? "—"),
          label: "边界条件",
        },
        {
          value: basics?.solver?.steady_state ? "稳态" : "瞬态",
          label: "工况",
        },
        {
          value: solverName.length > 8 ? solverName.slice(0, 8) + "…" : solverName,
          label: "求解器",
        },
      ];
    }

    case "boundary": {
      const counts = countPatchesByRole(basics?.patches);
      return [
        { value: String(counts.inlet ?? 0), label: "入口" },
        { value: String(counts.outlet ?? 0), label: "出口" },
        {
          value: String((counts.wall ?? 0) + (counts.moving_wall ?? 0)),
          label: "壁面",
        },
        {
          value: String(
            (counts.symmetry ?? 0) +
              (counts.cyclic ?? 0) +
              (counts.periodic ?? 0) +
              (counts.empty ?? 0),
          ),
          label: "其它",
        },
      ];
    }

    case "solver": {
      const kq = detail?.key_quantities as
        | Record<string, unknown>
        | null
        | undefined;
      const res = detail?.residuals as Record<string, number> | undefined;
      const resP =
        latestResidual(residualPayload, "p") ?? res?.p ?? res?.U ?? null;
      const success = detail?.success;
      const gauge = convergenceGaugeFromSeries(residualPayload);
      const progress = residualPayload
        ? Math.round(gauge.value)
        : success
          ? 100
          : detail
            ? 65
            : 0;
      const source = residualPayload?.source
        ? residualPayload.source.toUpperCase()
        : detail
          ? "RUN"
          : "—";
      // Scalar-only · arrays like u_centerline never reach a KPI chip.
      const kqEntries = scalarKqEntries(kq).slice(0, 2);
      return [
        {
          value: residualPayload
            ? String(residualPayload.sample_count)
            : ctx.latestRun?.duration_s != null
              ? fmt(ctx.latestRun.duration_s, 1)
              : "—",
          label: residualPayload ? "迭代样本" : "运行时长",
          unit: residualPayload ? undefined : "s",
        },
        {
          value: fmtSci(resP),
          label: "残差 p",
        },
        ...(residualPayload
          ? [
              {
                value: String(progress),
                label: gauge.worst ? `收敛 · ${gauge.worst}` : "收敛进度",
                unit: "%",
                delta: gauge.achieved ? "已达标" : "进行中",
                deltaTone: gauge.achieved ? "healthy" : "warn",
              } as KpiChip,
            ]
          : kqEntries.length > 0
          ? kqEntries.map<KpiChip>(([k, v]) => ({
              value: fmt(v, 3),
              label: k,
            }))
          : [{ value: "—", label: "key_quantity" } as KpiChip]),
        {
          value: source,
          label: "残差来源",
        },
      ];
    }

    case "post": {
      // Post tier prefers successful-run detail (see ModeRendererPost).
      const kq = postDetail?.key_quantities as
        | Record<string, unknown>
        | null
        | undefined;
      const verdict = postDetail?.success === true ? "通过" : postDetail ? "失败" : "—";
      const verdictTone =
        postDetail?.success === true
          ? "healthy"
          : postDetail
            ? "crit"
            : undefined;
      const kqEntries = scalarKqEntries(kq).slice(0, 3);
      const chips: KpiChip[] = kqEntries.map<KpiChip>(([k, v]) => ({
        value: fmt(v, 3),
        label: k,
      }));
      while (chips.length < 3) chips.push({ value: "—", label: "—" });
      chips.push({
        value: verdict,
        label: "对比基准",
        deltaTone: verdictTone,
      });
      return chips;
    }

    case "doe": {
      // No DOE backend yet · keep stub values but reference real case
      return [
        { value: "—", label: "样本", delta: "DOE 待接入", deltaTone: "warn" },
        { value: "—", label: "best 压力" },
        { value: "—", label: "best 温度" },
        { value: "—", label: "best 流量" },
      ];
    }
  }
}

interface KpiStripV4Props {
  activeStep: V4PipelineStepId;
  caseId?: string | null;
}

export function KpiStripV4({ activeStep, caseId = null }: KpiStripV4Props) {
  const ctx = useV4WorkbenchContext(caseId);
  const residuals = useResidualSeries(activeStep === "solver" ? caseId : null);
  const chips = chipsFor(activeStep, ctx, residuals.data);

  return (
    <div
      className="flex h-24 shrink-0 items-center gap-6 border-t border-v4-border bg-v4-shell px-6"
      data-testid="kpistrip-v4"
      data-active-step={activeStep}
      data-backend-connected={ctx.hasBackend ? "true" : "false"}
    >
      {chips.map((chip, i) => (
        <div
          key={i}
          className="flex min-w-[110px] flex-col justify-center"
          data-testid={`kpistrip-v4-chip-${i}`}
        >
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-[30px] font-semibold tabular-nums leading-none text-v4-textPrimary">
              {chip.value}
            </span>
            {chip.unit && (
              <span className="text-[11px] text-v4-textTertiary">
                {chip.unit}
              </span>
            )}
            {chip.delta && (
              <span
                className={[
                  "ml-1 text-[11px] font-medium",
                  chip.deltaTone === "healthy" && "text-v4-healthy",
                  chip.deltaTone === "warn" && "text-v4-warn",
                  chip.deltaTone === "crit" && "text-v4-crit",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {chip.delta}
              </span>
            )}
          </div>
          <div className="mt-1.5 truncate text-[11px] text-v4-textSecondary">
            {chip.label}
          </div>
        </div>
      ))}
    </div>
  );
}
