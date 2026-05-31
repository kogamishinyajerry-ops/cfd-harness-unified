/**
 * W3.1 Codex R0 P2 fix · forward-compat adapter carry-through tests.
 *
 * Verifies that adaptRunDetailToSlice and adaptBridgeArtifactToSlice carry
 * regions through to the RunArtifactSlice when the backend payload includes
 * them (W3.2 forward-compat path). Until W3.2 emits manifest["regions"],
 * the payload omits the field and the adapters correctly produce
 * regions: undefined → CHT rules R13–R16 silently dormant.
 *
 * Also verifies that when regions IS present in the payload, the CHT rules
 * can fire end-to-end through matchAdvisorPatterns (the full TS chain).
 *
 * All execution: MOCKED (no backend calls; all payloads are synthetic
 * TypeScript objects — MOCKED RUN, not a real solver run).
 */
import { describe, expect, it } from "vitest";

import {
  matchAdvisorPatterns,
  type RunArtifactSlice,
  type RegionSlice,
} from "../advisor_pattern_matcher";
import { V9_ADVISOR_RULES } from "../v9_advisor_rules";
import type { BridgeArtifact } from "../run_artifact_reader";
import type { RunDetail } from "../../types/run_history";

// ---------------------------------------------------------------------------
// Adapter implementations (mirrors the production adapters in their modules)
// ---------------------------------------------------------------------------

/** Mirror of adaptRunDetailToSlice from useV4AdvisorMatches.ts */
function adaptRunDetailToSlice(detail: RunDetail): RunArtifactSlice {
  return {
    run_id: detail.run_id,
    case_id: detail.case_id,
    success: detail.success,
    exit_code: detail.exit_code,
    residuals: undefined,
    forces: undefined,
    convergence_stats: undefined,
    gold_delta: undefined,
    regions: detail.regions ?? undefined,
  };
}

