// Smoke test for Viewport. The vtk.js module tree never loads in tests:
// Viewport delegates all WebGL work to ./viewport_kernel.ts, which we
// fully mock here. Combined with mocking ./stl_loader, this keeps the
// test environment hermetic and avoids the worker OOM that vtk.js
// Profiles registration triggers under jsdom.

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const {
  loadStlFromUrlMock,
  loadGlbFromUrlMock,
  createKernelMock,
  attachStlMock,
  attachGltfMock,
  resetCameraMock,
  setPickHandlerMock,
  disposeMock,
} = vi.hoisted(() => ({
  loadStlFromUrlMock: vi.fn(),
  loadGlbFromUrlMock: vi.fn(),
  createKernelMock: vi.fn(),
  attachStlMock: vi.fn(),
  attachGltfMock: vi.fn(),
  resetCameraMock: vi.fn(),
  setPickHandlerMock: vi.fn(),
  disposeMock: vi.fn(),
}));

vi.mock("../stl_loader", async () => {
  const actual =
    await vi.importActual<typeof import("../stl_loader")>("../stl_loader");
  return {
    ...actual,
    loadStlFromUrl: (url: string, signal?: AbortSignal) =>
      loadStlFromUrlMock(url, signal),
  };
});

vi.mock("../glb_loader", async () => {
  const actual =
    await vi.importActual<typeof import("../glb_loader")>("../glb_loader");
  return {
    ...actual,
    loadGlbFromUrl: (url: string, signal?: AbortSignal) =>
      loadGlbFromUrlMock(url, signal),
  };
});

vi.mock("../viewport_kernel", () => ({
  createKernel: (...args: unknown[]) => {
    createKernelMock(...args);
    return {
      attachStl: attachStlMock,
      attachGltf: attachGltfMock,
      resetCamera: resetCameraMock,
      setPickHandler: setPickHandlerMock,
      dispose: disposeMock,
      setBackground: vi.fn(),
    };
  },
}));

import { Viewport } from "../Viewport";

