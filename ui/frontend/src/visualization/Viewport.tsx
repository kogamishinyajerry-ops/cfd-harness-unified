// Viewport — vtk.js + STL renderer (M-VIZ Step 5 · DEC-V61-094 spec_v2 §A.1).
//
// Thin React shell. All vtk.js / WebGL concerns live in ./viewport_kernel.ts
// so this component is testable under jsdom without loading the vtk.js
// module tree.

import { useEffect, useRef, useState } from "react";

import { loadStlFromUrl, StlLoadError } from "./stl_loader";
import { createKernel, type ViewportKernel } from "./viewport_kernel";

interface ViewportProps {
  stlUrl: string;
  /** Fixed pixel width. If omitted, the canvas fills its parent container's
   *  width (responsive layout). */
  width?: number;
  height?: number;
  background?: [number, number, number];
}

type LoadState =
  | { status: "loading" }
  | { status: "ready"; triangleCount: number }
  | { status: "error"; message: string; kind: StlLoadError["kind"] | "unknown" };

export function Viewport({
  stlUrl,
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

    const kernel = createKernel(container, background ? { background } : {});
    kernelRef.current = kernel;

    const controller = new AbortController();
    let cancelled = false;
    setLoadState({ status: "loading" });

    loadStlFromUrl(stlUrl, controller.signal)
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

    return () => {
      cancelled = true;
      controller.abort();
      kernelRef.current?.dispose();
      kernelRef.current = null;
    };
  }, [stlUrl, background]);

  function onResetCamera() {
    kernelRef.current?.resetCamera();
  }

  return (
    <div className="rounded-md border border-surface-800 bg-surface-950/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-mono uppercase tracking-wider text-surface-500">
          Geometry preview
        </h3>
        <div className="flex items-center gap-3 text-[11px] text-surface-500">
          {loadState.status === "ready" && (
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
        <p className="mt-2 text-[11px] text-surface-500">Loading STL…</p>
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
