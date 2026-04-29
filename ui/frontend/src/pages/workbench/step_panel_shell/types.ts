// Type contract for the M-PANELS three-pane workbench shell
// (DEC-V61-096 spec_v2 §A.5). All step components, the StepTree,
// and the StepPanelShell consume these types.

import type { ComponentType } from "react";

/** The 5 hard-coded step IDs. Engineer-customizable steps are
 *  explicitly out of Tier-A scope (deferred to charter-future). */
export type StepId = 1 | 2 | 3 | 4 | 5;

/** Step state derived from the case + run state.
 *
 *  ``awaiting_user`` is a first-class state added by M-AI-COPILOT
 *  Tier-A (DEC-V61-098): when the AI returns a non-confident envelope
 *  (``confidence: "uncertain" | "blocked"``), the step parks here
 *  with the ``unresolved_questions[]`` rendered in the right-rail
 *  DialogPanel. The state persists across step navigation — the
 *  user can leave Step 3 and come back without losing the dialog
 *  context. ``[继续 AI 处理]`` arms only when all questions are
 *  answered; clicking it transitions back to ``active`` for re-run.
 */
export type StepStatus =
  | "pending"
  | "active"
  | "completed"
  | "error"
  | "awaiting_user";

// ────────── M-AI-COPILOT contract types (DEC-V61-098 spec_v2 §B.2) ──────────

/** Question-kind enumeration mirroring backend
 *  ``ui/backend/schemas/ai_action.py::QuestionKind``. */
export type AIQuestionKind =
  | "face_label"
  | "physics_value"
  | "boundary_type"
  | "free_text";

/** AI confidence enumeration mirroring backend
 *  ``ui/backend/schemas/ai_action.py::AIActionConfidence``. */
export type AIActionConfidence = "confident" | "uncertain" | "blocked";

/** A single unresolved question rendered in the DialogPanel. Mirrors
 *  ``ui/backend/schemas/ai_action.py::UnresolvedQuestion``.
 */
export interface UnresolvedQuestion {
  id: string;
  kind: AIQuestionKind;
  prompt: string;
  needs_face_selection: boolean;
  candidate_face_ids: string[];
  candidate_options: string[];
  default_answer: string | null;
}

/** Standard return shape for every AI action under M-AI-COPILOT.
 *  Mirrors ``ui/backend/schemas/ai_action.py::AIActionEnvelope``.
 *
 *  Frontend uses ``annotations_revision_consumed`` /
 *  ``annotations_revision_after`` to detect stale runs (the
 *  annotations have been edited since the AI started).
 */
export interface AIActionEnvelope {
  confidence: AIActionConfidence;
  summary: string;
  annotations_revision_consumed: number;
  annotations_revision_after: number;
  unresolved_questions: UnresolvedQuestion[];
  next_step_suggestion: string | null;
  error_detail: string | null;
}

/** A face entry in ``face_annotations.yaml`` mirrors
 *  ``ui/backend/services/case_annotations`` schema. Loose schema —
 *  most fields optional so the user can update one face at a time.
 */
export interface FaceAnnotation {
  face_id: string;
  name?: string;
  patch_type?: "patch" | "wall" | "symmetry" | "empty" | "cyclic" | string;
  bc?: Record<string, { type: string; value?: string }>;
  physics_notes?: string;
  confidence?: "user_authoritative" | "ai_confident" | "ai_uncertain";
  annotated_by?: string;
  annotated_at?: string;
}

/** Full annotations document returned by GET /face-annotations. */
export interface AnnotationsDocument {
  schema_version: number;
  case_id: string;
  revision: number;
  last_modified: string;
  faces: FaceAnnotation[];
}

/** PUT body for /face-annotations. */
export interface AnnotationsPutBody {
  if_match_revision: number;
  faces: FaceAnnotation[];
  annotated_by: string;
}

/** PUT 409 response body when revisions conflict. */
export interface AnnotationsRevisionConflictDetail {
  failing_check: "revision_conflict";
  attempted_revision: number;
  current_revision: number;
}

/** Viewport configuration the step prescribes for the center pane.
 *  Tier-A: Step 1 → /geometry/render glb · Step 2 → /mesh/render glb ·
 *  Steps 3-5 fall back to Step 1's geometry as a placeholder background. */
