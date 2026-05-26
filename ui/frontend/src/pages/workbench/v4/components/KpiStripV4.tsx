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
 *   - doe:      blueprint image 8 DOE scoreboard
 *
 * Graceful: when caseId is null OR backend missing, falls back to em-dash
 * placeholder so the visual frame is preserved.
 */
import { useEffectiveCaseId } from "../hooks/useEffectiveCaseId";
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
import {
  useComparisonVerdict,
  type PostVerdict,
} from "../hooks/useComparisonVerdict";
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

/** M5 C4 · the Post KPI strip's "对比基准" chip, derived from the REAL
 *  gold-vs-measured verdict (useComparisonVerdict) — never a fabricated
 *  "+4.2% 增益". No baseline ⇒ honest "无基准"; service error ⇒ "不可用". */
export function postVerdictKpi(v: PostVerdict): KpiChip {
  if (v.state === "verdict" && v.level) {
    const label =
      v.level === "PASS" ? "通过" : v.level === "PARTIAL" ? "部分通过" : "未通过";
    const tone =
      v.level === "PASS" ? "healthy" : v.level === "PARTIAL" ? "warn" : "crit";
    return {
      value:
        v.nPass != null && v.nTotal != null ? `${v.nPass}/${v.nTotal}` : label,
      label: "对比基准",
      delta: label,
      deltaTone: tone,
    };
  }
  if (v.state === "error") return { value: "不可用", label: "对比基准" };
  // Codex M5-C4 R1 P3 · while the verdict fetch is in flight, show a neutral
  // "对比中…" rather than reusing the no-baseline copy — otherwise a solved
  // gold-standard case briefly flashes a false "无基准" before PASS/FAIL.
  if (v.state === "loading") return { value: "…", label: "对比基准" };
  return { value: "无基准", label: "对比基准" };
}

