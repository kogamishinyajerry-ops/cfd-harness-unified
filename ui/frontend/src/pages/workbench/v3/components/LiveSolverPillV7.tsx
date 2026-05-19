/**
 * V86.4 · V7.C Live Solver Pill · TopBar surface
 *
 * Per .planning/blueprints/v7/INDEX.md Contract V7.C:
 *   - Renders ONLY when solver run is active (state = "starting" | "running")
 *   - Sand-coral accent matching existing v3 palette (#b78b65 ≈ v3-accent)
 *   - When state = "starting": label "STARTING …" (POST in flight)
 *   - When state = "running": label "LIVE · iter N" with optional iter count
 *
 * V130/V132:
 *   - Pure render from props · no fetch · no side effect
 *   - No buttons / form / input · descriptive surface only
 *
 * Visual distinction:
 *   - Distinct from V6.D BridgeModeShowcase pill ("LIVE DATA · advisor in
 *     passive mode") which is top-LEFT and indicates read-only bridge
 *   - V7.C LIVE pill goes inside TopBarV3 (top-center-left) and indicates
 *     an active solver run · USER triggered · cancellable
 */

import type { SolverRunState } from "../hooks/useSolverRunStateV7";

interface LiveSolverPillV7Props {
  runState: SolverRunState;
  /** Latest iteration count surfaced by V7.B onResidualTick. Optional ·
   *  when undefined or 0, the pill omits the "iter N" suffix. */
  iteration?: number | null;
}

export function LiveSolverPillV7({
  runState,
  iteration = null,
}: LiveSolverPillV7Props) {
  if (runState !== "starting" && runState !== "running") return null;

  const isStarting = runState === "starting";
  const label = isStarting
    ? "STARTING …"
    : iteration != null && iteration > 0
    ? `LIVE · iter ${iteration}`
    : "LIVE";

  return (
    <span
      data-testid="topbar-live-pill"
      data-run-state={runState}
      data-iteration={iteration ?? ""}
      className={
        "inline-flex items-center text-[10px] font-mono uppercase " +
        "tracking-[0.08em] border border-v3-accent text-v3-accent " +
        "rounded px-2 py-0.5"
      }
    >
      <span
        aria-hidden
        className="inline-block w-1.5 h-1.5 rounded-full bg-v3-accent mr-1.5 animate-pulse"
      />
      {label}
    </span>
  );
}
