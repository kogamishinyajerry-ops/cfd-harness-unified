# v2.3 Governance Loosen · Round 1

**Date**: 2026-05-11
**Scope class**: spike (this retro is itself the deliverable artifact + 3 small rule edits ≤20 lines each)
**Trigger**: calibration retro `.planning/retrospectives/2026-05-11_calibration_spike_v_series_corpus_injection.md` measured ~3× governance overhead on a real spike. User mandate: "渐进式松绑" (incremental loosen, don't over-correct).

## What this round changes

Three rule edits, each ≤20 lines, no DEC, no Codex, no Kogami, no Notion. Pure retro + inline doc patches.

### B1 · "Spike-class" promoted to first-class scope class

**Where**: `~/CLAUDE.md` v2.3 section (added §3 sub-bullet + new §9) · `.planning/methodology/dec_frontmatter_minimum.md` (added "Spike-class formal definition" section + scope-class table row).

**Definition** (verbatim from dec_frontmatter_minimum.md):

- ≤30 LOC production code
- 0 schema changes
- 0 contract breaks
- ≥1 test
- commit carries `confidence:` trailer
- ≤1 retro (only if learnings warrant)

**What spike skips**: DEC frontmatter · Codex relay · Kogami · Notion sync · phase tagging.

**Promotion path**: spike → sub-DEC if mid-work the diff grows to touch ≥3 shared code paths / schema / contract / safety boundary.

**Evidence**: the calibration retro measured spike-class governance overhead at ~3× the actual code work when forced through full sub-DEC ceremony. Recommendation lands as rule.

### B2 · Charter trigger uses ≥3 *shared code paths*, not module count

**Where**: `~/CLAUDE.md` v2.3 §3 (rewrote the "跨 ≥3 模块" clause) · `.planning/methodology/kogami_triggers.md` (added STATUS UPDATE block).

**Old (pre-2026-05-11)**: "跨 ≥3 模块 → 必须 charter" — modules counted at *strategic-brief* authoring time. A 4-pillar plan named 4 modules → charter trigger fired immediately even when only 1 pillar would ship.

**New**: charter trigger fires at **first sub-DEC implementation** when the diff actually touches the third shared code path. Strategic brief authorship does not trigger charter.

**Evidence**: calibration retro F-NEW-loosen-2 — the 4-pillar OSS-substitution brief named P1-P4, ostensibly triggered charter, but only P1 actually shipped (as a spike). Charter would have been process-for-process. Module count must reflect realized scope, not aspirational scope.

### B3 · Notion sync limited to Status=Accepted DECs

**Where**: `~/CLAUDE.md` "Notion 深度同步规则" section (rewrote 同步频率 sub-section) · added explicit rule that retro / spike commits / charter draft / Proposed DECs do NOT sync.

**Old**: session-end batch sync of all DECs + retros + Session Summary.

**New**: session-end batch sync of **only** `Status=Accepted` DECs. Retros stay local. Proposed DECs stay local until accepted. Charter drafts stay local.

**Evidence**: calibration retro F-NEW-loosen-3 — Notion was designed as a decision archive, not a process log. Proposed-state DECs pollute the audit trail; retro-decides-no-DEC leaves no Notion trace by design.

## What did NOT change (deliberate, despite temptation)

| Considered loosening | Why kept | What would have to break to revisit |
|---|---|---|
| **v2.2 1-sync-trigger** (auth/signing/security boundary → Codex pre-merge) | This is the only Codex sync trigger left; removing it would mean Opus self-reviews safety code. Real risk asymmetry. | A measured incident where Opus self-review caught a security regression Codex did not. None observed; keep the gate. |
| **Codex round cap = 3** | DEC-V61-133 (N1.1 22-round) is the binding precedent; relaxing it would re-open infinite-loop tail. | Three rounds genuinely insufficient on a *non-UX-abstraction* class of finding. None observed yet. |
| **DEC frontmatter 6-field minimum (for sub-DEC)** | These six fields are the irreducible identity (id/title/status/parent/phase/sync). Removing any breaks `notion_sync_dec.py`. | A `notion_sync_dec.py` rewrite that derives more from git. Out of round-1 scope. |
| **Cadence floor 30** | This is the auto-trigger threshold for counter retros; not actually firing in current workflow (counter is pure telemetry per V133). Floor change is paper-only. | If counter retros become useful again. |
| **Surface-scan trailer optionality** | V61-088 already made it optional except for routes/pages; nothing to loosen further. | n/a |

## What's still suspected as redundant but needs more data

Single-data-point pattern; do NOT generalize until 2-3 more spikes confirm:

1. **Kogami invocation policy for "data adds"** — calibration retro showed Kogami's 9 findings on a data-only spike were process-pure (P2-2 was about FAISS, not Kogami's actual layer). Rule today already says opt-in; question is whether to add a *falsifiable* "don't invoke for data adds" anti-trigger. **Defer to round 2** — need one more data-add spike where user is tempted to invoke Kogami, observe whether the temptation produces value or process.
2. **Auto-generated `_v61_NNN` DEC ID pressure** — calibration retro F-NEW-loosen-recommendation-5: numbering convention nudges toward escalation (I caught myself proposing V61-199 before user pivoted). A `draft/` directory for unaccepted IDs would help. **Defer to round 2** — touches notion_sync_dec.py, not pure rule edit.
3. **Phase tagging for non-code work** — already removed for spike-class above; broader question (do data milestones still need N-tier tags?) not yet pressing.

## What this round did NOT validate

- Whether the ≥3 shared code path count works in edge cases (e.g., one PR that imports from 3 modules but doesn't *touch* their internals — does that count?). Definition is "diff touches", but ambiguity remains on read-only imports.
- Whether spike-class actually stays at ≤30 LOC in practice or sprawls. The calibration spike was 56 LOC test + 0 code; spike-class definition counts production code, not test, so calibration was technically within bounds. Need 2-3 more spikes to confirm 30-LOC is the right ceiling.
- Whether Accepted-only Notion sync breaks anyone's audit habit. The Notion DB still receives all Accepted DECs (which is the majority). If any cross-session search relied on Proposed-state DECs being in Notion, this breaks it. None known.

## Process budget for this round

| Activity | Time |
|---|---|
| Read calibration retro + identify 3 candidate loosens | ~5 min |
| Read existing rule files (kogami_triggers, dec_frontmatter_minimum, user CLAUDE.md v2.3) | ~5 min |
| Edit 3 doc locations (≤20 lines each, narrow inline patches) | ~10 min |
| Write this retro | ~15 min |
| Total | ~35 min wall |

Compare to the counterfactual (write a sub-DEC for each of B1/B2/B3 + Kogami review of methodology change + Codex review of doc-only patch + Notion sync): estimated 2-3 hours. Round-1 loosen self-evidence: this retro arc demonstrates the rule it documents (spike-class governance ≈ 6× less overhead than sub-DEC ceremony for doc-only methodology evolution).

## confidence: high

- Rule changes are inline doc patches with no code dependency
- Each change is independently reversible (revert this commit → 3 lines back to pre-state)
- Calibration retro evidence base supports all three (1 spike's worth of data each)
- Round-2 candidates explicitly scoped out; no over-correction
