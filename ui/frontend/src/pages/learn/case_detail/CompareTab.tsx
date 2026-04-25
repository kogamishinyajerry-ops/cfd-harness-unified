// Compare tab: gold vs measurement, tolerance band, multi-dimension panel,
// run selector. The "evidence" surface where verdicts are surfaced.
//
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import { useQuery } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import { RunExportPanel } from "@/components/learn/ExportPanel";
import { getLearnCase } from "@/data/learnCases";
import type {
  RunCategory,
  RunDescriptor,
  ValidationReport,
} from "@/types/validation";

import { STATUS_CLASS, STATUS_TEXT } from "./constants";
import type { ComparisonReportContext } from "./ScientificComparisonReport";
import { ErrorCallout, SkeletonCallout } from "./shared";

// --- Compare tab body --------------------------------------------------

const RUN_CATEGORY_LABEL: Record<RunCategory, string> = {
  reference: "参考运行",
  real_incident: "真实故障",
  under_resolved: "欠分辨",
  wrong_model: "错模型",
  grid_convergence: "网格收敛",
  audit_real_run: "真实审计",
};

const RUN_CATEGORY_COLOR: Record<RunCategory, string> = {
  reference: "bg-emerald-900/40 text-emerald-200 border-emerald-800/60",
  real_incident: "bg-amber-900/30 text-amber-200 border-amber-800/50",
  under_resolved: "bg-orange-900/30 text-orange-200 border-orange-800/50",
  wrong_model: "bg-rose-900/30 text-rose-200 border-rose-800/50",
  grid_convergence: "bg-sky-900/30 text-sky-200 border-sky-800/50",
  audit_real_run: "bg-accent-900/40 text-accent-200 border-accent-800/60",
};

export function CompareTab({
  caseId,
  report,
  error,
  runs,
  activeRunId,
  onSelectRun,
}: {
  caseId: string;
  report: ValidationReport | undefined;
  error: ApiError | null;
  runs: RunDescriptor[];
  activeRunId: string | undefined;
  onSelectRun: (runId: string | null) => void;
}) {
  const learnCase = getLearnCase(caseId)!;

  if (error) {
    return (
      <ErrorCallout
        message={`后端没有为 ${caseId} 返回验证报告 (${error.status})`}
      />
    );
  }
  if (!report) {
    return <SkeletonCallout message="正在从后端取回验证报告…" />;
  }

  const { gold_standard, measurement, contract_status, deviation_pct, tolerance_lower, tolerance_upper } = report;

  // Which run is currently shown. If `activeRunId` is not set, the
  // backend resolves the default via `_pick_default_run_id` — post
  // DEC-V61-035 (honesty correction) that's audit_real_run first, then
  // reference, then any curated run, then legacy. We highlight whichever
  // run actually matches the loaded measurement; the heuristic below is
  // the UI-side fallback when measurement.run_id is somehow missing.
  const resolvedRun = runs.find((r) => r.run_id === measurement?.run_id)
    ?? runs.find((r) => activeRunId ? r.run_id === activeRunId : r.category === "audit_real_run")
    ?? runs.find((r) => r.category === "reference")
    ?? runs[0];

  return (
    <div className="space-y-6">
      {/* Run selector — only rendered when the case has curated runs */}
      {runs.length > 0 && (
        <section className="rounded-lg border border-surface-800 bg-surface-900/30 px-4 py-3">
          <div className="mb-2 flex items-baseline justify-between">
            <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">
              选择一条 run
            </p>
            <p className="text-[11px] text-surface-500">
              换一条运行 → 验证结果会不同 · 这就是"做对"和"数字碰巧对上"的区别
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {runs.map((run) => {
              const isActive =
                (resolvedRun && resolvedRun.run_id === run.run_id) ||
                activeRunId === run.run_id;
              return (
                <button
                  key={run.run_id}
                  onClick={() => onSelectRun(run.run_id)}
                  className={`rounded-md border px-3 py-1.5 text-left text-[12px] transition-colors ${
                    isActive
                      ? "border-sky-500 bg-sky-950/40 text-surface-100"
                      : "border-surface-700 bg-surface-900/40 text-surface-300 hover:border-surface-600"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${RUN_CATEGORY_COLOR[run.category]}`}
                    >
                      {RUN_CATEGORY_LABEL[run.category]}
                    </span>
                    <span className="font-medium">{run.label_zh}</span>
                  </div>
                  <p className="mono mt-0.5 text-[10px] text-surface-500">
                    run_id={run.run_id} · 预期={run.expected_verdict}
                  </p>
                </button>
              );
            })}
          </div>
          {resolvedRun?.description_zh && (
            <p className="mt-3 text-[12px] leading-relaxed text-surface-400">
              {resolvedRun.description_zh}
            </p>
          )}
        </section>
      )}

      {/* Verdict line */}
      <section className="rounded-lg border border-surface-800 bg-surface-900/40 px-5 py-4">
        <div className="flex items-baseline justify-between">
          <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">结果</p>
          <span className={`mono text-[12px] ${STATUS_CLASS[contract_status]}`}>
            {contract_status}
          </span>
        </div>
        <p className={`mt-1 text-[18px] font-medium ${STATUS_CLASS[contract_status]}`}>
          {STATUS_TEXT[contract_status]}
        </p>
        {/* Stage 6 ExportPack · per-run download chips inline with verdict.
            Uses resolvedRun (the actual run whose measurement is rendered)
            so the CSV/PDF match what the user is reading. */}
        {resolvedRun && (
          <div className="mt-3">
            <RunExportPanel caseId={caseId} runId={resolvedRun.run_id} />
          </div>
        )}
      </section>

      {/* Gold vs measured */}
      <section className="grid gap-4 md:grid-cols-2">
        <StatBlock
          label="黄金标准"
          subLabel={gold_standard.citation}
          value={gold_standard.ref_value}
          unit={gold_standard.unit}
          quantity={gold_standard.quantity}
        />
        <StatBlock
          label="你的测量"
          subLabel={measurement?.source ?? "—"}
          value={measurement?.value ?? null}
          unit={measurement?.unit ?? gold_standard.unit}
          quantity={gold_standard.quantity}
          accent
        />
      </section>

      {/* Tolerance band */}
      <section>
        <h3 className="card-title mb-2">容差带</h3>
        <ToleranceBand
          goldValue={gold_standard.ref_value}
          tolerancePct={gold_standard.tolerance_pct}
          lower={tolerance_lower}
          upper={tolerance_upper}
          measured={measurement?.value ?? null}
        />
        {deviation_pct !== null && (
          <p className="mt-3 text-[13px] text-surface-300">
            偏差 <span className={`mono ${STATUS_CLASS[contract_status]}`}>
              {deviation_pct > 0 ? "+" : ""}
              {deviation_pct.toFixed(2)}%
            </span>{" "}
            · 容差宽度 ±{(gold_standard.tolerance_pct * 100).toFixed(1)}%
          </p>
        )}
      </section>

      {/* DEC-V61-049 batch C · multi-dimensional Compare panel.
          Previously CompareTab was scalar-only (one anchor + one tolerance
          band). Backend already computes: profile PASS/PARTIAL/FAIL with
          n_pass/n_total counts, per-point deviation array, rendered
          profile + pointwise + residual PNGs, grid convergence rows, and
          Richardson GCI. Story tab's ScientificComparisonReportSection
          was the only place that surfaced them. This panel promotes 5
          named dimensions into Compare so the student can see >1 dim
          of validation evidence without leaving the tab named Compare.
          Optional: only renders for cases with gold-overlay context
          (404/400 → silent hide). */}
      <MultiDimensionComparePanel
        caseId={caseId}
        profileVerdict={report.profile_verdict}
        profilePassCount={report.profile_pass_count}
        profileTotalCount={report.profile_total_count}
      />

      {/* Learning angle — reframe FAIL/HAZARD as a teaching moment */}
      <section className="rounded-md border border-sky-900/40 bg-sky-950/15 px-4 py-3">
        <p className="mb-1 text-[11px] uppercase tracking-[0.14em] text-sky-300">
          学习点 · Learning angle
        </p>
        <p className="text-[14px] leading-relaxed text-surface-200">
          {learnCase.why_validation_matters_zh}
        </p>
      </section>
    </div>
  );
}

