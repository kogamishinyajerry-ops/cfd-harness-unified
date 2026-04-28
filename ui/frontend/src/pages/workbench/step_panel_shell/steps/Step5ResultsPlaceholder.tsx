// Step 5 · Results (placeholder · M-VIZ.results scope). Tier-A renders
// the existing BcCheckCard + completion-artifact list with a stub for the
// field overlay.

import type { StepTaskPanelProps } from "../types";

export function Step5ResultsPlaceholder(_props: StepTaskPanelProps) {
  return (
    <div className="space-y-3 p-3">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 5 · Results
      </h2>
      <p className="text-[12px] text-surface-400">
        Validate against literature, inspect convergence, overlay scalar
        fields on the geometry.
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Wires up in <strong className="text-surface-300">M-VIZ.results</strong>{" "}
        (field overlay via /api/cases/&lt;id&gt;/results/&lt;run&gt;/field/&lt;name&gt;
        with colormap mapping). Today this step shows the existing
        BcCheckCard + completion artifacts.
      </p>
    </div>
  );
}
