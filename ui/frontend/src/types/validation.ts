// Mirrors ui/backend/schemas/validation.py (Pydantic v2) 1:1.
// If the backend schema changes, update this file in the same commit.

export type ContractStatus = "PASS" | "HAZARD" | "FAIL" | "UNKNOWN";

export type RunCategory =
  | "reference"
  | "real_incident"
  | "under_resolved"
  | "wrong_model"
  | "grid_convergence";

export interface RunDescriptor {
  run_id: string;
  label_zh: string;
  label_en: string;
  description_zh: string;
  category: RunCategory;
  expected_verdict: ContractStatus;
}

export interface RunSummary {
  total: number;
  verdict_counts: Partial<Record<ContractStatus, number>>;
}

export interface CaseIndexEntry {
  case_id: string;
  name: string;
  flow_type: string;
  geometry_type: string;
  turbulence_model: string;
  has_gold_standard: boolean;
  has_measurement: boolean;
  contract_status: ContractStatus;
  run_summary: RunSummary;
}

export interface GoldStandardReference {
  quantity: string;
  ref_value: number;
  unit: string;
  tolerance_pct: number;
  citation: string;
  doi: string | null;
}

export interface Precondition {
  condition: string;
  satisfied: boolean;
  evidence_ref: string | null;
  consequence_if_unsatisfied: string | null;
}

export interface AuditConcern {
  concern_type: string;
  summary: string;
  detail: string | null;
  decision_refs: string[];
}

export interface DecisionLink {
  decision_id: string;
  date: string;
  title: string;
  autonomous: boolean;
}

// DEC-V61-039: profile_verdict + pointwise counts surfaced alongside
// contract_status so the UI can explain split-brain (LDC audit_real_run
// → scalar FAIL, profile PARTIAL 11/17).
export interface ValidationReportExtras {
  profile_verdict: "PASS" | "PARTIAL" | "FAIL" | null;
  profile_pass_count: number | null;
  profile_total_count: number | null;
}

export interface MeasuredValue {
  // DEC-V61-036 G1: value is null when the extractor could not locate the
  // gold's target quantity (MISSING_TARGET_QUANTITY concern is also emitted).
  value: number | null;
  unit: string;
  source: string;
  run_id: string | null;
  commit_sha: string | null;
  measured_at: string | null;
  // DEC-V61-036 G1: the canonical quantity name the extractor targeted.
  quantity?: string | null;
  // DEC-V61-036 G1: one of "comparator_deviation" / "key_quantities_direct"
  // / "key_quantities_alias:<key>" / "key_quantities_profile_sample" /
  // "key_quantities_fallback" (legacy) / "no_numeric_quantity".
  extraction_source?: string | null;
}

export interface CaseDetail {
  case_id: string;
  name: string;
  reference: string | null;
  doi: string | null;
  flow_type: string;
  geometry_type: string;
  compressibility: string | null;
  steady_state: string | null;
  solver: string | null;
  turbulence_model: string;
  parameters: Record<string, unknown>;
  gold_standard: GoldStandardReference | null;
  preconditions: Precondition[];
  contract_status_narrative: string | null;
}

export interface ValidationReport extends ValidationReportExtras {
  case: CaseDetail;
  gold_standard: GoldStandardReference;
  measurement: MeasuredValue | null;
  contract_status: ContractStatus;
  deviation_pct: number | null;
  within_tolerance: boolean | null;
  tolerance_lower: number;
  tolerance_upper: number;
  audit_concerns: AuditConcern[];
  preconditions: Precondition[];
  decisions_trail: DecisionLink[];
}
