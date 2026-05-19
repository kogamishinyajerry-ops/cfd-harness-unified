/**
 * V86.3 · V7.B Run State Machine contract tests
 *
 * Asserts the V7.B contract from .planning/blueprints/v7/INDEX.md:
 *   - Initial state = idle
 *   - request() → starting; first SSE 'start' event → running with run_id
 *   - SSE 'done' event → done with endedAt
 *   - SSE 'error' event OR HTTP error OR throw → failed
 *   - cancel() / AbortError → cancelled
 *   - dismiss() → idle (terminal states only · idle/active state preserved)
 *   - V130: hook does NOT auto-fire request on mount
 *   - onRunCompleted callback fires once on running → done with
 *     (runId, caseId) · errors swallowed (best-effort)
 */
import { describe, expect, it, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import {
  useSolverRunStateV7,
} from "../useSolverRunStateV7";

// Helper: build a ReadableStream that yields SSE blocks separated by \n\n.
function makeSseStream(blocks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    async pull(controller) {
      if (i >= blocks.length) {
        controller.close();
        return;
      }
      controller.enqueue(enc.encode(blocks[i] + "\n\n"));
      i += 1;
    },
  });
}

function okResponse(body: ReadableStream<Uint8Array>): Response {
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("useSolverRunStateV7 contract · V86.3 · V7.B", () => {
  it("initial state is idle · all fields null", () => {
    const { result } = renderHook(() => useSolverRunStateV7());
    expect(result.current.state).toBe("idle");
    expect(result.current.runId).toBeNull();
    expect(result.current.startedAt).toBeNull();
    expect(result.current.endedAt).toBeNull();
    expect(result.current.errorMessage).toBeNull();
  });

  it("V130: hook does NOT auto-fire request on mount", () => {
    const fetchImpl = vi.fn();
    renderHook(() => useSolverRunStateV7({ fetchImpl }));
    // Microtasks/effects have had a chance to fire; if any useEffect
    // called request(), fetchImpl would have been invoked.
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("request() → starting → running (on 'start' event)", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"2026-05-17T12-00-00Z"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const { result } = renderHook(() =>
      useSolverRunStateV7({ fetchImpl, now: () => "FAKE_TS" }),
    );
    await act(async () => {
      await result.current.request("lid_driven_cavity");
    });
    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/import/lid_driven_cavity/solve-stream",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.current.state).toBe("running");
    expect(result.current.runId).toBe("2026-05-17T12-00-00Z");
    expect(result.current.startedAt).toBe("FAKE_TS");
  });

  it("running → done on 'done' event · onRunCompleted called once", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"RID1"}`,
      `event: done\ndata: {"run_id":"RID1","success":true}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const onRunCompleted = vi.fn();
    const { result } = renderHook(() =>
      useSolverRunStateV7({
        fetchImpl,
        now: () => "T",
        onRunCompleted,
      }),
    );
    await act(async () => {
      await result.current.request("lid_driven_cavity");
    });
    expect(result.current.state).toBe("done");
    expect(result.current.endedAt).toBe("T");
    expect(onRunCompleted).toHaveBeenCalledTimes(1);
    expect(onRunCompleted).toHaveBeenCalledWith("RID1", "lid_driven_cavity");
  });

  it("running → failed on SSE 'error' event", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"RID2"}`,
      `event: error\ndata: {"message":"simpleFoam diverged"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    await act(async () => {
      await result.current.request("lid_driven_cavity");
    });
    expect(result.current.state).toBe("failed");
    expect(result.current.errorMessage).toBe("simpleFoam diverged");
  });

  it("starting → failed on HTTP 4xx response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { detail: "mesh_missing" } }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    await act(async () => {
      await result.current.request("lid_driven_cavity");
    });
    expect(result.current.state).toBe("failed");
    expect(result.current.errorMessage).toBe("mesh_missing");
  });

  it("starting → failed on fetch throw (non-abort)", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    await act(async () => {
      await result.current.request("lid_driven_cavity");
    });
    expect(result.current.state).toBe("failed");
    expect(result.current.errorMessage).toBe("network down");
  });

  it("cancel() during in-flight request → cancelled", async () => {
    // Use a fetch that throws AbortError when signal is aborted.
    const fetchImpl = vi.fn().mockImplementation((_url, init) => {
      return new Promise((_resolve, reject) => {
        const sig = (init as RequestInit).signal!;
        sig.addEventListener("abort", () => {
          const e = new Error("aborted");
          e.name = "AbortError";
          reject(e);
        });
      });
    });
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    let pending: Promise<void> | undefined;
    act(() => {
      pending = result.current.request("lid_driven_cavity");
    });
    // Cancel before any SSE arrives.
    act(() => {
      result.current.cancel();
    });
    await act(async () => {
      await pending;
    });
    expect(result.current.state).toBe("cancelled");
  });

  it("onRunCompleted error does NOT mutate solver state (best-effort)", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"RID3"}`,
      `event: done\ndata: {"run_id":"RID3"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const onRunCompleted = vi.fn(() => {
      throw new Error("audit-package build failed");
    });
    const { result } = renderHook(() =>
      useSolverRunStateV7({ fetchImpl, onRunCompleted }),
    );
    await act(async () => {
      await result.current.request("lid_driven_cavity");
    });
    // State stays at done even though callback threw.
    expect(result.current.state).toBe("done");
    expect(result.current.errorMessage).toBeNull();
    expect(onRunCompleted).toHaveBeenCalled();
  });

  it("dismiss() from terminal state → idle", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"R"}`,
      `event: done\ndata: {"run_id":"R"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    await act(async () => {
      await result.current.request("c");
    });
    expect(result.current.state).toBe("done");
    act(() => {
      result.current.dismiss();
    });
    expect(result.current.state).toBe("idle");
    expect(result.current.runId).toBeNull();
    expect(result.current.endedAt).toBeNull();
  });

  it("dismiss() during running is a no-op (active state preserved)", async () => {
    // Stream that opens 'start' then hangs (we don't close it).
    let pullCount = 0;
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          async pull(controller) {
            if (pullCount === 0) {
              controller.enqueue(
                new TextEncoder().encode(
                  `event: start\ndata: {"run_id":"R"}\n\n`,
                ),
              );
              pullCount += 1;
            }
            // Subsequent pulls never resolve — stream stays open
          },
        }),
        { status: 200 },
      ),
    );
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    act(() => {
      result.current.request("c");
    });
    await waitFor(() => {
      expect(result.current.state).toBe("running");
    });
    act(() => {
      result.current.dismiss();
    });
    // Still running — dismiss is no-op during active state.
    expect(result.current.state).toBe("running");
    // Clean up: cancel so the test doesn't leak the open stream.
    act(() => {
      result.current.cancel();
    });
  });

  it("request() while already running aborts prior + restarts", async () => {
    let firstAborted = false;
    const fetchImpl = vi.fn().mockImplementation((_url, init) => {
      const sig = (init as RequestInit).signal!;
      if (!firstAborted) {
        return new Promise((_resolve, reject) => {
          sig.addEventListener("abort", () => {
            firstAborted = true;
            const e = new Error("aborted");
            e.name = "AbortError";
            reject(e);
          });
        });
      }
      // Second call: return a clean done stream.
      const stream = makeSseStream([
        `event: start\ndata: {"run_id":"R2"}`,
        `event: done\ndata: {"run_id":"R2"}`,
      ]);
      return Promise.resolve(okResponse(stream));
    });
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    let first: Promise<void> | undefined;
    act(() => {
      first = result.current.request("c");
    });
    // Kick off second request immediately (no await on first).
    let second: Promise<void> | undefined;
    act(() => {
      second = result.current.request("c");
    });
    await act(async () => {
      await Promise.allSettled([first, second]);
    });
    // After both settle, state should reflect the SECOND run's outcome.
    expect(firstAborted).toBe(true);
    expect(result.current.state).toBe("done");
    expect(result.current.runId).toBe("R2");
  });

  it("empty caseId is a no-op", async () => {
    const fetchImpl = vi.fn();
    const { result } = renderHook(() => useSolverRunStateV7({ fetchImpl }));
    await act(async () => {
      await result.current.request("");
    });
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(result.current.state).toBe("idle");
  });
});
