/**
 * V4 · useV4WorkbenchContext · single hook fanning out the queries every
 * V4 zone (TopBar / LeftRail / KPI / RightPanel / BottomBar) needs to
 * render REAL backend data.
 *
 * Goal: turn the V4 shell from "placeholder mock data everywhere" into
 * "actual case + run telemetry" without forcing each zone to re-fetch.
 *
 * Endpoints aggregated (all GET · idempotent · V132 advisor surface):
 *   - api.listCases()                       → display name lookup
 *   - api.getWorkbenchBasics(caseId)        → patches · materials · solver · geometry
 *   - api.getMeshMetrics(caseId)            → mesh densities · GCI · QC band
 *   - api.getCaseCompleteness(caseId)       → pipeline step state
 *   - api.listRuns(caseId)                  → latest run id + duration
 *   - api.getRunDetail(caseId, latestRunId) → residuals · key_quantities · success
 *
 * Graceful degrade: when caseId is null OR backend returns 404/5xx,
 * fields default to null and components fall back to placeholder mocks.
 * 4Q gate: no mutation surface · pure read-only fan-out.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { CaseIndexEntry } from "@/types/validation";
import type { WorkbenchBasics } from "@/types/workbench_basics";
import type { MeshMetrics } from "@/types/mesh_metrics";
import type { CaseCompletenessReport } from "@/types/case_completeness";
import type { RunDetail, RunSummaryEntry } from "@/types/run_history";

const STALE = 30_000;
const RETRY = 1;

export interface V4Context {
  caseId: string | null;

  // Identity
  displayName: string | null;
  displayNameZh: string | null;

  // Run telemetry
  latestRun: RunSummaryEntry | null;
  /** Most recent run with success=true. Differs from ``latestRun`` when
   *  the most recent attempt failed — Post mode prefers this so the
   *  centerline + residuals stay informative; TopBar still surfaces
   *  ``latestRun`` so the user sees the actual head of history. */
  latestSuccessfulRun: RunSummaryEntry | null;
  runDetail: RunDetail | null;
  /** Detail for ``latestSuccessfulRun`` (or null if none exists). */
  successfulRunDetail: RunDetail | null;
  elapsedSeconds: number | null;
  elapsedDisplay: string; // "HH:MM:SS" formatted · "—" when null

  // Workbench artifacts
  basics: WorkbenchBasics | null;
  meshMetrics: MeshMetrics | null;
  completeness: CaseCompletenessReport | null;

  // Status flags
  isLoading: boolean;
  hasBackend: boolean; // true iff at least one query returned data
  error: Error | null;
}

