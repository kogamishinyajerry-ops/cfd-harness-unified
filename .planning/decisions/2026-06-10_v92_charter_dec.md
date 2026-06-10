---
decision_id: DEC-V92-charter
title: V92 Scoring-Evolution Arc · V78 scorer family 1-vote-veto → confirm-on-retry majority semantics (load-sensitive pillars only)
status: Accepted
accepted: 2026-06-10 (user verdict, same session as implementation commit a448e9d)
parent_dec: DEC-V91-close (2026-05-18_v91_close_dec.md) · V90/V91 retro Open Q #1
phase: V92 (scoring-evolution arc · user-mandated 2026-06-10)
notion_sync_status: n/a (Notion archive channel retired 2026-06-10 · DEC-V92-notion-retirement)
autonomous_governance: false  # external gate — user explicitly mandated direction ("V78 scorer 演进"); counter N/A per RETRO-V61-001
confidence: high
date: 2026-06-10
---

# DEC-V92-charter · Scorer confirm-on-retry semantics

## TL;DR

Evolve the two **load-sensitive** V78-family scorers (pillar #7 stability,
pillar #3 ux) from 1-vote-veto to **confirm-on-retry majority semantics**:
a failing unit (vitest run / playwright spec) only counts toward the score
penalty if it **fails again on retry**. Transient flakes are recorded as
telemetry subscores (auditable, zero penalty). Formulas, weights, the
16-pillar min one-vote-veto aggregation, and all 14 deterministic pillars
are **unchanged**.

This intentionally **ends the 14-arc no-scoring-change streak (V78→V91)**
— V90 retro explicitly deferred this evolution "until next real
scoring-evolution arc"; V92 is that arc, by user mandate (2026-06-10).
New streak baseline starts at the V92 scorer family.

## Evidence (2-arc CRITICAL · verbatim-anchored)

- **V90 iter-1** stability=70: 1-in-9 statistical vitest flake (9 isolation
  runs all PASS) cost a full extra close iteration. V90 retro:
  "treats any single flaky vitest subrun as −30 points, which is a 1-vote
  veto for a 1-in-N statistical noise event … consistently costing us
  1 extra iteration per arc (or per 2 arcs)."
  (`.planning/retrospectives/2026-05-18_v90_retro.md` L74-81)
- **V91 iter-2/3** ux=86: Playwright visual-baseline spec #50 timed out at
  5s under multi-process scoring load; isolation reproduces 1/1 PASS in
  8.9s. V91 retro: "Two pillars × one root cause = strong evidence the V78
  scorer family should evolve toward 'median of N runs' or 'majority-vote'
  semantics." (`.planning/retrospectives/2026-05-18_v91_retro.md` L60-72)

## Decision

**D1 · stability scorer** (`scripts/governance/v71_fleet/score_stability.sh`):
each failing vitest run gets exactly **one isolation retry**. Confirmed
fail (initial FAIL + retry FAIL) → counts in `flake_count` exactly as
before (−30 each). Transient flake (retry PASS) → `transient_flake_count`
subscore + evidence line, **0 penalty**. Formula
`100 − confirmed_fail×30 − mem_growth×5` shape unchanged. Test command
overridable via `STABILITY_TEST_CMD` env (default `npm run test`) to make
the vote logic testable.

**D2 · ux scorer** (`scripts/governance/v78_fleet/score_ux.sh`): run
playwright with `--retries=2`; per-spec vote via new helper
`scripts/governance/v92_fleet/pw_vote.py`: spec = PASS if **any attempt
passed**; `flaky` (eventually passed, ≥1 failed attempt) logged in
subscores + honest_note; `confirmed_failed` (no attempt passed) drives the
pro-rate exactly as before. Blocker subscore: when `confirmed_failed == 0`,
stderr timeout/click signals from eventually-passing attempts are classified
transient (no_blocker=15 + noise note); otherwise original grep behavior.

**D3 · unchanged**: pillar weights, the 60/25/15 ux split, the −30 flake
penalty, min-aggregation across 16 pillars, all deterministic pillars,
`score_all.sh` wiring (in-place edit; disposition: **extend**, no parallel
v92_fleet copy of the aggregator).

**D4 · anti-inflation guard** (SCORING-FRAMEWORK discipline): retries must
not silently mask real load-sensitivity regressions. Hard rule:
`flaky_specs ≥ 3` or `transient_flake_count ≥ 2` in a single iter →
mandatory mini-retro entry naming the flaky units. All transient counts are
emitted in the score artifact JSON/MD so the audit trail keeps the noise
visible.

**D5 · streak disposition**: 14-arc no-scoring-change streak (V78→V91)
ends here **by design**, recorded in this DEC. Historical scores remain
comparable for persistent failures (identical penalty); only transient-noise
events score differently (100 instead of 70/86) — i.e. strictly
noise-reduction, never threshold-loosening for confirmed regressions.

## Scope / blast radius

- Files: 2 scorer scripts (in-place) + 1 new helper + 1 new pytest module.
- No product code (src/, ui/) touched. No auth/signing/security boundary →
  no v2.2 1-sync Codex trigger; async post-merge Codex review optional.
- Reversibility: HIGH (git revert of 1 commit restores V78 semantics).
- Strategic package (intent/merge_risk YAML) not required — not a
  high-risk PR per DEC-V61-087 §4.4; Kogami opt-in not invoked (user may
  invoke per V133).

## Verification

- `pytest -q tests/governance/test_v92_scorer_vote.py` — pw_vote.py unit
  fixtures (all-pass / flaky-pass / confirmed-fail / parse-error / nested
  suites) + score_stability.sh integration via `STABILITY_TEST_CMD` fake
  (fail-once → score 100 + transient=1; fail-always → score 10 + confirmed=3).
- `bash -n` both edited scorers.
- Rollback trigger: any V92+ close iter where a confirmed regression was
  retried-away (found by D4 audit) → revert + retro.

## Open Qs carried

- Pillar-level min one-vote-veto across 16 pillars (different layer; not
  load-sensitive; out of scope here).
- Median-of-N as alternative semantics: rejected for now — full-suite ×N
  reruns are minutes-expensive (OpenFOAM-adjacent stacks); confirm-on-retry
  achieves the same noise rejection at marginal cost of retrying failures
  only.
