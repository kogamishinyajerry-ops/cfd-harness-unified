/**
 * V90.2 / V91.1 · V9.C Curated diagnostic commentary ruleset
 *
 * Per .planning/blueprints/v9/INDEX.md Contract V9.C:
 *   - Every rule: id · predicate · commentary · provenance · severity
 *   - `provenance` MUST be non-empty (V90 reverse-stop #32)
 *
 * V91.1 split:
 *   - Commentary + provenance + severity + id live in
 *     `v9_advisor_rules.json` (JSON SSOT shared with the Python matcher
 *     in `ui/backend/services/v9_advisor/`)
 *   - Predicate functions stay here (TS-native lambdas)
 *   - This file joins the two halves by id
 *
 * Reverse-stops honored:
 *   - #32 (provenance non-empty) — validated by buildRules()
 *   - #37 (JSON canonical) — backend Python contract test enforces
 *   - #38 (cross-language parity) — Python matcher uses same JSON + same
 *     predicate semantics → identical MatchedCommentary output
 *
 * V130 invariant honored BY CONSTRUCTION: this file is text + lambdas ·
 * NO LLM call · NO fetch · NO IO. Every commentary string is human-authored.
 */

import type {
  AdvisorRule,
  RunArtifactSlice,
} from "./advisor_pattern_matcher";
import rulesCorpus from "./v9_advisor_rules.json";

interface JsonRule {
  id: string;
  severity: "advise" | "warn" | "info";
  commentary: string;
  provenance: string;
}

interface JsonCorpus {
  version: string;
  rules: JsonRule[];
}

const corpus = rulesCorpus as JsonCorpus;

export const V9_RULESET_VERSION = corpus.version;

function recentResiduals(
  slice: RunArtifactSlice,
  quantity: string,
  count: number,
): number[] {
  const history = slice.residuals?.[quantity];
  if (!Array.isArray(history) || history.length < count) return [];
  return history.slice(-count);
}

function isMonotonicallyDecreasing(values: number[]): boolean {
  if (values.length < 2) return false;
  for (let i = 1; i < values.length; i++) {
    if (values[i] >= values[i - 1]) return false;
  }
  return true;
}

function isMonotonicallyIncreasing(values: number[]): boolean {
  if (values.length < 2) return false;
  for (let i = 1; i < values.length; i++) {
    if (values[i] <= values[i - 1]) return false;
  }
  return true;
}

function isOscillating(values: number[], thresholdRatio: number): boolean {
  if (values.length < 4) return false;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const meanMag = Math.abs(mean);
  if (meanMag === 0) return false;

  let signFlips = 0;
  let maxAmplitudeRatio = 0;
  for (let i = 1; i < values.length; i++) {
    const prev = values[i - 1] - mean;
    const curr = values[i] - mean;
    if (Math.sign(prev) !== Math.sign(curr) && Math.sign(curr) !== 0) {
      signFlips++;
    }
    maxAmplitudeRatio = Math.max(
      maxAmplitudeRatio,
      Math.abs(values[i] - mean) / meanMag,
    );
  }
  return signFlips >= 2 && maxAmplitudeRatio > thresholdRatio;
}

type PredicateFn = AdvisorRule["predicate"];

