// Preflight types · Stage 4 GuardedRun MVP.
// Mirrors `ui/backend/schemas/preflight.py`.

export type PreflightStatus =
  | "pass"
  | "fail"
  | "partial"
  | "skip"
  // Added per Opus 4.7 review 2026-04-25 ACCEPT_WITH_COMMENTS edge case
  // #4: a single category builder throw degrades to 'indeterminate'
  // rather than 500-ing the whole endpoint.
  | "indeterminate";
export type PreflightCategory =
  | "physics"
  | "schema"
  | "mesh"
  | "gold_standard"
  | "adapter"
  | (string & {}); // open for future categories

export interface PreflightCheck {
  category: PreflightCategory;
  id: string;
  label_zh: string;
  label_en?: string;
  status: PreflightStatus;
  evidence?: string;
  consequence?: string;
}

export interface PreflightCounts {
  pass: number;
  fail: number;
  partial: number;
  skip: number;
  total: number;
}

export interface PreflightSummary {
  case_id: string;
  checks: PreflightCheck[];
  counts: PreflightCounts;
  n_categories: number;
  overall: PreflightStatus;
  diagnostic_note?: string;
}
