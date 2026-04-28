// Type contract for the M-PANELS three-pane workbench shell
// (DEC-V61-096 spec_v2 §A.5). All step components, the StepTree,
// and the StepPanelShell consume these types.

import type { ComponentType } from "react";

/** The 5 hard-coded step IDs. Engineer-customizable steps are
 *  explicitly out of Tier-A scope (deferred to charter-future). */
export type StepId = 1 | 2 | 3 | 4 | 5;

/** Step state derived from the case + run state. */
export type StepStatus = "pending" | "active" | "completed" | "error";

/** Viewport configuration the step prescribes for the center pane.
 *  Tier-A: Step 1 → /geometry/render glb · Step 2 → /mesh/render glb ·
 *  Steps 3-5 fall back to Step 1's geometry as a placeholder background. */
export interface ViewportConfig {
  format: "stl" | "glb" | "none";
  /** Returns the URL to fetch when format='glb', or null if not applicable. */
  glbUrl: (caseId: string) => string | null;
  /** Returns the URL to fetch when format='stl', or null if not applicable. */
  stlUrl: (caseId: string) => string | null;
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
