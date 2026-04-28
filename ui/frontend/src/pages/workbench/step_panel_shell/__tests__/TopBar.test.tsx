// Per-component unit tests for TopBar (M-PANELS spec_v2 §E Step 3).

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { TopBar } from "../TopBar";

describe("TopBar · component unit tests", () => {
  it("renders the case_id in the canonical slot", () => {
    render(<TopBar caseId="imported_2026-04-28T00-00-00Z_demo" />);
    expect(screen.getByTestId("top-bar-case-id")).toHaveTextContent(
      "imported_2026-04-28T00-00-00Z_demo",
    );
  });

  it("defaults the save indicator to 'idle' when omitted", () => {
    render(<TopBar caseId="abc" />);
    const indicator = screen.getByTestId("save-indicator");
    expect(indicator).toHaveAttribute("data-state", "idle");
    expect(indicator).toHaveTextContent("ready");
  });

  it("maps each saveIndicator value to its label + data-state", () => {
    const cases = [
      { state: "idle" as const, label: "ready" },
      { state: "saving" as const, label: "saving…" },
      { state: "saved" as const, label: "saved" },
      { state: "error" as const, label: "save failed" },
    ];
    for (const { state, label } of cases) {
      const { unmount } = render(
        <TopBar caseId="abc" saveIndicator={state} />,
      );
      const indicator = screen.getByTestId("save-indicator");
      expect(indicator).toHaveAttribute("data-state", state);
      expect(indicator).toHaveTextContent(label);
      unmount();
    }
  });
});
