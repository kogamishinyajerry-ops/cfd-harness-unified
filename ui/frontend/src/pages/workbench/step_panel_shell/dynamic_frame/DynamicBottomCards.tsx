// DEC-V61-202-SUB-M30-CYCLE1 · bottom.cards slot renderer.
//
// Renders the full step-relevant list of audit findings + missing
// fields + step hints, sorted FAIL > WARN > info. Distinct from
// AIAdvisorPanel (V130 LLM-backed) — these cards are deterministic,
// sourced from audit artifacts + completeness report (LLM-offline).
//
// Failure modes:
//   - empty cards array → nothing rendered
//   - per-card body_text empty → title-only card

import type { BottomCard } from "@/types/workbench_frame";

interface DynamicBottomCardsProps {
  cards: BottomCard[];
}

const SEVERITY_TONE: Record<
  BottomCard["severity"],
  { border: string; label: string; dot: string }
> = {
  fail: {
    border: "border-rose-700/50",
    label: "text-rose-300",
    dot: "bg-rose-500",
  },
  warn: {
    border: "border-amber-700/50",
    label: "text-amber-300",
    dot: "bg-amber-400",
  },
  info: {
    border: "border-surface-700",
    label: "text-surface-300",
    dot: "bg-surface-500",
  },
};

const KIND_LABEL: Record<BottomCard["kind"], string> = {
  audit_finding: "审计发现",
  missing_field: "缺字段",
  step_hint: "本步提示",
};

export function DynamicBottomCards({ cards }: DynamicBottomCardsProps) {
  if (cards.length === 0) return null;

  return (
    <section
      data-testid="dynamic-bottom-cards"
      className="flex flex-col gap-1.5 px-3 py-2"
    >
      {cards.map((card, i) => {
        const tone = SEVERITY_TONE[card.severity] ?? SEVERITY_TONE.info;
        return (
          <article
            key={`${card.kind}-${card.title}-${i}`}
            data-testid="bottom-card"
            data-kind={card.kind}
            data-severity={card.severity}
            className={`rounded-sm border bg-surface-950/60 p-2 ${tone.border}`}
          >
            <header className="flex items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-1.5">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${tone.dot}`} />
                <span className={`truncate text-[11px] font-medium ${tone.label}`}>
                  {card.title}
                </span>
              </div>
              <span className="shrink-0 font-mono text-[9px] uppercase tracking-wider text-surface-500">
                {KIND_LABEL[card.kind]}
              </span>
            </header>
            {card.body_text && (
              <p className="mt-1 text-[11px] leading-snug text-surface-400">
                {card.body_text}
              </p>
            )}
            {(card.field_path || card.source_artifact) && (
              <footer className="mt-1 flex items-center gap-2 font-mono text-[9px] text-surface-600">
                {card.field_path && <span>路径 {card.field_path}</span>}
                {card.source_artifact && <span>来源 {card.source_artifact}</span>}
              </footer>
            )}
          </article>
        );
      })}
    </section>
  );
}
