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

// NASA-convention reference_comparison tolerance per DEC-V61-209
// ADDENDUM 4 (lines 304-339) — mirrored verbatim in
// `flat_plate_cf.py::station_rel` gate (`station_rel <= tolerance`).
// Used by BOTH R10 (station-pass precondition) and R12 (PASS/FAIL XOR
// boundary) so the literal cannot drift between the two rules.
// Per Codex CRS R0 W2.1 R1 fix.
const NASA_TOL_PCT = 10.0;

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

  // W2.1 · DEC-V61-209 ADDENDUM 5 #2 distillation (DEC-V61-216).
  //
  // R10: HONEST KNOWN KNOWN. Fires only when the scalar gold-delta drift
  // (R4 amplitude floor crossed) is fully explained by the cataloged
  // near-LE OpenFOAM-kΩSST-vs-CFL3D formulation discrepancy:
  //   (1) gold_delta.max_abs_pct > 5%
  //   (2) developed_region_gold_delta.n_failures === 0
  //   (3) integrated_drag_pct.within_tolerance === true
  //   (4) reference_comparison_band_summary.n_near_le_deviations > 0
  //   (5) reference_comparison_band_summary.x_floor_m != null
  //
  // Honest None handling (DEC-V61-213/214/215 R1 carry-forward): any
  // required source field missing/null → return null. NEVER equate
  // null with 0, false, or empty.
  //
  // Inline accessor pattern (DEC-V61-215 R1 carry-forward / W9 helper
  // early-return guard): read each nested field directly instead of
  // routing through a helper that could short-circuit on a truthy
  // check (e.g. a helper returning [] when the array is empty would
  // mask a populated-but-empty case). Mirrors Python
  // _pred_known_deviation_pattern_near_le exactly.
  KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10: (slice) => {
    const gd = slice.gold_delta;
    const dr = slice.developed_region_gold_delta;
    const idp = slice.integrated_drag_pct;
    const rcs = slice.reference_comparison_band_summary;
    if (gd == null || dr == null || idp == null || rcs == null) return null;

    if (gd.max_abs_pct == null || gd.max_abs_pct <= 5.0) return null;
    if (dr.n_failures !== 0) return null;
    // Codex CRS R0 P2 R1 fix: NASA dual-metric gate is a paired
    // PASS/PASS contract — both integrated AND station must clear the
    // NASA_TOL_PCT=10.0 tolerance (inclusive boundary, matches
    // flat_plate_cf.py `station_rel <= tolerance`). Mirrors Python
    // `_pred_known_deviation_pattern_near_le`.
    if (idp.within_tolerance !== true) return null;
    if (idp.station_pct == null) return null;
    if (idp.station_pct > NASA_TOL_PCT) return null;
    if (rcs.n_near_le_deviations <= 0) return null;
    if (rcs.x_floor_m == null) return null;

    const n = rcs.n_near_le_deviations;
    const worst = rcs.worst_near_le_pct != null ? rcs.worst_near_le_pct : 0.0;
    return {
      matched_at: `near_le_known_dev_n${n}_worst${worst.toFixed(2)}pct`,
    };
  },

  // W2.1 · DEC-V61-209 ADDENDUM 5 #1 distillation (DEC-V61-216).
  //
  // R11: developed-region per-point FAILURE is qualitatively different
  // from scalar amplitude drift (R4). ADDENDUM 5 added
  // developed_region_min_m = 0.1 m as a THIRD-PASS condition because
  // integral-drag + a single verification station cannot reject a
  // curve whose +/- area errors cancel in the integral AND happens to
  // match at the one station.
  //
  // Firing predicate (mirrors Python _pred_developed_region_shape_mismatch):
  //   (1) developed_region_gold_delta is not null
  //   (2) n_failures > 0
  //   (3) max_abs_pct > 5.0  (discriminator floor matches R4 scalar)
  //
  // Polarity-paired with R10: when R10 short-circuits at
  // `n_failures !== 0`, R11 picks up the same slice.
  //
  // Inline accessor pattern — read fields directly, no helper.
  DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11: (slice) => {
    const dr = slice.developed_region_gold_delta;
    if (dr == null) return null;
    if (dr.n_failures <= 0) return null;
    if (dr.max_abs_pct == null || dr.max_abs_pct <= 5.0) return null;
    return {
      matched_at:
        `developed_region_failures_${dr.n_failures}of${dr.n_points}_` +
        `max${dr.max_abs_pct.toFixed(2)}pct`,
    };
  },

  // W3.1 · R13 COUPLED_INTERFACE_DANGLING_REF_V9_R13
  //
  // Detects a dangling coupled-interface reference at the region-inventory
  // level: a coupled boundary patch on a region declares a neighbour_region
  // that is absent from the assembled multi-region inventory.
  //
  // This is the slice-level shadow of the V94 death-chain — a coupled-patch
  // BC referencing a counterpart that does not resolve in the per-region
  // polyMesh → solver FATAL 'Cannot find patchField entry for
  // region_hot_fluid_to_domain0'.
  //
  // Logic: build the set of region names from slice.regions. For each
  // region's coupled_patches (skip if null/absent or empty), for each
  // CoupledPatch cp: if cp.neighbour_region is not null AND cp.neighbour_region
  // is NOT in the region-name set → FIRE (dangling reference).
  //
  // Mirrors Python _pred_coupled_interface_dangling_ref exactly (same field
  // reads, same branch order, same boundary operators, same matched_at template).
  //
  // KNOWN-GAP (negative contract — R13 will NOT fire when):
  //   (a) regions is null/absent — legacy/non-CHT scalar slice (graceful-skip).
  //   (b) regions === [] — region list present but empty; no inventory to check.
  //   (c) a region's coupled_patches is null/absent — not extracted.
  //   (d) a region's coupled_patches === [] — extraction found zero patches.
  //   (e) cp.neighbour_region is null/absent — neighbour not extracted; cannot judge.
  //   (f) a HEALTHY case where every cp.neighbour_region resolves to a region in
  //       the inventory — all refs resolve → silent.
  //   (g) the previously-false-firing two-independent-consistent-interfaces case:
  //       if each interface's neighbour regions are all present → silent.
  COUPLED_INTERFACE_DANGLING_REF_V9_R13: (slice) => {
    const regions = slice.regions;
    if (regions == null) return null;
    if (regions.length === 0) return null;

    // Build the region-name inventory set for O(1) membership checks.
    const regionNames = new Set(regions.map((r) => r.name));

    for (const region of regions) {
      const cps = region.coupled_patches;
      if (cps == null) continue; // not extracted
      if (!Array.isArray(cps) || cps.length === 0) continue; // empty
      for (const cp of cps) {
        if (cp.neighbour_region != null) {
          if (!regionNames.has(cp.neighbour_region)) {
            return {
              matched_at: `dangling_coupled_ref:${region.name}.${cp.patch_name}->${cp.neighbour_region}`,
            };
          }
        }
      }
    }
    return null;
  },

  // W3.1 · R14 PER_REGION_THERMO_MISSING_V9_R14
  //
  // A region is listed in the CHT inventory but carries NO per-region
  // thermophysical model payload (both thermo_type and thermo_snapshot_ref
  // are null/absent for the same region).
  //
  // Mirrors Python _pred_per_region_thermo_missing exactly.
  //
  // KNOWN-GAP (negative contract — R14 will NOT fire when):
  //   (a) regions is null/absent — legacy slice (graceful-skip).
  //   (b) regions === [] — no regions to check.
  //   (c) thermo_type is present (non-null string) — payload extracted;
  //       thermo_snapshot_ref being null is a decoupling artifact, not missing.
  PER_REGION_THERMO_MISSING_V9_R14: (slice) => {
    const regions = slice.regions;
    if (regions == null) return null;
    if (regions.length === 0) return null;

    for (const region of regions) {
      const ttMissing = region.thermo_type == null;
      const refMissing = region.thermo_snapshot_ref == null;
      if (ttMissing && refMissing) {
        return { matched_at: `region:${region.name}:thermo_missing` };
      }
    }
    return null;
  },

  // W3.1 · R15 CONDUCTION_DOMINANCE_V9_R15
  //
  // Conduction-dominated degenerate-physics topology: the CHT region inventory
  // contains ZERO resolvable fluid regions (n_fluid == 0, n_solid >= 1).
  //
  // Mirrors Python _pred_conduction_dominance exactly.
  //
  // KNOWN-GAP (negative contract — R15 will NOT fire when):
  //   (a) regions is null/absent — legacy slice (graceful-skip).
  //   (b) regions === [] — no regions to count.
  //   (c) region.kind === null — ambiguous classification; must be SKIPPED.
  //   (d) n_fluid >= 1 after skipping null-kind regions — healthy CHT.
  CONDUCTION_DOMINANCE_V9_R15: (slice) => {
    const regions = slice.regions;
    if (regions == null) return null;
    if (regions.length === 0) return null;

    let nFluid = 0;
    let nSolid = 0;
    for (const region of regions) {
      if (region.kind === null) continue; // ambiguous — skip, never guess
      if (region.kind === "fluid") nFluid++;
      else if (region.kind === "solid") nSolid++;
    }

    if (nFluid === 0 && nSolid >= 1) {
      return { matched_at: `n_fluid=0_n_solid=${nSolid}` };
    }
    return null;
  },

  // W3.1 · R16 FACE_ZONE_LOSS_V9_R16
  //
  // Face-zone / region-mesh loss XOR (CHT mirror of R12 PASS/FAIL XOR):
  // a region is declared (name present) but its sHM face-zone output ref
  // is absent (shm_snapshot_ref is null). Requires at least one region
  // WITH a ref before flagging those without (R12 half-data discipline).
  //
  // Mirrors Python _pred_face_zone_loss exactly.
  //
  // KNOWN-GAP (negative contract — R16 will NOT fire when):
  //   (a) regions is null/absent — legacy slice (graceful-skip).
  //   (b) regions === [] — no regions to cross-check.
  //   (c) shm_snapshot_ref is non-null — no XOR disagreement.
  //   (d) NO region has any shm ref (all null) — sHM stage skipped entirely;
  //       cannot distinguish from face-zone loss; graceful skip.
  FACE_ZONE_LOSS_V9_R16: (slice) => {
    const regions = slice.regions;
    if (regions == null) return null;
    if (regions.length === 0) return null;

    // Require at least one region WITH a ref before flagging any without.
    const anyRefPresent = regions.some((r) => r.shm_snapshot_ref != null);
    if (!anyRefPresent) return null;

    for (const region of regions) {
      if (region.shm_snapshot_ref == null) {
        return {
          matched_at: `region:${region.name}:declared_no_shm_snapshot`,
        };
      }
    }
    return null;
  },

  // W2.1 · DEC-V61-209 ADDENDUM 4 distillation (DEC-V61-216).
  //
  // R12: NASA-convention dual-metric XOR. When integrated-Cf drag and
  // Cf@x=0.97008 station DISAGREE on PASS/FAIL at the same 10%
  // tolerance, the divergence itself is a citable finding pattern —
  // typically a post-processing / integration-pipeline bug rather
  // than a CFD issue (DEC-V61-209 lines 226-231: stale time-dir →
  // station-right, integration-wrong).
  //
  // Predicate is strict PASS/FAIL XOR at NASA_TOL_PCT=10.0. The same
  // literal is mirrored in Python (no config-file indirection;
  // cross-language parity by construction).
  //
  // Inline accessor pattern — read fields directly, no helper.
  INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12: (slice) => {
    const idp = slice.integrated_drag_pct;
    if (idp == null) return null;
    if (idp.station_pct == null) return null;

    // Codex CRS R0 P3 R1 fix: NASA gate is `<=` not `<` (matches
    // flat_plate_cf.py `station_rel <= tolerance`). A slice with
    // station_pct == 10.0 is IN tolerance (PASSES). Module-level
    // NASA_TOL_PCT shared with R10 so the literal cannot drift.
    const integratedPasses = Boolean(idp.within_tolerance);
    const stationPasses = idp.station_pct <= NASA_TOL_PCT;

    // XOR — exactly one metric passes.
    if (integratedPasses === stationPasses) return null;

    return {
      matched_at:
        `integrated_drag_${idp.pct.toFixed(2)}pct_` +
        `vs_station_${idp.station_pct.toFixed(2)}pct`,
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
