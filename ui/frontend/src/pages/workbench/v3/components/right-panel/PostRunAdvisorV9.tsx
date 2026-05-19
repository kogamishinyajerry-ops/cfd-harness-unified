/**
 * V90.4 · V9.A PostRunAdvisorV9 · post-run pattern-matching advisor surface
 *
 * Per .planning/blueprints/v9/INDEX.md Contract V9.A:
 *   - Pure presentational · NO useEffect that fires fetch · NO LLM call
 *   - Mounts inside AdvisorContent when a completed runId is available
 *   - Renders MatchedCommentary cards from props (parent supplies the
 *     matches via V9.B matcher run against V9.C ruleset)
 *   - Empty-state graceful when matches=[] · NOT crash · NOT error
 *   - Honest framing: section header "Curated diagnostic patterns" ·
 *     denylist: NO "AI generates" / "AI suggests" / "AI diagnoses"
 *
 * V130 invariant honored BY CONSTRUCTION: this component imports NO
 * LLM endpoint · no `/ai-review`, `/ai-diagnose`, `streamAICoach`. The
 * "advisor" is human-curated rule matching against real artifacts ·
 * complementary to (not replacing) the existing LLM-dependent paths.
 *
 * V90 reverse-stops enforced:
 *   #31 NO LLM call (literal-source absence enforced by contract test)
 *   #33 Honest framing (lexical denylist test)
 *   #34 Empty-state graceful
 */

import type { MatchedCommentary } from "@/data/advisor_pattern_matcher";

interface PostRunAdvisorV9Props {
  caseId: string | null;
  /** Completed run_id from V7.D handoff · null when no run completed yet. */
  runId: string | null;
  /** Matches from V9.B pattern matcher · parent computes from artifact + ruleset. */
  matches: MatchedCommentary[];
  /** Ruleset version (for audit-trail rendering in the footer). */
  rulesetVersion: string;
}

const SEVERITY_CHIP_CLASS: Record<
  MatchedCommentary["severity"],
  string
> = {
  advise:
    "text-[9px] font-mono uppercase tracking-[0.08em] px-1.5 py-0.5 rounded border border-v3-danger text-v3-danger",
  warn:
    "text-[9px] font-mono uppercase tracking-[0.08em] px-1.5 py-0.5 rounded border border-v3-accent text-v3-accent",
  info:
    "text-[9px] font-mono uppercase tracking-[0.08em] px-1.5 py-0.5 rounded border border-v3-border text-v3-textSecondary",
};

export function PostRunAdvisorV9({
  caseId,
  runId,
  matches,
  rulesetVersion,
}: PostRunAdvisorV9Props) {
  const hasRun = runId != null && runId.length > 0;
  const hasMatches = matches.length > 0;

  return (
    <section
      data-testid="post-run-advisor-v9"
      data-case-id={caseId ?? "__none__"}
      data-run-id={runId ?? "__none__"}
      data-match-count={String(matches.length)}
      data-ruleset-version={rulesetVersion}
      aria-label="Curated diagnostic patterns"
      className="flex flex-col gap-2 border-t border-v3-border pt-3 mt-3"
    >
      <header className="flex items-baseline justify-between">
        <h3
          data-testid="post-run-advisor-v9-heading"
          className="text-[11px] font-mono uppercase tracking-[0.08em] text-v3-textSecondary"
        >
          Curated diagnostic patterns
        </h3>
        <span
          data-testid="post-run-advisor-v9-ruleset-version"
          className="text-[9px] font-mono text-v3-textTertiary"
        >
          ruleset {rulesetVersion}
        </span>
      </header>

      {!hasRun && (
        <p
          data-testid="post-run-advisor-v9-empty-no-run"
          className="text-[11px] font-mono text-v3-textTertiary leading-relaxed"
        >
          no completed run yet · run a case to see structured diagnostic
          commentary keyed to real artifacts
        </p>
      )}

      {hasRun && !hasMatches && (
        <p
          data-testid="post-run-advisor-v9-empty-no-matches"
          className="text-[11px] font-mono text-v3-textTertiary leading-relaxed"
        >
          no matched patterns for this run · residuals, forces, and
          convergence stats all look unremarkable against the curated
          ruleset
        </p>
      )}

      {hasRun && hasMatches && (
        <ul
          data-testid="post-run-advisor-v9-card-list"
          className="flex flex-col gap-2"
        >
          {matches.map((m) => (
            <li
              key={m.rule_id}
              data-testid={`post-run-advisor-v9-card-${m.rule_id}`}
              data-severity={m.severity}
              data-matched-at={m.matched_at}
              className="border border-v3-border rounded p-2 flex flex-col gap-1 bg-v3-panel"
            >
              <header className="flex items-center justify-between gap-2">
                <span
                  data-testid={`post-run-advisor-v9-card-${m.rule_id}-id`}
                  className="text-[10px] font-mono text-v3-textPrimary"
                >
                  {m.rule_id}
                </span>
                <span
                  data-testid={`post-run-advisor-v9-card-${m.rule_id}-severity`}
                  className={SEVERITY_CHIP_CLASS[m.severity]}
                >
                  {m.severity}
                </span>
              </header>
              <p
                data-testid={`post-run-advisor-v9-card-${m.rule_id}-excerpt`}
                className="text-[11px] font-mono text-v3-textSecondary leading-relaxed"
              >
                {m.commentary_excerpt}
              </p>
              <footer className="flex items-center justify-between gap-2">
                <span
                  data-testid={`post-run-advisor-v9-card-${m.rule_id}-matched-at`}
                  className="text-[9px] font-mono text-v3-textTertiary"
                >
                  matched at: {m.matched_at}
                </span>
                <span
                  data-testid={`post-run-advisor-v9-card-${m.rule_id}-provenance`}
                  className="text-[9px] font-mono text-v3-textTertiary"
                >
                  source: {m.provenance}
                </span>
              </footer>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
