// Step 4 · Solve (placeholder · M7-redefined scope).
//
// Tier-A links to the existing WizardRunPage SSE-driven solver run
// route. M7-redefined will embed live residuals + log tail in this
// task panel and wire [AI 处理] to the solver-launch endpoint.

import { useEffect } from "react";
import { Link } from "react-router-dom";

import type { StepTaskPanelProps } from "../types";

export function Step4SolvePlaceholder({
  caseId,
  registerAiAction,
}: StepTaskPanelProps) {
  useEffect(() => {
    registerAiAction(null);
    return () => registerAiAction(null);
  }, [registerAiAction]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step4-solve-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 4 · Solve
      </h2>
      <p className="text-surface-400">
        Run the OpenFOAM solver and watch live residuals + log tail.
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Wires up in <strong className="text-surface-300">M7-redefined</strong>{" "}
        (full solver progress + V61-091 verdict cap autorun for imported
        cases).
      </p>
      <div className="flex flex-col gap-2">
        <Link
          to={`/workbench/run/${encodeURIComponent(caseId)}`}
          data-testid="step4-solve-run-link"
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
        >
          Open the legacy solver-run page →
        </Link>
        <span className="text-[10px] text-surface-500">
          (SSE-driven WizardRunPage · still works in M-PANELS Tier-A)
        </span>
      </div>
    </div>
  );
}
