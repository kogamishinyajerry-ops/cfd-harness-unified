/**
 * V86.4 · V7.C LiveSolverPillV7 + residual-tick callback contract tests
 *
 * Asserts the V7.C contract from .planning/blueprints/v7/INDEX.md:
 *   - Pill renders ONLY when runState = "starting" | "running"
 *   - "starting" → "STARTING …" label · "running" + iteration > 0 →
 *     "LIVE · iter N"
 *   - Pill never renders when runState in idle/done/failed/cancelled
 *   - V7.B onResidualTick fires for SSE "residual" events with correct
 *     iteration/values/ts_ms shape · callback errors swallowed
 *   - V7.B onResidualTick does NOT fire for malformed residual payloads
 *
 * Visual distinction from V6.D BridgeModeShowcase:
 *   - V7.C testid = "topbar-live-pill" (TopBar surface · solver run active)
 *   - V6.D testid = "bridge-mode-pill" (top-left · read-only bridge mode)
 *   - Both can coexist (real run feeding into bridge view) but each has
 *     a distinct testid so e2e + visual baselines can target each
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, renderHook, act } from "@testing-library/react";

import { LiveSolverPillV7 } from "../components/LiveSolverPillV7";
import {
  useSolverRunStateV7,
} from "../hooks/useSolverRunStateV7";
import type { SolverRunState } from "../hooks/useSolverRunStateV7";

describe("LiveSolverPillV7 · V86.4 · V7.C", () => {
  it("renders nothing when runState=idle", () => {
    render(<LiveSolverPillV7 runState="idle" />);
    expect(screen.queryByTestId("topbar-live-pill")).not.toBeInTheDocument();
  });

  it("renders STARTING when runState=starting", () => {
    render(<LiveSolverPillV7 runState="starting" />);
    const pill = screen.getByTestId("topbar-live-pill");
    expect(pill.textContent).toMatch(/STARTING/);
    expect(pill.getAttribute("data-run-state")).toBe("starting");
  });

  it("renders LIVE when runState=running with no iteration", () => {
    render(<LiveSolverPillV7 runState="running" />);
    const pill = screen.getByTestId("topbar-live-pill");
    expect(pill.textContent).toMatch(/LIVE/);
    expect(pill.textContent).not.toMatch(/iter \d/);
  });

  it("renders LIVE · iter N when runState=running + iteration > 0", () => {
    render(<LiveSolverPillV7 runState="running" iteration={42} />);
    const pill = screen.getByTestId("topbar-live-pill");
    expect(pill.textContent).toMatch(/LIVE/);
    expect(pill.textContent).toMatch(/iter 42/);
    expect(pill.getAttribute("data-iteration")).toBe("42");
  });

  it("omits iter suffix when iteration is 0 or null", () => {
    const { rerender } = render(
      <LiveSolverPillV7 runState="running" iteration={0} />,
    );
    expect(screen.getByTestId("topbar-live-pill").textContent).not.toMatch(
      /iter/,
    );
    rerender(<LiveSolverPillV7 runState="running" iteration={null} />);
    expect(screen.getByTestId("topbar-live-pill").textContent).not.toMatch(
      /iter/,
    );
  });

  it("renders nothing in terminal states (done/failed/cancelled)", () => {
    const terminals: SolverRunState[] = ["done", "failed", "cancelled"];
    for (const state of terminals) {
      const { unmount } = render(<LiveSolverPillV7 runState={state} />);
      expect(
        screen.queryByTestId("topbar-live-pill"),
        `state=${state}`,
      ).not.toBeInTheDocument();
      unmount();
    }
  });

  it("V130: zero buttons / forms / inputs · descriptive surface only", () => {
    render(<LiveSolverPillV7 runState="running" iteration={10} />);
    const pill = screen.getByTestId("topbar-live-pill");
    expect(pill.querySelectorAll("button").length).toBe(0);
    expect(pill.querySelectorAll("form").length).toBe(0);
    expect(pill.querySelectorAll("input").length).toBe(0);
  });

  it("distinct from V6.D bridge-mode-pill testid", () => {
    render(<LiveSolverPillV7 runState="running" />);
    expect(screen.getByTestId("topbar-live-pill")).toBeInTheDocument();
    expect(screen.queryByTestId("bridge-mode-pill")).not.toBeInTheDocument();
  });
});

// Helper: SSE block stream constructor
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

describe("useSolverRunStateV7 · V7.C onResidualTick callback", () => {
  it("fires onResidualTick for each SSE residual event with correct shape", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"R"}`,
      `event: residual\ndata: {"iteration":1,"values":{"p":0.1,"U_x":0.05},"ts_ms":1000}`,
      `event: residual\ndata: {"iteration":2,"values":{"p":0.05},"ts_ms":2000}`,
      `event: done\ndata: {"run_id":"R"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const onResidualTick = vi.fn();
    const { result } = renderHook(() =>
      useSolverRunStateV7({ fetchImpl, onResidualTick }),
    );
    await act(async () => {
      await result.current.request("c");
    });
    expect(onResidualTick).toHaveBeenCalledTimes(2);
    expect(onResidualTick).toHaveBeenNthCalledWith(1, {
      iteration: 1,
      values: { p: 0.1, U_x: 0.05 },
      ts_ms: 1000,
    });
    expect(onResidualTick).toHaveBeenNthCalledWith(2, {
      iteration: 2,
      values: { p: 0.05 },
      ts_ms: 2000,
    });
  });

  it("does NOT fire onResidualTick for malformed residual payloads", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"R"}`,
      `event: residual\ndata: {"values":{"p":0.1}}`,           // no iteration
      `event: residual\ndata: {"iteration":1,"ts_ms":1}`,       // no values
      `event: residual\ndata: {"iteration":1,"values":{}}`,    // no ts_ms
      `event: residual\ndata: not valid json`,                  // unparseable
      `event: done\ndata: {"run_id":"R"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const onResidualTick = vi.fn();
    const { result } = renderHook(() =>
      useSolverRunStateV7({ fetchImpl, onResidualTick }),
    );
    await act(async () => {
      await result.current.request("c");
    });
    expect(onResidualTick).not.toHaveBeenCalled();
    // State machine still completes cleanly
    expect(result.current.state).toBe("done");
  });

  it("callback errors do NOT mutate run state (best-effort · V7.C reverse-stop)", async () => {
    const stream = makeSseStream([
      `event: start\ndata: {"run_id":"R"}`,
      `event: residual\ndata: {"iteration":1,"values":{"p":0.1},"ts_ms":1}`,
      `event: done\ndata: {"run_id":"R"}`,
    ]);
    const fetchImpl = vi.fn().mockResolvedValue(okResponse(stream));
    const onResidualTick = vi.fn(() => {
      throw new Error("chart render failed");
    });
    const { result } = renderHook(() =>
      useSolverRunStateV7({ fetchImpl, onResidualTick }),
    );
    await act(async () => {
      await result.current.request("c");
    });
    expect(onResidualTick).toHaveBeenCalled();
    // Hook still reached done, no errorMessage from chart slowdown
    expect(result.current.state).toBe("done");
    expect(result.current.errorMessage).toBeNull();
  });
});
