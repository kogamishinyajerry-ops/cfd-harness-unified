/**
 * V4 R6 · Residual-series fetch hook backing the Post-mode chart.
 *
 * Wraps the structured residual time-series endpoint
 * (`GET /api/cases/{case_id}/residual-series`). Source selection
 * happens server-side: parsed solver log when available, else
 * multi-run final residuals, else empty. The hook just relays.
 *
 * Caching: React Query with 30s staleTime — the underlying data
 * mutates only when a new run lands, which we don't subscribe to.
 * Re-fetch is forced when the caller passes a new caseId.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { ResidualSeriesPayload } from "@/types/residual_series";

const STALE = 30_000;

export interface UseResidualSeriesResult {
  data: ResidualSeriesPayload | null;
  isLoading: boolean;
  error: Error | null;
}

export function useResidualSeries(
  caseId: string | null | undefined,
): UseResidualSeriesResult {
  const q = useQuery<ResidualSeriesPayload>({
    queryKey: ["v4-residual-series", caseId ?? "__none__"],
    queryFn: () => api.getResidualSeries(caseId as string),
    enabled: typeof caseId === "string" && caseId.length > 0,
    staleTime: STALE,
    retry: 0,
    refetchOnWindowFocus: false,
  });
  return {
    data: q.data ?? null,
    isLoading: q.isLoading,
    error: (q.error as Error | null) ?? null,
  };
}

/** Convergence gauge derived from the latest residual sample · returns
 *  a percentage 0..100. Formula:
 *
 *      gauge = (−log10(latest_residual)) / (−log10(target_floor))
 *
 *  clamped to [0,1] and rendered ×100. So:
 *   • residual at target floor (1e-6) → gauge ≈ 100%
 *   • residual at 1e-3 (typical convergence target) → gauge ≈ 50%
 *   • residual at 1 (diverged / not started) → gauge = 0%
 *
 *  The "worst" series across (Ux, Uy, p) wins — overall convergence
 *  is bounded by the slowest equation. This matches OpenFOAM's
 *  practical convergence criterion ("all residuals below threshold").
 */
export function convergenceGaugeFromSeries(
  payload: ResidualSeriesPayload | null,
): { value: number; worst: string | null; achieved: boolean } {
  if (!payload || payload.sample_count === 0) {
    return { value: 0, worst: null, achieved: false };
  }
  const denom = -Math.log10(Math.max(1e-30, payload.target_floor));
  if (!Number.isFinite(denom) || denom <= 0) {
    return { value: 0, worst: null, achieved: false };
  }
  // Bottleneck = the equation with the LARGEST residual (slowest
  // convergence). OpenFOAM practical convergence requires ALL series
  // below threshold, so the worst series bounds the gauge.
  let worstSeries: string | null = null;
  let worstValue = -Infinity;
  for (const [name, points] of Object.entries(payload.series)) {
    const last = points[points.length - 1];
    if (!last || !Number.isFinite(last.y) || last.y <= 0) continue;
    if (last.y > worstValue) {
      worstValue = last.y;
      worstSeries = name;
    }
  }
  if (!Number.isFinite(worstValue) || worstValue <= 0) {
    return { value: 0, worst: null, achieved: false };
  }
  const numer = -Math.log10(worstValue);
  const ratio = Math.max(0, Math.min(1, numer / denom));
  return {
    value: ratio * 100,
    worst: worstSeries,
    achieved: payload.achieved,
  };
}
