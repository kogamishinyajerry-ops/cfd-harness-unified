// Viewport — vtk.js + STL/glb renderer.
//
// Step-5 (M-VIZ · DEC-V61-094 spec_v2 §A.1) shipped the STL path.
// Step-6 (M-RENDER-API · DEC-V61-095 spec_v2 §F.1) adds optional glb
// support: pass `format='glb'` + `glbUrl` to consume the
// /api/cases/<id>/geometry/render or /mesh/render endpoint.
//
// Default behavior (`format` omitted or 'stl') is unchanged from M-VIZ
// — stlUrl is fetched and rendered exactly as before. ImportPage is
// not touched in M-RENDER-API; format='glb' wires up in M-PANELS.
//
// Thin React shell. All vtk.js / WebGL concerns live in ./viewport_kernel.ts
// so this component is testable under jsdom without loading the vtk.js
// module tree.

import { useEffect, useRef, useState } from "react";

import { GlbLoadError, loadGlbFromUrl } from "./glb_loader";
import { loadStlFromUrl, StlLoadError } from "./stl_loader";
import { createKernel, type ViewportKernel } from "./viewport_kernel";

interface ViewportProps {
  /** Source URL when format='stl' (or default). */
  stlUrl?: string;
  /** Source URL when format='glb'. */
  glbUrl?: string;
  /** Render path. Defaults to 'stl' for backward compatibility with M-VIZ. */
  format?: "stl" | "glb";
  /** Fixed pixel width. If omitted, the canvas fills its parent container's
   *  width (responsive layout). */
  width?: number;
  height?: number;
  background?: [number, number, number];
}

type LoaderErrorKind =
  | StlLoadError["kind"]
  | GlbLoadError["kind"]
  | "unknown"
  | "config";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; triangleCount?: number }
  | { status: "error"; message: string; kind: LoaderErrorKind };

export function Viewport({
  stlUrl,
  glbUrl,
  format = "stl",
  width,
  height = 480,
  background,
}: ViewportProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const kernelRef = useRef<ViewportKernel | null>(null);
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Validate the prop / URL combination up-front so the user sees a
    // clear error instead of a silent no-op or a vtk.js crash later.
    const sourceUrl = format === "glb" ? glbUrl : stlUrl;
    if (!sourceUrl) {
      setLoadState({
        status: "error",
        message: `Viewport requires ${format === "glb" ? "glbUrl" : "stlUrl"} when format='${format}'`,
        kind: "config",
      });
      return;
    }

    const kernel = createKernel(container, background ? { background } : {});
    kernelRef.current = kernel;

    const controller = new AbortController();
    let cancelled = false;
    setLoadState({ status: "loading" });

    if (format === "glb") {
      loadGlbFromUrl(sourceUrl, controller.signal)
        .then(({ importer }) => {
          if (cancelled) {
            importer.delete();
            return;
          }
          kernel.attachGltf(importer);
          setLoadState({ status: "ready" });
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name === "AbortError" || cancelled) return;
          if (err instanceof GlbLoadError) {
            setLoadState({ status: "error", message: err.message, kind: err.kind });
          } else {
            setLoadState({
              status: "error",
              message: (err as Error).message ?? "unknown error",
              kind: "unknown",
            });
          }
        });
    } else {
      loadStlFromUrl(sourceUrl, controller.signal)
        .then(({ reader, triangleCount }) => {
          if (cancelled) {
            reader.delete();
            return;
          }
          kernel.attachStl(reader);
          setLoadState({ status: "ready", triangleCount });
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name === "AbortError" || cancelled) return;
          if (err instanceof StlLoadError) {
            setLoadState({ status: "error", message: err.message, kind: err.kind });
          } else {
            setLoadState({
              status: "error",
              message: (err as Error).message ?? "unknown error",
              kind: "unknown",
            });
          }
        });
    }

    return () => {
      cancelled = true;
      controller.abort();
      kernelRef.current?.dispose();
      kernelRef.current = null;
    };
  }, [stlUrl, glbUrl, format, background]);

  function onResetCamera() {
    kernelRef.current?.resetCamera();
  }

  const loadingLabel = format === "glb" ? "Loading glb…" : "Loading STL…";

  return (
    <div className="rounded-md border border-surface-800 bg-surface-950/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-mono uppercase tracking-wider text-surface-500">
          Geometry preview
        </h3>
        <div className="flex items-center gap-3 text-[11px] text-surface-500">
          {loadState.status === "ready" && loadState.triangleCount !== undefined && (
            <span className="font-mono">{loadState.triangleCount} tris</span>
          )}
          <button
            type="button"
            onClick={onResetCamera}
            disabled={loadState.status !== "ready"}
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-0.5 text-[11px] text-surface-300 transition hover:bg-surface-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Reset camera
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        data-testid="viewport-container"
        style={{
          width: width ?? "100%",
          height,
          position: "relative",
        }}
        className="bg-surface-950"
      />
      {loadState.status === "loading" && (
        <p className="mt-2 text-[11px] text-surface-500">{loadingLabel}</p>
      )}
      {loadState.status === "error" && (
        <p className="mt-2 rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200">
          Viewport error ({loadState.kind}): {loadState.message}
        </p>
      )}
      {loadState.status === "ready" && (
        <p className="mt-2 text-[11px] text-surface-500">
          drag to rotate · wheel to zoom · shift+drag to pan · ⌥drag to spin
        </p>
      )}
    </div>
  );
}
