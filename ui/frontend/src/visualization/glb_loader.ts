// Binary glTF (.glb) fetch + parse helper for the Viewport.
//
// Mirrors the shape of stl_loader.ts (fetchXxxBytes / parseXxxBytes /
// loadXxxFromUrl + RenderLoadError-style error class) so the React
// component can dispatch on format='stl'|'glb' without leaking
// vtk.js specifics into Viewport.tsx.
//
// The vtk.js side uses vtkGLTFImporter which holds the parsed scene
// internally and exposes actors via getActors(). The kernel calls
// importActors() against its renderer to populate the scene; the
// loader's job is just to fetch the bytes and run parseAsArrayBuffer.
//
// Round-2 Finding 6: ``vtkGLTFImporter`` is loaded via dynamic
// ``import("@kitware/...")`` inside ``parseGlbBytes`` so STL-only
// Viewport consumers don't pull the GLTFImporter (and its transitive
// vtk.js dependencies) into the Viewport chunk. This preserves the
// spec_v2 §AC#10 +50 KB gz delta budget regardless of caller mix.
import type vtkGLTFImporterType from "@kitware/vtk.js/IO/Geometry/GLTFImporter";

export type GlbLoadFailureKind = "fetch" | "parse";

export class GlbLoadError extends Error {
  readonly kind: GlbLoadFailureKind;
  readonly status?: number;
  constructor(kind: GlbLoadFailureKind, message: string, status?: number) {
    super(message);
    this.name = "GlbLoadError";
    this.kind = kind;
    this.status = status;
  }
}

export interface GlbData {
  importer: ReturnType<typeof vtkGLTFImporterType.newInstance>;
}

export async function fetchGlbBytes(
  url: string,
  signal?: AbortSignal,
): Promise<ArrayBuffer> {
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") throw err;
    throw new GlbLoadError(
      "fetch",
      `network error fetching glb: ${(err as Error).message}`,
    );
  }
  if (!response.ok) {
    throw new GlbLoadError(
      "fetch",
      `glb fetch returned HTTP ${response.status}`,
      response.status,
    );
  }
  return response.arrayBuffer();
}

export async function parseGlbBytes(buffer: ArrayBuffer): Promise<GlbData> {
  // vtkGLTFImporter validates the glb header internally and throws on
  // malformed input. Wrap so every failure surfaces as
  // GlbLoadError(kind="parse") and the importer is released on the
  // failure branch (otherwise the failed importer leaks until GC,
  // mirroring the stl_loader contract from M-VIZ Codex round-2).
  //
  // Round-2 Finding 6: dynamic-import the GLTFImporter so the module
  // and its transitive vtk.js dependencies are split into their own
  // chunk and only fetched when the user actually opens a glb-format
  // Viewport.
  //
  // Round-3 Finding 7: the dynamic import itself can fail (chunk 404,
  // network drop after the splash, missing CSP allowance). Wrap the
  // import + newInstance + parse in a single try/catch so chunk-load
  // failures surface as GlbLoadError(kind="parse") instead of leaking
  // a raw error and falling through to the Viewport's "unknown" kind.
  let importer: ReturnType<typeof vtkGLTFImporterType.newInstance> | undefined;
  try {
    const { default: vtkGLTFImporter } = await import(
      "@kitware/vtk.js/IO/Geometry/GLTFImporter"
    );
    importer = vtkGLTFImporter.newInstance();
    importer.parseAsArrayBuffer(buffer);
    return { importer };
  } catch (err) {
    if (importer) {
      try {
        importer.delete();
      } catch {
        // delete() is not formally idempotent in vtk.js; suppress so the
        // original parse error reaches the caller.
      }
    }
    if (err instanceof GlbLoadError) throw err;
    const message =
      err instanceof Error ? err.message : "unknown vtk.js glb parse failure";
    throw new GlbLoadError("parse", `glb parser threw: ${message}`);
  }
}

export async function loadGlbFromUrl(
  url: string,
  signal?: AbortSignal,
): Promise<GlbData> {
  const buffer = await fetchGlbBytes(url, signal);
  return parseGlbBytes(buffer);
}
