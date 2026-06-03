// Workflow Monitor · page tests (DEC-V61-226)
// --------------------------------------------
// Locks the load-bearing behaviours: the HONESTY invariant (mock banner is
// shown whenever isMock), the six stages render, the BLOCKED report stage is
// surfaced (never hidden), default selection follows currentStage, and stage
// selection is interactive.

import { describe, expect, it } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";

import { WorkflowMonitorPage } from "../WorkflowMonitorPage";
import { WORKFLOW_MONITOR_MOCK } from "@/data/workflowMonitorMock";
import type { WorkflowRun } from "@/types/workflow";

describe("WorkflowMonitorPage", () => {
  it("stamps an indelible MOCK banner when the run is a design preview", () => {
    render(<WorkflowMonitorPage run={WORKFLOW_MONITOR_MOCK} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/mock · design preview/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/非真实算例/);
  });

  it("does NOT show the mock banner for a real (isMock=false) run", () => {
    const realRun: WorkflowRun = { ...WORKFLOW_MONITOR_MOCK, isMock: false };
    render(<WorkflowMonitorPage run={realRun} />);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("renders all six stages in the pipeline graph", () => {
    render(<WorkflowMonitorPage run={WORKFLOW_MONITOR_MOCK} />);
    const nav = screen.getByRole("navigation", { name: /workflow stages/i });
    for (const stage of WORKFLOW_MONITOR_MOCK.stages) {
      expect(within(nav).getByText(stage.title)).toBeInTheDocument();
    }
  });

  it("defaults the preview to the current stage (the running solver)", () => {
    render(<WorkflowMonitorPage run={WORKFLOW_MONITOR_MOCK} />);
    // center preview heading = the current stage's title
    expect(
      screen.getByRole("heading", { level: 2, name: /solver run/i })
    ).toBeInTheDocument();
    // running progress bar present
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "62");
  });

  it("surfaces the BLOCKED report stage honestly (not hidden)", () => {
    render(<WorkflowMonitorPage run={WORKFLOW_MONITOR_MOCK} />);
    const nav = screen.getByRole("navigation", { name: /workflow stages/i });
    // select the report stage
    fireEvent.click(within(nav).getByText(/result report/i));
    expect(
      screen.getByRole("heading", { level: 2, name: /result report/i })
    ).toBeInTheDocument();
    // its BLOCKED state + evidence-gate next-action are shown
    expect(screen.getAllByText(/blocked/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/no polar is published on an unconverged solve/i)).toBeInTheDocument();
  });

  it("lets the operator select a different stage", () => {
    render(<WorkflowMonitorPage run={WORKFLOW_MONITOR_MOCK} />);
    const nav = screen.getByRole("navigation", { name: /workflow stages/i });
    fireEvent.click(within(nav).getByText(/mesh quality check/i));
    expect(
      screen.getByRole("heading", { level: 2, name: /mesh quality check/i })
    ).toBeInTheDocument();
    // the leading-edge skewness HAZARD warning is shown
    expect(screen.getByText(/skewness 0\.91 at the leading edge/i)).toBeInTheDocument();
  });
});
