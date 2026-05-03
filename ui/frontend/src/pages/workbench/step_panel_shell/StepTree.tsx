// Left rail · Fluent-style hierarchical step tree (DEC-V61-117).
//
// V0 (M-PANELS spec_v2 §E Step 3) shipped a flat 5-row list. V61-117
// refactors to a parent/child tree where each parent step optionally
// has a `subNodes[]` array of indented sub-labels rendered when the
// parent is expanded. Matches the canonical Fluent / Star-CCM+
// tree-of-actions mental model CFD engineers carry across tools.
//
// Per user constraint "不需要过多的子菜单", sub-nodes are
// display-only labels in V1 — click navigation / scroll-to-anchor is
// out of scope and may be layered additively in a future DEC.
//
// Test-contract preservation: every existing data-testid and
// data-step-status attribute on parent rows is unchanged. Existing
// StepTree.test.tsx 6-test contract stays green without modification.

import { useEffect, useRef, useState } from "react";

import type { StepDef, StepId, StepStatus } from "./types";

interface StepTreeProps {
  steps: readonly StepDef[];
  currentStepId: StepId;
  stepStates: Record<StepId, StepStatus>;
  onStepClick: (stepId: StepId) => void;
  /** Round-1 Codex Finding 1 (M-PANELS): when an AI action is in
   *  flight, lock step-tree navigation so the user can't navigate
   *  away from a non-abortable in-flight mesh run and discard its
   *  result. Also locks chevron toggles — twiddling expansion mid-
   *  flight is a no-op risk we'd rather avoid. */
  disabled?: boolean;
}

const STATUS_DOT: Record<StepStatus, string> = {
  pending: "bg-surface-700",
  active: "bg-emerald-400",
  completed: "bg-emerald-500",
  error: "bg-rose-500",
  // M-AI-COPILOT: amber dot signals "AI is waiting for user input"
  // — distinct hue from active (emerald) and error (rose) so the
  // engineer can see at a glance that the step is parked, not running.
  awaiting_user: "bg-amber-400",
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
  awaiting_user:
    "border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20",
};

export function StepTree({
  steps,
  currentStepId,
  stepStates,
  onStepClick,
  disabled = false,
}: StepTreeProps) {
  // Expansion model after Codex R1+R2+R3+R4:
  //
  // - `expanded` is the visible disclosure state (drives `aria-expanded`).
  // - The chevron is a pure disclosure toggle (R3): click an expanded
  //   row → collapse; click a collapsed row → expand.
  // - Active-step transitions auto-expand the new step and auto-collapse
  //   the previous one (R1 + R4) — so route-driven step changes update
  //   the disclosure state and stale rows don't accumulate.
  // - `manuallyTouchedRef` (ref, not state — no re-render needed)
  //   records which steps the user has explicitly toggled. Manually-
  //   touched steps are exempt from the auto-collapse / auto-expand
  //   logic, so a user who clicks chevron N to expand an inactive row
  //   will keep that row visible across subsequent navigation (R2),
  //   and a user who clicks chevron N to collapse an active row won't
  //   have it spring back open when they navigate to it again.
  //
  // Trade-off: pinning an already-auto-expanded active row before
  // navigating away requires the click-twice path (collapse → reopen),
  // which marks it manually-touched. Codex R2 P2 flagged this as
  // unergonomic; we accept that tradeoff because R3 P2 (ARIA disclosure
  // semantics) is non-negotiable for assistive tech. A separate pin
  // affordance is a follow-up if engineer dogfood demands it.
  const [expanded, setExpanded] = useState<ReadonlySet<StepId>>(() => {
    const initial = steps.find((s) => s.id === currentStepId);
    return initial?.subNodes && initial.subNodes.length > 0
      ? new Set<StepId>([currentStepId])
      : new Set<StepId>();
  });
  const manuallyTouchedRef = useRef<Set<StepId>>(new Set());
  const prevStepIdRef = useRef<StepId>(currentStepId);

  useEffect(() => {
    const prevId = prevStepIdRef.current;
    if (prevId === currentStepId) return;
    prevStepIdRef.current = currentStepId;
    setExpanded((prev) => {
      const next = new Set(prev);
      // Auto-collapse the previously active step unless the user
      // explicitly toggled it (manual decisions outlive navigation).
      if (!manuallyTouchedRef.current.has(prevId)) next.delete(prevId);
      // Auto-expand the newly active step (when it has sub-nodes)
      // unless the user explicitly toggled it earlier — respect a
      // prior collapse-by-user.
      const target = steps.find((s) => s.id === currentStepId);
      if (
        target?.subNodes &&
        target.subNodes.length > 0 &&
        !manuallyTouchedRef.current.has(currentStepId)
      ) {
        next.add(currentStepId);
      }
      return next;
    });
  }, [currentStepId, steps]);

  const toggleExpanded = (stepId: StepId) => {
    manuallyTouchedRef.current.add(stepId);
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

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
        const hasSubNodes = !!step.subNodes && step.subNodes.length > 0;
        const isExpanded = hasSubNodes && expanded.has(step.id);
        return (
          <div key={step.id} className="flex flex-col gap-0.5">
            <div className="flex items-stretch gap-1">
              {hasSubNodes ? (
                <button
                  type="button"
                  data-testid={`step-tree-chevron-${step.id}`}
                  data-step-expanded={isExpanded ? "true" : "false"}
                  aria-expanded={isExpanded}
                  aria-label={
                    isExpanded
                      ? `Collapse step ${step.id}`
                      : `Expand step ${step.id}`
                  }
                  disabled={disabled}
                  onClick={() => toggleExpanded(step.id)}
                  className="flex w-4 shrink-0 items-center justify-center text-[10px] text-surface-500 hover:text-surface-300 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {/* Chevron triangles — small enough to not steal
                   *  visual weight from the status dot, but large
                   *  enough to be a real click target. */}
                  <span aria-hidden>{isExpanded ? "▼" : "▶"}</span>
                </button>
              ) : (
                <span
                  aria-hidden
                  data-testid={`step-tree-chevron-spacer-${step.id}`}
                  className="w-4 shrink-0"
                />
              )}
              <button
                type="button"
                data-testid={`step-tree-row-${step.id}`}
                data-step-id={step.id}
                data-step-status={status}
                data-step-expanded={
                  hasSubNodes ? (isExpanded ? "true" : "false") : undefined
                }
                data-step-has-subnodes={hasSubNodes ? "true" : "false"}
                disabled={disabled}
                onClick={() => onStepClick(step.id)}
                className={`${ROW_BASE} ${ROW_VARIANT[status]} flex-1 disabled:cursor-not-allowed disabled:opacity-50`}
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
            </div>
            {isExpanded && step.subNodes && (
              <ul
                data-testid={`step-tree-subnodes-${step.id}`}
                className="flex flex-col gap-0.5 pl-7"
              >
                {step.subNodes.map((sub) => (
                  <li
                    key={sub.id}
                    data-testid={`step-tree-subnode-${step.id}-${sub.id}`}
                    data-parent-step-id={step.id}
                    data-subnode-id={sub.id}
                    className="flex items-center gap-1.5 rounded-sm px-2 py-0.5 text-[11px] text-surface-500"
                  >
                    <span aria-hidden className="text-surface-700">
                      •
                    </span>
                    <span className="truncate">{sub.label}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </nav>
  );
}
