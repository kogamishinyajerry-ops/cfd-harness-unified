// Step 5 · Results (placeholder · M-VIZ.results scope).
//
// Tier-A links to the existing run-history table route so engineers
// can inspect prior solver runs while M-VIZ.results lands the
// in-viewport field overlay. M-VIZ.results will fetch
// /api/cases/<id>/results/<run>/field/<name> and bake colormap
// values onto the meshed geometry.

import { useEffect } from "react";
import { Link } from "react-router-dom";

import type { StepTaskPanelProps } from "../types";

export function Step5ResultsPlaceholder({
  caseId,
  registerAiAction,
}: StepTaskPanelProps) {
  useEffect(() => {
    registerAiAction(null);
    return () => registerAiAction(null);
  }, [registerAiAction]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step5-results-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 5 · Results
      </h2>
      <p className="text-surface-400">
        Validate against literature, inspect convergence, overlay scalar
        fields on the geometry.
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Wires up in <strong className="text-surface-300">M-VIZ.results</strong>{" "}
        (field overlay via{" "}
        <code className="font-mono">/api/cases/&lt;id&gt;/results/&lt;run&gt;/field/&lt;name&gt;</code>{" "}
        with colormap mapping).
      </p>
      <div className="flex flex-col gap-2">
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/runs`}
          data-testid="step5-results-runs-link"
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
        >
          Open the legacy run-history table →
        </Link>
        <span className="text-[10px] text-surface-500">
          (RunHistoryPage · still works in M-PANELS Tier-A)
        </span>
      </div>
    </div>
  );
}
