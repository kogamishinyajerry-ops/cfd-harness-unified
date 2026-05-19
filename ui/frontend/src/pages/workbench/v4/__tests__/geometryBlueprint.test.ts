import { describe, expect, it } from "vitest";

import {
  GEOMETRY_BLUEPRINT_PARTS,
  GEOMETRY_BLUEPRINT_SUMMARY,
  hasAuthoredCadParts,
} from "../components/geometryBlueprint";

describe("Geometry blueprint contract", () => {
  it("keeps image-2 intake KPIs mechanically auditable", () => {
    expect(GEOMETRY_BLUEPRINT_SUMMARY).toMatchObject({
      partCount: 17,
      instanceCount: 2,
      toleranceMm: 2.0,
      estimatedCellsM: 18.76,
    });
  });

  it("provides at least six CAD colors and sums to 17 parts", () => {
    const partTotal = GEOMETRY_BLUEPRINT_PARTS.reduce(
      (sum, part) => sum + part.count,
      0,
    );
    const colorCount = new Set(GEOMETRY_BLUEPRINT_PARTS.map((part) => part.color))
      .size;

    expect(partTotal).toBe(GEOMETRY_BLUEPRINT_SUMMARY.partCount);
    expect(colorCount).toBeGreaterThanOrEqual(6);
  });

  it("treats single-shell imports as missing authored CAD parts", () => {
    expect(hasAuthoredCadParts(0)).toBe(false);
    expect(hasAuthoredCadParts(1)).toBe(false);
    expect(hasAuthoredCadParts(2)).toBe(true);
  });
});