// DEC-V61-049 batch C — Multi-dimensional Compare panel.
// Reuses the existing comparison-report/context endpoint (same data
// source as Story tab's ScientificComparisonReportSection) but
// promotes the evidence into 5 named dimensions inside Compare tab.
// Dimensions:
//   D1 · scalar anchor (already rendered above, recap verdict here)
//   D2 · profile verdict (PASS/PARTIAL/FAIL with n/N count)
//   D3 · profile overlay chart (embedded profile_u_centerline.png)
//   D4 · pointwise deviation bars (embedded pointwise_deviation.png)
//   D5 · grid convergence + GCI (native card from grid_conv + gci)
//   D6 · v_centerline (Ghia Table II, horizontal centerline v profile) —
//        DEC-V61-050 batch 1: independent physical observable, not a
//        re-slice of u_centerline. Gold = Ghia 1982 Table II native 17
//        non-uniform x points. Measured = post-hoc VTK interpolation
//        of U_y onto y=0.05 line (no simpleFoam re-run).
//   D7 · primary vortex (x_c, y_c, ψ_min) — DEC-V61-050 batch 3:
//        2D observable, completely independent of the two line-
//        probe observables. Gold = Ghia 1982 Table III primary row.
//        Measured = 2D argmin of ψ(x, y) = ∫₀^y U_x dy' on a 129²
//        resampling of the audit VTK (see ui/backend/services/
//        psi_extraction.py).
//   D8 · secondary vortices BL + BR — DEC-V61-050 batch 4:
//        Corner-windowed ψ_max on the same 129² grid as D7. Gold =
//        Ghia 1982 Table III rows 3-4 (Re=100). Relaxed tolerance
//        (10% on |ψ| vs primary's 5%) — corner eddies are mesh-
//        sensitive by an order of magnitude more than the primary.
// After batch 4 the DEC-V61-050 arc is closed: every Ghia Re=100
// observable (4 of them) is exercised as a dimension here. Final
// footer celebrates that and points to the DEC for implementation
// trail.
function MultiDimensionComparePanel({
  caseId,
  profileVerdict,
  profilePassCount,
  profileTotalCount,
}: {
  caseId: string;
  profileVerdict: "PASS" | "PARTIAL" | "FAIL" | null;
  profilePassCount: number | null;
  profileTotalCount: number | null;
}) {
  const runLabel = "audit_real_run";
  const { data, error, isLoading } = useQuery<ComparisonReportContext, ApiError>({
    queryKey: ["comparison-report-ctx", caseId, runLabel],
    queryFn: async () => {
      const resp = await fetch(
        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
          runLabel,
        )}/comparison-report/context`,
        { credentials: "same-origin" },
      );
      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
      return (await resp.json()) as ComparisonReportContext;
    },
    retry: false,
    staleTime: 60_000,
  });

  // 404/400 = case not opted-in to gold-overlay (scalar-only case).
  // Silent hide — the panel is a value-add, not a blocker.
  if (isLoading) return null;
  if (error) {
    const status = error instanceof ApiError ? error.status : 0;
    if (status === 404 || status === 400) return null;
    return null; // Non-critical failure; scalar part above still renders.
  }
  if (!data) return null;
  // DEC-V61-052 Batch D + V61-053 Batch D: visual-only cases can still
  // render scalar-anchor cards. BFS → 1 card (Xr/H); cylinder → up to 4
  // cards (D-St, D-Cd, D-Cl_rms, D-u@4 profile). Full LDC-style multi-dim
  // panel requires data.metrics + data.paper below.
  if (data.visual_only) {
    // BFS scalar-anchor card (DEC-V61-052)
    if (data.case_id === "backward_facing_step") {
      if (!data.metrics_reattachment || !data.paper_reattachment) return null;
      const mr = data.metrics_reattachment;
      const pr = data.paper_reattachment;
      const passing = mr.within_tolerance;
      return (
        <section className="space-y-4">
          <div className="flex items-baseline justify-between">
            <h3 className="card-title">多维验证证据 · Multi-dimension evidence</h3>
            <p className="text-[11px] text-surface-500">{pr.short} · 1 个独立标量维度</p>
          </div>
          <div className={`rounded-md border p-4 ${
            passing
              ? "border-emerald-800/60 bg-emerald-900/15"
              : "border-rose-800/60 bg-rose-900/15"
          }`}>
            <div className="mb-2 flex items-baseline gap-2">
              <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
                D1 · Scalar anchor
              </span>
              <span className={`mono text-[10.5px] font-semibold ${
                passing ? "text-emerald-300" : "text-rose-300"
              }`}>
                {passing ? "PASS" : "FAIL"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <div className="text-[10.5px] text-surface-500">{mr.symbol} 测量</div>
                <div className="mono text-surface-100">{mr.actual.toFixed(3)}</div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">{mr.symbol} 金标准</div>
                <div className="mono text-surface-100">{mr.expected.toFixed(3)}</div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">偏差</div>
                <div className={`mono ${passing ? "text-emerald-300" : "text-rose-300"}`}>
                  {mr.deviation_pct.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">容差带</div>
                <div className="mono text-surface-100">±{mr.tolerance_pct.toFixed(0)}%</div>
              </div>
            </div>
            <div className="mt-3 text-[11px] text-surface-400">
              来源：{pr.source}
              {mr.method ? <> · 测量方法：<span className="mono">{mr.method}</span></> : null}
            </div>
          </div>
        </section>
      );
    }

    // Cylinder 4-scalar anchor cards (DEC-V61-053 Batch D)
    if (data.case_id === "circular_cylinder_wake") {
      const hasAnyCylinderMetric =
        data.metrics_strouhal || data.metrics_cd_mean ||
        data.metrics_cl_rms || data.metrics_u_centerline;
      if (!hasAnyCylinderMetric) return null;
      const dims = [
        data.metrics_strouhal,
        data.metrics_cd_mean,
        data.metrics_cl_rms,
        data.metrics_u_centerline,
      ].filter(Boolean).length;
      // Reusable scalar-card renderer
      const renderScalarCard = (
        label: string,
        metrics: typeof data.metrics_strouhal,
        paper: typeof data.paper_strouhal,
      ) => {
        if (!metrics || !paper) return null;
        const passing = metrics.within_tolerance;
        return (
          <div key={label} className={`rounded-md border p-3 ${
            passing
              ? "border-emerald-800/60 bg-emerald-900/15"
              : "border-rose-800/60 bg-rose-900/15"
          }`}>
            <div className="mb-2 flex items-baseline gap-2">
              <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
                {label} · {metrics.symbol}
              </span>
              <span className={`mono text-[10.5px] font-semibold ${
                passing ? "text-emerald-300" : "text-rose-300"
              }`}>
                {passing ? "PASS" : "FAIL"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <div className="text-[10.5px] text-surface-500">测量</div>
                <div className="mono text-surface-100">{metrics.actual.toFixed(4)}</div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">金标准</div>
                <div className="mono text-surface-100">{metrics.expected.toFixed(4)}</div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">偏差</div>
                <div className={`mono ${passing ? "text-emerald-300" : "text-rose-300"}`}>
                  {metrics.deviation_pct.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">容差带</div>
                <div className="mono text-surface-100">±{metrics.tolerance_pct.toFixed(0)}%</div>
              </div>
            </div>
            {metrics.method && (
              <div className="mt-2 text-[10.5px] text-surface-500">
                方法：<span className="mono">{metrics.method}</span>
              </div>
            )}
          </div>
        );
      };
      return (
        <section className="space-y-4">
          <div className="flex items-baseline justify-between">
            <h3 className="card-title">多维验证证据 · Multi-dimension evidence</h3>
            <p className="text-[11px] text-surface-500">
              Williamson 1996 · {dims} 个独立维度 (Type I 圆柱尾迹)
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {renderScalarCard("D-St · Strouhal 频率", data.metrics_strouhal, data.paper_strouhal)}
            {renderScalarCard("D-Cd · 平均阻力", data.metrics_cd_mean, data.paper_cd_mean)}
            {renderScalarCard("D-Cl · 升力 RMS", data.metrics_cl_rms, data.paper_cl_rms)}
          </div>
          {data.metrics_u_centerline && data.paper_u_centerline && (() => {
            const uc = data.metrics_u_centerline;
            const allPass = uc.all_within_tolerance;
            return (
              <div className={`rounded-md border p-4 ${
                allPass
                  ? "border-emerald-800/60 bg-emerald-900/15"
                  : "border-amber-800/60 bg-amber-900/15"
              }`}>
                <div className="mb-3 flex items-baseline gap-2">
                  <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
                    D-u · 尾迹中线速度亏损剖面 (4 stations)
                  </span>
                  <span className={`mono text-[10.5px] font-semibold ${
                    allPass ? "text-emerald-300" : "text-amber-300"
                  }`}>
                    {allPass ? "PASS (4/4)" : `PARTIAL (${
                      uc.stations.filter((s) => s.within_tolerance).length
                    }/${uc.stations.length})`}
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-2 text-center">
                  {uc.stations.map((s) => (
                    <div key={s.x_D} className={`rounded p-2 ${
                      s.within_tolerance
                        ? "bg-emerald-950/50"
                        : "bg-rose-950/50"
                    }`}>
                      <div className="text-[10.5px] text-surface-500">x/D={s.x_D}</div>
                      <div className="mono text-[12px] text-surface-100">
                        {s.actual.toFixed(3)}
                      </div>
                      <div className="text-[10px] text-surface-500">
                        gold {s.expected.toFixed(2)}
                      </div>
                      <div className={`mono text-[10.5px] ${
                        s.within_tolerance ? "text-emerald-300" : "text-rose-300"
                      }`}>
                        {s.deviation_pct >= 0 ? "+" : ""}{s.deviation_pct.toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 text-[11px] text-surface-400">
                  语义：wake deficit = (U∞ − u_mean)/U∞ · 容差 ±{uc.tolerance_pct.toFixed(0)}% · 来源：{data.paper_u_centerline.source}
                </div>
              </div>
            );
          })()}
        </section>
      );
    }

    // DHC 5-observable anchor cards (DEC-V61-057 Stage D · de Vahl Davis 1983)
    // 4 HARD_GATED + 1 PROVISIONAL_ADVISORY. Mirrors cylinder Stage-D pattern
    // but adds an "Advisory" badge for ψ_max and supports pending placeholders.
    if (data.case_id === "differential_heated_cavity") {
      const dhc = data.metrics_dhc;
      if (!dhc || !dhc.observables || dhc.observables.length === 0) return null;

      const renderDhcCard = (o: typeof dhc.observables[number]) => {
        const isAdvisory = o.gate_status === "PROVISIONAL_ADVISORY";
        const isPending = !!o.pending;
        const passing = o.within_tolerance === true;
        const failing = o.within_tolerance === false;

        // Border / background per state (advisory uses amber; hard pending uses surface-800).
        let borderBg: string;
        if (isPending) {
          borderBg = "border-surface-800 bg-surface-900/40";
        } else if (isAdvisory) {
          // Advisory observables: emerald when within, amber when out (not red,
          // because they don't gate the verdict — surface as informational).
          borderBg = passing
            ? "border-emerald-800/60 bg-emerald-900/15"
            : "border-amber-800/60 bg-amber-900/15";
        } else {
          borderBg = passing
            ? "border-emerald-800/60 bg-emerald-900/15"
            : "border-rose-800/60 bg-rose-900/15";
        }

        let statusLabel: string;
        let statusColor: string;
        if (isPending) {
          statusLabel = "PENDING";
          statusColor = "text-surface-400";
        } else if (passing) {
          statusLabel = isAdvisory ? "ADVISORY · WITHIN" : "PASS";
          statusColor = "text-emerald-300";
        } else if (failing) {
          statusLabel = isAdvisory ? "ADVISORY · OUTSIDE" : "FAIL";
          statusColor = isAdvisory ? "text-amber-300" : "text-rose-300";
        } else {
          statusLabel = "—";
          statusColor = "text-surface-400";
        }

        return (
          <div key={o.name} className={`rounded-md border p-3 ${borderBg}`}>
            <div className="mb-2 flex items-baseline gap-2">
              <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
                {o.label} · {o.symbol}
              </span>
              <span className={`mono text-[10.5px] font-semibold ${statusColor}`}>
                {statusLabel}
              </span>
              {isAdvisory && (
                <span className="mono text-[10px] text-amber-300/80" title="Excluded from overall verdict — Stage C gate_status=PROVISIONAL_ADVISORY">
                  · 不计入裁决
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <div className="text-[10.5px] text-surface-500">测量</div>
                <div className="mono text-surface-100">
                  {o.actual !== null && o.actual !== undefined ? o.actual.toFixed(3) : "—"}
                </div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">金标准</div>
                <div className="mono text-surface-100">
                  {o.expected !== null && o.expected !== undefined ? o.expected.toFixed(3) : "—"}
                </div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">偏差</div>
                <div className={`mono ${
                  isPending ? "text-surface-500" : (passing ? "text-emerald-300" : (isAdvisory ? "text-amber-300" : "text-rose-300"))
                }`}>
                  {o.deviation_pct !== null && o.deviation_pct !== undefined
                    ? `${o.deviation_pct.toFixed(1)}%`
                    : "—"}
                </div>
              </div>
              <div>
                <div className="text-[10.5px] text-surface-500">容差带</div>
                <div className="mono text-surface-100">±{o.tolerance_pct.toFixed(0)}%</div>
              </div>
            </div>
            <div className="mt-2 text-[10.5px] text-surface-500">
              {o.label_zh}
              {o.source_table ? <> · 来源：<span className="mono">{o.source_table}</span></> : null}
              {isPending && (
                <span className="ml-1 text-amber-300/80">
                  · Stage E live run 待跑（secondary_scalars 未填）
                </span>
              )}
            </div>
          </div>
        );
      };

      return (
        <section className="space-y-4">
          <div className="flex items-baseline justify-between">
            <h3 className="card-title">多维验证证据 · Multi-dimension evidence</h3>
            <p className="text-[11px] text-surface-500">
              {dhc.short} · {dhc.hard_gated_count} 个 HARD_GATED + {dhc.advisory_count} 个 PROVISIONAL_ADVISORY (Type I 自然对流方腔)
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {dhc.observables.map(renderDhcCard)}
          </div>
        </section>
      );
    }

    // Other visual_only cases: no scalar-anchor cards yet.
    return null;
  }
  if (!data.metrics || !data.paper) return null;

  const m = data.metrics;
  const renderUrl = (basename: string) =>
    `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
      runLabel,
    )}/renders/${basename}`;
  const profileUrl = data.renders.profile_png_rel ? renderUrl("profile_u_centerline.png") : null;
  const pointwiseUrl = data.renders.pointwise_png_rel ? renderUrl("pointwise_deviation.png") : null;

  const verdictStyles: Record<NonNullable<typeof profileVerdict>, { badge: string; label: string }> = {
    PASS: { badge: "bg-emerald-900/40 text-emerald-300", label: "PASS" },
    PARTIAL: { badge: "bg-amber-900/40 text-amber-300", label: "PARTIAL" },
    FAIL: { badge: "bg-rose-900/40 text-rose-300", label: "FAIL" },
  };
  const pv = profileVerdict ? verdictStyles[profileVerdict] : null;

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h3 className="card-title">多维验证证据 · Multi-dimension evidence</h3>
        <p className="text-[11px] text-surface-500">
          {data.paper.short} · 当前支持 {1 + (profileVerdict ? 1 : 0) + (profileUrl ? 1 : 0) + (pointwiseUrl ? 1 : 0) + (data.grid_conv && data.grid_conv.length ? 1 : 0) + (data.metrics_v_centerline ? 1 : 0) + (data.metrics_primary_vortex ? 1 : 0) + (data.metrics_secondary_vortices ? 1 : 0)} 个独立维度
        </p>
      </div>

      {/* D2 · Profile verdict split from scalar anchor */}
      {pv && profileTotalCount && (
        <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <div className="mb-1 flex items-baseline gap-2">
            <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
              D2 · 剖面整体裁决
            </span>
            <span className={`mono inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-semibold ${pv.badge}`}>
              {pv.label}
            </span>
          </div>
          <p className="text-[13px] leading-relaxed text-surface-200">
            <span className="mono font-semibold text-surface-100">{profilePassCount} / {profileTotalCount}</span>{" "}
            个采样点落在 ±{data.paper.tolerance_pct.toFixed(1)}% 容差带内。
            {profileVerdict === "PARTIAL" && (
              <span className="text-amber-200/90">
                {" "}注意：上面的 scalar 单点裁决和这个 profile 整体裁决可能不一致——scalar 取的是某一 y 的单点，profile 是全 17 点。写报告时必须两个维度都报告。
              </span>
            )}
            {profileVerdict === "FAIL" && (
              <span className="text-rose-200/90">
                {" "}Profile 整体未达标——即使 scalar 单点通过，也不能视为 case 通过。
              </span>
            )}
          </p>
          <div className="mt-2 grid grid-cols-4 gap-3 text-[11px]">
            <div>
              <div className="text-surface-500">L²</div>
              <div className="mono text-surface-100">{m.l2.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-surface-500">L∞</div>
              <div className="mono text-surface-100">{m.linf.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-surface-500">max |dev|</div>
              <div className="mono text-surface-100">{m.max_dev_pct.toFixed(2)}%</div>
            </div>
            <div>
              <div className="text-surface-500">RMS</div>
              <div className="mono text-surface-100">{m.rms.toFixed(4)}</div>
            </div>
          </div>
        </div>
      )}

      {/* D3 · Profile overlay chart */}
      {profileUrl && (
        <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <div className="mb-2 flex items-baseline justify-between">
            <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
              D3 · 剖面逐点对比
            </span>
            <span className="text-[10.5px] text-surface-500">
              17 点 vs {data.paper.short}
            </span>
          </div>
          <img
            src={profileUrl}
            alt={`${caseId} u_centerline profile vs ${data.paper.short}`}
            className="w-full rounded bg-white"
            loading="lazy"
          />
        </div>
      )}

      {/* D4 · Pointwise deviation bars */}
      {pointwiseUrl && (
        <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <div className="mb-2 flex items-baseline justify-between">
            <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
              D4 · 逐点偏差柱状图
            </span>
            <span className="text-[10.5px] text-surface-500">
              红色柱 = 超出 ±{data.paper.tolerance_pct.toFixed(1)}% 容差
            </span>
          </div>
          <img
            src={pointwiseUrl}
            alt={`${caseId} pointwise deviation`}
            className="w-full rounded bg-white"
            loading="lazy"
          />
          {m.per_point_dev_pct && m.per_point_dev_pct.length > 0 && (
            <p className="mono mt-2 text-[10.5px] leading-relaxed text-surface-500">
              raw: [
              {m.per_point_dev_pct
                .map((d) => d.toFixed(1))
                .join(", ")}
              ] %
            </p>
          )}
        </div>
      )}

      {/* D5 · Grid convergence + GCI */}
      {data.grid_conv && data.grid_conv.length > 0 && (
        <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <div className="mb-2 flex items-baseline justify-between">
            <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
              D5 · 网格收敛（Richardson / GCI）
            </span>
            {data.grid_conv_note && (
              <span className="text-[10.5px] text-surface-500">{data.grid_conv_note}</span>
            )}
          </div>
          <table className="w-full border-separate border-spacing-y-1 text-[11.5px]">
            <thead>
              <tr className="text-left text-[10.5px] uppercase tracking-wider text-surface-500">
                <th className="pb-1">mesh</th>
                <th className="pb-1">u @ y=0.0625</th>
                <th className="pb-1">|dev|%</th>
                <th className="pb-1">verdict</th>
              </tr>
            </thead>
            <tbody>
              {data.grid_conv.map((r) => {
                const cls =
                  r.verdict_class === "pass"
                    ? "text-emerald-300"
                    : r.verdict_class === "warn"
                    ? "text-amber-300"
                    : "text-rose-300";
                return (
                  <tr key={r.mesh} className="bg-surface-950/30">
                    <td className="mono px-2 py-1 text-surface-200">{r.mesh}</td>
                    <td className="mono px-2 py-1 text-surface-100">
                      {r.value.toFixed(4)}
                    </td>
                    <td className="mono px-2 py-1 text-surface-300">
                      {r.dev_pct.toFixed(2)}%
                    </td>
                    <td className={`mono px-2 py-1 font-semibold ${cls}`}>
                      {r.verdict}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {data.gci && (
            <div className="mt-3 rounded border border-surface-800 bg-surface-950/40 px-3 py-2 text-[11.5px]">
              <p className="mb-1 mono text-[10.5px] font-semibold uppercase tracking-wider text-sky-300">
                Richardson extrapolation
              </p>
              <div className="grid grid-cols-4 gap-3 text-[11px]">
                <div>
                  <div className="text-surface-500">p_obs</div>
                  <div className="mono text-surface-100">
                    {data.gci.p_obs !== null ? data.gci.p_obs.toFixed(2) : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-surface-500">GCI_21</div>
                  <div className="mono text-surface-100">
                    {data.gci.gci_21_pct !== null ? `${data.gci.gci_21_pct.toFixed(2)}%` : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-surface-500">GCI_32</div>
                  <div className="mono text-surface-100">
                    {data.gci.gci_32_pct !== null ? `${data.gci.gci_32_pct.toFixed(2)}%` : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-surface-500">渐近区</div>
                  <div className={`mono ${data.gci.asymptotic_range_ok ? "text-emerald-300" : "text-amber-300"}`}>
                    {data.gci.asymptotic_range_ok ? "OK" : "check"}
                  </div>
                </div>
              </div>
              {data.gci.note && (
                <p className="mt-1 text-[10.5px] leading-relaxed text-surface-400">
                  {data.gci.note}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* D6 · v_centerline (Ghia Table II) — DEC-V61-050 batch 1.
          Independent physical observable: horizontal centerline v profile
          at y=0.5L, compared against Ghia Table II Re=100 native 17-point
          non-uniform x grid. */}
      {data.metrics_v_centerline && data.paper_v_centerline && (
        <div className="rounded-md border border-emerald-900/40 bg-emerald-950/10 p-4">
          <div className="mb-1 flex items-baseline gap-2">
            <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-emerald-300">
              D6 · 水平中线 v 剖面（独立观测量）
            </span>
            <span className="mono inline-flex items-center rounded-sm bg-emerald-900/40 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
              {data.metrics_v_centerline.n_pass} / {data.metrics_v_centerline.n_total}
            </span>
          </div>
          <p className="text-[13px] leading-relaxed text-surface-200">
            {data.paper_v_centerline.short} · Ghia 原生 17 点非均匀 x 网格，从既有 VTK 体数据后验插值到 y=0.5L 水平线（无需重跑 simpleFoam）。
            <span className="mono font-semibold text-surface-100">
              {" "}{data.metrics_v_centerline.n_pass} / {data.metrics_v_centerline.n_total}
            </span>
            {" "}个点落在 ±{data.paper_v_centerline.tolerance_pct.toFixed(1)}% 容差带内。
          </p>
          <p className="mt-1 text-[11.5px] leading-relaxed text-emerald-200/80">
            这是<strong>独立于 u_centerline 的物理维度</strong>——u 量的是垂直中线上水平分量 U_x，v 量的是水平中线上竖直分量 U_y，曲线形状、极值位置、零交叉都完全不同。与 D2-D4 的 u_centerline 合计两个真正独立的 profile 观测量。
          </p>
          <div className="mt-2 grid grid-cols-4 gap-3 text-[11px]">
            <div>
              <div className="text-surface-500">L²</div>
              <div className="mono text-surface-100">{data.metrics_v_centerline.l2.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-surface-500">L∞</div>
              <div className="mono text-surface-100">{data.metrics_v_centerline.linf.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-surface-500">max |dev|</div>
              <div className="mono text-surface-100">{data.metrics_v_centerline.max_dev_pct.toFixed(2)}%</div>
            </div>
            <div>
              <div className="text-surface-500">RMS</div>
              <div className="mono text-surface-100">{data.metrics_v_centerline.rms.toFixed(4)}</div>
            </div>
          </div>
          {data.metrics_v_centerline.per_point_dev_pct && data.metrics_v_centerline.per_point_dev_pct.length > 0 && (
            <p className="mono mt-2 text-[10.5px] leading-relaxed text-surface-500">
              per-point |dev|%: [
              {data.metrics_v_centerline.per_point_dev_pct
                .map((d) => (Number.isFinite(d) ? d.toFixed(1) : "—"))
                .join(", ")}
              ]
            </p>
          )}
        </div>
      )}

      {/* D7 · Primary vortex (x_c, y_c, ψ_min) — DEC-V61-050 batch 3.
          Independent physical observable: 2D argmin of ψ over the whole
          cavity, compared against Ghia Table III Re=100. */}
      {data.metrics_primary_vortex && data.paper_primary_vortex && (
        <div className={`rounded-md border p-4 ${
          data.metrics_primary_vortex.all_pass
            ? "border-emerald-900/40 bg-emerald-950/10"
            : "border-amber-900/40 bg-amber-950/10"
        }`}>
          <div className="mb-1 flex items-baseline gap-2">
            <span className={`mono text-[10.5px] font-semibold uppercase tracking-wider ${
              data.metrics_primary_vortex.all_pass ? "text-emerald-300" : "text-amber-300"
            }`}>
              D7 · 主涡中心（独立观测量）
            </span>
            <span className={`mono inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-semibold ${
              data.metrics_primary_vortex.all_pass
                ? "bg-emerald-900/40 text-emerald-300"
                : "bg-amber-900/40 text-amber-300"
            }`}>
              {data.metrics_primary_vortex.all_pass ? "PASS" : "PARTIAL"}
            </span>
          </div>
          <p className="text-[13px] leading-relaxed text-surface-200">
            {data.paper_primary_vortex.short} · 由 ψ(x,y)=∫₀^y U_x dy' 在 129² 重采样网格上 2D argmin 提取，
            对比 Ghia 1982 Table III Re=100 的主涡中心和 ψ_min。
            <span className="block mt-1 text-[11.5px] text-emerald-200/80">
              这是<strong>与 u_centerline / v_centerline 都不同的 2D 结构观测量</strong>——前两者都是 1D 剖面，主涡中心是通过整个场的流函数 argmin 定位得到的二维点 + ψ 强度。完全独立于任何单线采样。
            </span>
          </p>
          <div className="mt-2 grid grid-cols-3 gap-3 text-[11px]">
            <div>
              <div className="text-surface-500">x_c (x/L)</div>
              <div className="mono text-surface-100">
                {data.metrics_primary_vortex.x_meas.toFixed(4)}
              </div>
              <div className="mono text-[10px] text-surface-500">
                gold: {data.metrics_primary_vortex.x_gold.toFixed(4)}
              </div>
            </div>
            <div>
              <div className="text-surface-500">y_c (y/L)</div>
              <div className="mono text-surface-100">
                {data.metrics_primary_vortex.y_meas.toFixed(4)}
              </div>
              <div className="mono text-[10px] text-surface-500">
                gold: {data.metrics_primary_vortex.y_gold.toFixed(4)}
              </div>
            </div>
            <div>
              <div className="text-surface-500">ψ_min / (U·L)</div>
              <div className="mono text-surface-100">
                {data.metrics_primary_vortex.psi_meas.toFixed(5)}
              </div>
              <div className="mono text-[10px] text-surface-500">
                gold: {data.metrics_primary_vortex.psi_gold.toFixed(5)}
              </div>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 text-[11px]">
            <div className="rounded border border-surface-800 bg-surface-950/40 px-2 py-1.5">
              <div className="text-surface-500">2D 位置误差</div>
              <div className="mono text-surface-100">
                {data.metrics_primary_vortex.position_error.toFixed(5)}
                <span className={`ml-1.5 ${data.metrics_primary_vortex.position_pass ? "text-emerald-300" : "text-rose-300"}`}>
                  {data.metrics_primary_vortex.position_pass ? "✓" : "✗"}
                </span>
              </div>
              <div className="mono text-[10px] text-surface-500">
                tol ≤ {data.metrics_primary_vortex.position_tolerance.toFixed(3)}
              </div>
            </div>
            <div className="rounded border border-surface-800 bg-surface-950/40 px-2 py-1.5">
              <div className="text-surface-500">|ψ| 相对误差</div>
              <div className="mono text-surface-100">
                {data.metrics_primary_vortex.psi_error_pct.toFixed(2)}%
                <span className={`ml-1.5 ${data.metrics_primary_vortex.psi_pass ? "text-emerald-300" : "text-rose-300"}`}>
                  {data.metrics_primary_vortex.psi_pass ? "✓" : "✗"}
                </span>
              </div>
              <div className="mono text-[10px] text-surface-500">
                tol ≤ {data.metrics_primary_vortex.psi_tolerance_pct.toFixed(1)}%
              </div>
            </div>
          </div>
          {data.metrics_primary_vortex.signal_to_residual_ratio !== null && (
            <p className="mono mt-2 text-[10.5px] text-surface-500">
              SNR: |ψ_gold| / max-wall-residual ={" "}
              <span className={data.metrics_primary_vortex.signal_above_noise ? "text-emerald-300" : "text-rose-300"}>
                {data.metrics_primary_vortex.signal_to_residual_ratio.toFixed(1)}×
              </span>
              {" "}· {data.metrics_primary_vortex.signal_above_noise
                ? "信号远高于数值噪声（>3×），裁决可信"
                : "信号 ≤ 3× 数值噪声，裁决可能不可靠"}
            </p>
          )}
        </div>
      )}

      {/* D8 · Secondary vortices BL/BR — DEC-V61-050 batch 4.
          Corner-windowed ψ_max extraction on the same 129² grid used
          by D7. Ghia Table III Re=100 secondary rows. */}
      {data.metrics_secondary_vortices && data.paper_secondary_vortices && (
        <div className={`rounded-md border p-4 ${
          data.metrics_secondary_vortices.all_pass
            ? "border-emerald-900/40 bg-emerald-950/10"
            : "border-amber-900/40 bg-amber-950/10"
        }`}>
          <div className="mb-1 flex items-baseline gap-2">
            <span className={`mono text-[10.5px] font-semibold uppercase tracking-wider ${
              data.metrics_secondary_vortices.all_pass ? "text-emerald-300" : "text-amber-300"
            }`}>
              D8 · 角涡 BL + BR（独立观测量）
            </span>
            <span className={`mono inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-semibold ${
              data.metrics_secondary_vortices.all_pass
                ? "bg-emerald-900/40 text-emerald-300"
                : "bg-amber-900/40 text-amber-300"
            }`}>
              {data.metrics_secondary_vortices.n_pass}/{data.metrics_secondary_vortices.n_total}
            </span>
          </div>
          <p className="text-[13px] leading-relaxed text-surface-200">
            {data.paper_secondary_vortices.short} · 角域 ψ_max 提取（与主涡共享同一个 129² ψ 场，换不同的窗口 + mode='max'）。
            <span className="block mt-1 text-[11.5px] text-emerald-200/80">
              BL / BR 是与主涡<strong>反向旋转</strong>的小角涡（ψ 为正，主涡 ψ 为负）。强度比主涡小 5-6 个数量级，对网格分辨率极其敏感——容差放宽到 10% (相比主涡的 5%)。Re=100 时 TL 角涡不存在（Re≥1000 才出现）。
            </span>
          </p>
          {data.psi_wall_residuals && !data.metrics_secondary_vortices.all_pass && (
            <div className="mt-2 rounded border border-rose-900/50 bg-rose-950/30 px-3 py-2">
              <p className="mono text-[10.5px] font-semibold uppercase tracking-wider text-rose-300">
                诚实声明 · 信号低于数值噪声地板
              </p>
              <p className="mt-1 text-[11.5px] leading-relaxed text-surface-200">
                当前 ψ 提取用的是 trapezoidal <span className="mono">∫U_x dy'</span> + pyvista 重采样，在 129² 网格上墙面闭合残差 ψ_wall ≈{" "}
                <span className="mono text-rose-200">{data.psi_wall_residuals.max.toExponential(2)}</span>（非零 = 积分常数漂移 + 采样插值误差）。
                Ghia BL/BR 的 ψ 量级只有 <span className="mono text-rose-200">1e-6 到 1e-5</span>——<strong>信号本身比数值噪声还小 2-3 个数量级</strong>。
                argmax 找到的点坐标"恰好"落在 Ghia 点附近，不能当作物理复现，而是 argmax 在噪声主导场里的<strong>巧合</strong>。
                要真正验证 BL/BR 需要 Poisson 解（<span className="mono">∇²ψ = -ω_z</span> 且 ψ=0 边界）或 OpenFOAM 原生 ψ 场——均超出 DEC-V61-050 范围。
                {" "}D7 主涡 SNR ={" "}
                <span className="mono text-emerald-200">
                  {data.metrics_primary_vortex ? data.metrics_primary_vortex.signal_to_residual_ratio?.toFixed(1) : "—"}×
                </span>
                {" "}安全；D8 用作证据前必须有 signal {'>'} 3× residual 的提取方法。
              </p>
            </div>
          )}
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {data.metrics_secondary_vortices.eddies.map((eddy) => (
              <div
                key={eddy.name}
                className={`rounded border px-3 py-2 ${
                  eddy.all_pass
                    ? "border-surface-800 bg-surface-950/40"
                    : "border-amber-900/40 bg-amber-950/20"
                }`}
              >
                <div className="flex items-baseline justify-between">
                  <span className="mono text-[11px] font-semibold text-surface-100">
                    {eddy.name}
                  </span>
                  <span className={`mono text-[10px] ${eddy.all_pass ? "text-emerald-300" : "text-amber-300"}`}>
                    {eddy.all_pass ? "PASS" : "PARTIAL"}
                  </span>
                </div>
                <p className="text-[10.5px] text-surface-500">{eddy.description}</p>
                <div className="mt-1.5 grid grid-cols-3 gap-2 text-[10.5px]">
                  <div>
                    <div className="text-surface-500">x/L</div>
                    <div className="mono text-surface-100">{eddy.x_meas.toFixed(4)}</div>
                    <div className="mono text-[9.5px] text-surface-500">g: {eddy.x_gold.toFixed(4)}</div>
                  </div>
                  <div>
                    <div className="text-surface-500">y/L</div>
                    <div className="mono text-surface-100">{eddy.y_meas.toFixed(4)}</div>
                    <div className="mono text-[9.5px] text-surface-500">g: {eddy.y_gold.toFixed(4)}</div>
                  </div>
                  <div>
                    <div className="text-surface-500">ψ</div>
                    <div className="mono text-surface-100">{eddy.psi_meas.toExponential(3)}</div>
                    <div className="mono text-[9.5px] text-surface-500">g: {eddy.psi_gold.toExponential(3)}</div>
                  </div>
                </div>
                <div className="mt-1.5 flex justify-between text-[10px]">
                  <span className={eddy.position_pass ? "text-emerald-300" : "text-rose-300"}>
                    pos_err {eddy.position_error.toExponential(2)} {eddy.position_pass ? "✓" : "✗"}
                  </span>
                  <span className={eddy.psi_pass ? "text-emerald-300" : "text-rose-300"}>
                    |ψ|_err {eddy.psi_error_pct.toFixed(2)}% {eddy.psi_pass ? "✓" : "✗"}
                  </span>
                </div>
                {eddy.signal_to_residual_ratio !== null && (
                  <div className="mt-1 text-[10px]">
                    <span className="text-surface-500">SNR: </span>
                    <span className={`mono ${eddy.signal_above_noise ? "text-emerald-300" : "text-rose-300"}`}>
                      {eddy.signal_to_residual_ratio < 0.01
                        ? eddy.signal_to_residual_ratio.toExponential(2)
                        : eddy.signal_to_residual_ratio.toFixed(3)}×
                    </span>
                    <span className="text-surface-500"> · signal {eddy.signal_above_noise ? "> 3× noise ✓" : "< 3× noise ✗"}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
          <p className="mono mt-2 text-[10px] text-surface-500">
            tol: pos ≤ {data.metrics_secondary_vortices.position_tolerance.toFixed(3)} · |ψ| ≤ {data.metrics_secondary_vortices.psi_tolerance_pct.toFixed(1)}%
          </p>
        </div>
      )}

      {/* Final closure footer — honest assessment of which Ghia
          observables are validated at what strength level. Codex round 1
          MED #2 / HIGH: the original footer claimed FULLY_SATISFIED for
          all 4 Ghia observables, but D8 BL/BR signals are 2-3 decades
          below the ∫U_x dy' wall-closure residual — argmax coincidences
          in a noise-dominated field, not validated physics. Post-fix,
          the footer distinguishes present-but-validated vs present-but-
          noise-dominated vs missing. */}
      {(() => {
        const missing: string[] = [];
        if (!data.metrics_v_centerline) missing.push("D6 v_centerline");
        if (!data.metrics_primary_vortex) missing.push("D7 primary vortex");
        if (!data.metrics_secondary_vortices) missing.push("D8 secondary vortices");
        if (missing.length > 0) {
          return (
            <div className="rounded-md border border-amber-900/40 bg-amber-950/10 p-4">
              <p className="mb-1 mono text-[10.5px] font-semibold uppercase tracking-wider text-amber-300">
                降级模式 · 部分 Ghia 观测量缺失
              </p>
              <p className="text-[12px] leading-relaxed text-surface-300">
                本次 audit run 以下维度未返回 metrics，当前 Compare tab 仅展示已有的维度：
                <span className="mono block mt-1 text-amber-200">
                  缺失: {missing.join(" · ")}
                </span>
                <span className="block mt-1 text-[11px] text-surface-400">
                  常见原因：后端缺 pyvista 且 <span className="mono">.psi_cache</span> 未预生成（需跑 <span className="mono">python3.11 ui/backend/services/psi_extraction.py</span>）；VTK 文件缺失或格式变更；gold YAML schema 漂移导致 loader 拒绝。
                </span>
              </p>
            </div>
          );
        }
        // Codex round 3 MED: the fail branch must only fire when there
        // is genuinely above-noise deviation — `any_above_noise_fail` =
        // "at least one eddy is above noise AND failed tolerance". That
        // excludes the mixed state where one eddy passes above noise and
        // the other is noise-floor; in that case `noise` is the honest
        // label. State matrix:
        //   ok:    all_pass && all_above_noise → 4/4 validated
        //   fail:  any_above_noise_fail → genuine above-noise deviation
        //   noise: otherwise (!all_pass && !any_above_noise_fail)
        const d8 = data.metrics_secondary_vortices!;
        const d8_all_pass = d8.all_pass === true;
        const d8_all_above_noise = d8.all_above_noise === true;
        const d8_any_fail_above_noise = d8.any_above_noise_fail === true;
        const validated_count = 3 + (d8_all_pass && d8_all_above_noise ? 1 : 0);
        const footer_tone: "ok" | "noise" | "fail" =
          d8_all_pass && d8_all_above_noise
            ? "ok"
            : d8_any_fail_above_noise
              ? "fail"
              : "noise";
        return (
          <div className={`rounded-md border p-4 ${footer_tone === "ok" ? "border-emerald-900/40 bg-emerald-950/10" : footer_tone === "noise" ? "border-amber-900/40 bg-amber-950/10" : "border-red-900/40 bg-red-950/10"}`}>
            <p className={`mb-1 mono text-[10.5px] font-semibold uppercase tracking-wider ${footer_tone === "ok" ? "text-emerald-300" : footer_tone === "noise" ? "text-amber-300" : "text-red-300"}`}>
              DEC-V61-050 closure · {validated_count} / 4 Ghia 观测量已验证（诚实等级）
            </p>
            <p className="text-[12px] leading-relaxed text-surface-300">
              <strong className="text-emerald-200">D2-D4（u_centerline Table I）· D6（v_centerline Table II）· D7（primary vortex Table III 主行）</strong> — 三个观测量的信号都远高于数值噪声地板，裁决可信，physics_contract 生效。
              {footer_tone === "ok" && (
                <span className="block mt-1">
                  <strong className="text-emerald-200">D8 BL/BR（Table III secondary 行）</strong>：ψ 信号已高于墙面闭合残差，argmax 裁决来自物理而非噪声，contract_status = <span className="mono text-emerald-200">FULLY_SATISFIED_ALL_4_GHIA_TABLES</span>。
                </span>
              )}
              {footer_tone === "noise" && (
                <span className="block mt-1">
                  <strong className="text-amber-200">D8 BL/BR（Table III secondary 行）</strong>：ψ 量级 <span className="mono">1e-6 ~ 1e-5</span> 低于 <span className="mono">∫U_x dy'</span> 在 129² 墙面的闭合残差 (<span className="mono">{data.psi_wall_residuals ? data.psi_wall_residuals.max.toExponential(2) : "~3e-3"}</span>)，<strong>argmax 找到的点是噪声巧合，不是物理复现</strong>。contract_status 为 <span className="mono text-amber-200">SATISFIED_FOR_U_V_AND_PRIMARY_VORTEX_NOT_SECONDARIES</span>。
                </span>
              )}
              {footer_tone === "fail" && (
                <span className="block mt-1">
                  <strong className="text-red-200">D8 BL/BR（Table III secondary 行）</strong>：至少一个角涡的 ψ 信号已高于墙面残差 (<span className="mono">{data.psi_wall_residuals ? data.psi_wall_residuals.max.toExponential(2) : "~3e-3"}</span>) 但未通过 tolerance，属于真实物理偏差 (非噪声巧合)。检查 mesh resolution / 流场对称性 / audit fixture 是否过期。
                </span>
              )}
              <span className="block mt-1 text-[11px] text-surface-500">
                角涡真正验证需后续 DEC：Poisson 解 <span className="mono">∇²ψ = -ω_z</span>（ψ=0 边界消除积分常数漂移）或 OpenFOAM 原生 ψ 场采样。当前 pipeline 在诚实等级停于 <span className="mono">{validated_count} / 4</span> — 这个 D8 banner 本身是 DEC-V61-050 Codex round 1 MED 补丁的结果。
              </span>
            </p>
          </div>
        );
      })()}
    </section>
  );
}

function StatBlock({
  label,
  subLabel,
  value,
  unit,
  quantity,
  accent,
}: {
  label: string;
  subLabel: string;
  value: number | null;
  unit: string;
  quantity: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-5 py-4 ${
        accent ? "border-sky-800/60 bg-sky-950/20" : "border-surface-800 bg-surface-900/40"
      }`}
    >
      <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">{label}</p>
      <p className="mono mt-3 text-[28px] font-medium leading-none text-surface-100">
        {value === null ? "—" : value.toPrecision(4)}
      </p>
      <div className="mt-3 flex items-baseline justify-between text-[12px] text-surface-400">
        <span className="mono">{quantity}</span>
        <span>{unit || "—"}</span>
      </div>
      <p className="mt-2 text-[11px] leading-snug text-surface-500">{subLabel}</p>
    </div>
  );
}

