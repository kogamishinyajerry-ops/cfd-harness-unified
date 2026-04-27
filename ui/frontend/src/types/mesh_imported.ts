// Mirrors ui/backend/schemas/mesh_imported.py — wire types only.

export type MeshMode = "beginner" | "power";

export type MeshFailingCheck =
  | "case_not_found"
  | "source_not_imported"
  | "gmsh_diverged"
  | "cell_cap_exceeded"
  | "gmshToFoam_failed";

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
