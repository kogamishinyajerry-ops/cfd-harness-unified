import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { getFlowFields } from "@/data/flowFields";
import { getLearnCase } from "@/data/learnCases";
import type {
  ContractStatus,
  Precondition,
  RunCategory,
  RunDescriptor,
  ValidationReport,
} from "@/types/validation";

// Student-facing case detail. Four tabs:
//   Story    — default. physics, canonical reference, why validation matters
//   Compare  — gold vs measurement, tolerance band. Framed as a learning moment
//   Run      — residuals chart placeholder (real streaming lives in Pro Workbench)
//   Advanced — decision trail + link to audit package (the pro-evidence surface)
//
// The backend ValidationReport fetch is shared; sub-tabs derive their views
// from that single record so the student can flip between them without
// re-fetching.

type TabId = "story" | "compare" | "mesh" | "run" | "advanced";

const TABS: { id: TabId; label_zh: string; label_en: string }[] = [
  { id: "story", label_zh: "故事", label_en: "Story" },
  { id: "compare", label_zh: "对比", label_en: "Compare" },
  { id: "mesh", label_zh: "网格", label_en: "Mesh" },
  { id: "run", label_zh: "运行", label_en: "Run" },
  { id: "advanced", label_zh: "进阶", label_en: "Advanced" },
];

// Cases with a curated grid-convergence sweep (4 meshes each). Every
// case in the /learn catalog now has one. If a new case is added,
// author 4 mesh_N fixtures and register its density labels here.
const GRID_CONVERGENCE_CASES: Record<
  string,
  { meshLabel: string; densities: { id: string; label: string; n: number }[] }
