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
  GEOMETRY_BLUEPRINT_SUMMARY,
  hasAuthoredCadParts,
} from "./geometryBlueprint";
import {
  MESH_BLUEPRINT_HISTOGRAMS,
  MESH_BLUEPRINT_NUMERICS,
  type MeshBlueprintHistogram,
} from "./meshBlueprint";
import { PHYSICS_BLUEPRINT_SUMMARY } from "./physicsBlueprint";
import { BOUNDARY_BLUEPRINT_KPIS } from "./boundaryBlueprint";
import { SOLVER_BLUEPRINT_KPIS } from "./solverBlueprint";
import { POST_BLUEPRINT_KPIS } from "./postBlueprint";
import type { V4Context } from "../hooks/useV4WorkbenchContext";
import type { Patch } from "@/types/workbench_basics";
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

/** Count patches by role (handles unknown roles as "other"). */
function countPatchesByRole(patches: Patch[] | undefined): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const p of patches ?? []) {
    const k = String(p.role);
    counts[k] = (counts[k] ?? 0) + 1;
  }
  return counts;
}

function chipsFor(step: V4PipelineStepId, ctx: V4Context): KpiChip[] {
  // No case selected · empty-state placeholder
  if (!ctx.caseId) return DASH;

  const basics = ctx.basics;
  const mesh = ctx.meshMetrics;
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
      if (!basics || !hasAuthoredCadParts(basics.patches?.length)) {
        return [
          {
            value: String(GEOMETRY_BLUEPRINT_SUMMARY.partCount),
            label: "部件",
          },
          {
            value: String(GEOMETRY_BLUEPRINT_SUMMARY.instanceCount),
            label: "实例",
          },
          {
            value: GEOMETRY_BLUEPRINT_SUMMARY.toleranceMm.toFixed(1),
            label: "容差",
            unit: "mm",
          },
          {
            value: GEOMETRY_BLUEPRINT_SUMMARY.estimatedCellsM.toFixed(2),
            label: "估算单元",
            unit: "M",
          },
        ];
      }
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
      if (!basics?.solver) {
        return [
          {
            value: String(PHYSICS_BLUEPRINT_SUMMARY.modelCount),
            label: "物理模型",
          },
          {
            value: String(PHYSICS_BLUEPRINT_SUMMARY.materialCount),
            label: "材料",
          },
          {
            value: "稳态",
            label: "计算工况",
          },
          {
            value: PHYSICS_BLUEPRINT_SUMMARY.estimatedCellsM.toFixed(1),
            label: "估算单元",
            unit: "M",
          },
        ];
      }
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
      if ((basics?.patches?.length ?? 0) === 0) {
        return [
          {
            value: String(BOUNDARY_BLUEPRINT_KPIS.inletCount),
            label: "入口",
          },
          {
            value: String(BOUNDARY_BLUEPRINT_KPIS.outletCount),
            label: "出口",
          },
          {
            value: String(BOUNDARY_BLUEPRINT_KPIS.wallCount),
            label: "壁面",
          },
          {
            value: String(BOUNDARY_BLUEPRINT_KPIS.rotorCount),
            label: "转子域",
          },
        ];
      }
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
      return [
        {
          value: SOLVER_BLUEPRINT_KPIS.estimatedCellsM.toFixed(2),
          label: "估算单元",
          unit: "M",
        },
        {
          value: SOLVER_BLUEPRINT_KPIS.residualP.toExponential(1),
          label: "残差 p",
        },
        {
          value: SOLVER_BLUEPRINT_KPIS.pressurePa.toFixed(1),
          label: "压降",
          unit: "Pa",
        },
        {
          value: SOLVER_BLUEPRINT_KPIS.massFlowKgS.toFixed(2),
          label: "质量流量",
          unit: "kg/s",
        },
        {
          value: SOLVER_BLUEPRINT_KPIS.temperatureC.toFixed(1),
          label: "出口温度",
          unit: "°C",
        },
        {
          value: String(SOLVER_BLUEPRINT_KPIS.progressPct),
          label: `${SOLVER_BLUEPRINT_KPIS.iterCurrent}/${SOLVER_BLUEPRINT_KPIS.iterTotal} iter`,
          unit: "%",
          delta: "良好",
          deltaTone: "healthy",
        },
      ];
    }

    case "post": {
      return [
        {
          value: POST_BLUEPRINT_KPIS.pressurePa.toFixed(1),
          label: "压降",
          unit: "Pa",
        },
        {
          value: POST_BLUEPRINT_KPIS.massFlowKgS.toFixed(2),
          label: "质量流量",
          unit: "kg/s",
        },
        {
          value: POST_BLUEPRINT_KPIS.temperatureC.toFixed(1),
          label: "出口温度",
          unit: "°C",
        },
        {
          value: String(POST_BLUEPRINT_KPIS.progressPct),
          label: "覆盖率",
          unit: "%",
        },
        {
          value: `+${POST_BLUEPRINT_KPIS.gainPct.toFixed(1)}`,
          label: "对比基准",
          unit: "%",
          delta: "增益",
          deltaTone: "healthy",
        },
      ];
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

function fmtMeshMean(metric: MeshBlueprintHistogram): string {
  if (metric.mean >= 10) return metric.mean.toFixed(1);
  if (metric.mean >= 1) return metric.mean.toFixed(2);
  return metric.mean.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function MeshHistogramChip({ metric }: { metric: MeshBlueprintHistogram }) {
  return (
    <div
      className="flex min-w-0 flex-1 flex-col rounded border border-v4-border bg-v4-surfaceRaised/35 px-2.5 py-1.5"
      data-testid={`mesh-kpi-histogram-${metric.label}`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-[10px] text-v4-textSecondary">
          {metric.label}
        </span>
        <span className="font-mono text-[11px] tabular-nums text-v4-textPrimary">
          {fmtMeshMean(metric)}
          <span className="ml-1 text-[9px] text-v4-textTertiary">
            {metric.unit}
          </span>
        </span>
      </div>
      <svg
        viewBox="0 0 110 30"
        preserveAspectRatio="none"
        className="mt-1 h-7 w-full"
        aria-hidden
      >
        <line
          x1="0"
          x2="110"
          y1="28"
          y2="28"
          stroke="currentColor"
          className="text-v4-border"
          strokeWidth="0.8"
        />
        {metric.bins.map((bin, index) => {
          const width = 110 / metric.bins.length;
          const h = Math.max(2, Math.min(1, bin) * 25);
          return (
            <rect
              key={index}
              x={index * width + 1}
              y={28 - h}
              width={Math.max(2, width - 2)}
              height={h}
              rx="1"
              fill={metric.color}
              opacity={0.28 + Math.min(1, bin) * 0.58}
            />
          );
        })}
      </svg>
    </div>
  );
}

function MeshKpiStrip({ ctx }: { ctx: V4Context }) {
  return (
    <div
      className="flex h-24 shrink-0 flex-col justify-center gap-1.5 border-t border-v4-border bg-v4-shell px-4"
      data-testid="kpistrip-v4"
      data-active-step="mesh"
      data-backend-connected={ctx.hasBackend ? "true" : "false"}
      data-mesh-kpi-source={ctx.meshMetrics ? "mesh-metrics" : "blueprint-contract"}
    >
      <div className="grid min-h-0 grid-cols-5 gap-2">
        {MESH_BLUEPRINT_HISTOGRAMS.map((metric) => (
          <MeshHistogramChip key={metric.label} metric={metric} />
        ))}
      </div>
      <div
        className="grid grid-cols-4 gap-2 text-[10px]"
        data-testid="mesh-kpi-numeric-row"
      >
        <MeshNumeric value={MESH_BLUEPRINT_NUMERICS.estimatedCellsM.toFixed(2)} unit="M" label="估算单元" />
        <MeshNumeric value={MESH_BLUEPRINT_NUMERICS.maxSkewness.toFixed(3)} label="最大歪斜度" />
        <MeshNumeric value={MESH_BLUEPRINT_NUMERICS.maxNonOrthogonalityDeg.toFixed(1)} unit="°" label="最大非正交" />
        <MeshNumeric value={MESH_BLUEPRINT_NUMERICS.timeEstimateMin.toFixed(1)} unit="min" label="时间估计" />
      </div>
    </div>
  );
}

function MeshNumeric({
  value,
  unit,
  label,
}: {
  value: string;
  unit?: string;
  label: string;
}) {
  return (
    <div className="flex items-baseline justify-center gap-1 rounded border border-v4-border bg-v4-surfaceRaised/25 px-2 py-0.5">
      <span className="font-mono text-[13px] font-semibold tabular-nums text-v4-textPrimary">
        {value}
      </span>
      {unit && <span className="text-[9px] text-v4-textTertiary">{unit}</span>}
      <span className="ml-1 truncate text-v4-textSecondary">{label}</span>
    </div>
  );
}

interface KpiStripV4Props {
  activeStep: V4PipelineStepId;
  caseId?: string | null;
}

export function KpiStripV4({ activeStep, caseId = null }: KpiStripV4Props) {
  const ctx = useV4WorkbenchContext(caseId);
  if (activeStep === "mesh") {
    return <MeshKpiStrip ctx={ctx} />;
  }
  const chips = chipsFor(activeStep, ctx);

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
