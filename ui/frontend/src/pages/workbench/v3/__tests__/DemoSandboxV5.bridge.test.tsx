/**
 * V85.3 · V6.B Bridge-Mode Sandbox contract test
 *
 * Asserts the V6.B contract from .planning/blueprints/v6/INDEX.md:
 *   - `?bridge=1` + non-null bridgeArtifact → renders bridge banner
 *     (data-source="bridge") with LIVE badge
 *   - `?bridge=1` + null artifact → graceful degrade to curated path
 *     (data-source="curated", no LIVE badge)
 *   - `?bridge` absent → curated path regardless of artifact
 *   - Failed artifact (success=false) renders FAIL verdict at step 5
 *   - V130 invariant: no auto-execute affordance · no buttons that
 *     would mutate backend state · bridge banner has zero buttons
 *
 * The bridge artifact data shape mirrors V6.A run_artifact_reader's
 * BridgeArtifact interface — see run_artifact_reader.test.ts for the
 * pure data-mapping assertions.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { DemoSandboxV5 } from "../components/DemoSandboxV5";
import type { StepId } from "../WorkbenchShellV3";
import type { BridgeArtifact } from "@/data/run_artifact_reader";

const SUCCESS_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-01-18Z",
  started_at: "2026-04-27T10:01:18Z",
  duration_s: 2476.66,
  success: true,
  exit_code: 0,
  verdict_summary: "OpenFOAM PASS",
  failure_category: null,
  task_spec: { Re: 100, steady_state: "STEADY", compressibility: "INCOMPRESSIBLE" },
  key_quantities: { cells: 16384, y_plus_max: 0.85 },
  residuals: { Ux: 1.2e-6, p: 3.4e-5 },
};

const FAILED_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-42-35Z",
  started_at: "2026-04-27T10:42:35Z",
  duration_s: 47.3,
  success: false,
  exit_code: 1,
  verdict_summary: "OpenFOAM failed · simpleFoam diverged",
  failure_category: "solver_diverged",
};

function BridgeHarness({
  step = 1 as StepId,
  bridgeOn = true,
  artifact = SUCCESS_ARTIFACT as BridgeArtifact | null,
  caseId = "lid_driven_cavity" as string | null,
}: {
  step?: StepId;
  bridgeOn?: boolean;
  artifact?: BridgeArtifact | null;
  caseId?: string | null;
}) {
  const query = bridgeOn
    ? `step=${step}&demo=2&bridge=1`
    : `step=${step}&demo=2`;
  return (
    <MemoryRouter initialEntries={[`/?${query}`]}>
      <Routes>
        <Route
          path="/"
          element={
            <DemoSandboxV5
              stepId={step}
              caseId={caseId}
              bridgeArtifact={artifact}
            />
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("DemoSandboxV5 bridge contract · V85.3 · V6.B", () => {
  it("renders bridge banner with LIVE badge when ?bridge=1 + artifact present", () => {
    render(<BridgeHarness step={1} bridgeOn artifact={SUCCESS_ARTIFACT} />);
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-source")).toBe("bridge");
    expect(banner.getAttribute("data-bridge-run-id")).toBe(
      "2026-04-27T10-01-18Z",
    );
    expect(screen.getByTestId("bridge-live-badge")).toBeInTheDocument();
    expect(banner.textContent).toMatch(/Import/);
    expect(banner.textContent).toMatch(/STEADY|INCOMPRESSIBLE/);
  });

  it("falls back to curated when ?bridge=1 but artifact is null (graceful degrade)", () => {
    render(<BridgeHarness step={2} bridgeOn artifact={null} />);
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-source")).toBe("curated");
    expect(banner.getAttribute("data-bridge-run-id")).toBeNull();
    expect(screen.queryByTestId("bridge-live-badge")).not.toBeInTheDocument();
    // Curated lid_driven_cavity step 2 banner from sandbox_step_states.ts
    expect(banner.textContent).toMatch(/skewness 0\.32|cartesian/);
  });

  it("uses curated path when ?bridge is absent, even if artifact provided", () => {
    render(
      <BridgeHarness step={1} bridgeOn={false} artifact={SUCCESS_ARTIFACT} />,
    );
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-source")).toBe("curated");
    expect(screen.queryByTestId("bridge-live-badge")).not.toBeInTheDocument();
  });

  it("step 4 bridge banner shows residuals + exit code from real run", () => {
    render(<BridgeHarness step={4} bridgeOn artifact={SUCCESS_ARTIFACT} />);
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-source")).toBe("bridge");
    expect(banner.textContent).toMatch(/Solver/);
    expect(banner.textContent).toMatch(/exit=0/);
  });

  it("step 5 bridge banner shows FAIL + failure_category from failed run", () => {
    render(<BridgeHarness step={5} bridgeOn artifact={FAILED_ARTIFACT} />);
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-source")).toBe("bridge");
    expect(banner.getAttribute("data-bridge-run-id")).toBe(
      "2026-04-27T10-42-35Z",
    );
    expect(banner.textContent).toMatch(/FAIL/);
    expect(banner.textContent).toMatch(/solver_diverged/);
  });

  it("V130: bridge banner contains no action-button affordance (still 1 button only: exit)", () => {
    render(<BridgeHarness step={4} bridgeOn artifact={SUCCESS_ARTIFACT} />);
    const section = screen.getByTestId("demo-sandbox-v5");
    const buttons = section.querySelectorAll("button");
    expect(buttons.length).toBe(1);
    expect(buttons[0].getAttribute("data-testid")).toBe("sandbox-exit");
    // No forms / inputs / selects — V83.2 + V85.3 carry
    expect(section.querySelectorAll("form").length).toBe(0);
    expect(section.querySelectorAll("input").length).toBe(0);
    expect(section.querySelectorAll("textarea").length).toBe(0);
  });

  it("LIVE badge sits inside the step banner span (not a separate testid surface)", () => {
    render(<BridgeHarness step={3} bridgeOn artifact={SUCCESS_ARTIFACT} />);
    const banner = screen.getByTestId("sandbox-step-banner");
    const liveBadge = screen.getByTestId("bridge-live-badge");
    expect(banner.contains(liveBadge)).toBe(true);
    expect(liveBadge.textContent).toMatch(/LIVE/);
  });

  it("data-case-id + data-case-curated still present in bridge mode (V84.5 carry)", () => {
    render(
      <BridgeHarness
        step={1}
        bridgeOn
        artifact={SUCCESS_ARTIFACT}
        caseId="lid_driven_cavity"
      />,
    );
    const banner = screen.getByTestId("sandbox-step-banner");
    expect(banner.getAttribute("data-case-id")).toBe("lid_driven_cavity");
    expect(banner.getAttribute("data-case-curated")).toBe("true");
    // data-source overrides the visual rendering, but case attrs remain
    // so V6.C diff panel can still locate the curated companion.
    expect(banner.getAttribute("data-source")).toBe("bridge");
  });
});
