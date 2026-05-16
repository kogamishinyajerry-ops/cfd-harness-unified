// V73.4 · VerdictPill DRY primitive · unit tests.
//
// Asserts the single primitive renders the right tone for every supported
// verdict input + that the normalizer collapses backend variants into the
// canonical VerdictKind enum (no drift between call sites).

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { VerdictPill, normalizeVerdict } from "../components/VerdictPill";

describe("V73.4 · normalizeVerdict", () => {
  it("maps PASS / audit-passing / audit_passing → PASS", () => {
    expect(normalizeVerdict("PASS")).toBe("PASS");
    expect(normalizeVerdict("pass")).toBe("PASS");
    expect(normalizeVerdict("audit-passing")).toBe("PASS");
    expect(normalizeVerdict("audit_passing")).toBe("PASS");
  });

  it("maps FAIL / audit-failing → FAIL", () => {
    expect(normalizeVerdict("FAIL")).toBe("FAIL");
    expect(normalizeVerdict("audit-failing")).toBe("FAIL");
  });

  it("maps PASS_WITH_DISCLAIMER variants", () => {
    expect(normalizeVerdict("PASS_WITH_DISCLAIMER")).toBe("PASS_WITH_DISCLAIMER");
    expect(normalizeVerdict("pass-with-disclaimer")).toBe("PASS_WITH_DISCLAIMER");
  });

  it("maps PENDING / gold-pending → PENDING", () => {
    expect(normalizeVerdict("PENDING")).toBe("PENDING");
    expect(normalizeVerdict("gold-pending")).toBe("PENDING");
  });

  it("nullish + unknown → PENDING / INCONCLUSIVE (never throws)", () => {
    expect(normalizeVerdict(null)).toBe("PENDING");
    expect(normalizeVerdict(undefined)).toBe("PENDING");
    expect(normalizeVerdict("")).toBe("PENDING");
    expect(normalizeVerdict("garbage")).toBe("INCONCLUSIVE");
  });
});

describe("V73.4 · VerdictPill render", () => {
  it("renders with default testid and data-verdict", () => {
    render(<VerdictPill verdict="PASS" />);
    const pill = screen.getByTestId("verdict-pill");
    expect(pill).toHaveAttribute("data-verdict", "PASS");
    expect(pill.textContent).toMatch(/pass/i);
  });

  it("accepts custom data-testid for call-site differentiation", () => {
    render(<VerdictPill verdict="FAIL" data-testid="ribbon-verdict" />);
    expect(screen.getByTestId("ribbon-verdict")).toHaveAttribute(
      "data-verdict",
      "FAIL",
    );
  });

  it("normalizes raw strings (audit-passing → data-verdict=PASS)", () => {
    render(<VerdictPill verdict="audit-passing" data-testid="raw-pill" />);
    expect(screen.getByTestId("raw-pill")).toHaveAttribute(
      "data-verdict",
      "PASS",
    );
  });

  it("renders no buttons / no mutating affordance (V130/V132)", () => {
    render(<VerdictPill verdict="PASS" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
