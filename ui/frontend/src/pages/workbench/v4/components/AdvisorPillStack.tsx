/**
 * V4 · AdvisorPillStack · industrial-minimalist replacement for V9.A
 * PostRunAdvisorV9 verbose-card UI.
 *
 * Consumes the SAME data contract as V3 (V91 matcher output) — no schema
 * change. Replaces the visual presentation only.
 *
 * Pill shape (collapsed):
 *   • severity dot · 1-line title (summarized from commentary) · expand button
 *
 * Pill shape (expanded):
 *   • severity dot · title · collapse button
 *   • full commentary paragraph (advisor-not-driver framing)
 *   • provenance link · matched_at chip
 *
 * 4Q gate honored by construction:
 *   - LLM offline: pure-presentational · matches computed upstream
 *     by pure matcher · no LLM endpoint imported here
 *   - Artifacts: provenance + matched_at carried per pill
 *   - TrustGate: no mutation surface · no apply/submit/run buttons
 *   - Advisory only: microcopy banner + denylist (no "AI suggests/diagnoses")
 *
 * V90 reverse-stops carried forward from PostRunAdvisorV9:
 *   #31 NO LLM call (literal-source absence)
 *   #33 Honest framing (lexical denylist)
 *   #34 Empty-state graceful
 */
import { useState } from "react";

import type { MatchedCommentary } from "@/data/advisor_pattern_matcher";
import { V4_SEVERITY_COLOR } from "@/theme/industrial_minimalist";

interface AdvisorPillStackProps {
  /** V91 matcher output · parent computes via `matchAdvisorPatterns`. */
  matches: MatchedCommentary[];
  /** Completed run_id this pill stack reflects · null when no run yet. */
  runId: string | null;
  /** Ruleset version (for audit footer). */
  rulesetVersion: string;
  /** Optional loading flag · parent indicates fetch in flight. */
  isLoading?: boolean;
}

/** Derive a 1-line summary from full commentary for pill collapsed state. */
function summarizeForPill(commentary: string): string {
  // Cut at first sentence (Chinese period / English period / exclamation /
  // question / line break). Fallback to first 50 chars + ellipsis.
  const match = commentary.match(/^[^。．.!?！？\n]+[。．.!?！？]?/);
  const head = (match?.[0] ?? commentary).trim();
  if (head.length <= 50) return head;
  return head.slice(0, 47).trimEnd() + "…";
}

interface PillProps {
  match: MatchedCommentary;
}

function Pill({ match }: PillProps) {
  const [expanded, setExpanded] = useState(false);
  const color = V4_SEVERITY_COLOR[match.severity];
  const title = summarizeForPill(match.commentary_excerpt);

  return (
    <article
      data-testid={`v4-advisor-pill-${match.rule_id}`}
      data-severity={match.severity}
      data-rule-id={match.rule_id}
      data-expanded={expanded ? "true" : "false"}
      className="flex flex-col gap-1.5 rounded border border-v4-border bg-v4-surfaceRaised p-2.5 transition-colors hover:border-v4-borderActive"
    >
      <div className="flex items-start gap-2">
        <span
          aria-hidden
          className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        <div className="min-w-0 flex-1">
          <div
            data-testid={`v4-advisor-pill-${match.rule_id}-title`}
            className="text-[12px] font-medium leading-tight text-v4-textPrimary"
          >
            {title}
          </div>
          {!expanded && (
            <div
              data-testid={`v4-advisor-pill-${match.rule_id}-meta`}
              className="mt-0.5 truncate text-[11px] text-v4-textSecondary"
            >
              <span className="uppercase tracking-wider">{match.severity}</span>
              <span className="mx-1.5 text-v4-textTertiary/60">·</span>
              <span className="font-mono">{match.rule_id}</span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          data-testid={`v4-advisor-pill-${match.rule_id}-toggle`}
          className="shrink-0 rounded border border-v4-border bg-v4-surface px-2 py-0.5 text-[10px] text-v4-textPrimary transition-colors hover:border-v4-borderActive hover:bg-v4-surfaceRaised"
          aria-expanded={expanded}
          aria-controls={`v4-advisor-pill-${match.rule_id}-body`}
        >
          {expanded ? "收起" : "查看详情"}
        </button>
      </div>

      {expanded && (
        <div
          id={`v4-advisor-pill-${match.rule_id}-body`}
          data-testid={`v4-advisor-pill-${match.rule_id}-body`}
          className="ml-4 flex flex-col gap-1.5 border-l border-v4-border pl-3"
        >
          <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-v4-textSecondary">
            {match.commentary_excerpt}
          </p>
          <div className="mt-1 flex items-center justify-between gap-2 text-[10px] text-v4-textTertiary">
            <span
              data-testid={`v4-advisor-pill-${match.rule_id}-matched-at`}
              className="font-mono"
            >
              {match.matched_at}
            </span>
            <span
              data-testid={`v4-advisor-pill-${match.rule_id}-provenance`}
              className="truncate font-mono"
              title={match.provenance}
            >
              {match.provenance}
            </span>
          </div>
        </div>
      )}
    </article>
  );
}

export function AdvisorPillStack({
  matches,
  runId,
  rulesetVersion,
  isLoading = false,
}: AdvisorPillStackProps) {
  const hasRun = runId != null && runId.length > 0;
  const hasMatches = matches.length > 0;

  return (
    <section
      data-testid="v4-advisor-pill-stack"
      data-run-id={runId ?? "__none__"}
      data-match-count={String(matches.length)}
      data-ruleset-version={rulesetVersion}
      data-loading={isLoading ? "true" : "false"}
      aria-label="Curated diagnostic patterns"
      className="flex flex-col gap-2"
    >
      <header className="flex items-center justify-between text-[10px] uppercase tracking-wider text-v4-textTertiary">
        <span>诊断模式 · curated patterns</span>
        <span className="font-mono">ruleset {rulesetVersion}</span>
      </header>

      {isLoading && (
        <p
          data-testid="v4-advisor-pill-stack-loading"
          className="text-[11px] text-v4-textTertiary"
        >
          加载运行结果中…
        </p>
      )}

      {!isLoading && !hasRun && (
        <p
          data-testid="v4-advisor-pill-stack-empty-no-run"
          className="text-[11px] leading-relaxed text-v4-textTertiary"
        >
          暂无已完成运行 · 运行算例后将基于真实工件匹配显示结构化诊断条目
        </p>
      )}

      {!isLoading && hasRun && !hasMatches && (
        <p
          data-testid="v4-advisor-pill-stack-empty-no-matches"
          className="text-[11px] leading-relaxed text-v4-textTertiary"
        >
          无匹配条目 · 残差 / 力 / 收敛统计与策展规则一致
        </p>
      )}

      {!isLoading && hasRun && hasMatches && (
        <ul className="flex flex-col gap-2">
          {matches.map((m) => (
            <li key={m.rule_id}>
              <Pill match={m} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
