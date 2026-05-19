/**
 * V83.3 · FailureModeShowcaseV5 contract test
 *
 * Asserts the V5.B contract from .planning/blueprints/v5/INDEX.md:
 *   - active=false renders nothing
 *   - active=true renders 3 cards each with symptom/diagnosis/fix sections
 *   - Each card has stable data-testid (failure-card-1/2/3)
 *   - V132 footer present
 *   - NO buttons inside the showcase (V130/V132 enforced structurally)
 */
import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { FailureModeShowcaseV5 } from "../components/right-panel/FailureModeShowcaseV5";

describe("FailureModeShowcaseV5 contract · V83.3 · V5.B", () => {
  it("renders nothing when active=false", () => {
    const { container } = render(<FailureModeShowcaseV5 active={false} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the showcase + 3 cards when active=true", () => {
    render(<FailureModeShowcaseV5 active />);
    expect(screen.getByTestId("failure-mode-showcase")).toBeInTheDocument();
    expect(screen.getByTestId("failure-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("failure-card-2")).toBeInTheDocument();
    expect(screen.getByTestId("failure-card-3")).toBeInTheDocument();
  });

  it("each card has symptom + diagnosis + fix sections", () => {
    render(<FailureModeShowcaseV5 active />);
    for (let i = 1; i <= 3; i++) {
      const card = screen.getByTestId(`failure-card-${i}`);
      expect(within(card).getByTestId("failure-symptom")).toBeInTheDocument();
      expect(within(card).getByTestId("failure-diagnosis")).toBeInTheDocument();
      expect(within(card).getByTestId("failure-fix")).toBeInTheDocument();
    }
  });

  it("renders V132 footer reasserting 0 fixes applied by AI", () => {
    render(<FailureModeShowcaseV5 active />);
    const footer = screen.getByTestId("failure-mode-v132-footer");
    expect(footer.textContent).toMatch(/0 fixes applied/);
    expect(footer.textContent).toMatch(/V132 locked/);
    expect(footer.textContent).toMatch(/advisory only/);
  });

  it("contains no interactive mutating affordances (V130/V132)", () => {
    render(<FailureModeShowcaseV5 active />);
    const section = screen.getByTestId("failure-mode-showcase");
    expect(within(section).queryAllByRole("button")).toHaveLength(0);
    expect(section.querySelectorAll("form").length).toBe(0);
    expect(section.querySelectorAll("input").length).toBe(0);
    expect(section.querySelectorAll("textarea").length).toBe(0);
    expect(section.querySelectorAll("a[href]").length).toBe(0);
  });

  it("card 1 covers mesh skewness with OpenFOAM citation", () => {
    render(<FailureModeShowcaseV5 active />);
    const card = screen.getByTestId("failure-card-1");
    expect(card.getAttribute("data-failure-id")).toBe("mesh-skewness");
    expect(card.textContent).toMatch(/skewness/i);
    expect(card.textContent).toMatch(/0\.94|0\.85/);
    expect(card.textContent).toMatch(/OpenFOAM/);
  });

  it("card 2 covers under-relaxation with Versteeg citation", () => {
    render(<FailureModeShowcaseV5 active />);
    const card = screen.getByTestId("failure-card-2");
    expect(card.getAttribute("data-failure-id")).toBe("under-relaxation");
    expect(card.textContent).toMatch(/relax/i);
    expect(card.textContent).toMatch(/Versteeg/);
  });

  it("card 3 covers wake resolution with Williamson citation", () => {
    render(<FailureModeShowcaseV5 active />);
    const card = screen.getByTestId("failure-card-3");
    expect(card.getAttribute("data-failure-id")).toBe("wake-resolution");
    expect(card.textContent).toMatch(/Williamson/);
    expect(card.textContent).toMatch(/Strouhal|St/);
  });
});