export interface ViewportConfig {
  format: "stl" | "glb" | "image" | "custom" | "none";
  /** Returns the URL to fetch when format='glb', or null if not applicable. */
  glbUrl: (caseId: string) => string | null;
  /** Returns the URL to fetch when format='stl', or null if not applicable. */
  stlUrl: (caseId: string) => string | null;
  /** Returns the URL to fetch when format='image', or null if not
   *  applicable. Used by Phase-1A Steps 3/4/5 — server-rendered PNGs
   *  for the BC overlay, residual history, and velocity slice. */
  imageUrl?: (caseId: string) => string | null;
  /** Optional version key — when this changes the Viewport bumps the
   *  image URL with a query parameter to bust browser cache. Used so
   *  Step 4's residual chart re-fetches after each [AI 处理] click. */
  imageVersionKey?: (stepStates: Record<StepId, StepStatus>) => string;
  /** Render an arbitrary component instead of the standard
   *  vtk.js / image renderers. Used by Phase-1A Step 4's live
   *  residual chart, which subscribes to the SolveStream context
   *  and renders SVG that updates per-event. */
  customViewport?: import("react").ComponentType<{
    caseId: string;
    height: number;
  }>;
  /** When set, the URL only resolves once `stepStates[gateOnStepCompletion]
   *  === "completed"`. Used to suppress the pre-mesh 404 from /mesh/render
   *  (the underlying glb only exists after Step 2 has run). null/undefined
   *  means the URL is always resolved (Step 1's /geometry/render works
   *  immediately after import). */
  gateOnStepCompletion?: StepId;
}

/** Props injected into a step's task-panel body. */
export interface StepTaskPanelProps {
  caseId: string;
  /** Called when this step's primary action ("import file", "generate mesh", etc.)
   *  successfully completes — the shell uses this signal to flip the step status
   *  to `completed`. */
  onStepComplete: () => void;
  /** Called when a step encounters an unrecoverable error. */
  onStepError: (message: string) => void;
  /** Register the step's [AI 处理] action with the shell. The shell wraps
   *  the registered action to track aiInFlight state + dispatch the
   *  StepNavigation's [AI 处理] button click to it. Pass `null` to clear
   *  the registration (e.g. on unmount or when the step has no AI action). */
  registerAiAction: (action: (() => Promise<void>) | null) => void;
}

/** Static descriptor for one step in the 5-step tree. */
export interface StepDef {
  id: StepId;
  /** Single-word label for the StepTree row (e.g. "Import"). */
  shortLabel: string;
  /** "1 · Geometry Import" — used in the TopBar / TaskPanel header. */
  longLabel: string;
  /** What the center pane shows when this step is active. */
  viewportConfig: ViewportConfig;
  /** The right-rail body. */
  taskPanelComponent: ComponentType<StepTaskPanelProps>;
  /** Whether this step's [AI 处理] button is wired in M-PANELS Tier-A.
   *  - true  → button is enabled (Step 2 mesh trigger lands in Step 5 of
   *           spec_v2 §E sequence)
   *  - false → button is disabled with a tooltip pointing at the future
   *           milestone that will wire it (M-AI-COPILOT / M7-redefined /
   *           M-VIZ.results) */
  aiActionWiredInTierA: boolean;
  /** Tooltip when the [AI 处理] button is disabled — points at the
   *  milestone that will wire it. Required when aiActionWiredInTierA=false. */
  aiActionDeferredTooltip?: string;
  /** Copy shown in the empty-viewport placeholder when the step's
   *  viewport URL is gated (gateOnStepCompletion). Defaults to a
   *  generic milestone-pending hint when omitted. */
  viewportEmptyHint?: string;
}

/** Per-step navigation contract surfaced by `<StepNavigation>`. */
export interface StepNavigationContract {
  /** When non-null, the [AI 处理] button fires this on click. Null/undefined
   *  renders the button disabled with the deferred-milestone tooltip. */
  onAiProcess: (() => Promise<void>) | null;
  /** Move to the previous step. The shell handles bounds (no-op at step 1). */
  onPrevious: () => void;
  /** Move to the next step. The shell handles bounds (no-op at step 5). */
  onNext: () => void;
  /** Whether the [下一步] button is enabled. */
  canAdvance: boolean;
  /** Whether the [上一步] button is enabled. */
  canRetreat: boolean;
  /** True while [AI 处理] is in flight; renders the spinner + disables the
   *  navigation buttons. */
  aiInFlight: boolean;
  /** When [AI 处理] errored, this surfaces in the StatusStrip. */
  aiErrorMessage?: string;
}

/** Top-level state the shell threads through every pane. */
export interface ShellState {
  caseId: string;
  /** Currently active step (URL-driven via ?step=N). */
  currentStepId: StepId;
  /** Per-step status map, derived from the case + run state. */
  stepStates: Record<StepId, StepStatus>;
}
