// Smoke tests for the Steps 3-5 placeholder bodies (M-PANELS spec_v2
// §E Step 6). Each placeholder is required to: (a) clear any prior
// AI action registration so [AI 处理] renders disabled, (b) link to
// its legacy fallback route, (c) include the
// "wires up in <future-milestone>" copy.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { Step3SetupPlaceholder } from "../steps/Step3SetupPlaceholder";
import { Step4SolvePlaceholder } from "../steps/Step4SolvePlaceholder";
import { Step5ResultsPlaceholder } from "../steps/Step5ResultsPlaceholder";

function renderPlaceholder(
  Component:
    | typeof Step3SetupPlaceholder
    | typeof Step4SolvePlaceholder
    | typeof Step5ResultsPlaceholder,
  caseId = "abc",
) {
  const registerAiAction = vi.fn();
  const utils = render(
    <MemoryRouter>
      <Component
        caseId={caseId}
        onStepComplete={() => {}}
        onStepError={() => {}}
        registerAiAction={registerAiAction}
      />
    </MemoryRouter>,
  );
  return { ...utils, registerAiAction };
}

describe("Step3SetupPlaceholder", () => {
  it("clears the AI action registration on mount", () => {
    const { registerAiAction } = renderPlaceholder(Step3SetupPlaceholder);
    expect(registerAiAction).toHaveBeenCalledWith(null);
  });

  it("links to the legacy YAML editor under the case_id", () => {
    renderPlaceholder(Step3SetupPlaceholder, "imported_demo");
    expect(
      screen.getByTestId("step3-setup-yaml-editor-link"),
    ).toHaveAttribute("href", "/workbench/case/imported_demo/edit");
  });

  it("includes 'wires up in M-AI-COPILOT' copy", () => {
    renderPlaceholder(Step3SetupPlaceholder);
    expect(screen.getByTestId("step3-setup-body")).toHaveTextContent(
      /M-AI-COPILOT/,
    );
  });
});

describe("Step4SolvePlaceholder", () => {
  it("clears the AI action registration on mount", () => {
    const { registerAiAction } = renderPlaceholder(Step4SolvePlaceholder);
    expect(registerAiAction).toHaveBeenCalledWith(null);
  });

  it("links to the legacy WizardRunPage under the case_id", () => {
    renderPlaceholder(Step4SolvePlaceholder, "imported_demo");
    expect(
      screen.getByTestId("step4-solve-run-link"),
    ).toHaveAttribute("href", "/workbench/run/imported_demo");
  });

  it("includes 'wires up in M7-redefined' copy", () => {
    renderPlaceholder(Step4SolvePlaceholder);
    expect(screen.getByTestId("step4-solve-body")).toHaveTextContent(
      /M7-redefined/,
    );
  });
});

describe("Step5ResultsPlaceholder", () => {
  it("clears the AI action registration on mount", () => {
    const { registerAiAction } = renderPlaceholder(Step5ResultsPlaceholder);
    expect(registerAiAction).toHaveBeenCalledWith(null);
  });

  it("links to the legacy run-history table under the case_id", () => {
    renderPlaceholder(Step5ResultsPlaceholder, "imported_demo");
    expect(
      screen.getByTestId("step5-results-runs-link"),
    ).toHaveAttribute("href", "/workbench/case/imported_demo/runs");
  });

  it("includes 'wires up in M-VIZ.results' copy", () => {
    renderPlaceholder(Step5ResultsPlaceholder);
    expect(screen.getByTestId("step5-results-body")).toHaveTextContent(
      /M-VIZ.results/,
    );
  });
});
