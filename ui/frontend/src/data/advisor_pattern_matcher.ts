/**
 * V90.3 · V9.B Pattern matcher · pure function
 *
 * Per .planning/blueprints/v9/INDEX.md Contract V9.B:
 *   - Pure function · no I/O · no fetch · no LLM · deterministic
 *   - Reads run artifact slice + curated ruleset → emits MatchedCommentary[]
 *   - Same inputs → same outputs always
 *   - Returns sorted by severity (advise > warn > info) for stable rendering
 *   - V130 invariant honored BY CONSTRUCTION (no LLM call to gate)
 *
 * Used by V9.A PostRunAdvisorV9 to populate matched-commentary cards
 * after a run completes (V7.D handoff supplies the run_id, the React
 * Query for run-history/run-detail provides the artifact slice).
 */

export interface RunArtifactSlice {
  run_id: string;
  case_id: string;
  success: boolean;
  exit_code: number;
  /** Per-quantity residual history (array of values, one per iter). */
  residuals?: Record<string, number[]>;
  /** Per-iter force coefficients. */
  forces?: { iteration: number; Cd: number; Cl: number; Cm: number }[];
  convergence_stats?: {
    final_iter: number;
    max_iters_reached: boolean;
    converged: boolean;
    elapsed_seconds: number;
  };
  /** V81-vintage gold-vs-actual comparison summary. */
  gold_delta?: { max_abs_pct: number };

  // ──────────────────────────────────────────────────────────────────────
  // W2.0.6 · DEC-V61-209 NASA-convention regional fields
  // (Python parity: see ui/backend/services/v9_advisor/pattern_matcher.py
  //  RunArtifactSlice — DevelopedRegionGoldDelta / IntegratedDragPct /
  //  ReferenceBandSummary nested dataclasses.)
  //
  // Source: trust_report.json gates.reference_comparison.details — only
  // populated by the deriver when details.gate_mode == 'nasa_integrated'.
  // Per_point gate cases + legacy manifests + empty fixtures leave these
  // undefined (graceful-skip, not partial).
  //
  // Scope: data-shape only. No current V9 predicate (R1–R9) reads these
  // fields. They sit in the slice as ADVISORY DATA AVAILABLE TO FUTURE
  // PREDICATES — W2.1 will distill regional rules (e.g. distinguish
  // global-delta-but-only-near-LE from delta-everywhere) keyed on
  // reference_comparison_band_summary + developed_region_gold_delta.
  //
  // Truth-chain (every field traces verbatim to cfdtrust qoi.py output;
  // no fabrication, no LLM inference):
  //   - developed_region_gold_delta ← details.developed_region.{max_rel_error*100,
  //     n_failures, n_points, developed_region_min_m}
  //   - integrated_drag_pct ← details.integrated_drag.{rel_error*100,
  //     within_tolerance} + details.verification_station.rel_error*100
  //   - reference_comparison_band_summary ← details.{n_known_deviations,
  //     max(known_deviations[].rel_error)*100, developed_region.developed_region_min_m}
  // ──────────────────────────────────────────────────────────────────────

  /**
   * W2.0.6 · Regional analog to scalar `gold_delta.max_abs_pct`. Scoped to
   * the developed-region band (x ≥ `min_x_m`) so a future W2.1 predicate
   * can distinguish near-LE noise from genuine shape failures.
   * Optional · undefined for per_point gate mode + empty fixtures.
   */
  developed_region_gold_delta?: {
    /** max(|rel_error|) over developed-region rows, as percentage. */
    max_abs_pct: number;
    /** Count of rows exceeding tolerance in the developed region. */
    n_failures: number;
    /** Total rows compared in the developed region. */
    n_points: number;
    /** Lower x-bound (metres) defining the developed-region scope. */
    min_x_m: number;
  };

