// Step 3 · Setup (placeholder · M-AI-COPILOT + M7-redefined scope).
//
// Tier-A renders informational copy + a direct link to the legacy
// YAML editor route so engineers don't lose access to per-case
// boundary-condition / fluid-property editing while Step 3 awaits
// its M-AI-COPILOT wireup. Per the M-PANELS surface_scan deviation
// D4 (DEC-V61-096), legacy /workbench/case/:caseId/edit stays alive
// as a direct route in M-PANELS Tier-A; M7-redefined will land the
// proper redirect once this step has functional parity.

import { useEffect } from "react";
import { Link } from "react-router-dom";

import type { StepTaskPanelProps } from "../types";

export function Step3SetupPlaceholder({
  caseId,
  registerAiAction,
}: StepTaskPanelProps) {
  // No AI action wired yet — clear any prior registration so the
  // shell renders [AI 处理] disabled with the deferred-tooltip.
  useEffect(() => {
    registerAiAction(null);
    return () => registerAiAction(null);
  }, [registerAiAction]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step3-setup-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 3 · Setup
      </h2>
      <p className="text-surface-400">
        Boundary conditions, fluid properties, solver settings.
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Wires up in <strong className="text-surface-300">M-AI-COPILOT</strong>{" "}
        (per-step AI 处理 buttons) and{" "}
        <strong className="text-surface-300">M7-redefined</strong>{" "}
        (detailed forms).
      </p>
      <div className="flex flex-col gap-2">
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/edit`}
          data-testid="step3-setup-yaml-editor-link"
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
        >
          Open the legacy YAML editor →
        </Link>
        <span className="text-[10px] text-surface-500">
          (direct route still works in M-PANELS Tier-A; deprecated in
          M7-redefined)
        </span>
      </div>
    </div>
  );
}
