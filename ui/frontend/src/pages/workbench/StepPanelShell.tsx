// M-PANELS · top-level workbench shell (DEC-V61-096 spec_v2 §A).
//
// Three-pane layout: TopBar (top) · StepTree (left) ·
// Viewport (center) · TaskPanel (right) · StatusStrip (bottom).
//
// Step state lives in the URL (?step=N) so the back button works,
// deep links work, and no cross-tree state library is needed.
// React Query handles server state per-step inside each step's
// task-panel body.
//
// Skeleton commit (spec_v2 §E Step 2): all step bodies are
// placeholder. Wire-up lands in spec_v2 §E Steps 3-6.

import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

// Lazy-load Viewport so the vtk.js bundle (~190 KB gzipped) is fetched
// only when a step actually surfaces a glb/stl url. Mirrors the
// ImportPage convention established by M-VIZ Codex round-1 P2 #3
// (preserves the §AC#10 +50 KB delta budget).
const Viewport = lazy(() =>
  import("@/visualization/Viewport").then((m) => ({ default: m.Viewport })),
);

import { StatusStrip } from "./step_panel_shell/StatusStrip";
import { Step1Import } from "./step_panel_shell/steps/Step1Import";
import { Step2Mesh } from "./step_panel_shell/steps/Step2Mesh";
import { Step3SetupPlaceholder } from "./step_panel_shell/steps/Step3SetupPlaceholder";
import { Step4SolvePlaceholder } from "./step_panel_shell/steps/Step4SolvePlaceholder";
import { Step5ResultsPlaceholder } from "./step_panel_shell/steps/Step5ResultsPlaceholder";
import { StepTree } from "./step_panel_shell/StepTree";
import { TaskPanel } from "./step_panel_shell/TaskPanel";
import { TopBar } from "./step_panel_shell/TopBar";
import type {
  StepDef,
  StepId,
  StepStatus,
} from "./step_panel_shell/types";

