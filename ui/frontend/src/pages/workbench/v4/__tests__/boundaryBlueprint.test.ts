import { describe, expect, it } from "vitest";

import {
  BOUNDARY_BLUEPRINT_KPIS,
  BOUNDARY_BLUEPRINT_RECOGNITION,
  BOUNDARY_BLUEPRINT_TREE_COUNTS,
  BOUNDARY_BLUEPRINT_TYPES,
} from "../components/boundaryBlueprint";

describe("Boundary blueprint contract", () => {
  it("keeps image-5 BC patch classes attached to the engine", () => {
    expect(BOUNDARY_BLUEPRINT_TYPES.map((type) => type.labelZh)).toEqual([
      "入口",
      "出口",
      "热壁面",
      "转子域",
      "壁面",
    ]);
    expect(BOUNDARY_BLUEPRINT_TYPES).toHaveLength(5);
  });

  it("keeps image-5 KPI counts mechanically auditable", () => {
    expect(BOUNDARY_BLUEPRINT_KPIS).toMatchObject({
      inletCount: 28,
      outletCount: 27,
      wallCount: 6,
      rotorCount: 1,
    });
  });

  it("keeps left-tree recognition and right-panel status consistent", () => {
    const recognized = BOUNDARY_BLUEPRINT_TREE_COUNTS
      .filter((item) => item.id !== "unidentified")
      .reduce((sum, item) => sum + item.count, 0);

    expect(recognized).toBe(BOUNDARY_BLUEPRINT_RECOGNITION.recognized);
    expect(BOUNDARY_BLUEPRINT_RECOGNITION).toMatchObject({
      recognized: 61,
      total: 62,
      unknown: 1,
    });
  });
});
