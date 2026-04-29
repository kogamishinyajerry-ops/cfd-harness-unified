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
  const [phase, setPhase] = useState<SolveStreamPhase>("idle");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [series, setSeries] = useState<PerTimestepRow[]>([]);
  const [summary, setSummary] = useState<SolveStreamSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

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
    setPhase("idle");
    setCaseId(null);
    setSeries([]);
    setSummary(null);
    setErrorMessage(null);
  }, []);

  const start = useCallback(async (newCaseId: string) => {
    // If a previous stream is still active, cancel it. The backend
    // doesn't kill the running icoFoam — that finishes on its own —
    // but we stop reading from the dead stream.
    abortRef.current?.abort();

    const controller = new AbortController();
    abortRef.current = controller;
    setCaseId(newCaseId);
    setPhase("streaming");
    setSeries([]);
    setSummary(null);
    setErrorMessage(null);

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
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMessage(msg);
      setPhase("error");
      return;
    }

    if (!resp.ok) {
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
      let payload: unknown;
      try {
        payload = JSON.parse(dataJson);
      } catch {
        return;
      }
      if (eventName === "residual") {
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
      flushPending();
      if ((e as { name?: string })?.name === "AbortError") return;
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMessage(msg);
      setPhase((prev) => (prev === "streaming" ? "error" : prev));
    }

    // If we exit the loop without a done event, the stream ended
    // unexpectedly. Mark as error so the user sees something went
    // wrong rather than a stuck "streaming…" state.
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
