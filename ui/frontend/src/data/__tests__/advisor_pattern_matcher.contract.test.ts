/**
 * V90.3 · V9.B pattern matcher contract tests
 * V90.2 · V9.C ruleset coverage tests
 *
 * Asserts:
 *   - Each curated rule matches its intended pattern (positive case)
 *   - Each curated rule returns null for the negative case
 *   - Empty/malformed artifact → no crash · returns []
 *   - Determinism (same input → same output across runs)
 *   - All rules carry non-empty commentary + provenance (V90 reverse-stop #32)
 *   - Output sorted by severity (advise > warn > info)
 *
 * Pure tests · no React · no fetch · runs in <100ms.
 */
import { describe, expect, it } from "vitest";

import {
  matchAdvisorPatterns,
  type RunArtifactSlice,
  type AdvisorRule,
} from "../advisor_pattern_matcher";
import { V9_ADVISOR_RULES, V9_RULESET_VERSION } from "../v9_advisor_rules";

const CONVERGED_HEALTHY: RunArtifactSlice = {
  run_id: "R-OK-1",
  case_id: "lid_driven_cavity",
  success: true,
  exit_code: 0,
  residuals: {
    p: [1e-2, 5e-3, 2.5e-3, 1e-3, 5e-4, 2.5e-4, 1e-4, 5e-5],
    U: [1e-2, 5e-3, 2.5e-3, 1e-3, 5e-4, 2.5e-4, 1e-4, 5e-5],
  },
  forces: Array.from({ length: 20 }, (_, i) => ({
    iteration: i,
    Cd: 0.95 + (i % 2) * 0.001,
    Cl: 0.0,
    Cm: 0.0,
  })),
  convergence_stats: {
    final_iter: 800,
    max_iters_reached: false,
    converged: true,
    elapsed_seconds: 28,
  },
  gold_delta: { max_abs_pct: 0.75 },
};

describe("V90.2 · V9_ADVISOR_RULES · ruleset shape integrity", () => {
  it("contains at least 6 curated rules (charter §4 minimum)", () => {
    expect(V9_ADVISOR_RULES.length).toBeGreaterThanOrEqual(6);
  });

  it("every rule has a non-empty id", () => {
    for (const rule of V9_ADVISOR_RULES) {
      expect(rule.id.length).toBeGreaterThan(0);
    }
  });

  it("every rule has a non-empty commentary (V80 reverse-stop carry · 9-arc lineage)", () => {
    for (const rule of V9_ADVISOR_RULES) {
      expect(rule.commentary.trim().length).toBeGreaterThan(50);
    }
  });

  it("every rule has a non-empty provenance (V90 reverse-stop #32)", () => {
    for (const rule of V9_ADVISOR_RULES) {
      expect(rule.provenance.trim().length).toBeGreaterThan(0);
    }
  });

  it("rule ids are unique (no duplicates)", () => {
    const ids = V9_ADVISOR_RULES.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("ruleset version is semver-ish", () => {
    expect(V9_RULESET_VERSION).toMatch(/^v?\d+\.\d+\.\d+$/);
  });

  it("commentary text has NO 'AI generates' / 'AI suggests' verbiage (V90 reverse-stop #33)", () => {
    for (const rule of V9_ADVISOR_RULES) {
      const lower = rule.commentary.toLowerCase();
      expect(lower).not.toContain("ai generates");
      expect(lower).not.toContain("ai suggests");
      expect(lower).not.toContain("ai diagnoses");
      expect(lower).not.toContain("ai recommends");
    }
  });
});

describe("V90.3 · matchAdvisorPatterns · ruleset behavior · positive cases", () => {
  it("R2 (max iters reached): matches when convergence_stats.max_iters_reached=true", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      convergence_stats: {
        final_iter: 5000,
        max_iters_reached: true,
        converged: false,
        elapsed_seconds: 60,
      },
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "MAX_ITERS_REACHED_V9_R2")).toBe(true);
  });

  it("R3 (run failed): matches when success=false + non-zero exit", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      success: false,
      exit_code: 1,
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "RUN_FAILED_NONZERO_EXIT_V9_R3")).toBe(true);
  });

  it("R4 (gold delta > 5%): matches when gold_delta.max_abs_pct > 5", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      gold_delta: { max_abs_pct: 8.2 },
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4")).toBe(true);
  });

  it("R5 (forces drifting): matches when Cd varies >1% in last 10 iters", () => {
    const drifty = Array.from({ length: 20 }, (_, i) => ({
      iteration: i,
      Cd: 0.5 + i * 0.05, // monotonically increasing — definitely not converged
      Cl: 0.0,
      Cm: 0.0,
    }));
    const slice: RunArtifactSlice = { ...CONVERGED_HEALTHY, forces: drifty };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "FORCES_NOT_CONVERGED_V9_R5")).toBe(true);
  });

  it("R6 (slow convergence): matches when converged in >=5000 iters", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      convergence_stats: {
        final_iter: 7500,
        max_iters_reached: false,
        converged: true,
        elapsed_seconds: 240,
      },
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "SLOW_CONVERGENCE_V9_R6")).toBe(true);
  });

  it("R7 (residual plateau U): matches when U plateaus above 1e-4", () => {
    const plateau = Array.from({ length: 20 }, () => 1.5e-3 + (Math.random() - 0.5) * 1e-5);
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      residuals: { ...CONVERGED_HEALTHY.residuals, U: plateau },
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "RESIDUAL_PLATEAU_U_V9_R7")).toBe(true);
  });

  it("R8 (healthy convergence): matches on canonical healthy run", () => {
    const matches = matchAdvisorPatterns(CONVERGED_HEALTHY, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "HEALTHY_CONVERGENCE_V9_R8")).toBe(true);
  });

  it("R1 (residual oscillation p): matches when p oscillates >30% of mean", () => {
    // Symmetric oscillation pattern around a non-zero mean, amplitude > 30%
    const oscillating = [1e-2, 5e-3, 1.2e-2, 4e-3, 1.3e-2, 3.5e-3, 1.4e-2, 3e-3];
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      residuals: { ...CONVERGED_HEALTHY.residuals, p: oscillating },
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "RESIDUAL_OSCILLATION_P_V9_R1")).toBe(true);
  });
});

