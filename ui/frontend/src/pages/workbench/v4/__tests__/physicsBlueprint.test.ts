import { describe, expect, it } from "vitest";

import {
  PHYSICS_BLUEPRINT_COLORMAP,
  PHYSICS_BLUEPRINT_MODELS,
  PHYSICS_BLUEPRINT_SUMMARY,
  PHYSICS_BLUEPRINT_TABS,
  PHYSICS_BLUEPRINT_VELOCITY_RANGE,
} from "../components/physicsBlueprint";

describe("Physics blueprint contract", () => {
  it("keeps image-3 secondary tab hierarchy intact", () => {
    expect(PHYSICS_BLUEPRINT_TABS.map((tab) => tab.label)).toEqual([
      "推荐物理模型",
      "自定义物理模型",
      "时间格式",
      "重力(g)=9.8",
    ]);
  });

  it("keeps image-3 KPIs mechanically auditable", () => {
    expect(PHYSICS_BLUEPRINT_SUMMARY).toMatchObject({
      modelCount: 5,
      materialCount: 5,
      caseType: "稳态流动",
      estimatedCellsM: 28.6,
      recommendedModel: "SST k-ω",
    });
  });

  it("pins the recommended turbulence model and colormap range", () => {
    expect(PHYSICS_BLUEPRINT_MODELS.map((model) => model.name)).toContain("SST k-ω");
    expect(PHYSICS_BLUEPRINT_VELOCITY_RANGE).toEqual({ min: 0, max: 40 });
    expect(PHYSICS_BLUEPRINT_COLORMAP.length).toBeGreaterThanOrEqual(6);
  });
});
