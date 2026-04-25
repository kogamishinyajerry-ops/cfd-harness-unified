// Story tab: physics contract panel + teaching cards + lineage + glossary +
// reproduction bundle + report skeleton. The case's "first encounter"
// surface — student should be able to read this top-to-bottom and
// understand WHY this case exists, before touching mesh / run / compare.
//
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import { getFlowFields } from "@/data/flowFields";
import { getLearnCase } from "@/data/learnCases";
import type { Precondition, ValidationReport } from "@/types/validation";

import { ScientificComparisonReportSection } from "./ScientificComparisonReport";

// --- Story tab body ----------------------------------------------------

export function StoryTab({
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
