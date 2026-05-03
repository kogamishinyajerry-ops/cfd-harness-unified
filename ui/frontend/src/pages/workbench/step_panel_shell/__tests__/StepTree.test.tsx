// Per-component unit tests for the StepTree (M-PANELS spec_v2 §E Step 3).
// Integration smoke is covered by StepPanelShell.test.tsx; this file
// exercises the visual states + click contract in isolation.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StepTree } from "../StepTree";
import type {
  StepDef,
  StepId,
  StepStatus,
  StepSubNode,
} from "../types";

function makeStubStep(
  id: StepId,
  shortLabel: string,
  subNodes?: readonly StepSubNode[],
): StepDef {
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
    subNodes,
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

// DEC-V61-117 · Fluent-style hierarchy refactor — sub-node rendering,
// chevron expand/collapse, auto-expand of active step.
describe("StepTree · Fluent-style hierarchy (DEC-V61-117)", () => {
  const HIER_STEPS: readonly StepDef[] = [
    makeStubStep(1, "Import"), // no sub-nodes
    makeStubStep(2, "Mesh", [
      { id: "mode", label: "Mode" },
      { id: "quality", label: "Quality" },
    ]),
    makeStubStep(3, "Setup", [
      { id: "annotations", label: "Annotations" },
      { id: "patches", label: "BC patches" },
    ]),
    makeStubStep(4, "Solve", [
      { id: "run", label: "Run" },
      { id: "residuals", label: "Residuals" },
    ]),
    makeStubStep(5, "Results", [
      { id: "fields", label: "Fields" },
      { id: "report", label: "Report" },
    ]),
  ];

  it("renders no chevron for steps without subNodes", () => {
    render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    // Step 1 has no sub-nodes → no chevron button, but a spacer for alignment.
    expect(
      screen.queryByTestId("step-tree-chevron-1"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("step-tree-chevron-spacer-1"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("step-tree-row-1")).toHaveAttribute(
      "data-step-has-subnodes",
      "false",
    );
  });

  it("auto-expands the active step's sub-nodes on first render", () => {
    render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={3}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    // Step 3 is active → its sub-nodes are visible.
    expect(screen.getByTestId("step-tree-subnodes-3")).toBeInTheDocument();
    expect(
      screen.getByTestId("step-tree-subnode-3-annotations"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("step-tree-subnode-3-patches"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("step-tree-chevron-3")).toHaveAttribute(
      "data-step-expanded",
      "true",
    );
    // Step 2 (not active) is collapsed by default.
    expect(
      screen.queryByTestId("step-tree-subnodes-2"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("step-tree-chevron-2")).toHaveAttribute(
      "data-step-expanded",
      "false",
    );
  });

  it("toggles sub-nodes visibility when chevron is clicked, without firing onStepClick", async () => {
    const user = userEvent.setup();
    const onStepClick = vi.fn();
    render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={onStepClick}
      />,
    );
    // Initially Step 4 is collapsed.
    expect(
      screen.queryByTestId("step-tree-subnodes-4"),
    ).not.toBeInTheDocument();
    // Click chevron → expand.
    await user.click(screen.getByTestId("step-tree-chevron-4"));
    expect(screen.getByTestId("step-tree-subnodes-4")).toBeInTheDocument();
    expect(screen.getByTestId("step-tree-chevron-4")).toHaveAttribute(
      "data-step-expanded",
      "true",
    );
    // Click again → collapse.
    await user.click(screen.getByTestId("step-tree-chevron-4"));
    expect(
      screen.queryByTestId("step-tree-subnodes-4"),
    ).not.toBeInTheDocument();
    // Chevron clicks must NOT trigger step navigation.
    expect(onStepClick).not.toHaveBeenCalled();
  });

  // Codex R1 P2 regression: navigating step→step used to leave each
  // visited step's auto-expansion behind, progressively filling the rail.
  // Auto entries must collapse when the active step transitions away;
  // only manually-pinned rows persist.
  it("collapses the previously-active step's auto-expansion on navigation", () => {
    const { rerender } = render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={2}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByTestId("step-tree-subnodes-2")).toBeInTheDocument();
    // Navigate 2 → 3.
    rerender(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={3}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByTestId("step-tree-subnodes-3")).toBeInTheDocument();
    expect(
      screen.queryByTestId("step-tree-subnodes-2"),
    ).not.toBeInTheDocument();
    // Navigate 3 → 4.
    rerender(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={4}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByTestId("step-tree-subnodes-4")).toBeInTheDocument();
    expect(
      screen.queryByTestId("step-tree-subnodes-2"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("step-tree-subnodes-3"),
    ).not.toBeInTheDocument();
  });

  it("preserves manual expansion when a different step becomes active", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    // User manually expands Step 5 while on Step 1.
    await user.click(screen.getByTestId("step-tree-chevron-5"));
    expect(screen.getByTestId("step-tree-subnodes-5")).toBeInTheDocument();
    // Active step flips to 3 → Step 3 auto-expands AND Step 5 stays expanded.
    rerender(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={3}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    expect(screen.getByTestId("step-tree-subnodes-3")).toBeInTheDocument();
    expect(screen.getByTestId("step-tree-subnodes-5")).toBeInTheDocument();
  });

  it("disables chevron buttons when disabled=true", async () => {
    const user = userEvent.setup();
    render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={1}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
        disabled
      />,
    );
    const chevron = screen.getByTestId("step-tree-chevron-2");
    expect(chevron).toBeDisabled();
    // Click is a no-op while disabled.
    await user.click(chevron);
    expect(
      screen.queryByTestId("step-tree-subnodes-2"),
    ).not.toBeInTheDocument();
  });

  it("renders sub-row labels with stable data-testid format", () => {
    render(
      <StepTree
        steps={HIER_STEPS}
        currentStepId={2}
        stepStates={ALL_PENDING}
        onStepClick={() => {}}
      />,
    );
    const modeRow = screen.getByTestId("step-tree-subnode-2-mode");
    expect(modeRow).toHaveAttribute("data-parent-step-id", "2");
    expect(modeRow).toHaveAttribute("data-subnode-id", "mode");
    expect(modeRow).toHaveTextContent("Mode");
  });
});
