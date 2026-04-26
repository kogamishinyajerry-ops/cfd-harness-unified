// Run history types · M3 · Workbench Closed-Loop main-line.
// Mirrors ui/backend/schemas/run_history.py.

export interface RunSummaryEntry {
  case_id: string;
  run_id: string;
  started_at: string; // ISO-8601 UTC
  duration_s: number;
  success: boolean;
  exit_code: number;
  verdict_summary: string;
  task_spec_excerpt: Record<string, unknown>;
}

export interface RunHistoryListResponse {
  case_id: string;
  runs: RunSummaryEntry[];
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
  source_origin: string; // 'draft' | 'whitelist' | 'unknown'
  task_spec: Record<string, unknown>;
  key_quantities: Record<string, unknown>;
  residuals: Record<string, number>;
}
