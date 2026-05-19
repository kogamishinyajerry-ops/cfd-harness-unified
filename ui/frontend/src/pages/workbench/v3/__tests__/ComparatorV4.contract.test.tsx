/**
 * V80.4 · ComparatorV4 contract test
 *
 * Asserts the V4.C contract from .planning/blueprints/v4/INDEX.md:
 *   - data-testid pattern: comparator-gold-actual-{case_id}-{quantity}
 *   - SVG with ≥17 reference circles (Ghia 1982 native sample count)
 *   - 1 computed polyline
 *   - ±5% tolerance band path present
 *   - max-delta annotation visible (worst-point highlight)
 *   - No mutating affordances (V130/V132)
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ComparatorV4 } from "../components/canvas/ComparatorV4";
import {
  GHIA_LID_CAVITY_U_CENTERLINE,
  computeLidCavityComputed,
  worstDelta,
} from "@/data/gold_references";

describe("ComparatorV4 contract · V80.4 · V4.C", () => {
  it("renders the V4.C testid for lid_driven_cavity u-centerline", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" quantity="u_centerline" />);
    expect(
      screen.getByTestId(
        "comparator-gold-actual-lid_driven_cavity-u_centerline",
      ),
    ).toBeInTheDocument();
  });

  it("renders exactly 17 reference circles + 1 computed polyline + 1 worst-point dot", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" />);
    const refs = screen.getAllByTestId("comparator-reference-point");
    expect(refs).toHaveLength(17);

    const svg = screen
      .getByTestId("comparator-gold-actual-lid_driven_cavity-u_centerline")
      .querySelector("svg");
    expect(svg).not.toBeNull();
    const polylines = svg!.querySelectorAll("polyline");
    expect(polylines).toHaveLength(1);
    expect(screen.getByTestId("comparator-worst-point")).toBeInTheDocument();
    expect(screen.getByTestId("comparator-computed-curve")).toBeInTheDocument();
  });

  it("renders the ±5% tolerance band path", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" />);
    const band = screen.getByTestId("comparator-tolerance-band");
    expect(band.getAttribute("fill")).toBe("#b78b65");
    expect(band.getAttribute("fill-opacity")).toBe("0.08");
  });

  it("renders max-delta annotation with a numeric percent", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" />);
    const annot = screen.getByTestId("comparator-max-delta");
    expect(annot.textContent).toMatch(/max \|Δu\| = \d+\.\d{2}%/);
  });

  it("worst point comes from worstDelta helper · ≤5% (PASS verdict)", () => {
    const computed = computeLidCavityComputed();
    const { abs_delta_pct } = worstDelta(
      GHIA_LID_CAVITY_U_CENTERLINE,
      computed,
    );
    expect(abs_delta_pct).toBeLessThan(5);
    expect(abs_delta_pct).toBeGreaterThan(0);
  });

  it("contains no interactive mutating affordances (V130/V132)", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" />);
    const section = screen.getByTestId(
      "comparator-gold-actual-lid_driven_cavity-u_centerline",
    );
    expect(section.querySelectorAll("button").length).toBe(0);
    expect(section.querySelectorAll("form").length).toBe(0);
    expect(section.querySelectorAll("input").length).toBe(0);
    expect(section.querySelectorAll("a[href]").length).toBe(0);
  });

  it("uses sand-coral for the computed curve (V4.C lock)", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" />);
    const polyline = screen.getByTestId("comparator-computed-curve");
    expect(polyline.getAttribute("stroke")).toBe("#b78b65");
    expect(polyline.getAttribute("stroke-width")).toBe("1.8");
  });

  it("uses dusty-amber for the worst-point highlight (V4.C lock)", () => {
    render(<ComparatorV4 caseId="lid_driven_cavity" />);
    const worst = screen.getByTestId("comparator-worst-point");
    expect(worst.getAttribute("fill")).toBe("#a89060");
  });
});
