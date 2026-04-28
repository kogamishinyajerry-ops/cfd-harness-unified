// Step 5 · Results — wired in Phase-1A (DEC-V61-097).
//
// Fetches GET /api/cases/<id>/results-summary, displays U field
// statistics + a recirculation flag (LDC sanity check). Step 5 is
// the only step where [AI 处理] simply re-fetches the summary —
// nothing to compute, just read.

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  CaseSolveRejection,
  ResultsSummary,
} from "@/types/case_solve";

import type { StepTaskPanelProps } from "../types";

const REJECTION_HINTS: Record<string, string> = {
  solve_not_run:
    "Run Step 4 (solve) first — there's no time directory > 0 to read from.",
  results_malformed:
    "The U field couldn't be parsed. The solver may have crashed mid-run; check log.icoFoam.",
};

export function Step5ResultsView({
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
}: StepTaskPanelProps) {
  const [summary, setSummary] = useState<ResultsSummary | null>(null);
  const [rejection, setRejection] = useState<CaseSolveRejection | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    try {
      const r = await api.resultsSummary(caseId);
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
        onStepError(`results-summary rejected: ${detail.failing_check}`);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setNetworkError(msg);
        onStepError(msg);
      }
      throw e;
    }
  }, [caseId, onStepComplete, onStepError]);

  useEffect(() => {
    registerAiAction(fetchSummary);
    return () => registerAiAction(null);
  }, [registerAiAction, fetchSummary]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step5-results-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 5 · Results
      </h2>
      <p className="text-surface-400">
        Read the final U field, summarize the velocity distribution.
      </p>

      {!summary && !rejection && !networkError && (
        <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
          Click <strong className="text-surface-200">[AI 处理]</strong> to
          fetch the result summary from the final time directory.
        </p>
      )}

      {summary && (
        <div
          data-testid="step5-results-success"
          className={
            "space-y-2 rounded-sm border p-2 " +
            (summary.is_recirculating
              ? "border-emerald-700/40 bg-emerald-900/10"
              : "border-amber-700/50 bg-amber-900/10")
          }
        >
          <div
            className={
              "font-mono text-[11px] " +
              (summary.is_recirculating
                ? "text-emerald-200"
                : "text-amber-200")
            }
          >
            {summary.is_recirculating
              ? "✓ Recirculating LDC vortex detected"
              : "⚠ Field doesn't look like a closed-cavity recirculation"}
          </div>
          <ul className="space-y-1 font-mono text-[10px] text-surface-300">
            <li>final time: t = {summary.final_time}s</li>
            <li>cells: {summary.cell_count.toLocaleString()}</li>
            <li>
              |U|: min={summary.u_magnitude_min.toExponential(2)} m/s, max=
              {summary.u_magnitude_max.toFixed(3)} m/s, mean=
              {summary.u_magnitude_mean.toFixed(3)} m/s
            </li>
            <li>
              Ux: min={summary.u_x_min.toFixed(3)} m/s, max=
              {summary.u_x_max.toFixed(3)} m/s, mean=
              {summary.u_x_mean.toExponential(2)} m/s
            </li>
            <li className="pt-1 text-surface-500">
              {summary.is_recirculating
                ? "Mean Ux ≈ 0 with min/max spanning ±values: vortex confirmed."
                : "Mean Ux ≠ 0: would indicate plug flow or solver issue."}
            </li>
          </ul>
        </div>
      )}

      {rejection && (
        <div
          data-testid="step5-results-rejection"
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
          data-testid="step5-results-network-error"
          className="rounded-sm border border-rose-700/50 bg-rose-900/10 px-2 py-1 text-[11px] text-rose-200"
        >
          Network error: {networkError}
        </div>
      )}
    </div>
  );
}
