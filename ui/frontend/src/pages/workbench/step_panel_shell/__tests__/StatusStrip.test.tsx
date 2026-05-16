// Per-component unit tests for StatusStrip · 4-field live indicators
// (V67-C.2 · Blueprint v3 §4 alignment).

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatusStrip } from "../StatusStrip";

describe("StatusStrip · 4-field live indicators (V67-C.2)", () => {
  it("renders em-dash placeholder when no lastAction provided (legacy)", () => {
    render(<StatusStrip />);
    expect(screen.getByTestId("status-strip-last-action")).toHaveTextContent(
      "—",
    );
  });

  it("displays lastAction string when provided (legacy)", () => {
    render(<StatusStrip lastAction="mesh generated · 1.2M cells" />);
    expect(screen.getByTestId("status-strip-last-action")).toHaveTextContent(
      "mesh generated · 1.2M cells",
    );
  });

  it("shows validation block only when validation is non-null (legacy)", () => {
    const { unmount } = render(<StatusStrip />);
    expect(screen.queryByTestId("status-strip-validation")).toBeNull();
    unmount();

    render(<StatusStrip validation="ready" />);
    expect(screen.getByTestId("status-strip-validation")).toHaveTextContent(
      "ready",
    );
  });

  it("hides validation when explicitly null but renders the strip (legacy)", () => {
    render(<StatusStrip lastAction="ok" validation={null} />);
    expect(screen.getByTestId("status-strip")).toBeInTheDocument();
    expect(screen.queryByTestId("status-strip-validation")).toBeNull();
  });

  it("renders progress indicator when currentStep + stepStatus provided", () => {
    render(<StatusStrip currentStep={2} stepStatus="running" />);
    const progress = screen.getByTestId("status-strip-progress");
    expect(progress).toHaveTextContent("step 2/5");
    expect(progress).toHaveTextContent("●"); // running icon
    expect(progress).toHaveAttribute("data-state", "running");
  });

  it("renders correct icons for each stepStatus", () => {
    const cases: Array<["idle" | "running" | "done" | "error", string]> = [
      ["idle", "○"],
      ["running", "●"],
      ["done", "✓"],
      ["error", "✗"],
    ];
    for (const [status, icon] of cases) {
      const { unmount } = render(
        <StatusStrip currentStep={1} stepStatus={status} />,
      );
      const progress = screen.getByTestId("status-strip-progress");
      expect(progress).toHaveAttribute("data-state", status);
      expect(progress).toHaveTextContent(icon);
      unmount();
    }
  });

  it("omits progress field when currentStep is null", () => {
    render(<StatusStrip lastAction="ok" />);
    expect(screen.queryByTestId("status-strip-progress")).toBeNull();
  });

  it("respects custom totalSteps", () => {
    render(<StatusStrip currentStep={3} totalSteps={8} stepStatus="idle" />);
    expect(screen.getByTestId("status-strip-progress")).toHaveTextContent(
      "step 3/8",
    );
  });

  it("renders trustState indicator for each variant", () => {
    const cases: Array<
      ["PASS" | "PASS_WITH_DISCLAIMER" | "FAIL" | "PENDING", string]
    > = [
      ["PASS", "trust ✓"],
      ["PASS_WITH_DISCLAIMER", "trust ✓*"],
      ["FAIL", "trust ✗"],
      ["PENDING", "trust —"],
    ];
    for (const [v, label] of cases) {
      const { unmount } = render(<StatusStrip trustState={v} />);
      const el = screen.getByTestId("status-strip-trust-state");
      expect(el).toHaveAttribute("data-state", v);
      expect(el).toHaveTextContent(label);
      unmount();
    }
  });

  it("omits trustState field when null", () => {
    render(<StatusStrip lastAction="ok" />);
    expect(screen.queryByTestId("status-strip-trust-state")).toBeNull();
  });

  it("renders all 4 fields when fully populated", () => {
    render(
      <StatusStrip
        lastAction="solver running · iter 320"
        validation="convergence stable"
        currentStep={4}
        stepStatus="running"
        trustState="PASS"
      />,
    );
    expect(screen.getByTestId("status-strip-last-action")).toHaveTextContent(
      "solver running · iter 320",
    );
    expect(screen.getByTestId("status-strip-validation")).toHaveTextContent(
      "convergence stable",
    );
    expect(screen.getByTestId("status-strip-progress")).toHaveTextContent(
      "step 4/5",
    );
    expect(screen.getByTestId("status-strip-trust-state")).toHaveTextContent(
      "trust ✓",
    );
  });
});
