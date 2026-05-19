import { describe, expect, it } from "vitest";

import {
  MESH_BLUEPRINT_HISTOGRAMS,
  MESH_BLUEPRINT_NUMERICS,
} from "../components/meshBlueprint";

describe("Mesh blueprint contract", () => {
  it("keeps the image-4 histogram KPI strip at five horizontal metrics", () => {
    expect(MESH_BLUEPRINT_HISTOGRAMS.map((item) => item.label)).toEqual([
      "流体距离",
      "表面距离",
      "单元质量",
      "歪斜度",
      "纵横比",
    ]);
    expect(MESH_BLUEPRINT_HISTOGRAMS).toHaveLength(5);
  });

  it("keeps the second-row mesh numerics mechanically auditable", () => {
    expect(MESH_BLUEPRINT_NUMERICS).toMatchObject({
      estimatedCellsM: 18.86,
      maxSkewness: 0.128,
      maxNonOrthogonalityDeg: 67.4,
      timeEstimateMin: 28.6,
    });
  });

  it("provides compact histogram bins for every metric", () => {
    for (const metric of MESH_BLUEPRINT_HISTOGRAMS) {
      expect(metric.bins.length).toBeGreaterThanOrEqual(8);
      expect(metric.bins.every((bin) => bin >= 0 && bin <= 1)).toBe(true);
      expect(metric.mean).toBeGreaterThanOrEqual(0);
    }
  });
});
