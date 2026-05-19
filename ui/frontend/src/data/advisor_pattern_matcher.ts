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
