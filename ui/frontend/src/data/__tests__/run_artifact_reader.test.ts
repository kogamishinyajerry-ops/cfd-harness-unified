/**
 * V85.2 · V6.A Bridge Reader contract tests
 *
 * Asserts the V6.A contract from .planning/blueprints/v6/INDEX.md:
 *   - artifact null → returns null (graceful degrade · curated fallback)
 *   - artifact present → returns BridgeStepState with source="real_artifact"
 *   - step 1-5 each produce a banner with step-appropriate fields
 *   - failed run (success=false) surfaces failure_category in step 5
 *   - sparse artifact (missing key_quantities / residuals) does NOT crash
 *   - artifact_success flag mirrors the underlying artifact.success bit
 *   - V130/V132 invariant: returned banners are descriptive only · no
 *     action verbs (this is asserted lexically against a denylist)
 */
import { describe, expect, it } from "vitest";

import {
  getBridgeStepState,
  isBridgeKnownCase,
  BRIDGE_KNOWN_CASES,
  type BridgeArtifact,
} from "../run_artifact_reader";

const SUCCESS_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-01-18Z",
  started_at: "2026-04-27T10:01:18.636875Z",
  duration_s: 2476.66,
  success: true,
  exit_code: 0,
  verdict_summary: "OpenFOAM PASS · all residuals < 1e-5",
  failure_category: null,
  task_spec: {
    Re: 100,
    flow_type: "INTERNAL",
    steady_state: "STEADY",
    compressibility: "INCOMPRESSIBLE",
  },
  key_quantities: {
    cells: 16384,
    y_plus_max: 0.85,
  },
  residuals: {
    Ux: 1.2e-6,
    p: 3.4e-5,
    k: 4.5e-6,
  },
};

const FAILED_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-01-18Z",
  started_at: "2026-04-27T10:01:18.636875Z",
  duration_s: 2476.66,
  success: false,
  exit_code: 1,
  verdict_summary: "OpenFOAM failed · simpleFoam diverged at iter 47",
  failure_category: "solver_diverged",
  task_spec: { Re: 99999999 },
  key_quantities: {},
  residuals: {},
};

