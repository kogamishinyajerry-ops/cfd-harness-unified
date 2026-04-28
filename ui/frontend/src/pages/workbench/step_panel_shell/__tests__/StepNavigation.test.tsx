// Per-component unit tests for StepNavigation (M-PANELS spec_v2 §E Step 3).

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StepNavigation } from "../StepNavigation";

const BASE = {
  onPrevious: () => {},
  onNext: () => {},
  canAdvance: true,
  canRetreat: true,
  aiInFlight: false,
};

describe("StepNavigation · component unit tests", () => {
  it("renders the three buttons with their canonical labels", () => {
    render(<StepNavigation {...BASE} onAiProcess={async () => {}} />);
    expect(screen.getByTestId("ai-process-button")).toHaveTextContent(
      "AI 处理",
    );
    expect(screen.getByTestId("previous-button")).toHaveTextContent(
      "上一步",
    );
    expect(screen.getByTestId("next-button")).toHaveTextContent("下一步");
  });

  it("disables [AI 处理] and surfaces tooltip when onAiProcess is null", () => {
    render(
      <StepNavigation
        {...BASE}
        onAiProcess={null}
        aiActionDeferredTooltip="Wires up in M-AI-COPILOT"
      />,
    );
    const ai = screen.getByTestId("ai-process-button");
    expect(ai).toBeDisabled();
    expect(ai).toHaveAttribute("title", "Wires up in M-AI-COPILOT");
  });

  it("falls back to a generic tooltip when no aiActionDeferredTooltip is provided", () => {
    render(<StepNavigation {...BASE} onAiProcess={null} />);
    expect(screen.getByTestId("ai-process-button")).toHaveAttribute(
      "title",
      "AI 处理 wires up in a later milestone",
    );
  });

  it("invokes onAiProcess when [AI 处理] is clicked while wired and not in-flight", async () => {
    const user = userEvent.setup();
    const onAiProcess = vi.fn().mockResolvedValue(undefined);
    render(<StepNavigation {...BASE} onAiProcess={onAiProcess} />);
    await user.click(screen.getByTestId("ai-process-button"));
    expect(onAiProcess).toHaveBeenCalledTimes(1);
  });

  it("disables [AI 处理] + nav buttons while aiInFlight=true and shows the spinner label", () => {
    render(
      <StepNavigation
        {...BASE}
        aiInFlight
        onAiProcess={async () => {}}
      />,
    );
    expect(screen.getByTestId("ai-process-button")).toBeDisabled();
    expect(screen.getByTestId("ai-process-button")).toHaveTextContent(
      "AI 处理…",
    );
    expect(screen.getByTestId("previous-button")).toBeDisabled();
    expect(screen.getByTestId("next-button")).toBeDisabled();
  });

  it("respects canAdvance / canRetreat bounds", () => {
    const { unmount } = render(
      <StepNavigation
        {...BASE}
        onAiProcess={null}
        canAdvance={false}
        canRetreat
      />,
    );
    expect(screen.getByTestId("next-button")).toBeDisabled();
    expect(screen.getByTestId("previous-button")).not.toBeDisabled();
    unmount();

    render(
      <StepNavigation
        {...BASE}
        onAiProcess={null}
        canAdvance
        canRetreat={false}
      />,
    );
    expect(screen.getByTestId("previous-button")).toBeDisabled();
    expect(screen.getByTestId("next-button")).not.toBeDisabled();
  });

  it("dispatches onPrevious / onNext on click", async () => {
    const user = userEvent.setup();
    const onPrevious = vi.fn();
    const onNext = vi.fn();
    render(
      <StepNavigation
        {...BASE}
        onAiProcess={null}
        onPrevious={onPrevious}
        onNext={onNext}
      />,
    );
    await user.click(screen.getByTestId("previous-button"));
    await user.click(screen.getByTestId("next-button"));
    expect(onPrevious).toHaveBeenCalledTimes(1);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it("renders the AI error banner when aiErrorMessage is set", () => {
    render(
      <StepNavigation
        {...BASE}
        onAiProcess={async () => {}}
        aiErrorMessage="mesh failed: gmsh exited 1"
      />,
    );
    const banner = screen.getByTestId("ai-error");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/mesh failed/);
  });

  it("does NOT render the AI error banner when aiErrorMessage is undefined", () => {
    render(<StepNavigation {...BASE} onAiProcess={async () => {}} />);
    expect(screen.queryByTestId("ai-error")).toBeNull();
  });

  it("does NOT call onAiProcess when the button is disabled and clicked", async () => {
    const user = userEvent.setup();
    const onAiProcess = vi.fn();
    render(
      <StepNavigation
        {...BASE}
        aiInFlight
        onAiProcess={onAiProcess}
      />,
    );
    // userEvent skips disabled buttons silently — assert no call landed.
    await user.click(screen.getByTestId("ai-process-button"));
    expect(onAiProcess).not.toHaveBeenCalled();
  });
});
