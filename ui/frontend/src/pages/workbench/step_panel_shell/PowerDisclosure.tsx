/**
 * V68-A.3 · Engineer Control Rail: advanced-section disclosure wrapper.
 *
 * Step bodies wrap their "engineer-only" advanced controls in this component.
 * Beginner mode renders a single-line preset summary; Power mode reveals the
 * children inline. The component degrades gracefully when no BeginnerPower
 * provider is present (test environments) — defaults to Beginner-mode preset
 * summary so the panel still surfaces an explanation rather than empty space.
 *
 * Per Blueprint v3 §3 "Engineer Control Rail":
 *   - Beginner: preset-driven defaults, summary line, no knobs
 *   - Power: full control surface exposed inline
 *
 * Each step body identifies ONE advanced section per V68-A.3 sub-DEC scope.
 */
import type { ReactNode } from "react";

import { useBeginnerPowerOptional } from "./BeginnerPowerContext";

interface PowerDisclosureProps {
  /** Short label shown alongside the disclosure state. */
  label: string;
  /** Beginner-mode summary text (≤ 1 line preferred). */
  summary: string;
  /** Power-mode rendered children — the actual advanced controls. */
  children: ReactNode;
  /** Optional test-id prefix · `{prefix}-disclosure` + `{prefix}-summary` / `{prefix}-advanced` */
  testIdPrefix?: string;
}

export function PowerDisclosure({
  label,
  summary,
  children,
  testIdPrefix,
}: PowerDisclosureProps) {
  const ctx = useBeginnerPowerOptional();
  const isPower = ctx?.isPower ?? false;
  const prefix = testIdPrefix ?? "power-disclosure";

  return (
    <section
      data-testid={`${prefix}-disclosure`}
      data-mode={isPower ? "power" : "beginner"}
      className="rounded border border-surface-800 bg-surface-950/40 p-3 text-xs text-surface-300"
    >
      <header className="mb-1 flex items-center justify-between">
        <span className="font-medium text-surface-100">{label}</span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
            isPower
              ? "bg-emerald-900/40 text-emerald-300"
              : "bg-surface-800 text-surface-400"
          }`}
        >
          {isPower ? "POWER" : "BEGINNER"}
        </span>
      </header>
      {isPower ? (
        <div data-testid={`${prefix}-advanced`} className="space-y-2">
          {children}
        </div>
      ) : (
        <p data-testid={`${prefix}-summary`} className="text-surface-400">
          {summary}
        </p>
      )}
    </section>
  );
}