// Static 5-step config. Engineer-customizable steps are explicitly
// out of Tier-A scope (deferred per DEC-V61-096 §Tier-C).
const STEPS: readonly StepDef[] = [
  {
    id: 1,
    shortLabel: "Import",
    longLabel: "1 · Geometry import",
    viewportConfig: {
      // Skeleton ships format='none' so the empty Viewport doesn't
      // try to fetch a glb that may not exist yet for the case_id.
      // Step 4 of the implementation flips this to format='glb' once
      // the upload primitives + format-toggle are in place.
      format: "none",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/geometry/render` : null,
      stlUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/geometry/stl` : null,
    },
    taskPanelComponent: Step1Import,
    aiActionWiredInTierA: false,
    aiActionDeferredTooltip:
      "Step 1 has no AI 处理 action — uploading is the engineer's gesture.",
  },
  {
    id: 2,
    shortLabel: "Mesh",
    longLabel: "2 · Mesh",
    viewportConfig: {
      format: "none",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
    },
    taskPanelComponent: Step2Mesh,
    // Tier-A wires Step 2 [AI 处理] to /api/import/<caseId>/mesh in
    // implementation Step 5; the skeleton commit keeps it disabled.
    aiActionWiredInTierA: false,
    aiActionDeferredTooltip:
      "AI 处理 wires up in M-PANELS Step 5 (mesh trigger via /api/import/<id>/mesh).",
  },
  {
    id: 3,
    shortLabel: "Setup",
    longLabel: "3 · Setup",
    viewportConfig: {
      format: "none",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/geometry/render` : null,
      stlUrl: () => null,
    },
    taskPanelComponent: Step3SetupPlaceholder,
    aiActionWiredInTierA: false,
    aiActionDeferredTooltip:
      "AI 处理 wires up in M-AI-COPILOT (per-step setup buttons).",
  },
  {
    id: 4,
    shortLabel: "Solve",
    longLabel: "4 · Solve",
    viewportConfig: {
      format: "none",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
    },
    taskPanelComponent: Step4SolvePlaceholder,
    aiActionWiredInTierA: false,
    aiActionDeferredTooltip:
      "AI 处理 wires up in M7-redefined (full solver progress).",
  },
  {
    id: 5,
    shortLabel: "Results",
    longLabel: "5 · Results",
    viewportConfig: {
      format: "none",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
    },
    taskPanelComponent: Step5ResultsPlaceholder,
    aiActionWiredInTierA: false,
    aiActionDeferredTooltip:
      "AI 处理 wires up in M-VIZ.results (field overlay).",
  },
] as const;

function clampStepId(raw: string | null): StepId {
  const n = raw ? parseInt(raw, 10) : 1;
  if (n >= 1 && n <= 5) return n as StepId;
  return 1;
}

export function StepPanelShell() {
  const { caseId = "" } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentStepId = clampStepId(searchParams.get("step"));

  // Skeleton state: all steps default to pending. The wire-up commits
  // derive these from the case + run state via react-query.
  const [stepStates] = useState<Record<StepId, StepStatus>>(() => ({
    1: "pending",
    2: "pending",
    3: "pending",
    4: "pending",
    5: "pending",
  }));
  const [lastAction] = useState<string | null>(null);
  const [aiInFlight] = useState(false);
  const [aiErrorMessage] = useState<string | undefined>(undefined);

  const setStep = useCallback(
    (stepId: StepId) => {
      const next = new URLSearchParams(searchParams);
      next.set("step", String(stepId));
      setSearchParams(next, { replace: false });
    },
    [searchParams, setSearchParams],
  );

  const onStepClick = useCallback(
    (stepId: StepId) => setStep(stepId),
    [setStep],
  );

  const onPrevious = useCallback(() => {
    if (currentStepId > 1) setStep((currentStepId - 1) as StepId);
  }, [currentStepId, setStep]);

  const onNext = useCallback(() => {
    if (currentStepId < 5) setStep((currentStepId + 1) as StepId);
  }, [currentStepId, setStep]);

  const onStepComplete = useCallback(() => {
    // Wired in spec_v2 §E Step 4 (Step 1) and Step 5 (Step 2). Skeleton
    // accepts the signal but does not yet flip stepStates.
  }, []);

  const onStepError = useCallback((_message: string) => {
    // Wired in spec_v2 §E Step 4/5. Skeleton accepts the signal.
  }, []);

  const activeStep = useMemo(
    () => STEPS.find((s) => s.id === currentStepId) ?? STEPS[0],
    [currentStepId],
  );

  const viewportProps = useMemo(() => {
    const cfg = activeStep.viewportConfig;
    if (cfg.format === "glb") {
      const glbUrl = cfg.glbUrl(caseId);
      if (glbUrl) return { format: "glb" as const, glbUrl };
    } else if (cfg.format === "stl") {
      const stlUrl = cfg.stlUrl(caseId);
      if (stlUrl) return { format: "stl" as const, stlUrl };
    }
    return null;
  }, [activeStep, caseId]);

  return (
    <div
      data-testid="step-panel-shell"
      data-current-step-id={currentStepId}
      className="flex h-[calc(100vh-1rem)] flex-col overflow-hidden rounded-md border border-surface-800 bg-surface-950"
    >
      <TopBar caseId={caseId} />
      <div className="flex min-h-0 flex-1">
        <div className="w-44 shrink-0 border-r border-surface-800 bg-surface-950/60">
          <StepTree
            steps={STEPS}
            currentStepId={currentStepId}
            stepStates={stepStates}
            onStepClick={onStepClick}
          />
        </div>
        <main
          data-testid="viewport-pane"
          className="flex min-h-0 flex-1 items-stretch"
        >
          <div className="flex flex-1 items-center justify-center p-3">
            {viewportProps ? (
              <div className="w-full">
                <Suspense
                  fallback={
                    <p className="text-[12px] text-surface-500">
                      Loading viewport…
                    </p>
                  }
                >
                  <Viewport {...viewportProps} height={420} />
                </Suspense>
              </div>
            ) : (
              <div
                data-testid="viewport-placeholder"
                className="flex h-full w-full items-center justify-center rounded-md border border-dashed border-surface-800 bg-surface-950/40 p-6 text-center text-[12px] text-surface-500"
              >
                <span>
                  Viewport for step {currentStepId} wires up in a later
                  M-PANELS implementation step.
                </span>
              </div>
            )}
          </div>
        </main>
        <div className="w-72 shrink-0">
          <TaskPanel
            step={activeStep}
            caseId={caseId}
            onStepComplete={onStepComplete}
            onStepError={onStepError}
            navigation={{
              onAiProcess: activeStep.aiActionWiredInTierA
                ? async () => {
                    /* wired in spec_v2 §E Step 5 */
                  }
                : null,
              onPrevious,
              onNext,
              canAdvance: currentStepId < 5,
              canRetreat: currentStepId > 1,
              aiInFlight,
              aiErrorMessage,
            }}
          />
        </div>
      </div>
      <StatusStrip lastAction={lastAction} />
    </div>
  );
}
