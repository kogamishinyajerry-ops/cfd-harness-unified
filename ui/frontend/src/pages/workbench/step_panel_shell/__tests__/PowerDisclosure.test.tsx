/**
 * V68-A.3 · PowerDisclosure wrapper tests · Beginner/Power semantics +
 * graceful fallback when no provider is present.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { BeginnerPowerProvider } from "../BeginnerPowerContext";
import { PowerDisclosure } from "../PowerDisclosure";

function renderWithMode(mode: "beginner" | "power", children: React.ReactNode) {
  window.localStorage.setItem("v67c_beginner_power_mode", mode);
  return render(<BeginnerPowerProvider>{children}</BeginnerPowerProvider>);
}

describe("PowerDisclosure (V68-A.3)", () => {
  it("renders Beginner summary by default (no provider) — graceful fallback", () => {
    render(
      <PowerDisclosure
        label="Advanced unit override"
        summary="Defaults to SI (m / kg / s)"
        testIdPrefix="step1-adv"
      >
        <div>knobs</div>
      </PowerDisclosure>,
    );
    expect(screen.getByTestId("step1-adv-disclosure")).toHaveAttribute(
      "data-mode",
      "beginner",
    );
    expect(screen.getByTestId("step1-adv-summary")).toHaveTextContent(
      "Defaults to SI",
    );
    expect(screen.queryByTestId("step1-adv-advanced")).toBeNull();
  });

  it("Beginner mode (via provider) renders summary, hides advanced", () => {
    renderWithMode(
      "beginner",
      <PowerDisclosure label="L" summary="preset summary" testIdPrefix="t">
        <div data-testid="hidden-child">advanced knobs</div>
      </PowerDisclosure>,
    );
    expect(screen.getByTestId("t-disclosure")).toHaveAttribute(
      "data-mode",
      "beginner",
    );
    expect(screen.getByTestId("t-summary")).toHaveTextContent("preset summary");
    expect(screen.queryByTestId("hidden-child")).toBeNull();
    expect(screen.getByText("BEGINNER")).toBeInTheDocument();
  });

  it("Power mode (via provider) renders advanced, hides summary", () => {
    renderWithMode(
      "power",
      <PowerDisclosure label="L" summary="preset summary" testIdPrefix="t">
        <div data-testid="visible-child">advanced knobs</div>
      </PowerDisclosure>,
    );
    expect(screen.getByTestId("t-disclosure")).toHaveAttribute(
      "data-mode",
      "power",
    );
    expect(screen.getByTestId("visible-child")).toBeInTheDocument();
    expect(screen.queryByTestId("t-summary")).toBeNull();
    expect(screen.getByText("POWER")).toBeInTheDocument();
  });

  it("uses default testIdPrefix when none provided", () => {
    render(
      <PowerDisclosure label="L" summary="S">
        <div>x</div>
      </PowerDisclosure>,
    );
    expect(screen.getByTestId("power-disclosure-disclosure")).toBeInTheDocument();
    expect(screen.getByTestId("power-disclosure-summary")).toBeInTheDocument();
  });
});
