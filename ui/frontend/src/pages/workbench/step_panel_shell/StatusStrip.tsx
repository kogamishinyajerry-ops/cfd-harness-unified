// Bottom strip · 4 live indicators per V67-C.2 (Blueprint v3 §4 spec).
//
// Four live fields:
//   1. lastAction · short log tail or last-action message
//   2. validation · per-step validation summary (e.g. "ready", "1 BC unmet")
//   3. progress · current step number + total + status icon
//   4. trustState · rolled-up trust indicator (mirrors TopBar but compact)
//
// Backward-compat: lastAction + validation preserved with original
// behaviour. New fields are optional and silently absent when not
// provided.

import type { ReactNode } from "react";

type StepStatus = "idle" | "running" | "done" | "error";

interface StatusStripProps {
  /** Short log tail or last-action message · null hides body but keeps
   *  rail height stable. */
  lastAction?: string | null;
  /** Validation summary from active step (e.g. "ready", "1 BC unmet"). */
  validation?: string | null;
  /** Current step number (1-5) · null when no active step. */
  currentStep?: number | null;
  /** Total step count (default 5). */
  totalSteps?: number;
  /** Status of the current step. */
  stepStatus?: StepStatus;
  /** Rolled-up trust indicator (compact echo of TopBar TrustGate). */
  trustState?: "PASS" | "PASS_WITH_DISCLAIMER" | "FAIL" | "PENDING" | null;
}

const STEP_ICON: Record<StepStatus, string> = {
  idle: "○",
  running: "●",
  done: "✓",
  error: "✗",
};

const STEP_TONE: Record<StepStatus, string> = {
  idle: "text-surface-500",
  running: "text-sky-400",
  done: "text-emerald-400",
  error: "text-rose-300",
};

const TRUST_LABEL: Record<
  Exclude<NonNullable<StatusStripProps["trustState"]>, null>,
  string
> = {
  PASS: "trust ✓",
  PASS_WITH_DISCLAIMER: "trust ✓*",
  FAIL: "trust ✗",
  PENDING: "trust —",
};

const TRUST_TONE: Record<
  Exclude<NonNullable<StatusStripProps["trustState"]>, null>,
  string
> = {
  PASS: "text-emerald-400",
  PASS_WITH_DISCLAIMER: "text-amber-300",
  FAIL: "text-rose-300",
  PENDING: "text-surface-500",
};

function FieldDivider({ children }: { children: ReactNode }) {
  return (
    <span className="flex items-center gap-2 text-surface-400">
      <span className="text-surface-700">·</span>
      {children}
    </span>
  );
}

export function StatusStrip({
  lastAction = null,
  validation = null,
  currentStep = null,
  totalSteps = 5,
  stepStatus = "idle",
  trustState = null,
}: StatusStripProps) {
  return (
    <footer
      data-testid="status-strip"
      className="flex items-center justify-between gap-2 border-t border-surface-800 bg-surface-950/80 px-3 py-1.5 text-[11px] text-surface-500"
    >
      <span
        data-testid="status-strip-last-action"
        className="truncate min-w-0 flex-1"
      >
        {lastAction ?? "—"}
      </span>

      <div className="flex items-center gap-2 shrink-0">
        {currentStep !== null && currentStep !== undefined && (
          <FieldDivider>
            <span
              data-testid="status-strip-progress"
              data-state={stepStatus}
              className={`font-mono ${STEP_TONE[stepStatus]}`}
            >
              {STEP_ICON[stepStatus]} step {currentStep}/{totalSteps}
            </span>
          </FieldDivider>
        )}

        {trustState !== null && trustState !== undefined && (
          <FieldDivider>
            <span
              data-testid="status-strip-trust-state"
              data-state={trustState}
              className={`font-mono ${TRUST_TONE[trustState]}`}
            >
              {TRUST_LABEL[trustState]}
            </span>
          </FieldDivider>
        )}

        {validation !== null && (
          <FieldDivider>
            <span
              data-testid="status-strip-validation"
              className="text-surface-400"
            >
              {validation}
            </span>
          </FieldDivider>
        )}
      </div>
    </footer>
  );
}