describe("V6.A Bridge Reader · getBridgeStepState", () => {
  it("returns null when artifact is null (graceful degrade)", () => {
    expect(getBridgeStepState(null, 1)).toBeNull();
    expect(getBridgeStepState(null, 5)).toBeNull();
  });

  it("returns BridgeStepState with source='real_artifact' when artifact present", () => {
    const state = getBridgeStepState(SUCCESS_ARTIFACT, 1);
    expect(state).not.toBeNull();
    expect(state!.source).toBe("real_artifact");
    expect(state!.caseId).toBe("lid_driven_cavity");
    expect(state!.runId).toBe("2026-04-27T10-01-18Z");
  });

  it("step 1 banner surfaces task_spec flow shape", () => {
    const state = getBridgeStepState(SUCCESS_ARTIFACT, 1);
    expect(state!.banner).toMatch(/Import/);
    expect(state!.banner).toMatch(/INTERNAL/);
    expect(state!.banner).toMatch(/2026-04-27T10-01-18Z/);
  });

  it("step 2 banner surfaces cell count + y+", () => {
    const state = getBridgeStepState(SUCCESS_ARTIFACT, 2);
    expect(state!.banner).toMatch(/Mesh/);
    expect(state!.banner).toMatch(/16384 cells/);
    expect(state!.banner).toMatch(/y\+ ≤ 0\.85/);
  });

  it("step 2 banner handles missing key_quantities gracefully", () => {
    const state = getBridgeStepState(FAILED_ARTIFACT, 2);
    expect(state!.banner).toMatch(/Mesh/);
    expect(state!.banner).toMatch(/not captured/);
  });

  it("step 3 banner surfaces Re + steadiness + compressibility", () => {
    const state = getBridgeStepState(SUCCESS_ARTIFACT, 3);
    expect(state!.banner).toMatch(/Physics/);
    expect(state!.banner).toMatch(/Re=100/);
    expect(state!.banner).toMatch(/STEADY/);
    expect(state!.banner).toMatch(/INCOMPRESSIBLE/);
  });

  it("step 4 banner surfaces residuals + exit code + duration", () => {
    const state = getBridgeStepState(SUCCESS_ARTIFACT, 4);
    expect(state!.banner).toMatch(/Solver/);
    expect(state!.banner).toMatch(/Ux=/);
    expect(state!.banner).toMatch(/exit=0/);
    expect(state!.banner).toMatch(/41\.3min|2476/); // duration formatted
  });

  it("step 4 banner shows non-zero exit + missing residuals on failed run", () => {
    const state = getBridgeStepState(FAILED_ARTIFACT, 4);
    expect(state!.banner).toMatch(/Solver/);
    expect(state!.banner).toMatch(/exit=1/);
    expect(state!.banner).toMatch(/residuals not captured/);
  });

  it("step 5 banner surfaces PASS verdict on success", () => {
    const state = getBridgeStepState(SUCCESS_ARTIFACT, 5);
    expect(state!.banner).toMatch(/Postprocess/);
    expect(state!.banner).toMatch(/PASS/);
    expect(state!.artifactSuccess).toBe(true);
    expect(state!.failureCategory).toBeNull();
  });

  it("step 5 banner surfaces FAIL + failure_category on failed run", () => {
    const state = getBridgeStepState(FAILED_ARTIFACT, 5);
    expect(state!.banner).toMatch(/Postprocess/);
    expect(state!.banner).toMatch(/FAIL/);
    expect(state!.banner).toMatch(/solver_diverged/);
    expect(state!.artifactSuccess).toBe(false);
    expect(state!.failureCategory).toBe("solver_diverged");
  });

  it("step 5 banner truncates multi-line verdict summary to first line", () => {
    const multiline: BridgeArtifact = {
      ...FAILED_ARTIFACT,
      verdict_summary:
        "OpenFOAM failed · simpleFoam failed:\n/*-----------*\\\n  =====    |\n  \\    /  F ield   | O",
    };
    const state = getBridgeStepState(multiline, 5);
    expect(state!.banner).not.toMatch(/\n/);
    expect(state!.banner).toMatch(/OpenFOAM failed/);
  });

  // V130/V132 invariant assertion: banners describe state, they do not
  // recommend or trigger actions. The denylist catches obvious slip-ups.
  it("V130: returned banners contain no action verbs", () => {
    const ACTION_DENYLIST = [
      "click here",
      "run now",
      "auto-fix",
      "auto-execute",
      "press to",
      "tap to",
      "execute",
      "fix it",
    ];
    const allSteps: number[] = [1, 2, 3, 4, 5];
    for (const stepNum of allSteps) {
      const step = stepNum as 1 | 2 | 3 | 4 | 5;
      const okBanner = getBridgeStepState(SUCCESS_ARTIFACT, step)!.banner.toLowerCase();
      const failBanner = getBridgeStepState(FAILED_ARTIFACT, step)!.banner.toLowerCase();
      for (const verb of ACTION_DENYLIST) {
        expect(okBanner, `success step ${step}`).not.toContain(verb);
        expect(failBanner, `failed step ${step}`).not.toContain(verb);
      }
    }
  });

  it("artifactSuccess mirrors artifact.success across steps", () => {
    for (let stepNum = 1; stepNum <= 5; stepNum++) {
      const step = stepNum as 1 | 2 | 3 | 4 | 5;
      expect(getBridgeStepState(SUCCESS_ARTIFACT, step)!.artifactSuccess).toBe(true);
      expect(getBridgeStepState(FAILED_ARTIFACT, step)!.artifactSuccess).toBe(false);
    }
  });

  it("placeholder Re (99999999) surfaces verbatim for V6.C diff detection", () => {
    const state = getBridgeStepState(FAILED_ARTIFACT, 3);
    expect(state!.banner).toMatch(/Re=99999999/);
  });
});

describe("V6.A Bridge Reader · BRIDGE_KNOWN_CASES + isBridgeKnownCase", () => {
  it("lid_driven_cavity is in the known list (real artifact committed)", () => {
    expect(BRIDGE_KNOWN_CASES).toContain("lid_driven_cavity");
    expect(isBridgeKnownCase("lid_driven_cavity")).toBe(true);
  });

  it("returns false for null/undefined/unknown cases", () => {
    expect(isBridgeKnownCase(null)).toBe(false);
    expect(isBridgeKnownCase(undefined)).toBe(false);
    expect(isBridgeKnownCase("not_a_real_case")).toBe(false);
  });

  it("known cases list is conservative (only cases with committed artifacts)", () => {
    // V85.2: only lid_driven_cavity has captured runs in reports/.
    // New cases get added when artifacts land.
    expect(BRIDGE_KNOWN_CASES.length).toBeGreaterThanOrEqual(1);
    expect(BRIDGE_KNOWN_CASES.length).toBeLessThanOrEqual(10);
  });
});
