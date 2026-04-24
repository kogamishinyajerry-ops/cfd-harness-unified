---
decision_id: DEC-V61-056
title: P1-T5 task_runner TrustGateReport integration (Control→Evaluation minimal slice)
supersedes_gate: none
intake_ref: none (P1 task-level DEC)
methodology_version: "v2.0"
commits_in_scope:
  - bc91716 feat(task_runner) P1-T5 TrustGateReport integration (+7 tests)
codex_verdict: PENDING_POST_MERGE_REVIEW
autonomous_governance: true
autonomous_governance_counter_v61: 43
external_gate_self_estimated_pass_rate: 0.85
external_gate_self_estimated_pass_rate_source: |
  Additive integration — no refactor of comparator/attestor paths.
  Existing 25 task_runner tests continue to pass (backward-compat
  validated). 7 new tests cover full verdict mapping matrix including
  the 4-way AttestVerdict mapping + ATTEST_FAIL short-circuit + edge
  case (neither input → None). Self-confidence ~85%. Above 70% pre-
  merge trigger, so post-merge Codex is procedurally correct.
external_gate_caveat: |
  First Control→Evaluation integration (task_runner imports src.metrics).
  ADR-001 matrix row "Control | ✓ (orchestrate) |" authorizes this. No
  plane contract regression expected. Pre-P1-T4 ObservableDef formalization,
  synthetic MetricReports are produced in-place; a future P1-T4 landing
  will replace the 2-report reduction with full MetricsRegistry per task.
  The additive RunReport.trust_gate_report field means that transition
  can happen without breaking downstream consumers.
codex_tool_report_path: reports/codex_tool_reports/dec_v61_056_p1_t5_review.log (pending)
notion_sync_status: synced 2026-04-25T04:55 · Status=Proposed (page_id=34cc6894-2bed-81f1-b99e-eb962162691e, URL=https://www.notion.so/DEC-V61-056-P1-T5-task_runner-TrustGateReport-integration-Control-Evaluation-34cc68942bed81f1b99eeb962162691e)
github_sync_status: pushed (1 commit on origin/main locally; main not yet pushed to remote)
reversibility: MEDIUM — revert would remove one field (default None) from
  RunReport + one helper function + 1 test file. Downstream consumers don't
  yet read the field, so revert is safe.
canonical_follow_up: |
  P1-T4 ObservableDef formalization (blocked on KNOWLEDGE_OBJECT_MODEL
  Active). When P1-T4 lands, _build_trust_gate_report will be
  superseded by full MetricsRegistry-per-task instantiation. Downstream:
  UI consumption of trust_gate_report in Compare tab / dashboard.
---

# DEC-V61-056 · P1-T5 task_runner TrustGateReport Integration

## Scope

Wires the P1 Metrics & Trust Layer (DEC-V61-054 registry + DEC-V61-055
reducer) into the Control-plane task pipeline. RunReport now carries
a `trust_gate_report: Optional[TrustGateReport]` field populated by a
module-level `_build_trust_gate_report` helper.

## Design

**Additive, no-refactor**. The existing `ComparisonResult` and
`AttestationResult` paths remain untouched. The new helper converts
those outputs into synthetic MetricReports (per `src.metrics.base`
schema) and reduces them worst-wins via `src.metrics.reduce_reports`.

Synthetic report naming pattern:
- `{task_name}_convergence_attestation` (ResidualMetric class)
- `{task_name}_gold_comparison` (PointwiseMetric class)

Status mapping verbatim from ResidualMetric:
- `ATTEST_PASS` → PASS
- `ATTEST_HAZARD` → WARN (preserves diagnostic signal)
- `ATTEST_FAIL` → FAIL (comparator short-circuited upstream → 1 report only)
- `ATTEST_NOT_APPLICABLE` → WARN (no log → cannot silently PASS)
- `comparison.passed=True/False` → PASS / FAIL

Returns `None` only when both inputs are absent (edge case — Notion-only
path where executor never produced artifacts).

## Plane contract

Control → Evaluation: ADR-001 §2.2 matrix row `Control | ✓ (orchestrate)
|` authorizes this import direction. `.importlinter` unchanged —
`src.metrics` is Evaluation plane but is not in any Control-source
forbidden contract.

Post-commit `uv run lint-imports`: 4 kept / 0 broken.

## Transition path to P1-T4

When KNOWLEDGE_OBJECT_MODEL promotes from Draft to Active and P1-T4
ObservableDef formalization lands, `_build_trust_gate_report` will be
superseded by full MetricsRegistry-per-task instantiation:

1. Load CaseProfile.tolerance_policy via `load_tolerance_policy(case_id)`
2. Register MetricRegistry with observable-specific Metric subclasses
3. `registry.evaluate_all(artifacts, observable_defs, tolerance_policy)`
4. `reduce_reports(reports)` → TrustGateReport

Same `RunReport.trust_gate_report` field — downstream UI consumers
won't notice the change.

## Test coverage

- 7 new tests in `tests/test_task_runner_trust_gate.py`:
  - 5 direct-helper tests covering full verdict matrix
  - 1 edge case (no inputs → None)
  - 1 E2E via actual `TaskRunner.run_task` + MockExecutor + solver-log
    fixture
- 25 existing `test_task_runner.py` tests continue to pass

Full suite: 663 passed, 1 skipped. 4 import contracts KEPT.

## Post-merge Codex review protocol

1. Backward-compat: is `RunReport.trust_gate_report = None` default
   behavior preserved for all 25 existing test paths?
2. Status mapping consistency with `ResidualMetric._VERDICT_TO_STATUS`
   in `src/metrics/residual.py` — any drift?
3. Duck-typed `_FakeAttestation` / `_FakeAttestorCheck` in test file —
   does helper correctly read `.overall` / `.checks` / `.verdict` /
   `.check_id` / `.concern_type` / `.summary` without assuming the real
   dataclass?
4. Notes formatting — `f"{c.check_id}/{c.concern_type}: {c.summary}"` —
   stable format for UI consumption?
5. Deviation extraction from `ComparisonResult.deviations` — max
   relative_error across all DeviationDetails. Edge case: all deviations
   have `relative_error=None` → deviation=None. Covered?
6. Plane import: `from .metrics import ...` at top of task_runner.py
   crosses Control→Evaluation. ADR-001 matrix allows. Confirm no
   secondary imports that cross Evaluation→Execution.
7. Absence of tolerance_policy dispatch — this MVP doesn't call
   `load_tolerance_policy`. Is that defensible as a P1-T5 minimal-slice
   scope, deferred to P1-T4-followup?
