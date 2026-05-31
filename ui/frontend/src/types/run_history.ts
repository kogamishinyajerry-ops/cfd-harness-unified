// Run history types · M3 · Workbench Closed-Loop main-line.
// Mirrors ui/backend/schemas/run_history.py.

import type { RegionSlice } from "@/data/advisor_pattern_matcher";

// M4 closed-set categories. Adding a new one needs both backend
// (_FAILURE_CATEGORIES in wizard_drivers.py) and frontend (this union +
// the FAILURE_CATEGORY_LABEL_ZH map below) to stay in sync.
export type FailureCategory =
  | "docker_missing"
  | "openfoam_missing"
  | "mesh_failed"
  | "solver_diverged"
  | "postprocess_failed"
  | "unknown_error";

export interface RunSummaryEntry {
  case_id: string;
  run_id: string;
  started_at: string; // ISO-8601 UTC
  duration_s: number;
  success: boolean;
  exit_code: number;
  verdict_summary: string;
  failure_category?: FailureCategory | null;
  task_spec_excerpt: Record<string, unknown>;
}

export interface RunHistoryListResponse {
  case_id: string;
  runs: RunSummaryEntry[];
}

export interface RecentRunsResponse {
  runs: RunSummaryEntry[];
  total: number;
}

export interface RunDetail {
  case_id: string;
  run_id: string;
  started_at: string;
  ended_at: string | null;
  duration_s: number;
  success: boolean;
  exit_code: number;
  verdict_summary: string;
  error_message: string | null;
  failure_category?: FailureCategory | null;
  // Backend-provided remediation hint matching failure_category. Frontend
  // doesn't compute this — it's the single source of truth from
  // wizard_drivers.failure_remediation().
  failure_remediation?: string | null;
  source_origin: string; // 'draft' | 'whitelist' | 'unknown'
  task_spec: Record<string, unknown>;
  key_quantities: Record<string, unknown>;
  residuals: Record<string, number>;
  /**
   * W3.1 · DEC-V61-215 · per-region CHT snapshots.
   * Forward-compat: populated once W3.2 wires build_manifest() to emit
   * manifest["regions"]. Until then, the backend run-detail payload omits
   * this field → undefined here → R13–R16 silently dormant (correct behavior).
   * Adding this field is ADDITIVE-OPTIONAL: no existing RunDetail literal breaks.
   */
  regions?: RegionSlice[] | null;
}

// Bilingual label map for the FailureBanner / table chip.
export const FAILURE_CATEGORY_LABEL_ZH: Record<FailureCategory, string> = {
  docker_missing: "Docker 缺失",
  openfoam_missing: "OpenFOAM 缺失",
  mesh_failed: "网格生成失败",
  solver_diverged: "求解器发散",
  postprocess_failed: "后处理失败",
  unknown_error: "未知错误",
};