describe("Viewport", () => {
  beforeEach(() => {
    loadStlFromUrlMock.mockReset();
    loadGlbFromUrlMock.mockReset();
    createKernelMock.mockReset();
    attachStlMock.mockReset();
    attachGltfMock.mockReset();
    resetCameraMock.mockReset();
    setPickHandlerMock.mockReset();
    disposeMock.mockReset();
  });

  it("creates a kernel, fetches the STL, and attaches it", async () => {
    const fakeReader = { getOutputPort: vi.fn(), delete: vi.fn() };
    loadStlFromUrlMock.mockResolvedValue({
      reader: fakeReader,
      triangleCount: 42,
    });

    render(<Viewport stlUrl="/api/cases/abc/geometry/stl" />);

    await waitFor(() => {
      expect(loadStlFromUrlMock).toHaveBeenCalledTimes(1);
    });
    const [url, signal] = loadStlFromUrlMock.mock.calls[0];
    expect(url).toBe("/api/cases/abc/geometry/stl");
    expect(signal).toBeInstanceOf(AbortSignal);

    expect(createKernelMock).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(attachStlMock).toHaveBeenCalledWith(fakeReader);
    });
    expect(await screen.findByText(/42 tris/)).toBeInTheDocument();
  });

  it("disposes the kernel on unmount (no WebGL leak)", async () => {
    loadStlFromUrlMock.mockResolvedValue({
      reader: { getOutputPort: vi.fn(), delete: vi.fn() },
      triangleCount: 12,
    });

    const { unmount } = render(<Viewport stlUrl="/api/cases/abc/geometry/stl" />);
    await waitFor(() => {
      expect(loadStlFromUrlMock).toHaveBeenCalled();
    });
    unmount();
    expect(disposeMock).toHaveBeenCalledTimes(1);
  });

  it("renders an error banner when loadStlFromUrl rejects", async () => {
    const { StlLoadError } = await import("../stl_loader");
    loadStlFromUrlMock.mockRejectedValue(
      new StlLoadError("fetch", "STL fetch returned HTTP 404", 404),
    );

    render(<Viewport stlUrl="/api/cases/missing/geometry/stl" />);

    expect(
      await screen.findByText(/Viewport error \(fetch\)/),
    ).toBeInTheDocument();
  });

  it("Reset camera button dispatches kernel.resetCamera once load completes", async () => {
    loadStlFromUrlMock.mockResolvedValue({
      reader: { getOutputPort: vi.fn(), delete: vi.fn() },
      triangleCount: 7,
    });

    const user = userEvent.setup();
    render(<Viewport stlUrl="/api/cases/abc/geometry/stl" />);
    const button = await screen.findByRole("button", { name: /reset camera/i });
    await waitFor(() => expect(button).not.toBeDisabled());
    await user.click(button);
    expect(resetCameraMock).toHaveBeenCalledTimes(1);
  });

  it("Reset button is disabled while STL is loading", async () => {
    let resolveLoad: ((v: unknown) => void) | undefined;
    loadStlFromUrlMock.mockReturnValue(
      new Promise((resolve) => {
        resolveLoad = resolve;
      }),
    );
    render(<Viewport stlUrl="/api/cases/abc/geometry/stl" />);
    const button = await screen.findByRole("button", { name: /reset camera/i });
    expect(button).toBeDisabled();
    await act(async () => {
      resolveLoad?.({
        reader: { getOutputPort: vi.fn(), delete: vi.fn() },
        triangleCount: 1,
      });
    });
  });

  it("dispatches to loadGlbFromUrl + attachGltf when format='glb'", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });

    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/geometry/render"
      />,
    );

    await waitFor(() => {
      expect(loadGlbFromUrlMock).toHaveBeenCalledTimes(1);
    });
    expect(loadStlFromUrlMock).not.toHaveBeenCalled();
    const [url, signal] = loadGlbFromUrlMock.mock.calls[0];
    expect(url).toBe("/api/cases/abc/geometry/render");
    expect(signal).toBeInstanceOf(AbortSignal);

    await waitFor(() => {
      expect(attachGltfMock).toHaveBeenCalledWith(fakeImporter);
    });
    expect(attachStlMock).not.toHaveBeenCalled();
  });

  it("renders an error banner when loadGlbFromUrl rejects", async () => {
    const { GlbLoadError } = await import("../glb_loader");
    loadGlbFromUrlMock.mockRejectedValue(
      new GlbLoadError("parse", "glb parser threw: bad header"),
    );

    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/x/geometry/render"
      />,
    );

    expect(
      await screen.findByText(/Viewport error \(parse\)/),
    ).toBeInTheDocument();
  });

  it("emits a config error if format='glb' but glbUrl is missing", async () => {
    render(<Viewport format="glb" />);
    expect(
      await screen.findByText(/Viewport error \(config\)/),
    ).toBeInTheDocument();
    expect(loadGlbFromUrlMock).not.toHaveBeenCalled();
    expect(loadStlFromUrlMock).not.toHaveBeenCalled();
  });

  it("emits a config error if format='stl' (default) but stlUrl is missing", async () => {
    render(<Viewport />);
    expect(
      await screen.findByText(/Viewport error \(config\)/),
    ).toBeInTheDocument();
    expect(loadStlFromUrlMock).not.toHaveBeenCalled();
  });

  it("renders an error banner when kernel.attachGltf throws (Round-2 Finding 5)", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });
    attachGltfMock.mockImplementationOnce(() => {
      throw new Error("importActors blew up");
    });

    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/geometry/render"
      />,
    );

    expect(
      await screen.findByText(/Viewport error \(unknown\)/),
    ).toBeInTheDocument();
  });

  it("disposes the kernel on unmount even on the glb path", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });

    const { unmount } = render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/geometry/render"
      />,
    );
    await waitFor(() => {
      expect(attachGltfMock).toHaveBeenCalled();
    });
    unmount();
    expect(disposeMock).toHaveBeenCalledTimes(1);
  });

  // ───────── pickMode (DEC-V61-098 spec_v2 §A6) ─────────

  it("pickMode=false: kernel.setPickHandler is invoked with null on mount", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });

    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/geometry/render"
        pickMode={false}
      />,
    );
    await waitFor(() => expect(attachGltfMock).toHaveBeenCalled());
    // pickMode is false → handler explicitly cleared. The kernel is
    // shared across glb and stl paths so we always issue the clear.
    expect(setPickHandlerMock).toHaveBeenCalledWith(null);
  });

  it("pickMode=true + caseId: fetches /face-index and registers pick handler", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });
    const fakeFaceIndex = {
      case_id: "abc",
      primitives: [
        { patch_name: "lid", face_ids: ["fid_aaa", "fid_aaa"] },
        {
          patch_name: "fixedWalls",
          face_ids: ["fid_bbb", "fid_bbb", "fid_ccc", "fid_ccc"],
        },
      ],
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(fakeFaceIndex), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const onFacePick = vi.fn();
    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/mesh/render"
        pickMode={true}
        caseId="abc"
        onFacePick={onFacePick}
      />,
    );
    await waitFor(() => expect(attachGltfMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/cases/abc/face-index",
        expect.objectContaining({ method: "GET" }),
      ),
    );
    // The kernel handler should be registered with a non-null function
    // after the fetch resolves.
    await waitFor(() => {
      const handlerCalls = setPickHandlerMock.mock.calls.filter(
        (c) => typeof c[0] === "function",
      );
      expect(handlerCalls.length).toBeGreaterThanOrEqual(1);
    });
    fetchSpy.mockRestore();
  });

  it("pickMode pick callback resolves face_id via the cached face-index", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });
    const fakeFaceIndex = {
      case_id: "abc",
      primitives: [
        { patch_name: "lid", face_ids: ["fid_lid_a", "fid_lid_a"] },
        {
          patch_name: "fixedWalls",
          face_ids: ["fid_w0", "fid_w0", "fid_w1", "fid_w1"],
        },
      ],
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(fakeFaceIndex), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const onFacePick = vi.fn();
    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/mesh/render"
        pickMode={true}
        caseId="abc"
        onFacePick={onFacePick}
      />,
    );
    await waitFor(() => expect(attachGltfMock).toHaveBeenCalled());
    await waitFor(() => {
      const fnCalls = setPickHandlerMock.mock.calls.filter(
        (c) => typeof c[0] === "function",
      );
      expect(fnCalls.length).toBeGreaterThanOrEqual(1);
    });
    // Grab the latest registered handler and dispatch a synthetic
    // kernel pick. fixedWalls is primitive 1; cellId 2 → face_ids[2] = fid_w1.
    const fnCalls = setPickHandlerMock.mock.calls.filter(
      (c) => typeof c[0] === "function",
    );
    const handler = fnCalls[fnCalls.length - 1][0] as (r: {
      patchName: string;
      cellId: number;
      worldPosition: [number, number, number];
    }) => void;
    handler({
      patchName: "fixedWalls",
      cellId: 2,
      worldPosition: [0.5, 0.5, 0.5],
    });

    expect(onFacePick).toHaveBeenCalledWith({
      faceId: "fid_w1",
      patchName: "fixedWalls",
      cellId: 2,
      worldPosition: [0.5, 0.5, 0.5],
    });
    fetchSpy.mockRestore();
  });

  it("pickMode degrades silently when /face-index returns 404", async () => {
    const fakeImporter = { delete: vi.fn() };
    loadGlbFromUrlMock.mockResolvedValue({ importer: fakeImporter });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "no_polymesh" }), { status: 404 }),
    );

    const onFacePick = vi.fn();
    render(
      <Viewport
        format="glb"
        glbUrl="/api/cases/abc/mesh/render"
        pickMode={true}
        caseId="abc"
        onFacePick={onFacePick}
      />,
    );
    await waitFor(() => expect(attachGltfMock).toHaveBeenCalled());
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    // The kernel handler must NOT be installed with a function — only
    // the initial null-clear from the pickMode effect.
    await new Promise((r) => setTimeout(r, 20));
    const fnCalls = setPickHandlerMock.mock.calls.filter(
      (c) => typeof c[0] === "function",
    );
    expect(fnCalls.length).toBe(0);
    expect(onFacePick).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
