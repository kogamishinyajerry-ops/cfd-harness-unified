// Unit smoke for stl_loader — the network path uses fetch mock, the
// parser path uses a vtk.js mock so we don't need a real STL fixture or
// WebGL in jsdom.
import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  fetchStlBytes,
  parseStlBytes,
  StlLoadError,
} from "../stl_loader";

// Mock vtkSTLReader so the parser path is testable without WebGL/native code.
const setNumberOfCellsMock = (n: number) => ({
  getNumberOfCells: () => n,
});
const polydataMock = (cells: number) => ({
  getNumberOfPoints: () => cells * 3,
  getPolys: () => setNumberOfCellsMock(cells),
});
const readerInstance = {
  parseAsArrayBuffer: vi.fn(),
  getOutputData: vi.fn(() => polydataMock(12)),
  getOutputPort: vi.fn(),
  delete: vi.fn(),
};
vi.mock("@kitware/vtk.js/IO/Geometry/STLReader", () => ({
  default: {
    newInstance: () => readerInstance,
  },
}));

describe("stl_loader.fetchStlBytes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the response body as ArrayBuffer on 200", async () => {
    const buf = new Uint8Array([0x73, 0x6f, 0x6c, 0x69, 0x64]).buffer;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        arrayBuffer: () => Promise.resolve(buf),
      }),
    );
    const result = await fetchStlBytes("/api/cases/test/geometry/stl");
    expect(result).toBe(buf);
  });

  it("throws StlLoadError with kind=fetch on non-2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404 }),
    );
    await expect(
      fetchStlBytes("/api/cases/missing/geometry/stl"),
    ).rejects.toMatchObject({
      name: "StlLoadError",
      kind: "fetch",
      status: 404,
    });
  });

  it("throws StlLoadError with kind=fetch on network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(
      fetchStlBytes("/api/cases/x/geometry/stl"),
    ).rejects.toBeInstanceOf(StlLoadError);
  });

  it("propagates AbortError unchanged so callers can detect abort", async () => {
    const abort = new Error("aborted");
    abort.name = "AbortError";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(
      fetchStlBytes("/api/cases/x/geometry/stl"),
    ).rejects.toMatchObject({ name: "AbortError" });
  });
});

describe("stl_loader.parseStlBytes", () => {
  beforeEach(() => {
    readerInstance.parseAsArrayBuffer.mockClear();
    readerInstance.delete.mockClear();
    readerInstance.getOutputData.mockReset();
    readerInstance.getOutputData.mockReturnValue(polydataMock(12));
  });

  it("parses a non-empty buffer and reports triangle count", () => {
    const buf = new Uint8Array(80).buffer;
    const data = parseStlBytes(buf);
    expect(readerInstance.parseAsArrayBuffer).toHaveBeenCalledWith(buf);
    expect(data.triangleCount).toBe(12);
    expect(data.reader).toBe(readerInstance);
  });

  it("throws StlLoadError(kind=parse) when polydata is missing", () => {
    readerInstance.getOutputData.mockReturnValueOnce(
      null as unknown as ReturnType<typeof polydataMock>,
    );
    expect(() => parseStlBytes(new Uint8Array(0).buffer)).toThrow(
      StlLoadError,
    );
  });

  it("throws StlLoadError(kind=parse) when triangle count is zero", () => {
    readerInstance.getOutputData.mockReturnValueOnce(polydataMock(0));
    expect(() => parseStlBytes(new Uint8Array(0).buffer)).toThrow(
      /zero triangles/,
    );
  });

  // Codex round-2 P2 finding: vtkSTLReader.parseAsArrayBuffer itself
  // throws RangeError for short binary buffers (<84 bytes for the header
  // DataView). Verify the wrap converts that to StlLoadError(kind=parse)
  // and still calls reader.delete() to avoid leaking the failed reader.
  it("converts vtk.js parser exceptions into StlLoadError(kind=parse) and disposes the reader", () => {
    readerInstance.parseAsArrayBuffer.mockImplementationOnce(() => {
      throw new RangeError("Invalid DataView length 84");
    });
    expect(() => parseStlBytes(new Uint8Array(10).buffer)).toThrow(
      StlLoadError,
    );
    expect(readerInstance.delete).toHaveBeenCalledTimes(1);
  });
});
