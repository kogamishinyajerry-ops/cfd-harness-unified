// Regression test for the M3.10 vtk.js proxy root-fix.
//
// Cannot import viewport_kernel.ts here (vite.config:50 — vtk.js Profiles/*
// side-effect imports crash vitest workers under jsdom), which is exactly why
// detectWebGL + WebGLUnavailableError live in their own vtk-free module. Under
// jsdom there is no WebGL context, so this asserts the guard's two halves:
// the detector reports unavailability, and the typed error is well-formed for
// callers to switch on.
import { describe, expect, it } from "vitest";

import { detectWebGL, WebGLUnavailableError } from "../webgl_support";

describe("webgl_support", () => {
  it("detectWebGL() returns false under jsdom (no WebGL context)", () => {
    // jsdom's canvas.getContext('webgl') yields null — the same condition that
    // makes vtk.js throw the opaque Proxy(null) TypeError. The guard must
    // report this rather than throw.
    expect(detectWebGL()).toBe(false);
  });

  it("WebGLUnavailableError is a typed Error callers can switch on", () => {
    const err = new WebGLUnavailableError();
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(WebGLUnavailableError);
    expect(err.name).toBe("WebGLUnavailableError");
    expect(err.message).toBe("WebGL context unavailable");
  });

  it("preserves a custom message and underlying cause", () => {
    const root = new TypeError("Cannot create proxy with a non-object as target");
    const err = new WebGLUnavailableError("init failed", { cause: root });
    expect(err.message).toBe("init failed");
    expect((err as { cause?: unknown }).cause).toBe(root);
  });
});
