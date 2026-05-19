import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  IMPORT_BLUEPRINT_CHECKS,
  IMPORT_BLUEPRINT_KPIS,
  IMPORT_BLUEPRINT_RIGHT_CARDS,
  IMPORT_BLUEPRINT_SOURCES,
  IMPORT_BLUEPRINT_TASK,
} from "../components/importBlueprint";
import { GEOMETRY_REAL_CAD_ASSEMBLY } from "../components/geometryBlueprint";

describe("Import blueprint contract", () => {
  it("locks the import page task to source intake rather than an empty upload card", () => {
    expect(IMPORT_BLUEPRINT_TASK).toMatchObject({
      sourceImage: ".planning/blueprints/v3/02-import.png",
      pageTask: "把外部 CAD / 网格源文件转成可审计的 case 摄入清单",
      primaryPreview: GEOMETRY_REAL_CAD_ASSEMBLY,
    });
    expect(IMPORT_BLUEPRINT_SOURCES.map((source) => source.kind)).toEqual([
      "STEP",
      "STL",
      "CSV",
      "JSON",
    ]);
    expect(IMPORT_BLUEPRINT_KPIS).toMatchObject({
      fileCount: 4,
      acceptedCount: 3,
      reviewCount: 1,
      partCount: GEOMETRY_REAL_CAD_ASSEMBLY.partCount,
      sourceScale: "0.001",
    });
  });

  it("keeps validation semantics explicit and advisor-only", () => {
    expect(IMPORT_BLUEPRINT_CHECKS.map((check) => check.label)).toEqual([
      "文件类型",
      "单位与比例",
      "拓扑水密性",
      "分件语义",
      "TrustGate",
    ]);
    expect(IMPORT_BLUEPRINT_CHECKS.find((check) => check.label === "TrustGate"))
      .toMatchObject({
        value: "manual accept",
        status: "REVIEW",
      });
    expect(IMPORT_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "来源完整度",
      "单位与比例",
      "分件命名",
    ]);
  });

  it("renders the Import page from real CAD preview data, not SVG or bitmap fallback", () => {
    const rendererSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/modes/ModeRendererImport.tsx`,
      "utf8",
    );
    const kpiSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/KpiStripV4.tsx`,
      "utf8",
    );
    const rightPanelSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/RightPanelV4.tsx`,
      "utf8",
    );
    const mainCanvasSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/MainCanvasV4.tsx`,
      "utf8",
    );
    const assemblyBytes = readFileSync(
      `${process.cwd()}/public${GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl}`,
    );

    expect(rendererSource).toContain("v4-import-cad-preview");
    expect(rendererSource).toContain("v4-import-cad-preview-loading");
    expect(rendererSource).toContain("cadProbe.available === null");
    expect(rendererSource).toContain("ViewportV4");
    expect(rendererSource).toContain("GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl");
    expect(rendererSource).toContain("v4-import-manual-acceptance-gate");
    expect(rendererSource).not.toContain("<svg");
    expect(rendererSource).not.toContain("type=\"file\"");
    expect(rendererSource).not.toContain("<img");
    expect(kpiSource).toContain("IMPORT_BLUEPRINT_KPIS");
    expect(rightPanelSource).toContain("IMPORT_BLUEPRINT_RIGHT_CARDS");
    expect(mainCanvasSource).toContain("right-[232px] top-[108px]");
    expect(mainCanvasSource).not.toContain(
      'activeStep !== "doe" && activeStep !== "import"',
    );
    expect(assemblyBytes.subarray(0, 4).toString("ascii")).toBe("glTF");
  });
});
