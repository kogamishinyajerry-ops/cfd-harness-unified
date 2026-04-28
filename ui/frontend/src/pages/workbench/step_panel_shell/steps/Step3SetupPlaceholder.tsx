// Step 3 · Setup (placeholder · M-AI-COPILOT + M7-redefined scope).
// Tier-A renders the case_manifest.yaml read-only preview + a disabled
// [AI 处理] button so engineers see the contract slot.

import type { StepTaskPanelProps } from "../types";

export function Step3SetupPlaceholder(_props: StepTaskPanelProps) {
  return (
    <div className="space-y-3 p-3">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 3 · Setup
      </h2>
      <p className="text-[12px] text-surface-400">
        Boundary conditions, fluid properties, solver settings.
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Wires up in <strong className="text-surface-300">M-AI-COPILOT</strong>{" "}
        (per-step AI 处理 buttons) and{" "}
        <strong className="text-surface-300">M7-redefined</strong>{" "}
        (detailed setup forms). Today this step shows the live{" "}
        case_manifest.yaml preview and the disabled-by-design [AI 处理]
        slot.
      </p>
    </div>
  );
}
