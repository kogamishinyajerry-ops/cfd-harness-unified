/**
 * V4 · useV4AdvisorMatches · binds RightPanelV4 / AdvisorPillStack to
 * the V91 matcher data flow.
 *
 * Pipeline:
 *   caseId → listRuns(caseId) → pick latest run → getRunDetail(caseId, runId)
 *          → adapt to RunArtifactSlice → matchAdvisorPatterns(slice, V9_RULES)
 *          → MatchedCommentary[]
 *
 * No mutation surface · GET only · matcher is pure · zero LLM call.
 * Aligns with V3's wiring pattern in WorkbenchShellV3.tsx but stays
 * decoupled (V4 owns its own hook so V3 abstractions aren't dragged in).
 *
 * Graceful states:
 *   - no caseId → matches=[], runId=null, isLoading=false
 *   - listRuns in flight → isLoading=true
 *   - listRuns succeeded but zero runs → matches=[], runId=null
 *   - getRunDetail failed → matches=[], error surfaced
 *
 * V90 RS#34 graceful-empty + V92 RS#39 manifest-adapter-degrade carried
 * forward: any failure path returns empty matches, never crashes.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import {
  matchAdvisorPatterns,
  type MatchedCommentary,
  type RunArtifactSlice,
} from "@/data/advisor_pattern_matcher";
import {
  V9_ADVISOR_RULES,
  V9_RULESET_VERSION,
} from "@/data/v9_advisor_rules";
import type { RunDetail } from "@/types/run_history";

/**
 * Adapt RunDetail (backend payload) to RunArtifactSlice (matcher input).
 *
 * RunDetail.residuals is single-value (`Record<string, number>`), but the
 * matcher expects history (`Record<string, number[]>`). History-array
 * support requires backend widening (V92 Open Q #3 BridgeArtifact widening).
 * For now: leave residuals undefined so history-dependent rules (R1
 * oscillation · R7 plateau) gracefully return null instead of false-match.
 */
function adaptRunDetailToSlice(detail: RunDetail): RunArtifactSlice {
  return {
    run_id: detail.run_id,
    case_id: detail.case_id,
    success: detail.success,
    exit_code: detail.exit_code,
    residuals: undefined,
    forces: undefined,
    convergence_stats: undefined,
    gold_delta: undefined,
    // W3.1 · DEC-V61-215 · forward-compat carry-through.
    // detail.regions is populated once W3.2 emits manifest["regions"] into
    // the run-detail backend payload. Until then undefined → R13–R16 silent.
    regions: detail.regions ?? undefined,
  };
}

export interface V4AdvisorMatchesResult {
  /** Matched commentary entries · empty when no run or no matches. */
  matches: MatchedCommentary[];
  /** Run_id of the latest completed run · null when no run available. */
  runId: string | null;
  /** Ruleset version (audit-trail). */
  rulesetVersion: string;
  /** Any fetch in flight. */
  isLoading: boolean;
  /** Last error encountered (listRuns or getRunDetail), null otherwise. */
  error: Error | null;
}

const EMPTY_MATCHES: MatchedCommentary[] = [];

export function useV4AdvisorMatches(
  caseId: string | null,
): V4AdvisorMatchesResult {
  const runsQuery = useQuery({
    queryKey: ["v4-advisor-runs", caseId],
    queryFn: () => api.listRuns(caseId as string),
    enabled: Boolean(caseId),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Latest run = first item (backend sorts newest-first per M3 contract).
  const latestRunId = runsQuery.data?.runs?.[0]?.run_id ?? null;

  const detailQuery = useQuery({
    queryKey: ["v4-advisor-detail", caseId, latestRunId],
    queryFn: () =>
      api.getRunDetail(caseId as string, latestRunId as string),
    enabled: Boolean(caseId) && Boolean(latestRunId),
    staleTime: 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const matches = useMemo<MatchedCommentary[]>(() => {
    if (!detailQuery.data) return EMPTY_MATCHES;
    const slice = adaptRunDetailToSlice(detailQuery.data);
    return matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
  }, [detailQuery.data]);

  const isLoading = runsQuery.isLoading || detailQuery.isLoading;
  const error =
    (runsQuery.error as Error | null) ??
    (detailQuery.error as Error | null) ??
    null;

  return {
    matches,
    runId: latestRunId,
    rulesetVersion: V9_RULESET_VERSION,
    isLoading,
    error,
  };
}