/** Mirror of adaptBridgeArtifactToSlice from WorkbenchShellV3.tsx */
function adaptBridgeArtifactToSlice(bridge: BridgeArtifact): RunArtifactSlice {
  return {
    run_id: bridge.run_id,
    case_id: bridge.case_id,
    success: bridge.success,
    exit_code: bridge.exit_code,
    residuals: undefined,
    forces: undefined,
    convergence_stats: undefined,
    gold_delta: undefined,
    regions: bridge.regions ?? undefined,
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SOLID_REGION_NO_THERMO: RegionSlice = {
  name: "solid_plate",
  kind: "solid",
  thermo_type: null,          // missing — R14 trigger
  thermo_snapshot_ref: null,  // missing — R14 trigger
  shm_snapshot_ref: "shm_solid",
  coupled_patches: [],
};

const FLUID_REGION_HEALTHY: RegionSlice = {
  name: "fluid_hot",
  kind: "fluid",
  thermo_type: "heRhoThermo",
  thermo_snapshot_ref: "snap_fluid",
  shm_snapshot_ref: "shm_fluid",
  coupled_patches: [],
};

const BASE_RUN_DETAIL: RunDetail = {
  case_id: "cht_test",
  run_id: "R-W31-TEST",
  started_at: "2026-05-31T10:00:00Z",
  ended_at: null,
  duration_s: 120,
  success: true,
  exit_code: 0,
  verdict_summary: "PASS",
  error_message: null,
  source_origin: "draft",
  task_spec: {},
  key_quantities: {},
  residuals: {},
};

const BASE_BRIDGE_ARTIFACT: BridgeArtifact = {
  case_id: "cht_test",
  run_id: "R-W31-BRIDGE",
  started_at: "2026-05-31T10:00:00Z",
  duration_s: 120,
  success: true,
  exit_code: 0,
  verdict_summary: "PASS",
};

// ---------------------------------------------------------------------------
// Tests: RunDetail adapter carry-through
// ---------------------------------------------------------------------------

describe("W3.1 · adaptRunDetailToSlice · regions carry-through", () => {
  it("carries regions when RunDetail payload includes them (W3.2 forward-compat)", () => {
    const detail: RunDetail = {
      ...BASE_RUN_DETAIL,
      regions: [FLUID_REGION_HEALTHY, SOLID_REGION_NO_THERMO],
    };
    const slice = adaptRunDetailToSlice(detail);
    expect(slice.regions).toBeDefined();
    expect(Array.isArray(slice.regions)).toBe(true);
    expect(slice.regions).toHaveLength(2);
    expect(slice.regions![0].name).toBe("fluid_hot");
    expect(slice.regions![1].name).toBe("solid_plate");
  });

  it("produces undefined regions when RunDetail has no regions field (pre-W3.2)", () => {
    const detail: RunDetail = { ...BASE_RUN_DETAIL };
    // regions is not set → adapter must pass undefined
    const slice = adaptRunDetailToSlice(detail);
    expect(slice.regions).toBeUndefined();
  });

  it("produces undefined regions when RunDetail.regions is null", () => {
    const detail: RunDetail = { ...BASE_RUN_DETAIL, regions: null };
    const slice = adaptRunDetailToSlice(detail);
    expect(slice.regions).toBeUndefined();
  });

  it("produces empty array when RunDetail.regions is [] (present, zero regions)", () => {
    const detail: RunDetail = { ...BASE_RUN_DETAIL, regions: [] };
    const slice = adaptRunDetailToSlice(detail);
    expect(slice.regions).toBeDefined();
    expect(slice.regions).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Tests: BridgeArtifact adapter carry-through
// ---------------------------------------------------------------------------

describe("W3.1 · adaptBridgeArtifactToSlice · regions carry-through", () => {
  it("carries regions when BridgeArtifact payload includes them (W3.2 forward-compat)", () => {
    const bridge: BridgeArtifact = {
      ...BASE_BRIDGE_ARTIFACT,
      regions: [FLUID_REGION_HEALTHY, SOLID_REGION_NO_THERMO],
    };
    const slice = adaptBridgeArtifactToSlice(bridge);
    expect(slice.regions).toBeDefined();
    expect(Array.isArray(slice.regions)).toBe(true);
    expect(slice.regions).toHaveLength(2);
  });

  it("produces undefined regions when BridgeArtifact has no regions field (pre-W3.2)", () => {
    const bridge: BridgeArtifact = { ...BASE_BRIDGE_ARTIFACT };
    const slice = adaptBridgeArtifactToSlice(bridge);
    expect(slice.regions).toBeUndefined();
  });

  it("produces undefined regions when BridgeArtifact.regions is null", () => {
    const bridge: BridgeArtifact = { ...BASE_BRIDGE_ARTIFACT, regions: null };
    const slice = adaptBridgeArtifactToSlice(bridge);
    expect(slice.regions).toBeUndefined();
  });

  it("produces empty array when BridgeArtifact.regions is [] (present, zero regions)", () => {
    const bridge: BridgeArtifact = { ...BASE_BRIDGE_ARTIFACT, regions: [] };
    const slice = adaptBridgeArtifactToSlice(bridge);
    expect(slice.regions).toBeDefined();
    expect(slice.regions).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Tests: End-to-end CHT rule activation via adapted slices
// ---------------------------------------------------------------------------

describe("W3.1 · end-to-end CHT rule activation via adapted slices", () => {
  it("R14 fires when RunDetail carries regions with thermo-missing solid", () => {
    const detail: RunDetail = {
      ...BASE_RUN_DETAIL,
      regions: [FLUID_REGION_HEALTHY, SOLID_REGION_NO_THERMO],
    };
    const slice = adaptRunDetailToSlice(detail);
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const ids = matches.map((m) => m.rule_id);
    expect(ids).toContain("PER_REGION_THERMO_MISSING_V9_R14");
  });

  it("R14 silent when RunDetail has no regions field (pre-W3.2 payload)", () => {
    const detail: RunDetail = { ...BASE_RUN_DETAIL };
    const slice = adaptRunDetailToSlice(detail);
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const ids = matches.map((m) => m.rule_id);
    expect(ids).not.toContain("PER_REGION_THERMO_MISSING_V9_R14");
  });

  it("R14 fires when BridgeArtifact carries regions with thermo-missing solid", () => {
    const bridge: BridgeArtifact = {
      ...BASE_BRIDGE_ARTIFACT,
      regions: [FLUID_REGION_HEALTHY, SOLID_REGION_NO_THERMO],
    };
    const slice = adaptBridgeArtifactToSlice(bridge);
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const ids = matches.map((m) => m.rule_id);
    expect(ids).toContain("PER_REGION_THERMO_MISSING_V9_R14");
  });

  it("R14 silent when BridgeArtifact has no regions field (pre-W3.2 payload)", () => {
    const bridge: BridgeArtifact = { ...BASE_BRIDGE_ARTIFACT };
    const slice = adaptBridgeArtifactToSlice(bridge);
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const ids = matches.map((m) => m.rule_id);
    expect(ids).not.toContain("PER_REGION_THERMO_MISSING_V9_R14");
  });

  it("all CHT rules silent when slice has regions=undefined (forward-compat gate)", () => {
    const slice: RunArtifactSlice = {
      run_id: "R-NO-REGIONS",
      case_id: "legacy",
      success: true,
      exit_code: 0,
      // regions: undefined (not set)
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const ids = matches.map((m) => m.rule_id);
    for (const rId of [
      "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
      "PER_REGION_THERMO_MISSING_V9_R14",
      "CONDUCTION_DOMINANCE_V9_R15",
      "FACE_ZONE_LOSS_V9_R16",
    ]) {
      expect(ids).not.toContain(rId);
    }
  });
});
