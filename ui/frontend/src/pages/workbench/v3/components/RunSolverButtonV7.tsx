/**
 * V86.2 · V7.A Run Solver Button · USER-clickable trigger affordance
 *
 * Per .planning/blueprints/v7/INDEX.md Contract V7.A:
 *   - Surfaces in Engineer Control Rail / BottomPanel · NOT in sandbox /
 *     cinematic / bridge surfaces (those are read-only per V83.2 + V83.4
 *     + V85.X carries)
 *   - USER-click affordance ONLY · NO useEffect auto-fire · NO timer
 *     auto-execute · NO programmatic invocation outside user click event
 *   - Disabled when prerequisites unmet (meshReady=false OR bcSetup=false)
 *   - During runState="running", label flips to "Cancel run" + click
 *     invokes onCancelRun; cancellation is user-controlled (no runaway runs)
 *   - V130 invariant: AI does NOT call onRequestRun · parent state
 *     machine receives the user click and POSTs to existing
 *     /api/import/{case_id}/solve-stream endpoint (V132 = 9 preserved)
 *
 * V86 reverse-stops:
 *   #16 USER-click only (V130 invariant lexically enforced by denylist tests)
 *   #17 Engineer Control Rail only · not sandbox/cinematic/bridge
 *   #18 cancellable from UI (no runaway runs)
 */

import type { SolverRunState } from "../hooks/useSolverRunStateV7";

interface RunSolverButtonV7Props {
  caseId: string | null;
  meshReady: boolean;
  bcSetup: boolean;
  runState: SolverRunState;
  onRequestRun: () => void;
  onCancelRun: () => void;
}

function prereqMessage(meshReady: boolean, bcSetup: boolean): string | null {
  if (!meshReady && !bcSetup) return "mesh + BC not ready";
  if (!meshReady) return "mesh not ready";
  if (!bcSetup) return "BC not setup";
  return null;
}

export function RunSolverButtonV7({
  caseId,
  meshReady,
  bcSetup,
  runState,
  onRequestRun,
  onCancelRun,
}: RunSolverButtonV7Props) {
  const prereqUnmet = prereqMessage(meshReady, bcSetup);
  const caseUnset = caseId == null;
  const isRunning =
    runState === "running" || runState === "starting";
  // Disabled in idle when prereqs unmet OR no case; in terminal states
  // we let the user click again to start a new run (transitions back to
  // idle via dismiss flow handled by parent).
  const disabled = isRunning
    ? false  // running → button stays enabled to allow Cancel
    : caseUnset || prereqUnmet != null;

  const label = isRunning ? "Cancel run" : "Run solver";
  const handleClick = isRunning ? onCancelRun : onRequestRun;

  // Hint surfaces underneath the button so the user knows why the
  // button is disabled. We do NOT auto-fire when prereqs become satisfied —
  // user MUST explicitly click (V130 invariant).
  const hint = caseUnset
    ? "select a case to enable"
    : prereqUnmet
    ? `disabled · ${prereqUnmet}`
    : runState === "done"
    ? "last run completed · click to run again"
    : runState === "failed"
    ? "last run failed · click to retry"
    : runState === "cancelled"
    ? "run cancelled · click to retry"
    : null;

  return (
    <div
      data-testid="run-solver-v7"
      data-case-id={caseId ?? "__none__"}
      data-prerequisites-met={
        caseUnset || prereqUnmet ? "false" : "true"
      }
      data-run-state={runState}
      className="inline-flex flex-col items-start gap-0.5"
    >
      <button
        type="button"
        data-testid="run-solver-v7-button"
        onClick={handleClick}
        disabled={disabled}
        aria-label={isRunning ? "Cancel solver run" : "Start solver run"}
        className={
          isRunning
            ? "px-3 py-1 text-[11px] font-mono uppercase tracking-[0.08em] " +
              "border border-v3-accent text-v3-accent rounded " +
              "hover:bg-v3-accent/10 focus:outline focus:outline-2 " +
              "focus:outline-v3-borderFocus"
            : "px-3 py-1 text-[11px] font-mono uppercase tracking-[0.08em] " +
              "border border-v3-border rounded " +
              "text-v3-textPrimary disabled:text-v3-textTertiary " +
              "disabled:cursor-not-allowed disabled:opacity-50 " +
              "hover:enabled:border-v3-accent hover:enabled:text-v3-accent " +
              "focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        }
      >
        {label}
      </button>
      {hint && (
        <span
          data-testid="run-solver-v7-hint"
          className="text-[10px] text-v3-textTertiary font-mono"
        >
          {hint}
        </span>
      )}
    </div>
  );
}
