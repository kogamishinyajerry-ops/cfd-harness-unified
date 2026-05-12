# Skill description audit · opt-in transcript-driven loop (v2.3 · DEC-V61-199)

> Established by **DEC-V61-199 Rule 3** (Anthropic agent canon adoption, 2026-05-12).
> Source: Anthropic *Writing effective tools for AI agents* (2025).
> **Opt-in only** — same posture as Kogami (v2.3 §1). No auto-trigger.

## What this audits

The `SKILL.md` `description:` frontmatter field of each project- or user-scope skill is itself a **prompt**: the main session reads it (every turn) to decide whether to invoke the skill. A description that is ambiguous, stale, or missing a key trigger keyword causes:

- **Misroute** — wrong skill invoked instead
- **Miss** — no skill invoked when one should have been
- **Error** — right skill invoked but with wrong args because description is unclear about parameter semantics

The audit's job is to catch these from transcript evidence and rewrite descriptions to remove the failure mode.

## In-scope skills (project-relevant subset)

| Skill | Owner | Last audit |
|---|---|---|
| `codex-relay` | user-scope `~/.claude/skills/codex-relay/` | never (baseline) |
| `cad-step-stl-prep` | user-scope `~/.claude/skills/cad-step-stl-prep/` | never (baseline; new 2026-05-11) |
| `gsd-*` family | plugin (read-only from this project's perspective) | n/a — not editable here |
| Any project-local `.claude/skills/*` | project-scope (none currently) | n/a |

The plugin `gsd-*` skills are read-only from this repo and audited upstream by the GSD plugin maintainer. Project audit only touches **user-scope skills used during cfd-harness work** and any future **project-scope skills**.

## Trigger

This protocol fires **only when**:

1. User explicitly summons (`run the skill audit` or similar), **or**
2. A retro identifies skill-invocation as a contributing failure (e.g., "I called `codex-relay` with wrong model — the description doesn't say spark is only on 86gs").

There is **no calendar-based** auto-fire. Anthropic's writing-tools paper recommends "monthly", but v2.3 §1 retreat from Kogami auto-trigger applies here too: the maintenance loop must be user- or retro-pulled, not scheduled.

## Process

1. **Collect transcript samples** — gather 5-20 turns where the skill in question was invoked (or should have been invoked but wasn't). Source: recent session histories, retro docs, user reports. The bottleneck is sample availability, not analysis effort.
2. **Tag each turn** with one of:
   - `correct_invoke` — right skill, right args
   - `misroute` — different skill (or no skill) chosen when this one was the right one
   - `miss` — main session did the work inline instead of invoking
   - `wrong_args` — right skill but parameters wrong because description was unclear
3. **Look at the `misroute` / `miss` / `wrong_args` rows.** For each, identify the **specific phrase in `description:`** that was insufficient. Examples:
   - "Codex" alone routes to any code-review-ish thing; missing "ALL Codex calls" causes miss
   - "review" routes to `/review` slash command; need "code review, governance review, exec" to disambiguate
   - "STAR-CCM+" needs to appear in description so users mentioning STAR-CCM+ trigger discovery
4. **Rewrite the description.** Edit the skill's frontmatter `description:` field. Rules (from Anthropic writing-tools paper):
   - Namespace prefix (already done: `codex-*`, `gsd-*`, `cad-*`)
   - Unambiguous parameter names referenced in description
   - "Onboarding paragraph" style — read like a new-hire briefing, not API reference
   - Include canonical trigger keywords (verbatim phrases the user is likely to type)
5. **Commit as spike-class** — description-only edit, no code, no test. Commit message: `docs(skill): audit-driven rewrite of <skill-name> description. confidence:high. Parent: V61-199 Rule 3.`
6. **Record the audit pass** in the table at top of this doc (`Last audit` column).

## Anti-scope

- **Not a rewrite of skill behavior.** Body of SKILL.md (the instructions the skill carries) is out of scope for this protocol. Behavioral changes go through their own DEC.
- **Not a Codex review trigger.** Description-only edits do not hit v2.3 §2 risk-tier (no code, no auth, no signing). Skip Codex relay.
- **Not a Notion sync trigger.** No DEC, no SSOT change.
- **Not auto-fire on `~/.claude/skills/*` mtime change.** The protocol explicitly waits for user/retro pull.

## Calibration

After 2-3 audit passes (across multiple skills), retro the protocol itself: did the rewrites measurably reduce misroute / miss / wrong_args rates in subsequent transcripts? If no observable improvement in 3 passes, the protocol's cost-benefit needs reassessment — either the sampling method is too thin, or skill descriptions weren't the real bottleneck.

The empty `Last audit` column at top is intentional: it makes "we've never run this" visible at a glance until the first pass lands.

## Parent

- DEC-V61-199 §2 Rule 3
- `~/CLAUDE.md Anthropic Agent Canon §四` (originator)
- Anthropic *Writing effective tools for AI agents* §"iteration loop"
