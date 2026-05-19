import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  MESH_BLUEPRINT_HISTOGRAMS,
  MESH_BLUEPRINT_NUMERICS,
  MESH_BLUEPRINT_VISUAL_CONTRACT,
} from "../components/meshBlueprint";

describe("Mesh blueprint contract", () => {
  it("locks the Mesh viewport to surface-visible mesh inspection", () => {
    expect(MESH_BLUEPRINT_VISUAL_CONTRACT).toMatchObject({
      sourceImage: ".planning/blueprints/v3/03-mesh.png",
      viewportTask: "show solid case surface with mesh lines riding on the visible faces",
      surfaceLayer: "geometry.glb",
      lineLayer: "mesh.glb",
      occlusionModel: "opaque surface depth-occludes internal volume edges",
    });
  });

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

  it("wires mesh mode as a solid surface plus a mesh-line overlay", () => {
    const modeRendererSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/modes/ModeRendererMesh.tsx`,
      "utf8",
    );
    const viewportSource = readFileSync(
      `${process.cwd()}/src/pages/workbench/v4/components/ViewportV4.tsx`,
      "utf8",
    );
    const kernelSource = readFileSync(
      `${process.cwd()}/src/visualization/viewport_kernel.ts`,
      "utf8",
    );

    expect(modeRendererSource).toContain("geometryGlbUrl");
    expect(modeRendererSource).toContain("meshOverlayGlbUrl");
    expect(modeRendererSource).toContain("mesh.glb 表面网格线");
    expect(viewportSource).toContain("meshOverlayGlbUrl");
    expect(viewportSource).toContain("mesh-surface");
    expect(viewportSource).toContain("mesh-lines");
    expect(kernelSource).toContain("GltfAttachOptions");
    expect(kernelSource).toContain('primitiveName === "primitive-0"');
    expect(kernelSource).toContain('primitiveName === "primitive-1"');
    expect(kernelSource).toContain("setRepresentation(2)");
    expect(kernelSource).toContain("setRepresentation(1)");
    expect(kernelSource).toContain("setLineWidth");
    expect(kernelSource).toContain("setResolveCoincidentTopologyToPolygonOffset");
  });
});
