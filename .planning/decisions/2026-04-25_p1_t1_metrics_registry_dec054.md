---
decision_id: DEC-V61-054
title: P1-T1 Metrics Registry + 4 Metric-Class extractor wrappers · MVP landed · Codex review pending
supersedes_gate: none
intake_ref: none (P1 task-level DEC, not a Foundation-Freeze gate)
methodology_version: "v2.0 (per RETRO-V61-001 + RETRO-V61-053 addendum)"
commits_in_scope:
  - 2b5ceb7 feat(metrics) P1-T1 MetricsRegistry MVP skeleton (7 src/metrics/ files + 12 registry tests + ADR-001 §2.1 plane table + .importlinter additions)
  - d333122 chore(state) STATE.md P1-T1 skeleton landed stamp
  - 9b7aeaf feat(metrics) P1-T1ab Pointwise+Integrated wrappers via _comparator_wrap helper (12 tests)
  - 27c42fe feat(metrics) P1-T1c SpectralMetric WARN-on-low-confidence demotion (9 tests + wrapper-level deviation-gate fix)
  - 1dd91eb feat(metrics) P1-T1d ResidualMetric attestor-verdict → MetricStatus mapping (10 tests)
codex_verdict: PENDING_POST_MERGE_REVIEW (batched arc review to run against commits 2b5ceb7..1dd91eb)
autonomous_governance: true
autonomous_governance_counter_v61: 41
external_gate_self_estimated_pass_rate: 0.75
external_gate_self_estimated_pass_rate_source: "Wrapper-level deviation-gate override (fix for comparator ref-key gap) + 3 verdict-translation mappings (ATTEST_* → MetricStatus, low_confidence demotion, PASS→FAIL override) are non-obvious. Tests cover happy + 3-4 failure modes per class. 619 pass overall. 4 import contracts KEPT. Moderate confidence; Codex may flag edge cases around tolerance-policy dispatch or provenance key name conventions."
external_gate_caveat: "First concrete implementation of METRICS_AND_TRUST_GATES v0.1 Draft accepting clause (VCP §8.2 tolerance_policy dispatch). SpectralMetric/ResidualMetric wrappers add verdict-translation logic that did not exist before; Pointwise/Integrated reuse existing result_comparator so regression risk is contained. No production code touched outside src/metrics/. ADR-001 Contract 2 honored — Evaluation plane does not import cylinder_strouhal_fft (classified Execution); SpectralMetric reads pre-extracted scalars from ExecutionResult.key_quantities instead."
codex_tool_report_path: reports/codex_tool_reports/dec_v61_054_p1_t1_arc_review.log (to be written by /codex-gpt54)
notion_sync_status: pending
github_sync_status: pushed (5 commits on origin/main)
reversibility: MEDIUM — reverting 5 commits would remove src/metrics/ package entirely; no downstream consumers yet (TrustGate reducer is P1-T2, next DEC). Single atomic revert is safe.
canonical_follow_up: "P1-T2 TrustGate overall-verdict reducer (consumes List[MetricReport] → TrustGateReport with PASS/WARN/FAIL). P1-T3 CaseProfile.tolerance_policy YAML schema + loader. P1-T4 Knowledge schema ObservableDef formalization (currently ad-hoc dict)."
---

# DEC-V61-054 · P1-T1 Metrics Registry + 4 Metric-Class Wrappers

## Scope

First concrete implementation of the P1 Metrics & Trust Layer per
PIVOT_CHARTER §7. Delivers the Evaluation-plane `src.metrics` package:

- **Metric ABC + MetricReport dataclass + MetricStatus/Class enums** (commit 2b5ceb7)
- **MetricsRegistry** (register / lookup / filter_by_class / evaluate_all)
- **4 Metric subclasses with real `evaluate()` impls**:
  - `PointwiseMetric` → `src.result_comparator.ResultComparator.compare()` (commit 9b7aeaf)
  - `IntegratedMetric` → same comparator, different `metric_class` label (commit 9b7aeaf)
  - `SpectralMetric` → shared comparator + `low_confidence` flag demotion (commit 27c42fe)
  - `ResidualMetric` → `src.convergence_attestor.attest()` with verdict mapping (commit 1dd91eb)

## Key design decisions

