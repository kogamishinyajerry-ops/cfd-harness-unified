import { describe, expect, it } from "vitest";

import {
  DOE_BLUEPRINT_CONFIDENCE,
  DOE_BLUEPRINT_KPIS,
  DOE_BLUEPRINT_LEFT_TREE,
  DOE_BLUEPRINT_RIGHT_CARDS,
  DOE_BLUEPRINT_TOOLBAR,
  DOE_BLUEPRINT_VERDICT,
  DOE_BLUEPRINT_VISIBLE_SAMPLES,
} from "../components/doeBlueprint";

describe("DOE blueprint contract", () => {
  it("keeps image-8 toolbar, visible 4-column card set, and KPI strip auditable", () => {
    expect(DOE_BLUEPRINT_TOOLBAR.map((item) => item.label)).toEqual([
      "搜索方案",
      "全部状态",
      "视图",
      "排序：综合评分",
      "设置",
    ]);
    expect(DOE_BLUEPRINT_VISIBLE_SAMPLES).toHaveLength(8);
    expect(DOE_BLUEPRINT_VISIBLE_SAMPLES.map((sample) => sample.id)).toEqual([
      "V-07",
      "V-08",
      "V-09",
      "V-10",
      "V-11",
      "V-12",
      "V-13",
      "V-14",
    ]);
    expect(DOE_BLUEPRINT_KPIS).toMatchObject({
      sampleCount: 28,
      completedCount: 28,
      bestPressurePa: 212.6,
      bestTemperatureC: 94.1,
      estimatedComputeTime: "18 h 42 m",
    });
  });

  it("keeps the selected DOE candidate tied to the original V-12 optimum", () => {
    const selected = DOE_BLUEPRINT_VISIBLE_SAMPLES.find(
      (sample) => sample.id === DOE_BLUEPRINT_VERDICT.selectedId,
    );
    expect(selected).toMatchObject({
      id: "V-12",
      variableLabel: "风扇转速 +20%",
      pressurePa: DOE_BLUEPRINT_KPIS.bestPressurePa,
      temperatureC: DOE_BLUEPRINT_KPIS.bestTemperatureC,
      optimal: true,
    });
    expect(DOE_BLUEPRINT_VERDICT.label).toBe("V-12 最优解");
  });

  it("keeps DOE-specific left tree and right AI copilot cards aligned to blueprint image 8", () => {
    expect(DOE_BLUEPRINT_LEFT_TREE.map((section) => section.label)).toEqual([
      "参数",
      "变量 (16)",
      "方案集",
      "目标函数",
      "约束",
      "最优解",
    ]);
    expect(DOE_BLUEPRINT_CONFIDENCE.modelPct).toBe(92);
    expect(DOE_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "推荐 3 个新方案",
      "发现最优点",
      "生成对比报告",
      "导出模板",
    ]);
  });
});
