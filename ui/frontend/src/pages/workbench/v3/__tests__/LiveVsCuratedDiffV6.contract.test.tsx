/**
 * V85.4 · V6.C Live-vs-Curated Diff Panel contract test
 *
 * Asserts the V6.C contract from .planning/blueprints/v6/INDEX.md:
 *   - Hidden when active=false (curated mode default preserved)
 *   - Two columns: curated (V5) left, bridge (V6) right
 *   - Divergence badge appears when significant differences detected
 *   - Failed run surfaces verdict_mismatch + failure_category_present
 *   - Placeholder Re (99999999) surfaces placeholder_re divergence
 *   - V130 invariant: zero buttons · zero form/input/select · passive
 *     observation text only
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { LiveVsCuratedDiffV6 } from "../components/LiveVsCuratedDiffV6";
import type { BridgeArtifact } from "@/data/run_artifact_reader";
import type { StepId } from "../WorkbenchShellV3";

const SUCCESS_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-01-18Z",
  started_at: "2026-04-27T10:01:18Z",
  duration_s: 2476.66,
  success: true,
  exit_code: 0,
  verdict_summary: "OpenFOAM PASS",
  failure_category: null,
  task_spec: { Re: 100, steady_state: "STEADY" },
  key_quantities: { cells: 16384 },
  residuals: { Ux: 1.2e-6 },
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
  task_spec: { Re: 99999999 },
};

describe("LiveVsCuratedDiffV6 contract · V85.4 · V6.C", () => {
  it("renders nothing when active=false", () => {
    const { container } = render(
      <LiveVsCuratedDiffV6
        active={false}
        caseId="lid_driven_cavity"
        stepId={1}
        bridgeArtifact={SUCCESS_ARTIFACT}
      />,
    );
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId("live-vs-curated-diff")).not.toBeInTheDocument();
  });

  it("renders nothing when artifact is null even if active=true", () => {
    const { container } = render(
      <LiveVsCuratedDiffV6
        active={true}
        caseId="lid_driven_cavity"
        stepId={1}
        bridgeArtifact={null}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders two columns (curated + bridge) when active + artifact", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={1}
        bridgeArtifact={SUCCESS_ARTIFACT}
      />,
    );
    expect(screen.getByTestId("live-vs-curated-diff")).toBeInTheDocument();
    expect(screen.getByTestId("diff-column-curated")).toBeInTheDocument();
    expect(screen.getByTestId("diff-column-bridge")).toBeInTheDocument();
  });

  it("curated column shows V5 sandbox_step_states banner", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={2}
        bridgeArtifact={SUCCESS_ARTIFACT}
      />,
    );
    const curatedCol = screen.getByTestId("diff-column-curated");
    expect(curatedCol.textContent).toMatch(/curated · V5/);
    expect(curatedCol.textContent).toMatch(/skewness 0\.32|cartesian/);
  });

  it("bridge column shows V6 real-artifact banner with run_id", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={1}
        bridgeArtifact={SUCCESS_ARTIFACT}
      />,
    );
    const bridgeCol = screen.getByTestId("diff-column-bridge");
    expect(bridgeCol.textContent).toMatch(/live · V6 bridge/);
    expect(bridgeCol.textContent).toMatch(/2026-04-27T10-01-18Z/);
    expect(bridgeCol.textContent).toMatch(/Import/);
  });

  it("no divergences shown on successful run with sane task_spec", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={1}
        bridgeArtifact={SUCCESS_ARTIFACT}
      />,
    );
    const root = screen.getByTestId("live-vs-curated-diff");
    expect(root.getAttribute("data-divergence-count")).toBe("0");
    expect(screen.queryByTestId("diff-divergences")).not.toBeInTheDocument();
    expect(screen.queryByTestId("divergence-badge")).not.toBeInTheDocument();
  });

  it("verdict_mismatch + failure_category_present divergences on failed run", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={5}
        bridgeArtifact={FAILED_ARTIFACT}
      />,
    );
    const root = screen.getByTestId("live-vs-curated-diff");
    // failed run with placeholder Re → 3 divergences
    expect(root.getAttribute("data-divergence-count")).toBe("3");
    const kinds = root
      .querySelector("[data-testid='diff-divergences']")!
      .getAttribute("data-divergence-kinds");
    expect(kinds).toContain("verdict_mismatch");
    expect(kinds).toContain("failure_category_present");
    expect(kinds).toContain("placeholder_re");
    expect(screen.getByTestId("divergence-badge").textContent).toMatch(/× 3/);
    expect(
      screen.getByTestId("divergence-note-verdict_mismatch"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("divergence-note-failure_category_present"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("divergence-note-placeholder_re"),
    ).toBeInTheDocument();
  });

  it("placeholder Re alone (no failure) surfaces 1 divergence", () => {
    const partial: BridgeArtifact = {
      ...SUCCESS_ARTIFACT,
      task_spec: { Re: 99999999 },
    };
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={3}
        bridgeArtifact={partial}
      />,
    );
    const root = screen.getByTestId("live-vs-curated-diff");
    expect(root.getAttribute("data-divergence-count")).toBe("1");
    expect(
      screen.getByTestId("divergence-note-placeholder_re"),
    ).toBeInTheDocument();
  });

  it("V130: zero buttons + zero form/input/select in diff panel", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={5}
        bridgeArtifact={FAILED_ARTIFACT}
      />,
    );
    const root = screen.getByTestId("live-vs-curated-diff");
    expect(root.querySelectorAll("button").length).toBe(0);
    expect(root.querySelectorAll("form").length).toBe(0);
    expect(root.querySelectorAll("input").length).toBe(0);
    expect(root.querySelectorAll("textarea").length).toBe(0);
    expect(root.querySelectorAll("select").length).toBe(0);
  });

  it("V130: divergence notes describe (no action verbs)", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="lid_driven_cavity"
        stepId={5}
        bridgeArtifact={FAILED_ARTIFACT}
      />,
    );
    const ACTION_DENYLIST = [
      "click",
      "press",
      "tap",
      "auto-fix",
      "auto-execute",
      "run now",
      "execute",
      "fix it",
      "remediate",
    ];
    const root = screen.getByTestId("live-vs-curated-diff");
    const txt = root.textContent!.toLowerCase();
    // Allow "no remediation action available" as the explicit V130 disclaimer.
    // Strip that phrase before checking the denylist.
    const stripped = txt.replace(/no remediation action available[^.]*/g, "");
    for (const verb of ACTION_DENYLIST) {
      expect(stripped, `denylist hit: "${verb}"`).not.toContain(verb);
    }
  });

  it("data-step-id and data-case-id mirror props for V6.D + tests", () => {
    render(
      <LiveVsCuratedDiffV6
        active
        caseId="naca0012_airfoil"
        stepId={4}
        bridgeArtifact={SUCCESS_ARTIFACT}
      />,
    );
    const root = screen.getByTestId("live-vs-curated-diff");
    expect(root.getAttribute("data-step-id")).toBe("4");
    expect(root.getAttribute("data-case-id")).toBe("naca0012_airfoil");
  });

  it("each step (1-5) renders both columns with appropriate content", () => {
    const steps: StepId[] = [1, 2, 3, 4, 5];
    for (const step of steps) {
      const { unmount } = render(
        <LiveVsCuratedDiffV6
          active
          caseId="lid_driven_cavity"
          stepId={step}
          bridgeArtifact={SUCCESS_ARTIFACT}
        />,
      );
      const curated = screen.getByTestId("diff-column-curated");
      const bridge = screen.getByTestId("diff-column-bridge");
      expect(curated.textContent).toMatch(new RegExp(`Step ${step}`));
      // bridge column always shows some Step content; verify non-empty
      expect(bridge.textContent!.length).toBeGreaterThan(20);
      unmount();
    }
  });
});
