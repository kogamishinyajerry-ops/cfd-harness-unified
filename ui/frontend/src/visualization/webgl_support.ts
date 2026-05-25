// WebGL availability detection + a typed error for graceful 3D-viewport
// degradation. Kept in its OWN module (zero @kitware/vtk.js imports) so that:
//   - viewport_kernel.ts can guard createKernel() at the single chokepoint,
//   - ViewportV4 (and any future caller) can catch a meaningful typed error
//     instead of the cryptic `TypeError: Cannot create proxy with a non-object
//     as target` that vtk.js throws from RenderWindow.js when there is no
//     usable WebGL context (headless Chrome without --use-gl=swiftshader, a
//     machine with no GPU, or a context-lost situation), and
//   - it is unit-testable under jsdom (vite.config:50 notes vtk.js Profiles/*
//     side-effect imports crash vitest workers, so the kernel itself cannot be
//     imported in a test — this module can).
//
// Mirrors the proven detectWebGL() guard already shipped in VtkCanvasV3.tsx
// (the V3 canvas), centralising it so V4 and the legacy Viewport share one
// source of truth.

/**
 * True iff the browser can hand out a WebGL (or WebGL2) rendering context.
 * Returns false under jsdom and on GPU-less / context-lost environments
 * rather than throwing.
 */
export function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(
      canvas.getContext("webgl2") ||
      canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl")
    );
  } catch {
    return false;
  }
}

/**
 * Thrown by createKernel() when no usable WebGL context is available, so
 * callers can render a graceful fallback instead of letting vtk.js crash the
 * React tree with an opaque Proxy(null) TypeError.
 */
export class WebGLUnavailableError extends Error {
  constructor(message = "WebGL context unavailable", options?: { cause?: unknown }) {
    super(message);
    this.name = "WebGLUnavailableError";
    if (options?.cause !== undefined) {
      (this as { cause?: unknown }).cause = options.cause;
    }
  }
}
