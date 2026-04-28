// STL fetch + parse helper — wraps vtkSTLReader behind a Promise<STLData>
// so the Viewport useEffect can stay readable.
//
// Errors are normalised into a single `StlLoadError` shape so the React
// layer can show a single error banner regardless of whether the failure
// was network (4xx/5xx, fetch reject) or parse (vtk.js returned no
// polydata / zero triangles). Concrete failure messaging stays inline
// in the Viewport — this module surfaces the cause + classification.

import vtkSTLReader from "@kitware/vtk.js/IO/Geometry/STLReader";

export type StlLoadFailureKind = "fetch" | "parse";

export class StlLoadError extends Error {
  readonly kind: StlLoadFailureKind;
  readonly status?: number;
  constructor(kind: StlLoadFailureKind, message: string, status?: number) {
    super(message);
    this.name = "StlLoadError";
    this.kind = kind;
    this.status = status;
  }
}

export interface StlData {
  reader: ReturnType<typeof vtkSTLReader.newInstance>;
  triangleCount: number;
}

export async function fetchStlBytes(
  url: string,
  signal?: AbortSignal,
): Promise<ArrayBuffer> {
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") throw err;
    throw new StlLoadError(
      "fetch",
      `network error fetching STL: ${(err as Error).message}`,
    );
  }
  if (!response.ok) {
    throw new StlLoadError(
      "fetch",
      `STL fetch returned HTTP ${response.status}`,
      response.status,
    );
  }
  return response.arrayBuffer();
}

export function parseStlBytes(buffer: ArrayBuffer): StlData {
  const reader = vtkSTLReader.newInstance();
  reader.parseAsArrayBuffer(buffer);
  const polydata = reader.getOutputData();
  if (!polydata || typeof polydata.getNumberOfPoints !== "function") {
    throw new StlLoadError("parse", "STL parser returned no polydata");
  }
  const polys = polydata.getPolys?.();
  // getNumberOfCells is on the cell array; fall back to point count
  // heuristic when the cell array isn't present (defensive — vtk.js
  // has occasionally evolved this shape between minor versions).
  const triangleCount =
    typeof polys?.getNumberOfCells === "function"
      ? polys.getNumberOfCells()
      : Math.floor((polydata.getNumberOfPoints?.() ?? 0) / 3);
  if (triangleCount <= 0) {
    throw new StlLoadError("parse", "STL contained zero triangles");
  }
  return { reader, triangleCount };
}

export async function loadStlFromUrl(
  url: string,
  signal?: AbortSignal,
): Promise<StlData> {
  const buffer = await fetchStlBytes(url, signal);
  return parseStlBytes(buffer);
}
