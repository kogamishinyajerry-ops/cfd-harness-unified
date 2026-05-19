// V67-C.3 · BeginnerPowerContext + BeginnerPowerToggle unit tests

import { describe, expect, it, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { useEffect } from "react";

import {
  BeginnerPowerProvider,
  useBeginnerPower,
  useBeginnerPowerOptional,
} from "../BeginnerPowerContext";
import { BeginnerPowerToggle } from "../BeginnerPowerToggle";

const STORAGE_KEY = "v67c_beginner_power_mode";

describe("BeginnerPowerContext (V67-C.3)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("default mode is beginner when localStorage empty", () => {
    function Probe() {
      const { mode } = useBeginnerPower();
      return <span data-testid="probe-mode">{mode}</span>;
    }
    render(
      <BeginnerPowerProvider>
        <Probe />
      </BeginnerPowerProvider>,
    );
    expect(screen.getByTestId("probe-mode")).toHaveTextContent("beginner");
  });

  it("reads mode from localStorage on mount", () => {
    window.localStorage.setItem(STORAGE_KEY, "power");
    function Probe() {
      const { mode } = useBeginnerPower();
      return <span data-testid="probe-mode">{mode}</span>;
    }
    render(
      <BeginnerPowerProvider>
        <Probe />
      </BeginnerPowerProvider>,
    );
    expect(screen.getByTestId("probe-mode")).toHaveTextContent("power");
  });

  it("setMode persists to localStorage", () => {
    function Setter() {
      const { setMode } = useBeginnerPower();
      useEffect(() => {
        setMode("power");
      }, [setMode]);
      return null;
    }
    render(
      <BeginnerPowerProvider>
        <Setter />
      </BeginnerPowerProvider>,
    );
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("power");
  });

  it("toggle flips beginner ⇄ power", () => {
    let toggleFn: () => void = () => {};
    function Probe() {
      const { mode, toggle } = useBeginnerPower();
      toggleFn = toggle;
      return <span data-testid="probe-mode">{mode}</span>;
    }
    render(
      <BeginnerPowerProvider>
        <Probe />
      </BeginnerPowerProvider>,
    );
    expect(screen.getByTestId("probe-mode")).toHaveTextContent("beginner");
    act(() => toggleFn());
    expect(screen.getByTestId("probe-mode")).toHaveTextContent("power");
    act(() => toggleFn());
    expect(screen.getByTestId("probe-mode")).toHaveTextContent("beginner");
  });

  it("isBeginner / isPower derived flags match mode", () => {
    function Probe() {
      const { mode, isBeginner, isPower } = useBeginnerPower();
      return (
        <span data-testid="probe">
          {mode}/{String(isBeginner)}/{String(isPower)}
        </span>
      );
    }
    render(
      <BeginnerPowerProvider>
        <Probe />
      </BeginnerPowerProvider>,
    );
    expect(screen.getByTestId("probe")).toHaveTextContent(
      "beginner/true/false",
    );
  });

  it("useBeginnerPower throws when used without Provider", () => {
    function Bad() {
      useBeginnerPower();
      return null;
    }
    // Suppress error boundary noise in test output
    const orig = console.error;
    console.error = () => {};
    expect(() => render(<Bad />)).toThrow(
      /useBeginnerPower must be used within a <BeginnerPowerProvider>/,
    );
    console.error = orig;
  });

  it("useBeginnerPowerOptional returns null outside Provider", () => {
    let captured: unknown = "untouched";
    function Probe() {
      captured = useBeginnerPowerOptional();
      return null;
    }
    render(<Probe />);
    expect(captured).toBeNull();
  });

  it("useBeginnerPowerOptional returns value inside Provider", () => {
    let mode: string | undefined;
    function Probe() {
      const v = useBeginnerPowerOptional();
      mode = v?.mode;
      return null;
    }
    render(
      <BeginnerPowerProvider>
        <Probe />
      </BeginnerPowerProvider>,
    );
    expect(mode).toBe("beginner");
  });
});

describe("BeginnerPowerToggle UI (V67-C.3)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders both buttons + reflects default mode (beginner pressed)", () => {
    render(
      <BeginnerPowerProvider>
        <BeginnerPowerToggle />
      </BeginnerPowerProvider>,
    );
    const wrapper = screen.getByTestId("beginner-power-toggle");
    expect(wrapper).toHaveAttribute("data-mode", "beginner");

    const beginnerBtn = screen.getByTestId("beginner-power-toggle-beginner");
    const powerBtn = screen.getByTestId("beginner-power-toggle-power");
    expect(beginnerBtn).toHaveAttribute("aria-pressed", "true");
    expect(powerBtn).toHaveAttribute("aria-pressed", "false");
    expect(beginnerBtn).toHaveTextContent("Beginner");
    expect(powerBtn).toHaveTextContent("Power");
  });

  it("clicking Power switches data-mode + aria-pressed", () => {
    render(
      <BeginnerPowerProvider>
        <BeginnerPowerToggle />
      </BeginnerPowerProvider>,
    );
    const powerBtn = screen.getByTestId("beginner-power-toggle-power");
    act(() => {
      powerBtn.click();
    });
    expect(screen.getByTestId("beginner-power-toggle")).toHaveAttribute(
      "data-mode",
      "power",
    );
    expect(powerBtn).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByTestId("beginner-power-toggle-beginner"),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking Beginner switches back from power", () => {
    window.localStorage.setItem(STORAGE_KEY, "power");
    render(
      <BeginnerPowerProvider>
        <BeginnerPowerToggle />
      </BeginnerPowerProvider>,
    );
    expect(screen.getByTestId("beginner-power-toggle")).toHaveAttribute(
      "data-mode",
      "power",
    );
    act(() => {
      screen.getByTestId("beginner-power-toggle-beginner").click();
    });
    expect(screen.getByTestId("beginner-power-toggle")).toHaveAttribute(
      "data-mode",
      "beginner",
    );
  });

  it("supports xs size variant", () => {
    render(
      <BeginnerPowerProvider>
        <BeginnerPowerToggle size="xs" />
      </BeginnerPowerProvider>,
    );
    // size variant should not break rendering
    expect(screen.getByTestId("beginner-power-toggle")).toBeInTheDocument();
  });
});
