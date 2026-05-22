// DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL · v4 ↔ backend step mapping.
//
// V4 declares an 8-step pipeline (import / geometry / mesh / physics /
// boundary / solver / post / doe; see industrial_minimalist.ts). The
// backend decide() endpoint speaks the M3.0 5-step spine (1..5: Geometry,
// Mesh, Physics, BCs, Solve+Postp). This helper bridges them.
//
// Mapping rationale:
//   import / geometry → 1 (Geometry — import is the on-ramp to geometry)
//   mesh              → 2 (Mesh)
//   physics           → 3 (Physics)
//   boundary          → 4 (BCs)
//   solver / post / doe → 5 (Solve+Postp — all run-side steps share the
//                            same backend-frame because solve+postp are
//                            grouped in the M3.0 spine. DOE is a higher-
//                            order solver that orchestrates many runs.)

import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

export type BackendStepId = 1 | 2 | 3 | 4 | 5;

export function v4StepToBackendStep(v4: V4PipelineStepId): BackendStepId {
  switch (v4) {
    case "import":
    case "geometry":
      return 1;
    case "mesh":
      return 2;
    case "physics":
      return 3;
    case "boundary":
      return 4;
    case "solver":
    case "post":
    case "doe":
      return 5;
    default: {
      // TypeScript narrows on exhaustive switch; this is a safety net
      // that fires only if a new v4 step id lands without an update here.
      const _exhaustive: never = v4;
      void _exhaustive;
      return 1;
    }
  }
}
