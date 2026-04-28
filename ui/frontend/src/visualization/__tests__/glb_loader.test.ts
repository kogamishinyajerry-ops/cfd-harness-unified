// Unit smoke for glb_loader. Mirrors stl_loader.test.ts shape — fetch
// path uses fetch-mock, parser path uses a vtk.js mock so jsdom doesn't
// need WebGL or the GLTFImporter real implementation.

import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  fetchGlbBytes,
  parseGlbBytes,
  GlbLoadError,
} from "../glb_loader";

const importerInstance = {
  parseAsBinary: vi.fn(),
  setRenderer: vi.fn(),
  importActors: vi.fn(),
  delete: vi.fn(),
};
vi.mock("@kitware/vtk.js/IO/Geometry/GLTFImporter", () => ({
  default: {
    newInstance: () => importerInstance,
  },
}));

describe("glb_loader.fetchGlbBytes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the response body as ArrayBuffer on 200", async () => {
    const buf = new Uint8Array([0x67, 0x6c, 0x54, 0x46]).buffer;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        arrayBuffer: () => Promise.resolve(buf),
      }),
    );
    const result = await fetchGlbBytes("/api/cases/test/geometry/render");
    expect(result).toBe(buf);
  });

  it("throws GlbLoadError with kind=fetch on non-2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404 }),
    );
    await expect(
      fetchGlbBytes("/api/cases/missing/geometry/render"),
    ).rejects.toMatchObject({
      name: "GlbLoadError",
      kind: "fetch",
      status: 404,
    });
  });

  it("throws GlbLoadError with kind=fetch on network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(
      fetchGlbBytes("/api/cases/x/geometry/render"),
    ).rejects.toBeInstanceOf(GlbLoadError);
  });

  it("propagates AbortError unchanged so callers can detect abort", async () => {
    const abort = new Error("aborted");
    abort.name = "AbortError";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(
      fetchGlbBytes("/api/cases/x/geometry/render"),
    ).rejects.toMatchObject({ name: "AbortError" });
  });
});

describe("glb_loader.parseGlbBytes", () => {
  beforeEach(() => {
    importerInstance.parseAsBinary.mockClear();
    importerInstance.delete.mockClear();
  });

  it("returns the importer on a successful parse", async () => {
    const buf = new Uint8Array(64).buffer;
    const data = await parseGlbBytes(buf);
    expect(importerInstance.parseAsBinary).toHaveBeenCalledWith(buf);
    expect(data.importer).toBe(importerInstance);
  });

  it("converts vtk.js parser exceptions into GlbLoadError(kind=parse) and disposes the importer", async () => {
    importerInstance.parseAsBinary.mockImplementationOnce(() => {
      throw new RangeError("Invalid glb header");
    });
    await expect(parseGlbBytes(new Uint8Array(10).buffer)).rejects.toBeInstanceOf(
      GlbLoadError,
    );
    expect(importerInstance.delete).toHaveBeenCalledTimes(1);
  });

  // M-PANELS Step 10 visual-smoke regression: @kitware/vtk.js@35.11
  // ships stale .d.ts that lists `parseAsArrayBuffer` but the runtime
  // only exposes `parseAsBinary`. The original glb_loader called
  // parseAsArrayBuffer + the test mock provided that method, so unit
  // tests passed and CFDJerry hit a runtime "is not a function" the
  // moment they opened the M-PANELS workbench. This test pins the
  // contract to the real runtime API: parseGlbBytes must invoke the
  // method that actually exists at runtime.
  it("uses parseAsBinary (the real runtime method, not the stale-d.ts parseAsArrayBuffer)", async () => {
    vi.resetModules();
    const fakeImporter = {
      parseAsBinary: vi.fn().mockResolvedValue(undefined),
      // Intentionally NOT providing parseAsArrayBuffer — mirrors the
      // real @kitware/vtk.js@35.11 runtime where calling that method
      // would throw "is not a function".
      setRenderer: vi.fn(),
      importActors: vi.fn(),
      delete: vi.fn(),
    };
    vi.doMock("@kitware/vtk.js/IO/Geometry/GLTFImporter", () => ({
      default: { newInstance: () => fakeImporter },
    }));
    const mod = await import("../glb_loader");
    const buf = new Uint8Array(32).buffer;
    const data = await mod.parseGlbBytes(buf);
    expect(fakeImporter.parseAsBinary).toHaveBeenCalledWith(buf);
    expect(fakeImporter.parseAsBinary).toHaveBeenCalledTimes(1);
    expect(data.importer).toBe(fakeImporter);
    vi.doUnmock("@kitware/vtk.js/IO/Geometry/GLTFImporter");
    vi.resetModules();
  });

  it("normalizes lazy-chunk-load failures to GlbLoadError(kind=parse) (Round-3 Finding 7)", async () => {
    // Simulate a dynamic-import that resolves but whose default export
    // throws when newInstance is called — same observable shape as a
    // chunk-load TypeError reaching our try/catch. Without the Round-3
    // wrap, this raw error would bubble up to Viewport as kind="unknown"
    // instead of "parse".
    vi.resetModules();
    vi.doMock("@kitware/vtk.js/IO/Geometry/GLTFImporter", () => ({
      default: {
        newInstance: () => {
          throw new TypeError("Failed to load chunk: net::ERR_FAILED");
        },
      },
    }));
    const mod = await import("../glb_loader");
    await expect(
      mod.parseGlbBytes(new Uint8Array(8).buffer),
    ).rejects.toMatchObject({
      name: "GlbLoadError",
      kind: "parse",
    });
    vi.doUnmock("@kitware/vtk.js/IO/Geometry/GLTFImporter");
    vi.resetModules();
  });
});
