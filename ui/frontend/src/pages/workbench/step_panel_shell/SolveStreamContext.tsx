// Phase-1A live solve streaming (DEC-V61-097).
//
// The SSE solve endpoint is consumed by TWO components:
//   - Step4SolveRun (task panel) owns the [AI 处理] button + final
//     numerical summary panel.
//   - LiveResidualChart (viewport) renders the live residual plot.
//
// They share state via this Context so a single EventSource backs
// both views; the alternative (each opens its own EventSource)
// would double-run icoFoam.

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import { useQueryClient } from "@tanstack/react-query";

export type SolveResidualKind = "p" | "Ux" | "Uy" | "Uz";

export interface ResidualEvent {
  field: SolveResidualKind;
  init: number;
  final: number;
  iters: number;
  t: number;
}

export interface ContinuityEvent {
  sum_local: number;
  global: number;
  t: number;
}

export interface SolveStreamSummary {
  case_id: string;
  end_time_reached: number;
  last_initial_residual_p: number | null;
  last_initial_residual_U: [number | null, number | null, number | null];
  last_continuity_error: number | null;
  n_time_steps_written: number;
  time_directories: string[];
  wall_time_s: number;
  converged: boolean;
}

export type SolveStreamPhase =
  | "idle"
  | "streaming"
  | "completed"
  | "error";

export interface PerTimestepRow {
  t: number;
  p?: number;       // last p initial residual within this timestep (post-PISO)
  Ux?: number;
  Uy?: number;
  Uz?: number;
  continuity?: number;
}

interface SolveStreamState {
  phase: SolveStreamPhase;
  caseId: string | null;
  series: PerTimestepRow[];
  summary: SolveStreamSummary | null;
  errorMessage: string | null;
  // Lifecycle:
  start: (caseId: string) => Promise<void>;
  reset: () => void;
}

const Ctx = createContext<SolveStreamState | null>(null);

