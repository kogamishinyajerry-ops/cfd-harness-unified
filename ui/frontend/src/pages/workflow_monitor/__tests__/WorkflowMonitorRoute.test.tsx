// Workflow Monitor · route container tests (DEC-V61-226)
// -------------------------------------------------------
// Locks the honest wiring: a real fetched run renders WITHOUT the mock banner;
// when the backend is unavailable the page falls back to the design-preview
// fixture WITH its indelible MOCK banner (a fallback is never mistaken for real
// data).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type {
  StageKey,
  WorkflowRun,
  WorkflowStage,
} from "@/types/workflow";

const apiMock = vi.hoisted(() => ({
  listWorkflowRuns: vi.fn(),
  getWorkflowRun: vi.fn(),
}));
vi.mock("@/api/client", () => ({ api: apiMock }));

import { WorkflowMonitorRoute } from "../WorkflowMonitorRoute";

function stage(key: StageKey, title: string): WorkflowStage {
  return {
    key,
    title,
    state: "passed",
    progress: 100,
    metrics: [],
    warnings: [],
    errors: [],
    artifacts: [],
  };
}

const REAL_RUN: WorkflowRun = {
  runId: "naca0012_showcase_a04",
  caseName: "NACA0012 · α=4.0° · Re=3e+06 (external aero, RANS)",
  isMock: false,
  currentStage: "result_report",
  stages: [
    stage("geometry_intake", "Geometry Intake"),
    stage("geometry_validation", "Geometry Validation"),
    stage("mesh_generation", "Mesh Generation"),
    stage("mesh_quality_check", "Mesh Quality Check"),
    stage("solver_run", "Solver Run"),
    stage("result_report", "Result Report"),
  ],
  edges: [],
  advisorLog: [],
  timeline: [],
};

function renderRoute() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <WorkflowMonitorRoute />
    </QueryClientProvider>,
  );
}

describe("WorkflowMonitorRoute", () => {
  beforeEach(() => {
    apiMock.listWorkflowRuns.mockReset();
    apiMock.getWorkflowRun.mockReset();
  });

  it("renders a real fetched run with NO mock banner", async () => {
    apiMock.listWorkflowRuns.mockResolvedValue([
      {
        runKey: "naca0012_showcase_a04",
        runId: "naca0012_showcase_a04",
        caseName: REAL_RUN.caseName,
        isMock: false,
        currentStage: "result_report",
      },
    ]);
    apiMock.getWorkflowRun.mockResolvedValue(REAL_RUN);

    renderRoute();

    await waitFor(() =>
      expect(screen.getByText(/α=4\.0°/)).toBeInTheDocument(),
    );
    // real data → the MOCK banner must NOT appear
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("falls back to the MOCK fixture (banner shown) when the backend is unavailable", async () => {
    apiMock.listWorkflowRuns.mockRejectedValue(new Error("offline"));

    renderRoute();

    // the design-preview fixture renders, with its indelible mock banner
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/mock · design preview/i),
    );
    // getWorkflowRun is never called when there are no runs to select
    expect(apiMock.getWorkflowRun).not.toHaveBeenCalled();
  });
});
