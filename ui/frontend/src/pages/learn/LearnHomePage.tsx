import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { BatchMatrix } from "@/components/learn/BatchMatrix";
import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { ExportPanel } from "@/components/learn/ExportPanel";
import { LEARN_CASES, type LearnCase } from "@/data/learnCases";
import type { CaseIndexEntry } from "@/types/validation";

// Student-facing catalog. No marketing hero — a three-line intro, then
// the 10 cases as visual cards. Each card leads with a line-art SVG of
// the geometry, then a short Chinese headline, the canonical historical
// reference, and a one-line teaser.

const DIFFICULTY_LABEL: Record<LearnCase["difficulty"], string> = {
  intro: "入门",
  core: "进阶",
  advanced: "高阶",
};

const DIFFICULTY_DOT: Record<LearnCase["difficulty"], string> = {
  intro: "bg-emerald-400/90",
  core: "bg-sky-400/90",
  advanced: "bg-amber-400/90",
};

export function LearnHomePage() {
  // Pull live case index so we can surface the run distribution badge per
  // card. When the backend is down the catalog still renders from static
  // LEARN_CASES metadata — just without badges.
  const { data: cases } = useQuery<CaseIndexEntry[]>({
    queryKey: ["cases"],
    queryFn: api.listCases,
    retry: false,
  });
  const indexById = new Map((cases ?? []).map((c) => [c.case_id, c]));

  return (
    <div className="mx-auto max-w-6xl px-6 pt-10 pb-16">
      {/* Hero — buyer-facing (bilingual) + differentiation strip. Earlier
          student-only hero "用十个经典流动问题学 CFD 验证思维" didn't answer
          a CFD team lead's 30-second "why should I evaluate this" question.
          DEC-V61-046 round-1 R1-M1/M4: surface real-solver / literature /
          audit-package differentiation and bilingual positioning up front;
          move the student framing into supporting teaser text below. */}
      <section className="mb-10 max-w-3xl">
        <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-surface-500">
          AI-CFD Workbench · Physics-Trust Layer
        </p>
        <h1 className="mt-2 text-3xl font-semibold leading-tight text-surface-100">
          Prove a CFD result is <span className="text-sky-300">physically trustworthy</span>,
          not just numerically converged.
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-surface-200">
          让 CFD 结果"可信"，而不只是"收敛"——把求解器输出、黄金标准、运行证据
          编到同一条可审计证据链里，对 CFD 团队负责人、审计员、审稿人透明。
        </p>
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-surface-800 bg-surface-900/50 px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wider text-surface-400">Real-solver evidence</p>
            <p className="mt-0.5 text-[12px] leading-snug text-surface-200">
              每个 verdict 可以溯源到实际 OpenFOAM 运行的残差、场图、wall shear，
              不是代理模型或预计算快照。
            </p>
          </div>
          <div className="rounded-md border border-surface-800 bg-surface-900/50 px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wider text-surface-400">Literature-backed comparator</p>
            <p className="mt-0.5 text-[12px] leading-snug text-surface-200">
              黄金标准是 Ghia/Williamson/Kim/Le-Moin 原始表格数据，
              physics_contract 显式标 satisfied/partial/false 的 precondition。
            </p>
          </div>
          <div className="rounded-md border border-surface-800 bg-surface-900/50 px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wider text-surface-400">Signed audit package</p>
            <p className="mt-0.5 text-[12px] leading-snug text-surface-200">
              HMAC-signed manifest + zip + decision trail，
              结构 inspired by DO-178C / V&amp;V40 / NQA-1 审计实践（不是等同替代，是交付路径）。
            </p>
          </div>
        </div>
      </section>

      {/* Buyer-facing CTA strip — R1-M3: an impressed reviewer needs a next
          step that isn't "click into a random audit package". Keep the CTAs
          directionally concrete but non-committal (mailto / doc / GitHub). */}
      <section className="mb-10">
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-sky-900/50 bg-sky-950/25 px-4 py-3 text-[13px]">
          <span className="text-surface-200">
            想让你的团队认真评估？
            <span className="text-surface-400 ml-2 text-[12px]">
              Serious evaluation for your team →
            </span>
          </span>
          <span className="h-4 w-px bg-sky-900/60" aria-hidden />
          <a
            href="https://github.com/kogamishinyajerry-ops/cfd-harness-unified"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sky-300 hover:text-sky-200"
          >
            GitHub · source + physics_contracts
          </a>
          <span className="text-surface-700">·</span>
          <a
            href="/workbench/new"
            className="text-emerald-300 hover:text-emerald-200"
            title="Stage 8a · Onboarding Workbench — newcomer's first-case wizard"
          >
            ▶ 新手向导 · 从模板建第一个案例
          </a>
          <span className="text-surface-700">·</span>
          <a
            href="/pro"
            className="text-sky-300 hover:text-sky-200"
          >
            Pro Workbench · audit package builder
          </a>
          <span className="text-surface-700">·</span>
          <a
            href="mailto:evaluation@example.invalid?subject=CFD%20Harness%20Pilot%20Inquiry"
            className="text-sky-300 hover:text-sky-200"
            title="Placeholder mailto until a real evaluation contact is configured"
          >
            Pilot / bring-your-own-case inquiry
          </a>
        </div>
      </section>

      {/* Stage 5 GoldOps · BatchMatrix system-pulse view. Sits between the
          buyer hero and the student framing so a casual visitor sees
          actual cross-case verdict status before drilling into a card. */}
      <section className="mb-10">
        <BatchMatrix />
      </section>

      {/* Stage 6 ExportPack · dual-format download cards + manifest summary.
          One click below the matrix lets the audience pull the same data
          they just saw, structured for independent verification. */}
      <section className="mb-10">
        <ExportPanel />
      </section>

      {/* Student-facing framing moved below the buyer hero — supporting teaser,
          not primary headline. Keeps /learn useful as a teaching surface
          without pretending the CTA audience is a student. */}
      <section className="mb-10 max-w-2xl">
        <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-surface-500">
          Canonical CFD Problems · Teaching surface
        </p>
        <h2 className="mt-2 text-xl font-semibold leading-snug text-surface-100">
          用十个经典流动问题，看懂 CFD 的验证思维。
        </h2>
        <p className="mt-3 text-[14px] leading-relaxed text-surface-300">
          每一个案例都配有对应的历史文献、黄金标准数据、以及最容易踩的陷阱。
          你会看到"算出一个数字"和"算对"之间的距离——这才是 CFD 真正的门槛。
          对已经在做工程 CFD 的人，这些 case 也是对我们 physics_contract 和
          comparator 诚实度的压力测试。
        </p>
      </section>

      {/* Catalog grid */}
      <section>
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-sm font-medium uppercase tracking-[0.14em] text-surface-300">
            10 个经典案例
          </h2>
          <p className="text-[12px] text-surface-500">
            按学习路径排序 · 入门 → 进阶 → 高阶
          </p>
        </div>

        <ul className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {LEARN_CASES.map((c) => (
            <li key={c.id}>
              <CatalogCard caseData={c} indexEntry={indexById.get(c.id)} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function RunDistributionPill({ summary }: { summary: CaseIndexEntry["run_summary"] }) {
  if (!summary || summary.total === 0) return null;
  const counts = summary.verdict_counts;
  const chips: { label: string; color: string }[] = [];
  if (counts.PASS) chips.push({ label: `${counts.PASS} PASS`, color: "text-contract-pass" });
  if (counts.HAZARD) chips.push({ label: `${counts.HAZARD} HAZARD`, color: "text-contract-hazard" });
  if (counts.FAIL) chips.push({ label: `${counts.FAIL} FAIL`, color: "text-contract-fail" });
  if (counts.UNKNOWN) chips.push({ label: `${counts.UNKNOWN} UNKNOWN`, color: "text-surface-500" });
  return (
    <div className="flex flex-wrap items-baseline gap-2 text-[11px]">
      <span className="mono text-surface-400">{summary.total} runs ·</span>
      {chips.map((c, i) => (
        <span key={i} className={`mono ${c.color}`}>{c.label}</span>
      ))}
    </div>
  );
}

function CatalogCard({
  caseData,
  indexEntry,
}: {
  caseData: LearnCase;
  indexEntry: CaseIndexEntry | undefined;
}) {
  return (
    <Link
      to={`/learn/cases/${caseData.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-lg border border-surface-800 bg-surface-900/60 transition-colors hover:border-sky-700/60 hover:bg-surface-900"
    >
      {/* Illustration panel */}
      <div className="relative aspect-[3/2] bg-gradient-to-b from-surface-900 to-surface-950 px-4 py-2 text-surface-100">
        <CaseIllustration caseId={caseData.id} className="h-full w-full text-surface-100" />
        <span
          className={`absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-surface-900/90 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-surface-300`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${DIFFICULTY_DOT[caseData.difficulty]}`} aria-hidden />
          {DIFFICULTY_LABEL[caseData.difficulty]}
        </span>
      </div>

      {/* Text body */}
      <div className="flex flex-1 flex-col gap-2 px-5 py-4">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="text-[17px] font-semibold text-surface-100">
            {caseData.headline_zh}
          </h3>
          <span className="text-[11px] text-surface-500">
            {caseData.headline_en}
          </span>
        </div>
        <p className="text-[13px] leading-relaxed text-surface-400 line-clamp-2">
          {caseData.teaser_zh}
        </p>
        {indexEntry && indexEntry.run_summary.total > 0 && (
          <div className="pt-1">
            <RunDistributionPill summary={indexEntry.run_summary} />
          </div>
        )}
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="mono text-[11px] text-surface-500">
            {caseData.canonical_ref}
          </span>
          <span className="text-[12px] text-sky-400 group-hover:text-sky-300">
            进入 →
          </span>
        </div>
      </div>
    </Link>
  );
}
