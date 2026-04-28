// Step 2 · Mesh (placeholder body for the M-PANELS skeleton commit ·
// DEC-V61-096 spec_v2 §E Step 2). The real mesh-mode form + [AI 处理]
// trigger + wireframe-glb viewport switch wires up in Step 5 of the
// implementation sequence (extracted from MeshWizardPage primitives).

import type { StepTaskPanelProps } from "../types";

export function Step2Mesh(_props: StepTaskPanelProps) {
  return (
    <div className="space-y-3 p-3">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 2 · Mesh
      </h2>
      <p className="text-[12px] text-surface-400">
        Generate the polyMesh via gmsh + sHM (mesh-mode beginner / power).
        Wires up in M-PANELS implementation Step 5 (extract from
        MeshWizardPage + show wireframe via /api/cases/&lt;id&gt;/mesh/render).
      </p>
      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-500">
        Placeholder body — skeleton commit only.
      </p>
    </div>
  );
}