const PREDICATES_BY_ID: Record<string, PredicateFn> = {
  RESIDUAL_OSCILLATION_P_V9_R1: (slice) => {
    const last8 = recentResiduals(slice, "p", 8);
    if (last8.length < 8) return null;
    if (!isOscillating(last8, 0.3)) return null;
    return {
      matched_at: `iter_${(slice.convergence_stats?.final_iter ?? last8.length).toString()}_p_residual`,
    };
  },

  MAX_ITERS_REACHED_V9_R2: (slice) => {
    if (!slice.convergence_stats?.max_iters_reached) return null;
    return { matched_at: "convergence_stats" };
  },

  RUN_FAILED_NONZERO_EXIT_V9_R3: (slice) => {
    if (slice.success !== false) return null;
    if (slice.exit_code === 0) return null;
    return { matched_at: `exit_code_${slice.exit_code}` };
  },

  GOLD_DELTA_EXCEEDS_5_PCT_V9_R4: (slice) => {
    const pct = slice.gold_delta?.max_abs_pct;
    if (pct == null) return null;
    if (pct <= 5) return null;
    return { matched_at: `gold_delta_${pct.toFixed(2)}pct` };
  },

  FORCES_NOT_CONVERGED_V9_R5: (slice) => {
    const forces = slice.forces;
    if (!Array.isArray(forces) || forces.length < 10) return null;
    const last10 = forces.slice(-10);
    const cds = last10.map((f) => f.Cd);
    const cdMean = cds.reduce((a, b) => a + b, 0) / cds.length;
    if (Math.abs(cdMean) < 1e-9) return null;
    const maxDriftPct =
      Math.max(...cds.map((cd) => Math.abs((cd - cdMean) / cdMean))) * 100;
    if (maxDriftPct <= 1) return null;
    return { matched_at: `forces_drift_${maxDriftPct.toFixed(2)}pct` };
  },

  SLOW_CONVERGENCE_V9_R6: (slice) => {
    const final = slice.convergence_stats?.final_iter;
    const converged = slice.convergence_stats?.converged;
    if (!converged) return null;
    if (final == null || final < 5000) return null;
    return { matched_at: `iter_${final}_slow_converge` };
  },

  RESIDUAL_PLATEAU_U_V9_R7: (slice) => {
    const last20 = recentResiduals(slice, "U", 20);
    if (last20.length < 20) return null;
    const mean = last20.reduce((a, b) => a + b, 0) / last20.length;
    const meanMag = Math.abs(mean);
    if (meanMag < 1e-12) return null;
    const variance =
      last20.reduce((a, v) => a + (v - mean) ** 2, 0) / last20.length;
    const stdDev = Math.sqrt(variance);
    const variationPct = (stdDev / meanMag) * 100;
    if (variationPct >= 2 || meanMag < 1e-4) return null;
    return { matched_at: `U_plateau_${meanMag.toExponential(2)}` };
  },

  HEALTHY_CONVERGENCE_V9_R8: (slice) => {
    if (!slice.convergence_stats?.converged) return null;
    const last8 = recentResiduals(slice, "p", 8);
    if (last8.length < 8) return null;
    if (!isMonotonicallyDecreasing(last8)) return null;
    return { matched_at: "healthy_convergence_p" };
  },

  // Divergence (blow-up): p residual climbing monotonically AND past O(1).
  // Normalized residuals start ~1.0 and fall when converging, so a residual
  // increasing past 1.0 is unambiguous divergence. Distinct from R1
  // (oscillation) / R7 (plateau) / R2 (max-iters) / R3 (nonzero-exit crash —
  // divergence can happen without a crash).
  //
  // Window: opportunistic up to 4 samples — fires as soon as ≥2 consecutive
  // samples exist and the pattern holds. Cadence Codex 2026-05-29 (CRS) caught
  // that the prior strict-4 requirement missed the V3-class fast blow-up the
  // docstring claimed to cover (V3 iter-3 = 3 samples; strict-4 never fired on
  // its own target). Relaxed to ≥2 + monotonic + final>1.0; >1.0 floor still
  // guards startup transients.
  //
  // KNOWN-GAP: V6 first-iter mass-flow-zero-IC = 1 sample only; a single
  // residual at O(1) cannot be told apart from a normal startup transient.
  // R3 (nonzero-exit) catches V6 when the case dies; remaining V6 gap is
  // tracked in retro 2026-05-29 cadence_codex_r1 (slice-extension follow-up).
  //
  // Mirrors Python _pred_residual_divergence. Both bindings inline the history
  // access (the shared recentResiduals helper returns [] when length<count,
  // which is the prior bug; do NOT route this rule through that helper).
  RESIDUAL_DIVERGENCE_V9_R9: (slice) => {
    const history = slice.residuals?.["p"];
    if (!Array.isArray(history)) return null;
    const recent = history.slice(-4);
    if (recent.length < 2) return null;
    if (!isMonotonicallyIncreasing(recent)) return null;
    if (recent[recent.length - 1] <= 1.0) return null;
    return {
      matched_at: `iter_${(slice.convergence_stats?.final_iter ?? recent.length).toString()}_p_divergence`,
    };
  },
};

function buildRules(): readonly AdvisorRule[] {
  return corpus.rules.map((r) => {
    const predicate = PREDICATES_BY_ID[r.id];
    if (!predicate) {
      throw new Error(
        `V91.1 join error: JSON rule id "${r.id}" has no matching TS predicate`,
      );
    }
    if (!r.provenance || r.provenance.length === 0) {
      throw new Error(
        `V90 RS#32: rule "${r.id}" has empty provenance`,
      );
    }
    return {
      id: r.id,
      severity: r.severity,
      commentary: r.commentary,
      provenance: r.provenance,
      predicate,
    };
  });
}

export const V9_ADVISOR_RULES: readonly AdvisorRule[] = buildRules();
