// Phase 7f scientific CFD-vs-Gold comparison report block.
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import { useQuery } from "@tanstack/react-query";

import { ApiError } from "@/api/client";

import { ErrorCallout } from "./shared";

// --- Phase 7f: Scientific CFD-vs-Gold comparison report section -----------

export type ComparisonReportContext = {
  // Shared across both modes.
  case_id: string;
  case_display_name?: string;
  run_label: string;
  timestamp: string;
  // Tier C marker: if true, this is a visual-only reduced context with
  // no gold-overlay / verdict / metrics / paper. Renders still populated.
  visual_only?: boolean;
  // Full (LDC gold-overlay) fields:
  verdict: "PASS" | "PARTIAL" | "FAIL" | string | null;
  verdict_subtitle?: string;
  subtitle?: string;
  metrics?: {
    max_dev_pct: number;
    l2: number;
    linf: number;
    rms: number;
    n_pass: number;
    n_total: number;
    // DEC-V61-049 batch C1 — backend already computes this array in
    // comparison_report.py:_compute_metrics (line 210) but the frontend
    // type previously omitted it, so the pointwise bars could only be
    // viewed via the rendered PNG. Adding it lets CompareTab render a
    // native live chart if we want to (currently still PNG-first for
    // simplicity; field is populated regardless).
    per_point_dev_pct?: number[];
  } | null;
  // DEC-V61-050 batch 1 — v_centerline observable (Ghia Table II).
  // Optional: null when the case has no v_centerline gold block or
  // the audit fixture has no vCenterline.xy. For LDC post-batch-1 it
  // is populated from the post-hoc VTK interpolation onto Ghia's 17
  // native x points on y=0.5 horizontal centerline.
  metrics_v_centerline?: {
    max_dev_pct: number;
    l2: number;
    linf: number;
    rms: number;
    n_pass: number;
    n_total: number;
    per_point_dev_pct?: number[];
  } | null;
  // DEC-V61-050 batch 3: primary vortex (x_c, y_c, ψ_min) from 2D
  // argmin of ψ. Fields match comparison_report.py exactly.
  metrics_primary_vortex?: {
    x_meas: number;
    y_meas: number;
    psi_meas: number;
    x_gold: number;
    y_gold: number;
    psi_gold: number;
    position_error: number;
    psi_error_pct: number;
    position_tolerance: number;
    psi_tolerance_pct: number;
    position_pass: boolean;
    psi_pass: boolean;
    all_pass: boolean;
    signal_to_residual_ratio: number | null;
    signal_above_noise: boolean;
  } | null;
  paper_primary_vortex?: {
    source: string;
    doi?: string;
    short: string;
    position_tolerance: number;
    psi_tolerance_pct: number;
  } | null;
  // DEC-V61-050 batch 4: secondary corner eddies (BL + BR) from
  // Ghia Table III cells 3-4. Mirror shape of primary_vortex but
  // as a list so Re≥1000 TL can be added without another key.
  metrics_secondary_vortices?: {
    eddies: {
      name: string;
      description: string;
      x_meas: number;
      y_meas: number;
      psi_meas: number;
      x_gold: number;
      y_gold: number;
      psi_gold: number;
      position_error: number;
      psi_error_pct: number;
      position_pass: boolean;
      psi_pass: boolean;
      all_pass: boolean;
      signal_to_residual_ratio: number | null;
      signal_above_noise: boolean;
    }[];
    position_tolerance: number;
    psi_tolerance_pct: number;
    all_pass: boolean;
    n_pass: number;
    n_total: number;
    all_above_noise: boolean;
    any_above_noise: boolean;
    any_above_noise_fail: boolean;
  } | null;
  psi_wall_residuals?: {
    left: number;
    right: number;
    bottom: number;
    top: number;
    max: number;
    L: number;
  } | null;
  paper_secondary_vortices?: {
    source: string;
    doi?: string;
    short: string;
    position_tolerance: number;
    psi_tolerance_pct: number;
  } | null;
  paper?: {
    title: string;
    source: string;
    doi?: string;
    short: string;
    gold_count: number;
    tolerance_pct: number;
  } | null;
  paper_v_centerline?: {
    source: string;
    doi?: string;
    short: string;
    gold_count: number;
    tolerance_pct: number;
  } | null;
  renders: {
    profile_png_rel?: string;
    pointwise_png_rel?: string;
    contour_png_rel: string;
    residuals_png_rel: string;
  };
  meta?: {
    commit_sha: string;
    report_generated_at: string;
  };
  // DEC-V61-049 batch C1 — grid convergence + GCI + residual info are
  // all already returned by comparison_report.py build_report_context
  // (lines 516, 524-526) but were not previously surfaced in the
  // frontend type. CompareTab now consumes them for the grid-convergence
  // dim and the residual/iteration dim.
  // Shapes match comparison_report.py exactly:
  // - grid_conv row: _load_grid_convergence (line 275 at 2026-04-23)
  // - gci: _gci_to_template_dict (line 290)
  // - residual_info: _parse_residuals_csv (line 239)
  grid_conv?: Array<{
    mesh: string;
    value: number;
    dev_pct: number;
    verdict: "PASS" | "WARN" | "FAIL";
    verdict_class: "pass" | "warn" | "fail";
  }> | null;
  grid_conv_note?: string | null;
  gci?: {
    coarse_label: string;
    coarse_n: number;
    coarse_value: number;
    medium_label: string;
    medium_n: number;
    medium_value: number;
    fine_label: string;
    fine_n: number;
    fine_value: number;
    r_21: number;
    r_32: number;
    p_obs: number | null;
    f_extrapolated: number | null;
    gci_21_pct: number | null;
    gci_32_pct: number | null;
    asymptotic_range_ok: boolean;
    note: string | null;
  } | null;
  residual_info?: {
    total_iter: number;
    final_ux: number | null;
    note: string | null;
  } | null;
  // Visual-only top-level fields:
  solver?: string;
  commit_sha?: string;
  // DEC-V61-052 Batch D: BFS scalar-anchor (Xr/H) Compare-tab card.
  // Populated only when case_id == "backward_facing_step" and both the
  // audit measurement YAML and the gold anchor are present. Other
  // visual-only cases see null here until their own anchors are wired.
  metrics_reattachment?: {
    quantity: string;
    symbol: string;
    actual: number;
    expected: number;
    deviation_pct: number;
    tolerance_pct: number;
    within_tolerance: boolean;
    method?: string | null;
  } | null;
  paper_reattachment?: {
    source: string;
    doi?: string;
    short: string;
    tolerance_pct: number;
  } | null;
  // DEC-V61-053 Batch D: cylinder 4-scalar anchor (Williamson 1996).
  // All 4 metrics + matching paper blocks are null when the audit fixture
  // is stale (measurement.quantity=U_max_approx, no secondary_scalars).
  // Lighten/flatten shape mirrors metrics_reattachment so the BFS card
  // pattern can be reused × 3 for D-St / D-Cd / D-Cl_rms.
  metrics_strouhal?: {
    quantity: string;
    symbol: string;
    actual: number;
    expected: number;
    deviation_pct: number;
    tolerance_pct: number;
    within_tolerance: boolean;
    method?: string | null;
  } | null;
  paper_strouhal?: {
    source: string;
    doi?: string;
    short: string;
    tolerance_pct: number;
  } | null;
  metrics_cd_mean?: {
    quantity: string;
    symbol: string;
    actual: number;
    expected: number;
    deviation_pct: number;
    tolerance_pct: number;
    within_tolerance: boolean;
    method?: string | null;
  } | null;
  paper_cd_mean?: {
    source: string;
    doi?: string;
    short: string;
    tolerance_pct: number;
  } | null;
  metrics_cl_rms?: {
    quantity: string;
    symbol: string;
    actual: number;
    expected: number;
    deviation_pct: number;
    tolerance_pct: number;
    within_tolerance: boolean;
    method?: string | null;
  } | null;
  paper_cl_rms?: {
    source: string;
    doi?: string;
    short: string;
    tolerance_pct: number;
  } | null;
  // Profile observable (4 stations at x/D ∈ {1, 2, 3, 5}).
  metrics_u_centerline?: {
    quantity: string;
    symbol: string;
    stations: {
      x_D: number;
      actual: number;
      expected: number;
      deviation_pct: number;
      within_tolerance: boolean;
    }[];
    tolerance_pct: number;
    all_within_tolerance: boolean;
    method?: string | null;
  } | null;
  paper_u_centerline?: {
    source: string;
    doi?: string;
    short: string;
    tolerance_pct: number;
  } | null;
  // DEC-V61-057 Stage D: differential_heated_cavity 5-observable Compare-tab
  // block (4 HARD_GATED + 1 PROVISIONAL_ADVISORY).
  // null when fixture is missing the measurement YAML or the gold YAML can't
  // be parsed; pending entries (actual=null) when secondary_scalars haven't
  // been populated by Stage E live run yet — UI renders them as placeholder
  // cards so users see the 5-observable promise instead of empty space.
  metrics_dhc?: {
    observables: {
      label: string;
      label_zh: string;
      symbol: string;
      name: string;
      actual: number | null;
      expected: number | null;
      deviation_pct: number | null;
      tolerance_pct: number;
      within_tolerance: boolean | null;
      gate_status: string;
      family: string;
      role: string;
      source_table: string;
      pending?: boolean;
    }[];
    hard_gated_count: number;
    advisory_count: number;
    source: string;
    literature_doi: string;
    short: string;
  } | null;
};

