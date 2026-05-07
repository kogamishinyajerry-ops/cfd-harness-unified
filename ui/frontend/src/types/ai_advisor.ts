// DEC-V61-160 (N6.4) · Frontend types for AI advisor surfaces.
//
// Mirrors the backend wire schema in
// `ui/backend/schemas/ai_advisor.py`. Schema fields kept in sync
// manually — there is no codegen step for the workbench API in V1.
//
// Hard contract (charter §"Why citation grounding is mandatory"):
//   * Every finding/hypothesis carries a citation that resolves to
//     a real corpus chunk on the server side. The frontend can
//     trust the citation block — it has been verified before reach
//     ing the wire.
//   * `recommended_change` / `suggested_fix` are metadata-only
//     prose. The UI MUST render them as text + copy buttons only —
//     never as actionable controls (no Apply / Submit / Execute).

export type CorpusSource = "openfoam_corpus" | "project_decisions";

export interface CitedChunk {
  chunk_id: string;
  source: CorpusSource;
  path: string;
  sha: string;
  section_anchor: string | null;
  byte_offset: number;
  text: string;
}

export type FindingArea =
  | "geometry"
  | "mesh"
  | "physics"
  | "solver"
  | "output";

export type FindingSeverity = "critical" | "warning" | "info";
export type FindingSource = "llm" | "rule_based";

export interface ReviewFinding {
  severity: FindingSeverity;
  area: FindingArea;
  message: string;
  citation: CitedChunk;
  recommended_change: string | null;
  source: FindingSource;
}

export interface ReviewResponse {
  case_id: string;
  findings: ReviewFinding[];
  llm_available: boolean;
  corpus_sha: string;
  degradation_note: string | null;
  generated_at: string;
}

export type FailureMode =
  | "stalled_residuals"
  | "diverging_residuals"
  | "mesh_quality_critical"
  | "bc_or_physics_setup"
  | "unknown";

export type HypothesisLikelihood = "high" | "medium" | "low";

export interface DiagnosisHypothesis {
  failure_mode: FailureMode;
  likelihood: HypothesisLikelihood;
  summary: string;
  evidence: Record<string, string>;
  citation: CitedChunk;
  suggested_fix: string | null;
  source: FindingSource;
}

export interface DiagnoseResponse {
  case_id: string;
  problem_hint: FailureMode | null;
  hypotheses: DiagnosisHypothesis[];
  llm_available: boolean;
  corpus_sha: string;
  degradation_note: string | null;
  generated_at: string;
}
