import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { getLearnCase } from "@/data/learnCases";
import type { RunDescriptor, ValidationReport } from "@/types/validation";

import { AdvancedTab } from "./case_detail/AdvancedTab";
import { CaseFrame } from "./case_detail/CaseFrame";
import { CaseHealthStrip } from "./case_detail/CaseHealthStrip";
import { CompareTab } from "./case_detail/CompareTab";
import { MeshTab } from "./case_detail/MeshTab";
import { RunTab } from "./case_detail/RunTab";
import { StoryTab } from "./case_detail/StoryTab";

// Student-facing case detail · entry shell. The 5 tabs (story / compare /
// mesh / run / advanced) live in ./case_detail/. This file owns:
//   - tab routing via ?tab= query param
//   - shared ValidationReport / RunDescriptor fetches
//   - hero header + breadcrumb + Pro Workbench switch
// Sub-tabs derive their views from the shared record so the student can
// flip between them without re-fetching.
//
// Stage 1 shell-split landed 2026-04-25 (Codex industrial-workbench
// meeting verdict): the page was 3294 LOC × 5 tabs single-file, now
// distributed across 8 files in ./case_detail/. Behavior unchanged.

type TabId = "story" | "compare" | "mesh" | "run" | "advanced";

const TABS: { id: TabId; label_zh: string; label_en: string }[] = [
  { id: "story", label_zh: "故事", label_en: "Story" },
  { id: "compare", label_zh: "对比", label_en: "Compare" },
  { id: "mesh", label_zh: "网格", label_en: "Mesh" },
  { id: "run", label_zh: "运行", label_en: "Run" },
  { id: "advanced", label_zh: "进阶", label_en: "Advanced" },
];

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

      {/* Post-Stage-6 polish · CaseHealthStrip ties Stages 2/3/4 status
          into a 3-chip pulse strip. Sits above CaseFrame so the user
          sees overall case health before reading geometry detail. */}
      <CaseHealthStrip caseId={caseId} />

      {/* Workbench first-screen (Stage 2 MVP). Soft-skips with `return null`
          when the case lacks a knowledge/workbench_basics/<id>.yaml authored,
          so cases not yet covered by Stage 2 fall through to the existing
          hero illustration + tabs unchanged. */}
      <CaseFrame caseId={caseId} />

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
