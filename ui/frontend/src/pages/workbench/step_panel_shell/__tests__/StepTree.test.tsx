// Per-component unit tests for the StepTree (M-PANELS spec_v2 §E Step 3).
// Integration smoke is covered by StepPanelShell.test.tsx; this file
// exercises the visual states + click contract in isolation.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StepTree } from "../StepTree";
import type { StepDef, StepId, StepStatus } from "../types";

function makeStubStep(id: StepId, shortLabel: string): StepDef {
  return {
    id,
    shortLabel,
    longLabel: `${id} · ${shortLabel}`,
    viewportConfig: {
      format: "none",
      glbUrl: () => null,
      stlUrl: () => null,
    },
    taskPanelComponent: () => null,
    aiActionWiredInTierA: false,
  };
}

const STUB_STEPS: readonly StepDef[] = [
  makeStubStep(1, "Import"),
  makeStubStep(2, "Mesh"),
  makeStubStep(3, "Setup"),
  makeStubStep(4, "Solve"),
  makeStubStep(5, "Results"),
];

const ALL_PENDING: Record<StepId, StepStatus> = {
  1: "pending",
  2: "pending",
  3: "pending",
  4: "pending",
  5: "pending",
};

describe("StepTree · component unit tests", () => {
  it("renders one row per step with the short label", () => {
    render(
      <StepTree
        steps={STUB_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByText("Import")).toBeInTheDocument();
    expect(screen.getByText("Mesh")).toBeInTheDocument();
    expect(screen.getByText("Setup")).toBeInTheDocument();
    expect(screen.getByText("Solve")).toBeInTheDocument();
    expect(screen.getByText("Results")).toBeInTheDocument();
  });

  it("flags the current step as data-step-status='active' regardless of stepStates", () => {
    render(
      <StepTree
        steps={STUB_STEPS}
        currentStepId={3}
        stepStates={{ ...ALL_PENDING, 3: "completed" }}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByTestId("step-tree-row-3")).toHaveAttribute(
      "data-step-status",
      "active",
    );
  });

  it("propagates non-active step statuses from stepStates", () => {
    render(
      <StepTree
        steps={STUB_STEPS}
        currentStepId={1}
        stepStates={{ ...ALL_PENDING, 2: "completed", 4: "error" }}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByTestId("step-tree-row-2")).toHaveAttribute(
      "data-step-status",
      "completed",
    );
    expect(screen.getByTestId("step-tree-row-4")).toHaveAttribute(
      "data-step-status",
      "error",
    );
    expect(screen.getByTestId("step-tree-row-3")).toHaveAttribute(
      "data-step-status",
      "pending",
    );
  });

  it("dispatches onStepClick(id) when a row is clicked", async () => {
    const user = userEvent.setup();
    const onStepClick = vi.fn();
    render(
      <StepTree
        steps={STUB_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={onStepClick}
      />,
    );
    await user.click(screen.getByTestId("step-tree-row-4"));
    expect(onStepClick).toHaveBeenCalledTimes(1);
    expect(onStepClick).toHaveBeenCalledWith(4);
  });

  it("uses a navigation landmark with an aria-label", () => {
    render(
      <StepTree
        steps={STUB_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    const nav = screen.getByRole("navigation", {
      name: /workbench step tree/i,
    });
    expect(nav).toBeInTheDocument();
  });

  // Round-1 Codex Finding 1: when an AI action is in flight, the shell
  // passes disabled=true so the user can't navigate away from a
  // non-abortable mesh run and discard its result.
  it("disables every row and exposes data-disabled when disabled=true", async () => {
    const user = userEvent.setup();
    const onStepClick = vi.fn();
    render(
      <StepTree
        steps={STUB_STEPS}
        currentStepId={2}
        stepStates={ALL_PENDING}
        onStepClick={onStepClick}
        disabled
      />,
    );
    expect(screen.getByTestId("step-tree")).toHaveAttribute(
      "data-disabled",
      "true",
    );
    for (const id of [1, 2, 3, 4, 5] as const) {
      expect(screen.getByTestId(`step-tree-row-${id}`)).toBeDisabled();
    }
    await user.click(screen.getByTestId("step-tree-row-3"));
    expect(onStepClick).not.toHaveBeenCalled();
  });
});
