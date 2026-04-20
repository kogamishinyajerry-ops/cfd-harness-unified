import { Link } from "react-router-dom";

import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { LEARN_CASES, type LearnCase } from "@/data/learnCases";

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
  return (
    <div className="mx-auto max-w-6xl px-6 pt-10 pb-16">
      {/* Intro — deliberately short. Teach, don't sell. */}
      <section className="mb-10 max-w-2xl">
        <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-surface-500">
          Canonical CFD Problems
        </p>
        <h1 className="mt-2 text-3xl font-semibold leading-tight text-surface-100">
          用十个经典流动问题，学会
          <span className="text-sky-300"> CFD 的验证思维</span>。
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-surface-300">
          每一个案例都配有对应的历史文献、黄金标准数据、以及最容易踩的陷阱。
          你会看到"算出一个数字"和"算对"之间的距离——这才是 CFD 真正的门槛。
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
              <CatalogCard caseData={c} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function CatalogCard({ caseData }: { caseData: LearnCase }) {
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
