---
retrospective_id: RETRO-V61-001
timestamp: 2026-04-21T04:50 local
scope: v6.1 autonomous_governance arc from cutover (DEC-V61-001) through PR-5d.1 closure (DEC-V61-019). Counter progression 0 → 16 across 19 DECs. Hard-floor-4 threshold ≥10 was crossed at DEC-V61-012 (PR-5a, Phase 5 kickoff). This retrospective was self-flagged as overdue in the handoff doc at counter=15 and is landed at counter=16 per user request P1.
status: DECIDED — Kogami chose bundle D (2026-04-21T04:55) and delegated Q1-Q5 to Claude. Codification landed in `~/CLAUDE.md` §"v6.1 自主治理规则".
author: Claude Opus 4.7 (1M context) — analytical
decided_by: Kogami (verbatim: "D，Q1～Q5由你推荐决定"); Q1-Q5 resolved by Claude per recommendations below.
ratification: 2026-04-21T04:55 local
---

# v6.1 Counter-16 Retrospective · Autonomous Governance Arc

## Purpose

Per `~/CLAUDE.md` v6.1 discipline, a formal retrospective is owed when
the autonomous_governance counter crosses the hard-floor-4 threshold
(≥10). It crossed at counter=10 (DEC-V61-012, PR-5a) and has now run 6
further DECs past that threshold to counter=16. At counter=10 the
runtime pattern shifted from "counter as stop-signal" to "counter as
audit metric + Codex post-merge review as default for risky PRs".
This document evaluates whether that shift was correct and what the
rules should be going forward.

## Data · counter progression

Each row is one DEC that incremented the counter (`autonomous_governance: true`).
`autonomous_governance: false` rows (external-gate decisions) do not
increment; they appear in the list but are marked N/A.

| DEC | Date | Counter | Scope | Codex? | Verdict | Est. pass rate |
|---|---|---|---|---|---|---|
| V61-001 | 04-20 | **1** | v6.1 cutover | — | — | 95% |
| V61-002 | 04-20 | **2** | Path B election | — | — | 92% |
| V61-003 | 04-20 | **3** | Phase 1-4 MVP | — | — | 90% |
| V61-004 | 04-20 | **4** | C-class C1/C2 | — | — | 95% |
| V61-005 | 04-20 | **5** | A-class metadata | — | — | 92% |
| V61-006 | 04-20 | N/A | B-class gold remediation | (external gate — Kogami) | — | — |
| V61-007 | 04-20 | **6** | C3A LDC gold anchored | — | — | 95% |
| V61-008 | 04-20 | **7** | C3B NACA surfaces | — | — | 97% |
| V61-009 | 04-20 | **8** | C3C impinging jet | — | — | 97% |
| V61-010 | 04-20 | **9** | C3 result harvest | — | — | 97% |
| V61-011 | 04-20 | N/A | Q-2 R-A-relabel | (gate-approved — Kogami Path A) | — | — |
| V61-012 | 04-21 | **10 ⚠** | PR-5a manifest builder | — | — | 97% |
| V61-013 | 04-21 | **11** | PR-5b serialize | — | — | 94% |
| V61-014 | 04-21 | **12** | PR-5c HMAC sign | ✅ round 1 | APPROVED_WITH_NOTES | 93% |
| V61-015 | 04-21 | **13** | PR-5c.1 M1+L1 fixes | ✅ round 2 | APPROVED_WITH_NOTES | 92% |
| V61-016 | 04-21 | **14** | PR-5c.2 M3 mitigation | ✅ round 3 | APPROVED_WITH_NOTES | 88% |
| V61-017 | 04-21 | **15** | PR-5c.3 warning class | ❌ (verbatim exception) | — | 99% |
| V61-018 | 04-21 | **16** | PR-5d Screen 6 UI | ✅ round 4 | **CHANGES_REQUIRED** | 60% |
| V61-019 | 04-21 | **17**? | PR-5d.1 closure | ✅ round 5 | APPROVED_WITH_NOTES | 90% |

(Note: DEC-V61-019 counter_status reads "15 → 16" which conflicts with
the column above. Two possible explanations: either one of the early
V61-00x entries was retroactively recategorized as non-autonomous, or
the counter stopped incrementing at a session boundary. The data-of-record
for governance is the DEC frontmatter; the counter column in this table
is derived. For decision-making below we trust the frontmatter value of
16 at DEC-V61-019.)

