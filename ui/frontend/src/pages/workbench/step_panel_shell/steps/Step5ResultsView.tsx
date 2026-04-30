// Step 5 · Results — multi-figure research-grade post-processing
// (2026-04-30 dogfood-feedback rewrite).
//
// The original Phase-1A wireup just fetched /results-summary and
// rendered min/max/mean of |U| as a small text card. User feedback:
// that's far below the line-B pipeline's multi-data reports.
//
// This rewrite hits the new GET /report-bundle endpoint which returns
// four pre-rendered PNGs (contour+streamlines, pressure, vorticity,
// centerline) plus a summary string. The Step 5 right-rail keeps the
// concise text summary; the actual figure GRID is rendered by the
// matching custom viewport (Step5ResultsGrid) wired into the shell.
//
// The right rail registers the [AI 处理] action which simply re-fetches
// the bundle. matplotlib renders cache by final_time so a re-fetch
// after a re-solve picks up the new field; same-final-time fetches
// short-circuit at <1s.

import { useCallback, useEffect, useState } from "react";

import { useQuery, useQueryClient } from "@tanstack/react-query";

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
  const queryClient = useQueryClient();
  // Codex round-7 P3 (2026-04-30): observe the same React Query cache
  // entry the grid uses so the right rail's "✓ Bundle ready" card
  // disappears when the grid drops the cache (e.g. on 410 stale-tile
  // detection). Local useState held bundle independently and could
  // drift out of sync. resultsSummary stays in local state because
  // it's a separate endpoint with its own lifecycle, but it's reset
  // alongside the bundle on every fetchBundle call.
  const bundleQuery = useQuery({
    queryKey: ["report-bundle", caseId],
    queryFn: () => api.reportBundle(caseId),
    enabled: false,
    retry: false,
    staleTime: Infinity,
  });
  const bundle = bundleQuery.data ?? null;
  const [resultsSummary, setResultsSummary] = useState<ResultsSummary | null>(
    null,
  );
  const [rejection, setRejection] = useState<CaseSolveRejection | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  // Codex round-15 P3 (2026-04-30): a 409 from /report-bundle is the
  // documented "Step 4 (solve) hasn't run yet" precondition — not a
  // failure. Round-6 routed it through `rejection`, but that state
  // drives the red `step5-results-rejection` card, contradicting
  // the center grid's neutral "finish Step 4 first" hint. Use a
  // separate state with a neutral surface_900/40 banner so the
  // right rail mirrors the grid's UX instead of flagging the step
  // as errored.
  const [preSolveHint, setPreSolveHint] = useState<string | null>(null);

  // Reset resultsSummary whenever the bundle cache is dropped (the
  // grid's onStale handler removeQueries it on a 410 / SolveStream
  // does the same on a re-solve). Without this, the right rail
  // would keep showing stale recirculation text after the grid
  // already collapsed back to its empty hint.
  useEffect(() => {
    if (bundle === null) {
      setResultsSummary(null);
    }
  }, [bundle]);

  const fetchBundle = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    setPreSolveHint(null);
    // Codex round-9 P2 (2026-04-30): the prior implementation Promise.all'd
    // fetchQuery(report-bundle) and api.resultsSummary, then dropped the
    // bundle cache from a single shared catch block. A summary failure
    // would therefore wipe an already-successful bundle (4 PNGs) from
    // the cache and collapse the grid back to the empty hint —
    // confusing because the figures had already rendered server-side.
    // We now sequence the two fetches so the cleanup only fires when
    // /report-bundle itself failed; a downstream summary fetch error
    // is best-effort (the recirculation banner just doesn't surface).
    try {
      // fetchQuery populates the React Query cache under
      // ['report-bundle', caseId]; the matching Step5ResultsGrid
      // useQuery hook observes the same cache entry and re-renders
      // automatically when this resolves. invalidateQueries first
      // so any stale observers re-render — the matplotlib render is
      // already cached on disk keyed by cache_version (final_time +
      // U mtime) so the network request is cheap when nothing
      // changed.
      await queryClient.invalidateQueries({
        queryKey: ["report-bundle", caseId],
      });
      await queryClient.fetchQuery({
        queryKey: ["report-bundle", caseId],
        queryFn: () => api.reportBundle(caseId),
      });
    } catch (e) {
      // Codex round-8 P2 (2026-04-30): React Query preserves the
      // previous successful `data` payload when a later fetchQuery
      // throws. Drop the cache entry so the right rail and grid
      // both see data===undefined immediately and don't show a
      // stale "✓ Bundle ready" card next to the new error.
      queryClient.removeQueries({
        queryKey: ["report-bundle", caseId],
      });
      // Codex round-6 P3 (2026-04-30): a 409 from /report-bundle just
      // means "Step 4 hasn't run yet" — that's an expected precondition
      // miss when the user clicks [AI 处理] on Step 5 first. The center
      // grid already shows a friendly "finish Step 4 first" hint; the
      // right rail should mirror that, not flag the step as errored.
      // Codex round-15 P3: route through the neutral preSolveHint
      // surface, not the red rejection card.
      if (e instanceof ApiError && e.status === 409) {
        setPreSolveHint(
          typeof e.message === "string" && e.message.length > 0
            ? e.message
            : "Solve hasn't run yet. Finish Step 4 (solve) first.",
        );
        // Don't onStepError() — 409 is an expected pre-solve state.
        return;
      }
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object" &&
        "failing_check" in e.detail
      ) {
        const detail = e.detail as CaseSolveRejection;
        setRejection(detail);
        onStepError(`report-bundle rejected: ${detail.failing_check}`);
      } else if (e instanceof ApiError && typeof e.message === "string") {
        setNetworkError(`${e.message} (HTTP ${e.status})`);
        onStepError(e.message);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setNetworkError(msg);
        onStepError(msg);
      }
      throw e;
    }
    // Bundle fetch succeeded; the grid is already rendering. Pull the
    // results-summary as a best-effort enrichment — its only consumer
    // is the LDC recirculation sanity banner, which simply hides if
    // resultsSummary stays null. A failure here must NOT drop the
    // freshly-fetched bundle.
    try {
      const s = await api.resultsSummary(caseId);
      setResultsSummary(s);
    } catch {
      setResultsSummary(null);
    }
    onStepComplete();
  }, [caseId, onStepComplete, onStepError, queryClient]);

  useEffect(() => {
    registerAiAction(fetchBundle);
    return () => registerAiAction(null);
  }, [registerAiAction, fetchBundle]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step5-results-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 5 · Results
      </h2>
      <p className="text-surface-400">
        Render the final field as a multi-panel report — |U| contour
        with streamlines, gauge pressure, vorticity, and centreline
        velocity profiles.
      </p>

      {!bundle && !rejection && !networkError && !preSolveHint && (
        <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
          Click <strong className="text-surface-200">[AI 处理]</strong> to
          render the report bundle from the final time directory.
        </p>
      )}

      {preSolveHint && (
        <p
          data-testid="step5-results-pre-solve-hint"
          className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400"
        >
          {preSolveHint}
        </p>
      )}

      {bundle && (() => {
        // Codex round-4 P2 (2026-04-30): the recirculation sanity
        // check is meaningful ONLY for closed-cavity LDC cases. On a
        // through-flow channel `is_recirculating` is correctly false,
        // and surfacing it as an amber warning would be a false
        // positive. Gate on bundle.case_kind so non-LDC flows just
        // show the green ✓ banner without the LDC-specific check.
        const isLdc = bundle.case_kind === "lid_driven_cavity";
        const recircFails =
          isLdc && resultsSummary !== null && !resultsSummary.is_recirculating;
        return (
          <div
            data-testid="step5-results-success"
            className={
              "space-y-2 rounded-sm border p-2 " +
              (recircFails
                ? "border-amber-700/50 bg-amber-900/10"
                : "border-emerald-700/40 bg-emerald-900/10")
            }
          >
            <div
              className={
                "font-mono text-[11px] " +
                (recircFails ? "text-amber-200" : "text-emerald-200")
              }
            >
              {recircFails
                ? "⚠ Bundle ready — but field doesn't look like a closed-cavity recirculation. Check BCs / convergence."
                : "✓ Bundle ready — see grid in the centre pane."}
            </div>
            <ul className="space-y-1 font-mono text-[10px] text-surface-300">
              <li>final time: t = {bundle.final_time}s</li>
              <li>{bundle.summary_text}</li>
              <li>
                plane: {bundle.plane_axes.join("-")} ·{" "}
                {bundle.slab_cell_count.toLocaleString()} slab cells · case
                kind: {bundle.case_kind}
              </li>
              {isLdc && resultsSummary && (
                <li className="pt-1 text-surface-500">
                  {resultsSummary.is_recirculating
                    ? "Mean Ux ≈ 0 with min/max spanning ±values: vortex confirmed."
                    : "Mean Ux ≠ 0: would indicate plug flow or solver issue."}
                </li>
              )}
            </ul>
            <p className="pt-1 text-[10px] text-surface-500">
              Re-click [AI 处理] after a re-solve to refresh; matplotlib
              output is cached per cache_version (final_time + U mtime)
              so unchanged solves return in &lt;1 s.
            </p>
          </div>
        );
      })()}

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
          {networkError}
        </div>
      )}
    </div>
  );
}
