// DEC-V61-131 N1.1: api.setupBCWithEnvelope is advisory-only and
// MUST NEVER dispatch mesh:mutated under any branch (the backend
// hard-strip removed all polyMesh-mutating calls from the envelope
// path). The legacy api.setupBC retains the only mutation surface
// for Step 3 and dispatches mesh:mutated as before — that remains
// covered by the api.setupBC tests.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../client";

describe("api.setupBCWithEnvelope · advisory-only (no mesh:mutated dispatch)", () => {
  const fetchMock = vi.fn();
  const dispatchSpy = vi.spyOn(window, "dispatchEvent");

  beforeEach(() => {
    fetchMock.mockReset();
    dispatchSpy.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function envelopeResponse(
    confidence: "confident" | "uncertain" | "blocked",
  ) {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        confidence,
        summary: "test",
        annotations_revision_consumed: 0,
        annotations_revision_after: 0,
        unresolved_questions: [],
        next_step_suggestion: null,
        error_detail: null,
      }),
      text: async () => "",
    };
  }

  function meshMutatedCalls() {
    return dispatchSpy.mock.calls.filter(
      ([e]) => (e as Event).type === "mesh:mutated",
    );
  }

  it("does NOT dispatch mesh:mutated when confidence='confident' (advisory)", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("confident"));
    await api.setupBCWithEnvelope("ldc");
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("does NOT dispatch mesh:mutated for force_uncertain (no setup runs post-N1.1)", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("uncertain"));
    await api.setupBCWithEnvelope("ldc", { forceUncertain: true });
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("does NOT dispatch mesh:mutated when classifier returns 'uncertain' without force flag", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("uncertain"));
    await api.setupBCWithEnvelope("ldc");
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("does NOT dispatch mesh:mutated when confidence='blocked' (force_blocked short-circuits before setup)", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("blocked"));
    await api.setupBCWithEnvelope("ldc", { forceBlocked: true });
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("does NOT dispatch mesh:mutated when both force flags are set", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("blocked"));
    await api.setupBCWithEnvelope("ldc", {
      forceUncertain: true,
      forceBlocked: true,
    });
    expect(meshMutatedCalls()).toHaveLength(0);
  });
});
