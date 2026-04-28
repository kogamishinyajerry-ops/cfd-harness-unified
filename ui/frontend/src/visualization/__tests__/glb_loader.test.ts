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
  parseAsArrayBuffer: vi.fn(),
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
    importerInstance.parseAsArrayBuffer.mockClear();
    importerInstance.delete.mockClear();
  });

  it("returns the importer on a successful parse", () => {
    const buf = new Uint8Array(64).buffer;
    const data = parseGlbBytes(buf);
    expect(importerInstance.parseAsArrayBuffer).toHaveBeenCalledWith(buf);
    expect(data.importer).toBe(importerInstance);
  });

  it("converts vtk.js parser exceptions into GlbLoadError(kind=parse) and disposes the importer", () => {
    importerInstance.parseAsArrayBuffer.mockImplementationOnce(() => {
      throw new RangeError("Invalid glb header");
    });
    expect(() => parseGlbBytes(new Uint8Array(10).buffer)).toThrow(
      GlbLoadError,
    );
    expect(importerInstance.delete).toHaveBeenCalledTimes(1);
  });
});
