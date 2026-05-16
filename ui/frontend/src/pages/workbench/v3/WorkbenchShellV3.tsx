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
import { useState, useCallback, type ReactNode } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { CaseBrowserV3 } from "./components/CaseBrowserV3";
import { PipelineStripV3 } from "./components/PipelineStripV3";
import { ViewportToolbarV3 } from "./components/ViewportToolbarV3";
import { RightPanelV3 } from "./components/RightPanelV3";
import { BottomPanelV3 } from "./components/BottomPanelV3";
import { ActivityBarV3 } from "./components/ActivityBarV3";
import { TopBarV3 } from "./components/TopBarV3";
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
      <div className="col-span-4 row-start-1 border-b border-v3-border">
        <TopBarV3 caseId={caseId} stepId={stepId} />
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
          />
        </RightPanelErrorBoundary>
      </div>
    </div>
  );
}
