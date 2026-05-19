/**
 * V77.3 · SolverStateBadge · running / converged / diverged badge from
 * SSE solverState. Semantic borders + neutral fill (no competing accents).
 *
 * data-state attribute is the source of truth; CSS only styles based on it.
 */

import { useSseResidualStream } from "@/hooks/useSseResidualStream";

interface SolverStateBadgeProps {
  caseId: string;
  eventSourceCtor?: typeof EventSource;
}

const STATE_STYLES = {
  running: "border-blue-500/40 text-blue-200 bg-blue-500/10",
  converged: "border-emerald-500/40 text-emerald-200 bg-emerald-500/10",
  diverged: "border-rose-500/40 text-rose-200 bg-rose-500/10",
  idle: "border-v3-borderSubtle text-v3-textTertiary bg-v3-bgRaised/40",
} as const;

const STATE_LABEL = {
  running: "RUNNING",
  converged: "CONVERGED",
  diverged: "DIVERGED",
  idle: "IDLE",
} as const;

export function SolverStateBadge({ caseId, eventSourceCtor }: SolverStateBadgeProps) {
  const { solverState, status } = useSseResidualStream(caseId, {
    eventSourceCtor,
  });

  const styles = STATE_STYLES[solverState];
  const label = STATE_LABEL[solverState];

  return (
    <span
      data-testid="solver-state-badge"
      data-state={solverState}
      data-source={status === "open" ? "live" : "fallback"}
      className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.08em] ${styles}`}
    >
      {label}
    </span>
  );
}
