/**
 * V80.3 · AdvisorCommentaryV4 contract test
 *
 * Asserts the V4.B contract from .planning/blueprints/v4/INDEX.md:
 *   - 3 commentary kinds always render (mesh-quality / convergence /
 *     result-interpretation)
 *   - Each card has data-testid="advisor-commentary-<kind>"
 *   - The V132 footer is present and reads "0 actions taken"
 *   - No <button>, <form>, <input>, or onClick handler exists inside the
 *     commentary section (V130/V132 enforced structurally)
 *   - Static lookup behavior: known case (lid_driven_cavity) gets its
 *     case-specific text; unknown case falls back to defaults
 */
import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { AdvisorCommentaryV4 } from "../components/right-panel/AdvisorCommentaryV4";

describe("AdvisorCommentaryV4 contract · V80.3", () => {
  it("renders the 3 curated commentary cards with stable data-testid", () => {
    render(<AdvisorCommentaryV4 caseId="lid_driven_cavity" stepId={2} />);

    expect(screen.getByTestId("advisor-commentary-v4")).toBeInTheDocument();
    expect(
      screen.getByTestId("advisor-commentary-mesh-quality"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("advisor-commentary-convergence"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("advisor-commentary-result-interpretation"),
    ).toBeInTheDocument();
  });

  it("renders the V132 footer reasserting 0 actions taken", () => {
    render(<AdvisorCommentaryV4 caseId="lid_driven_cavity" stepId={4} />);
    const footer = screen.getByTestId("advisor-commentary-v132-footer");
    expect(footer.textContent).toMatch(/0 actions taken/);
    expect(footer.textContent).toMatch(/V132 locked/);
    expect(footer.textContent).toMatch(/advisory only/);
  });

  it("contains no interactive mutating affordance inside the commentary surface", () => {
    render(<AdvisorCommentaryV4 caseId="lid_driven_cavity" stepId={4} />);
    const section = screen.getByTestId("advisor-commentary-v4");

    expect(within(section).queryAllByRole("button")).toHaveLength(0);
    expect(section.querySelectorAll("form").length).toBe(0);
    expect(section.querySelectorAll("input").length).toBe(0);
    expect(section.querySelectorAll("textarea").length).toBe(0);
    expect(section.querySelectorAll("select").length).toBe(0);
    expect(section.querySelectorAll("a[href]").length).toBe(0);
  });

  it("surfaces case-specific commentary for lid_driven_cavity at step 4 (solver)", () => {
    render(<AdvisorCommentaryV4 caseId="lid_driven_cavity" stepId={4} />);
    const convergence = screen.getByTestId("advisor-commentary-convergence");
    expect(convergence.textContent).toMatch(/Re=100/);
    expect(convergence.textContent).toMatch(/simpleFoam/);
  });

  it("surfaces gold-reference citation for lid_driven_cavity at step 5", () => {
    render(<AdvisorCommentaryV4 caseId="lid_driven_cavity" stepId={5} />);
    const result = screen.getByTestId(
      "advisor-commentary-result-interpretation",
    );
    expect(result.textContent).toMatch(/Ghia/);
  });

  it("falls back to default commentary for unknown case_id", () => {
    render(<AdvisorCommentaryV4 caseId="not_a_real_case" stepId={2} />);
    const mesh = screen.getByTestId("advisor-commentary-mesh-quality");
    expect(mesh.textContent).toMatch(/skewness/i);
  });

  it("handles null caseId by serving the default set", () => {
    render(<AdvisorCommentaryV4 caseId={null} stepId={1} />);
    expect(screen.getByTestId("advisor-commentary-v4")).toHaveAttribute(
      "data-case-id",
      "__none__",
    );
    expect(
      screen.getByTestId("advisor-commentary-mesh-quality"),
    ).toBeInTheDocument();
  });

  it("annotates the section with the current step for testability", () => {
    render(<AdvisorCommentaryV4 caseId="lid_driven_cavity" stepId={3} />);
    expect(screen.getByTestId("advisor-commentary-v4")).toHaveAttribute(
      "data-step-id",
      "3",
    );
  });

  // V81.1 · commentary breadth extension · canonical cases beyond lid_driven_cavity
  it("surfaces NACA 0012 airfoil curated commentary at step 2 (mesh)", () => {
    render(<AdvisorCommentaryV4 caseId="naca0012_airfoil" stepId={2} />);
    const mesh = screen.getByTestId("advisor-commentary-mesh-quality");
    expect(mesh.textContent).toMatch(/C-mesh|O-mesh/);
    expect(mesh.textContent).toMatch(/y\+/);
  });

  it("surfaces NACA 0012 airfoil curated commentary at step 5 (Cl validation)", () => {
    render(<AdvisorCommentaryV4 caseId="naca0012_airfoil" stepId={5} />);
    const result = screen.getByTestId(
      "advisor-commentary-result-interpretation",
    );
    expect(result.textContent).toMatch(/Cl|AGARD/);
  });

  it("surfaces backward-facing step reattachment commentary at step 5", () => {
    render(<AdvisorCommentaryV4 caseId="backward_facing_step" stepId={5} />);
    const result = screen.getByTestId(
      "advisor-commentary-result-interpretation",
    );
    expect(result.textContent).toMatch(/reattachment|Driver/);
    expect(result.textContent).toMatch(/6\.1/);
  });

  it("surfaces backward-facing step mesh discipline at step 2", () => {
    render(<AdvisorCommentaryV4 caseId="backward_facing_step" stepId={2} />);
    const mesh = screen.getByTestId("advisor-commentary-mesh-quality");
    expect(mesh.textContent).toMatch(/step height|cells across h/);
  });

  // V82.1 · commentary breadth completion · all 10 Gold-Standard cases covered
  it.each([
    {
      caseId: "circular_cylinder_wake",
      step: 5 as const,
      kind: "result-interpretation",
      match: /Strouhal|Williamson/,
    },
    {
      caseId: "turbulent_flat_plate",
      step: 5 as const,
      kind: "result-interpretation",
      match: /log-law|Schlichting|y\+/,
    },
    {
      caseId: "plane_channel_flow",
      step: 2 as const,
      kind: "mesh-quality",
      match: /Moser|Re_τ|Δx\+/,
    },
    {
      caseId: "impinging_jet",
      step: 5 as const,
      kind: "result-interpretation",
      match: /Cooper|Nu_0/,
    },
    {
      caseId: "rayleigh_benard_convection",
      step: 5 as const,
      kind: "result-interpretation",
      match: /Kerr|Nu.*Ra|2\/7/,
    },
    {
      caseId: "differential_heated_cavity",
      step: 5 as const,
      kind: "result-interpretation",
      match: /de Vahl Davis|Nu_hot/,
    },
    {
      caseId: "duct_flow",
      step: 5 as const,
      kind: "result-interpretation",
      match: /Gavrilakis|secondary|vortices/,
    },
  ])(
    "surfaces curated commentary for $caseId at step $step / kind $kind",
    ({ caseId, step, kind, match }) => {
      render(<AdvisorCommentaryV4 caseId={caseId} stepId={step} />);
      const card = screen.getByTestId(`advisor-commentary-${kind}`);
      expect(card.textContent).toMatch(match);
    },
  );
});
