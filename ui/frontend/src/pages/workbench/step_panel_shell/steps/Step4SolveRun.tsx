// Step 4 · Solve — wired in Phase-1A (DEC-V61-097).
//
// Invokes icoFoam in the cfd-openfoam container via
// POST /api/import/<id>/solve. The call blocks for ~60s (icoFoam
// running 400 implicit time steps); a spinner is provided by the
// shell's aiInFlight wrapper.

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  CaseSolveRejection,
  SolveSummary,
} from "@/types/case_solve";

import type { StepTaskPanelProps } from "../types";

const REJECTION_HINTS: Record<string, string> = {
  bc_not_setup:
    "Run Step 3 (setup-bc) before solving — icoFoam needs the dict files.",
  container_unavailable:
    "The cfd-openfoam container is not running. Start it with: docker start cfd-openfoam",
  solver_diverged:
    "icoFoam exited non-zero. Check the log file at the case dir for divergence/Floating-point errors.",
  post_stage_failed:
    "icoFoam ran but the host couldn't pull time directories back from the container. Likely a docker SDK or filesystem fault.",
};

export function Step4SolveRun({
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
}: StepTaskPanelProps) {
  const [summary, setSummary] = useState<SolveSummary | null>(null);
  const [rejection, setRejection] = useState<CaseSolveRejection | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const triggerSolve = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    try {
      const r = await api.solve(caseId);
      setSummary(r);
      onStepComplete();
    } catch (e) {
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object" &&
        "failing_check" in e.detail
      ) {
        const detail = e.detail as CaseSolveRejection;
        setRejection(detail);
        onStepError(`solve rejected: ${detail.failing_check}`);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setNetworkError(msg);
        onStepError(msg);
      }
      throw e;
    }
  }, [caseId, onStepComplete, onStepError]);

  useEffect(() => {
    registerAiAction(triggerSolve);
    return () => registerAiAction(null);
  }, [registerAiAction, triggerSolve]);

  const formatRes = (v: number | null) =>
    v === null ? "—" : v.toExponential(3);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step4-solve-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 4 · Solve
      </h2>
      <p className="text-surface-400">
        icoFoam · 400 steps × Δt=0.005 → endTime=2s. Runs in the
        cfd-openfoam container (≈60s wall-time).
      </p>

      {!summary && !rejection && !networkError && (
        <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
          Click <strong className="text-surface-200">[AI 处理]</strong> below
          to start the solver.
        </p>
      )}

      {summary && (
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
              : "⚠ Solver finished but convergence is borderline"}
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
              time directories written: {summary.n_time_steps_written} ({summary.time_directories.join(", ")})
            </li>
            <li>wall-time: {summary.wall_time_s.toFixed(1)}s</li>
          </ul>
        </div>
      )}

      {rejection && (
        <div
          data-testid="step4-solve-rejection"
          className="space-y-1 rounded-sm border border-rose-700/50 bg-rose-900/10 p-2 text-[11px]"
        >
          <div className="font-mono text-rose-300">
            ✗ {rejection.failing_check}
          </div>
          <div className="text-rose-200">{rejection.detail}</div>
          {REJECTION_HINTS[rejection.failing_check] && (
            <div className="pt-1 text-[10px] text-rose-300/70">
              {REJECTION_HINTS[rejection.failing_check]}
            </div>
          )}
        </div>
      )}

      {networkError && (
        <div
          data-testid="step4-solve-network-error"
          className="rounded-sm border border-rose-700/50 bg-rose-900/10 px-2 py-1 text-[11px] text-rose-200"
        >
          Network error: {networkError}
        </div>
      )}
    </div>
  );
}