  /**
   * W2.0.6 · NASA-convention metric introduced by DEC-V61-209 ADDENDUM 4.
   * Pairs the global integrated-Cf drag % with the verification-station
   * Cf % (NASA-canonical pointwise sanity check companion).
   * Optional · undefined for per_point gate mode + empty fixtures.
   */
  integrated_drag_pct?: {
    /** Integrated-drag relative error, as percentage. */
    pct: number;
    /** PASS/FAIL on the integrated-drag tolerance (DEC-V61-209 untouchable). */
    within_tolerance: boolean;
    /** Verification-station Cf relative error, as percentage. Absent when station missing. */
    station_pct?: number;
  };

  /**
   * W2.0.6 · Near-LE band rollup. Lets a future W2.1 rule predicate
   * recognise the DEC-V61-209 ADDENDUM 5 #2 "known-deviation" pattern
   * (high pointwise rel_error only at x < developed_region_min_m).
   * Optional · undefined for per_point gate mode + empty fixtures.
   */
  reference_comparison_band_summary?: {
    /** Count of pointwise rows flagged as near-LE (x < x_floor_m). */
    n_near_le_deviations: number;
    /** max(rel_error)*100 over near-LE deviations. Absent when n_near_le_deviations == 0. */
    worst_near_le_pct?: number;
    /**
     * Boundary used to scope near-LE (metres, mirrors developed_region_min_m).
     * OPTIONAL (cadence Codex R1 · 2026-05-30 CRS P2 #2): NASA-integrated
     * gate schema does NOT require developed_region_min_m; flat_plate_cf.py
     * omits details.developed_region when no developed-region guard is
     * configured. In that case x_floor_m stays absent rather than being
     * fabricated as 0.0 (which would silently relabel "cutoff unknown" as
     * "cutoff at the leading edge" — a truth-chain violation).
     */
    x_floor_m?: number;
  };
}

export type MatchSeverity = "info" | "warn" | "advise";

export interface MatchSite {
  matched_at: string;
}

export interface AdvisorRule {
  id: string;
  severity: MatchSeverity;
  /** Human-curated paragraph (V90 reverse-stop #33 honest framing). */
  commentary: string;
  /** V-series link or CFD textbook citation (V90 reverse-stop #32). */
  provenance: string;
  /**
   * Pure predicate · returns the match site when triggered, null otherwise.
   * MUST NOT have side effects · MUST NOT call fetch/IO/LLM.
   */
  predicate: (slice: RunArtifactSlice) => MatchSite | null;
}

export interface MatchedCommentary {
  rule_id: string;
  matched_at: string;
  commentary_excerpt: string;
  provenance: string;
  severity: MatchSeverity;
}

const SEVERITY_RANK: Record<MatchSeverity, number> = {
  advise: 0,
  warn: 1,
  info: 2,
};

/**
 * Match a run artifact against the curated ruleset. Pure · deterministic ·
 * runs in <5ms for typical artifact sizes.
 */
export function matchAdvisorPatterns(
  slice: RunArtifactSlice,
  rules: readonly AdvisorRule[],
): MatchedCommentary[] {
  const matched: MatchedCommentary[] = [];

  for (const rule of rules) {
    let site: MatchSite | null = null;
    try {
      site = rule.predicate(slice);
    } catch {
      // V90 reverse-stop carry: matcher MUST NOT crash on malformed
      // artifact. Treat predicate exceptions as no-match · skip.
      site = null;
    }
    if (site == null) continue;

    matched.push({
      rule_id: rule.id,
      matched_at: site.matched_at,
      // Truncate commentary excerpt to first 240 chars for card display;
      // full text accessed via provenance link.
      commentary_excerpt:
        rule.commentary.length > 240
          ? rule.commentary.slice(0, 237) + "…"
          : rule.commentary,
      provenance: rule.provenance,
      severity: rule.severity,
    });
  }

  // Stable sort: advise > warn > info, then by rule_id for tie-breaks.
  matched.sort((a, b) => {
    const rankDiff = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (rankDiff !== 0) return rankDiff;
    return a.rule_id.localeCompare(b.rule_id);
  });

  return matched;
}