## Data · Codex review economics (Phase 5)

| Round | PR | Tokens | Verdict | Novel findings | Value |
|---|---|---|---|---|---|
| 1 | PR-5c (HMAC) | 117,588 | APPROVED_WITH_NOTES | M1 M2 L1 L2 (4 findings, M or L) | Medium |
| 2 | PR-5c.1 (fixes) | 76,152 | APPROVED_WITH_NOTES | M3 (legacy migration) | Low-medium |
| 3 | PR-5c.2 (M3 mitigation) | 94,316 | APPROVED_WITH_NOTES | Warning-class nit | Low |
| 4 | **PR-5d (Screen 6)** | **143,521** | **CHANGES_REQUIRED** | **2 HIGH + 1 MEDIUM** | **Critical** |
| 5 | PR-5d.1 (closure) | 95,221 | APPROVED_WITH_NOTES | L3 (generated_at semantics) | Validation |

**Cumulative: 526,798 tokens.**

**Key observation — the value was non-uniform**. Rounds 1-3 surfaced
module-level improvements worth landing but not blocking. Round 4
caught 2 HIGH semantic issues that would have shipped silently broken
to production:

- HIGH #1: The signing route would have signed hollow bundles for
  nonexistent case_ids — a signed "audit package" referencing no
  evidence is *worse than no signature* in a regulated review.
- HIGH #2: Byte-reproducibility was documented in `docs/ui_roadmap.md`
  as a core contract but silently broken by wall-clock-stamping. External
  verifiers computing hash divergence would have had no explanation.

**Round 4 alone justified the entire 5-round arc.** Cost attribution:
~263k tokens per HIGH finding caught. That is a *bargain* relative to
the regulated-review blast radius of shipping either issue.

Rounds 1-3 and 5 were still useful (M1/M3/L1/L3 all merged as
real fixes) but their cost-per-value would have been borderline in
isolation. They're the "price of vigilance" that enabled round 4 to
catch the semantic problem — without the established Codex discipline,
PR-5d would have merged unreviewed.

## Data · self-pass-rate calibration

Self-estimated `external_gate_self_estimated_pass_rate` vs Codex verdict:

| DEC | Self-estimate | Actual Codex verdict | Calibrated? |
|---|---|---|---|
| V61-014 | 93% | APPROVED_WITH_NOTES (4 Notes) | Slight overconfidence (pass rate assumed "no blocking"; Notes not counted against) |
| V61-015 | 92% | APPROVED_WITH_NOTES (1 note) | Fair |
| V61-016 | 88% | APPROVED_WITH_NOTES (1 low) | Fair |
| V61-018 | **60%** | **CHANGES_REQUIRED** | **Correctly pessimistic** — acknowledged "semantic risk surface unknown" |
| V61-019 | 90% | APPROVED_WITH_NOTES (1 low) | Fair |

**Key calibration win**: DEC-V61-018's self-estimated 60% was
unusually low for an autonomous merge. It signaled real uncertainty
about the operator-endpoint semantics — and Codex round 4 confirmed
the uncertainty was warranted. Keeping self-pass-rate honest (vs
marketing it up) is the mechanism that made the retrospective arc
constructive.

## Hard-floor-4 threshold: what actually happened at counter=10?

Per `~/CLAUDE.md` spec: "hard-floor-4 threshold ≥10 — driver STOPS
for Kogami ping + Codex tool review invocation strategy."

What actually happened at counter 9 → 10 (PR-5b → PR-5c transition,
2026-04-21 pre-dawn):

1. STATE.md line 611 recorded the threshold trip.
2. Driver (this agent) paused before starting PR-5c (HMAC sign,
   highest-risk PR in Phase 5).
3. Kogami approved: "continue autonomous PR-5c, self-dispatch Codex
   review post-merge". This became DEC-V61-014's operating pattern.
4. Every subsequent risky PR has invoked Codex post-merge (except
   PR-5c.3 where the verbatim-exception rule applied).