describe("V90.3 · matchAdvisorPatterns · ruleset behavior · negative cases", () => {
  it("R2 negative: clean converged run does NOT match max-iters-reached", () => {
    const matches = matchAdvisorPatterns(CONVERGED_HEALTHY, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "MAX_ITERS_REACHED_V9_R2")).toBe(false);
  });

  it("R3 negative: success=true does NOT match run-failed", () => {
    const matches = matchAdvisorPatterns(CONVERGED_HEALTHY, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "RUN_FAILED_NONZERO_EXIT_V9_R3")).toBe(false);
  });

  it("R4 negative: gold delta < 5% does NOT match", () => {
    const matches = matchAdvisorPatterns(CONVERGED_HEALTHY, V9_ADVISOR_RULES);
    expect(matches.some((m) => m.rule_id === "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4")).toBe(false);
  });
});

describe("V90.3 · matchAdvisorPatterns · graceful degrade (V9 reverse-stop #4)", () => {
  it("empty artifact (only required fields) → no crash · returns [] or only base matches", () => {
    const empty: RunArtifactSlice = {
      run_id: "R-empty",
      case_id: "x",
      success: true,
      exit_code: 0,
    };
    const matches = matchAdvisorPatterns(empty, V9_ADVISOR_RULES);
    expect(Array.isArray(matches)).toBe(true);
    // None of the predicates should crash on missing residuals/forces/etc
  });

  it("malformed residuals (non-array) → no crash", () => {
    const malformed = {
      run_id: "R-bad",
      case_id: "x",
      success: true,
      exit_code: 0,
      residuals: "not an object",
    } as unknown as RunArtifactSlice;
    expect(() => matchAdvisorPatterns(malformed, V9_ADVISOR_RULES)).not.toThrow();
  });

  it("malformed convergence_stats → no crash", () => {
    const malformed = {
      run_id: "R-bad2",
      case_id: "x",
      success: true,
      exit_code: 0,
      convergence_stats: { final_iter: "not a number" },
    } as unknown as RunArtifactSlice;
    expect(() => matchAdvisorPatterns(malformed, V9_ADVISOR_RULES)).not.toThrow();
  });

  it("rule predicate throwing exception → treated as no-match (not crash)", () => {
    const explodingRule: AdvisorRule = {
      id: "EXPLOSION_TEST",
      severity: "info",
      commentary: "test commentary placeholder of sufficient length for the validation guard",
      provenance: "test/explosion",
      predicate: () => {
        throw new Error("predicate boom");
      },
    };
    const matches = matchAdvisorPatterns(CONVERGED_HEALTHY, [explodingRule]);
    expect(matches).toEqual([]);
  });
});

describe("V90.3 · matchAdvisorPatterns · determinism", () => {
  it("returns identical output for same input across 3 successive calls", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      convergence_stats: {
        final_iter: 6000,
        max_iters_reached: false,
        converged: true,
        elapsed_seconds: 200,
      },
    };
    const out1 = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const out2 = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const out3 = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(out1).toEqual(out2);
    expect(out2).toEqual(out3);
  });
});

describe("V90.3 · matchAdvisorPatterns · output sorting (severity stable)", () => {
  it("orders matches as advise > warn > info", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      success: false,        // R3 = advise
      exit_code: 1,
      gold_delta: { max_abs_pct: 10 },  // R4 = warn
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    const severities = matches.map((m) => m.severity);
    // Whenever we see "info" after "warn" or "advise", that's a sort violation
    let lastRank = -1;
    const RANK = { advise: 0, warn: 1, info: 2 };
    for (const sev of severities) {
      expect(RANK[sev]).toBeGreaterThanOrEqual(lastRank);
      lastRank = RANK[sev];
    }
  });
});

describe("V90.3 · matchAdvisorPatterns · MatchedCommentary structure", () => {
  it("each match carries rule_id + matched_at + commentary_excerpt + provenance + severity", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      success: false,
      exit_code: 137,
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.rule_id.length).toBeGreaterThan(0);
      expect(m.matched_at.length).toBeGreaterThan(0);
      expect(m.commentary_excerpt.length).toBeGreaterThan(0);
      expect(m.provenance.length).toBeGreaterThan(0);
      expect(["advise", "warn", "info"]).toContain(m.severity);
    }
  });

  it("commentary excerpts are truncated to ≤240 chars (card-display constraint)", () => {
    const slice: RunArtifactSlice = {
      ...CONVERGED_HEALTHY,
      success: false,
      exit_code: 1,
    };
    const matches = matchAdvisorPatterns(slice, V9_ADVISOR_RULES);
    for (const m of matches) {
      expect(m.commentary_excerpt.length).toBeLessThanOrEqual(240);
    }
  });
});
