// Mirrors ui/backend/schemas/mesh_imported.py — wire types only.

// Request modes the engineer can pick in Step 2's preset radio.
export type MeshRequestMode = "beginner" | "power";

// Response modes the backend can label a run with. Includes "target"
// (DEC-V61-124 / V125 engineer-supplied lc) and "custom" (DEC-V61-135
// / N2.1 structured sizing field).
export type MeshMode = "beginner" | "power" | "target" | "custom";

export type MeshFailingCheck =
  | "case_not_found"
  | "source_not_imported"
  | "gmsh_diverged"
  | "cell_cap_exceeded"
  | "gmshToFoam_failed"
  // DEC-V61-136 (N2.2): structured rejection when a refinement zone
  // has zero spatial overlap with the case AABB.
  | "refinement_zone_invalid";

// DEC-V61-135 (N2.1): structured per-job sizing field. All fields
// optional; setting any one switches gmsh away from preset/target lc
// derivation. Backend MeshSizingField validators (mesh_sizing.py)
// enforce min ≤ base ≤ max plus positivity.
export interface MeshSizingField {
  base_lc?: number | null;
  min_lc?: number | null;
  max_lc?: number | null;
  curvature_target_size?: number | null;
  proximity_layers?: number | null;
}

// DEC-V61-136 (N2.2): refinement zone limits. Keep parity with
// ui/backend/schemas/mesh_refinement.py LEVEL_MIN/LEVEL_MAX.
export const REFINEMENT_LEVEL_MIN = 1;
export const REFINEMENT_LEVEL_MAX = 3;
export type RefinementLevel = 1 | 2 | 3;

export interface BoxRefinementZone {
  geometry: "box";
  // Axis-aligned bounding box: [xmin, ymin, zmin, xmax, ymax, zmax].
  // Backend rejects zero-extent or inverted boxes via Pydantic.
  bbox: [number, number, number, number, number, number];
  level: RefinementLevel;
}

export interface SphereRefinementZone {
  geometry: "sphere";
  center: [number, number, number];
  radius: number;
  level: RefinementLevel;
}

// Discriminated union — JSON-compatible with the backend's
// MeshRefinementZone (Pydantic discriminator on ``geometry``).
export type MeshRefinementZone = BoxRefinementZone | SphereRefinementZone;

export interface MeshSummary {
  cell_count: number;
  face_count: number;
  point_count: number;
  mesh_mode_used: MeshMode;
  polyMesh_path: string;
  msh_path: string;
  generation_time_s: number;
  warning: string | null;
}

export interface MeshSuccessResponse {
  case_id: string;
  mesh_summary: MeshSummary;
}

export interface MeshRejectionDetail {
  reason: string;
  failing_check: MeshFailingCheck | string;
}
