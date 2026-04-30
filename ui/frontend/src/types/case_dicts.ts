// DEC-V61-102 M-RESCUE Phase 2 · case_dicts wire types.
//
// Mirrors the Python wire shapes in ui/backend/routes/case_dicts.py.
// The two endpoints exposed:
//
//   GET /api/cases/{id}/dicts/{path:path}     → RawDictGet
//   POST /api/cases/{id}/dicts/{path:path}    → RawDictPostResponse
//   GET /api/cases/{id}/dicts                 → RawDictAllowlistEntry[]

export type RawDictSource = "ai" | "user";

export interface RawDictGet {
  case_id: string;
  path: string;
  content: string;
  source: RawDictSource;
  etag: string;
  edited_at: string | null;
}

export interface RawDictAllowlistEntry {
  path: string;
  exists: boolean;
  source: RawDictSource;
  etag: string | null;
}

export interface RawDictPostBody {
  content: string;
  expected_etag?: string;
}

export interface RawDictValidationIssue {
  severity: string;
  message: string;
}

export interface RawDictPostResponse {
  case_id: string;
  path: string;
  new_etag: string;
  source: RawDictSource;
  warnings: RawDictValidationIssue[];
}

// 409 etag-mismatch detail body.
export interface RawDictEtagMismatchDetail {
  failing_check: "etag_mismatch";
  expected_etag: string;
  current_etag: string;
  hint: string;
}

// 422 validation-failed detail body.
export interface RawDictValidationFailedDetail {
  failing_check: "validation_failed";
  issues: RawDictValidationIssue[];
  hint: string;
}

// 422 symlink_escape detail body (round-3 closure).
export interface RawDictSymlinkEscapeDetail {
  failing_check: "symlink_escape";
  hint: string;
}
