# Kogami-Claude-cosplay Trigger Rules · v6.2

> Authoritative source for **when** Kogami subprocess review fires.
> Established by **DEC-V61-087** (Accepted 2026-04-27) §4.
> Implementation: `scripts/governance/kogami_invoke.sh`.

## Must trigger (5 cases)

| Trigger | Timing | Strategic package input | Expected outcome |
|---|---|---|---|
| **Phase-close** (if phase-dir model used) | Before marking phase COMPLETE | phase CONTEXT.md + PLAN.md + commit message list (NOT diff) + linked RETRO draft if any | APPROVE / APPROVE_WITH_COMMENTS to advance Phase status |
| **RETRO draft to git** | Before Notion sync of RETRO | RETRO draft file (full) | APPROVE / APPROVE_WITH_COMMENTS to seal RETRO |
| **High-risk PR** (after Codex APPROVE) | Before merge | linked DEC + intent_summary.md + merge_risk_summary.md + Codex `final_verdict_enum` string ONLY (NOT finding text) | APPROVE → merge; CHANGES_REQUIRED → block merge |
| **counter ≥ 20 arc-size retro** | When counter triggers retro per RETRO-V61-001 | DEC titles + frontmatter list across the arc (NOT Codex round details) | APPROVE → close arc; CHANGES_REQUIRED → escalate |
| **autonomous_governance rule change** | Any DEC modifying RETRO-V61-001 / DEC-V61-087 / kogami_*.md | proposed DEC + diff summary (NOT raw diff) | per Hard Boundary: cannot self-approve, see §Hard Boundary |

## Must NOT trigger (5 cases)

| Skip case | Rationale |
|---|---|
| Single-file ≤50 LOC routine commit | Trust path per Pivot Charter §4.7 |
| Codex APPROVE'd verbatim-exception path | per CLAUDE.md 5-condition verbatim rule |
| docs-only CLASS-1 changes | per V61-086 precedent |
| Kogami review output's own review | Anti-recursion |
| Kogami's own P-1/P-1.5/P-2/P-2.5/P-3/P-4/P-5 modifications | per Hard Boundary (anti-self-approval) |

## Trigger precedence (when multiple fire on same arc)

Per DEC §4.3 (P2-1 fix), execute **only** the highest priority:

```
priority 1 (highest): arc-size retro (counter ≥ 20)
priority 2:          retro draft review
priority 3:          phase-close review
priority 4 (lowest): high-risk PR review
```

Lower-priority reviews are **superseded** but their trigger reasons must be
recorded in the executed review's `invoke_meta.json`:

```json
{
  "trigger": "arc_size_retro_60",
  "superseded_triggers": ["retro_draft_v61_007", "phase_close_p3_t2"]
}
```

## Disambiguation with Codex (RETRO-V61-001)

Kogami and Codex are **complementary**, not redundant:

| Aspect | Codex GPT-5.4 | Kogami |
|---|---|---|
| Layer | Code | Strategic |
| Input | PR diff + modified files | Strategic package (no diff, no Codex finding text) |
| Output location | `reports/codex_tool_reports/*.md` | `.planning/reviews/kogami/<topic>_<date>/` |
| Counter | Not counted | Not counted (advisory chain) |
| Order on shared trigger | First (code correctness gate) | Second (strategic adequacy gate) |
| Failure handling | Per RETRO-V61-001 risk-tier triggers | Per DEC-V61-087 §4 |

When **both** trigger:
1. Codex first — its verdict goes into the strategic package as ENUM only
2. Kogami second — sees the ENUM (APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED) but never sees the finding text

This prevents Codex framing from contaminating Kogami's independent strategic judgment.
**Both** must APPROVE for merge (double-necessary, neither sufficient).

## Hard Boundary (anti-self-approval)

Per DEC §Out of Scope:

Kogami **cannot approve** any of the following (file-level OR meta-level):

**Files**:
- `.claude/agents/kogami-claude-cosplay.md` (P-1)
- `scripts/governance/kogami_invoke.sh` (P-1.5)
- `scripts/governance/kogami_brief.py` (P-2)
- `scripts/governance/validate_strategic_package.py` (P-2.5)
- `.planning/reviews/kogami/README.md` (P-3)
- `.planning/methodology/kogami_triggers.md` (P-4 — this file)
- `.planning/methodology/kogami_counter_rules.md` (P-5)

**Meta DECs** (recursion gap closure · per W3 blind-control Kogami P2-1 finding):
- DEC-V61-087 itself (the governance contract)
- Any DEC whose `parent_dec` field includes `DEC-V61-087` (successor governance evolution)
- Any DEC whose subject matter modifies the Kogami isolation contract, counter rules,
  trigger rules, or Tier 1/Tier 2 boundary — **regardless of which file paths are touched**

For all the above, the trigger STILL fires (transparency), but Kogami MUST return
`CHANGES_REQUIRED` with verdict reason `out_of_scope_self_modification`. The
required path is: user explicit ratification + Codex review APPROVE.

This rule prevents governance self-inflation (Kogami approving expansion of its
own scope) AND closes the framing-bypass loophole (a DEC re-architecting Kogami
without touching P-1..P-5 files is still self-modification).

## Strategic package authoring (high-risk PR only)

For the high-risk PR trigger, the PR author must produce two YAML files alongside
the linked DEC:

- `intent_summary.md` — see DEC §4.4 for schema (roadmap_milestone, business_goal,
  affected_subsystems, optional rationale)
- `merge_risk_summary.md` — see DEC §4.4 for schema (risk_class, reversibility,
  blast_radius, optional rationale)

`scripts/governance/validate_strategic_package.py` (P-2.5) validates both before
the wrapper builds the briefing. Schema-invalid → wrapper exits non-zero → review
not triggered. Author must fix schema first.

The validator's regex blacklist (applied ONLY to free-text rationale fields):
- `\bP[0-3]\b` (word-boundary; does NOT match P2-T2 milestone IDs)
- `\bCodex\b` / `\bround\s+\d+\b` / `\bfinding(s)?\b`
- `\b(CHANGES_REQUIRED|APPROVE_WITH_COMMENTS|APPROVE)\b`
- `\S+\.\w+:\d+\b` (file:line citations)

Honest residual risk: paraphrase laundering ("the previous review identified a
blocker" avoids `Codex/finding`). Per DEC §4.4 acknowledged "improved, not closed";
mitigation = structured field constraints + `rationale ≤100 words` + sampling
audit on accumulated review history.

## Tier 1 → Tier 2 escalation

If any of these occur, this entire trigger system needs Tier 2 OS sandbox upgrade
(independent DEC, not in scope of DEC-V61-087):

- Q1 canary regression test (monthly cron) fails
- Anthropic upgrades `claude` CLI and any §3.1 flag combo behavior changes
- Live governance incident attributed to Kogami exceeding isolation
- Q5 keyword sampling shows new content-leak vector
- OS platform changes (macOS → Linux requires re-verification)
- P-2.5 sampling audit on accumulated review history finds ≥3 paraphrase laundering instances
