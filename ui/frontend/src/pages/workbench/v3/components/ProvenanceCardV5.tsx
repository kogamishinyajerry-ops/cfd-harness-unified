/**
 * V83.5 · ProvenanceCardV5 · V5.D contract · end-of-tour summary
 *
 * Per .planning/blueprints/v5/INDEX.md Contract V5.D:
 *   - Renders ONCE when tour completes (tour-step goes 6→0 OR cinema exit)
 *   - Bottom-right card · NOT modal · NOT full-screen
 *   - 4 stat lines (cases · steps · commentary · citations) · static counts
 *   - "Try sandbox →" link sets ?demo=2 · "× close" dismisses card
 *   - NO analytics beacon · NO fetch/XHR · counts derived from observable state
 *
 * Triggering: parent component tracks "tour was active and just transitioned
 * to 0 or null"; passes `justFinished=true` for one render after which the
 * user dismisses or the card auto-hides on next URL change.
 */
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

interface ProvenanceCardV5Props {
  /** True when a V4 tour just finished (last beat → exit). Parent
   *  computes this from URL state transitions. */
  justFinished: boolean;
  /** Current case_id (for the "cases shown" stat). */
  caseId: string | null;
  /** Max pipeline step reached during the tour (for "steps walked"). */
  maxStepWalked: number;
}

// V83.5 · static stats lookup from V4 + V5 substrate (NO analytics)
const STAT_COMMENTARY_CARDS = 3; // V4.B per (case, step) → 3 cards
const STAT_CITATIONS_PER_TOUR = 12; // Curated commentary + comparator gold + truthchain refs

export function ProvenanceCardV5({
  justFinished,
  caseId,
  maxStepWalked,
}: ProvenanceCardV5Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [closed, setClosed] = useState<boolean>(false);

  // V83.5 · re-open the card when a new tour finishes
  useEffect(() => {
    if (justFinished) setClosed(false);
  }, [justFinished]);

  if (!justFinished || closed) return null;

  const handleSandboxCta = () => {
    const next = new URLSearchParams(searchParams);
    next.set("demo", "2");
    next.delete("tour");
    next.delete("cinema");
    setSearchParams(next, { replace: true });
    setClosed(true);
  };

  const handleClose = () => setClosed(true);

  return (
    <aside
      data-testid="provenance-card"
      role="region"
      aria-label="Tour complete · what you saw"
      className="absolute bottom-3 right-3 z-30 w-[280px] border border-v3-accent/50 bg-v3-bg rounded-md p-3 text-[12px] shadow-lg"
    >
      <header className="flex items-baseline justify-between mb-2">
        <h3 className="text-[11px] uppercase tracking-[0.08em] text-v3-textPrimary font-medium">
          Tour complete · here's what you saw
        </h3>
        <button
          type="button"
          data-testid="provenance-close"
          onClick={handleClose}
          aria-label="Close provenance card"
          className="text-v3-textTertiary hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus text-[14px] leading-none"
        >
          ×
        </button>
      </header>
      <dl className="text-[11.5px] text-v3-textSecondary space-y-1 mt-2">
        <div className="flex items-baseline justify-between">
          <dt className="text-v3-textTertiary">Cases shown</dt>
          <dd
            data-testid="provenance-stats-cases"
            className="font-mono text-v3-textPrimary"
          >
            {caseId ? 1 : 0}
          </dd>
        </div>
        <div className="flex items-baseline justify-between">
          <dt className="text-v3-textTertiary">Pipeline steps walked</dt>
          <dd
            data-testid="provenance-stats-steps"
            className="font-mono text-v3-textPrimary"
          >
            {Math.max(1, Math.min(5, maxStepWalked))}
          </dd>
        </div>
        <div className="flex items-baseline justify-between">
          <dt className="text-v3-textTertiary">Advisor commentary cards</dt>
          <dd
            data-testid="provenance-stats-commentary"
            className="font-mono text-v3-textPrimary"
          >
            ≥{STAT_COMMENTARY_CARDS}
          </dd>
        </div>
        <div className="flex items-baseline justify-between">
          <dt className="text-v3-textTertiary">Citation references</dt>
          <dd
            data-testid="provenance-stats-citations"
            className="font-mono text-v3-textPrimary"
          >
            ≥{STAT_CITATIONS_PER_TOUR}
          </dd>
        </div>
      </dl>
      <footer className="mt-3 pt-2 border-t border-v3-border flex items-center justify-between text-[11px]">
        <button
          type="button"
          data-testid="provenance-sandbox-cta"
          onClick={handleSandboxCta}
          className="text-v3-textPrimary underline decoration-v3-accent decoration-1 underline-offset-2 hover:text-v3-accent focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          Try sandbox mode →
        </button>
        <span className="text-[10px] text-v3-textTertiary font-mono">
          no telemetry sent
        </span>
      </footer>
    </aside>
  );
}
