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

  it("R6 P2: dispatches mesh:mutated for force_uncertain (backend ran setup_ldc_bc before wrapping)", async () => {
    // force_uncertain runs setup_ldc_bc THEN returns 'uncertain' to
    // exercise the dialog UI. polyMesh IS written, so the cache must
    // be busted.
    fetchMock.mockResolvedValueOnce(envelopeResponse("uncertain"));
    await api.setupBCWithEnvelope("ldc", { forceUncertain: true });
    expect(meshMutatedCalls()).toHaveLength(1);
  });

  it("does NOT dispatch mesh:mutated when classifier returns 'uncertain' without force flag", async () => {
    // Without force flags, an 'uncertain' envelope means the
    // classifier short-circuited BEFORE setup_ldc_bc — polyMesh was
    // not written.
    fetchMock.mockResolvedValueOnce(envelopeResponse("uncertain"));
    await api.setupBCWithEnvelope("ldc");
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("does NOT dispatch mesh:mutated when confidence='blocked' (force_blocked short-circuits before setup)", async () => {
    fetchMock.mockResolvedValueOnce(envelopeResponse("blocked"));
    await api.setupBCWithEnvelope("ldc", { forceBlocked: true });
    expect(meshMutatedCalls()).toHaveLength(0);
  });

  it("R7 P3: does NOT dispatch when both force flags are set (force_blocked wins server-side)", async () => {
    // spec_v2 §A3: when both flags are passed, force_blocked wins and
    // the backend returns 'blocked' WITHOUT running setup_ldc_bc. The
    // dispatch must respect the response confidence rather than blindly
    // trusting forceUncertain.
    fetchMock.mockResolvedValueOnce(envelopeResponse("blocked"));
    await api.setupBCWithEnvelope("ldc", {
      forceUncertain: true,
      forceBlocked: true,
    });
    expect(meshMutatedCalls()).toHaveLength(0);
  });
});
