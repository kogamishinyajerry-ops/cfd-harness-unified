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
          {/* DEC-V61-049 batch D · kind badge legend. Codex CFD-novice walk
              Step 4: the stream-function ansatz looked more symmetric than
              the real OpenFOAM contour, and the student had no way to tell
              "this is published data" from "this is a pedagogical
              reconstruction". Badge makes it visible at a glance. */}
          <p className="mb-3 text-[10.5px] leading-relaxed text-surface-500">
            <span className="mr-1 inline-flex items-center rounded-sm bg-emerald-900/40 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">literature_data</span>
            直接来自文献 / 实验表格 ·
            <span className="mx-1 inline-flex items-center rounded-sm bg-amber-900/40 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">analytical_visual</span>
            解析公式 / ansatz / 合成图 — 不是 solver 输出 ·
            <span className="ml-1 inline-flex items-center rounded-sm bg-sky-900/40 px-1.5 py-0.5 text-[10px] font-semibold text-sky-300">solver_output</span>
            实跑 OpenFOAM 产出
          </p>
          <div className="space-y-4">
            {flowFields.map((ff) => {
              const kindStyles: Record<typeof ff.kind, string> = {
                literature_data: "bg-emerald-900/40 text-emerald-300",
                analytical_visual: "bg-amber-900/40 text-amber-300",
                solver_output: "bg-sky-900/40 text-sky-300",
              };
              const kindBorder: Record<typeof ff.kind, string> = {
                literature_data: "border-surface-800",
                analytical_visual: "border-amber-900/50",
                solver_output: "border-sky-900/50",
              };
              return (
                <figure
                  key={ff.src}
                  className={`overflow-hidden rounded-md border bg-surface-900/30 ${kindBorder[ff.kind]}`}
                >
                  <img
                    src={ff.src}
                    alt={ff.caption_zh}
                    className="w-full max-w-full"
                    loading="lazy"
                  />
                  <figcaption className="border-t border-surface-800 px-4 py-3">
                    <div className="mb-1 flex items-start gap-2">
                      <span
                        className={`mono inline-flex shrink-0 items-center rounded-sm px-1.5 py-0.5 text-[10px] font-semibold ${kindStyles[ff.kind]}`}
                      >
                        {ff.kind}
                      </span>
                      <p className="flex-1 text-[13px] text-surface-200">{ff.caption_zh}</p>
                    </div>
                    <p className="mono mt-1.5 text-[10px] leading-relaxed text-surface-500">
                      provenance: {ff.provenance}
                    </p>
                  </figcaption>
                </figure>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h2 className="card-title mb-3">为什么要做验证</h2>
        <p className="text-[14px] leading-relaxed text-surface-200">
          {learnCase.why_validation_matters_zh}
        </p>
      </section>

      {/* DEC-V61-048 round-1 batch 4 (flagship deep-dive) — physical
          intuition narrative for the 3 lowest-scoring cases (LDC, RBC,
          duct). Codex B-axis: even with lineage + teaching cards +
          runbook + troubleshooting, these cases still lacked "what does
          this flow actually look like standing inside it, and how does
          it change across regimes". Populated only for flagship cases
          — optional field, rendered only when present. Paragraphs split
          on \n\n for readability. */}
      {learnCase.physics_intuition_zh && (
        <section>
          <h2 className="card-title mb-3">物理直觉 · Physical intuition</h2>
          <div className="space-y-3 rounded-md border border-indigo-900/40 bg-indigo-950/10 p-4">
            {learnCase.physics_intuition_zh.split("\n\n").map((para, i) => (
              <p key={i} className="text-[13.5px] leading-relaxed text-surface-100">
                {para}
              </p>
            ))}
          </div>
        </section>
      )}

      {/* DEC-V61-049 batch E — glossary for novice vocabulary.
          Codex CFD-novice walk Step 1: TeachingCards + physics_intuition
          use terms like SIMPLE / URF / residualControl / stream function
          / GCI / tolerance band without defining them. A first-semester
          student would have to Google each one. Optional per-case;
          populated for LDC pilot only. */}
      {learnCase.glossary_zh && learnCase.glossary_zh.length > 0 && (
        <section>
          <h2 className="card-title mb-3">术语表 · Glossary</h2>
          <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
            本页 TeachingCards + 物理直觉块里用到的每个非日常 CFD 术语的一句定义，本 case 的 scope 内够用；想深究请去对应的教材章节。
          </p>
          <dl className="space-y-2.5 rounded-md border border-surface-800 bg-surface-900/40 p-4">
            {learnCase.glossary_zh.map((g, i) => (
              <div key={i} className="grid gap-2 md:grid-cols-[max-content_1fr] md:gap-4">
                <dt className="mono shrink-0 text-[12px] font-semibold text-sky-300">
                  {g.term}
                </dt>
                <dd className="text-[12.5px] leading-relaxed text-surface-200">
                  {g.definition}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section>
        <h2 className="card-title mb-3 text-amber-300">常见陷阱</h2>
        <div className="rounded-md border border-amber-900/40 bg-amber-950/20 px-4 py-3">
          <p className="text-[14px] leading-relaxed text-amber-100/85">
            {learnCase.common_pitfall_zh}
          </p>
        </div>
      </section>

      {/* DEC-V61-047 round-1 F4 teaching cards — surface solver / mesh /
          BC / observable-extraction directly in Story so a novice does
          not need to open gold YAML or Pro Workbench. 2-col grid on
          medium+ screens; each card is a compact Chinese paragraph. */}
      <section>
        <h2 className="card-title mb-3">CFD 全流程</h2>
        <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
          从问题到数值结果，本 case 的每一步设置 —— 让你理解"这个 case 的网格 / solver / BC 是怎么来的"，而不只是"它的数值能不能对上"。
        </p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <TeachingCard
            label="Solver 设置"
            label_en="Solver"
            body={learnCase.solver_setup_zh}
            tone="sky"
          />
          <TeachingCard
            label="网格策略"
            label_en="Mesh"
            body={learnCase.mesh_strategy_zh}
            tone="emerald"
          />
          <TeachingCard
            label="边界条件"
            label_en="Boundary conditions"
            body={learnCase.boundary_conditions_zh}
            tone="violet"
          />
          <TeachingCard
            label="观察量提取"
            label_en="Observable extraction"
            body={learnCase.observable_extraction_zh}
            tone="amber"
          />
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

      {/* DEC-V61-048 round-1 batch 1 (A) — benchmark lineage + next-reading
          ladder. Codex deep-dive: every case had only a single canonical_ref
          citation token; for graduate-course reading value the page needs
          to tell the student WHY this paper is the teaching anchor, what
          parallel benchmarks exist, and what to read next. Renders 3-part
          structure: why_primary paragraph + secondary refs as bulleted list
          + next_reading paragraph. */}
      <section>
        <h2 className="card-title mb-3">历史基准链 · Benchmark lineage</h2>
        <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
          这条链告诉你当前页锚定的这一篇文献为什么成了课堂共同语言、同主题还有哪些并列或互相补充的基准、以及读完这一 case 之后下一篇应该读什么。
        </p>
        <div className="space-y-4 rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-sky-300">
              为什么选这一篇 · Why this paper
            </p>
            <p className="text-[13px] leading-relaxed text-surface-200">
              {learnCase.benchmark_lineage_zh.why_primary}
            </p>
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              并列 / 补充文献 · Parallel + complementary
            </p>
            <ul className="space-y-1 text-[12px] leading-relaxed text-surface-300">
              {learnCase.benchmark_lineage_zh.secondary.map((s, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mono text-surface-500">·</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-amber-300">
              下一篇读什么 · Next reading
            </p>
            <p className="text-[13px] leading-relaxed text-surface-200">
              {learnCase.benchmark_lineage_zh.next_reading}
            </p>
          </div>
        </div>
      </section>

      {/* DEC-V61-048 round-1 batch 3 (B) — reproducibility runbook +
          troubleshooting checklist. Codex deep-dive D/F axes: every case
          lacked a "from zero" OpenFOAM pipeline walk and a symptom→cause→fix
          troubleshooting checklist. Without them the page reads like a
          description of a finished run, not a chapter the student can
          follow. Rendered between benchmark lineage and short citation so
          a student reads: why this case → physics → solver/mesh/BC/extract
          → lineage → "here is exactly how to rerun it and what to do when
          it breaks" → citation. */}
      <section>
        <h2 className="card-title mb-3">复现流程 · Reproducibility walk-through</h2>
        <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
          下面是在 OpenFOAM 里从零到 comparator verdict 的完整命令/文件 sequence。每一步给出操作、对应 command (若有) 和应该检查的产物，方便在你自己的环境里逐步对照。
        </p>
        <ol className="space-y-3 rounded-md border border-surface-800 bg-surface-900/40 p-4">
          {learnCase.workflow_steps_zh.map((w, i) => (
            <li key={i} className="flex gap-3">
              <span className="mono mt-0.5 shrink-0 text-[11px] font-semibold text-sky-300">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="flex-1 space-y-1">
                <p className="text-[13px] font-medium text-surface-100">{w.step}</p>
                {w.command && (
                  <pre className="mono overflow-x-auto rounded bg-surface-950/60 px-2.5 py-1.5 text-[11.5px] leading-snug text-emerald-200/90">
                    {w.command}
                  </pre>
                )}
                <p className="text-[12px] leading-relaxed text-surface-300">{w.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* DEC-V61-049 pilot batch B — complete OpenFOAM reproduction bundle.
          Codex CFD-novice walk: workflow_steps described "edit system/
          blockMeshDict" without giving the file contents, so a student
          couldn't actually reproduce. Optional per-case bundle (only LDC
          populated in V61-049 pilot); hidden for cases without one. Uses
          native <details> for progressive disclosure to avoid dominating
          the Story tab with 9 large monospace blocks. */}
      {learnCase.reproduction_bundle_zh && (
        <section>
          <h2 className="card-title mb-3">复现 bundle · Complete OpenFOAM case files</h2>
          <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
            {learnCase.reproduction_bundle_zh.intro}
          </p>
          <div className="mb-3 rounded-md border border-sky-900/40 bg-sky-950/10 p-3 text-[12px] leading-relaxed text-sky-100/85">
            <span className="mr-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-sky-300">
              操作流程
            </span>
            {learnCase.reproduction_bundle_zh.usage}
          </div>
          <div className="space-y-2">
            {learnCase.reproduction_bundle_zh.files.map((f, i) => (
              <details
                key={i}
                className="rounded-md border border-surface-800 bg-surface-900/40 p-3 open:bg-surface-900/60"
              >
                <summary className="flex cursor-pointer select-none items-start gap-3 text-[12.5px] leading-relaxed text-surface-100 hover:text-sky-200">
                  <span className="mono mt-0.5 shrink-0 text-[11px] font-semibold text-sky-300">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="flex-1">
                    <p className="mono font-semibold text-sky-200">{f.path}</p>
                    <p className="mt-0.5 text-[11.5px] leading-snug text-surface-300">
                      {f.role}
                    </p>
                  </div>
                </summary>
                <pre className="mono mt-3 max-h-[420px] overflow-auto rounded bg-surface-950/70 p-3 text-[11px] leading-snug text-surface-100">
                  {f.content}
                </pre>
              </details>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="card-title mb-3">故障排查 · Troubleshooting checklist</h2>
        <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
          按经验可能性从高到低排列的失败模式。每一行是一个"如果你看到 X，十有八九是 Y，修 Z"的三段式诊断，帮你在 solver 不收敛或 comparator 给出奇怪数字时快速定位根因。
        </p>
        <div className="space-y-2">
          {learnCase.troubleshooting_zh.map((t, i) => (
            <div
              key={i}
              className="rounded-md border border-amber-900/40 bg-amber-950/10 p-3"
            >
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-amber-300">
                症状 · Symptom
              </p>
              <p className="mb-2 text-[13px] leading-relaxed text-surface-100">{t.symptom}</p>
              <div className="grid gap-2 text-[12px] leading-relaxed text-surface-300 md:grid-cols-2">
                <div>
                  <p className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-rose-300">
                    根因 · Likely cause
                  </p>
                  <p>{t.likely_cause}</p>
                </div>
                <div>
                  <p className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-emerald-300">
                    修复 · Fix
                  </p>
                  <p>{t.fix}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* DEC-V61-049 batch E — report-writing scaffold.
          Codex CFD-novice walk Step 5: the page had no explicit scaffold
          for a 1000-word reproduction report, so the student would
          invent structure and might claim unsupported dimensions. This
          block maps the page's content to a 7-section outline with
          explicit "supported / partial / not_yet" honesty markers per
          section. Student writes what is supported, flags what is not.
          Optional per-case; LDC pilot only. */}
      {learnCase.report_skeleton_zh && learnCase.report_skeleton_zh.length > 0 && (
        <section>
          <h2 className="card-title mb-3">课程报告骨架 · Report skeleton</h2>
          <p className="mb-3 text-[12px] leading-relaxed text-surface-400">
            如果你要用本 case 写一份 ~1000 词的 CFD 复现 / 验证报告，下面 7 段是建议的结构。每段都标明当前页面"已经支持 / 部分支持 / 目前不支持"的状态——未支持的维度不要在报告里假装能写，老实写 "NOT YET in current harness" 比伪装通过更值钱。
          </p>
          <div className="space-y-2">
            {learnCase.report_skeleton_zh.map((r, i) => {
              const supportStyles: Record<typeof r.supported, { border: string; bg: string; badge: string; label: string }> = {
                yes: {
                  border: "border-emerald-900/40",
                  bg: "bg-emerald-950/10",
                  badge: "bg-emerald-900/40 text-emerald-300",
                  label: "supported",
                },
                partial: {
                  border: "border-amber-900/40",
                  bg: "bg-amber-950/10",
                  badge: "bg-amber-900/40 text-amber-300",
                  label: "partial",
                },
                not_yet: {
                  border: "border-rose-900/40",
                  bg: "bg-rose-950/10",
                  badge: "bg-rose-900/40 text-rose-300",
                  label: "NOT yet",
                },
              };
              const s = supportStyles[r.supported];
              return (
                <div key={i} className={`rounded-md border p-3 ${s.border} ${s.bg}`}>
                  <div className="mb-1.5 flex items-baseline gap-2">
                    <h3 className="text-[13.5px] font-semibold text-surface-100">{r.section}</h3>
                    <span className={`mono inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-semibold ${s.badge}`}>
                      {s.label}
                    </span>
                  </div>
                  <p className="text-[12.5px] leading-relaxed text-surface-200">
                    {r.what_to_write}
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h2 className="card-title mb-3">参考文献 · Short citation</h2>
        <p className="mono text-[13px] text-surface-300">{learnCase.canonical_ref}</p>
      </section>
    </div>
  );
}

// DEC-V61-047 round-1 F4: per-case teaching card — solver/mesh/BC/
// observable-extraction surfaced on Story tab. Accepts dangerouslySet
// for small HTML tags (<strong>, <code>) in the YAML-sourced bodies.
function TeachingCard({
  label,
  label_en,
  body,
  tone,
}: {
  label: string;
  label_en: string;
  body: string;
  tone: "sky" | "emerald" | "violet" | "amber";
}) {
  const TONE_BORDER: Record<typeof tone, string> = {
    sky: "border-sky-900/50 bg-sky-950/20",
    emerald: "border-emerald-900/50 bg-emerald-950/20",
    violet: "border-violet-900/50 bg-violet-950/20",
    amber: "border-amber-900/50 bg-amber-950/20",
  };
  const TONE_TAG: Record<typeof tone, string> = {
    sky: "text-sky-300",
    emerald: "text-emerald-300",
    violet: "text-violet-300",
    amber: "text-amber-300",
  };
  return (
    <div className={`rounded-md border ${TONE_BORDER[tone]} p-4`}>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className={`text-[13px] font-semibold ${TONE_TAG[tone]}`}>
          {label}
        </h3>
        <span className="mono text-[10px] uppercase tracking-wider text-surface-500">
          {label_en}
        </span>
      </div>
      <p
        className="text-[13px] leading-relaxed text-surface-200"
        dangerouslySetInnerHTML={{ __html: body }}
      />
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
                    {/* DEC-V61-047 round-1 F6: evidence_ref 是 reviewer-grade
                        文本（含文件路径、adapter 行号、attestor 术语），对
                        novice 会产生认知过载（参考 codex persona-2 在
                        impinging_jet case 的 🔴）。把它折叠到 <details> 里，
                        默认收起；好奇的读者可以点开看审计证据。
                        consequence_if_unsatisfied 保持常驻因为它是"如果
                        这条 precondition 不满足会怎样"的学生级 takeaway。 */}
                    {p.evidence_ref && (
                      <details className="group mt-1.5">
                        <summary className="cursor-pointer list-none text-[11px] text-surface-500 hover:text-surface-400">
                          <span className="mono">▸ 查看审计证据 (evidence)</span>
                          <span className="hidden text-surface-600 group-open:inline">
                            {" "}· 点击收起
                          </span>
                        </summary>
                        <div className="mt-1 mono text-[10px] leading-relaxed text-surface-500">
                          {p.evidence_ref}
                        </div>
                      </details>
                    )}
                    {p.consequence_if_unsatisfied && (
                      <div className="mt-1 text-[11px] italic leading-relaxed text-amber-300/80">
                        如果不满足：{p.consequence_if_unsatisfied}
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