export function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  const runLabel = "audit_real_run";
  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
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

  if (isLoading) return null; // quiet during fetch
  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
  // → silent hide) from 5xx / malformed JSON / network errors (show banner
  // so regressions are visible, not silently swallowed).
  if (error) {
    const status = error instanceof ApiError ? error.status : 0;
    if (status === 404 || status === 400) return null; // case not opted-in
    return (
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
          <p className="text-[11px] text-surface-500">报告服务暂不可用</p>
        </div>
        <ErrorCallout
          message={`无法加载对比报告 (HTTP ${status || "network"}): ${error.message.slice(0, 200)}`}
        />
      </section>
    );
  }
  if (!data) return null;

  // DEC-V61-034 Tier C: visual-only branch. No verdict card / iframe; just
  // show the real contour + residuals PNGs directly so every case has real
  // OpenFOAM evidence on the /learn page.
  if (data.visual_only) {
    // Serve PNGs via the /api route (with path-containment defense) rather
    // than raw /reports paths — keeps the visible URL under the signed API
    // surface and avoids needing a FastAPI StaticFiles mount.
    const renderUrl = (rel: string | undefined, basename: string) => {
      if (!rel) return null;
      return `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runLabel)}/renders/${basename}`;
    };
    const contourUrl = renderUrl(data.renders.contour_png_rel, "contour_u_magnitude.png");
    const residualsUrl = renderUrl(data.renders.residuals_png_rel, "residuals.png");
    return (
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="card-title">
            仿真场图 · Visual evidence only · 未完成金标准验证
          </h2>
          <p className="text-[11px] text-surface-500">
            OpenFOAM {data.solver ?? "solver"} · audit_real_run ·
            commit {data.commit_sha ?? ""}
          </p>
        </div>
        {/* DEC-V61-047 round-1 F1 blocker fix: the prior copy hardcoded
            "audit_real_run verdict 为 FAIL" in visual-only mode, but the
            backend context (`comparison_report._build_visual_only_context`)
            explicitly returns verdict=None in this branch and some run
            fixtures declare expected_verdict: PASS (cylinder, plane_channel).
            The hardcoded FAIL was a demonstrable false negative on those
            cases. Reframe as "Tier C: visual evidence only, no automated
            gold comparison yet" — honest about what the user is looking at. */}
        <div className="mb-3 rounded-md border border-amber-600/50 bg-amber-950/30 p-3 text-[12px] text-amber-100">
          <span className="font-semibold text-amber-300">Tier C · 过程证据，未做自动化金标准比对</span>
          ：下方 |U| 速度云图 + 残差曲线来自实际 OpenFOAM 求解器（
          <code className="mono text-amber-200">audit_real_run</code> ·
          commit <code className="mono text-amber-200">{data.commit_sha ?? ""}</code>）。
          本 case 当前处于 visual-only 层——没有跑自动化 gold-overlay / metrics /
          GCI（详见 Run Inspector → audit_real_run 的 physics_contract 与 audit_concerns）。
          云图 + 残差仅作为<strong> 过程证据 </strong>展示求解器跑通了，
          <strong>不等于自动化金标准通过也不等于失败</strong>。Tier B 全金标准覆盖在
          Phase 7c Sprint 2 之后上线。
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {contourUrl && (
            <div className="rounded-md border border-surface-800 bg-white p-2">
              <div className="mb-1 text-[11px] font-semibold text-surface-500 px-1">
                |U| 速度幅值云图
              </div>
              <img src={contourUrl} alt={`${caseId} |U| contour`} className="w-full" />
            </div>
          )}
          {residualsUrl && (
            <div className="rounded-md border border-surface-800 bg-white p-2">
              <div className="mb-1 text-[11px] font-semibold text-surface-500 px-1">
                残差收敛历史 (log scale)
              </div>
              <img src={residualsUrl} alt={`${caseId} residuals`} className="w-full" />
            </div>
          )}
          {!contourUrl && !residualsUrl && (
            <p className="text-[12px] text-surface-500">
              (artifact capture empty — re-run phase5 audit script for this case)
            </p>
          )}
        </div>
      </section>
    );
  }

  // Gold-overlay mode (LDC today). Verdict card + iframe 8-section report.
  const verdictColor =
    data.verdict === "PASS"
      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
      : data.verdict === "PARTIAL"
      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";

  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
    runLabel,
  )}/comparison-report`;
  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
    runLabel,
  )}/comparison-report.pdf`;

  // Defensive: if gold-overlay shape is missing fields, bail silently.
  if (!data.metrics || !data.meta) return null;

  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
        <p className="text-[11px] text-surface-500">
          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
        </p>
      </div>

      <div
        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
        role="status"
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
              Verdict
            </div>
            <div className="mt-1 text-[22px] font-bold leading-tight">
              {data.verdict}
            </div>
            <div className="mt-1 text-[12px] text-surface-200">
              {data.verdict_subtitle}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
            <div>
              <div className="text-surface-400">max |dev|</div>
              <div className="mono text-surface-100">
                {data.metrics.max_dev_pct.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-surface-400">n_pass</div>
              <div className="mono text-surface-100">
                {data.metrics.n_pass} / {data.metrics.n_total}
              </div>
            </div>
            <div>
              <div className="text-surface-400">L²</div>
              <div className="mono text-surface-100">
                {data.metrics.l2.toFixed(4)}
              </div>
            </div>
            <div>
              <div className="text-surface-400">L∞</div>
              <div className="mono text-surface-100">
                {data.metrics.linf.toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-2 text-[12px]">
        <a
          href={reportHtmlUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
        >
          ↗ 新窗口打开完整报告
        </a>
        <a
          href={reportPdfUrl}
          download
          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
        >
          ↓ 下载 PDF
        </a>
      </div>

      <div className="overflow-hidden rounded-md border border-surface-800 bg-white">
        <iframe
          title="CFD vs Gold comparison report"
          src={reportHtmlUrl}
          className="h-[1400px] w-full border-0"
          sandbox=""
        />
      </div>
    </section>
  );
}
