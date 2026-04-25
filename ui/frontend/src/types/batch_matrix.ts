// Batch matrix types · Stage 5 GoldOps MVP.
// Mirrors `ui/backend/schemas/batch_matrix.py`.

import type { ContractStatus } from "@/types/validation";

export interface MatrixCell {
  density_id: string;
  n_cells_1d: number;
  verdict: ContractStatus;
  deviation_pct?: number | null;
  measurement_value?: number | null;
  verdict_reason?: string | null;
}

export interface MatrixRow {
  case_id: string;
  display_name: string;
  display_name_zh?: string;
  canonical_ref?: string;
  cells: MatrixCell[];
  has_workbench_basics: boolean;
}

export interface VerdictCounts {
  PASS: number;
  HAZARD: number;
  FAIL: number;
  UNKNOWN: number;
  total: number;
}

export interface BatchMatrix {
  rows: MatrixRow[];
  densities: string[];
  counts: VerdictCounts;
  n_cases: number;
  n_densities: number;
  diagnostic_note?: string;
}
