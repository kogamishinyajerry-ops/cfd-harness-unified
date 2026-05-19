/**
 * V83.2 · DemoSandboxV5 contract test
 *
 * Asserts the V5.A contract from .planning/blueprints/v5/INDEX.md:
 *   - `?demo=2` activates sandbox-mode-pill + exit link
 *   - `?demo=1` (V4 tour) does NOT activate sandbox
 *   - Step transition produces a sandbox-step-banner with the new stepId
 *   - Exit link clears the demo query param
 *   - NO buttons that emit POST/PUT/DELETE (V130/V132 enforced structurally)
 */
import { describe, expect, it } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { DemoSandboxV5 } from "../components/DemoSandboxV5";
import type { StepId } from "../WorkbenchShellV3";

function Harness({ initialStep = 1 as StepId }: { initialStep?: StepId }) {
  return (
    <MemoryRouter initialEntries={[`/?step=${initialStep}&demo=2`]}>
      <Routes>
        <Route path="/" element={<DemoSandboxV5 stepId={initialStep} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("DemoSandboxV5 contract · V83.2 · V5.A", () => {
  it("does not render when ?demo is absent", () => {
    render(
      <MemoryRouter initialEntries={["/?step=1"]}>
        <Routes>
          <Route path="/" element={<DemoSandboxV5 stepId={1} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("demo-sandbox-v5")).not.toBeInTheDocument();
  });

  it("does not render when ?demo=1 (V4 tour mode, not sandbox)", () => {
    render(
      <MemoryRouter initialEntries={["/?step=1&demo=1"]}>
        <Routes>
          <Route path="/" element={<DemoSandboxV5 stepId={1} />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("demo-sandbox-v5")).not.toBeInTheDocument();
  });

  it("activates sandbox-mode-pill + exit link when ?demo=2", () => {
    render(<Harness />);
    expect(screen.getByTestId("demo-sandbox-v5")).toBeInTheDocument();
    expect(screen.getByTestId("sandbox-mode-pill")).toBeInTheDocument();
    expect(screen.getByTestId("sandbox-exit")).toBeInTheDocument();
    expect(screen.getByTestId("sandbox-mode-pill").textContent).toMatch(
      /SANDBOX MODE/,
    );
    expect(screen.getByTestId("sandbox-mode-pill").textContent).toMatch(
      /no real solver/,
    );
  });

  it("shows step-transition banner with the current step label (fallback path)", () => {
    render(<Harness initialStep={2} />);
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner).toBeInTheDocument();
    expect(banner.getAttribute("data-step-id")).toBe("2");
    expect(banner.textContent).toMatch(/Step 2/);
    // V84.5 · Harness doesn't pass caseId → falls back to generic FALLBACK label
    expect(banner.textContent).toMatch(/curated quality preview/);
  });

  it("renders different step labels per stepId", () => {
    const { rerender } = render(<Harness initialStep={4} />);
    expect(screen.getByTestId("sandbox-step-banner").textContent).toMatch(
      /Step 4/,
    );
    rerender(<Harness initialStep={5} />);
    expect(screen.getByTestId("sandbox-step-banner").textContent).toMatch(
      /Step 5/,
    );
  });

  it("exit link clears the demo query param", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/?step=1&demo=2"]}>
        <Routes>
          <Route path="/" element={<DemoSandboxV5 stepId={1} />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("sandbox-mode-pill")).toBeInTheDocument();
    await act(async () => {
      await user.click(screen.getByTestId("sandbox-exit"));
    });
    // After exit, the component unmounts (demo param is gone)
    expect(screen.queryByTestId("demo-sandbox-v5")).not.toBeInTheDocument();
  });

  it("contains no form/input/POST-style affordance (V130/V132)", () => {
    render(<Harness />);
    const section = screen.getByTestId("demo-sandbox-v5");
    expect(section.querySelectorAll("form").length).toBe(0);
    expect(section.querySelectorAll("input").length).toBe(0);
    expect(section.querySelectorAll("textarea").length).toBe(0);
    expect(section.querySelectorAll("select").length).toBe(0);
    // Only one button (exit) and it sets URL state, doesn't mutate backend
    const buttons = section.querySelectorAll("button");
    expect(buttons.length).toBe(1);
    expect(buttons[0].getAttribute("data-testid")).toBe("sandbox-exit");
  });

  // V84.5 · multi-case sandbox traversal
  it.each([
    {
      caseId: "lid_driven_cavity",
      step: 2 as const,
      match: /skewness 0\.32|cartesian/,
    },
    {
      caseId: "naca0012_airfoil",
      step: 4 as const,
      match: /Cl convergence|iter 2000/,
    },
    {
      caseId: "backward_facing_step",
      step: 5 as const,
      match: /x_r\/h|Driver-Seegmiller/,
    },
    {
      caseId: "circular_cylinder_wake",
      step: 5 as const,
      match: /St =|Williamson/,
    },
    {
      caseId: "turbulent_flat_plate",
      step: 5 as const,
      match: /log-law|κ/,
    },
    {
      caseId: "plane_channel_flow",
      step: 4 as const,
      match: /Re_τ|bulk Re/,
    },
    {
      caseId: "impinging_jet",
      step: 5 as const,
      match: /Nu_0|Cooper/,
    },
    {
      caseId: "rayleigh_benard_convection",
      step: 5 as const,
      match: /Nu ≈ 27|Kerr/,
    },
    {
      caseId: "differential_heated_cavity",
      step: 5 as const,
      match: /Nu_hot|de Vahl Davis/,
    },
    {
      caseId: "duct_flow",
      step: 5 as const,
      match: /vortices|Gavrilakis/,
    },
  ])(
    "surfaces per-case curated banner for $caseId at step $step",
    ({ caseId, step, match }) => {
      render(
        <MemoryRouter initialEntries={[`/?step=${step}&demo=2`]}>
          <Routes>
            <Route
              path="/"
              element={<DemoSandboxV5 stepId={step} caseId={caseId} />}
            />
          </Routes>
        </MemoryRouter>,
      );
      const banner = screen.getByTestId("sandbox-step-banner");
      expect(banner.getAttribute("data-case-id")).toBe(caseId);
      expect(banner.getAttribute("data-case-curated")).toBe("true");
      expect(banner.textContent).toMatch(match);
    },
  );

  it("falls back to generic banner for non-curated caseId", () => {
    render(
      <MemoryRouter initialEntries={["/?step=1&demo=2"]}>
        <Routes>
          <Route
            path="/"
            element={<DemoSandboxV5 stepId={1} caseId="not_a_real_case" />}
          />
        </Routes>
      </MemoryRouter>,
    );
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-case-curated")).toBe("false");
    expect(banner.textContent).toMatch(/case geometry preview/);
  });
});
