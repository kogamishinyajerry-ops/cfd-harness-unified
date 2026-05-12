// Mirrors ui/backend/schemas/mesh_prism_layers.py — wire types only.
// DEC-V61-137 (N2.3): snappyHexMesh addLayers stage.

export const PRISM_EXPANSION_RATIO_MIN = 1.0;
export const PRISM_EXPANSION_RATIO_MAX = 2.0;
export const PRISM_MAX_LAYER_COUNT = 20;

// Per-patch prism configuration.
export interface PatchPrismConfig {
  patch: string;
  first_cell_height: number;
  expansion_ratio: number;
  num_layers: number;
}

// Request body for POST /api/import/{case_id}/mesh/prism-layers.
// v0 ships with `patches: list[PatchPrismConfig]` constrained to
// length 1; multi-patch is N2.3-extend.
export interface MeshPrismLayersRequest {
  patches: PatchPrismConfig[];
}

export type PrismFailingCheck =
  | "case_not_found"
  | "polyMesh_not_ready"
  | "patch_not_found"
  | "snappy_diverged"
  | "snappy_addlayers_did_not_converge"
  | "snappy_container_failed";

export interface PrismLayersSummary {
  cell_count: number;
  face_count: number;
  layers_added: number;
  coverage_fraction: number | null;
  polyMesh_path: string;
  log_path: string;
  generation_time_s: number;
}

export interface PrismLayersSuccessResponse {
  case_id: string;
  prism_summary: PrismLayersSummary;
}

export interface PrismLayersRejectionDetail {
  reason: string;
  failing_check: PrismFailingCheck | string;
}
