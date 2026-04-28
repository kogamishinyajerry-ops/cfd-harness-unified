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

import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { Step3SetupBC } from "./step_panel_shell/steps/Step3SetupBC";
import { Step4SolveRun } from "./step_panel_shell/steps/Step4SolveRun";
import { Step5ResultsView } from "./step_panel_shell/steps/Step5ResultsView";
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
      // rendered in the center pane. The URL is gated on Step 2 being
      // completed — pre-mesh, /mesh/render returns 404 (the underlying
      // file doesn't exist yet); without gating, the Viewport rendered
      // a hostile red error banner ("Viewport error (fetch): glb fetch
      // returned HTTP 404") that the user reported as a UI 404 bug.
      // Gated state shows the friendly viewportEmptyHint instead.
      format: "glb",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
      gateOnStepCompletion: 2,
    },
    taskPanelComponent: Step2Mesh,
    // Step 2 [AI 处理] is the mesh-generation trigger — wired in spec_v2
    // §E Step 5. The Step2Mesh body registers its mesh action with the
    // shell on mount via the registerAiAction prop.
    aiActionWiredInTierA: true,
    viewportEmptyHint:
      "Step 2 · Mesh — pick mesh mode in the right rail and click [AI 处理] to generate the polyMesh. The wireframe will appear here once gmsh + gmshToFoam complete.",
  },
  {
    id: 3,
    shortLabel: "Setup",
    longLabel: "3 · Setup BC",
    viewportConfig: {
      // Show the meshed wireframe — Step 3's BC patches are written
      // ON this mesh, so visually re-using the Step 2 viewport is the
      // right reference image for the user.
      format: "glb",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
      gateOnStepCompletion: 2,
    },
    taskPanelComponent: Step3SetupBC,
    aiActionWiredInTierA: true,
  },
  {
    id: 4,
    shortLabel: "Solve",
    longLabel: "4 · Solve",
    viewportConfig: {
      format: "glb",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
      gateOnStepCompletion: 2,
    },
    taskPanelComponent: Step4SolveRun,
    aiActionWiredInTierA: true,
  },
  {
    id: 5,
    shortLabel: "Results",
    longLabel: "5 · Results",
    viewportConfig: {
      format: "glb",
      glbUrl: (caseId) =>
        caseId ? `/api/cases/${caseId}/mesh/render` : null,
      stlUrl: () => null,
      gateOnStepCompletion: 2,
    },
    taskPanelComponent: Step5ResultsView,
    aiActionWiredInTierA: true,
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
  //
  // Round-1 Codex Finding 2: a parallel state flag tracks whether an
  // action is currently registered. The shell now gates the
  // StepNavigation [AI 处理] enabled state on BOTH the step's
  // aiActionWiredInTierA flag AND this state — without it, the button
  // would be enabled on Step 2's first render before Step2Mesh's
  // useEffect runs, and the first click would be a silent no-op.
  const activeAiActionRef = useRef<(() => Promise<void>) | null>(null);
  const [hasRegisteredAiAction, setHasRegisteredAiAction] = useState(false);
  const registerAiAction = useCallback(
    (action: (() => Promise<void>) | null) => {
      activeAiActionRef.current = action;
      setHasRegisteredAiAction(action !== null);
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

  // Probe-on-mount: stepStates is in-memory, so a page refresh after
  // meshing would lose the "Step 2 completed" signal and re-gate the
  // mesh viewport. HEAD /mesh/render to detect a pre-existing polyMesh
  // and restore the completed state. 200 = mesh artifacts on disk →
  // mark Step 2 completed; any other status leaves it pending.
  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    fetch(`/api/cases/${encodeURIComponent(caseId)}/mesh/render`, {
      method: "HEAD",
    })
      .then((resp) => {
        if (cancelled) return;
        if (resp.ok) {
          setStepStates((prev) =>
            prev[2] === "completed" ? prev : { ...prev, 2: "completed" },
          );
        }
      })
      .catch(() => {
        // network errors leave stepStates[2] pending — same outcome as a
        // 404, which is the correct pre-mesh state.
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const activeStep = useMemo(
    () => STEPS.find((s) => s.id === currentStepId) ?? STEPS[0],
    [currentStepId],
  );

  const viewportProps = useMemo(() => {
    const cfg = activeStep.viewportConfig;
    // Gate the URL on the prerequisite step's completion when configured.
    // Without this gate, Step 2's /mesh/render fires pre-mesh and the
    // Viewport renders a red "HTTP 404" error — a routing-style bug from
    // the user's perspective, even though the route works post-mesh.
    if (
      cfg.gateOnStepCompletion !== undefined &&
      stepStates[cfg.gateOnStepCompletion] !== "completed"
    ) {
      return null;
    }
    if (cfg.format === "glb") {
      const glbUrl = cfg.glbUrl(caseId);
      if (glbUrl) return { format: "glb" as const, glbUrl };
    } else if (cfg.format === "stl") {
      const stlUrl = cfg.stlUrl(caseId);
      if (stlUrl) return { format: "stl" as const, stlUrl };
    }
    return null;
  }, [activeStep, caseId, stepStates]);

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
            disabled={aiInFlight}
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
                  {activeStep.viewportEmptyHint ??
                    `Viewport for step ${currentStepId} wires up in a later M-PANELS implementation step.`}
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
              // aiInFlight tracking + error capture. The button is
              // enabled only when (a) the step's metadata says its AI
              // action is wired in Tier-A AND (b) the step body has
              // actually registered its action with the shell — Codex
              // Round-1 Finding 2 race fix.
              onAiProcess:
                activeStep.aiActionWiredInTierA && hasRegisteredAiAction
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