> = {
  lid_driven_cavity: {
    meshLabel: "uniform grid N×N",
    densities: [
      { id: "mesh_20", label: "20²", n: 400 },
      { id: "mesh_40", label: "40²", n: 1600 },
      { id: "mesh_80", label: "80²", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  turbulent_flat_plate: {
    meshLabel: "wall-normal cells",
    densities: [
      { id: "mesh_20", label: "20 y-cells", n: 20 },
      { id: "mesh_40", label: "40 y-cells", n: 40 },
      { id: "mesh_80", label: "80 y-cells + 4:1", n: 80 },
      { id: "mesh_160", label: "160 y-cells", n: 160 },
    ],
  },
  backward_facing_step: {
    meshLabel: "recirculation cells",
    densities: [
      { id: "mesh_20", label: "20 cells", n: 20 },
      { id: "mesh_40", label: "40 cells", n: 40 },
      { id: "mesh_80", label: "80 cells", n: 80 },
      { id: "mesh_160", label: "160 cells", n: 160 },
    ],
  },
  circular_cylinder_wake: {
    meshLabel: "azimuthal cells around cylinder",
    densities: [
      { id: "mesh_20", label: "20 azim", n: 20 },
      { id: "mesh_40", label: "40 azim", n: 40 },
      { id: "mesh_80", label: "80 azim", n: 80 },
      { id: "mesh_160", label: "160 azim", n: 160 },
    ],
  },
  duct_flow: {
    meshLabel: "cross-section cells",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  differential_heated_cavity: {
    meshLabel: "square cavity N×N + wall grading",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 1.5:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
  plane_channel_flow: {
    // Honest labels: the live adapter path is laminar icoFoam at Re_bulk=5600
    // (see knowledge/gold_standards/plane_channel_flow.yaml physics_contract —
    // contract_status is INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE
    // because laminar N-S cannot reproduce Kim 1987 Re_τ=180 turbulent DNS).
    // Earlier mesh labels ("WR-LES" / "DNS") implied the solver could switch
    // regimes at higher density — it cannot. Labels now just describe mesh
    // count so the UI does not front-run the solver reality.
    meshLabel: "isotropic cubed cells (laminar icoFoam; aspirational turbulent solver path not yet wired)",
    densities: [
      { id: "mesh_20", label: "20³ cells", n: 8000 },
      { id: "mesh_40", label: "40³ cells", n: 64000 },
      { id: "mesh_80", label: "80³ cells", n: 512000 },
      { id: "mesh_160", label: "160³ cells", n: 4096000 },
    ],
  },
  impinging_jet: {
    meshLabel: "radial cells in stagnation region",
    densities: [
      { id: "mesh_20", label: "20 rad", n: 20 },
      { id: "mesh_40", label: "40 rad + 2:1", n: 40 },
      { id: "mesh_80", label: "80 rad + 4:1", n: 80 },
      { id: "mesh_160", label: "160 rad", n: 160 },
    ],
  },
  naca0012_airfoil: {
    meshLabel: "surface cells per side",
    densities: [
      { id: "mesh_20", label: "20 surf + 8-chord", n: 20 },
      { id: "mesh_40", label: "40 surf + 15-chord", n: 40 },
      { id: "mesh_80", label: "80 surf + 40-chord", n: 80 },
      { id: "mesh_160", label: "160 surf", n: 160 },
    ],
  },
  rayleigh_benard_convection: {
    meshLabel: "square cavity + wall packing",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
};

const STATUS_TEXT: Record<ContractStatus, string> = {
  PASS: "对齐黄金标准",
  HAZARD: "落入带内，但可能是 silent-pass",
  FAIL: "偏离了 tolerance band",
  UNKNOWN: "尚无可对比的测量值",
};

const STATUS_CLASS: Record<ContractStatus, string> = {
  PASS: "text-contract-pass",
  HAZARD: "text-contract-hazard",
  FAIL: "text-contract-fail",
  UNKNOWN: "text-surface-400",
};

const isTabId = (v: string | null): v is TabId =>
  v === "story" ||
  v === "compare" ||
  v === "mesh" ||
  v === "run" ||
  v === "advanced";

export function LearnCaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const tab: TabId = isTabId(rawTab) ? rawTab : "story";
  const setTab = (next: TabId) => {
    const params = new URLSearchParams(searchParams);
    if (next === "story") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  const learnCase = caseId ? getLearnCase(caseId) : undefined;
  const runId = searchParams.get("run") || undefined;

  const { data: report, error } = useQuery<ValidationReport, ApiError>({
    queryKey: ["validation-report", caseId, runId ?? "default"],
    queryFn: () => api.getValidationReport(caseId!, runId),
    enabled: !!caseId,
    retry: false,
  });

  const { data: runs } = useQuery<RunDescriptor[], ApiError>({
    queryKey: ["case-runs", caseId],
    queryFn: () => api.listCaseRuns(caseId!),
    enabled: !!caseId,
    retry: false,
  });

  const setRunId = (nextRun: string | null) => {
    const params = new URLSearchParams(searchParams);
    if (nextRun) params.set("run", nextRun);
    else params.delete("run");
    setSearchParams(params, { replace: true });
  };

  if (!caseId || !learnCase) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-surface-400">
        <p>找不到这个案例。</p>
        <Link to="/learn" className="mt-4 inline-block text-sky-400 hover:text-sky-300">
          ← 回到目录
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 pt-8 pb-16">
      {/* Breadcrumb + case-export + Pro Workbench switch */}
      <nav className="mb-6 flex items-center justify-between gap-3 text-[12px] text-surface-500">
        <div>
          <Link to="/learn" className="hover:text-surface-300">
            目录
          </Link>
          <span className="mx-2 text-surface-700">/</span>
          <span className="mono text-surface-400">{caseId}</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`/api/cases/${caseId}/export`}
            download={`${caseId}_reference.zip`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-emerald-700/60 hover:bg-surface-900 hover:text-emerald-300"
            title="Download a reference bundle: gold standard YAML, validation contract, reproduction README"
          >
            <span>下载参考包</span>
            <span className="mono text-surface-600 group-hover:text-emerald-400">
              .zip ↓
            </span>
          </a>
          <Link
            to={`/audit-package?case=${encodeURIComponent(caseId ?? "")}&run=audit_real_run`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-amber-700/60 hover:bg-surface-900 hover:text-amber-300"
            title="Build a signed audit package from the real-solver audit_real_run fixture (HMAC-signed zip + manifest + html + pdf + sig)"
          >
            <span>签名审计包</span>
            <span className="mono text-surface-600 group-hover:text-amber-400">
              HMAC ↓
            </span>
          </Link>
          <Link
            to={`/cases/${caseId}/report`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-sky-700/60 hover:bg-surface-900 hover:text-sky-300"
            title="Switch to the evidence-heavy audit surface (Validation Report, Decisions Queue, Audit Package)"
          >
            <span>进入专业工作台</span>
            <span className="mono text-surface-600 group-hover:text-sky-400">
              Pro Workbench →
            </span>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <header className="mb-8 grid gap-6 md:grid-cols-[1fr_240px]">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-surface-500">
            {learnCase.canonical_ref}
          </p>
          <h1 className="mt-1.5 text-3xl font-semibold leading-tight text-surface-100">
            {learnCase.headline_zh}
          </h1>
          <p className="mt-1 text-[13px] text-surface-400">
            {learnCase.displayName} · {learnCase.headline_en}
          </p>
          <p className="mt-4 text-[15px] leading-relaxed text-surface-300">
            {learnCase.teaser_zh}
          </p>
        </div>
        <div className="flex items-center rounded-lg border border-surface-800 bg-gradient-to-br from-surface-900 to-surface-950 p-4">
          <CaseIllustration caseId={caseId} className="h-auto w-full text-surface-100" />
        </div>
      </header>

      {/* Tab nav */}
      <div className="sticky top-0 -mx-6 mb-8 border-b border-surface-800 bg-surface-950/80 px-6 py-2 backdrop-blur">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-sm px-3 py-1.5 text-[13px] transition-colors ${
                tab === t.id
                  ? "bg-surface-800 text-surface-100"
                  : "text-surface-400 hover:bg-surface-900 hover:text-surface-200"
              }`}
            >
              {t.label_zh}
              <span className="ml-1.5 text-[10px] uppercase tracking-wider text-surface-600">
                {t.label_en}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab panels */}
      {tab === "story" && <StoryTab caseId={caseId} report={report} />}
      {tab === "compare" && (
        <CompareTab
          caseId={caseId}
          report={report}
          error={error}
          runs={runs ?? []}
          activeRunId={runId}
          onSelectRun={setRunId}
        />
      )}
      {tab === "mesh" && <MeshTab caseId={caseId} />}
      {tab === "run" && <RunTab caseId={caseId} />}
      {tab === "advanced" && <AdvancedTab caseId={caseId} report={report} />}
    </div>
  );
}

// --- Story tab ----------------------------------------------------------------

function StoryTab({
  caseId,
  report,
}: {
  caseId: string;
  report: ValidationReport | undefined;
}) {
  const learnCase = getLearnCase(caseId)!;
  const flowFields = getFlowFields(caseId);
  return (
    <div className="space-y-8">
      {/* DEC-V61-046 round-1 R1-M2 + R2-M7: surface physics_contract.contract_status
          + preconditions summary ABOVE the PASS/HAZARD/FAIL tile. The three-state
          verdict alone reads as "the tool can't even pass its own tests"; what
          a serious reviewer actually wants to see is the *contract* — what the
          gold claims, what preconditions the adapter satisfies or doesn't, and
          the explicit partial/false labels from the YAML. */}
      <PhysicsContractPanel report={report} />

      <section>
        <h2 className="card-title mb-3">这个问题是什么</h2>
        <ul className="space-y-2 text-[14px] leading-relaxed text-surface-200">
          {learnCase.physics_bullets_zh.map((b, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-sky-400" aria-hidden />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Phase 7f + DEC-V61-034: live CFD-vs-Gold comparison report with real
          OpenFOAM contour + residuals. Positioned BEFORE literature-reference
          block so the reader sees simulation output first. Gracefully hidden
          for cases not yet opted-in. */}
      <ScientificComparisonReportSection caseId={caseId} />

      {flowFields.length > 0 && (
        <section>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="card-title">文献参考图 · Literature reference</h2>
            <p className="text-[11px] text-surface-500">
              每张图都直接来自文献精确解或公开实验表格（对照基准）
            </p>
          </div>
          <div className="space-y-4">
            {flowFields.map((ff) => (
              <figure
                key={ff.src}
                className="overflow-hidden rounded-md border border-surface-800 bg-surface-900/30"
              >
                <img
                  src={ff.src}
                  alt={ff.caption_zh}
                  className="w-full max-w-full"
                  loading="lazy"
                />
                <figcaption className="border-t border-surface-800 px-4 py-3">
                  <p className="text-[13px] text-surface-200">{ff.caption_zh}</p>
                  <p className="mono mt-1.5 text-[10px] leading-relaxed text-surface-500">
                    provenance: {ff.provenance}
                  </p>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="card-title mb-3">为什么要做验证</h2>
        <p className="text-[14px] leading-relaxed text-surface-200">
          {learnCase.why_validation_matters_zh}
        </p>
      </section>

      <section>
        <h2 className="card-title mb-3 text-amber-300">常见陷阱</h2>
        <div className="rounded-md border border-amber-900/40 bg-amber-950/20 px-4 py-3">
          <p className="text-[14px] leading-relaxed text-amber-100/85">
            {learnCase.common_pitfall_zh}
          </p>
        </div>
      </section>

      <section>
        <h2 className="card-title mb-3">可观察量</h2>
        <div className="inline-flex items-center gap-2 rounded-md border border-surface-800 bg-surface-900/50 px-3 py-2">
          <span className="text-[11px] uppercase tracking-wider text-surface-500">
            canonical observable
          </span>
          <span className="mono text-[13px] text-surface-100">{learnCase.observable}</span>
        </div>
      </section>

      <section>
        <h2 className="card-title mb-3">参考文献</h2>
        <p className="mono text-[13px] text-surface-300">{learnCase.canonical_ref}</p>
      </section>
    </div>
  );
}

// Physics-contract panel — surfaces the gold YAML's physics_contract block
// (contract_status + preconditions with three-state satisfied markers) so a
// reader sees the nuanced CFD-level verdict before the downstream PASS/HAZARD/
// FAIL tile. Rendering is best-effort: if the backend hasn't returned the
// ValidationReport yet we show a compact skeleton; if the case has no
// physics_contract (shouldn't happen after DEC-V61-046 backfill) we hide.
function PhysicsContractPanel({
  report,
}: {
  report: ValidationReport | undefined;
}) {
  if (!report) {
    return (
      <section className="rounded-md border border-surface-800 bg-surface-900/30 px-4 py-3 text-[12px] text-surface-500">
        正在从后端取回 physics contract…
      </section>
    );
  }
  const narrative = report.case.contract_status_narrative?.trim();
  const preconds = report.preconditions ?? [];
  if (!narrative && preconds.length === 0) {
    return null;
  }

  // The contract_status string is often shaped "VERDICT — human detail".
  // Split on the first em/en-dash or " - " so the verdict token can be
  // highlighted while the detail stays as body text.
  let verdict = narrative ?? "";
  let detail = "";
  if (narrative) {
    const m = narrative.match(/^([A-Z_]+)(?:\s*[—\-–]\s*(.+))?$/s);
    if (m) {
      verdict = m[1];
      detail = (m[2] ?? "").trim();
    }
  }
  // Tri-state precondition marker, mirroring ui/backend/routes/case_export.py's
  // [✓]/[~]/[✗] renderer so the student / reviewer sees the same characters
  // across the downloadable contract md and the in-UI panel. DEC-V61-046
  // round-3 R3-B1: the backend now delivers the raw tri-state via
  // Precondition.satisfied ∈ { true, false, "partial" }, so we can render
  // it directly instead of reconstructing from evidence text.
  const mark = (
    satisfied: Precondition["satisfied"],
  ): { glyph: string; tone: string } => {
    if (satisfied === "partial") return { glyph: "~", tone: "text-amber-300" };
    if (satisfied === false) return { glyph: "✗", tone: "text-contract-fail" };
    return { glyph: "✓", tone: "text-contract-pass" };
  };

  const verdictTone =
    verdict.startsWith("SATISFIED") || verdict === "COMPATIBLE"
      ? "text-contract-pass border-contract-pass/40 bg-contract-pass/10"
      : verdict.startsWith("INCOMPATIBLE") ||
        verdict.startsWith("INCOMPATIBLE_WITH_LITERATURE")
      ? "text-contract-fail border-contract-fail/40 bg-contract-fail/10"
      : "text-amber-300 border-amber-700/40 bg-amber-950/20";

  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="card-title">物理契约 · Physics contract</h2>
        <p className="text-[11px] text-surface-500">
          来自 knowledge/gold_standards/*.yaml
        </p>
      </div>
      {narrative && (
        <div className={`rounded-md border px-4 py-3 ${verdictTone}`}>
          <p className="mono text-[11px] uppercase tracking-wider opacity-80">
            contract_status
          </p>
          <p className="mt-0.5 text-[15px] font-semibold leading-snug">
            {verdict}
          </p>
          {detail && (
            <p className="mt-2 text-[13px] leading-relaxed text-surface-200">
              {detail}
            </p>
          )}
        </div>
      )}
      {preconds.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-[11px] uppercase tracking-wider text-surface-500">
            preconditions · 标记 [✓] 满足 · [~] 部分 · [✗] 不满足
          </p>
          <ul className="space-y-2">
            {preconds.map((p, i) => {
              const m = mark(p.satisfied);
              return (
                <li
                  key={i}
                  className="flex gap-3 rounded-md border border-surface-800 bg-surface-900/40 px-3 py-2"
                >
                  <span className={`mono font-semibold ${m.tone}`}>[{m.glyph}]</span>
                  <div className="flex-1 text-[13px] leading-relaxed text-surface-200">
                    {p.condition}
                    {p.evidence_ref && (
                      <div className="mt-1 mono text-[10px] leading-relaxed text-surface-500">
                        evidence: {p.evidence_ref}
                      </div>
                    )}
                    {p.consequence_if_unsatisfied && (
                      <div className="mt-1 text-[11px] italic leading-relaxed text-amber-300/80">
                        if unsatisfied: {p.consequence_if_unsatisfied}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}

// --- Compare tab --------------------------------------------------------------

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

function CompareTab({
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

function MeshTab({ caseId }: { caseId: string }) {
  const sweep = GRID_CONVERGENCE_CASES[caseId];

  // Unconditionally create state + queries so the hook call count stays
  // stable regardless of whether this case has a sweep. (React will
  // throw if hook count varies between renders.)
  const densities = sweep?.densities ?? [];
  const [idx, setIdx] = useState(densities.length > 1 ? 2 : 0);

  const reports = useQueries({
    queries: densities.map((d) => ({
      queryKey: ["validation-report", caseId, d.id],
      queryFn: () => api.getValidationReport(caseId, d.id),
      enabled: !!caseId,
      retry: false,
      staleTime: 60_000,
    })),
  });

  if (!sweep) {
    return (
      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
        <p className="card-title mb-2">网格收敛演示尚未为此案例准备</p>
        <p className="text-[13px] leading-relaxed text-surface-400">
          这个案例目前只有一套默认网格的 fixture。目前有网格收敛 sweep 的案例：
          <span className="mono ml-1 text-surface-300">
            {Object.keys(GRID_CONVERGENCE_CASES).join(" · ")}
          </span>
        </p>
      </div>
    );
  }

  const active = reports[idx];
  const activeReport = active?.data as ValidationReport | undefined;
  const activeDensity = densities[idx];
  const loading = reports.some((r) => r.isLoading);

  // Map each density to its (value, verdict) — used for the sparkline.
  const series = reports.map((r, i) => {
    const rep = r.data as ValidationReport | undefined;
    return {
      idx: i,
      label: densities[i].label,
      value: rep?.measurement?.value,
      status: rep?.contract_status ?? "UNKNOWN",
    };
  });

  const goldRef = activeReport?.gold_standard?.ref_value;
  const tol = activeReport?.gold_standard?.tolerance_pct;
  const unit = activeReport?.gold_standard?.unit ?? "";

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
        <div className="mb-4 flex items-baseline justify-between">
          <div>
            <h2 className="card-title">网格收敛演示 · Grid Convergence</h2>
            <p className="mt-1 text-[12px] text-surface-500">
              拖动滑块，实时看 {activeReport?.gold_standard?.quantity ?? "key quantity"} 如何随网格密度逼近 gold 值。
            </p>
          </div>
          <span className="mono text-[11px] text-surface-500">
            sweep: {sweep.meshLabel}
          </span>
        </div>

        {/* Density slider */}
        <div className="mb-6">
          <div className="mb-2 flex justify-between text-[11px] text-surface-500">
            {densities.map((d, i) => (
              <button
                key={d.id}
                onClick={() => setIdx(i)}
                className={`rounded-sm px-1.5 py-0.5 transition-colors ${
                  i === idx ? "bg-sky-900/50 text-sky-200" : "hover:text-surface-300"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
          <input
            type="range"
            min={0}
            max={densities.length - 1}
            step={1}
            value={idx}
            onChange={(e) => setIdx(Number(e.target.value))}
            className="w-full accent-sky-500"
            aria-label="mesh density"
          />
        </div>

        {/* Active value card */}
        <div className="mb-4 grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-surface-500">
              测量值
            </p>
            <p className="mono mt-1 text-2xl text-surface-100">
              {loading || active?.data == null
                ? "—"
                : formatNumber(activeReport?.measurement?.value)}
              {unit ? <span className="ml-1 text-[11px] text-surface-500">{unit}</span> : null}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-surface-500">
              相对 gold 偏差
            </p>
            <p className="mono mt-1 text-2xl text-surface-100">
              {activeReport?.deviation_pct == null ||
              !Number.isFinite(activeReport.deviation_pct)
                ? "—"
                : `${activeReport.deviation_pct >= 0 ? "+" : ""}${activeReport.deviation_pct.toFixed(1)}%`}
            </p>
          </div>
          <div
            className={`rounded-md border px-3 py-1.5 text-[12px] font-medium ${
              activeReport
                ? STATUS_CLASS[activeReport.contract_status]
                : "text-surface-400"
            }`}
          >
            {activeReport ? STATUS_TEXT[activeReport.contract_status] : "加载中…"}
          </div>
        </div>

        {/* Sparkline — convergence trend */}
        <ConvergenceSparkline
          series={series}
          goldRef={goldRef}
          tolPct={tol}
          activeIdx={idx}
        />

        {/* Density description */}
        <div className="mt-4 text-[12px] leading-relaxed text-surface-400">
          <span className="mono text-surface-300">{activeDensity.label}</span>
          <span className="mx-2 text-surface-700">·</span>
          <span className="mono text-surface-500">{activeDensity.n} cells</span>
          <span className="mx-2 text-surface-700">·</span>
          <span className="mono text-surface-500">run_id: {activeDensity.id}</span>
        </div>
      </section>

      <section className="rounded-md border border-surface-800/60 bg-surface-900/20 p-5 text-[12px] leading-relaxed text-surface-400">
        <p className="mb-1 font-medium text-surface-300">读图指南</p>
        <p>
          网格收敛的基本要求：随 h → 0 你应该看到测量值**单调**逼近 gold（或至少一条光滑曲线），
          且相邻两级之间的变化随 h 的某个幂次衰减（Richardson extrapolation 就是在测这个幂次）。
          如果测量值在粗网格处大幅震荡、或 "看起来收敛了但其实离 gold 还很远"——那是 scheme 精度问题，不是 mesh。
        </p>
      </section>
    </div>
  );
}

function ConvergenceSparkline({
  series,
  goldRef,
  tolPct,
  activeIdx,
}: {
  series: { idx: number; label: string; value: number | null | undefined; status: ContractStatus }[];
  goldRef: number | undefined;
  tolPct: number | undefined;
  activeIdx: number;
}) {
  const W = 600;
  const H = 180;
  const padX = 40;
  const padY = 20;

  const values = series
    .map((s) => s.value)
    .filter((v): v is number => v != null && Number.isFinite(v));
  if (goldRef == null || !Number.isFinite(goldRef) || values.length === 0) {
    return (
      <div className="h-[180px] rounded border border-surface-800 bg-surface-950/40 p-3 text-[11px] text-surface-500">
        等待后端数据…
      </div>
    );
  }
  const allVals = [...values, goldRef];
  if (tolPct != null) {
    allVals.push(goldRef * (1 + tolPct), goldRef * (1 - tolPct));
  }
  const yMin = Math.min(...allVals);
  const yMax = Math.max(...allVals);
  const yRange = yMax - yMin || Math.abs(goldRef) * 0.2 || 1;
  const yPad = yRange * 0.15;
  const yLo = yMin - yPad;
  const yHi = yMax + yPad;

  const xStep = series.length > 1 ? (W - 2 * padX) / (series.length - 1) : 0;
  const toX = (i: number) => padX + i * xStep;
  const toY = (v: number) => padY + (H - 2 * padY) * (1 - (v - yLo) / (yHi - yLo));

  const goldY = toY(goldRef);
  const upperY = tolPct != null ? toY(goldRef * (1 + tolPct)) : null;
  const lowerY = tolPct != null ? toY(goldRef * (1 - tolPct)) : null;

  const points = series
    .map((s) =>
      s.value == null || !Number.isFinite(s.value)
        ? null
        : `${toX(s.idx)},${toY(s.value)}`,
    )
    .filter((p): p is string => p != null)
    .join(" ");

  const statusColor: Record<ContractStatus, string> = {
    PASS: "#4ade80",
    HAZARD: "#fbbf24",
    FAIL: "#f87171",
    UNKNOWN: "#9ca3af",
  };

  return (
    <div className="rounded border border-surface-800 bg-surface-950/40 p-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img">
        {/* tolerance band */}
        {upperY != null && lowerY != null && (
          <rect
            x={padX - 6}
            y={Math.min(upperY, lowerY)}
            width={W - 2 * padX + 12}
            height={Math.abs(upperY - lowerY)}
            fill="#4ade80"
            opacity={0.08}
          />
        )}
        {/* gold line */}
        <line
          x1={padX - 6}
          x2={W - padX + 6}
          y1={goldY}
          y2={goldY}
          stroke="#4ade80"
          strokeWidth={1.4}
          strokeDasharray="4 3"
        />
        <text x={W - padX + 10} y={goldY + 3} fontSize="10" fill="#4ade80">
          gold {formatNumber(goldRef)}
        </text>
        {/* connecting line */}
        <polyline
          points={points}
          fill="none"
          stroke="#60a5fa"
          strokeWidth={1.5}
          opacity={0.6}
        />
        {/* density anchor points */}
        {series.map((s) => {
          if (s.value == null || !Number.isFinite(s.value)) return null;
          const cx = toX(s.idx);
          const cy = toY(s.value);
          const r = s.idx === activeIdx ? 6 : 4;
          return (
            <g key={s.idx}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={statusColor[s.status]}
                stroke="#0a0e14"
                strokeWidth={1.5}
              />
              <text
                x={cx}
                y={H - 4}
                textAnchor="middle"
                fontSize="10"
                fill={s.idx === activeIdx ? "#e5e7eb" : "#6b7280"}
              >
                {s.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function formatNumber(v: number | undefined | null): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const abs = Math.abs(v);
  if (abs === 0) return "0";
  if (abs < 0.001) return v.toExponential(2);
  if (abs < 1) return v.toFixed(4);
  if (abs < 100) return v.toFixed(3);
  return v.toFixed(1);
}

// --- Run tab ------------------------------------------------------------------

function RunTab({ caseId }: { caseId: string }) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-5">
        <p className="card-title mb-3">运行求解器</p>
        <p className="text-[13px] leading-relaxed text-surface-300">
          真正的 solver 执行、残差流式、收敛监测在 Pro Workbench 里。
          这里我们保持学习视角——先理解问题，再动手。
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Link
            to={`/runs/${caseId}`}
            className="rounded-md bg-sky-600 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-sky-500"
          >
            去 Pro Workbench 跑这个案例 →
          </Link>
          <Link
            to={`/cases/${caseId}/edit`}
            className="rounded-md border border-surface-700 bg-surface-900 px-3.5 py-1.5 text-[13px] text-surface-200 hover:border-surface-600"
          >
            查看/编辑 YAML
          </Link>
        </div>
      </div>

      {/* DEC-V61-047 round-1 F2 blocker fix: the synthetic SVG preview
          below was previously shown under "你大概会看到" with no clear
          signal that it was decorative. A novice reading the page
          could mistake it for this case's real solver trace. We now
          try the real audit_real_run residuals.png first (exists for
          all 10 cases via phase5_audit_run.py captures), and only
          fall back to the synthetic preview with an explicit 示意图
          marker if the real artifact is missing. */}
      <RunResidualsCard caseId={caseId} />
    </div>
  );
}

function RunResidualsCard({ caseId }: { caseId: string }) {
  const realUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/audit_real_run/renders/residuals.png`;
  const [realOk, setRealOk] = useState<boolean | null>(null);

  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="card-title">残差收敛 · 真实 solver 输出</p>
        {realOk && (
          <span className="mono text-[10px] text-contract-pass">
            audit_real_run · 真实数据
          </span>
        )}
      </div>
      {realOk !== false ? (
        <div className="rounded-md border border-surface-800 bg-white p-2">
          <img
            src={realUrl}
            alt={`${caseId} audit_real_run residuals`}
            className="w-full"
            onLoad={() => setRealOk(true)}
            onError={() => setRealOk(false)}
          />
        </div>
      ) : (
        <>
          <div className="mb-2 rounded-md border border-amber-600/50 bg-amber-950/30 p-2 text-[11px] text-amber-200">
            <span className="font-semibold">⚠ 示意图 · illustrative only</span>
            ：该 case 的 audit_real_run 真实残差 PNG 暂未生成（可能是尚未 phase-5
            audit 过）。下方 SVG 是<strong>示意性装饰</strong>，不是本 case 真实
            的 solver 残差 —— 目的仅是让新手了解"残差应该长什么样"。要看真实残差
            请去 Pro Workbench 或重跑 <code className="mono">scripts/phase5_audit_run.py</code>。
          </div>
          <ResidualsPreview />
        </>
      )}
      <p className="mt-4 text-[12px] leading-relaxed text-surface-400">
        残差随迭代步数下降到判据以下意味着解收敛——但<strong>收敛不等于"算对"</strong>。
        残差降下去只说明离散方程的数值解稳定了，它不知道你的 mesh / BC /
        model 是否符合物理。下一步请回到 "对比" tab 看数值能不能贴住黄金标准。
      </p>
    </div>
  );
}

// Pure-SVG residual chart (no chart lib dependency). Shows a decaying
// multi-residual hint like a real simpleFoam log would render.
function ResidualsPreview() {
  const SERIES = useMemo(() => {
    const makeSeries = (decay: number, noise: number, seed: number) => {
      const pts: [number, number][] = [];
      let val = 1;
      for (let i = 0; i <= 60; i++) {
        val *= decay;
        const jitter = Math.sin(i * 0.7 + seed) * noise * val;
        pts.push([i, Math.max(val + jitter, 1e-6)]);
      }
      return pts;
    };
    return [
      { key: "p", color: "#60a5fa", pts: makeSeries(0.9, 0.2, 0.1) },
      { key: "Ux", color: "#a78bfa", pts: makeSeries(0.91, 0.22, 1.3) },
      { key: "Uy", color: "#f472b6", pts: makeSeries(0.92, 0.18, 2.1) },
    ];
  }, []);

  const W = 560;
  const H = 160;
  const PADL = 36;
  const PADR = 12;
  const PADT = 8;
  const PADB = 22;

  const xToPx = (x: number) => PADL + (x / 60) * (W - PADL - PADR);
  const yToPx = (y: number) => {
    // log scale from 1 down to 1e-6
    const logY = Math.log10(Math.max(y, 1e-6));
    const frac = (0 - logY) / 6; // 0 at top, 1 at bottom
    return PADT + frac * (H - PADT - PADB);
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-hidden>
      {/* log-grid horizontal lines at 1e0..1e-6 */}
      {[0, -1, -2, -3, -4, -5, -6].map((p) => (
        <g key={p}>
          <line
            x1={PADL}
            x2={W - PADR}
            y1={yToPx(Math.pow(10, p))}
            y2={yToPx(Math.pow(10, p))}
            stroke="currentColor"
            className="text-surface-800"
            strokeWidth="0.5"
          />
          <text
            x={PADL - 6}
            y={yToPx(Math.pow(10, p)) + 3}
            fontSize="10"
            textAnchor="end"
            fill="currentColor"
            className="mono text-surface-500"
          >
            1e{p}
          </text>
        </g>
      ))}
      {/* x-axis */}
      <line
        x1={PADL}
        x2={W - PADR}
        y1={H - PADB}
        y2={H - PADB}
        stroke="currentColor"
        className="text-surface-700"
        strokeWidth="1"
      />
      <text
        x={(W + PADL) / 2}
        y={H - 6}
        fontSize="10"
        textAnchor="middle"
        fill="currentColor"
        className="text-surface-500"
      >
        迭代步数
      </text>
      {/* series */}
      {SERIES.map((s) => (
        <g key={s.key}>
          <polyline
            fill="none"
            stroke={s.color}
            strokeWidth="1.4"
            points={s.pts.map(([x, y]) => `${xToPx(x)},${yToPx(y)}`).join(" ")}
            opacity="0.85"
          />
          <text
            x={xToPx(61)}
            y={yToPx(s.pts[s.pts.length - 1][1]) + 3}
            fontSize="10"
            fill={s.color}
            className="mono"
          >
            {s.key}
          </text>
        </g>
      ))}
    </svg>
  );
}

// --- Advanced tab -------------------------------------------------------------

function AdvancedTab({
  caseId,
  report,
}: {
  caseId: string;
  report: ValidationReport | undefined;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-5">
        <p className="card-title mb-2">为什么这里叫 Advanced</p>
        <p className="text-[13px] leading-relaxed text-surface-300">
          下面这些能力——决策溯源、签名审计包、字节可复现打包——
          是给要对审计员、合规官、审稿人负责的专业用户准备的。
          学习场景用不到也没关系。等你真的要把一个 CFD 预测交给别人信的时候再回来。
        </p>
      </div>

      {/* Decisions trail — compact */}
      <section className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
        <h3 className="card-title mb-3">决策溯源 · Decision trail</h3>
        {report && report.decisions_trail.length > 0 ? (
          <ul className="space-y-2">
            {report.decisions_trail.map((d) => (
              <li key={d.decision_id} className="flex items-start gap-3 text-[13px]">
                <span className="mono mt-0.5 inline-flex shrink-0 rounded-sm bg-surface-800 px-1.5 py-0.5 text-[11px] text-surface-200">
                  {d.decision_id}
                </span>
                <span className="text-surface-300">{d.title}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[12px] text-surface-500">
            这个案例还没有关联决策。复杂案例（比如 DHC、duct_flow）会累积决策轨迹。
          </p>
        )}
      </section>

      {/* Audit concerns — if any */}
      {report && report.audit_concerns.length > 0 && (
        <section className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
          <h3 className="card-title mb-3">审计关注项</h3>
          <ul className="space-y-3">
            {report.audit_concerns.map((ac, i) => (
              <li key={i} className="text-[13px]">
                <div className="mb-1 flex items-center gap-2">
                  <span className="mono inline-flex rounded-sm bg-amber-950/40 px-1.5 py-0.5 text-[10px] text-amber-200">
                    {ac.concern_type}
                  </span>
                </div>
                <p className="leading-relaxed text-surface-300">{ac.summary}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Bridge to Pro Workbench */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-sky-900/40 bg-sky-950/15 px-5 py-4">
        <div>
          <p className="text-[13px] text-surface-200">
            要生成签名的证据包（manifest + zip + HMAC .sig）？
          </p>
          <p className="mt-1 text-[11px] text-surface-400">
            Pro Workbench · Audit Package Builder ·{" "}
            <span className="mono">case_id={caseId}</span>
          </p>
        </div>
        <Link
          to="/audit-package"
          className="rounded-md bg-sky-600 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-sky-500"
        >
          进入 Audit Package Builder →
        </Link>
      </div>
    </div>
  );
}

// --- Shared callouts ----------------------------------------------------------

function ErrorCallout({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 p-4 text-[13px] text-contract-fail">
      {message}
    </div>
  );
}

function SkeletonCallout({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-4 text-[13px] text-surface-400">
      {message}
    </div>
  );
}

// --- Phase 7f: Scientific CFD-vs-Gold comparison report section -----------

type ComparisonReportContext = {
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
  } | null;
  paper?: {
    title: string;
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
  // Visual-only top-level fields:
  solver?: string;
  commit_sha?: string;
};

function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
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
