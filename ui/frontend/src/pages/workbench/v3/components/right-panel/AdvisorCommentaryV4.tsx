/**
 * V80.3 · AdvisorCommentaryV4 · 3 curated depth panels on the Advisor tab.
 *
 * Per .planning/blueprints/v4/INDEX.md V4.B + V80 charter §4 sub-DEC roadmap:
 *   - 3 commentary kinds rendered as cards: mesh-quality / convergence / result-interpretation
 *   - Each carries headline + body + citation chip
 *   - Text is human-curated and lives in src/data/advisor_commentary.ts
 *   - No action affordance — read-only, advisory by construction
 *   - Footer reasserts V132 invariant
 *
 * V130/V132 invariants enforced structurally:
 *   - No <button>, <form>, or onClick handler that mutates anything
 *   - The component is GET-equivalent — pure render from static lookup
 *   - 0 actions taken · MUTATING_ROUTES still 9
 */
import {
  getCommentary,
  type CommentaryEntry,
  COMMENTARY_KINDS,
} from "@/data/advisor_commentary";
import type { StepId } from "../../WorkbenchShellV3";

interface AdvisorCommentaryV4Props {
  caseId: string | null;
  stepId: StepId;
}

function CommentaryCard({ entry }: { entry: CommentaryEntry }) {
  return (
    <article
      data-testid={`advisor-commentary-${entry.kind}`}
      data-commentary-kind={entry.kind}
      className="border border-v3-border rounded-md px-3 py-2.5 mb-2.5"
    >
      <header className="flex items-center text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-1.5">
        <span className="font-mono">{entry.kind.replace(/-/g, " ")}</span>
        <span className="mx-1.5 text-v3-textTertiary/50">·</span>
        <span>curated</span>
      </header>
      <h4 className="text-[12.5px] text-v3-textPrimary font-medium leading-snug">
        {entry.headline}
      </h4>
      <p className="mt-1.5 text-[12px] text-v3-textSecondary leading-relaxed">
        {entry.body}
      </p>
      <footer className="mt-2 text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary border border-v3-border rounded px-1.5 py-0.5 inline-block font-mono">
        {entry.citation.source} · {entry.citation.label}
      </footer>
    </article>
  );
}

export function AdvisorCommentaryV4({
  caseId,
  stepId,
}: AdvisorCommentaryV4Props) {
  const set = getCommentary(caseId, stepId);

  return (
    <section
      data-testid="advisor-commentary-v4"
      data-case-id={caseId ?? "__none__"}
      data-step-id={String(stepId)}
      aria-label="AI advisor depth commentary"
      className="mt-4"
    >
      <header className="flex items-baseline justify-between mb-2">
        <h3 className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary">
          depth commentary · step {stepId}
        </h3>
        <span className="text-[10px] text-v3-textTertiary font-mono">
          {COMMENTARY_KINDS.length} kinds · curated
        </span>
      </header>
      {COMMENTARY_KINDS.map((kind) => (
        <CommentaryCard key={kind} entry={set[kind]} />
      ))}
      <p
        data-testid="advisor-commentary-v132-footer"
        className="mt-2 text-[10px] text-v3-textTertiary font-mono"
      >
        0 actions taken · V132 locked · advisory only
      </p>
    </section>
  );
}
