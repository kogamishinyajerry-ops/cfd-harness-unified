---
decision_id: DEC-V61-161
title: N6.5 · LLM-offline rule-based fallback — broaden review path with mesh-quality advisor outputs
status: Accepted
parent_dec: V61-156
phase: N6
notion_sync_status: pending
---

# DEC-V61-161 · N6.5 · LLM-Offline Rule-Based Fallback

## Scope

Broaden the offline-mode `review_case` output by stitching
`mesh_quality/advisor::derive_suggestions` (DEC-V61-138) onto the
existing N5.2 IssueList → ReviewFinding pipeline. When LLM is
unavailable, the engineer now sees fine-grained mesh-quality fix
advice (non-orthogonal patches, skewness, aspect ratio,
severe-face counts) — not just the binary `mesh_checkmesh_failed`
flag from N5.2.

## Surface delivered

- `ui/backend/services/ai_advisor/fallback.py` — orchestrator
  module with:
  - `broaden_review_findings(case_dir, base_findings, corpus)` —
    appends mesh-advisor outputs to base findings; gracefully no-ops
    when no mesh / clean mesh / corpus has no matching chunk
  - `_suggestion_to_finding(sug, corpus)` — unit-testable
    conversion helper from `MeshFixSuggestion` → `ReviewFinding`
    with citation grounding
  - `_serialize_recommended_change(rec)` — dict → plain prose
- `ui/backend/services/ai_advisor/review.py` — both offline
  branches (mock provider + LLM-call-failed) now call broaden
- `ui/backend/tests/test_ai_advisor_contract.py` —
  `_AI_DISPATCH_MODULES` extended with `fallback.py`
- `ui/backend/tests/test_n6_5_offline_fallback.py` — 14 tests

## V1 scope deferrals

Per charter §sequencing ("rule-based subset of N6.2/N6.3 templates
derived from existing emitters") — V1 ships mesh-quality advisor
wiring only. Deferred to V1.1 (no charter or sub-DEC needed; can
land as a follow-up commit when prioritized):

- `physics/urf_advisor` wiring — needs URFOverride + RegimeContract
  reader from `system/fvSolution` + `constant/momentumTransport`
- `case_solve/timing_advisor` wiring — needs controlDict reader
- Diagnose-path broadening — N6.3's residual classifier already
  covers solver-failure hypothesis space; mesh-advisor output is
  review-shaped, not failure-mode-shaped

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Workbench remains 100% functional; `review_case` offline path now emits both N5.2 issue findings AND mesh-advisor fix advice |
| Q2 | Artifacts output? | ✅ Same ReviewResponse schema; `findings[]` carries broadened set; `degradation_note` updated to acknowledge new sources |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Each broadened finding has corpus citation (chunk_id resolves to loaded chunk); missing citation → finding dropped |
| Q4 | AI advisory only (no mutating call)? | ✅ Fallback module not in `KNOWN_MUTATION_FUNCTIONS`; AST scan asserts no mutation symbol imported; `derive_suggestions` is itself read-only by V130 contract; lazy-import isolates the import-graph dependency from non-fallback paths |

## Verification

- 14/14 N6.5 tests pass
- 21/21 V132 contract tests pass (Layer-C now scans 7 N6 modules: route + corpus + review + diagnose + safety + fallback + init; +1 parametrized case vs N6.4)
- 36/36 N6.3 + 39/39 N6.2 + 25/25 N6.1 — no regressions
- Backend total across N6 + V132: 135/135 green
- Defensive design verified: no-mesh case, clean mesh, missing
  corpus, malformed advisor output — all gracefully return base
  findings unchanged

## Confidence

`high` — orchestrator wraps existing read-only emitters with
defensive try/except gates; the fallback module never causes the
route to 5xx (verified by test). All emitter outputs go through
the same citation-grounding contract that N6.2 already enforces.

## Codex pre-merge review

Per charter: charter says N6.5 is "per Opus confidence" (not a
V132 contract surface change — fallback is a service, not a route).
Confidence high; no Codex review.

## Notes

- `_serialize_recommended_change` does NOT apply
  `safety.has_action_text` because mesh-advisor outputs are
  hand-curated (DEC-V61-138 controlled text) and never contain
  HTTP / route / button-label phrasing. The action-text strip
  remains reserved for LLM-generated text where the contract
  relies on prompt compliance.
- Lazy import of `mesh_quality` modules inside
  `broaden_review_findings` keeps the import-graph dependency
  contained — N6.2 LLM path doesn't pay the numpy/docker SDK
  import cost.
- Fallback emits findings with `source: "rule_based"` so the UI
  renders them with a "rule-based" badge alongside source:"llm"
  findings (N6.4 already supports both).

## References

- DEC-V61-156 · N6 charter
- DEC-V61-138 · N2.4 checkMesh advisor (mesh-quality emitter consumed)
- DEC-V61-153 · N5.2 honest issue list (already wired in N6.2)
- DEC-V61-148 · N4.3 URF advisor (deferred wiring)
- DEC-V61-150 · N4.5 timing advisor (deferred wiring)
