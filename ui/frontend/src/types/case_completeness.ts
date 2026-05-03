// DEC-V61-116 · TS mirror of CaseCompletenessReport
// (ui/backend/services/case_completeness/schemas.py).
//
// Wire shape for GET /api/cases/{case_id}/completeness. Used by the
// right-rail "距离入库标准还差 N 项" card in StepPanelShell.

export type CompletenessSeverity = "critical" | "warning" | "info";

export type CaseKind = "whitelist" | "imported_user" | "draft";

export interface MissingField {
  field_path: string;
  severity: CompletenessSeverity;
  why: string;
  // Tier-A: surfaced but UI does not yet auto-apply (V61-117 scope).
  suggested_default: unknown | null;
}

export interface CaseCompletenessReport {
  case_id: string;
  case_kind: CaseKind;
  ready_for_archive: boolean;
  blocked_by_critical: number;
  present_count: number;
  total_count: number;
  // 0..100, 1dp.
  percentage: number;
  missing: MissingField[];
  notes: string[];
}
