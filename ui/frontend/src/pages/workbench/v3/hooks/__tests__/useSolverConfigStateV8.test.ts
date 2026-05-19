/**
 * V88.5 · V8.D useSolverConfigStateV8 contract tests
 *
 * Asserts the V8.D contract from .planning/blueprints/v8/INDEX.md:
 *   - State transitions: clean → dirty → saving → saved · saving → error
 *     · error → dirty (via dismissError or setField) · dirty → clean (via
 *     discard or revert-to-baseline edit)
 *   - `configReady` is true iff (state ∈ {clean, saved}) AND no validation
 *     errors AND at least one field populated
 *   - confirmCommit gates internally: invalid fields → error, NOT saving
 *   - ETag 409 surfaces as recoverable error (V87.4 carry · graceful degrade)
 *   - 422 backend validation surfaces as structured error
 *   - V130 invariant: hook does NOT auto-call confirmCommit on mount
 *     (no useEffect calls the commit path)
 *
 * Tests use postImpl override so they don't touch the real network.
 */
import { describe, expect, it, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useSolverConfigStateV8 } from "../useSolverConfigStateV8";
import { ApiError } from "@/api/client";
import type {
  RawDictPostBody,
  RawDictPostResponse,
} from "@/types/case_dicts";

const validBaseline = {
  application: "icoFoam",
  endTime: "10.0",
  deltaT: "0.005",
  writeInterval: "0.5",
  writeFormat: "ascii",
};

const baseContent = `
application     icoFoam;
endTime         10.0;
deltaT          0.005;
writeInterval   0.5;
writeFormat     ascii;
`;

function harness(opts?: {
  postImpl?: (
    caseId: string,
    relativePath: string,
    body: RawDictPostBody,
  ) => Promise<RawDictPostResponse>;
}) {
  return renderHook(() =>
    useSolverConfigStateV8({
      caseId: "lid_driven_cavity",
      initial: { content: baseContent, etag: "etag-v1" },
      postImpl: opts?.postImpl,
    }),
  );
}

describe("V88.5 · useSolverConfigStateV8 · hydration + initial state", () => {
  it("hydrates baseline from initial content + etag", async () => {
    const { result } = harness();
    await waitFor(() => {
      expect(result.current.fields.application).toBe("icoFoam");
    });
    expect(result.current.state).toBe("clean");
    expect(result.current.etag).toBe("etag-v1");
    expect(result.current.baseline).toEqual(validBaseline);
    expect(result.current.errorMessage).toBeNull();
    expect(result.current.configReady).toBe(true);
  });

  it("configReady=true when clean + valid baseline", async () => {
    const { result } = harness();
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    expect(result.current.configReady).toBe(true);
  });

  it("configReady=false when no fields hydrated yet", () => {
    const { result } = renderHook(() =>
      useSolverConfigStateV8({ caseId: "x", initial: null }),
    );
    expect(result.current.configReady).toBe(false);
  });
});

describe("V88.5 · useSolverConfigStateV8 · setField + dirty transition", () => {
  it("transitions clean → dirty on field change", async () => {
    const { result } = harness();
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    expect(result.current.state).toBe("dirty");
    expect(result.current.configReady).toBe(false);
  });

  it("transitions dirty → clean when field reverts to baseline value", async () => {
    const { result } = harness();
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    expect(result.current.state).toBe("dirty");
    act(() => result.current.setField("endTime", "10.0"));
    expect(result.current.state).toBe("clean");
    expect(result.current.configReady).toBe(true);
  });

  it("discard returns dirty → clean with baseline values", async () => {
    const { result } = harness();
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    expect(result.current.state).toBe("dirty");
    act(() => result.current.discard());
    expect(result.current.state).toBe("clean");
    expect(result.current.fields.endTime).toBe("10.0");
  });
});

describe("V88.5 · useSolverConfigStateV8 · validation gates configReady", () => {
  it("configReady=false when dirty edit has validation error", async () => {
    const { result } = harness();
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "-1"));
    expect(result.current.validationErrors.length).toBeGreaterThan(0);
    expect(result.current.configReady).toBe(false);
  });

  it("validationErrors surface structured field/kind/message", async () => {
    const { result } = harness();
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("application", "noSuchFoam"));
    const err = result.current.validationErrors.find((e) => e.field === "application");
    expect(err?.kind).toBe("invalid_solver");
  });
});

