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

/** Build the per-timestep table from raw events. The chart renders
 *  this as polylines indexed by timestep. */
function upsertRow(
  rows: PerTimestepRow[],
  t: number,
): { rows: PerTimestepRow[]; row: PerTimestepRow } {
  // Rows are appended in time order; if t is the latest, that's the
  // last row. Otherwise scan from the end (typical SSE order keeps
  // this O(1) amortized).
  if (rows.length > 0 && rows[rows.length - 1].t === t) {
    return { rows, row: rows[rows.length - 1] };
  }
  const row: PerTimestepRow = { t };
  return { rows: [...rows, row], row };
}

export function SolveStreamProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<SolveStreamPhase>("idle");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [series, setSeries] = useState<PerTimestepRow[]>([]);
  const [summary, setSummary] = useState<SolveStreamSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
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
        const ev = payload as ResidualEvent;
        setSeries((prev) => {
          const { rows, row } = upsertRow(prev, ev.t);
          // For p we keep the LAST init residual within a timestep
          // (post-PISO). For U components there's only one solve per
          // timestep, but we still overwrite to match.
          row[ev.field] = ev.init;
          // Replace the final row in-place (rows array is fresh).
          const out = rows.slice(0, rows.length - 1);
          out.push({ ...row });
          return out;
        });
      } else if (eventName === "continuity") {
        const ev = payload as ContinuityEvent;
        setSeries((prev) => {
          const { rows, row } = upsertRow(prev, ev.t);
          row.continuity = ev.sum_local;
          const out = rows.slice(0, rows.length - 1);
          out.push({ ...row });
          return out;
        });
      } else if (eventName === "done") {
        const s = payload as SolveStreamSummary;
        setSummary(s);
        setPhase(s.converged ? "completed" : "completed");
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
      if ((e as { name?: string })?.name === "AbortError") return;
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMessage(msg);
      setPhase((prev) => (prev === "streaming" ? "error" : prev));
    }

    // If we exit the loop without a done event, the stream ended
    // unexpectedly. Mark as error so the user sees something went
    // wrong rather than a stuck "streaming…" state.
    setPhase((prev) => (prev === "streaming" ? "error" : prev));
  }, []);

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
