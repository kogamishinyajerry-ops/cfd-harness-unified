// Left rail · 5-step tree (controlled component). Renders a vertical
// list with active / completed / pending / error visual states. Skeleton
// commit ships the placeholder rendering; the active-step highlight +
// click handler land in the shell-components commit (spec_v2 §E Step 3).

import type { StepDef, StepId, StepStatus } from "./types";

interface StepTreeProps {
  steps: readonly StepDef[];
  currentStepId: StepId;
  stepStates: Record<StepId, StepStatus>;
  onStepClick: (stepId: StepId) => void;
  /** Round-1 Codex Finding 1: when an AI action is in flight, lock
   *  step-tree navigation so the user can't navigate away from a
   *  non-abortable in-flight mesh run and discard its result. */
  disabled?: boolean;
}

const STATUS_DOT: Record<StepStatus, string> = {
  pending: "bg-surface-700",
  active: "bg-emerald-400",
  completed: "bg-emerald-500",
  error: "bg-rose-500",
};

const ROW_BASE =
  "flex items-center gap-2 rounded-sm border px-2 py-1.5 text-left text-[12px] transition";

const ROW_VARIANT: Record<StepStatus, string> = {
  pending:
    "border-surface-800 bg-surface-950/40 text-surface-500 hover:bg-surface-900/40",
  active:
    "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  completed:
    "border-surface-800 bg-surface-900/40 text-emerald-300 hover:bg-surface-900/60",
  error:
    "border-rose-500/40 bg-rose-500/10 text-rose-200",
};

export function StepTree({
  steps,
  currentStepId,
  stepStates,
  onStepClick,
  disabled = false,
}: StepTreeProps) {
  return (
    <nav
      aria-label="Workbench step tree"
      data-testid="step-tree"
      data-disabled={disabled ? "true" : undefined}
      className="flex flex-col gap-1 p-3"
    >
      <h3 className="mb-1 text-[10px] font-mono uppercase tracking-wider text-surface-500">
        Steps
      </h3>
      {steps.map((step) => {
        const status = step.id === currentStepId ? "active" : stepStates[step.id];
        return (
          <button
            key={step.id}
            type="button"
            data-testid={`step-tree-row-${step.id}`}
            data-step-id={step.id}
            data-step-status={status}
            disabled={disabled}
            onClick={() => onStepClick(step.id)}
            className={`${ROW_BASE} ${ROW_VARIANT[status]} disabled:cursor-not-allowed disabled:opacity-50`}
          >
            <span
              aria-hidden
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${STATUS_DOT[status]}`}
            />
            <span className="font-mono text-[11px] text-surface-500">
              {step.id}
            </span>
            <span className="truncate">{step.shortLabel}</span>
          </button>
        );
      })}
    </nav>
  );
}
