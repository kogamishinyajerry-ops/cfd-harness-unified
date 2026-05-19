import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  SOLVER_BLUEPRINT_KPIS,
  SOLVER_BLUEPRINT_RESIDUAL_SERIES,
  SOLVER_BLUEPRINT_RIGHT_CARDS,
  SOLVER_BLUEPRINT_STREAMLINE_COUNT,
  SOLVER_BLUEPRINT_TASK,
  SOLVER_BLUEPRINT_TELEMETRY,
  SOLVER_BLUEPRINT_TEMPERATURE_HISTORY,
  SOLVER_BLUEPRINT_VELOCITY_RANGE,
} from "../components/solverBlueprint";

describe("Solver blueprint contract", () => {
  it("locks the Solver page task to the original running/convergence blueprint", () => {
    expect(SOLVER_BLUEPRINT_TASK).toMatchObject({
      sourceImage: ".planning/blueprints/v3/05-solve.png",
      pageTask:
        "求解运行页同时呈现真实 CAD/场视口、密集曲线流线、残差/温度 split charts 和 GPU/CPU/MEM telemetry",
      primaryViewport:
        "ViewportV4 geometry.glb + post/surface.vtp + post/streamlines.vtp",
      forbiddenMainSceneFallback:
        "IndustrialBoxScene / StreamlineField hand-drawn SVG scene",
    });
  });

  it("keeps image-1 running KPIs aligned with image-6 convergence state", () => {
    expect(SOLVER_BLUEPRINT_KPIS).toMatchObject({
      estimatedCellsM: 18.76,
      residualP: 2.3e-5,
      pressurePa: 248.6,
      massFlowKgS: 3.62,
      temperatureC: 96.4,
      progressPct: 65,
      iterCurrent: 1250,
      iterTotal: 2000,
    });
    expect(SOLVER_BLUEPRINT_VELOCITY_RANGE).toEqual([0, 40]);
  });

  it("keeps dense curved streamlines and split charts mechanically auditable", () => {
    expect(SOLVER_BLUEPRINT_STREAMLINE_COUNT).toBeGreaterThanOrEqual(60);
    expect(SOLVER_BLUEPRINT_RESIDUAL_SERIES).toHaveLength(3);
    for (const series of SOLVER_BLUEPRINT_RESIDUAL_SERIES) {
      expect(series.samples.length).toBeGreaterThanOrEqual(10);
    }
    expect(SOLVER_BLUEPRINT_TEMPERATURE_HISTORY.length).toBeGreaterThanOrEqual(10);
  });

  it("keeps system telemetry and right convergence cards from the blueprint", () => {
    expect(SOLVER_BLUEPRINT_TELEMETRY).toMatchObject({
      gpuPct: 94,
      cpuPct: 71,
      memGb: 48,
      deltaT: "2.5e-4",
    });
    expect(SOLVER_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "收敛趋势良好",
      "通过验证 200 步",
      "GPU 满载",
    ]);
  });

  it("wires the Solver main scene to real GLB/VTP layers, not an SVG streamlines fallback", () => {
    const rendererSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/modes/ModeRendererSolver.tsx`,
      "utf8",
    );

    expect(rendererSource).toContain("ViewportV4");
    expect(rendererSource).toContain("geometryGlbUrl(caseId)");
    expect(rendererSource).toContain("surfaceVtpUrl");
    expect(rendererSource).toContain("streamlinesVtpUrl");
    expect(rendererSource).toContain("post/surface.vtp");
    expect(rendererSource).toContain("post/streamlines.vtp");
    expect(rendererSource).not.toContain("IndustrialBoxScene");
    expect(rendererSource).not.toContain("StreamlineField");
    expect(rendererSource).not.toContain("SolverFlowOverlay");
    expect(rendererSource).not.toContain("../scene/streamlines");
  });
});
