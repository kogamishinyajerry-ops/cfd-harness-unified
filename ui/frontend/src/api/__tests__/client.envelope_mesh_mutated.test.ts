// V127 R5 P2: api.setupBCWithEnvelope must only dispatch mesh:mutated
// for the "confident" envelope outcome. "uncertain" / "blocked"
// envelopes short-circuit before touching polyMesh (force_blocked=1
// path, classifier short-circuit) and must NOT bust the
// MeshQualityCard cache.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../client";

describe("api.setupBCWithEnvelope · mesh:mutated dispatch (R5 P2)", () => {
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

  function envelopeResponse(confidence: "confident" | "uncertain" | "blocked") {
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

  it("dispatches mesh:mutated when confidence='confident'", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("confident"));
    await api.setupBCWithEnvelope("ldc");
    expect(meshMutatedCalls()).toHaveLength(1);
    const evt = meshMutatedCalls()[0][0] as CustomEvent<{ caseId: string }>;
    expect(evt.detail.caseId).toBe("ldc");
  });

  it("does NOT dispatch mesh:mutated when confidence='uncertain'", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("uncertain"));
    await api.setupBCWithEnvelope("ldc", { forceUncertain: true });
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("does NOT dispatch mesh:mutated when confidence='blocked'", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("blocked"));
    await api.setupBCWithEnvelope("ldc", { forceBlocked: true });
    expect(meshMutatedCalls()).toHaveLength(0);
  });
});
