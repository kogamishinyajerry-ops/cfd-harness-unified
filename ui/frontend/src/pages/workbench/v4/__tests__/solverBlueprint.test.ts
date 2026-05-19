import { describe, expect, it } from "vitest";

import {
  SOLVER_BLUEPRINT_KPIS,
  SOLVER_BLUEPRINT_RESIDUAL_SERIES,
  SOLVER_BLUEPRINT_RIGHT_CARDS,
  SOLVER_BLUEPRINT_STREAMLINE_COUNT,
  SOLVER_BLUEPRINT_TELEMETRY,
  SOLVER_BLUEPRINT_TEMPERATURE_HISTORY,
} from "../components/solverBlueprint";

describe("Solver blueprint contract", () => {
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
});
