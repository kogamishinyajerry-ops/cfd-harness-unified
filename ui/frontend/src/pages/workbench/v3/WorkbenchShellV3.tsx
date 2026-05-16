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

  // V71.S · viewport mode is INDEPENDENT of pipeline step · engineer can
  // override at any time · default per step but override persists
  const [viewportMode, setViewportMode] = useState<ViewportMode>(
    initialViewportMode ?? DEFAULT_VIEWPORT_FOR_STEP[stepId],
  );
  const [rightTab, setRightTab] = useState<RightPanelTab>(
    initialRightTab ?? "inspector",
  );
  const [bottomCollapsed, setBottomCollapsed] = useState<boolean>(stepId < 4);

  function handleSetStep(next: StepId) {
    const sp = new URLSearchParams(searchParams);
    sp.set("step", String(next));
    setSearchParams(sp, { replace: true });
    // V71.S · viewport mode auto-adjusts to step default UNLESS engineer
    // already overrode it (we keep their override on step change)
    setViewportMode((current) => {
      const defaultForCurrent = DEFAULT_VIEWPORT_FOR_STEP[stepId];
      if (current === defaultForCurrent) {
        return DEFAULT_VIEWPORT_FOR_STEP[next];
      }
      // engineer had overridden · keep override
      return current;
    });
    // Bottom panel auto-expands at Step 4+
    setBottomCollapsed(next < 4);
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
            <MainCanvasV3
              caseId={caseId}
              stepId={stepId}
              viewportMode={viewportMode}
            />
          )}
        </div>
        {stepId === 5 && caseId && (
          <MultiCaseRibbonV3 caseId={caseId} />
        )}
        <BottomPanelV3
          collapsed={bottomCollapsed}
          onToggle={() => setBottomCollapsed((v) => !v)}
          stepId={stepId}
        />
      </div>

      {/* Row 2 · Col 4: Right Panel */}
      <div
        data-testid="workbench-right-panel"
        className="row-start-2 border-l border-v3-border overflow-y-auto"
      >
        <RightPanelV3
          activeTab={rightTab}
          onSetTab={setRightTab}
          caseId={caseId}
          stepId={stepId}
          viewportMode={viewportMode}
        />
      </div>
    </div>
  );
}
