---
decision_id: DEC-V61-133
dec_id: V61-133
title: Governance simplification B+ · Kogami opt-in · Codex round cap · DEC scope-driven · retire dual-track guard / freeze advisory / sampling audit
status: Proposed (drafted 2026-05-07 · self-bootstrap; awaiting user ratification)
parent_dec: V61-130
parent_artifacts:
  - ~/CLAUDE.md (global; will become v2.3)
  - .planning/decisions/2026-05-07_v61_133_governance_simplification_b_plus.md (this file)
  - .pre-commit-config.yaml (will retire 3 hooks)
  - CLAUDE.md (project; will become v6.3 of three-layer governance with Kogami opt-in)
  - .planning/methodology/kogami_triggers.md (will rewrite to opt-in)
  - .planning/methodology/kogami_counter_rules.md (kept; counter is pure telemetry)
phase: governance · meta · self-bootstrap
trigger: User mandate 2026-05-07 — "deep think on validation gate overhead; pivot to B+ aggressive cuts; retain DEC three-layer governance + Codex review structure but Kogami opt-in only"
autonomous_governance: true
counter_impact: +1
counter_value_after: 30 (V132 was 29)
codex_review_relay: 86gs (xhigh) primary; CRS (high) fallback if 86gs slow
kogami_review_path: SKIPPED (per self-bootstrap §6 — this DEC creates the rule that retires Kogami auto-trigger; one-time bootstrap exception explicitly authorized by user)
notion_sync_status: pending (session-end batch)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-07
confidence: high (clear mandate, narrow scope, reversible)
---

# DEC-V61-133 · Governance simplification B+

## 1. Why now

After 22 Codex review rounds on N1.1 (DEC-V61-131 envelope hard-strip),
user observed two things:

