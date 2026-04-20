// Mirrors ui/backend/schemas/validation.py (Pydantic v2) 1:1.
// If the backend schema changes, update this file in the same commit.

export type ContractStatus = "PASS" | "HAZARD" | "FAIL" | "UNKNOWN";

export interface CaseIndexEntry {
  case_id: string;
  name: string;
  flow_type: string;
  geometry_type: string;
  turbulence_model: string;
  has_gold_standard: boolean;
  has_measurement: boolean;
  contract_status: ContractStatus;
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

export interface MeasuredValue {
  value: number;
  unit: string;
  source: string;
  run_id: string | null;
  commit_sha: string | null;
  measured_at: string | null;
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

export interface ValidationReport {
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
