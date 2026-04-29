// Step 4 · Solve — Phase-1A live-streaming variant (DEC-V61-097).
//
// Replaces the blocking POST /solve with the streaming
// POST /solve-stream endpoint. The [AI 处理] action now starts the
// stream via the SolveStream context; the LiveResidualChart in the
// viewport reads from that same context to render residuals live.
//
// User report 2026-04-29: "第4步应该直接实时监控求解器的残差图，
// 而不是跑完了给我一个截图." This component implements that.

import { useCallback, useEffect } from "react";

import { useSolveStream } from "../SolveStreamContext";

import type { StepTaskPanelProps } from "../types";

const REJECTION_HINTS: Record<string, string> = {
  bc_not_setup:
    "Run Step 3 (setup-bc) before solving — icoFoam needs the dict files.",
  container_unavailable:
    "The cfd-openfoam container is not running. Start it with: docker start cfd-openfoam",
  solver_diverged:
    "icoFoam exited non-zero. Check the log file at the case dir for divergence.",
  post_stage_failed:
    "icoFoam ran but the host couldn't pull time directories back from the container.",
};

const formatRes = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : v.toExponential(3);

export function Step4SolveRun({
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
}: StepTaskPanelProps) {
  const { phase, summary, errorMessage, start, series } = useSolveStream();

  const triggerSolve = useCallback(async () => {
    await start(caseId);
  }, [caseId, start]);

  useEffect(() => {
    registerAiAction(triggerSolve);
    return () => registerAiAction(null);
  }, [registerAiAction, triggerSolve]);

  // Map phase transitions to the shell's onStepComplete / onStepError.
  useEffect(() => {
    if (phase === "completed" && summary) {
      onStepComplete();
    } else if (phase === "error" && errorMessage) {
      onStepError(errorMessage);
    }
  }, [phase, summary, errorMessage, onStepComplete, onStepError]);

  const lastRow = series[series.length - 1];
  const progressPct =
    lastRow && lastRow.t ? Math.min(100, (lastRow.t / 2.0) * 100) : 0;

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step4-solve-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 4 · Solve
      </h2>
      <p className="text-surface-400">
        icoFoam · 400 steps × Δt=0.005 → endTime=2s. Residuals stream
        live to the chart in the center pane.
      </p>

      {phase === "idle" && (
        <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
          Click <strong className="text-surface-200">[AI 处理]</strong> to
          start streaming the solver.
        </p>
      )}

      {phase === "streaming" && (
        <div
          data-testid="step4-solve-streaming"
          className="space-y-2 rounded-sm border border-amber-700/50 bg-amber-900/10 p-2"
        >
          <div className="font-mono text-[11px] text-amber-200">
            ⟳ icoFoam streaming…
          </div>
          <div className="font-mono text-[10px] text-surface-300">
            t = {lastRow?.t.toFixed(3) ?? "0.000"}s &nbsp;·&nbsp;{" "}
            {progressPct.toFixed(0)}% &nbsp;·&nbsp;{" "}
            {series.length} timesteps captured
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-900">
            <div
              data-testid="step4-solve-progress-bar"
              className="h-full rounded-full bg-amber-400 transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {phase === "completed" && summary && (
        <div
          data-testid="step4-solve-success"
          className={
            "space-y-2 rounded-sm border p-2 " +
            (summary.converged
              ? "border-emerald-700/40 bg-emerald-900/10"
              : "border-amber-700/50 bg-amber-900/10")
          }
        >
          <div
            className={
              "font-mono text-[11px] " +
              (summary.converged ? "text-emerald-200" : "text-amber-200")
            }
          >
            {summary.converged
              ? "✓ Solver converged"
              : "⚠ Solver finished, convergence borderline"}
          </div>
          <ul className="space-y-1 font-mono text-[10px] text-surface-300">
            <li>endTime reached: {summary.end_time_reached.toFixed(3)}s</li>
            <li>
              Initial residuals (last step):
              <ul className="ml-3 list-disc">
                <li>p: {formatRes(summary.last_initial_residual_p)}</li>
                <li>
                  Ux/Uy/Uz: {formatRes(summary.last_initial_residual_U[0])} /{" "}
                  {formatRes(summary.last_initial_residual_U[1])} /{" "}
                  {formatRes(summary.last_initial_residual_U[2])}
                </li>
                <li>continuity: {formatRes(summary.last_continuity_error)}</li>
              </ul>
            </li>
            <li>
              time directories: {summary.n_time_steps_written} (
              {summary.time_directories.join(", ")})
            </li>
            <li>wall-time: {summary.wall_time_s.toFixed(1)}s</li>
          </ul>
        </div>
      )}

      {phase === "error" && errorMessage && (
        <div
          data-testid="step4-solve-error"
          className="space-y-1 rounded-sm border border-rose-700/50 bg-rose-900/10 p-2 text-[11px]"
        >
          <div className="font-mono text-rose-300">✗ Solve failed</div>
          <div className="text-rose-200">{errorMessage}</div>
          {Object.entries(REJECTION_HINTS).map(([key, hint]) =>
            errorMessage.toLowerCase().includes(key.replace("_", " ")) ? (
              <div key={key} className="pt-1 text-[10px] text-rose-300/70">
                {hint}
              </div>
            ) : null,
          )}
        </div>
      )}
    </div>
  );
}
