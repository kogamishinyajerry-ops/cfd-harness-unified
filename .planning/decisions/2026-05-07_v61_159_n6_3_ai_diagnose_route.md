---
decision_id: DEC-V61-159
title: N6.3 · AI 诊断 (case diagnose) advisor route — GET /api/cases/{id}/ai-diagnose with bounded log read + path containment
status: Accepted
parent_dec: V61-156
phase: N6
notion_sync_status: pending
---

# DEC-V61-159 · N6.3 · AI 诊断 Advisor Route

## Scope

Read-only `GET /api/cases/{case_id}/ai-diagnose` route returning a
citation-grounded `DiagnoseResponse`. LLM path uses N6.1 corpus +
N5.2 IssueList + bounded solver-log tail; offline path emits
rule-based hypotheses from issue signals + residual-trajectory
classification. Optional `?problem=` query param (validated against
`FailureMode` literal whitelist before service entry).

## Surface delivered

- `ui/backend/schemas/ai_advisor.py` — `DiagnosisHypothesis`,
  `DiagnoseResponse`, `FailureMode`, `HypothesisLikelihood`
- `ui/backend/services/ai_advisor/safety.py` — extracted
  `has_action_text` + `ACTION_TEXT_PATTERNS` (shared with N6.2;
  source-of-truth for advisory-only sanitizer)
- `ui/backend/services/ai_advisor/diagnose.py` — `diagnose_case`,
  bounded log read with symlink-escape rejection, residual
  trajectory classifier (`stalled_residuals` /
  `diverging_residuals`), rule-based hypothesis emitter
- `ui/backend/services/ai_advisor/review.py` — refactored to import
  shared `has_action_text` from `safety.py` (no behavior change)
- `ui/backend/routes/ai_advisor.py` — second GET endpoint with
  `FailureMode` whitelist validation on `?problem=` param + same
  loopback guard as `/ai-review`
- `ui/backend/tests/test_ai_advisor_contract.py` —
  `_AI_DISPATCH_MODULES` extended with diagnose + safety modules
- `ui/backend/tests/test_n6_3_ai_diagnose.py` — 30 tests

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ MockLLMProvider triggers rule-based hypotheses derived from N5.2 IssueList signals + residual-trajectory classifier; route returns 200 + populated hypotheses on populated cases |
| Q2 | Artifacts output? | ✅ DiagnoseResponse JSON with case_id + hypotheses[] + corpus_sha + degradation_note + problem_hint + generated_at; pipeable through `jq` |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Each hypothesis cites `citation.chunk_id` + path + sha; structured `evidence` dict carries verifiable observations; `corpus_sha` is corpus fingerprint; `llm_available` exposes degradation |
| Q4 | AI advisory only (no mutating call)? | ✅ Route is GET (idempotent); module path in `_AI_DISPATCH_MODULES`; V132 Layer-A sentinel patches across LLM + offline branches assert zero mutation invocations; Layer-C AST scan asserts no mutation symbol imported; **read-only file ops** (log paths contained under `case_dir.resolve()` with symlink-escape rejection); shared `has_action_text` drops route descriptors / button labels / shell mutations from LLM output |

## Verification

- 30/30 N6.3 tests pass
- 20/20 V132 contract tests pass (Layer-C now scans 6 N6 modules: route + 4 services + safety; +2 parametrized cases vs N6.2)
- 39/39 N6.2 tests pass (no regression after safety extraction)
- 25/25 N6.1 tests pass
- Path containment verified: symlinked log to `tmp_path/rogue.log` outside case_dir is NOT followed; rogue residual signal does not surface
- Bounded log read verified: 1MB synthetic log truncates to last 256KiB without memory blow-up
- Action-text strip applies to both `summary` and `suggested_fix` fields
- Non-string LLM output handled per Codex N6.2 R1 P1 lesson (test parametrized over list/dict/int/bool)

## Codex pre-merge review

Per charter: V132 contract surface change extends v2.2 1-sync-trigger.

**Pre-emptive Codex-aware design** (carried lessons from N6.2 R0+R1):
- Loopback guard wired from the start
- Action-text strip via shared `has_action_text` (covers summary +
  suggested_fix); same regex set as N6.2
- Type-safe `has_action_text` for non-string LLM fields
- Path containment + symlink-escape rejection on log read
- Bounded log read (256KiB cap, last 200 lines)
- Whitelist validation on `?problem=` query param at route boundary
  (returns 400 with structured detail before service entry)
- Evidence dict server-side stringifies non-string values (Pydantic
  schema declares `dict[str, str]`)

Will run `codex-review-relay` once committed.

## Confidence

`high` — pre-emptive lessons from N6.2 round chain applied.
Refactor of `_has_action_text` → shared `safety.py` keeps both N6.2
and N6.3 single-sourced.

## Notes

- Sequencing followed charter: N6.3 reuses N6.2 schema patterns
  (citation REQUIRED, source: llm|rule_based, action-text strip)
- Residual trajectory classifier:
  - stalled: every consecutive delta < 1% relative change
  - diverging: monotonic increase by >10x over the window
- N5.2 → N6.3 reverse import edge avoided by re-implementing
  `_extract_recent_u_residuals` locally (5 LOC) rather than importing
  from `case_issues/enumerator.py`
- N6.5 will broaden the rule-based emitter set (currently 3
  failure-mode hypotheses; missing: thermal/multiphase/compressibility
  signals — those need new corpus content first)

## References

- DEC-V61-156 · N6 charter
- DEC-V61-157 · N6.1 corpus loader
- DEC-V61-158 · N6.2 AI 审查 (parent of safety.py extraction)
- DEC-V61-132 · MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS
- DEC-V61-153 · N5.2 honest issue list (consumed)
- DEC-V61-118/119 · LLM provider abstraction (reused)
