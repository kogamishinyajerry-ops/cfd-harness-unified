/**
 * V86.3 · V7.B Run State Machine
 *
 * Per .planning/blueprints/v7/INDEX.md Contract V7.B:
 *   - SolverRunState enum + transitions:
 *       idle → starting → running → done/failed/cancelled → (user dismiss) → idle
 *   - POSTs to existing `/api/import/{case_id}/solve-stream` (V132=9 preserved)
 *   - Parses SSE manually (EventSource doesn't support POST) — mirrors
 *     the legacy step-panel-shell pattern but as a hook, not a Context
 *   - AbortController-driven cancellation · user retains stop control
 *   - Generation counter handles stale runs (consumer re-requests while
 *     prior is in-flight → prior aborted, new run takes over)
 *
 * V130 invariants enforced here:
 *   - `request()` is exposed as a user-click handler · NO useEffect in
 *     this module fires it automatically · contract test asserts the
 *     hook does NOT auto-call request on mount
 *   - `cancel()` is a user-click handler · no programmatic invocation
 *
 * The hook accepts `fetchImpl` + `now` overrides so unit tests can
 * drive transitions deterministically without a real network.
 */

import { useCallback, useReducer, useRef, useEffect } from "react";
import {
  isStartEvent,
  isDoneEvent,
  isErrorEvent,
  isResidualEvent,
} from "./sseSchemaGuardV7";

export type SolverRunState =
  | "idle"
  | "starting"
  | "running"
  | "done"
  | "failed"
  | "cancelled";

export interface SolverRunStateV7 {
  state: SolverRunState;
  runId: string | null;
  startedAt: string | null;
  endedAt: string | null;
  errorMessage: string | null;
  request: (caseId: string) => Promise<void>;
  cancel: () => void;
  dismiss: () => void;
}

interface ReducerState {
  state: SolverRunState;
  runId: string | null;
  startedAt: string | null;
  endedAt: string | null;
  errorMessage: string | null;
}

type Action =
  | { type: "request"; startedAt: string }
  | { type: "started"; runId: string }
  | { type: "done"; endedAt: string }
  | { type: "failed"; endedAt: string; message: string }
  | { type: "cancelled"; endedAt: string }
  | { type: "dismiss" };

const INITIAL: ReducerState = {
  state: "idle",
  runId: null,
  startedAt: null,
  endedAt: null,
  errorMessage: null,
};

function reducer(state: ReducerState, action: Action): ReducerState {
  switch (action.type) {
    case "request":
      return {
        state: "starting",
        runId: null,
        startedAt: action.startedAt,
        endedAt: null,
        errorMessage: null,
      };
    case "started":
      // Only valid from starting (in-flight POST → first SSE event)
      if (state.state !== "starting") return state;
      return { ...state, state: "running", runId: action.runId };
    case "done":
      // done transitions from running OR starting (zero-residual fast runs)
      if (state.state !== "running" && state.state !== "starting") return state;
      return { ...state, state: "done", endedAt: action.endedAt };
    case "failed":
      // failed transitions from any active state
      if (state.state !== "running" && state.state !== "starting") return state;
      return {
        ...state,
        state: "failed",
        endedAt: action.endedAt,
        errorMessage: action.message,
      };
    case "cancelled":
      if (state.state !== "running" && state.state !== "starting") return state;
      return { ...state, state: "cancelled", endedAt: action.endedAt };
    case "dismiss":
      // Only valid from terminal states (done/failed/cancelled)
      if (
        state.state === "running" ||
        state.state === "starting" ||
        state.state === "idle"
      ) {
        return state;
      }
      return INITIAL;
  }
}

/** V7.C live residual tick · payload mirrors the existing
 *  useSseResidualStream `ResidualTick` shape so the chart consumer can
 *  swap sources transparently. */
export interface SolverResidualTick {
  iteration: number;
  values: Partial<Record<"p" | "U_x" | "U_y" | "U_z" | "k" | "omega", number>>;
  ts_ms: number;
}

interface UseSolverRunStateV7Options {
  /** Override fetch for tests. */
  fetchImpl?: typeof fetch;
  /** Override timestamp source for tests. */
  now?: () => string;
  /** Hook called when state transitions running → done. Parent uses this
   *  to wire V7.D post-run hand-off (audit-package build, bridge feed). */
  onRunCompleted?: (runId: string, caseId: string) => void;
  /** V86.4 · V7.C · per-residual-event callback. Parent uses this to
   *  populate the live residual chart while the run is active. Errors
   *  inside the callback are swallowed (best-effort · chart slowdown
   *  must NOT break the run state machine). */
  onResidualTick?: (tick: SolverResidualTick) => void;
}

