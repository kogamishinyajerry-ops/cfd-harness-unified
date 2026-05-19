/**
 * V77.1 · useSseResidualStream
 *
 * EventSource hook for /api/cases/{caseId}/solver/stream. Closes the
 * 7-arc-aged V71.L SSE bookmark.
 *
 * Contract:
 *  - Connects on mount, closes on unmount (no memory leak — reverse-stop §5)
 *  - Exponential backoff reconnect (1s → 2s → 4s → 8s → max 30s) on error
 *  - Tracks last-N events for ticker consumers
 *  - Falls back to "offline" status if backend SSE unavailable (4Q gate:
 *    "solver-offline runnable" — UI degrades, doesn't crash)
 *
 * Event payload shapes (canonical CAE solver telemetry):
 *  - ResidualTick · iteration + per-variable residual values
 *  - StateChange · running / converged / diverged
 *  - IterationCheckpoint · iteration + wall-clock + estimated-time-remaining
 */

import { useEffect, useReducer, useRef } from "react";

export type SolverState = "running" | "converged" | "diverged" | "idle";

export interface ResidualTick {
  type: "residual";
  iteration: number;
  values: Partial<Record<"p" | "U_x" | "U_y" | "U_z" | "k" | "omega", number>>;
  ts_ms: number;
}

export interface StateChange {
  type: "state";
  state: SolverState;
  reason?: string;
  ts_ms: number;
}

export interface IterationCheckpoint {
  type: "checkpoint";
  iteration: number;
  wall_clock_ms: number;
  eta_ms?: number;
}

export type SseEvent = ResidualTick | StateChange | IterationCheckpoint;

export type StreamStatus =
  | "idle"
  | "connecting"
  | "open"
  | "offline"
  | "closed";

export interface SseState {
  status: StreamStatus;
  latestResiduals: ResidualTick["values"];
  latestIteration: number;
  solverState: SolverState;
  recent: SseEvent[];
  errorMsg: string;
  reconnectAttempts: number;
}

type Action =
  | { type: "CONNECTING" }
  | { type: "OPEN" }
  | { type: "EVENT"; event: SseEvent }
  | { type: "ERROR"; msg: string }
  | { type: "OFFLINE" }
  | { type: "CLOSED" }
  | { type: "BUMP_RECONNECT" };

const RECENT_CAP = 10;

const initialState: SseState = {
  status: "idle",
  latestResiduals: {},
  latestIteration: 0,
  solverState: "idle",
  recent: [],
  errorMsg: "",
  reconnectAttempts: 0,
};

function reducer(state: SseState, action: Action): SseState {
  switch (action.type) {
    case "CONNECTING":
      return { ...state, status: "connecting", errorMsg: "" };
    case "OPEN":
      return { ...state, status: "open", reconnectAttempts: 0, errorMsg: "" };
    case "EVENT": {
      const ev = action.event;
      const recent = [...state.recent, ev].slice(-RECENT_CAP);
      if (ev.type === "residual") {
        return {
          ...state,
          recent,
          latestIteration: ev.iteration,
          latestResiduals: { ...state.latestResiduals, ...ev.values },
        };
      }
      if (ev.type === "state") {
        return { ...state, recent, solverState: ev.state };
      }
      return { ...state, recent, latestIteration: ev.iteration };
    }
    case "ERROR":
      return { ...state, status: "connecting", errorMsg: action.msg };
    case "OFFLINE":
      return { ...state, status: "offline" };
    case "CLOSED":
      return { ...state, status: "closed" };
    case "BUMP_RECONNECT":
      return { ...state, reconnectAttempts: state.reconnectAttempts + 1 };
    default:
      return state;
  }
}

function nextBackoffMs(attempts: number): number {
  // 1s · 2s · 4s · 8s · 16s · 30s cap
  return Math.min(1000 * Math.pow(2, attempts), 30_000);
}

export interface UseSseResidualStreamOptions {
  /** Disable hook entirely (e.g., when no caseId selected). */
  enabled?: boolean;
  /**
   * Max reconnect attempts before settling on "offline". Default 5
   * (~30s of escalating backoff). Pass 0 to disable reconnects entirely.
   */
  maxReconnects?: number;
  /**
   * Override EventSource constructor for tests. The default uses the
   * global `EventSource`; under jsdom we inject a mock.
   */
  eventSourceCtor?: typeof EventSource;
}

export function useSseResidualStream(
  caseId: string | null,
  opts: UseSseResidualStreamOptions = {},
): SseState {
  const [state, dispatch] = useReducer(reducer, initialState);
  const sourceRef = useRef<EventSource | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptsRef = useRef(0);
  const cancelledRef = useRef(false);

  const enabled = opts.enabled !== false && !!caseId;
  const maxReconnects = opts.maxReconnects ?? 5;
  const ES =
    opts.eventSourceCtor ??
    (typeof EventSource !== "undefined" ? EventSource : undefined);

  useEffect(() => {
    if (!enabled || !caseId || !ES) {
      if (!ES) dispatch({ type: "OFFLINE" });
      return;
    }
    cancelledRef.current = false;
    attemptsRef.current = 0;

    const connect = () => {
      if (cancelledRef.current) return;
      dispatch({ type: "CONNECTING" });
      const url = `/api/cases/${encodeURIComponent(caseId)}/solver/stream`;
      let es: EventSource;
      try {
        es = new ES(url);
      } catch (err) {
        dispatch({
          type: "ERROR",
          msg: (err as Error)?.message ?? "EventSource construct failed",
        });
        scheduleReconnect();
        return;
      }
      sourceRef.current = es;
      es.onopen = () => {
        if (cancelledRef.current) return;
        dispatch({ type: "OPEN" });
      };
      es.onmessage = (msg: MessageEvent) => {
        if (cancelledRef.current) return;
        try {
          const parsed = JSON.parse(msg.data) as SseEvent;
          if (
            parsed &&
            (parsed.type === "residual" ||
              parsed.type === "state" ||
              parsed.type === "checkpoint")
          ) {
            dispatch({ type: "EVENT", event: parsed });
          }
        } catch {
          // Drop malformed payloads silently — the stream stays open.
        }
      };
      es.onerror = () => {
        if (cancelledRef.current) return;
        es.close();
        sourceRef.current = null;
        scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (cancelledRef.current) return;
      if (attemptsRef.current >= maxReconnects) {
        dispatch({ type: "OFFLINE" });
        return;
      }
      const wait = nextBackoffMs(attemptsRef.current);
      attemptsRef.current += 1;
      dispatch({ type: "BUMP_RECONNECT" });
      timerRef.current = setTimeout(connect, wait);
    };

    connect();

    return () => {
      cancelledRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = null;
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
      dispatch({ type: "CLOSED" });
    };
  }, [caseId, enabled, maxReconnects, ES]);

  return state;
}
