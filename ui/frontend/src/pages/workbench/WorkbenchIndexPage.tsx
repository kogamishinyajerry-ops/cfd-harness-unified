import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import { FirstTimeBanner } from "@/components/FirstTimeBanner";
import type { CaseIndexEntry } from "@/types/validation";

// Workbench landing index. Engineer-first surface (DEC-V61-115, 2026-05-04):
// the page leads with a hero that puts 新建案例 / 导入 STL front-and-center,
// because those are the entry gestures for a CFD engineer creating a real
// case. The 10 whitelist cases stay below the hero as `参考案例 · Reference
// cases` — a baseline of literature-backed flows the engineer can fork or
// study, but no longer the visual headline.
//
// History: between 2026-04-26 and 2026-05-04 this page opened with a small
// `Workbench` h1 + a `Pick a case to edit parameters and run...` line, then
// jumped straight into the 10 CaseCard grid. With /learn as the default
// landing (DEC-V61-046 era), that two-step "click /workbench → see 10 demos"
// path made the new-case flow feel like a side-quest. DEC-V61-115 flipped /
// → /workbench AND raised the new-case CTA visual weight to match the engineer
// north-star in ROADMAP §L9.

export function WorkbenchIndexPage() {
  const casesQuery = useQuery({
    queryKey: ["workbenchIndexCases"],
    queryFn: () => api.listCases(),
  });

  // DEC-V61-115 Codex R1 P2 #2: render the hero unconditionally — it does
  // not depend on /api/cases. Earlier draft gated the hero behind the
  // loading/error states, which meant a slow or hanging /api/cases left the
  // newly-promoted 新建案例 / 导入 STL CTAs unreachable from the default
  // landing. The 参考案例 section below the hero still respects the query
  // states (loading spinner / error message / cards), so the hero is always
  // actionable while the reference grid degrades gracefully.
  const refCasesBody = casesQuery.isLoading ? (
    <p className="text-surface-300">Loading reference cases…</p>
  ) : casesQuery.isError || !casesQuery.data ? (
    <p className="text-sm text-contract-fail">
      Failed to load reference cases:{" "}
      {casesQuery.error instanceof ApiError
        ? `${casesQuery.error.status}: ${casesQuery.error.message}`
        : String(casesQuery.error)}
    </p>
  ) : (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {casesQuery.data.map((c) => (
        <CaseCard key={c.case_id} c={c} />
      ))}
    </div>
  );

  return (
    <Section>
      <FirstTimeBanner />
      <WorkbenchHero />

      <header className="mt-10 mb-4 flex items-baseline justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-surface-300">
            参考案例 · Reference cases
          </h2>
          <p className="mt-1 text-[12px] text-surface-500">
            10 个金标准案例 — 复现历史文献，可直接编辑参数二次仿真，是验证 workbench 可信度的基线。
          </p>
        </div>
        <Link
          to="/workbench/today"
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-2.5 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
        >
          Today's runs →
        </Link>
      </header>

      {refCasesBody}
    </Section>
  );
}