export function useSolverRunStateV7(
  opts: UseSolverRunStateV7Options = {},
): SolverRunStateV7 {
  const fetchImpl = opts.fetchImpl ?? fetch;
  const now = opts.now ?? (() => new Date().toISOString());

  const [state, dispatch] = useReducer(reducer, INITIAL);
  const abortRef = useRef<AbortController | null>(null);
  const genRef = useRef<number>(0);
  const caseIdRef = useRef<string | null>(null);
  // Capture latest onRunCompleted via ref so request() closure stays stable
  // across re-renders without forcing parent to memoize the callback.
  const onCompletedRef = useRef(opts.onRunCompleted);
  useEffect(() => {
    onCompletedRef.current = opts.onRunCompleted;
  }, [opts.onRunCompleted]);
  // V86.4 · same ref-stash pattern for the residual-tick callback.
  const onResidualTickRef = useRef(opts.onResidualTick);
  useEffect(() => {
    onResidualTickRef.current = opts.onResidualTick;
  }, [opts.onResidualTick]);

  // Unmount: abort any in-flight request to avoid memory leak / orphan
  // network handle. No state writes after unmount because abortRef
  // signal is what the request body checks against.
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  const request = useCallback(
    async (caseId: string) => {
      if (!caseId) return;

      // Bump generation; abort prior controller if mid-flight.
      abortRef.current?.abort();
      genRef.current += 1;
      const myGen = genRef.current;
      caseIdRef.current = caseId;

      const controller = new AbortController();
      abortRef.current = controller;
      dispatch({ type: "request", startedAt: now() });

      const isStale = () => genRef.current !== myGen;

      let resp: Response;
      try {
        resp = await fetchImpl(
          `/api/import/${encodeURIComponent(caseId)}/solve-stream`,
          {
            method: "POST",
            credentials: "same-origin",
            signal: controller.signal,
          },
        );
      } catch (e) {
        const errName = (e as { name?: string })?.name;
        if (errName === "AbortError") {
          if (isStale()) return;
          dispatch({ type: "cancelled", endedAt: now() });
          return;
        }
        if (isStale()) return;
        const msg = e instanceof Error ? e.message : String(e);
        dispatch({ type: "failed", endedAt: now(), message: msg });
        return;
      }

      if (!resp.ok) {
        if (isStale()) return;
        let detail = `solve-stream failed (${resp.status})`;
        try {
          const body = await resp.json();
          const d =
            body?.detail?.detail ?? body?.detail ?? detail;
          detail = typeof d === "string" ? d : JSON.stringify(d);
        } catch {
          // ignore parse errors; default detail
        }
        dispatch({ type: "failed", endedAt: now(), message: detail });
        return;
      }

      if (!resp.body) {
        if (isStale()) return;
        dispatch({
          type: "failed",
          endedAt: now(),
          message: "solve-stream returned no body",
        });
        return;
      }

      // Manual SSE parser. EventSource doesn't support POST so we
      // consume the ReadableStream body directly.
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      const handleEvent = (eventName: string, dataJson: string) => {
        if (isStale()) return;
        let payload: unknown;
        try {
          payload = JSON.parse(dataJson);
        } catch {
          return;
        }
        // V87.4 · schema-drift guard at the parse boundary · invalid
        // event payloads degrade gracefully (skip · no crash · no state
        // corruption · no error propagation to user).
        if (eventName === "start") {
          if (!isStartEvent(payload)) return;
          dispatch({ type: "started", runId: payload.run_id });
        } else if (eventName === "done") {
          if (!isDoneEvent(payload)) return;
          const ts = now();
          dispatch({ type: "done", endedAt: ts });
          // Snapshot ids BEFORE the async callback so transient state
          // changes don't race the consumer.
          const completedRunId = payload.run_id;
          const completedCaseId = caseIdRef.current;
          if (completedRunId && completedCaseId) {
            const cb = onCompletedRef.current;
            if (cb) {
              // Fire-and-forget · errors in the callback do NOT propagate
              // into solver state (V7 reverse-stop #10: audit-package
              // best-effort).
              try {
                cb(completedRunId, completedCaseId);
              } catch {
                // Intentionally swallowed · run state already === done
              }
            }
          }
        } else if (eventName === "error") {
          if (!isErrorEvent(payload)) return;
          dispatch({
            type: "failed",
            endedAt: now(),
            message: payload.message ?? "stream error",
          });
        } else if (eventName === "residual") {
          // V86.4 · V7.C live residual tick · V87.4 strict schema guard.
          if (!isResidualEvent(payload)) return;
          const cb = onResidualTickRef.current;
          if (cb) {
            try {
              cb({
                iteration: payload.iteration,
                values: payload.values,
                ts_ms: payload.ts_ms,
              });
            } catch {
              // V7.C reverse-stop · callback errors do NOT affect run state
            }
          }
        }
        // Unknown event names are silently ignored (forward-compat ·
        // server can introduce new event types without breaking older
        // clients).
      };

      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          // Split on blank-line event boundaries.
          let idx: number;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            let eventName = "message";
            let dataJson = "";
            for (const line of block.split("\n")) {
              if (line.startsWith("event:")) {
                eventName = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                dataJson = line.slice(5).trim();
              }
            }
            if (dataJson) handleEvent(eventName, dataJson);
          }
        }
      } catch (e) {
        const errName = (e as { name?: string })?.name;
        if (errName === "AbortError") {
          if (isStale()) return;
          dispatch({ type: "cancelled", endedAt: now() });
          return;
        }
        if (isStale()) return;
        const msg = e instanceof Error ? e.message : String(e);
        dispatch({ type: "failed", endedAt: now(), message: msg });
      }
    },
    [fetchImpl, now],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    // Reducer transitions to cancelled when the abort propagates through
    // the fetch/read loop. We don't dispatch here to avoid a double
    // transition if the loop has already errored out.
  }, []);

  const dismiss = useCallback(() => {
    dispatch({ type: "dismiss" });
  }, []);

  return {
    state: state.state,
    runId: state.runId,
    startedAt: state.startedAt,
    endedAt: state.endedAt,
    errorMessage: state.errorMessage,
    request,
    cancel,
    dismiss,
  };
}
