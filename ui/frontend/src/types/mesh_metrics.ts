// Mesh metrics · Stage 3 MVP types.
// Mirrors `ui/backend/schemas/mesh_metrics.py`.

export type QcVerdict = "green" | "yellow" | "red" | "gray";

export interface MeshDensityPoint {
  id: string;
  n_cells_1d: number;
  value: number | null;
  has_value: boolean;
}

export interface GciSummary {
  p_obs?: number | null;
  f_extrapolated?: number | null;
  e_21?: number | null;
  e_32?: number | null;
  gci_21_pct?: number | null;
  gci_32_pct?: number | null;
  asymptotic_range_ok?: boolean | null;
  note?: string | null;
}

export interface QcBand {
  gci_32: QcVerdict;
  asymptotic_range: QcVerdict;
  richardson_p: QcVerdict;
  n_levels: QcVerdict;
}

export interface MeshMetrics {
  case_id: string;
  densities: MeshDensityPoint[];
  gci?: GciSummary;
  qc_band: QcBand;
  diagnostic_note?: string;
}
