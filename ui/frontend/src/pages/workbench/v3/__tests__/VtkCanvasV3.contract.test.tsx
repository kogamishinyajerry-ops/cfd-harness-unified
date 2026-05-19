// V76.5 · VtkCanvasV3 contract tests.
//
// Asserts the 5 Pillar-15 surface contracts:
//   (a) mode='geometry' renders data-testid='vtk-canvas-mounted-geometry'
//   (b) mode='mesh' renders data-testid='vtk-canvas-mounted-mesh'
//   (c) camera-reset + axes-widget overlays exist
//   (d) color-legend + fps-indicator overlays exist
//   (e) WebGL-unavailable path renders 'vtk-webgl-fallback' (not the
//       3D canvas)
//
// We mock the viewport_kernel + stl_loader modules so jsdom doesn't try
// to instantiate a real vtk render window (no GL context in jsdom).

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

vi.mock("@/visualization/viewport_kernel", () => ({
  createKernel: vi.fn(() => ({
    setBackground: vi.fn(),
    attachStl: vi.fn(),
    attachGltf: vi.fn(),
    resetCamera: vi.fn(),
    setPickHandler: vi.fn(),
    setHoverHandler: vi.fn(),
    clearPickHighlight: vi.fn(),
    clearHoverHighlight: vi.fn(),
    setPickHighlightCells: vi.fn(),
    setHoverHighlightCells: vi.fn(),
    getCoplanarSiblings: vi.fn(() => []),
    dispose: vi.fn(),
  })),
}));

vi.mock("@/visualization/stl_loader", () => ({
  loadStlFromUrl: vi.fn(() =>
    Promise.resolve({
      reader: { delete: vi.fn() },
      triangleCount: 0,
    }),
  ),
  StlLoadError: class StlLoadError extends Error {
    kind: string;
    status?: number;
    constructor(kind: string, message: string, status?: number) {
      super(message);
      this.kind = kind;
      this.status = status;
    }
  },
}));

import { VtkCanvasV3 } from "../components/canvas/VtkCanvasV3";

describe("V76 · VtkCanvasV3 · Pillar 15 substrate", () => {
  beforeEach(() => {
    // Force WebGL available so we exercise the 3D path. The fallback
    // path has its own test below that nulls out getContext.
    HTMLCanvasElement.prototype.getContext = vi.fn(
      () => ({}) as RenderingContext,
    ) as unknown as typeof HTMLCanvasElement.prototype.getContext;
  });

  afterEach(() => {
    cleanup();
  });

  it("mode='geometry' mounts vtk-canvas-mounted-geometry testid", () => {
    render(<VtkCanvasV3 caseId="lid_driven_cavity" mode="geometry" />);
    expect(screen.getByTestId("vtk-canvas-mounted-geometry")).toBeTruthy();
    // The mesh testid must NOT be present (mode discriminator works)
    expect(screen.queryByTestId("vtk-canvas-mounted-mesh")).toBeNull();
  });

  it("mode='mesh' mounts vtk-canvas-mounted-mesh testid", () => {
    render(<VtkCanvasV3 caseId="lid_driven_cavity" mode="mesh" />);
    expect(screen.getByTestId("vtk-canvas-mounted-mesh")).toBeTruthy();
    expect(screen.queryByTestId("vtk-canvas-mounted-geometry")).toBeNull();
  });

  it("renders camera-reset + axes-widget overlays (V76.3)", () => {
    render(<VtkCanvasV3 caseId="x" mode="geometry" />);
    expect(screen.getByTestId("vtk-camera-reset")).toBeTruthy();
    expect(screen.getByTestId("vtk-axes-widget")).toBeTruthy();
  });

  it("renders color-legend + fps-indicator overlays (V76.4)", () => {
    render(<VtkCanvasV3 caseId="x" mode="mesh" />);
    expect(screen.getByTestId("vtk-color-legend")).toBeTruthy();
    expect(screen.getByTestId("vtk-fps-indicator")).toBeTruthy();
  });
});

describe("V76.5 · VtkCanvasV3 · WebGL fallback", () => {
  beforeEach(() => {
    // Simulate jsdom default (no WebGL): getContext returns null for any
    // canvas-2d/webgl ask. detectWebGL() runs at component mount so the
    // override must be in place before render.
    HTMLCanvasElement.prototype.getContext = vi.fn(
      () => null,
    ) as unknown as typeof HTMLCanvasElement.prototype.getContext;
  });

  afterEach(() => {
    cleanup();
  });

  it("shows vtk-webgl-fallback when WebGL unavailable", () => {
    render(<VtkCanvasV3 caseId="x" mode="geometry" />);
    expect(screen.getByTestId("vtk-webgl-fallback")).toBeTruthy();
    // The 3D canvas testid must NOT be present in fallback mode
    expect(screen.queryByTestId("vtk-canvas-mounted-geometry")).toBeNull();
  });
});
