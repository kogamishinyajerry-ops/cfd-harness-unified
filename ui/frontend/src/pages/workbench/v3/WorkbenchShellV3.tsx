/**
 * V71.1 · WorkbenchShellV3 · v3 blueprint persistent 4-panel architecture
 *
 * V71-UI-V3-SHELL · the load-bearing workspace shell.
 * Per .planning/blueprints/v3/INDEX.md Image 01 architectural lock:
 *   Row 1: TopBar 40px
 *   Col 1: Activity Bar 48px
 *   Col 2: Left Panel ~260px (collapsible · default open)
 *   Col 3: Center (Pipeline Strip 44px + Viewport Toolbar 36px + Canvas +
 *                  Bottom Panel toggle bar)
 *   Col 4: Right Panel ~340px (collapsible · default open) · tabs:
 *          Inspector / Advisor / TruthChain
 *
 * SINGLE accent: sand-coral #b78b65 (v3.accent token) · used ONLY for
 *   active step indicator / active viewport mode / active right-panel tab /
 *   currently-running indicator / one critical advisor signal.
 *
 * Routes: /workbench/v3/case/:caseId?step=N
 *
 * Mounting context: this is a PARALLEL route to existing workbench surfaces.
 * V71 does NOT migrate legacy /workbench routes · those continue working.
 * V72+ may migrate. This file is the v3 SSOT.
 */
import { useState, useCallback, useEffect, useRef, type ReactNode } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CaseBrowserV3 } from "./components/CaseBrowserV3";
import { PipelineStripV3 } from "./components/PipelineStripV3";
import { ViewportToolbarV3 } from "./components/ViewportToolbarV3";
import { RightPanelV3 } from "./components/RightPanelV3";
import { BottomPanelV3 } from "./components/BottomPanelV3";
import { ActivityBarV3 } from "./components/ActivityBarV3";
import { TopBarV3 } from "./components/TopBarV3";
import { DemoBannerV4 } from "./components/DemoBannerV4";
import { DemoSandboxV5 } from "./components/DemoSandboxV5";
import { ProvenanceCardV5 } from "./components/ProvenanceCardV5";
import { LiveSolverPillV7 } from "./components/LiveSolverPillV7";
import { useSolverRunStateV7 } from "./hooks/useSolverRunStateV7";
import { usePostRunHandoffV7 } from "./hooks/usePostRunHandoffV7";
import { useSolverConfigStateV8 } from "./hooks/useSolverConfigStateV8";
import { readInjectionState } from "./components/solver_config_injection";
import type { BridgeArtifact } from "@/data/run_artifact_reader";
import {
  matchAdvisorPatterns,
  type RunArtifactSlice,
} from "@/data/advisor_pattern_matcher";
import {
  V9_ADVISOR_RULES,
  V9_RULESET_VERSION,
} from "@/data/v9_advisor_rules";

const TOUR_LAST_STEP = 6;

/**
 * V90.4 · adapt BridgeArtifact (V6 shape) → RunArtifactSlice (V9.B input).
 * BridgeArtifact's `residuals` is `Record<string, number>` (single value);
 * V9.B's slice expects `Record<string, number[]>` (history). When history
 * unavailable, we pass undefined so history-dependent rules return null
 * gracefully (graceful degrade · matcher won't crash).
 */
function adaptBridgeArtifactToSlice(
  bridge: BridgeArtifact,
): RunArtifactSlice {
  return {
    run_id: bridge.run_id,
    case_id: bridge.case_id,
    success: bridge.success,
    exit_code: bridge.exit_code,
    // V90 scope: BridgeArtifact shape only carries single-value residuals.
    // History-based rules (R1 oscillation, R7 plateau) won't fire without
    // a history array. V91+ candidate: extend BridgeArtifact / RunDetail
    // to expose per-iter history.
    residuals: undefined,
    forces: undefined,
    convergence_stats: undefined,
    gold_delta: undefined,
    // W3.1 · DEC-V61-215 · forward-compat carry-through.
    // bridge.regions is populated once W3.2 emits manifest["regions"] into
    // the bridge/run-detail backend payload. Until then undefined → R13–R16 silent.
    regions: bridge.regions ?? undefined,
  };
}
import { MainCanvasV3 } from "./components/MainCanvasV3";
import { MultiCaseRibbonV3 } from "./components/MultiCaseRibbonV3";
import {
  RightPanelErrorBoundary,
  BottomPanelErrorBoundary,
  MainCanvasErrorBoundary,
  MultiCaseRibbonErrorBoundary,
} from "./components/ErrorBoundaryV3";
import { useV3Keyboard } from "./hooks/useV3Keyboard";