1. **Pointwise + Integrated share the wrapper**: at the extractor level
   the semantic is identical (scalar float or profile list). `metric_class`
   carries the distinction for downstream tolerance-policy dispatch per
   VCP §8.2.

2. **SpectralMetric consumes pre-extracted scalars, not the FFT itself**:
   `src.cylinder_strouhal_fft` is classified Execution Plane in ADR-001
   §2.1 (it's invoked from `foam_agent_adapter` as part of the solver
   pipeline). Evaluation Plane cannot import Execution per Contract 2.
   The FFT runs upstream; SpectralMetric reads `strouhal_number` +
   `{quantity}_low_confidence` from `ExecutionResult.key_quantities`
   and adds the WARN demotion on low-confidence flag.

3. **Wrapper-level deviation gate** (fix landed in 27c42fe):
   `result_comparator._compare_scalar`'s ref-dict-key list is
   `{value, Nu, Cp, Cf, u_plus, f}` — missing "St" and others. When
   observable uses an unrecognized key, comparator silently returns
   `passed=True`. The `_comparator_wrap` helper now independently
   re-gates on `deviation > tolerance_applied` and demotes PASS→FAIL
   with a wrapper-level note so TrustGate doesn't see a bogus PASS.

4. **ResidualMetric uses attestor verdicts, not gold-standard refs**:
   `value`, `reference_value`, `deviation`, `tolerance_applied` are all
   None on ResidualMetric reports — the `AttestVerdict` string is
   surfaced via `provenance.attest_verdict`. Status mapping:
   PASS/HAZARD/FAIL/NOT_APPLICABLE → PASS/WARN/FAIL/WARN.
   `NOT_APPLICABLE → WARN` (not PASS) so downstream TrustGate cannot
   silently pass on a missing solver log.

## Plane contract verification

ADR-001 §2.1 Evaluation-plane additions:
- `src.metrics.*` added to 3 forbidden contracts (Evaluation→Execution HARD NO as source; Knowledge no-reverse as forbidden; models-pure as forbidden)

All 4 contracts KEPT after each commit. 619 tests pass (43 new in
`tests/test_metrics/`).

## Test coverage summary

| File | Tests | Covers |
|------|-------|--------|
| `test_registry.py` | 12 | CRUD, filter_by_class, evaluate_all iteration, skip-missing-observable-def, metadata invariants |
| `test_pointwise_integrated.py` | 12 | scalar PASS/FAIL, missing quantity, tolerance-policy override, dict/ExecutionResult coercion, alias resolution |
| `test_spectral.py` | 9 | PASS, WARN-on-low-confidence (3 key-discovery shapes), FAIL-not-upgraded, missing quantity, tolerance-policy override |
| `test_residual.py` | 10 | PASS/WARN/FAIL/NOT_APPLICABLE mapping, log-path resolution (4 shapes), all-6-checks provenance |

## Why autonomous_governance=true

P1-T1 is an internal Evaluation-plane module addition with no public
API surface changes, no frontend impact, no OpenFOAM solver changes,
no API contract / adapter boundary changes. Reuses existing extractors
(result_comparator, convergence_attestor) verbatim. Test coverage
comprehensive at class-level. Codex post-merge review is the
governance check; no pre-merge gate required under RETRO-V61-001 rules.

## Post-merge Codex review protocol

Batched arc review (5 commits 2b5ceb7..1dd91eb) to run via `/codex-gpt54`
with focus areas:
1. Verdict-translation edge cases (ATTEST_NOT_APPLICABLE vs silent PASS; WARN demotion interaction with FAIL)
2. Wrapper-level deviation-gate correctness (is `tolerance_applied is not None` the right guard?)
3. Log-path resolution priority order (observable_def override vs ExecutionResult.raw_output_path — any shadowing bugs?)
4. Tolerance-policy dispatch (registry passes `tolerance_policy.get(name, tolerance_policy)` — the fallback-to-whole-dict behavior may produce unexpected per-metric tolerance when policy has a top-level "tolerance" key)
5. Provenance key name convention (is `low_confidence_key` / `{quantity}_low_confidence` / `strouhal_low_confidence` priority order defensible?)
6. ADR-001 plane boundary on `_comparator_wrap` — does it correctly stay Evaluation-only?
