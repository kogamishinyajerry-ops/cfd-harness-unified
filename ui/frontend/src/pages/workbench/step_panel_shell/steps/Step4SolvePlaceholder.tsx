// Step 4 · Solve (placeholder · M7-redefined scope). Tier-A renders the
// existing WizardRunPage SSE log behind a static panel + a disabled
// [AI 处理] button.

import type { StepTaskPanelProps } from "../types";

export function Step4SolvePlaceholder(_props: StepTaskPanelProps) {
  return (
    <div className="space-y-3 p-3">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 4 · Solve
      </h2>
      <p className="text-[12px] text-surface-400">
        Run the OpenFOAM solver and watch live residuals + log tail.
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Wires up in <strong className="text-surface-300">M7-redefined</strong>{" "}
        (full solver progress + V61-091 verdict cap autorun for imported
        cases). Today this step shows the existing WizardRunPage SSE
        log behind a static panel.
      </p>
    </div>
  );
}
