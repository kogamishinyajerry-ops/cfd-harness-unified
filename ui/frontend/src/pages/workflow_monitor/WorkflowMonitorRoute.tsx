// Workflow Monitor · route container (DEC-V61-226)
// -------------------------------------------------
// Fetches the REAL run set from /api/workflow-runs (assembled server-side from
// on-disk artifacts, is_mock=false) and feeds the pure WorkflowMonitorPage.
//
// Honest fallback: when the backend is unavailable (offline / no runs), the
// page falls back to the design-preview fixture — which renders its indelible
// MOCK banner, so a fallback is never mistaken for real data. The container is
// kept separate from the page so the page stays hook-free + trivially testable.

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { WORKFLOW_MONITOR_MOCK } from "@/data/workflowMonitorMock";

import { WorkflowMonitorPage } from "./WorkflowMonitorPage";

export function WorkflowMonitorRoute() {
  const runsQ = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: api.listWorkflowRuns,
    retry: false,
  });
  const runs = runsQ.data ?? [];

  const [selectedRunKey, setSelectedRunKey] = useState<string | null>(null);
  const effectiveKey = selectedRunKey ?? runs[0]?.runKey ?? null;

  const runQ = useQuery({
    queryKey: ["workflow-run", effectiveKey],
    queryFn: () => api.getWorkflowRun(effectiveKey as string),
    enabled: !!effectiveKey,
    retry: false,
  });

  // real fetched run > mock design-preview (the latter shows its MOCK banner).
  const run = runQ.data ?? WORKFLOW_MONITOR_MOCK;

  return (
    <WorkflowMonitorPage
      run={run}
      runs={runs}
      selectedRunKey={effectiveKey}
      onSelectRun={setSelectedRunKey}
    />
  );
}

export default WorkflowMonitorRoute;
