import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "../..");
const KERNEL = readFileSync(
  resolve(ROOT, "visualization/viewport_kernel.ts"),
  "utf-8",
);
const VIEWPORT_V4 = readFileSync(
  resolve(ROOT, "pages/workbench/v4/components/ViewportV4.tsx"),
  "utf-8",
);

describe("B2.5 VTP render contract", () => {
  it("maps VTP actors from the mutated polyData and selected magU array", () => {
    expect(KERNEL).toMatch(/renderPolyData = tube\.getOutputData\(\)/);
    expect(KERNEL).toMatch(/mapper\.setInputData\(\s*renderPolyData/s);
    expect(KERNEL).toMatch(/setColorByArrayName\(\s*scalarName\s*\)/);
    expect(KERNEL).toMatch(/polyData\.modified\?\.\(\)/);
    expect(KERNEL).toMatch(/mapper\.modified\?\.\(\)/);
  });

  it("keeps VTP overlays visible over the glb and fits the VTP bounds", () => {
    expect(KERNEL).toMatch(/TubeFilter/);
    expect(KERNEL).toMatch(/a\.setVisibility\(false\)/);
    expect(KERNEL).toMatch(/function _fitVtpCamera/);
    expect(KERNEL).toMatch(/window\.setTimeout\(_fitVtpCamera, 50\)/);
    expect(KERNEL).toMatch(/const displayRange/);
  });

  it("does not let a no-slip wall surface range overwrite streamline U range", () => {
    expect(VIEWPORT_V4).toMatch(/function isNonDegenerateScalarRange/);
    expect(VIEWPORT_V4).toMatch(
      /if \(isNonDegenerateScalarRange\(h\.scalarRange\)\) \{\s*onVtpRangeReady\?\.\(h\.scalarRange\);/s,
    );
  });
});