1. **Marginal P2/P3 findings on rounds 18-22 were UX polish, not
   correctness or safety**. The R0 functional change ("AI doesn't
   silently mutate case files") could have shipped in 2-3 commits;
   the remaining 19 rounds were correctness-of-error-handling and
   field-rendering minutiae.
2. **The strategic pivot itself (V130 — the most consequential
   decision) was caught by user feedback, not by the governance
   stack**. Kogami / Codex / counter / surface-scan all passed prior
   AI-auto-apply DECs (V61-097/098/100/120-126). The stack catches
   code-quality issues, not strategic errors.

Combined: the governance stack costs ~3-5 hours per N-tier sub-DEC
in review iteration + bookkeeping, while modern Opus 4.7 + GPT-5.4
xhigh make N1.1-class errors that 22-round chains barely resolve
(diminishing returns). The CFD reliability vector (OpenFOAM
correctness · gold-standard validation · engineer judgment ·
reproducibility) is **not** the dimension this overhead protects.

User's framing on 2026-05-07: "I want a bit more aggressive than B,
reduce Kogami (except when user wants it)."

## 2. New rules (B+ baseline)

### 2.1 KEEP (load-bearing · unchanged)

- **AI advisor contract** (V130 Principle B + V131 + V132): AI never
  writes case files. V132 behavioral test is the merge gate; this
  doesn't relax.
- **Tests** as the primary safety net. Pytest must stay green; new
  features land with tests.
- **TrustGate three-state verdict** + **Gold Standard 10 cases
  frozen**.
- **Codex review on the v2.2 1-sync-trigger** (security boundary /
  auth / signing / authorization paths). Async post-merge for
  byte-reproducibility and E2E ≥3 fail (unchanged from v2.2).
- **Charter-class DEC discipline** (V130 charter, V133 this DEC,
  V61-087 governance-rule changes): full DEC + parent_artifacts +
  status flow. These are leverage decisions; governance overhead is
  proportionate.
- **Four-plane import contract** (ADR-001) via import-linter pre-commit.

### 2.2 RELAX (kept but loosened)

| Rule | Old | New (B+) |
|---|---|---|
| Codex review rounds | unbounded; each P2/P3 needs another round until APPROVE | **cap 3 rounds**. After R3, remaining P3 (and non-P1 P2) findings go to retro queue; user explicitly ratifies if any P1 remains |
| DEC scope | every meaningful task | **charter / cross-cutting (≥3 modules) / governance-rule-change only**. Single-feature work (e.g., N2.1 sizing field UI) lands via commit messages + tests |
| Counter `autonomous_governance_counter_v61` | live increment per DEC + audit per fire | **pure retrospective telemetry**. Increment but don't gate on it; audit at retro time |
| Cadence floor THRESHOLD | 10 commits | **30 commits** (Q5/Q14 risk-class trigger unchanged — still fires on routes/pages/security globs) |
| Surface-scan trailer (V61-088) | mandatory unless skip-clause | **optional** for ≥30 LOC AND new top-level file. Encouraged but not blocking. Skip-clauses unchanged |
| DEC frontmatter | 27+ fields | **6 core fields** required (decision_id / title / status / parent_dec / phase / notion_sync_status) + others optional |

### 2.3 CUT (retired entirely)

| Mechanism | Reason for cut |
|---|---|
| **Dual-track isolation guard** (`dual-track-isolation-precommit` + `-msg` hooks) | Designed for parallel CORE-A vs CORE-B development; no longer parallel. Adds friction every commit (must add `[ops]/[shared]/...` tag) for zero protection |
| **§11.1 Workbench freeze advisory** (`workbench-freeze-advisory` hook) | Already scheduled to retire 2026-05-19; pull retirement forward by 12 days. Was advisory-only, never blocked |
| **§10.5 sampling audit ratchet** | Methodology self-check that duplicates what tests already cover. Retire the ratchet schedule (5→7→10→15→20); keep the underlying capability if anyone wants to fire it manually |

### 2.4 Kogami → opt-in only (the B+ delta vs B)

**Old behavior** (V61-087 + V130 §4 N1.2 Kogami trigger checklist):
Kogami fires automatically on (a) phase-close, (b) RETRO draft, (c)
high-risk PR after Codex APPROVE, (d) counter ≥ 20 arc-size retro,
(e) governance rule-change DEC.

**New behavior**: Kogami fires only when **user explicitly invokes**
it via `bash scripts/governance/kogami_invoke.sh ...` or asks
Claude Code to trigger it. No auto-trigger from any of the (a)-(e)
conditions.

**Justification**:
- Kogami's strategic-layer review value is real but discretionary.
  When user wants a second opinion on architecture, they trigger it.
- Auto-trigger means Kogami runs on every governance-rule DEC (this
  one would have triggered it; V130 did trigger it). The runs that
  pass APPROVE_WITH_COMMENTS with inline-closeable findings are
  process-completion, not value-creation.
- Removing auto-trigger does NOT remove Kogami; the
  `kogami_invoke.sh` wrapper, P-1 agent prompt, briefing builder, and
  review directory convention remain operational. Manual invocation
  works exactly as before.

**What stays**:
- Kogami's governance contract files (P-1 through P-5) remain
  protected — modifications still need user + Codex ratification.
- Q1 canary regression test still runs on `claude --version`
  changes (dependency-triggered, not governance-triggered).
- Existing Kogami review artifacts (`.planning/reviews/kogami/...`)
  remain immutable historical records.

## 3. Self-bootstrap exception

This DEC creates the rule that retires Kogami auto-trigger on
governance-rule-change DECs. Under old rule, this DEC itself would
trigger Kogami. Under new rule, it doesn't.

**Resolution**: user explicitly mandated the change on 2026-05-07
("减少 Kogami（除非用户主动想介入）"). The user mandate IS the
ratification that Kogami auto-trigger would have provided. One-time
bootstrap exception, recorded here. Future governance DECs follow
new rule (no auto-Kogami).

If user wants belt-and-suspenders, they can manually invoke Kogami
on this DEC after-the-fact. The artifacts at `.planning/reviews/
kogami/v61_133_governance_simplification_2026-05-07/` stay as a
placeholder; if user invokes, the review lands there.

## 4. What changes in code / config

### 4.1 Hooks retired in `.pre-commit-config.yaml`

- Remove `dual-track-isolation-precommit` (pre-commit stage)
- Remove `dual-track-isolation-msg` (commit-msg stage)
- Remove `workbench-freeze-advisory` (pre-commit stage)

Scripts kept in tree (not deleted) so they can be re-enabled if a
future DEC re-introduces the need: `scripts/check_track_isolation.py`,
`scripts/check_track_isolation_msg.py`,
`tools/methodology_guards/workbench_freeze_advisory.sh`.

### 4.2 `scripts/check_codex_cadence.py` THRESHOLD 10 → 30

Single constant change. Risk-class trigger logic unchanged (still
fires on `routes/**`, `pages/**`, security-path globs, LOC delta
> 500).

### 4.3 `~/CLAUDE.md` global v2.2 → v2.3

Replace the `## My Default Agent Rules > 模型分工` v2.2 anchor with
v2.3 reflecting:
- DEC scope-driven (≥3 modules / charter / governance only)
- Codex round cap 3
- Surface-scan optional
- Cadence floor 30
- Counter pure telemetry
- Kogami opt-in only

### 4.4 `cfd-harness-unified/CLAUDE.md` (project) update

- Three-layer governance description: change "Kogami auto-trigger
  on (a)-(e)" to "Kogami opt-in only; user invokes when wanted".
- Kogami trigger checklist section: rewrite as "examples of when to
  consider invoking Kogami" rather than "MUST run before X".

### 4.5 `.planning/methodology/kogami_triggers.md` rewrite

From "trigger conditions that fire Kogami automatically" to
"situations where Kogami review is high-value (consider invoking)".
Same conditions listed but as advisory not mandatory.

### 4.6 DEC frontmatter slimming

Document the 6 core required fields in
`.planning/methodology/dec_frontmatter_minimum.md` (new file). Old
DECs unchanged; new DECs MAY use slim frontmatter. Notion sync
script supports both shapes (it already reads decision_id field; the
others are optional).

## 5. What stays unchanged in code / config

- `import-linter` pre-commit hook (ADR-001 four-plane contract)
- `codex-cadence` pre-push hook (just THRESHOLD bumped)
- `ai-path-mutation-grep` pre-commit hook (V132 R0)
- All `scripts/governance/kogami_*.sh` and `kogami_brief.py` —
  manual invocation still works
- All Kogami contract files (P-1..P-5)
- All existing DEC artifacts in `.planning/decisions/`
- Notion sync script `notion_sync_dec.py`
- Q1 canary test + verification scripts

## 6. Verification

R0 checklist:
- [ ] `.pre-commit-config.yaml` has 3 hooks removed; `pre-commit
      run --all-files` still passes (only kept hooks fire)
- [ ] `scripts/check_codex_cadence.py` THRESHOLD = 30
- [ ] `~/CLAUDE.md` global anchor reads v2.3
- [ ] `cfd-harness-unified/CLAUDE.md` Kogami section reads opt-in
- [ ] `.planning/methodology/kogami_triggers.md` reads opt-in
- [ ] `.planning/methodology/dec_frontmatter_minimum.md` exists with
      the 6-field contract
- [ ] Manual `bash scripts/governance/kogami_invoke.sh ...` still
      executes (regression test for opt-in path)
- [ ] No Kogami review run created automatically on this DEC's
      landing (verify by absence of new directory under
      `.planning/reviews/kogami/`)

## 7. Predicted Codex rounds

V123 §L1: docs + config change. No production code logic. Predict
**1-2 rounds APPROVE**. Likely findings: wording tightenings,
"did you remember to retire X file/path/reference".

Confidence: **high** — narrow scope, reversible (every retire is a
single git revert), explicit user mandate.

## 8. Risks

- **R-1 · Loss of strategic safety net**: Kogami opt-in means user
  must remember to invoke for charter-class DECs. Mitigation: (i)
  high-leverage governance rule changes are rare (V130, V133, V61-087
  are the canonical 3 in the past 6 months — user can budget the
  invocations); (ii) post-incident retro can identify when missing
  Kogami contributed.
- **R-2 · Hook retirement misses regression**: removing dual-track
  guard might re-allow cross-track absorption mistakes. Mitigation:
  the actual mistake the guard caught (line-A SOLE ∧ line-B in same
  commit) is structurally rarer post-pivot single-track development;
  if it recurs, re-enable from kept-in-tree script.
- **R-3 · Cadence floor 30 too lax**: a 30-commit no-review window
  could drift quality. Mitigation: risk-class trigger (Q14) still
  fires on touched-routes/pages/security regardless of count; the
  count-only path was always the weakest layer.
- **R-4 · Self-bootstrap legitimacy**: user authorization replaces
  Kogami auto-trigger for this DEC. If user later regrets, they can
  manually run Kogami on this DEC and ratify retroactively. The
  retire/un-retire is git-revert symmetric.
- **R-5 · Drift via implicit re-introduction**: future DECs might
  re-introduce auto-Kogami-style triggers without recognizing they
  re-violate B+. Mitigation: `~/CLAUDE.md` v2.3 anchor explicitly
  states "Kogami opt-in only"; periodic re-read by any future
  Claude Code instance restores the rule.

## 9. Decision

**R0 (this draft)**: land DEC + apply 4.1-4.6 changes in a single
commit (the changes are tightly coupled — partial application would
leave the project in a half-relaxed state). Push for Codex review
on 86gs gpt-5.4 xhigh; CRS fallback if 86gs slow. On APPROVE, advance
to Accepted; this DEC's rule applies retroactively to itself.

User retains override at any time: explicit "run Kogami on this"
brings the strategic layer back for any specific DEC.

## 10. Surface-scan (per DEC-V61-088)

ROADMAP scan: V133 is governance, not in N-sequence (which is
workbench feature work). No N-sequence scope conflict.

Existing-implementation grep:
- `THRESHOLD = 10` in `scripts/check_codex_cadence.py` exists; will
  change to 30.
- `dual-track-isolation` references: hook config + 2 scripts +
  `.planning/ops/2026-04-25_dual_track_plan.md`. Hook config
  retires; scripts kept; ops plan referenced but not modified.
- `workbench-freeze-advisory` references: hook config + advisory
  shell script + Methodology v2.0 §11.1. Hook retires; script kept;
  Methodology v2.0 §11.1 marked superseded by V133 §2.3.
- `kogami_triggers.md` exists at expected path; will rewrite.

Disposition: **clean / extend** — config changes overwrite known
loci; new methodology file additive; no implementation collisions.
