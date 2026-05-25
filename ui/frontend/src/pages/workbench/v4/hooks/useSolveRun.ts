// DEC-V61-204 · M4 cycle 2 · V4 run-trigger.
//
// Engineer-initiated solve mutation for the V4 Step-6 (solver) topbar CTA.
// Mirrors the M3.0 PATCH loop (useManifestPatch): observation → engineer
// action → backend mutation → invalidate the read queries so results
// refresh. The AI never auto-runs this — it fires only from a button
// click (advisor-not-driver, DEC-V61-130; four-question gate V130).
//
// `/solve` is a blocking ~60s backend Docker call (api.solve →
// POST /api/import/{caseId}/solve → SolveSummary). On success we invalidate
// the V4 read queries that reflect post-run state so Step-6/7 refresh
// without a manual reload:
//   - v4-residual-series : the residual convergence chart (Step-6/7)
//   - v4-ctx-runs        : run history → latestRun (ModeRendererSolver/Post)
//   - v4-ctx-detail      : per-run detail (residual source flips empty→log)
//   - v4-advisor-runs    : advisor match list keyed off the latest run
//   - v4-report-bundle   : matplotlib figure bundle (M4 C3) — re-render
//                          on the new run's cache_version

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { SolveSummary } from "@/types/case_solve";

export interface UseSolveRunResult {
  /**
   * Engineer-initiated trigger. No-op while a run is already in flight or
   * when no case is selected (the CTA is also disabled in those states),
   * so a double-click can't launch two solves.
   */
  runSolve: () => void;
  isRunning: boolean;
  summary: SolveSummary | null;
  error: Error | null;
  reset: () => void;
}

/** Query keys whose data reflects post-run state — invalidated on a
 *  successful solve so the V4 Step-6/7 surfaces re-fetch. caseId is
 *  appended at call time. */
const POST_RUN_QUERY_PREFIXES = [
  "v4-residual-series",
  "v4-ctx-runs",
  "v4-ctx-detail",
  "v4-advisor-runs",
  "v4-report-bundle",
] as const;

export function useSolveRun(
  caseId: string | null | undefined,
): UseSolveRunResult {
  const qc = useQueryClient();

  const mutation = useMutation<SolveSummary, unknown, void>({
    mutationKey: ["v4-solve-run", caseId ?? "__none__"],
    mutationFn: () => {
      if (!caseId) {
        return Promise.reject(new Error("no case selected"));
      }
      return api.solve(caseId);
    },
    onSuccess: () => {
      if (!caseId) return;
      for (const prefix of POST_RUN_QUERY_PREFIXES) {
        // Partial-key invalidation: matches the prefixed query and any
        // deeper keys (e.g. v4-ctx-detail also carries a runId tail).
        qc.invalidateQueries({ queryKey: [prefix, caseId] });
      }
    },
  });

  return {
    runSolve: () => {
      if (caseId && !mutation.isPending) {
        mutation.mutate();
      }
    },
    isRunning: mutation.isPending,
    summary: mutation.data ?? null,
    error: (mutation.error as Error | null) ?? null,
    reset: mutation.reset,
  };
}
