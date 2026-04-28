// Step 1 · Geometry Import (placeholder body for the M-PANELS skeleton
// commit · DEC-V61-096 spec_v2 §E Step 2). The real upload + format='glb'
// preview wires up in Step 4 of the implementation sequence (extracted
// from the existing ImportPage.tsx primitives).

import type { StepTaskPanelProps } from "../types";

export function Step1Import(_props: StepTaskPanelProps) {
  return (
    <div className="space-y-3 p-3">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 1 · Geometry import
      </h2>
      <p className="text-[12px] text-surface-400">
        Upload an STL file to scaffold the case. Wires up in M-PANELS
        implementation Step 4 (extract from ImportPage + switch Viewport
        to format='glb' via /api/cases/&lt;id&gt;/geometry/render).
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Placeholder body — skeleton commit only.
      </p>
    </div>
  );
}
