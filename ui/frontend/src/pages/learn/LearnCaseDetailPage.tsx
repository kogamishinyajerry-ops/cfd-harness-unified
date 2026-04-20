import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { getLearnCase } from "@/data/learnCases";
import type {
  ContractStatus,
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

type TabId = "story" | "compare" | "run" | "advanced";

const TABS: { id: TabId; label_zh: string; label_en: string }[] = [
  { id: "story", label_zh: "故事", label_en: "Story" },
  { id: "compare", label_zh: "对比", label_en: "Compare" },
  { id: "run", label_zh: "运行", label_en: "Run" },
  { id: "advanced", label_zh: "进阶", label_en: "Advanced" },
];

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
  v === "story" || v === "compare" || v === "run" || v === "advanced";

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
      {/* Breadcrumb */}
      <nav className="mb-6 text-[12px] text-surface-500">
        <Link to="/learn" className="hover:text-surface-300">
          目录
        </Link>
        <span className="mx-2 text-surface-700">/</span>
        <span className="mono text-surface-400">{caseId}</span>
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
      {tab === "story" && <StoryTab caseId={caseId} />}
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
      {tab === "run" && <RunTab caseId={caseId} />}
      {tab === "advanced" && <AdvancedTab caseId={caseId} report={report} />}
    </div>
  );
}

// --- Story tab ----------------------------------------------------------------

function StoryTab({ caseId }: { caseId: string }) {
  const learnCase = getLearnCase(caseId)!;
  return (
    <div className="space-y-8">
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

// --- Compare tab --------------------------------------------------------------

const RUN_CATEGORY_LABEL: Record<RunCategory, string> = {
  reference: "参考运行",
  real_incident: "真实故障",
  under_resolved: "欠分辨",
  wrong_model: "错模型",
};

const RUN_CATEGORY_COLOR: Record<RunCategory, string> = {
  reference: "bg-emerald-900/40 text-emerald-200 border-emerald-800/60",
  real_incident: "bg-amber-900/30 text-amber-200 border-amber-800/50",
  under_resolved: "bg-orange-900/30 text-orange-200 border-orange-800/50",
  wrong_model: "bg-rose-900/30 text-rose-200 border-rose-800/50",
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
  // backend resolved the default (first reference run, then fallback).
  // Highlight whichever run actually matches the loaded measurement.
  const resolvedRun = runs.find((r) => r.run_id === measurement?.run_id)
    ?? runs.find((r) => activeRunId ? r.run_id === activeRunId : r.category === "reference")
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

      <div className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
        <p className="card-title mb-3">你大概会看到</p>
        <ResidualsPreview />
        <p className="mt-4 text-[12px] leading-relaxed text-surface-400">
          残差随迭代步数下降到判据以下意味着解收敛。
          但是——收敛不代表"算对"。下一步请回到"对比"tab
          看看你的数值能不能贴住黄金标准。
        </p>
      </div>
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
