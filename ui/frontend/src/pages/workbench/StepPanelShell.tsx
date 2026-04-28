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

import { lazy, Suspense, useCallback, useMemo, useRef, useState } from "react";
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
      // Wired in spec_v2 §E Step 4 (DEC-V61-096): the imported case's
      // geometry is fetched as glb via M-RENDER-API's /geometry/render
      // endpoint and rendered in the center pane.
      format: "glb",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/geometry/render` : null,
      stlUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/geometry/stl` : null,
    },
    taskPanelComponent: Step1Import,
    aiActionWiredInTierA: false,
    aiActionDeferredTooltip:
      "Step 1 has no AI 处理 action — uploading is the engineer's gesture (re-upload at /workbench/import).",
  },
  {
    id: 2,
    shortLabel: "Mesh",
    longLabel: "2 · Mesh",
    viewportConfig: {
      // Wired in spec_v2 §E Step 5 (DEC-V61-096): the polyMesh wireframe
      // is fetched as glb via M-RENDER-API's /mesh/render endpoint and
      // rendered in the center pane. Falls back to the empty placeholder
      // until the mesh is generated (404 from /mesh/render → Viewport
      // surfaces the kind='fetch' status).
      format: "glb",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
    },
    taskPanelComponent: Step2Mesh,
    // Step 2 [AI 处理] is the mesh-generation trigger — wired in spec_v2
    // §E Step 5. The Step2Mesh body registers its mesh action with the
    // shell on mount via the registerAiAction prop.
    aiActionWiredInTierA: true,
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

  // Each step's task-panel calls onStepComplete / onStepError to
  // signal its own status; the shell threads those into stepStates.
  // Step 1 fires complete on mount (the case existing implies the
  // import scaffold ran); Steps 2-5 will fire complete from their own
  // wire-up commits.
  const [stepStates, setStepStates] = useState<Record<StepId, StepStatus>>(
    () => ({
      1: "pending",
      2: "pending",
      3: "pending",
      4: "pending",
      5: "pending",
    }),
  );
  const [lastAction, setLastAction] = useState<string | null>(null);
  const [aiInFlight, setAiInFlight] = useState(false);
  const [aiErrorMessage, setAiErrorMessage] = useState<string | undefined>(
    undefined,
  );
  // Each step registers its own [AI 处理] action with the shell via the
  // registerAiAction prop. Stored in a ref (not state) so the shell can
  // dispatch the latest registered action from inside the wrapped
  // onAiProcess closure without re-creating that closure on every
  // re-render (which would defeat StepNavigation's identity check).
  const activeAiActionRef = useRef<(() => Promise<void>) | null>(null);
  const registerAiAction = useCallback(
    (action: (() => Promise<void>) | null) => {
      activeAiActionRef.current = action;
    },
    [],
  );

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
    setStepStates((prev) =>
      prev[currentStepId] === "completed"
        ? prev
        : { ...prev, [currentStepId]: "completed" },
    );
    setLastAction(`Step ${currentStepId} ready`);
    setAiErrorMessage(undefined);
  }, [currentStepId]);

  const onStepError = useCallback(
    (message: string) => {
      setStepStates((prev) =>
        prev[currentStepId] === "error"
          ? prev
          : { ...prev, [currentStepId]: "error" },
      );
      setLastAction(`Step ${currentStepId} error`);
      setAiErrorMessage(message);
    },
    [currentStepId],
  );

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
            registerAiAction={registerAiAction}
            navigation={{
              // The shell wraps the active step's registered action with
              // aiInFlight tracking + error capture. If no action is
              // registered the button renders disabled (per
              // StepNavigation contract).
              onAiProcess: activeStep.aiActionWiredInTierA
                ? async () => {
                    const action = activeAiActionRef.current;
                    if (!action) return;
                    setAiInFlight(true);
                    setAiErrorMessage(undefined);
                    try {
                      await action();
                    } catch (err) {
                      const msg =
                        err instanceof Error ? err.message : String(err);
                      setAiErrorMessage(msg);
                      setLastAction(`Step ${currentStepId} AI error`);
                    } finally {
                      setAiInFlight(false);
                    }
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
