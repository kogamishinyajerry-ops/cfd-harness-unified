// Mirrors ui/backend/schemas/case_solve.py — wire types only.

export interface SetupBcSummary {
  case_id: string;
  n_lid_faces: number;
  n_wall_faces: number;
  lid_velocity: [number, number, number];
  nu: number;
  reynolds: number;
  written_files: string[];
}

export interface SolveSummary {
  case_id: string;
  end_time_reached: number;
  last_initial_residual_p: number | null;
  last_initial_residual_U: [number | null, number | null, number | null];
  last_continuity_error: number | null;
  n_time_steps_written: number;
  time_directories: string[];
  wall_time_s: number;
  converged: boolean;
}

export interface ResultsSummary {
  case_id: string;
  final_time: number;
  cell_count: number;
  u_magnitude_min: number;
  u_magnitude_max: number;
  u_magnitude_mean: number;
  u_x_mean: number;
  u_x_min: number;
  u_x_max: number;
  is_recirculating: boolean;
}

export interface CaseSolveRejection {
  failing_check: string;
  detail: string;
}

/** Step 5 multi-figure post-processing bundle (2026-04-30). The
 *  artifacts map carries fully-qualified URLs the frontend can
 *  &lt;img src&gt; directly; the backend renders to disk and serves the
 *  cached PNGs. plane_axes documents which 2D plane was auto-picked
 *  (e.g. ['x','y'] for a z-midplane slab). */
export interface ReportBundle {
  final_time: number;
  cell_count: number;
  slab_cell_count: number;
  plane_axes: string[];
  summary_text: string;
  /** Stable token combining final_time + U mtime. The artifact URLs
   *  already embed it as ?v=...; surfaced here so the frontend can
   *  use it as a queryKey suffix or trigger explicit re-mounts. */
  cache_version: string;
  /** Auto-classified case geometry — used to gate semantics that
   *  only make sense for one kind of flow (e.g. the LDC
   *  recirculation banner shouldn't fire on a channel). Values:
   *  "lid_driven_cavity" | "channel" | "unknown". */
  case_kind: "lid_driven_cavity" | "channel" | "unknown";
  artifacts: {
    contour_streamlines: string;
    pressure: string;
    vorticity: string;
    centerline: string;
  };
}