describe("V88.5 · useSolverConfigStateV8 · confirmCommit happy path", () => {
  it("dirty → saving → saved on successful POST", async () => {
    const postImpl: (
      caseId: string,
      relativePath: string,
      body: RawDictPostBody,
    ) => Promise<RawDictPostResponse> = vi.fn(async () => ({
      case_id: "lid_driven_cavity",
      path: "system/controlDict",
      new_etag: "etag-v2",
      source: "user" as const,
      warnings: [],
    }));
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    expect(result.current.state).toBe("dirty");

    await act(async () => {
      await result.current.confirmCommit();
    });

    const mocked = vi.mocked(postImpl);
    expect(mocked).toHaveBeenCalledTimes(1);
    const [calledCaseId, calledPath, calledBody] = mocked.mock.calls[0];
    expect(calledCaseId).toBe("lid_driven_cavity");
    expect(calledPath).toBe("system/controlDict");
    expect(calledBody.content).toContain("endTime         20.0;");
    expect(calledBody.expected_etag).toBe("etag-v1");

    expect(result.current.state).toBe("saved");
    expect(result.current.etag).toBe("etag-v2");
    expect(result.current.configReady).toBe(true);
  });

  it("subsequent setField after saved transitions saved → dirty", async () => {
    const postImpl = vi.fn(async () => ({
      case_id: "lid_driven_cavity",
      path: "system/controlDict",
      new_etag: "etag-v2",
      source: "user" as const,
      warnings: [],
    }));
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    await act(async () => {
      await result.current.confirmCommit();
    });
    expect(result.current.state).toBe("saved");

    act(() => result.current.setField("deltaT", "0.01"));
    expect(result.current.state).toBe("dirty");
  });
});

describe("V88.5 · useSolverConfigStateV8 · confirmCommit guards", () => {
  it("blocks commit when validation errors exist (state → error, NOT saving)", async () => {
    const postImpl = vi.fn(async () => ({
      case_id: "x",
      path: "system/controlDict",
      new_etag: "z",
      source: "user" as const,
      warnings: [],
    }));
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "-1"));

    await act(async () => {
      await result.current.confirmCommit();
    });

    expect(postImpl).not.toHaveBeenCalled();
    expect(result.current.state).toBe("error");
    expect(result.current.errorMessage).toContain("validation failed");
  });

  it("blocks commit when caseId is null", async () => {
    const postImpl = vi.fn();
    const { result } = renderHook(() =>
      useSolverConfigStateV8({
        caseId: null,
        initial: { content: baseContent, etag: "etag-v1" },
        postImpl,
      }),
    );
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    await act(async () => {
      await result.current.confirmCommit();
    });
    expect(postImpl).not.toHaveBeenCalled();
    expect(result.current.state).toBe("error");
  });
});

describe("V88.5 · useSolverConfigStateV8 · error surfaces gracefully", () => {
  it("ETag 409 mismatch surfaces as recoverable error (V87.4 carry)", async () => {
    const postImpl = vi.fn(async () => {
      throw new ApiError(409, "etag mismatch", {
        failing_check: "etag_mismatch",
      });
    });
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    await act(async () => {
      await result.current.confirmCommit();
    });
    expect(result.current.state).toBe("error");
    expect(result.current.errorMessage).toContain("409");
    expect(result.current.errorMessage).toContain("refresh");
  });

  it("422 backend validation surfaces as structured error", async () => {
    const postImpl = vi.fn(async () => {
      throw new ApiError(422, "validation failed", {
        failing_check: "validation_failed",
        issues: [],
      });
    });
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    await act(async () => {
      await result.current.confirmCommit();
    });
    expect(result.current.state).toBe("error");
    expect(result.current.errorMessage).toContain("backend validation");
  });

  it("dismissError transitions error → dirty so user can retry", async () => {
    const postImpl = vi.fn(async () => {
      throw new ApiError(500, "server explosion");
    });
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    act(() => result.current.setField("endTime", "20.0"));
    await act(async () => {
      await result.current.confirmCommit();
    });
    expect(result.current.state).toBe("error");
    act(() => result.current.dismissError());
    expect(result.current.state).toBe("dirty");
    expect(result.current.errorMessage).toBeNull();
  });
});

describe("V88.5 · useSolverConfigStateV8 · V130 invariant", () => {
  it("does NOT auto-fire confirmCommit on mount (no useEffect commits)", async () => {
    const postImpl = vi.fn();
    const { result } = harness({ postImpl });
    // wait a tick for mount-time useEffect (hydrate) to run
    await waitFor(() => expect(result.current.fields.application).toBe("icoFoam"));
    // Still zero POST calls — only hydrate (which is a GET-like data
    // flow handled by parent · no fetch in the hook on mount).
    expect(postImpl).not.toHaveBeenCalled();
  });
});

describe("V88.5 · useSolverConfigStateV8 · V8→V7 handoff via configReady", () => {
  it("emits configReady=false during dirty, true after saved", async () => {
    const postImpl = vi.fn(async () => ({
      case_id: "x",
      path: "system/controlDict",
      new_etag: "etag-v2",
      source: "user" as const,
      warnings: [],
    }));
    const { result } = harness({ postImpl });
    await waitFor(() => expect(result.current.configReady).toBe(true));

    act(() => result.current.setField("endTime", "20.0"));
    expect(result.current.configReady).toBe(false);

    await act(async () => {
      await result.current.confirmCommit();
    });
    expect(result.current.configReady).toBe(true);
  });
});