export function SolveStreamProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<SolveStreamPhase>("idle");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [series, setSeries] = useState<PerTimestepRow[]>([]);
  const [summary, setSummary] = useState<SolveStreamSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // Codex round-1 HIGH-2 (frontend half): every call to start() bumps
  // a local generation counter; each closure inside start() captures
  // its own gen and short-circuits state writes if the active gen
  // moved past it. Without this guard, a stale `done` from run A could
  // overwrite the live state of a freshly-started run B (e.g. user
  // navigates away mid-solve, comes back, clicks [AI 处理] again, and
  // the abandoned A's done event lands AFTER B starts).
  const genRef = useRef(0);
  // The server-issued run_id from the `start` SSE event. Surfaced for
  // tests + future debug instrumentation; not exposed to consumers.
  const runIdRef = useRef<string | null>(null);

  // Batch SSE events through a single requestAnimationFrame flush. The
  // raw stream emits ~6 events per timestep × 400 timesteps = ~2400
  // events; calling setSeries on each forced React + the SVG chart to
  // re-render thousands of times. Pending events accumulate in a ref
  // (no React render) and a single rAF callback merges them into one
  // setSeries — at most ~60 renders/sec regardless of event rate.
  type PendingEvent =
    | { kind: "residual"; ev: ResidualEvent }
    | { kind: "continuity"; ev: ContinuityEvent };
  const pendingRef = useRef<PendingEvent[]>([]);
  const flushScheduledRef = useRef(false);

  const flushPending = useCallback(() => {
    flushScheduledRef.current = false;
    const pending = pendingRef.current;
    if (pending.length === 0) return;
    pendingRef.current = [];
    setSeries((prev) => {
      const out = prev.slice();
      const lastIdxByT = new Map<number, number>();
      for (let i = 0; i < out.length; i++) {
        lastIdxByT.set(out[i].t, i);
      }
      for (const item of pending) {
        const t = item.ev.t;
        let idx = lastIdxByT.get(t);
        if (idx === undefined) {
          idx = out.length;
          out.push({ t });
          lastIdxByT.set(t, idx);
        }
        const row = { ...out[idx] };
        if (item.kind === "residual") {
          row[item.ev.field] = item.ev.init;
        } else {
          row.continuity = item.ev.sum_local;
        }
        out[idx] = row;
      }
      return out;
    });
  }, []);

  const scheduleFlush = useCallback(() => {
    if (flushScheduledRef.current) return;
    flushScheduledRef.current = true;
    requestAnimationFrame(flushPending);
  }, [flushPending]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    pendingRef.current = [];
    flushScheduledRef.current = false;
    runIdRef.current = null;
    genRef.current += 1;
    setPhase("idle");
    setCaseId(null);
    setSeries([]);
    setSummary(null);
    setErrorMessage(null);
  }, []);

  const start = useCallback(async (newCaseId: string) => {
    // If a previous stream is still active, cancel it. The backend
    // doesn't kill the running icoFoam — that finishes on its own —
    // but we stop reading from the dead stream. The new run_id system
    // (HIGH-2) ensures any stale events from run A that slip past the
    // abort cannot mutate run B's state.
    abortRef.current?.abort();

    // HIGH-2: bump the generation counter and capture the local copy.
    // Every state mutation below checks `genRef.current !== myGen`
    // before writing. Closure-only — state mutations stay safe even
    // if the consumer remounts the provider.
    genRef.current += 1;
    const myGen = genRef.current;
    runIdRef.current = null;
    pendingRef.current = [];
    flushScheduledRef.current = false;

    const controller = new AbortController();
    abortRef.current = controller;
    setCaseId(newCaseId);
    setPhase("streaming");
    setSeries([]);
    setSummary(null);
    setErrorMessage(null);

    // Helper: short-circuit if the active run moved past myGen. Use
    // this in front of every state mutation inside start().
    const isStaleRun = () => genRef.current !== myGen;

    let resp: Response;
    try {
      // EventSource doesn't support POST, so we use fetch + manual
      // SSE-line parsing instead. This also lets us abort cleanly.
      resp = await fetch(
        `/api/import/${encodeURIComponent(newCaseId)}/solve-stream`,
        {
          method: "POST",
          credentials: "same-origin",
          signal: controller.signal,
        },
      );
    } catch (e) {
      if ((e as { name?: string })?.name === "AbortError") return;
      if (isStaleRun()) return;
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMessage(msg);
      setPhase("error");
      return;
    }

    if (!resp.ok) {
      if (isStaleRun()) return;
      try {
        const body = await resp.json();
        const detail =
          body?.detail?.detail ??
          body?.detail ??
          `solve-stream failed (${resp.status})`;
        setErrorMessage(typeof detail === "string" ? detail : JSON.stringify(detail));
      } catch {
        setErrorMessage(`solve-stream failed (${resp.status})`);
      }
      setPhase("error");
      return;
    }
    if (!resp.body) {
      if (isStaleRun()) return;
      setErrorMessage("solve-stream returned no body");
      setPhase("error");
      return;
    }

    // Manual SSE parser. Each event is a block of "key: value" lines
    // terminated by a blank line. We only care about `event:` and
    // `data:` (single-line JSON).
    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    const handleEvent = (eventName: string, dataJson: string) => {
      // HIGH-2: stale events from a prior run must not mutate state.
      if (isStaleRun()) return;
      let payload: unknown;
      try {
        payload = JSON.parse(dataJson);
      } catch {
        return;
      }
      if (eventName === "start") {
        // Server announces the run_id as the first SSE event.
        const startPayload = payload as { run_id?: string };
        if (startPayload.run_id) {
          runIdRef.current = startPayload.run_id;
        }
      } else if (eventName === "residual") {
        pendingRef.current.push({ kind: "residual", ev: payload as ResidualEvent });
        scheduleFlush();
      } else if (eventName === "continuity") {
        pendingRef.current.push({ kind: "continuity", ev: payload as ContinuityEvent });
        scheduleFlush();
      } else if (eventName === "done") {
        flushPending();
        const s = payload as SolveStreamSummary;
        setSummary(s);
        setPhase("completed");
        // Codex round-3 P2 + round-4 P2 (2026-04-30): a re-solve
        // invalidates the Step 5 report bundle. The grid observer
        // reads from React Query cache with enabled:false, so without
        // this, navigating back to Step 5 after a re-solve would show
        // the previous bundle's plots until the user clicked [AI 处理]
        // again.
        //
        // Round-3 used invalidateQueries which marks data stale but
        // KEEPS it in cache; an enabled:false observer will re-render
        // with the same stale value. Round-4 uses removeQueries which
        // actually drops the entry — the grid sees `data === undefined`
        // and renders the empty hint until the user clicks [AI 处理].
        if (s.case_id) {
          queryClient.removeQueries({
            queryKey: ["report-bundle", s.case_id],
          });
        }
      } else if (eventName === "error") {
        const e = payload as { detail: string };
        // In-stream errors don't kill the stream — icoFoam may still
        // emit the done event after a non-fatal warning. Surface but
        // don't change phase.
        setErrorMessage(e.detail);
      }
    };

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Split into events on the SSE blank-line delimiter.
        let blankIdx = buffer.indexOf("\n\n");
        while (blankIdx !== -1) {
          const block = buffer.slice(0, blankIdx);
          buffer = buffer.slice(blankIdx + 2);
          // Parse the block.
          let eventName = "message";
          let dataJson = "";
          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataJson += line.slice(5).trim();
            }
          }
          if (dataJson) {
            handleEvent(eventName, dataJson);
          }
          blankIdx = buffer.indexOf("\n\n");
        }
      }
    } catch (e) {
      if (!isStaleRun()) flushPending();
      if ((e as { name?: string })?.name === "AbortError") return;
      if (isStaleRun()) return;
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMessage(msg);
      setPhase((prev) => (prev === "streaming" ? "error" : prev));
    }

    // If we exit the loop without a done event, the stream ended
    // unexpectedly. Mark as error so the user sees something went
    // wrong rather than a stuck "streaming…" state.
    if (isStaleRun()) return;
    flushPending();
    setPhase((prev) => (prev === "streaming" ? "error" : prev));
  }, [flushPending, scheduleFlush]);

  const value = useMemo<SolveStreamState>(
    () => ({
      phase,
      caseId,
      series,
      summary,
      errorMessage,
      start,
      reset,
    }),
    [phase, caseId, series, summary, errorMessage, start, reset],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSolveStream(): SolveStreamState {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error("useSolveStream must be used inside SolveStreamProvider");
  }
  return ctx;
}
