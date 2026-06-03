// Workflow Monitor · structured per-stage status contract (DEC-V61-226)
// ---------------------------------------------------------------------
// The product decision (chief-engineer assessment, 2026-06-03): build the
// "visible / resumable / traceable CFD workflow runtime" in-house on the
// existing FastAPI + SSE (routes/solver_stream.py) + React substrate rather
// than adopting an external orchestration platform (Trigger.dev). Reasons:
// local-first / offline-runnable / auditable north star (Blueprint v4 +
// four-question gate), no Python<->TS orchestration seam, and the six stages
// already exist as backend routes (import_geometry, preflight, mesh_*,
// case_solve+solver_stream, comparison_report/audit_package).
//
// THIS file is that decision's most load-bearing output: the cross-stage
// status schema. The frontend renders against it now (mock-driven); the
// backend grows a Pydantic mirror + a WorkflowRunner that persists each
// StageStatus to runs/<run_id>/ (resumable) when we wire real data.
//
// HONESTY INVARIANT (the project's defining principle): a run carries an
// explicit `isMock` flag. A mock/design-preview run is ALWAYS visibly stamped
// and can NEVER be mistaken for a real solve — mirrors the backend
// ExecutionResult.is_mock discipline. No fake CFD presented as real.

/** The six canonical CFD workflow stages (maps 1:1 onto existing backend routes). */
export type StageKey =
  | "geometry_intake"
  | "geometry_validation"
  | "mesh_generation"
  | "mesh_quality_check"
  | "solver_run"
  | "result_report";

/**
 * Stage lifecycle. `blocked` is a FIRST-CLASS honest outcome (evidence
 * insufficient / gate not met) — distinct from `failed` (hard error). This
 * mirrors the backend's "evidence-insufficient → BLOCK, never a silent pass".
 */
export type StageState =
  | "pending"
  | "running"
  | "passed"
  | "blocked"
  | "failed";

/** Verdict tone for a single metric — reuses the three-state contract palette. */
export type MetricVerdict = "pass" | "hazard" | "fail" | "info";

export interface StageMetric {
  label: string;
  value: string | number;
  unit?: string;
  /** Optional gate verdict so a number can be colored honestly (e.g. maxSkewness 0.91 → hazard). */
  verdict?: MetricVerdict;
}

export type ArtifactKind =
  | "geometry"
  | "mesh"
  | "field"
  | "log"
  | "report"
  | "table";

export interface StageArtifact {
  name: string;
  kind: ArtifactKind;
  /** null/undefined in mock — wired to a real download/preview URL later. */
  href?: string | null;
}

export interface WorkflowStage {
  key: StageKey;
  title: string;
  state: StageState;
  /** 0..100 — only meaningful while `running`; terminal states pin to 0/100. */
  progress: number;
  /** What the stage is operating on right now, e.g. "starboard wing / leading edge". */
  currentObject?: string;
  metrics: StageMetric[];
  warnings: string[];
  errors: string[];
  artifacts: StageArtifact[];
  /** The advisor's recommended next action when the stage warns/blocks. */
  nextAction?: string;
  /** One-line agent explanation of what this stage did / decided. */
  advisor?: string;
  startedAt?: string;
  durationLabel?: string;
}

export interface WorkflowEdge {
  from: StageKey;
  to: StageKey;
}

export type AdvisorLevel = "info" | "warn" | "block";

export interface AdvisorLogEntry {
  ts: string;
  stage: StageKey;
  level: AdvisorLevel;
  message: string;
}

export interface TimelineEntry {
  stage: StageKey;
  label: string;
  state: StageState;
  at: string;
}

/** The full monitor payload — what `/api/runs/<id>` (future) returns and the page renders. */
export interface WorkflowRun {
  runId: string;
  caseName: string;
  /** HONEST flag — true for the design-preview fixture; the UI stamps it indelibly. */
  isMock: boolean;
  currentStage: StageKey;
  stages: WorkflowStage[];
  edges: WorkflowEdge[];
  advisorLog: AdvisorLogEntry[];
  timeline: TimelineEntry[];
}

/** Lightweight listing entry — GET /api/workflow-runs. */
export interface WorkflowRunSummary {
  runKey: string;
  runId: string;
  caseName: string;
  isMock: boolean;
  currentStage: StageKey;
}

/** Stable display order of stages (used by the graph + timeline). */
export const STAGE_ORDER: StageKey[] = [
  "geometry_intake",
  "geometry_validation",
  "mesh_generation",
  "mesh_quality_check",
  "solver_run",
  "result_report",
];
