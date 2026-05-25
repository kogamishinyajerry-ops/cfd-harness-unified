// DEC-V61-204 · M4 cycle 3 · V4 report-bundle display.
//
// Fetches the backend matplotlib figure bundle for V4 Post. Unlike the
// retired V3 Step5ResultsGrid (which used enabled:false + a manual
// "[AI 处理]" button to populate the cache), V4 auto-fetches when the
// Post step is viewed with a case selected — there is no AI-run button
// in the advisor-not-driver UI (DEC-V61-130); the report is a read-only
// artifact of the solve.
//
// The artifact URLs are absolute backend paths
// (/api/cases/{id}/report/{name}.png?v={cache_version}); the embedded
// cache_version (final_time + U-field mtime) makes the browser refetch
// figures automatically after a re-solve. A fresh solve also invalidates
// this query (see useSolveRun) so the metadata + URLs refresh.
//
// Error states are surfaced (not swallowed) so ReportFiguresPanel can
// classify them: 409 (solver hasn't run), 500 + "matplotlib" (matplotlib
// absent on this build → "report unavailable"), 503 (results service
// down), other.

import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { ReportBundle } from "@/types/case_solve";

export interface UseReportBundleResult {
  data: ReportBundle | null;
  isLoading: boolean;
  error: Error | null;
}

export function useReportBundle(
  caseId: string | null | undefined,
): UseReportBundleResult {
  const q = useQuery<ReportBundle>({
    queryKey: ["v4-report-bundle", caseId ?? "__none__"],
    queryFn: () => api.reportBundle(caseId as string),
    enabled: typeof caseId === "string" && caseId.length > 0,
    // Report figures don't change until a re-solve (which invalidates
    // this key via useSolveRun), so a long staleTime avoids refetch churn.
    staleTime: 60_000,
    retry: 0,
    refetchOnWindowFocus: false,
  });
  return {
    data: q.data ?? null,
    isLoading: q.isLoading,
    error: (q.error as Error | null) ?? null,
  };
}
