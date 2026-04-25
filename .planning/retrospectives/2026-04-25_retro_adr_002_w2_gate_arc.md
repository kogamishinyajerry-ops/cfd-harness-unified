---
retro_id: RETRO-V61-005
title: ADR-002 W2 Gate · three-round arc + same-day Accepted flip · methodology calibration
date: 2026-04-25
trigger: incident-retro (round-1 CHANGES_REQUIRED on ADR-002 Draft v1) + phase-close (W2 Foundation-Freeze runtime layer Accepted)
related_artifacts:
  - docs/adr/ADR-002-four-plane-runtime-enforcement.md (Status: Accepted, 2026-04-25T15:00)
  - src/_plane_assignment.py · src/_plane_guard.py · scripts/gen_importlinter.py
  - tests/test_plane_assignment_ssot.py · test_plane_guard.py · test_plane_guard_edge.py · test_plane_guard_escape.py · test_gen_importlinter.py
  - 12 commits: e4d118a → 87e5c9e → 01de7da → a21c05d → 5d4fd87 → 7e0fe5c → 3e9205f → efc25ce → acf1ffe → 8651d1c → 72ddcd0 → 0fae68e → 494455e
counter_at_retro: 43 (P1-arc end, no further DEC counter increments today; ADR work is governance-class not DEC-class)
notion_page: 34dc6894-2bed-811c-9e0e-e822d11f21e0 (Notion Decisions DB · ADR-002 · Status=Active 2026-04-25)
notion_sync_status: synced 2026-04-25 (https://www.notion.so/RETRO-V61-005-ADR-002-W2-Gate-three-round-arc-same-day-Accepted-flip-34dc68942bed812a9ddcfa72cb925078)
---

## Incident summary

Opus 4.7 W2 Gate round 1 returned **CHANGES_REQUIRED** on `ADR-002
Draft v1` (commit `87e5c9e`, 353 LOC). Four design-level blocking
items were flagged:

1. §2.1 single-frame `sys._getframe(1)` not robust for pytest
   fixtures / `__main__` / Cython trampolines → required bounded
   multi-frame walk
2. §1.1 covered 6 of 9 critical bypass patterns (missing
   `sys.modules` pollution, `importlib.reload`, PEP 420 namespace
   package)
3. §4.1 AC matrix incomplete (missing fork-safety, thread-safety,
   bootstrap zero-src-deps; A7 deliberate-violation fixture under-
   specified)
4. §2.4 test-allowlist conditions under-specified (regex literal
   form ambiguous, no reverse-test, no Option A→B rollback trigger)

Round 2 returned **ACCEPT_WITH_COMMENTS** (5 minors); round 3
returned **ACCEPT_WITH_TRIVIAL_COMMENTS** (6 trivial). All 9
follow-up + minor + trivial items were inlined the same day in
Draft-rev2 → rev3 → rev4. W2 Impl Start + Mid + Late + Accepted
flip all delivered on 2026-04-25 under explicit user authorization
to bypass the §5 calendar gating (originally targeted Mid 5/1, Late
5/2-5/3, Accepted 5/4 — pulled forward 6-9 days each).

## Calibration

| Round | Self-estimate | Opus verdict | Calibration |
|---|---|---|---|
| R1 | n/a (Claude self-est not gathered before R1) | CHANGES_REQUIRED 4 blocking | Baseline anchor |
| R2 | 0.55 (Opus independent prediction) | ACCEPT_WITH_COMMENTS 5 minors | On target — predicted "1-3 blocking + 1-3 non-blocking", actual 4 blocking already addressed + 5 minors |
| R3 | 0.72 (Opus updated) | ACCEPT_WITH_TRIVIAL_COMMENTS 6 trivial | Marginally optimistic — 0.72 implied APPROVE-clean ~30% probability; actual was ACCEPT_WITH_TRIVIAL not ACCEPT-clean |
| Codex post-merge (pending) | 0.83 (Opus updated · stair-anchored ceiling 0.87 not unlocked) | TBD | Per RETRO-V61-004 stair convention, only actual Codex APPROVE-clean unlocks 0.90 anchor; 0.83 self-est does not pre-unlock |

**Calibration health**: Opus's three self-estimates (0.55 → 0.72 →
0.83) tracked the actual closure trajectory accurately. The
stair-anchor ceiling (0.87 from RETRO-V61-004) was correctly
respected — never claimed pre-unlock, even at 0.83.

## What worked

1. **Opus W2 Gate as multi-round design-iteration vehicle**.
   Three independent rounds in a single day produced more design
   surface coverage than a single-shot review would. Round 1 caught
   structural mechanism issues (frame walk, pattern coverage);
   round 2 caught mechanism-detail issues (regex form, log schema);
   round 3 caught polish-level issues (logger hierarchy, dedup
   anti-flood, bootstrap purity scope). Each round's findings were
   crisper than they would have been in a fused single-round review
   — same density Codex GPT-5.4 provides for code, applied to spec.

2. **Pre-emptive consolidation in Draft-rev3**. After round 2
   ACCEPT_WITH_COMMENTS, Claude Code chose to land round-2 minors
   AND round-1 follow-ups together rather than splitting into two
   passes. Result: round 3 verdict was on a near-final state, not a
   half-finished one. Saved one review round.

3. **Same-day W3 init Accepted flip under user authorization**.
   The §5 calendar timeline existed primarily as a buffer against
   uncertainty; with all blocking ACs demonstrably green and user
   authorization to bypass, the flip became a pure status-line
   edit. No technical compromise — 41 new tests + 5 import-linter
   contracts kept + 723 pytest passing.

