// Workflow Monitor · page (DEC-V61-226)
// --------------------------------------
// The "visible / resumable / traceable CFD workflow runtime" surface, built
// in-house on the existing React + (future) SSE substrate rather than an
// external orchestration platform (chief-engineer decision, 2026-06-03 —
// see types/workflow.ts header for rationale).
//
// FIRST DELIVERABLE (user-chosen): the frontend page, MOCK-data-driven, so the
// interaction/layout can be validated before wiring the real backend. The
// `isMock` banner is indelible — a design-preview run can NEVER be mistaken for
// a real solve (the project's defining honesty invariant).
//
// Layout: left = stage flow graph · center = current-object preview + structured
// status · right = advisor explanation log · bottom = stage timeline.
//
// Lives at pages/workflow_monitor/ (NOT pages/workbench/) so it is outside the
// §11.1 workbench freeze — it is a new observation surface, not a workbench fork.

import { useState } from "react";

import type { WorkflowRun, WorkflowRunSummary } from "@/types/workflow";
import { WORKFLOW_MONITOR_MOCK } from "@/data/workflowMonitorMock";

import {
  AdvisorLog,
  StageGraph,
  StagePreview,
  StageTimeline,
} from "./panels";

export function WorkflowMonitorPage({
  run = WORKFLOW_MONITOR_MOCK,
  runs = [],
  selectedRunKey,
  onSelectRun,
}: {
  // Pure presentational. Injectable `run` so a real /api/workflow-runs payload
  // (via WorkflowMonitorRoute) or a test drives the same page. Defaults to the
  // design-preview fixture. `runs`/`onSelectRun` render an optional run picker.
  run?: WorkflowRun;
  runs?: WorkflowRunSummary[];
  selectedRunKey?: string | null;
  onSelectRun?: (key: string) => void;
}) {
  const [selectedKey, setSelectedKey] = useState<string>(run.currentStage);
  const selected =
    run.stages.find((s) => s.key === selectedKey) ?? run.stages[0];

  return (
    <div className="mx-auto flex h-full max-w-7xl flex-col gap-4 px-5 py-6">
      {run.isMock && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-contract-hazard/50 bg-contract-hazard/10 px-3 py-2"
        >
          <span className="rounded-sm bg-contract-hazard/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-contract-hazard">
            Mock · design preview
          </span>
          <span className="text-xs text-surface-200">
            非真实算例 — this page is driven by hand-authored mock data to validate
            the WorkflowMonitor layout. It is NOT a CFD run and is not yet wired to
            the backend.
          </span>
        </div>
      )}

      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
            Workflow Monitor · DEC-V61-226
          </p>
          <h1 className="mt-0.5 text-2xl font-semibold text-surface-100">
            {run.caseName}
          </h1>
        </div>
        <p className="font-mono text-[11px] text-surface-500">run: {run.runId}</p>
      </header>

      {runs.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-[0.12em] text-surface-400">
            Run
          </span>
          {runs.map((r) => {
            const active = r.runKey === (selectedRunKey ?? run.runId);
            return (
              <button
                key={r.runKey}
                type="button"
                onClick={() => onSelectRun?.(r.runKey)}
                className={`rounded-sm border px-2 py-1 text-xs transition-colors ${
                  active
                    ? "border-surface-500 bg-surface-800 text-surface-100"
                    : "border-surface-800 bg-surface-900/40 text-surface-300 hover:bg-surface-800/50"
                }`}
              >
                {r.runKey.replace("naca0012_showcase_", "")}
              </button>
            );
          })}
        </div>
      )}

      <main className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(220px,260px)_minmax(0,1fr)_minmax(260px,320px)]">
        <StageGraph
          stages={run.stages}
          selectedKey={selectedKey}
          currentStage={run.currentStage}
          onSelect={setSelectedKey}
        />
        <StagePreview stage={selected} />
        <AdvisorLog entries={run.advisorLog} />
      </main>

      <StageTimeline timeline={run.timeline} currentStage={run.currentStage} />
    </div>
  );
}

export default WorkflowMonitorPage;