function chipsFor(
  step: V4PipelineStepId,
  ctx: V4Context,
  postVerdict: PostVerdict,
): KpiChip[] {
  if (
    step === "geometry" &&
    (!ctx.basics || !hasAuthoredCadParts(ctx.basics.patches?.length))
  ) {
    return [
      {
        value: String(GEOMETRY_BLUEPRINT_SUMMARY.partCount),
        label: "零件总数",
        unit: "个",
      },
      {
        value: String(GEOMETRY_BLUEPRINT_SUMMARY.gapCount),
        label: "缝隙检测",
        unit: "处",
        delta: "待采纳",
        deltaTone: "warn",
      },
      {
        value: GEOMETRY_BLUEPRINT_SUMMARY.toleranceMm.toFixed(1),
        label: "包裹尺寸",
        unit: "mm",
        delta: "建议全局",
      },
      {
        value: GEOMETRY_BLUEPRINT_SUMMARY.estimatedCellsM.toFixed(2),
        label: "流体域体积",
        unit: "m³",
        delta: "±2.1%",
        deltaTone: "healthy",
      },
    ];
  }

  if (step === "doe") {
    // M5.5 C3 · DOE has no real sweep backend (see the illustrative banner in
    // ModeRendererDoe). The old strip presented fabricated optima (28 方案 /
    // 212.6 Pa 最优 / 94.1 °C / 18h42m · "V-12" winner) as truth. Honest
    // placeholder instead — no fabricated optimisation results (DEC-V61-206).
    return [
      { value: "示意", label: "设计探索", delta: "功能开发中", deltaTone: "warn" },
      { value: "—", label: "方案数" },
      { value: "—", label: "最优压降", unit: "Pa" },
      { value: "—", label: "预计计算时长" },
    ];
  }

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
            label: "零件总数",
            unit: "个",
          },
          {
            value: String(GEOMETRY_BLUEPRINT_SUMMARY.gapCount),
            label: "缝隙检测",
            unit: "处",
            delta: "待采纳",
            deltaTone: "warn",
          },
          {
            value: GEOMETRY_BLUEPRINT_SUMMARY.toleranceMm.toFixed(1),
            label: "包裹尺寸",
            unit: "mm",
            delta: "建议全局",
          },
          {
            value: GEOMETRY_BLUEPRINT_SUMMARY.estimatedCellsM.toFixed(2),
            label: "流体域体积",
            unit: "m³",
            delta: "±2.1%",
            deltaTone: "healthy",
          },
        ];
      }
      return [
        { value: String(basics?.patches?.length ?? "—"), label: "边界面" },
        {
          value: String(basics?.dimension ?? "—"),
          label: "维度",
          // Codex R2 P3: drop the "D" suffix when dimension is unknown so the
          // chip reads "—" not "— D".
          unit: basics?.dimension != null ? "D" : undefined,
        },
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
        // M5.5 C4 · de-faked (DEC-V61-206). The old strip showed fabricated
        // patch counts (inlet 28 / outlet 27 / wall 6 / rotor 1) from
        // BOUNDARY_BLUEPRINT_KPIS, presented as if real. When this case has no
        // derived patches yet, show honest placeholders rather than fake counts.
        return [
          { value: "—", label: "入口" },
          { value: "—", label: "出口" },
          { value: "—", label: "壁面" },
          { value: "待识别", label: "边界面" },
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
      // M5.5 C2 · de-faked. The old strip showed fabricated KPIs (18.76M cells
      // / 248.6 Pa 压降 / 3.62 kg/s 质量流量 / 96.4 °C 出口温度 / 65%) the
      // workbench never computes for a generic case. Now reports REAL run-truth.
      //
      // Codex R1 P1 · the SOLVER step reflects the LATEST run (not the last
      // successful one — unlike Post). Using `successfulRunDetail ?? runDetail`
      // here would report a FAILED latest run as 成功 (with a 历史成功 delta),
      // which is false for "did the solve just succeed?". So the solver strip is
      // keyed on ctx.runDetail (latest) only; honest "待求解"/"—" when absent.
      const d = ctx.runDetail;
      if (!d) {
        return [
          { value: "待求解", label: "求解状态" },
          { value: "—", label: "用时", unit: "s" },
          { value: "—", label: "退出码" },
          { value: "—", label: "残差 p" },
        ];
      }
      const pRes = typeof d.residuals?.p === "number" ? d.residuals.p : null;
      return [
        {
          value: d.success ? "成功" : "失败",
          label: "求解状态",
          delta: d.success ? "已完成" : "已退出",
          deltaTone: d.success ? "healthy" : "crit",
        },
        { value: fmt(d.duration_s, 1), label: "用时", unit: "s" },
        { value: String(d.exit_code), label: "退出码" },
        {
          value: pRes != null ? pRes.toExponential(1) : "—",
          label: "残差 p",
        },
      ];
    }

    case "post": {
      // M5 C4 · de-faked. The old strip showed fabricated domain KPIs
      // (248.6 Pa 压降 / 3.62 kg/s 质量流量 / 96.4°C 出口温度 / +4.2% 增益)
      // that the workbench never computes for a generic imported case.
      // It now reports REAL solver-truth facts from the run being shown plus
      // the real gold-vs-measured verdict — honest "—"/"待求解"/"无基准"
      // when a fact is absent, never a confident invented number.
      //
      // Codex M5-C4 R0 P2 · fall back to the latest run (which may be FAILED)
      // rather than collapsing a failed-only case into "待求解": runDetail
      // still carries the real exit code / duration the user needs to debug.
      // The verdict chip stays keyed on successfulRunDetail (a failed run has
      // no valid gold comparison ⇒ honest "无基准").
      const d = ctx.successfulRunDetail ?? ctx.runDetail;
      if (!d) {
        return [
          { value: "待求解", label: "求解状态" },
          { value: "—", label: "用时", unit: "s" },
          { value: "—", label: "残差 p" },
          postVerdictKpi(postVerdict),
        ];
      }
      const pRes =
        typeof d.residuals?.p === "number" ? d.residuals.p : null;
      // Codex M5-C4 R1 P2 · when the newest run failed but an older success is
      // being shown (fallback), disclose "历史成功" like ModeRendererPost does
      // — a plain green "成功" here would contradict the failed head run the
      // user is debugging.
      const showingFallbackRun =
        ctx.successfulRunDetail != null &&
        ctx.latestRun?.run_id !== ctx.latestSuccessfulRun?.run_id;
      return [
        {
          value: d.success ? "成功" : "失败",
          label: "求解状态",
          delta: showingFallbackRun ? "历史成功" : d.success ? "已完成" : "已退出",
          deltaTone: showingFallbackRun ? "warn" : d.success ? "healthy" : "crit",
        },
        { value: fmt(d.duration_s, 1), label: "用时", unit: "s" },
        { value: String(d.exit_code), label: "退出码" },
        {
          value: pRes != null ? pRes.toExponential(1) : "—",
          label: "残差 p",
        },
        postVerdictKpi(postVerdict),
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
  // DEC-V61-202 M3.8 cycle 1: shared blueprint-vs-case gate (see useEffectiveCaseId.ts).
  const { effectiveCaseId } = useEffectiveCaseId(caseId, activeStep);
  const ctx = useV4WorkbenchContext(effectiveCaseId);
  // M5 C4 · real gold-vs-measured verdict for the Post strip's 对比基准 chip.
  // Gated to the post step (runLabel null elsewhere ⇒ the hook stays idle).
  const postVerdict = useComparisonVerdict(
    effectiveCaseId,
    activeStep === "post" ? (ctx.successfulRunDetail?.run_id ?? null) : null,
  );
  if (activeStep === "mesh") {
    return <MeshKpiStrip ctx={ctx} />;
  }
  const chips = chipsFor(activeStep, ctx, postVerdict);
  const isGeometry = activeStep === "geometry";

  return (
    <div
      className={[
        "flex shrink-0 items-center border-t border-v4-border bg-v4-shell",
        isGeometry ? "h-[104px] gap-4 px-4" : "h-24 gap-6 px-6",
      ].join(" ")}
      data-testid="kpistrip-v4"
      data-active-step={activeStep}
      data-backend-connected={ctx.hasBackend ? "true" : "false"}
    >
      {chips.map((chip, i) => (
        <div
          key={i}
          className={[
            "flex flex-col justify-center",
            isGeometry
              ? "h-[72px] min-w-0 flex-1 border border-v4-border bg-v4-surfaceRaised/40 px-4"
              : "min-w-[110px]",
          ].join(" ")}
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