4. **SSOT + byte-identical CI check pattern (ADR-002 §2.2)**.
   Closed ADR-001 AC-A7 (hand-enumerated brittleness) at the same
   time as adding the runtime layer. One mechanism, two
   acceptance criteria satisfied. Worth reusing for any future
   "single source declared, multiple consumers" pattern in the
   project (e.g. observable definitions, gold-standard schemas).

## What did not work / improve next time

1. **Round 1 Draft v1 missed `sys.modules` pollution as a §1.1
   pattern**. Pattern was noted in Opus's original Post-Hoc Review
   §3 末 in passing but Claude Code's initial §1.1 enumeration
   stopped at the 6 most-cited patterns. **Lesson**: when an ADR
   transcribes upstream-review patterns, do an explicit "what did
   the reviewer mention that I haven't yet captured" sweep before
   shipping the Draft. Cheap insurance against round-1
   CHANGES_REQUIRED on completeness grounds.

2. **A7 deliberate-violation fixture was under-specified in
   Draft v1** (one fixture vs. the 4×3 matrix Opus required in
   round 2). The original AC text said "deliberate-violation
   fixture proves CI fails" without specifying scope. **Lesson**:
   ACs at the v1.0 mark should specify cardinality (×4 contracts ×
   3 modes = 12 cells) when the test surface is structured. Fuzzy
   "fixture proves" wording lets review rounds spend cycles
   pinning down what was self-evident in retrospect.

3. **§5 timeline buffer was too generous**. Original schedule had
   W2-Mid (5/1), W2-Late (5/2-5/3), W3-Accept (5/4) — 9 calendar
   days total from Draft to Accepted. With user time-bypass
   authorization, the same scope landed in 6 hours of the same
   day. **Lesson**: the §5-style timeline should optimize for the
   serial path (Draft → Opus → Code → Tests → Accepted) at the
   project's actual execution density (V61-054 / V61-053 single-day
   precedent), not for hypothetical worst-case slippage. Schedule
   inflation creates a false ceiling.

## Open questions (for next retrospective or Notion follow-up)

1. **Should ADRs go through Codex review in addition to Opus
   review?** Opus three-round ACCEPT_WITH_COMMENTS / TRIVIAL
   verdict provided strong design coverage. Codex on the
   implementation (src/_plane_guard.py + tests) is still pending
   per Model Routing v6.2 §B (key-claim verification on multi-file
   high-LOC delivery). For ADRs themselves (the document, not the
   implementation), Codex's value vs. Opus is less clear — Codex
   excels at code-level claim verification, Opus excels at
   architectural / governance reasoning. Tentative position:
   continue Opus-only for ADR docs; Codex for implementation. Re-
   examine if a future ADR's implementation regresses post-Codex.

2. **Where does the `runtime-plane-guard` opt-in CI job sit
   relative to A6?** AC-A6 originally intended a separate CI job
   that runs pytest with `CFD_HARNESS_PLANE_GUARD=1` and asserts
   one green run before W4 hard-fail. v1.0 reality: existing
   pytest CI job already exercises the guard via fixture-installed
   ON / WARN modes; the prod-env-var pathway is OFF by default
   and won't flip until W3 (5/4 → ?) or auto-install lands in
   `src/__init__.py`. **Tentative position**: A6 is satisfied by
   the existing pytest job until prod auto-install lands. The
   "deliberate-violation sentinel branch" demonstration deferred
   to that flip event.

3. **A13 sys.modules watchdog + A18 rollback counter — when?**
   Both are observability-only (detect-not-prevent per Draft-rev4
   framing). v1.0 Accepted state ships without them. Expected
   landing: post-Codex-review polish or W3-W5 hardening sprint.
   Not enforcement-critical; not a re-open trigger.

## Methodology changes proposed

**No new methodology changes**. The existing v6.2 conventions
(autonomous-governance counter, RETRO-V61-001 cadence, stair-
anchor self-pass-rate calibration, three-round Opus Gate +
Codex post-merge review) handled this arc cleanly. Three points
of positive validation worth recording:

- **Stair anchor honored** — Claude Code did not bump the 0.87
  ceiling on a strong round-3 verdict; waited for actual Codex
  R1 APPROVE-clean to anchor up
- **§4.3a (b) compliance was correctly classified** — ADR-002
  artifacts (ADR doc + import-linter tooling + GitHub Actions
  step + tests) all fit allow-list b#3 / b#7 / b#8 without
  invoking (c) gray-zone Gate
- **post-R3 self-driven follow-up consolidation worked** —
  Draft-rev3's pre-emptive close of round-1 follow-ups
  (deferred-by-Opus to Accepted phase) produced a near-final
  state for round 3, saving one cycle

## Counter impact

ADR work is governance-class, not DEC-class. No
`autonomous_governance_counter_v61` increment. Counter remains
**43** (post-P1-arc end at RETRO-V61-004). Retrospective itself
is doc-only with no counter tick.

## Cross-refs

- ADR-002 file: `docs/adr/ADR-002-four-plane-runtime-enforcement.md`
- Notion ADR-002 page: 34dc6894-2bed-811c-9e0e-e822d11f21e0
  (Status=Active, 2026-04-25)
- Same-day P1 arc retro: `RETRO-V61-004`
  (`.planning/retrospectives/2026-04-25_p1_arc_complete_retrospective.md`)
- ADR-001 §2.7 cross-reference: amended in commit `efc25ce`
- §4.3a (b) compliance: recorded in ADR-002 §7 commit `acf1ffe`
- 12 same-day commits range: `e4d118a` (P1-verdict ops items) →
  `494455e` (Accepted flip + STATE stamp)
