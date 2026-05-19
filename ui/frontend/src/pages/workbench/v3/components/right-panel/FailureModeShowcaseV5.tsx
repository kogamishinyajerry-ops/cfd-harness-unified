/**
 * V83.3 · FailureModeShowcaseV5 · V5.B contract
 *
 * Mounted inside AdvisorContent right-panel when `?failmode=1` query is set.
 * Renders 3 canonical CFD failure-mode cards showing what AI advisor catches
 * that a beginner misses · all text human-curated (V80 reverse-stop #7).
 *
 * V130/V132 invariants:
 *   - Pure render from static lookup · zero buttons / forms / mutations
 *   - The "FIX SUGGESTION" is text the engineer copies + applies manually
 */
import { FAILURE_MODES } from "@/data/failure_modes";
import type { FailureMode } from "@/data/failure_modes";

interface FailureModeShowcaseV5Props {
  active: boolean;
}

function FailureCard({
  mode,
  index,
}: {
  mode: FailureMode;
  index: number;
}) {
  return (
    <article
      data-testid={`failure-card-${index + 1}`}
      data-failure-id={mode.id}
      className="border border-v3-border rounded-md px-3 py-2.5 mb-2.5"
    >
      <header className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
        <span className="font-mono">failure mode {index + 1}</span>
        <span className="mx-1.5 text-v3-textTertiary/50">·</span>
        <span>{mode.id.replace(/-/g, " ")}</span>
      </header>
      <h4 className="text-[12.5px] text-v3-textPrimary font-medium leading-snug mb-2">
        {mode.title}
      </h4>

      {/* SYMPTOM · red border */}
      <section
        data-testid="failure-symptom"
        className={`mt-2 pl-2 border-l-2 ${
          mode.symptom.severity === "critical"
            ? "border-v3-wall"
            : "border-v3-symmetry"
        }`}
      >
        <div className="text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary">
          symptom · {mode.symptom.severity}
        </div>
        <p className="text-[12px] text-v3-textPrimary leading-relaxed mt-1">
          <strong className="font-medium">{mode.symptom.headline}</strong>
        </p>
        <p className="text-[11.5px] text-v3-textSecondary leading-relaxed mt-1">
          {mode.symptom.body}
        </p>
      </section>

      {/* AI DIAGNOSIS · sand-coral border */}
      <section
        data-testid="failure-diagnosis"
        className="mt-3 pl-2 border-l-2 border-v3-accent/60"
      >
        <div className="text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary">
          AI diagnosis · {mode.diagnosis.advisor_signal}
        </div>
        <p className="text-[12px] text-v3-textPrimary leading-relaxed mt-1">
          <strong className="font-medium">{mode.diagnosis.headline}</strong>
        </p>
        <p className="text-[11.5px] text-v3-textSecondary leading-relaxed mt-1">
          {mode.diagnosis.body}
        </p>
      </section>

      {/* FIX SUGGESTION · text-secondary (no apply button · V132 invariant) */}
      <section data-testid="failure-fix" className="mt-3 pl-2 border-l-2 border-v3-border">
        <div className="text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary">
          fix · engineer applies manually
        </div>
        <p className="text-[12px] text-v3-textPrimary leading-relaxed mt-1">
          <strong className="font-medium">{mode.fix.headline}</strong>
        </p>
        <p className="text-[11.5px] text-v3-textSecondary leading-relaxed mt-1">
          {mode.fix.body}
        </p>
        <div className="mt-2 text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary border border-v3-border rounded px-1.5 py-0.5 inline-block font-mono">
          {mode.fix.citation.source} · {mode.fix.citation.label}
        </div>
      </section>
    </article>
  );
}

export function FailureModeShowcaseV5({ active }: FailureModeShowcaseV5Props) {
  if (!active) return null;

  return (
    <section
      data-testid="failure-mode-showcase"
      aria-label="AI advisor failure-mode showcase"
      className="mt-4"
    >
      <header className="flex items-baseline justify-between mb-2">
        <h3 className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary">
          failure-mode showcase · what AI catches
        </h3>
        <span className="text-[10px] text-v3-textTertiary font-mono">
          {FAILURE_MODES.length} curated patterns
        </span>
      </header>
      {FAILURE_MODES.map((mode, i) => (
        <FailureCard key={mode.id} mode={mode} index={i} />
      ))}
      <p
        data-testid="failure-mode-v132-footer"
        className="mt-2 text-[10px] text-v3-textTertiary font-mono"
      >
        0 fixes applied by AI · V132 locked · advisory only
      </p>
    </section>
  );
}
