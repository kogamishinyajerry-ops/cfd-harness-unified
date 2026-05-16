/**
 * V68-A.4 · ViewportModeDispatcher unit tests · 6-mode coverage + step
 * defaulting + user override semantics.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  ViewportModeDispatcher,
  VIEWPORT_MODES,
  defaultModeForStep,
} from "../ViewportMode";

describe("defaultModeForStep (V68-A.4)", () => {
  it("maps Step 1 → geometry", () => {
    expect(defaultModeForStep(1)).toBe("geometry");
    expect(defaultModeForStep("1")).toBe("geometry");
  });
  it("maps Step 2 → mesh-wireframe", () => {
    expect(defaultModeForStep(2)).toBe("mesh-wireframe");
  });
  it("maps Step 3 → bc-faces", () => {
    expect(defaultModeForStep(3)).toBe("bc-faces");
  });
  it("maps Step 4 → residuals (mid-solve default)", () => {
    expect(defaultModeForStep(4)).toBe("residuals");
  });
  it("maps Step 5 → report-grid", () => {
    expect(defaultModeForStep(5)).toBe("report-grid");
  });
  it("falls back to geometry for unknown / null stepId", () => {
    expect(defaultModeForStep(null)).toBe("geometry");
    expect(defaultModeForStep(undefined)).toBe("geometry");
    expect(defaultModeForStep(99)).toBe("geometry");
  });
});

describe("VIEWPORT_MODES (V68-A.4)", () => {
  it("exposes all 6 canonical modes per Blueprint v3 §4", () => {
    expect(VIEWPORT_MODES).toHaveLength(6);
    expect(VIEWPORT_MODES).toContain("geometry");
    expect(VIEWPORT_MODES).toContain("mesh-wireframe");
    expect(VIEWPORT_MODES).toContain("bc-faces");
    expect(VIEWPORT_MODES).toContain("field-slice");
    expect(VIEWPORT_MODES).toContain("residuals");
    expect(VIEWPORT_MODES).toContain("report-grid");
  });
});

describe("ViewportModeDispatcher (V68-A.4)", () => {
  it("defaults viewport mode from stepId", () => {
    render(<ViewportModeDispatcher stepId={2} />);
    const wrap = screen.getByTestId("viewport-mode-dispatcher");
    expect(wrap).toHaveAttribute("data-viewport-mode", "mesh-wireframe");
    expect(wrap).toHaveAttribute("data-viewport-step", "2");
  });

  it("renders all 6 mode buttons in the toolbar", () => {
    render(<ViewportModeDispatcher stepId={1} />);
    for (const m of VIEWPORT_MODES) {
      expect(screen.getByTestId(`viewport-mode-button-${m}`)).toBeInTheDocument();
    }
  });

  it("user click switches mode and toggles data-active flag", () => {
    render(<ViewportModeDispatcher stepId={1} />);
    const wrap = screen.getByTestId("viewport-mode-dispatcher");
    expect(wrap).toHaveAttribute("data-viewport-mode", "geometry");
    fireEvent.click(screen.getByTestId("viewport-mode-button-field-slice"));
    expect(wrap).toHaveAttribute("data-viewport-mode", "field-slice");
    expect(screen.getByTestId("viewport-mode-button-field-slice")).toHaveAttribute(
      "data-active",
      "true",
    );
  });

  it("clicking the active mode resets to step-default", () => {
    render(<ViewportModeDispatcher stepId={3} />);
    const wrap = screen.getByTestId("viewport-mode-dispatcher");
    expect(wrap).toHaveAttribute("data-viewport-mode", "bc-faces");
    fireEvent.click(screen.getByTestId("viewport-mode-button-residuals"));
    expect(wrap).toHaveAttribute("data-viewport-mode", "residuals");
    fireEvent.click(screen.getByTestId("viewport-mode-button-residuals"));
    expect(wrap).toHaveAttribute("data-viewport-mode", "bc-faces");
  });

  it("overrideMode prop wins over user state and step default", () => {
    render(
      <ViewportModeDispatcher stepId={1} overrideMode="report-grid" />,
    );
    const wrap = screen.getByTestId("viewport-mode-dispatcher");
    expect(wrap).toHaveAttribute("data-viewport-mode", "report-grid");
  });
});