// Hero — engineer-first entry block. Two large primary CTAs (new case /
// import STL) carry the visual weight; an AI-assistant explainer line under
// the CTAs makes the "AI on demand per step" contract visible; a small
// footer link points buyers/reviewers at the demo gallery (/learn).
function WorkbenchHero() {
  return (
    <section
      aria-labelledby="workbench-hero-title"
      className="rounded-md border border-surface-800 bg-gradient-to-b from-surface-900/80 to-surface-950 px-6 py-7"
    >
      <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-surface-500">
        CFD Simulation Workbench
      </p>
      <h1
        id="workbench-hero-title"
        className="mt-2 text-2xl font-semibold leading-tight text-surface-100"
      >
        CFD 仿真工作台
      </h1>
      <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-surface-300">
        从空白模板新建案例、上传几何，或编辑已有案例 — 全在 GUI 中完成。
        每个步骤右侧 [AI 处理] = 召唤 AI 跑当前阶段（网格 / 边界条件 / 求解 / 报告生成）。
      </p>

      <div className="mt-5 flex flex-wrap items-stretch gap-3">
        <Link
          to="/workbench/new"
          className="group flex min-w-[14rem] flex-1 items-center gap-3 rounded-md border border-emerald-500/50 bg-emerald-500/15 px-4 py-3 text-emerald-100 transition hover:border-emerald-400 hover:bg-emerald-500/25"
        >
          <span aria-hidden className="text-2xl leading-none">▶</span>
          <span className="flex flex-col">
            <span className="text-[15px] font-semibold">新建案例（从模板）</span>
            <span className="text-[11px] text-emerald-200/80">
              New case from template — 方腔 / 后台阶 / 层流圆管
            </span>
          </span>
        </Link>
        <Link
          to="/workbench/import"
          className="group flex min-w-[14rem] flex-1 items-center gap-3 rounded-md border border-sky-500/50 bg-sky-500/15 px-4 py-3 text-sky-100 transition hover:border-sky-400 hover:bg-sky-500/25"
        >
          <span aria-hidden className="text-2xl leading-none">📥</span>
          <span className="flex flex-col">
            <span className="text-[15px] font-semibold">导入 STL 几何</span>
            <span className="text-[11px] text-sky-200/80">
              Import STL geometry — trimesh 摄入 + 自动建 case 目录
            </span>
          </span>
        </Link>
      </div>

      <p className="mt-4 text-[11px] text-surface-500">
        想看 10 个金标准案例的演示模式？
        <Link to="/learn" className="ml-1 text-sky-300 hover:text-sky-200">
          → /learn
        </Link>
      </p>
    </section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  // Responsive padding (DEC-V61-115 Codex R1 P2 #1 follow-on): tighter on
  // narrow screens, full breathing room from md+. Pairs with Layout sidebar
  // collapse so a phone-width visitor gets the full viewport for the hero +
  // CTAs without wasted edge gutter.
  return (
    <section className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-8">{children}</section>
  );
}

function CaseCard({ c }: { c: CaseIndexEntry }) {
  const editHref = `/workbench/case/${encodeURIComponent(c.case_id)}/edit`;
  const runsHref = `/workbench/case/${encodeURIComponent(c.case_id)}/runs`;
  const isGoldPending = c.gold_pending === true;
  return (
    <div
      data-testid={`case-card-${c.case_id}`}
      data-case-kind={c.case_kind ?? "whitelist"}
      data-gold-pending={isGoldPending ? "true" : "false"}
      className="flex flex-col rounded-md border border-surface-800 bg-surface-900/40 p-4 transition hover:border-surface-700"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-surface-100">{c.name}</h3>
          <p className="mt-0.5 font-mono text-[11px] text-surface-500">{c.case_id}</p>
        </div>
        {isGoldPending ? <GoldPendingBadge /> : <ContractChip status={c.contract_status} />}
      </div>
      {isGoldPending && (
        <p
          data-testid={`case-card-gold-pending-disclaimer-${c.case_id}`}
          className="mt-2 rounded-sm border border-amber-700/40 bg-amber-900/10 px-2 py-1 text-[10px] text-amber-200"
        >
          ⏳ Gold pending · industrial substrate listed for browsing; no curated
          reference yet, so the trust gate stays PENDING until gold authoring.
        </p>
      )}

      <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-[11px]">
        <dt className="font-mono text-surface-500">flow</dt>
        <dd className="font-mono text-surface-300">{c.flow_type}</dd>
        <dt className="font-mono text-surface-500">geometry</dt>
        <dd className="font-mono text-surface-300">{c.geometry_type}</dd>
        <dt className="font-mono text-surface-500">turbulence</dt>
        <dd className="font-mono text-surface-300">{c.turbulence_model}</dd>
      </dl>

      <div className="mt-auto flex items-center justify-between pt-4">
        <span className="text-[10px] text-surface-500">
          {c.run_summary?.total ?? 0} historical run{(c.run_summary?.total ?? 0) === 1 ? "" : "s"}
        </span>
        <div className="flex gap-2">
          <Link
            to={runsHref}
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
          >
            Runs
          </Link>
          <Link
            to={editHref}
            className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
          >
            Edit & run →
          </Link>
        </div>
      </div>
    </div>
  );
}

function GoldPendingBadge() {
  return (
    <span
      data-testid="case-card-gold-pending-badge"
      className="whitespace-nowrap rounded-sm border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-amber-300"
      title="Gold reference not yet authored — case is listable but trust gate stays PENDING"
    >
      ⏳ gold pending
    </span>
  );
}

function ContractChip({ status }: { status: string }) {
  // The contract_status values are PASS / PASS_WITH_DEVIATIONS / FAIL /
  // INCOMPATIBLE / etc. — colour-tone by family without hard-coding the
  // full enum, so additions on the backend don't silently render plain.
  const tone = status.startsWith("PASS")
    ? "border-contract-pass/40 bg-contract-pass/10 text-contract-pass"
    : status === "FAIL" || status === "INCOMPATIBLE"
      ? "border-contract-fail/40 bg-contract-fail/10 text-contract-fail"
      : "border-amber-500/40 bg-amber-500/10 text-amber-300";
  return (
    <span
      className={`whitespace-nowrap rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${tone}`}
    >
      {status}
    </span>
  );
}
