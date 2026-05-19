/**
 * V68-A.4 · Dev-only standalone harness for ViewportModeDispatcher.
 *
 * Renders the dispatcher in isolation so Playwright e2e tests can verify
 * the 6-mode UI without depending on StepPanelShell / case fixtures /
 * MSW. Mounted only in dev (gated by import.meta.env.DEV in App.tsx).
 */
import { useState } from "react";

import { ViewportModeDispatcher } from "@/pages/workbench/step_panel_shell/ViewportMode";

export function ViewportModeDevPage() {
  const [stepId, setStepId] = useState(1);
  return (
    <div className="min-h-screen bg-surface-950 p-4 text-surface-200">
      <h1 className="mb-3 text-sm font-mono uppercase tracking-wider">
        DEV · ViewportModeDispatcher harness
      </h1>
      <div className="mb-3 flex gap-2 text-xs">
        <span>Step ID:</span>
        {[1, 2, 3, 4, 5].map((id) => (
          <button
            key={id}
            data-testid={`dev-step-button-${id}`}
            onClick={() => setStepId(id)}
            className={`rounded px-2 py-0.5 ${
              stepId === id
                ? "bg-emerald-900/40 text-emerald-300"
                : "bg-surface-800 text-surface-400"
            }`}
          >
            {id}
          </button>
        ))}
      </div>
      <div className="h-[500px] rounded border border-surface-800 bg-surface-900/40">
        <ViewportModeDispatcher stepId={stepId}>
          <div className="flex h-full items-center justify-center text-xs text-surface-500">
            (placeholder viewport content)
          </div>
        </ViewportModeDispatcher>
      </div>
    </div>
  );
}
