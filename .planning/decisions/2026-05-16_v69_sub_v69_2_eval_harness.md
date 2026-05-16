---
decision_id: DEC-V69-2
title: V69.2 · Canonical advisor eval regression harness (22 tests · 0.07s)
status: Accepted
parent_dec: DEC-V69-charter
phase: V69
notion_sync_status: pending
batch: B154
confidence: high
autonomous_governance: true
verdict: LANDED
---

# DEC-V69-2 · Eval regression harness

## 1 · Decision

Author `ui/backend/tests/test_canonical_advisor_eval.py` as the AI-advisor SSOT regression gate. Harness reads each `.planning/evals/canonical/E*.md` file, parses YAML frontmatter, and asserts:

1. Frontmatter parses (10 required fields present)
2. `eval_case_id` matches filename prefix
3. Each canonical case lists ≥3 expected advisor firings
4. Each cited advisor exists in `assemble_stack` surface (skip-listed if known F-NEW)
5. Aggregate firings ≥100 across the 20 cases
6. No gaps E01..E20 (must be contiguous)

22 tests (20 parametrized + 2 aggregate) · 22 passed in 0.07s · charter ≤5s budget exceeded.

## 2 · Honest scope: KNOWN_F_NEW_ADVISORS skip set

V66-B planned but never landed 6 advisors:
- `cf_canonical_choice`
- `low_re_kOmegaSST_trigger`
- `yplus_regime_match`
- `yplus_target_validation`
- `substrate_inspection`
- `residual_gate_qualifier`

Skip-list documented in test file head comment + `.planning/followups/v69_v66b_planned_advisors_not_landed.md` with 3 disposition options. This is **structural honesty** — not hiding the 6 misses.

## 3 · Done dims

V69-DONE-2 MET. V69-DONE-4 partial (regression-protected · skip list explicit).

## 4 · Evidence

- `ui/backend/tests/test_canonical_advisor_eval.py` — 22/22 PASS
- `.planning/followups/v69_v66b_planned_advisors_not_landed.md` — 6 missing advisors disclosed
- Commit `ccc0b97` · B154