**Interpretation**: Threshold did its job as a forcing function. It
didn't stop work; it forced a review-strategy decision. The resulting
pattern (Codex post-merge on risky PRs) has been in steady use for 6
consecutive DECs and was validated by round 4 catching real bugs.

**Interpretation risk**: The threshold did NOT force a formal retrospective
until explicitly requested by the user at counter=16. That's a 6-DEC
gap between threshold trip and retrospective. If Phase 5 had been
shorter-lived or less risk-critical, the gap might have hidden a
governance drift that the retrospective would have caught earlier.

## Five open questions for Kogami

### Q1. Reset the counter?

Counter=16 is currently the running tally of autonomous DECs since v6.1
cutover. Options:

- **Reset to 0** after this retrospective lands (classic "retro closes
  arc, new arc begins"). Pro: clean signal that the arc is evaluated.
  Con: loses historical-trend insight.
- **Keep running** (counter=16 becomes the all-time v6.1 tally). Pro:
  long-term drift visibility. Con: threshold semantics need redefining
  (see Q2).

**Claude's recommendation**: reset. Retrospectives make counter numbers
easier to reason about if they correspond to bounded arcs.

### Q2. Adjust the threshold?

Current: ≥10 triggers "review strategy check".

Options:

- **A. Keep at 10**. Next threshold trip would mean another
  retrospective in ~10 DECs. Might be too frequent if Phase 6 is
  lower-risk than Phase 5.
- **B. Raise to ≥15 or ≥20**. Allow longer autonomous runs but with
  proportionally larger blast-radius at retrospective time. Works if
  per-PR Codex discipline is robust.
- **C. Retire the counter** and replace with per-PR risk tiering
  (Claude self-assigns LOW/MED/HIGH, auto-Codex on HIGH, regular
  retrospectives on session boundaries regardless of counter).
- **D. Hybrid** — keep counter as audit metric (no threshold
  behavior), codify "Codex post-merge on risky PRs" as baseline
  discipline decoupled from counter. Retrospectives owed on
  phase boundaries OR on counter ≥20, whichever comes first.

**Claude's recommendation**: **D**. The counter is a cheap telemetry
signal; the discipline that actually prevents bugs is Codex-per-risky-PR.
Coupling them is what caused the 6-DEC retrospective gap. Decouple.

### Q3. Codify the Codex-per-risky-PR rule?

`~/CLAUDE.md` already enumerates trigger scenarios (multi-file
frontend, API contract changes, OpenFOAM solver fixes, `foam_agent_adapter.py`
>5 LOC, etc.). The question is whether Phase 5 taught us new triggers
that should be added:

**Proposed new triggers** (extracted from round-4 findings):

1. **Security-sensitive operator endpoints that sign artifacts** —
   auto-Codex even if the module-level signing code was previously
   reviewed. PR-5d demonstrated that module-level review (rounds 1-3)
   does not catch operator-level semantic flaws.
2. **Any PR changing byte-reproducibility-sensitive code paths** —
   tests alone are not enough; Codex probes with targeted temporal
   diffs are needed.
3. **API schema field rename that touches 3+ files** — even
   "mechanical" renames (Codex's own suggestion) benefit from a
   round 5-style validation pass.

### Q4. Mechanical-verbatim-exception rule: was it safe?

DEC-V61-017 (PR-5c.3, warning-class fix) skipped Codex review on the
grounds that it was Codex's verbatim round-3 recommendation + atomic +
mechanical. No subsequent round surfaced any issue with that decision.

**Evidence**: PR-5c.3 landed clean; PR-5d and PR-5d.1 reviews did not
flag regressions in the warning-class code.

**Risk**: The exception can be abused to skip Codex on any change
Claude can frame as "mechanical". Recommend tightening the rule:

- Must be Codex's verbatim `Suggested fix` bullet (diff-level match)
- Must be ≤20 LOC
- Must touch ≤2 files
- Must not change any public API surface
- Claude must cite the round + finding-ID in the PR body

PR-5c.3 met all 5 criteria. Future applications must too.

### Q5. What about `autonomous_governance: false` DECs (V61-006, V61-011)?

Both were external-gate decisions where Kogami was the deciding vote.
They don't increment the counter. Is that correct?

**Current semantics**: counter counts autonomous-merge events; externally-
gated decisions are tracked separately (external_gate_queue.md).

**Proposed clarification**: yes, this is correct — but the retrospective
should explicitly include both classes so we see the full decision
arc. Going forward, retrospectives should tabulate both.

## Recommendation bundle (Claude's default, if Kogami doesn't specify)

Adopt **D** from Q2 + **tighten** from Q4 + **formalize triggers** from Q3:

1. **Counter reset to 0** at this retrospective.
2. **Counter threshold retired** as a stop-signal; becomes a pure
   telemetry metric shown in STATE.md for arc-size awareness.
3. **Retrospective cadence**: owed on every phase close (whichever
   comes first between "phase marked COMPLETE" and "counter ≥ 20").
4. **Codex-per-risky-PR discipline** codified in
   `~/CLAUDE.md` as baseline rule, with the 5-trigger list expanded
   per Q3 and the 5-criterion verbatim-exception per Q4.
5. **Self-pass-rate honesty** retained as a documented norm; any
   estimate ≤70% triggers mandatory Codex pre-merge (not post-merge)
   to catch blockers *before* they land in main.

This shifts governance from "counter-threshold-driven" to
"risk-tier-driven" while preserving the audit metrics that let us
detect drift.

## Open items to queue (post-retrospective)

These should roll forward regardless of which option is chosen:

- **L3** (DEC-V61-019): `generated_at` semantic rename (path A vs B)
- **M2** (DEC-V61-014): sidecar v2 with kid/alg/domain metadata
- **L2** (DEC-V61-014): canonical JSON spec publication
- **3 pre-existing** `ui/backend/tests/test_validation_report.py`
  failures (DHC Nu=30→8.8 / TFP SST→laminar legacy) — tech debt
- **`datetime.datetime.utcnow()`** deprecation in `correction_recorder.py:76`
  and `knowledge_db.py:220` — tech debt
- **`foam_agent_adapter.py` 7000-line monolith** — refactor after API
  freeze — tech debt

## Ratified decision (2026-04-21T04:55)

Kogami reply: **"D，Q1～Q5由你推荐决定"** — adopts bundle D, delegates Q1-Q5 to Claude's recommendations.

**Resolved per recommendations**:

- **Q1 · Reset counter to 0** at this retrospective (arc-close semantic). Next counter increment begins at Phase 6 (or the first post-retro autonomous DEC).
- **Q2 · Option D (hybrid)** — threshold retired as stop-signal; counter becomes pure telemetry; retrospectives required on phase-close OR counter ≥ 20 OR any `CHANGES_REQUIRED` verdict (incident retro, small-scope).
- **Q3 · Codify 3 new Codex triggers** (added to `~/CLAUDE.md` §"v6.1 自主治理规则 · Codex-per-risky-PR baseline"):
  1. Security-sensitive operator endpoints (signing, auth)
  2. Byte-reproducibility-sensitive paths (canonical manifest, HMAC, zip serialize)
  3. ≥3-file API schema renames (even "mechanical" ones)
- **Q4 · Tighten verbatim-exception rule** to 5-of-5 hard criteria (added to `~/CLAUDE.md` §"Verbatim exception"): diff-level verbatim match + ≤20 LOC + ≤2 files + no public API change + PR body cites round + finding ID.
- **Q5 · External-gate DEC accounting** — `autonomous_governance: false` DECs do NOT increment counter but MUST be listed in every retro's counter table (marked N/A).

**New operational rules**:
- `external_gate_self_estimated_pass_rate ≤ 70%` → **mandatory pre-merge Codex review** (not post-merge). DEC-V61-018's 60% self-estimate would have triggered this under the new rule.
- Counter is displayed in STATE.md but carries no stop-signal semantics.

**Updated files**:
- `~/CLAUDE.md` §"v6.1 自主治理规则" — new section (replaces implicit ADWM v5.2 counter discipline)
- `.planning/STATE.md` — counter reset to 0 at 2026-04-21T04:55
- `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` — this file, status DECIDED
- Notion Decisions DB — retrospective mirrored at https://www.notion.so/348c68942bed819185f1fa3351e89ace (Scope=Project, Status=Accepted)

**Phase 6 kicks off at counter=0 + new governance active.**
