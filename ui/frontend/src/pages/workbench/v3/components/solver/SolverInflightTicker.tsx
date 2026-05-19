/**
 * V77.4 · SolverInflightTicker · console-style last-N event log.
 *
 * Renders the SSE stream's most recent 10 events as a monospace ticker.
 * Industrial parity: STAR-CCM+'s solver log pane / Fluent's transcript window.
 */

import { useSseResidualStream } from "@/hooks/useSseResidualStream";
import type { SseEvent } from "@/hooks/useSseResidualStream";

interface SolverInflightTickerProps {
  caseId: string;
  eventSourceCtor?: typeof EventSource;
}

function formatEvent(ev: SseEvent): string {
  if (ev.type === "residual") {
    const vs = ev.values;
    const parts: string[] = [`iter=${ev.iteration}`];
    if (vs.p !== undefined) parts.push(`p=${vs.p.toExponential(1)}`);
    if (vs.U_x !== undefined) parts.push(`U_x=${vs.U_x.toExponential(1)}`);
    if (vs.U_y !== undefined) parts.push(`U_y=${vs.U_y.toExponential(1)}`);
    if (vs.U_z !== undefined) parts.push(`U_z=${vs.U_z.toExponential(1)}`);
    return parts.join("  ");
  }
  if (ev.type === "state") {
    return `state→${ev.state}${ev.reason ? ` (${ev.reason})` : ""}`;
  }
  return `checkpoint iter=${ev.iteration} t=${ev.wall_clock_ms}ms`;
}

export function SolverInflightTicker({
  caseId,
  eventSourceCtor,
}: SolverInflightTickerProps) {
  const { recent, status } = useSseResidualStream(caseId, { eventSourceCtor });

  return (
    <div
      data-testid="solver-inflight-residual"
      data-source={status === "open" ? "live" : "fallback"}
      role="log"
      aria-live="polite"
      aria-label="Solver telemetry log"
      tabIndex={0}
      className="rounded-md border border-v3-borderSubtle bg-black/50 p-2 font-mono text-[10px] text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
      style={{ maxHeight: 140, overflowY: "auto" }}
    >
      <div className="mb-1 text-v3-textTertiary text-[9px] uppercase tracking-[0.08em]">
        Solver log · last {recent.length}
      </div>
      {recent.length === 0 ? (
        <div className="text-v3-textTertiary text-[10px]">
          {status === "offline"
            ? "stream offline · solver telemetry unavailable"
            : "waiting for first event…"}
        </div>
      ) : (
        recent.map((ev, i) => {
          const tsMs = ev.type === "checkpoint" ? ev.wall_clock_ms : ev.ts_ms;
          return (
            <div key={`${tsMs}-${i}`} className="leading-tight">
              <span className="text-v3-textTertiary">
                [{new Date(tsMs ?? 0).toISOString().slice(11, 19)}]
              </span>{" "}
              {formatEvent(ev)}
            </div>
          );
        })
      )}
    </div>
  );
}
