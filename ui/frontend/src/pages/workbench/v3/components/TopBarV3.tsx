/**
 * V71-UI-V3 · TopBarV3 · workbench top bar per Image 01/02/05
 * 40px tall · breadcrumb left · run-state pill center-left · SHA/user/⌘K/gear right
 *
 * V74.3 · canonical run_id surfaces from /api/cases/:id/runs (the most
 * recent run's run_id). Fallback "no-run" placeholder shown when the case
 * has no runs yet or backend is offline.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { StepId } from "../WorkbenchShellV3";

interface TopBarV3Props {
  caseId: string | null;
  stepId: StepId;
}

function useLatestRunId(caseId: string | null) {
  return useQuery({
    queryKey: ["v3-topbar-latest-run", caseId],
    queryFn: () => api.listCaseRuns(caseId as string),
    enabled: Boolean(caseId),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function TopBarV3({ caseId }: TopBarV3Props) {
  const { data: runs, isError } = useLatestRunId(caseId);
  const latest = Array.isArray(runs) && runs.length > 0 ? runs[0] : null;
  const runId = latest?.run_id ?? null;
  const dataSource = runId ? "live" : isError ? "fallback" : "no-run";
  // 12-char truncation matches the established TruthChain provenance display
  const displayId = runId ? runId.slice(0, 12) : "no-run";
  return (
    <div
      data-testid="topbar-v3"
      data-v71-ui-shell="true"
      className="h-10 flex items-center px-4 text-[13px]"
    >
      <div className="text-v3-textSecondary">
        Workbench{caseId ? ` / ${caseId}` : ""}
      </div>
      <div className="ml-6 text-v3-textTertiary text-[11px] uppercase tracking-[0.08em]">
        {runId ? "● run · " : "○ no run · "}
        {/* V74.3 · data-source can be "live" | "fallback" | "no-run".
            "live" emitted when backend returned a real run_id. */}
        {dataSource === "live" ? (
          <span
            data-testid="topbar-run-id"
            data-source="live"
            className="font-mono normal-case tracking-normal"
          >
            {displayId}
          </span>
        ) : dataSource === "fallback" ? (
          <span
            data-testid="topbar-run-id"
            data-source="fallback"
            className="font-mono normal-case tracking-normal"
          >
            {displayId}
          </span>
        ) : (
          <span
            data-testid="topbar-run-id"
            data-source="no-run"
            className="font-mono normal-case tracking-normal"
          >
            {displayId}
          </span>
        )}
      </div>
      <div className="flex-1" />
      <div className="flex items-center gap-4 text-v3-textTertiary text-[11px]">
        <span className="font-mono">a4f3b21</span>
        <span
          role="img"
          aria-label="user avatar"
          className="w-5 h-5 rounded-full bg-v3-surface2 border border-v3-border"
        />
        <span>⌘K</span>
        <span role="img" aria-label="settings">⚙</span>
      </div>
    </div>
  );
}
