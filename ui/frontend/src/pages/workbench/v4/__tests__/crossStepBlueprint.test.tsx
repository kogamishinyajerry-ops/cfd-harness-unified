import { readFileSync } from "node:fs";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  CROSS_STEP_BLUEPRINT_DOCK,
  CROSS_STEP_BLUEPRINT_TASK,
  V4_VIEWPORT_MODES,
} from "../components/crossStepBlueprint";
import { ViewportModeToolbarV4 } from "../components/ViewportModeToolbarV4";
import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

describe("Cross-step blueprint contract", () => {
  it("locks blueprint image 08 to independent viewport inspection", () => {
    expect(CROSS_STEP_BLUEPRINT_TASK).toMatchObject({
      sourceImage: ".planning/blueprints/v3/08-cross-step.png",
      pageTask: "求解仍在运行时，把主视图切到网格检查而不中断 pipeline 状态",
      activePipelineStep: "solver",
      viewportMode: "mesh",
      bottomDock: "residuals",
    });
    expect(V4_VIEWPORT_MODES.map((mode) => mode.id)).toEqual([
      "import",
      "geometry",
      "mesh",
      "physics",
      "boundary",
      "solver",
      "post",
      "doe",
    ]);
    expect(CROSS_STEP_BLUEPRINT_DOCK).toMatchObject({
      activeStep: "solver",
      viewportMode: "mesh",
      content: "residuals",
    });
  });

  it("renders a navigation-only viewport toolbar with explicit cross-step state", () => {
    const changes: V4PipelineStepId[] = [];

    render(
      <ViewportModeToolbarV4
        activeStep="solver"
        viewportMode="mesh"
        onViewportModeChange={(mode) => changes.push(mode)}
      />,
    );

    const root = screen.getByTestId("v4-viewport-mode-toolbar");
    expect(root.getAttribute("data-active-step")).toBe("solver");
    expect(root.getAttribute("data-viewport-mode")).toBe("mesh");
    expect(root.getAttribute("data-cross-step")).toBe("true");
    expect(screen.getByTestId("v4-viewport-mode-mesh").getAttribute("data-active")).toBe("true");
    expect(screen.getByTestId("v4-viewport-mode-solver").getAttribute("data-active")).toBe("false");
    expect(screen.getByTestId("v4-cross-step-hint").textContent).toContain(
      "viewing Mesh while 求解 solves",
    );
    expect(root.textContent).toContain("仅切换视图");

    fireEvent.click(screen.getByTestId("v4-viewport-mode-post"));
    expect(changes).toEqual(["post"]);
  });

  it("keeps non-solver cross-step copy generic and keeps Import selectable", () => {
    render(
      <ViewportModeToolbarV4
        activeStep="boundary"
        viewportMode="mesh"
        onViewportModeChange={() => undefined}
      />,
    );

    expect(screen.getByTestId("v4-viewport-mode-import").getAttribute("data-active")).toBe("false");
    expect(screen.getByTestId("v4-cross-step-hint").textContent).toContain(
      "viewing Mesh while pipeline stays on 边界",
    );
    expect(screen.getByTestId("v4-cross-step-hint").textContent).not.toContain(
      "solves",
    );
  });

  it("wires viewport mode separately from pipeline step across shell, canvas, and right panel", () => {
    const shellSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/WorkbenchShellV4.tsx`,
      "utf8",
    );
    const mainCanvasSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/MainCanvasV4.tsx`,
      "utf8",
    );
    const toolbarSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/ViewportModeToolbarV4.tsx`,
      "utf8",
    );
    const rightPanelSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/RightPanelV4.tsx`,
      "utf8",
    );

    expect(shellSource).toContain("viewportMode");
    expect(shellSource).toContain("viewportOverride");
    expect(shellSource).toContain("if (!viewportOverride)");
    expect(shellSource).toContain("next === viewportMode");
    expect(shellSource).toContain("onViewportModeChange={handleViewportModeChange}");
    expect(mainCanvasSource).toContain("renderForStep(viewportMode");
    expect(mainCanvasSource).toContain("data-active-step={activeStep}");
    expect(mainCanvasSource).toContain("data-viewport-mode={viewportMode}");
    expect(mainCanvasSource).toContain("ViewportModeToolbarV4");
    expect(mainCanvasSource).toContain("v4-viewport-mode-toolbar-frame");
    expect(mainCanvasSource).toContain("v4-cross-step-residual-dock");
    expect(toolbarSource).not.toContain("absolute left-3 top-10");
    expect(rightPanelSource).toContain("viewportMode");
    expect(rightPanelSource).toContain("跨步骤检查");
    expect(rightPanelSource).toContain("viewportModeCards");
    expect(rightPanelSource).toContain("activeSolveCards");
    expect(rightPanelSource).toContain("viewportSummaryCards");
    expect(rightPanelSource).toContain("isSolverMeshCrossStep");
    expect(rightPanelSource).toContain("data-inspector-section={section}");
    expect(rightPanelSource).toContain('"active-solve"');
    expect(rightPanelSource).toContain('section: "mesh-summary"');
    expect(rightPanelSource).toContain('value: "需 checkMesh artifact"');
    expect(rightPanelSource).toContain("viewportModeLabel(effectiveViewportMode)");
  });
});
