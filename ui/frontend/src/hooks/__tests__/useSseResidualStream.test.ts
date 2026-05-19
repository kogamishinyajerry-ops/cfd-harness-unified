// V77.5 · useSseResidualStream hook unit tests · validates reducer +
// reconnect backoff + lifecycle.
//
// We test the reducer directly (no React) + a minimal render-hook
// wrapper to exercise EventSource lifecycle through the mock.

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import {
  useSseResidualStream,
  type SseEvent,
} from "../useSseResidualStream";

interface FakeES {
  url: string;
  readyState: number;
  onopen: ((ev: Event) => void) | null;
  onmessage: ((ev: MessageEvent) => void) | null;
  onerror: ((ev: Event) => void) | null;
  close: () => void;
  __emit(e: SseEvent): void;
  __open(): void;
  __error(): void;
}

function makeFakeES() {
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
    this.__emit = (e: SseEvent) => {
      this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(e) }));
    };
    this.__error = () => {
      this.onerror?.(new Event("error"));
    };
    instances.push(this);
  } as unknown as typeof EventSource;
  return { ctor, instances };
}

describe("V77.1 · useSseResidualStream · lifecycle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts in 'connecting', flips to 'open' on connect", () => {
    const { ctor, instances } = makeFakeES();
    const { result } = renderHook(() =>
      useSseResidualStream("case-a", { eventSourceCtor: ctor }),
    );
    expect(result.current.status).toBe("connecting");
    act(() => {
      instances[0].__open();
    });
    expect(result.current.status).toBe("open");
  });

  it("accumulates residual values from events", () => {
    const { ctor, instances } = makeFakeES();
    const { result } = renderHook(() =>
      useSseResidualStream("case-b", { eventSourceCtor: ctor }),
    );
    act(() => {
      instances[0].__open();
      instances[0].__emit({
        type: "residual",
        iteration: 5,
        values: { p: 1e-3, U_x: 2e-4 },
        ts_ms: 1700000000000,
      });
      instances[0].__emit({
        type: "residual",
        iteration: 6,
        values: { U_y: 5e-5 },
        ts_ms: 1700000001000,
      });
    });
    expect(result.current.latestIteration).toBe(6);
    expect(result.current.latestResiduals.p).toBe(1e-3);
    expect(result.current.latestResiduals.U_x).toBe(2e-4);
    expect(result.current.latestResiduals.U_y).toBe(5e-5);
  });

  it("tracks solver state via state events", () => {
    const { ctor, instances } = makeFakeES();
    const { result } = renderHook(() =>
      useSseResidualStream("case-c", { eventSourceCtor: ctor }),
    );
    act(() => {
      instances[0].__open();
      instances[0].__emit({
        type: "state",
        state: "diverged",
        reason: "p overflow",
        ts_ms: 1700000000000,
      });
    });
    expect(result.current.solverState).toBe("diverged");
  });

  it("falls back to offline after maxReconnects=2 errors", () => {
    const { ctor, instances } = makeFakeES();
    renderHook(() =>
      useSseResidualStream("case-d", {
        eventSourceCtor: ctor,
        maxReconnects: 2,
      }),
    );
    act(() => {
      instances[0].__error();
    });
    // After error, reconnect timer should be set. Drive forward.
    act(() => {
      vi.advanceTimersByTime(1100); // 1s backoff + buffer
    });
    expect(instances.length).toBe(2);
    act(() => {
      instances[1].__error();
    });
    act(() => {
      vi.advanceTimersByTime(2100); // 2s backoff
    });
    expect(instances.length).toBe(3);
    act(() => {
      instances[2].__error();
    });
    // Now attempts (3) ≥ max (2), should go offline
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    // No new EventSource should have been constructed
    expect(instances.length).toBe(3);
  });

  it("closes EventSource on unmount (no leak)", () => {
    const { ctor, instances } = makeFakeES();
    const { unmount } = renderHook(() =>
      useSseResidualStream("case-e", { eventSourceCtor: ctor }),
    );
    act(() => {
      instances[0].__open();
    });
    expect(instances[0].readyState).toBe(1);
    unmount();
    expect(instances[0].readyState).toBe(2);
  });

  it("returns offline when EventSource is not available globally", () => {
    const originalES = (globalThis as unknown as { EventSource?: unknown }).EventSource;
    (globalThis as unknown as { EventSource?: unknown }).EventSource = undefined;
    try {
      const { result } = renderHook(() => useSseResidualStream("case-f"));
      expect(result.current.status).toBe("offline");
    } finally {
      (globalThis as unknown as { EventSource?: unknown }).EventSource = originalES;
    }
  });
});