export type StepId = 1 | 2 | 3 | 4 | 5;
export type ViewportMode =
  | "geometry"
  | "mesh"
  | "bc"
  | "field"
  | "residuals"
  | "report";
export type RightPanelTab = "inspector" | "advisor" | "truthchain";

interface WorkbenchShellV3Props {
  /** Optional initial overrides (mostly for tests / storybook). */
  initialViewportMode?: ViewportMode;
  initialRightTab?: RightPanelTab;
  /** Optional content slot for the main canvas (defaults to MainCanvasV3). */
  canvasSlot?: ReactNode;
}

const DEFAULT_VIEWPORT_FOR_STEP: Record<StepId, ViewportMode> = {
  1: "geometry",
  2: "mesh",
  3: "bc",
  4: "residuals",
  5: "report",
};

export function WorkbenchShellV3({
  initialViewportMode,
  initialRightTab,
  canvasSlot,
}: WorkbenchShellV3Props = {}) {
  const params = useParams<{ caseId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const stepParam = Number(searchParams.get("step")) as StepId;
  const stepId: StepId =
    stepParam >= 1 && stepParam <= 5 ? (stepParam as StepId) : 1;
  const caseId = params.caseId ?? null;

  // V75.3 · URL state resumability · 3 aspects survive page refresh:
  //   ?view=geometry|mesh|bc|residuals|report|forces
  //   ?tab=inspector|advisor|truthchain
  //   ?btab=open|closed
  // Engineers can paste a deep-link and land in the exact same UI state.
  const VALID_VIEWPORTS: ReadonlyArray<ViewportMode> = [
    "geometry",
    "mesh",
    "bc",
    "field",
    "residuals",
    "report",
  ];
  const VALID_TABS: ReadonlyArray<RightPanelTab> = [
    "inspector",
    "advisor",
    "truthchain",
  ];
  const urlView = searchParams.get("view");
  const urlTab = searchParams.get("tab");
  const urlBtab = searchParams.get("btab");
  // V83.3 · V5.B · ?failmode=1 mounts the failure-mode showcase in Advisor.
  const failmodeActive = searchParams.get("failmode") === "1";
  // V83.5 · V5.D · detect tour completion (last beat → Finish press clears
  // tour while demo stays 1, then both clear) · track prev tour-step in a
  // ref to spot the "was-at-last → now-cleared" transition.
  const tourStepNum = Number(searchParams.get("tour")) || 0;
  const prevTourStepRef = useRef<number>(tourStepNum);
  const maxStepWalkedRef = useRef<number>(1);
  const [provenanceJustFinished, setProvenanceJustFinished] =
    useState<boolean>(false);
  useEffect(() => {
    const prev = prevTourStepRef.current;
    // Track furthest step reached during tour (used by provenance card)
    if (tourStepNum > maxStepWalkedRef.current) {
      maxStepWalkedRef.current = tourStepNum;
    }
    // Only count "Finish" — went from last beat to 0/cleared (NOT a Skip
    // from middle of the tour, NOT a back-step in cinematic mode).
    if (prev === TOUR_LAST_STEP && tourStepNum === 0) {
      setProvenanceJustFinished(true);
    } else if (tourStepNum > 0) {
      // User started a new tour (or moved in one) · reset card state
      setProvenanceJustFinished(false);
    }
    prevTourStepRef.current = tourStepNum;
  }, [tourStepNum]);

  // V87.1 · V7 substantiation · wire solver state machine + post-run handoff.
  // V130 invariant: handoff.notifyCompleted is passed as the onRunCompleted
  // callback · the chain user-click → V7.B request → SSE done → handoff
  // is fully user-initiated · no useEffect that calls request() exists.
  const postRunHandoff = usePostRunHandoffV7();
  const solverRunState = useSolverRunStateV7({
    onRunCompleted: postRunHandoff.notifyCompleted,
  });

  // V87.1 · V6 bridge hand-off · GET /api/cases/{id}/run-history/{runId}
  // when a real run completes, feed the resulting RunDetail into the V6
  // bridgeArtifact pipeline for V6.B/V6.C/V6.D consumption.
  const handoffRunId = postRunHandoff.lastCompletedRunId;
  const handoffCaseId = postRunHandoff.lastCompletedCaseId;
  const runDetailQuery = useQuery({
    queryKey: ["v87-bridge-run-detail", handoffCaseId, handoffRunId],
    queryFn: () =>
      api.getRunDetail(handoffCaseId as string, handoffRunId as string),
    enabled: Boolean(handoffCaseId) && Boolean(handoffRunId),
    staleTime: 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
  // RunDetail is structurally compatible with BridgeArtifact (V6.A subset).
  const bridgeArtifact: BridgeArtifact | null =
    runDetailQuery.data
      ? (runDetailQuery.data as unknown as BridgeArtifact)
      : null;

  // V90.4 · V9.A wiring · compute post-run advisor matches from
  // bridgeArtifact (the completed run's RunDetail). Pure-function call
  // · no I/O · no LLM · deterministic. When bridgeArtifact is null
  // (no completed run yet OR query in flight), V9.A renders empty-state.
  const v9AdvisorMatches = bridgeArtifact
    ? matchAdvisorPatterns(
        adaptBridgeArtifactToSlice(bridgeArtifact),
        V9_ADVISOR_RULES,
      )
    : [];

  // V87.1 · Reverse-stop #20 · disable Run button (still mount-visible · the
  // button itself handles disabled state) when URL mode is read-only:
  // sandbox / cinematic tour / bridge. Compute meshReady/bcSetup from
  // stepId for V87 (Step ≥4 implies the pipeline gated mesh + BC). A
  // proper readiness check would consult /api/cases/{id} completeness;
  // V87 keeps the heuristic simple to stay scoped to wiring.
  const demoActive = searchParams.get("demo");
  const bridgeRequested = searchParams.get("bridge") === "1";
  const readOnlyMode =
    demoActive === "1" || demoActive === "2" || bridgeRequested;
  const meshReady = stepId >= 2 && !readOnlyMode;

  // V88.2 · V8 wiring · GET controlDict to seed editor + state machine.
  // Skipped in read-only modes (sandbox/cinematic/bridge). Errors do not
  // crash the shell — V8.D hook hydrates from null and configReady stays
  // false until the user opens + commits an edit OR the GET succeeds.
  const controlDictQuery = useQuery({
    queryKey: ["v88-controldict", caseId],
    queryFn: () => api.getRawDict(caseId!, "system/controlDict"),
    enabled: Boolean(caseId) && !readOnlyMode,
    staleTime: 60_000,
    retry: 0,
    refetchOnWindowFocus: false,
  });
  const initialControlDict = controlDictQuery.data
    ? {
        content: controlDictQuery.data.content,
        etag: controlDictQuery.data.etag,
      }
    : null;
  const solverConfig = useSolverConfigStateV8({
    caseId,
    initial: initialControlDict,
  });
  // V88 reverse-stop #25 · V7.A gating uses shell-level shared state ·
  // V7.A does NOT import V8.D directly. Composition rules:
  //   - When the controlDict GET has NOT yet resolved (loading · error ·
  //     404 — no dict on disk), V8 does NOT gate V7.A · the solver runs
  //     with defaults · V8 is an additive opt-in editor.
  //   - When the GET succeeded AND the user later edited an invalid
  //     value (configReady → false), V7.A IS gated until they fix +
  //     commit or discard.
  // This preserves V7 happy-path behavior + provides the documented V8
  // gating without forcing every case to have a fetchable controlDict.
  const v8Hydrated = controlDictQuery.isSuccess;
  const bcSetup =
    stepId >= 4 &&
    !readOnlyMode &&
    (!v8Hydrated || solverConfig.configReady);

  const requestSolverRun = useCallback(() => {
    if (!caseId) return;
    void solverRunState.request(caseId);
  }, [caseId, solverRunState]);

  const [viewportMode, setViewportModeState] = useState<ViewportMode>(
    (VALID_VIEWPORTS.includes(urlView as ViewportMode)
      ? (urlView as ViewportMode)
      : null) ??
      initialViewportMode ??
      DEFAULT_VIEWPORT_FOR_STEP[stepId],
  );
  const [rightTab, setRightTabState] = useState<RightPanelTab>(
    (VALID_TABS.includes(urlTab as RightPanelTab)
      ? (urlTab as RightPanelTab)
      : null) ??
      initialRightTab ??
      "inspector",
  );
  const [bottomCollapsed, setBottomCollapsedState] = useState<boolean>(
    urlBtab === "open" ? false : urlBtab === "closed" ? true : stepId < 4,
  );

  // URL-syncing setters · V75.3
  const setViewportMode = useCallback(
    (next: ViewportMode | ((current: ViewportMode) => ViewportMode)) => {
      setViewportModeState((current) => {
        const resolved = typeof next === "function" ? next(current) : next;
        setSearchParams(
          (sp) => {
            sp.set("view", resolved);
            return sp;
          },
          { replace: true },
        );
        return resolved;
      });
    },
    [setSearchParams],
  );
  const setRightTab = useCallback(
    (next: RightPanelTab) => {
      setRightTabState(next);
      setSearchParams(
        (sp) => {
          sp.set("tab", next);
          return sp;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );
  const setBottomCollapsed = useCallback(
    (next: boolean | ((current: boolean) => boolean)) => {
      setBottomCollapsedState((current) => {
        const resolved = typeof next === "function" ? next(current) : next;
        setSearchParams(
          (sp) => {
            sp.set("btab", resolved ? "closed" : "open");
            return sp;
          },
          { replace: true },
        );
        return resolved;
      });
    },
    [setSearchParams],
  );

  function handleSetStep(next: StepId) {
    // V75.3 · batch all URL writes in one setSearchParams call so the route
    // re-renders once, not three times (avoids racing the in-flight test
    // assertions that find-by-testid right after the click).
    const defaultForCurrent = DEFAULT_VIEWPORT_FOR_STEP[stepId];
    const nextViewport: ViewportMode =
      viewportMode === defaultForCurrent
        ? DEFAULT_VIEWPORT_FOR_STEP[next]
        : viewportMode;
    const nextBottomCollapsed = next < 4;

    setViewportModeState(nextViewport);
    setBottomCollapsedState(nextBottomCollapsed);
    setSearchParams(
      (sp) => {
        sp.set("step", String(next));
        sp.set("view", nextViewport);
        sp.set("btab", nextBottomCollapsed ? "closed" : "open");
        return sp;
      },
      { replace: true },
    );
  }

  // V72.2 · keyboard shortcuts (Esc collapses bottom panel; 1..5/g/m/b/r/p/f
  // jump steps + viewport; [/] cycle right-panel tabs).
  const handleEscape = useCallback(() => {
    setBottomCollapsed(true);
  }, []);
  useV3Keyboard({
    onSetStep: handleSetStep,
    onSetViewport: setViewportMode,
    onSetRightTab: setRightTab,
    onEscape: handleEscape,
    currentTab: rightTab,
  });

  // V71-UI-V3 · CSS grid template-columns 48 / 260 / 1fr / 340 ·
  // template-rows 40 / 1fr
  return (
    <div
      data-testid="workbench-shell-v3"
      data-v71-ui-shell="true"
      className="h-screen w-screen bg-v3-bg text-v3-textPrimary font-sans grid"
      style={{
        gridTemplateColumns: "48px 260px 1fr 340px",
        gridTemplateRows: "40px 1fr",
      }}
    >
      {/* Row 1: TopBar spans all 4 columns */}
      <div className="col-span-4 row-start-1 border-b border-v3-border relative">
        <TopBarV3 caseId={caseId} stepId={stepId} />
        {/* V80.2 · Demo banner / first-time hint overlay · opt-in only */}
        <DemoBannerV4 />
        {/* V83.2 · V5.A · Demo sandbox mode pill + transition banner · ?demo=2
            V84.5 · multi-case · per-case curated step state
            V87.1 · V6.A bridge artifact feed from V7.D handoff */}
        <DemoSandboxV5
          stepId={stepId}
          caseId={caseId}
          bridgeArtifact={bridgeArtifact}
        />
        {/* V87.1 · V7.C · Live solver run pill in TopBar · sand-coral accent
            · renders only when runState ∈ {starting, running} */}
        <LiveSolverPillV7 runState={solverRunState.state} />
        {/* V83.5 · V5.D · Provenance card on tour completion */}
        <ProvenanceCardV5
          justFinished={provenanceJustFinished}
          caseId={caseId}
          maxStepWalked={maxStepWalkedRef.current}
        />
      </div>

      {/* Row 2 · Col 1: Activity Bar */}
      <div className="row-start-2 border-r border-v3-border">
        <ActivityBarV3 active="workbench" />
      </div>

      {/* Row 2 · Col 2: Left Panel */}
      <div
        data-testid="workbench-left-panel"
        className="row-start-2 border-r border-v3-border overflow-y-auto"
      >
        <CaseBrowserV3 activeCaseId={caseId} />
      </div>

      {/* Row 2 · Col 3: Center workspace (vertical: pipeline / toolbar /
          canvas / bottom toggle) */}
      <div
        data-testid="workbench-center"
        className="row-start-2 flex flex-col min-h-0"
      >
        <PipelineStripV3
          activeStep={stepId}
          onSetStep={handleSetStep}
          caseId={caseId}
        />
        <ViewportToolbarV3
          activeMode={viewportMode}
          onSetMode={setViewportMode}
          activeStep={stepId}
        />
        <div className="flex-1 min-h-0 overflow-hidden">
          {canvasSlot ?? (
            <MainCanvasErrorBoundary panelName="Main canvas">
              <MainCanvasV3
                caseId={caseId}
                stepId={stepId}
                viewportMode={viewportMode}
              />
            </MainCanvasErrorBoundary>
          )}
        </div>
        {stepId === 5 && caseId && (
          <MultiCaseRibbonErrorBoundary panelName="Multi-case ribbon">
            <MultiCaseRibbonV3 caseId={caseId} />
          </MultiCaseRibbonErrorBoundary>
        )}
        <BottomPanelErrorBoundary panelName="Bottom panel">
          <BottomPanelV3
            collapsed={bottomCollapsed}
            onToggle={() => setBottomCollapsed((v) => !v)}
            stepId={stepId}
            caseId={caseId}
            solverRunState={solverRunState.state}
            meshReady={meshReady}
            bcSetup={bcSetup}
            onRequestRun={requestSolverRun}
            onCancelRun={solverRunState.cancel}
            solverConfig={(() => {
              // V89.2 · state-injection harness · env-gated · production
              // discards the URL param silently. When `_v89_inject` is
              // active, override the real V8.D slice with synthetic
              // dirty/diff_open/error data so visual baselines can
              // deterministically capture hard-to-reach UI states.
              const injected = readInjectionState(
                searchParams.get("_v89_inject"),
              );
              if (injected) {
                return {
                  fields: injected.fields,
                  baseline: injected.baseline,
                  state: injected.state,
                  validationErrors: injected.validationErrors,
                  errorMessage: injected.errorMessage,
                  readOnlyMode,
                  // Injection MUST NOT fire mutating fetch (reverse-stop
                  // #29). These handlers are no-ops in injection mode.
                  onFieldChange: () => {},
                  onConfirmCommit: () => {},
                  onDiscard: () => {},
                  forceDiffOpen: injected.forceDiffOpen,
                  injectionKey: injected.injectionKey,
                };
              }
              return {
                fields: solverConfig.fields,
                baseline: solverConfig.baseline,
                state: solverConfig.state,
                validationErrors: solverConfig.validationErrors,
                errorMessage: solverConfig.errorMessage,
                readOnlyMode,
                onFieldChange: solverConfig.setField,
                onConfirmCommit: () => void solverConfig.confirmCommit(),
                onDiscard: solverConfig.discard,
              };
            })()}
          />
        </BottomPanelErrorBoundary>
      </div>

      {/* Row 2 · Col 4: Right Panel */}
      <div
        data-testid="workbench-right-panel"
        className="row-start-2 border-l border-v3-border overflow-y-auto"
      >
        <RightPanelErrorBoundary panelName="Right panel">
          <RightPanelV3
            activeTab={rightTab}
            onSetTab={setRightTab}
            caseId={caseId}
            stepId={stepId}
            viewportMode={viewportMode}
            failmodeActive={failmodeActive}
            postRunRunId={handoffRunId}
            postRunMatches={v9AdvisorMatches}
            postRunRulesetVersion={V9_RULESET_VERSION}
          />
        </RightPanelErrorBoundary>
      </div>
    </div>
  );
}
