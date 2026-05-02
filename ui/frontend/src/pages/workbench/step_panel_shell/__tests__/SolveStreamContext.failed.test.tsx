// DEC-V61-107.5 / Codex R18 P1-B: when /solve-stream's terminal `done`
// SSE event carries failed=true, the SolveStreamProvider must route
// state to phase="error" + errorMessage=failed_reason (not "completed"),
// so Step4SolveRun's existing `phase === "error"` branch fires
// onStepError and renders the rose-themed rejection panel.
//
// We exercise the provider end-to-end by stubbing fetch with a
// ReadableStream that emits the SSE byte-stream we want, then assert
// on the public `useSolveStream` hook state after the stream drains.

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";

import {
  SolveStreamProvider,
  useSolveStream,
} from "../SolveStreamContext";

function StreamProbe({
  caseId,
  onState,
}: {
  caseId: string;
  onState: (s: ReturnType<typeof useSolveStream>) => void;
}) {
  const s = useSolveStream();
  useEffect(() => {
    onState(s);
  }, [onState, s]);
  useEffect(() => {
    void s.start(caseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}

function sseBytes(...events: Array<{ event: string; data: unknown }>): Uint8Array {
  const enc = new TextEncoder();
  const blocks = events
    .map(({ event, data }) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
    .join("");
  return enc.encode(blocks);
}

function mockSSEResponse(payload: Uint8Array) {
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(payload);
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

const fetchSpy = vi.fn();

beforeEach(() => {
  fetchSpy.mockReset();
  vi.stubGlobal("fetch", fetchSpy);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SolveStreamContext · failed=true wiring (DEC-V61-107.5 R18 P1-B)", () => {
  it("routes failed=true done event to phase=error with failed_reason as errorMessage", async () => {
    const fatalReason =
      "--> FOAM FATAL IO ERROR: \nkeyword nuTilda is undefined in dictionary \"constant/transportProperties\"\n\nFOAM exiting";
    const body = sseBytes(
      { event: "start", data: { run_id: "run-001", case_id: "case_a" } },
      {
        event: "done",
        data: {
          case_id: "case_a",
          end_time_reached: 0.005,
          last_initial_residual_p: null,
          last_initial_residual_U: [null, null, null],
          last_continuity_error: null,
          n_time_steps_written: 0,
          time_directories: [],
          wall_time_s: 0.4,
          converged: false,
          failed: true,
          failed_reason: fatalReason,
        },
      },
    );
    fetchSpy.mockResolvedValueOnce(mockSSEResponse(body));

    const states: Array<ReturnType<typeof useSolveStream>> = [];
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    await act(async () => {
      render(
        <QueryClientProvider client={client}>
          <SolveStreamProvider>
            <StreamProbe caseId="case_a" onState={(s) => states.push(s)} />
          </SolveStreamProvider>
        </QueryClientProvider>,
      );
      // Allow the fetch microtask + reader pump to drain.
      await new Promise((r) => setTimeout(r, 50));
    });

    const last = states[states.length - 1];
    expect(last.phase).toBe("error");
    expect(last.errorMessage).toContain("nuTilda");
    expect(last.summary?.failed).toBe(true);
  });

  it("routes failed=false done event to phase=completed (regression guard)", async () => {
    const body = sseBytes(
      { event: "start", data: { run_id: "run-002", case_id: "case_b" } },
      {
        event: "done",
        data: {
          case_id: "case_b",
          end_time_reached: 2.0,
          last_initial_residual_p: 1e-6,
          last_initial_residual_U: [1e-6, 1e-6, 1e-6],
          last_continuity_error: 1e-9,
          n_time_steps_written: 400,
          time_directories: ["0.005", "2"],
          wall_time_s: 12.3,
          converged: true,
          failed: false,
          failed_reason: null,
        },
      },
    );
    fetchSpy.mockResolvedValueOnce(mockSSEResponse(body));

    const states: Array<ReturnType<typeof useSolveStream>> = [];
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    await act(async () => {
      render(
        <QueryClientProvider client={client}>
          <SolveStreamProvider>
            <StreamProbe caseId="case_b" onState={(s) => states.push(s)} />
          </SolveStreamProvider>
        </QueryClientProvider>,
      );
      await new Promise((r) => setTimeout(r, 50));
    });

    const last = states[states.length - 1];
    expect(last.phase).toBe("completed");
    expect(last.errorMessage).toBeNull();
    expect(last.summary?.converged).toBe(true);
  });
});