function formatElapsed(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "—";
  const s = Math.floor(seconds);
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

export function useV4WorkbenchContext(caseId: string | null): V4Context {
  const enabled = Boolean(caseId);

  // Case index (case display names · lightweight · shared cache)
  const casesQ = useQuery<CaseIndexEntry[]>({
    queryKey: ["v4-ctx-cases"],
    queryFn: () => api.listCases(),
    staleTime: 60_000,
    retry: RETRY,
    refetchOnWindowFocus: false,
  });

  // Workbench basics (patches/materials/solver/geometry)
  const basicsQ = useQuery<WorkbenchBasics>({
    queryKey: ["v4-ctx-basics", caseId],
    queryFn: () => api.getWorkbenchBasics(caseId as string),
    enabled,
    staleTime: STALE,
    retry: RETRY,
    refetchOnWindowFocus: false,
  });

  // Mesh metrics
  const meshQ = useQuery<MeshMetrics>({
    queryKey: ["v4-ctx-mesh", caseId],
    queryFn: () => api.getMeshMetrics(caseId as string),
    enabled,
    staleTime: STALE,
    retry: 0, // tolerate 404 (case may have no mesh-metrics)
    refetchOnWindowFocus: false,
  });

  // Completeness (pipeline step state)
  const completenessQ = useQuery<CaseCompletenessReport>({
    queryKey: ["v4-ctx-completeness", caseId],
    queryFn: () => api.getCaseCompleteness(caseId as string),
    enabled,
    staleTime: STALE,
    retry: 0,
    refetchOnWindowFocus: false,
  });

  // Run history (latest run lookup)
  const runsQ = useQuery({
    queryKey: ["v4-ctx-runs", caseId],
    queryFn: () => api.listRuns(caseId as string),
    enabled,
    staleTime: STALE,
    retry: RETRY,
    refetchOnWindowFocus: false,
  });

  const latestRun: RunSummaryEntry | null =
    runsQ.data?.runs?.[0] ?? null;
  const latestRunId = latestRun?.run_id ?? null;

  // Most recent successful run · Post mode prefers this so a failed
  // tail of run history doesn't blank out the centerline + residuals.
  const latestSuccessfulRun: RunSummaryEntry | null =
    runsQ.data?.runs?.find((r) => r.success) ?? null;
  const successfulRunId = latestSuccessfulRun?.run_id ?? null;

  // Run detail (residuals + key_quantities · only when latestRunId known)
  const detailQ = useQuery<RunDetail>({
    queryKey: ["v4-ctx-detail", caseId, latestRunId],
    queryFn: () =>
      api.getRunDetail(caseId as string, latestRunId as string),
    enabled: enabled && Boolean(latestRunId),
    staleTime: STALE,
    retry: RETRY,
    refetchOnWindowFocus: false,
  });

  // Successful-run detail · skipped when it equals latestRunId (most
  // common case) to save a duplicate fetch; React Query also dedupes
  // by queryKey so the shared key wouldn't double-fetch anyway.
  const successDetailQ = useQuery<RunDetail>({
    queryKey: ["v4-ctx-detail", caseId, successfulRunId],
    queryFn: () =>
      api.getRunDetail(caseId as string, successfulRunId as string),
    enabled:
      enabled &&
      Boolean(successfulRunId) &&
      successfulRunId !== latestRunId,
    staleTime: STALE,
    retry: RETRY,
    refetchOnWindowFocus: false,
  });

  const ctx = useMemo<V4Context>(() => {
    const caseEntry =
      casesQ.data?.find((c) => c.case_id === caseId) ?? null;
    const elapsed = latestRun?.duration_s ?? null;

    return {
      caseId,
      displayName: caseEntry?.name ?? caseId,
      displayNameZh:
        basicsQ.data?.display_name_zh ??
        caseEntry?.name ??
        caseId,
      latestRun,
      latestSuccessfulRun,
      runDetail: detailQ.data ?? null,
      successfulRunDetail:
        successfulRunId === latestRunId
          ? detailQ.data ?? null
          : successDetailQ.data ?? null,
      elapsedSeconds: elapsed,
      elapsedDisplay: formatElapsed(elapsed),
      basics: basicsQ.data ?? null,
      meshMetrics: meshQ.data ?? null,
      completeness: completenessQ.data ?? null,
      isLoading:
        casesQ.isLoading ||
        basicsQ.isLoading ||
        runsQ.isLoading ||
        detailQ.isLoading,
      hasBackend: Boolean(
        casesQ.data ||
          basicsQ.data ||
          meshQ.data ||
          completenessQ.data ||
          runsQ.data,
      ),
      error:
        (basicsQ.error as Error | null) ??
        (runsQ.error as Error | null) ??
        null,
    };
  }, [
    caseId,
    casesQ.data,
    casesQ.isLoading,
    basicsQ.data,
    basicsQ.isLoading,
    basicsQ.error,
    meshQ.data,
    completenessQ.data,
    runsQ.data,
    runsQ.isLoading,
    runsQ.error,
    detailQ.data,
    detailQ.isLoading,
    successDetailQ.data,
    successDetailQ.isLoading,
    successfulRunId,
    latestRunId,
    latestRun,
    latestSuccessfulRun,
  ]);

  return ctx;
}
