import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  DOE_BLUEPRINT_CONFIDENCE,
  DOE_BLUEPRINT_KPIS,
  DOE_BLUEPRINT_LEFT_TREE,
  DOE_BLUEPRINT_RIGHT_CARDS,
  DOE_BLUEPRINT_SCATTER_POINTS,
  DOE_BLUEPRINT_TASK,
  DOE_BLUEPRINT_TOOLBAR,
  DOE_BLUEPRINT_VERDICT,
  DOE_BLUEPRINT_VISIBLE_SAMPLES,
} from "../components/doeBlueprint";

describe("DOE blueprint contract", () => {
  it("locks the original image-8 page task to real CAD thumbnails", () => {
    expect(DOE_BLUEPRINT_TASK).toMatchObject({
      sourceCompanion:
        ".planning/transitions/2026-05-18_blueprint_read.md#image-8-design-exploration",
      pageTask:
        "设计探索页用 3x3 真实 CAD/场缩略图矩阵承载样点对比，并在下方保留 Pareto scatter",
      thumbnailRenderer: "ViewportV4 + /blueprints/v4/apu-cad-assembly.glb",
      forbiddenThumbnailFallback:
        "IndustrialBoxScene / StreamlineField hand-drawn SVG thumbnail",
    });
  });

  it("keeps image-8 toolbar, visible 3x3 card set, and KPI strip auditable", () => {
    expect(DOE_BLUEPRINT_TOOLBAR.map((item) => item.label)).toEqual([
      "搜索方案",
      "全部状态",
      "视图",
      "排序：综合评分",
      "设置",
    ]);
    expect(DOE_BLUEPRINT_VISIBLE_SAMPLES).toHaveLength(9);
    expect(DOE_BLUEPRINT_VISIBLE_SAMPLES.map((sample) => sample.id)).toEqual([
      "V-07",
      "V-08",
      "V-09",
      "V-10",
      "V-11",
      "V-12",
      "V-13",
      "V-14",
      "V-15",
    ]);
    expect(DOE_BLUEPRINT_KPIS).toMatchObject({
      sampleCount: 28,
      completedCount: 28,
      bestPressurePa: 212.6,
      bestTemperatureC: 94.1,
      bestFlowM3S: 18.42,
    });
    expect(DOE_BLUEPRINT_VISIBLE_SAMPLES.every((sample) => sample.deltaPct > 0))
      .toBe(true);
    expect(DOE_BLUEPRINT_SCATTER_POINTS).toHaveLength(9);
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
      "推荐 5 个设计",
      "实验比对就绪",
      "导出报告",
    ]);
  });

  it("wires DOE thumbnails to real GLB viewports, not SVG scene fallbacks", () => {
    const rendererSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/modes/ModeRendererDoe.tsx`,
      "utf8",
    );

    expect(rendererSource).toContain("ViewportV4");
    expect(rendererSource).toContain("GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl");
    expect(rendererSource).toContain("v4-mode-doe-cad-thumb");
    expect(rendererSource).toContain("grid-cols-3");
    expect(rendererSource).not.toContain("IndustrialBoxScene");
    expect(rendererSource).not.toContain("StreamlineField");
    expect(rendererSource).not.toContain("../scene/streamlines");
  });
});
