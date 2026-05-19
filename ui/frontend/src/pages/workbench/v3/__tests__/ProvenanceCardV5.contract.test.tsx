/**
 * V83.5 · ProvenanceCardV5 contract test · V5.D
 *
 * Asserts the V5.D contract from .planning/blueprints/v5/INDEX.md:
 *   - justFinished=false renders nothing
 *   - justFinished=true renders provenance-card with 4 stat lines
 *   - Sandbox CTA sets ?demo=2
 *   - Close button removes card from DOM
 *   - NO form/input/fetch (V130/V132)
 *   - Stats: cases=1 when caseId, steps=clamp(maxStepWalked, 1-5), commentary≥3, citations≥12
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";

import { ProvenanceCardV5 } from "../components/ProvenanceCardV5";

function Harness({
  justFinished,
  caseId = "lid_driven_cavity",
  maxStepWalked = 5,
  initial = "/?",
}: {
  justFinished: boolean;
  caseId?: string | null;
  maxStepWalked?: number;
  initial?: string;
}) {
  function ParamProbe() {
    const [params] = useSearchParams();
    return (
      <span data-testid="param-probe">{params.toString()}</span>
    );
  }
  return (
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route
          path="/"
          element={
            <>
              <ProvenanceCardV5
                justFinished={justFinished}
                caseId={caseId}
                maxStepWalked={maxStepWalked}
              />
              <ParamProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProvenanceCardV5 contract · V83.5 · V5.D", () => {
  it("renders nothing when justFinished=false", () => {
    render(<Harness justFinished={false} />);
    expect(screen.queryByTestId("provenance-card")).not.toBeInTheDocument();
  });

  it("renders 4 stat lines when justFinished=true", () => {
    render(<Harness justFinished />);
    expect(screen.getByTestId("provenance-card")).toBeInTheDocument();
    expect(screen.getByTestId("provenance-stats-cases")).toBeInTheDocument();
    expect(screen.getByTestId("provenance-stats-steps")).toBeInTheDocument();
    expect(
      screen.getByTestId("provenance-stats-commentary"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("provenance-stats-citations"),
    ).toBeInTheDocument();
  });

  it("Cases count = 1 when caseId is set", () => {
    render(<Harness justFinished caseId="lid_driven_cavity" />);
    expect(screen.getByTestId("provenance-stats-cases").textContent).toBe("1");
  });

  it("Cases count = 0 when caseId is null", () => {
    render(<Harness justFinished caseId={null} />);
    expect(screen.getByTestId("provenance-stats-cases").textContent).toBe("0");
  });

  it("Steps count clamps to 1..5 range", () => {
    const { rerender } = render(<Harness justFinished maxStepWalked={6} />);
    expect(screen.getByTestId("provenance-stats-steps").textContent).toBe("5");
    rerender(<Harness justFinished maxStepWalked={0} />);
    expect(screen.getByTestId("provenance-stats-steps").textContent).toBe("1");
  });

  it("Commentary count is at least 3", () => {
    render(<Harness justFinished />);
    expect(
      screen.getByTestId("provenance-stats-commentary").textContent,
    ).toMatch(/≥3/);
  });

  it("Citation count is at least 12", () => {
    render(<Harness justFinished />);
    expect(
      screen.getByTestId("provenance-stats-citations").textContent,
    ).toMatch(/≥12/);
  });

  it("close button removes the card from DOM", async () => {
    const user = userEvent.setup();
    render(<Harness justFinished />);
    await user.click(screen.getByTestId("provenance-close"));
    expect(screen.queryByTestId("provenance-card")).not.toBeInTheDocument();
  });

  it("Sandbox CTA sets ?demo=2 and clears tour/cinema params", async () => {
    const user = userEvent.setup();
    render(<Harness justFinished initial="/?tour=6&cinema=1" />);
    await user.click(screen.getByTestId("provenance-sandbox-cta"));
    const params = screen.getByTestId("param-probe").textContent ?? "";
    expect(params).toMatch(/demo=2/);
    expect(params).not.toMatch(/tour=/);
    expect(params).not.toMatch(/cinema/);
    // Card also closes after CTA
    expect(screen.queryByTestId("provenance-card")).not.toBeInTheDocument();
  });

  it("contains no form/input · only 2 buttons (close + sandbox CTA) · V132", () => {
    render(<Harness justFinished />);
    const card = screen.getByTestId("provenance-card");
    expect(card.querySelectorAll("form").length).toBe(0);
    expect(card.querySelectorAll("input").length).toBe(0);
    expect(card.querySelectorAll("textarea").length).toBe(0);
    expect(card.querySelectorAll("a[href]").length).toBe(0);
    const buttons = card.querySelectorAll("button");
    expect(buttons.length).toBe(2);
  });

  it("annotates 'no telemetry sent' to make V130 invariant visible", () => {
    render(<Harness justFinished />);
    expect(screen.getByTestId("provenance-card").textContent).toMatch(
      /no telemetry sent/,
    );
  });
});
