import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  GEOMETRY_BLUEPRINT_CALLOUTS,
  GEOMETRY_BLUEPRINT_RIGHT_CARDS,
  GEOMETRY_BLUEPRINT_PARTS,
  GEOMETRY_BLUEPRINT_SUMMARY,
  GEOMETRY_BLUEPRINT_TABS,
  GEOMETRY_BLUEPRINT_TOOLBAR,
  GEOMETRY_REAL_CAD_ASSEMBLY,
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

  it("keeps image-2 CAD preparation tabs and toolbar aligned to the original workbench", () => {
    expect(GEOMETRY_BLUEPRINT_TABS.map((tab) => tab.label)).toEqual([
      "几何与 CAD 准备",
      "模型设置",
    ]);
    expect(GEOMETRY_BLUEPRINT_TOOLBAR.map((tool) => tool.label)).toEqual([
      "修复",
      "简化",
      "缝隙检查",
      "印模",
      "包裹",
      "区域提取",
      "布尔",
      "测量",
      "视图",
      "显示",
    ]);
  });

  it("uses real GLB CAD assets as the primary CAD renderer", () => {
    const rendererSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/modes/ModeRendererGeometry.tsx`,
      "utf8",
    );
    const assemblyBytes = readFileSync(
      `${process.cwd()}/public${GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl}`,
    );

    expect(rendererSource).toContain("geometryGlbUrl(caseId)");
    expect(rendererSource).toContain("GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl");
    expect(rendererSource).toContain("const useAssemblyGlb");
    expect(rendererSource).toContain("\"apu-cad-assembly-glb\"");
    expect(rendererSource).toContain("showGrid={false}");
    expect(GEOMETRY_REAL_CAD_ASSEMBLY).toMatchObject({
      kind: "apu-cad-assembly-glb",
      glbUrl: "/blueprints/v4/apu-cad-assembly.glb",
      partCount: 28,
    });
    expect(assemblyBytes.subarray(0, 4).toString("ascii")).toBe("glTF");
    expect(assemblyBytes.byteLength).toBeGreaterThan(1_000_000);
    expect(rendererSource).not.toContain("probe.available === true && authoredCadParts");
    expect(rendererSource).not.toContain("IndustrialBoxScene");
    expect(rendererSource).not.toContain("v4-mode-geometry-cad-callouts");
    expect(rendererSource).not.toContain("v4-mode-geometry-bitmap-scene");
    expect(rendererSource).not.toContain("geometry-apu-exploded.png");
    expect(rendererSource).not.toContain("GEOMETRY_BLUEPRINT_SCENE");
  });

  it("keeps the visible geometry shell free of inline SVG chrome", () => {
    const shellFiles = [
      `${process.cwd()}/src/pages/workbench/v4/components/TopBarV4.tsx`,
      `${process.cwd()}/src/pages/workbench/v4/components/BottomBarV4.tsx`,
    ];

    for (const filePath of shellFiles) {
      expect(readFileSync(filePath, "utf8")).not.toContain("<svg");
    }
  });

  it("keeps image-2 callouts and AI geometry recommendations mechanically auditable", () => {
    expect(GEOMETRY_BLUEPRINT_CALLOUTS.map((callout) => callout.label)).toEqual([
      "入口",
      "风扇区",
      "散热件",
      "壳体",
      "出口",
    ]);
    expect(GEOMETRY_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "自动识别零件",
      "缝隙检查",
      "包裹建议",
      "流体域提取",
    ]);
    expect(GEOMETRY_BLUEPRINT_RIGHT_CARDS.map((card) => card.confidencePct)).toEqual([
      94,
      91,
      92,
      93,
    ]);
  });
});