function ToleranceBand({
  goldValue,
  lower,
  upper,
  measured,
}: {
  goldValue: number;
  tolerancePct: number;
  lower: number;
  upper: number;
  measured: number | null;
}) {
  // Compute a display range that includes gold, both tolerance bounds,
  // and measured — with sensible margin. Clamp width to avoid division
  // by zero for PASS cases where measured ≈ gold.
  const values = [lower, upper, goldValue, measured].filter(
    (v): v is number => v !== null && Number.isFinite(v),
  );
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = Math.max(rawMax - rawMin, Math.abs(goldValue) * 0.3, 0.01);
  const padding = span * 0.2;
  const displayMin = rawMin - padding;
  const displayMax = rawMax + padding;
  const toPct = (v: number) =>
    ((v - displayMin) / (displayMax - displayMin)) * 100;

  const goldX = toPct(goldValue);
  const lowerX = toPct(lower);
  const upperX = toPct(upper);
  const measuredX = measured !== null ? toPct(measured) : null;
  const measuredInside = measured !== null && measured >= lower && measured <= upper;

  return (
    <div className="relative mt-1">
      {/* Track */}
      <div className="relative h-2 rounded-full bg-surface-800">
        {/* Tolerance band shading */}
        <div
          className="absolute top-0 h-2 rounded-full bg-sky-600/30"
          style={{ left: `${lowerX}%`, width: `${upperX - lowerX}%` }}
        />
      </div>
      {/* Gold marker */}
      <div
        className="absolute -top-1 flex h-4 -translate-x-1/2 flex-col items-center"
        style={{ left: `${goldX}%` }}
      >
        <div className="h-4 w-px bg-surface-300" />
      </div>
      <div
        className="absolute top-5 -translate-x-1/2 mono text-[10px] text-surface-400"
        style={{ left: `${goldX}%` }}
      >
        gold
      </div>
      {/* Measurement marker (only if present) */}
      {measuredX !== null && (
        <>
          <div
            className="absolute -top-2 h-6 w-0.5 -translate-x-1/2 rounded-full"
            style={{
              left: `${Math.max(0, Math.min(100, measuredX))}%`,
              background: measuredInside ? "#4ade80" : "#f87171",
            }}
          />
          <div
            className="absolute top-5 -translate-x-1/2 mono text-[10px]"
            style={{
              left: `${Math.max(0, Math.min(100, measuredX))}%`,
              color: measuredInside ? "#4ade80" : "#f87171",
            }}
          >
            measured
          </div>
        </>
      )}
      {/* Out-of-range indicator */}
      {measuredX !== null && (measuredX < 0 || measuredX > 100) && (
        <div
          className={`absolute -top-3 mono text-[10px] ${measuredX < 0 ? "left-0" : "right-0"} text-contract-fail`}
        >
          {measuredX < 0 ? "← 远低于" : "远高于 →"}
        </div>
      )}
    </div>
  );
}

// --- Mesh tab (interactive grid-convergence slider) --------------------------

