---
decision_id: V61-231
title: Advisory-honesty hardening — out-of-scope verdict SKIPPED (no fabrication) + machine-checked zero-LLM-on-POST-/ai-review invariant
status: Proposed
accepted_date:
parent_dec:
phase: positioning-optimization (multi-agent role taxonomy arc · §5 P2 items)
autonomous_governance: true
confidence: high
kogami_opt_in: false (two small honesty hardenings; reversible; no §11.1 workbench-freeze paths)
round_cap: 3
codex_review_relay: pending (CRS gpt-5.4 — 86gs saturated by cross-project reviews this session)
codex_verdict: pending
codex_tool_report_path:
touches_shared_dec: src/auto_verifier/verifier.py (verdict producer) — verdict field consumed across ≥3 paths (report_engine/data_collector, report_engine/visual_acceptance, audit_package/reference_lookup) → DEC · ui/backend/routes/ai_review.py invariant (test-only, no prod change)
notion_sync_status: N/A (Proposed; syncs only on Accepted)
date: 2026-06-07
---

# DEC-V61-231 · Advisory-honesty hardening (§5 P2 items)

## Context

Roadmap §5 two P2 honesty items: (P2a) "AutoVerifier ... 缺证据时必须保持 SKIPPED, 绝不凭空
造 verdict"; (P2b) "明确 ai_review POST 路由'刻意不调 provider'的不变量 + 文档化". Both are
"引擎不撒谎" hardenings — the first fixes a real fabrication, the second machine-pins an
existing invariant.

## P2a — out-of-scope verdict fabrication (real defect, fixed)

`src/auto_verifier/verifier.py` early-returns for any case outside the Phase-7 anchor set
(`case_id not in ANCHOR_CASE_IDS`) with honest `convergence.status="UNKNOWN"` +
`gold_standard_comparison.overall="SKIPPED"` — BUT it stamped **`verdict="PASS_WITH_DEVIATIONS"`**
on that unverified case. Safe-refactor caller analysis confirmed this was LIVE-impacting:
downstream report engines bucket that verdict with *passing* cases —
- `report_engine/data_collector.py:125`: success bucket `{"PASS","PASS_WITH_DEVIATIONS"}`
- `report_engine/visual_acceptance.py:496`: PASS_WITH_DEVIATIONS tally
- `audit_package/reference_lookup.py:244`: non-negative → treated acceptable

So an unverified out-of-scope case was reported as acceptable — fabricating a verdict with
zero evidence. **Fix**: `verdict="SKIPPED"` (the verdict vocabulary is `str`, schemas.py:103;
`SKIPPED` already exists in the sibling `overall` vocab). In-scope cases are UNTOUCHED — they
still resolve to PASS/PASS_WITH_DEVIATIONS/FAIL via `_determine_verdict`. Consumers handle
`SKIPPED` gracefully (it falls in no success/fail bucket → displayed as itself, not counted as
pass). `reference_lookup` returns "acceptable" for both old+new (separate permissive contract,
out of scope here — flagged for a possible follow-up).

## P2b — zero-LLM-on-POST-/ai-review invariant (machine-pinned)

`ui/backend/routes/ai_review.py::_try_llm_enhance` late-imports `get_default_provider` ONLY as
an importability probe and explicitly never invokes it (source comment ai_review.py:686-692).
This kept the 4-question advisory-only gate honest (zero LLM call on POST). The invariant lived
only in a comment; now machine-checked by a test that patches the provider factory and asserts
`call_count == 0` + degrades to `llm_enhanced=False` when the provider is unimportable. NO
production code changed.

## Verification

- `tests/test_auto_verifier/` + `tests/test_report_engine/`: 89 passed (P2a consumer-safety).
- `ui/backend/tests/test_ai_review_no_llm_invocation_dec231.py` (2) + `test_ai_review_route.py`
  (43): 45 passed (P2b invariant + no regression).
- New regression in `tests/test_auto_verifier/test_schema.py`: out-of-scope `verdict=="SKIPPED"`
  AND `verdict not in {"PASS","PASS_WITH_DEVIATIONS"}`.

## Reversibility / blast radius

- **P2a**: reversibility high (1-line producer change + additive verdict value). Blast radius
  low-med: changes out-of-scope reporting from pass-ish to SKIPPED (the CORRECT honest direction);
  no consumer breaks (89 tests green). Behavior change is intentional + desired.
- **P2b**: test-only, zero risk.

## Status

Status=**Proposed** pending Codex review. NOT pushed. On Codex APPROVE → Status=Accepted.
Deferred follow-ups: `reference_lookup` permissive non-negative=acceptable contract;
the THIRD reducer `cwos_status.py` (from DEC-230); harden-A-fail-closed (from DEC-230).
