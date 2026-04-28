// Per-component unit tests for StatusStrip (M-PANELS spec_v2 §E Step 3).

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatusStrip } from "../StatusStrip";

describe("StatusStrip · component unit tests", () => {
  it("renders the strip with an em-dash placeholder when no lastAction is provided", () => {
    render(<StatusStrip />);
    expect(screen.getByTestId("status-strip-last-action")).toHaveTextContent(
      "—",
    );
  });

  it("displays the lastAction string when provided", () => {
    render(<StatusStrip lastAction="mesh generated · 1.2M cells" />);
    expect(screen.getByTestId("status-strip-last-action")).toHaveTextContent(
      "mesh generated · 1.2M cells",
    );
  });

  it("shows the validation block only when validation is non-null", () => {
    const { unmount } = render(<StatusStrip />);
    expect(screen.queryByTestId("status-strip-validation")).toBeNull();
    unmount();

    render(<StatusStrip validation="ready" />);
    expect(screen.getByTestId("status-strip-validation")).toHaveTextContent(
      "ready",
    );
  });

  it("hides validation when explicitly null but still renders the strip", () => {
    render(<StatusStrip lastAction="ok" validation={null} />);
    expect(screen.getByTestId("status-strip")).toBeInTheDocument();
    expect(screen.queryByTestId("status-strip-validation")).toBeNull();
  });
});
