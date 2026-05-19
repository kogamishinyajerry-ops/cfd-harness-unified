// V4 R6 (Codex-driven) · TypeScript mirror of
// ui/backend/services/case_visualize/residual_series.py
// Returned by GET /api/cases/{case_id}/residual-series.

export type ResidualSeriesSource = "log" | "runs" | "empty";

export interface ResidualSeriesPoint {
  /** x-axis position. For source="log", iteration / time-step index.
   *  For source="runs", 1-based oldest→newest run ordinal. */
  x: number;
  /** Initial residual (or final, for run-history) on a linear scale.
   *  Frontend log-transforms before plotting. Always > 0 by contract. */
  y: number;
}

export interface ResidualSeriesPayload {
  case_id: string;
  source: ResidualSeriesSource;
  /** Per-quantity series keyed by name (Ux / Uy / Uz / p / Tilde…). */
  series: Record<string, ResidualSeriesPoint[]>;
  /** Max series length, useful for x-axis bounds. */
  sample_count: number;
  /** Run id of the newest run when source="runs"; null otherwise. */
  latest_run_id: string | null;
  /** Convergence target floor (typically 1e-6). */
  target_floor: number;
  /** True when every series's last sample is at or below target_floor. */
  achieved: boolean;
  /** Human-readable diagnostic string (frontend may surface verbatim). */
  note: string;
}
