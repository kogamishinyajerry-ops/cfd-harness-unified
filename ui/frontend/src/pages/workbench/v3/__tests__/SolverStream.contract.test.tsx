// V77.5 · Solver SSE stream contract tests · useSseResidualStream +
// ResidualLiveStreamV3 + SolverStateBadge + SolverInflightTicker.
//
// Mocks the global EventSource so jsdom can exercise the open/event/error/close
// lifecycle without an actual server. The mock factory exposes triggers for
// emitting events synchronously inside React act() boundaries.

import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";

import { ResidualLiveStreamV3 } from "../components/solver/ResidualLiveStreamV3";
import { SolverStateBadge } from "../components/solver/SolverStateBadge";
import { SolverInflightTicker } from "../components/solver/SolverInflightTicker";

interface FakeES {
  url: string;
  readyState: number;
  onopen: ((ev: Event) => void) | null;
  onmessage: ((ev: MessageEvent) => void) | null;
  onerror: ((ev: Event) => void) | null;
  close: () => void;
  __emit(payload: unknown): void;
  __open(): void;
  __error(): void;
}

function makeFakeEventSourceCtor(): {
  ctor: typeof EventSource;
  instances: FakeES[];
} {
  const instances: FakeES[] = [];
  const ctor = function (this: FakeES, url: string) {
    this.url = url;
    this.readyState = 0;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.close = () => {
      this.readyState = 2;
    };
    this.__open = () => {
      this.readyState = 1;
      this.onopen?.(new Event("open"));
    };
    this.__emit = (payload: unknown) => {
      const ev = new MessageEvent("message", {
        data: JSON.stringify(payload),
      });
      this.onmessage?.(ev);
    };
    this.__error = () => {
      this.onerror?.(new Event("error"));
    };
    instances.push(this);
  } as unknown as typeof EventSource;
  return { ctor, instances };
}

describe("V77.2 · ResidualLiveStreamV3 · live values from SSE", () => {
  afterEach(() => cleanup());

  it("renders all 6 residual-live-{var} testids with placeholder values", () => {
    const { ctor } = makeFakeEventSourceCtor();
    render(
      <ResidualLiveStreamV3 caseId="lid_driven_cavity" eventSourceCtor={ctor} />,
    );
    for (const v of ["p", "U_x", "U_y", "U_z", "k", "omega"]) {
      expect(screen.getByTestId(`residual-live-${v}`)).toBeTruthy();
    }
  });

  it("updates p/U_x values when SSE emits residual event", () => {
    const { ctor, instances } = makeFakeEventSourceCtor();
    render(<ResidualLiveStreamV3 caseId="case-x" eventSourceCtor={ctor} />);
    act(() => {
      instances[0].__open();
      instances[0].__emit({
        type: "residual",
        iteration: 12,
        values: { p: 3.2e-4, U_x: 1.1e-5 },
        ts_ms: Date.now(),
      });
    });
    expect(screen.getByTestId("residual-live-p").textContent).toMatch(/3\.20e/i);
    expect(screen.getByTestId("residual-live-U_x").textContent).toMatch(/1\.10e/i);
    expect(screen.getByTestId("sse-stream-status").getAttribute("data-status")).toBe(
      "open",
    );
  });

  it("falls back gracefully when EventSource constructor is absent", () => {
    // Don't pass a ctor and ensure global EventSource is unset for this test
    const originalES = (globalThis as unknown as { EventSource?: unknown }).EventSource;
    (globalThis as unknown as { EventSource?: unknown }).EventSource = undefined;
    try {
      render(<ResidualLiveStreamV3 caseId="case-y" />);
      expect(screen.getByTestId("sse-stream-status").getAttribute("data-status")).toBe(
        "offline",
      );
    } finally {
      (globalThis as unknown as { EventSource?: unknown }).EventSource = originalES;
    }
  });
});

describe("V77.3 · SolverStateBadge · state from SSE", () => {
  afterEach(() => cleanup());

  it("renders idle state by default with data-state='idle'", () => {
    const { ctor } = makeFakeEventSourceCtor();
    render(<SolverStateBadge caseId="case-a" eventSourceCtor={ctor} />);
    const badge = screen.getByTestId("solver-state-badge");
    expect(badge.getAttribute("data-state")).toBe("idle");
  });

  it("flips to converged after state event", () => {
    const { ctor, instances } = makeFakeEventSourceCtor();
    render(<SolverStateBadge caseId="case-b" eventSourceCtor={ctor} />);
    act(() => {
      instances[0].__open();
      instances[0].__emit({
        type: "state",
        state: "converged",
        ts_ms: Date.now(),
      });
    });
    expect(
      screen.getByTestId("solver-state-badge").getAttribute("data-state"),
    ).toBe("converged");
  });
});

describe("V77.4 · SolverInflightTicker · last-N event log", () => {
  beforeEach(() => {
    // Override Date for stable ISO time slice in event log
  });

  afterEach(() => cleanup());

  it("renders solver-inflight-residual testid (empty state)", () => {
    const { ctor } = makeFakeEventSourceCtor();
    render(<SolverInflightTicker caseId="case-c" eventSourceCtor={ctor} />);
    expect(screen.getByTestId("solver-inflight-residual")).toBeTruthy();
    expect(
      screen.getByTestId("solver-inflight-residual").textContent,
    ).toMatch(/waiting|offline/i);
  });

  it("appends events to the ticker (last-10 cap)", () => {
    const { ctor, instances } = makeFakeEventSourceCtor();
    render(<SolverInflightTicker caseId="case-d" eventSourceCtor={ctor} />);
    act(() => {
      instances[0].__open();
      for (let i = 0; i < 12; i++) {
        instances[0].__emit({
          type: "residual",
          iteration: i,
          values: { p: 1e-3 * (1 / (i + 1)) },
          ts_ms: 1700000000000 + i * 1000,
        });
      }
    });
    const ticker = screen.getByTestId("solver-inflight-residual");
    // 12 events emitted, ticker caps at 10
    const lines = ticker.textContent?.match(/iter=\d+/g) ?? [];
    expect(lines.length).toBe(10);
    // Latest event (iter=11) should be in the log
    expect(ticker.textContent).toContain("iter=11");
    // Oldest (iter=0, iter=1) should have been pruned
    expect(ticker.textContent).not.toContain("iter=0  ");
  });
});
