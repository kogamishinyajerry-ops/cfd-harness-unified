"""P1-T5 · task_runner TrustGateReport integration tests.

Verifies that `_build_trust_gate_report` correctly aggregates the
existing ComparisonResult + AttestationResult outputs into a
TrustGateReport populated on the RunReport, without changing the
comparator/attestor paths themselves.

Scenarios covered:
  - clean pass (ATTEST_PASS + comparison.passed=True) → overall PASS
  - gold miss (ATTEST_PASS + comparison.passed=False) → overall FAIL
  - attestor HAZARD + gold pass → overall WARN
  - attestor FAIL (short-circuits comparator) → overall FAIL, only
    attestation report present
  - no attestation + no comparison (edge case) → trust_gate_report=None
  - attestor NOT_APPLICABLE (no log) → overall WARN
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.metrics import MetricClass, MetricStatus
from src.models import ComparisonResult, DeviationDetail, ExecutionResult
from src.task_runner import _build_trust_gate_report


class _FakeAttestorCheck:
    """Duck-typed check (matches src.convergence_attestor.AttestorCheck fields
    used by _build_trust_gate_report — no need to import the real class for
    tests since the helper only reads .verdict / .check_id / .concern_type /
    .summary)."""

    def __init__(
        self, check_id: str, concern_type: str, verdict: str, summary: str = ""
    ) -> None:
        self.check_id = check_id
        self.concern_type = concern_type
        self.verdict = verdict
        self.summary = summary


class _FakeAttestation:
    def __init__(self, overall: str, checks: list) -> None:
        self.overall = overall
        self.checks = checks


# ---------------------------------------------------------------------------
# Clean pass path
# ---------------------------------------------------------------------------


def test_clean_attest_pass_plus_comparison_pass_yields_overall_pass() -> None:
    attestation = _FakeAttestation(
        overall="ATTEST_PASS",
        checks=[
            _FakeAttestorCheck("A1", "SOLVER_CRASH_LOG", "PASS"),
            _FakeAttestorCheck("A2", "CONTINUITY", "PASS"),
        ],
    )
    comparison = ComparisonResult(
        passed=True,
        deviations=[],
        summary="Quantity: cd_mean | Tolerance: 5.0% | PASS",
        gold_standard_id="backward_facing_step",
    )
    tg = _build_trust_gate_report(
        task_name="bfs", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.PASS
    assert tg.count_by_status[MetricStatus.PASS] == 2
    assert tg.count_by_status[MetricStatus.FAIL] == 0
    # Two synthetic reports: attestation + comparison
    assert len(tg.reports) == 2
    names = {r.name for r in tg.reports}
    assert "bfs_convergence_attestation" in names
    assert "bfs_gold_comparison" in names


# ---------------------------------------------------------------------------
# Gold miss → overall FAIL
# ---------------------------------------------------------------------------


def test_gold_miss_with_clean_attestation_yields_overall_fail() -> None:
    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    comparison = ComparisonResult(
        passed=False,
        deviations=[
            DeviationDetail(
                quantity="cd_mean",
                expected=1.0,
                actual=1.5,
                relative_error=0.5,
                tolerance=0.1,
            )
        ],
        summary="Quantity: cd_mean | deviation 0.5 > 0.1",
        gold_standard_id="bfs",
    )
    tg = _build_trust_gate_report(
        task_name="bfs", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.FAIL
    # attestation report → PASS, comparison → FAIL
    assert tg.count_by_status[MetricStatus.PASS] == 1
    assert tg.count_by_status[MetricStatus.FAIL] == 1
    # Deviation surfaced on the comparison MetricReport
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.deviation == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Attestor HAZARD → overall WARN (when gold passes)
# ---------------------------------------------------------------------------


def test_attestor_hazard_plus_gold_pass_yields_overall_warn() -> None:
    attestation = _FakeAttestation(
        overall="ATTEST_HAZARD",
        checks=[
            _FakeAttestorCheck(
                "A2",
                "CONTINUITY_NOT_CONVERGED",
                "HAZARD",
                "sum_local=5e-4 exceeds floor",
            ),
        ],
    )
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="PASS", gold_standard_id="x"
    )
    tg = _build_trust_gate_report(
        task_name="x", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.WARN
    # hazard notes surfaced
    assert any("A2" in n or "CONTINUITY" in n for n in tg.notes)


# ---------------------------------------------------------------------------
# Attestor FAIL short-circuits comparator (comparison=None)
# ---------------------------------------------------------------------------


def test_attestor_fail_with_no_comparison_yields_overall_fail() -> None:
    attestation = _FakeAttestation(
        overall="ATTEST_FAIL",
        checks=[
            _FakeAttestorCheck(
                "A1", "SOLVER_CRASH_LOG", "FAIL", "FOAM FATAL ERROR"
            ),
        ],
    )
    # task_runner skips comparator when ATTEST_FAIL, so comparison is None
    tg = _build_trust_gate_report(
        task_name="x", comparison=None, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.FAIL
    assert len(tg.reports) == 1
    assert tg.reports[0].name == "x_convergence_attestation"
    assert tg.reports[0].metric_class is MetricClass.RESIDUAL
    assert tg.reports[0].provenance["attest_verdict"] == "ATTEST_FAIL"


# ---------------------------------------------------------------------------
# Neither attestation nor comparison → None
# ---------------------------------------------------------------------------


def test_no_inputs_returns_none() -> None:
    tg = _build_trust_gate_report(
        task_name="x", comparison=None, attestation=None
    )
    assert tg is None


# ---------------------------------------------------------------------------
# Attestor NOT_APPLICABLE → overall WARN (no solver log resolvable)
# ---------------------------------------------------------------------------


def test_attestor_not_applicable_yields_overall_warn() -> None:
    attestation = _FakeAttestation(overall="ATTEST_NOT_APPLICABLE", checks=[])
    comparison = ComparisonResult(
        passed=True, deviations=[], summary="PASS", gold_standard_id="x"
    )
    tg = _build_trust_gate_report(
        task_name="x", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    # attestation → WARN, comparison → PASS. worst-wins → WARN.
    assert tg.overall is MetricStatus.WARN


# ---------------------------------------------------------------------------
# E2E via actual TaskRunner.run_task — verifies RunReport.trust_gate_report
# is populated by the integrated call site (not just the helper directly).
# ---------------------------------------------------------------------------


def test_run_report_populates_trust_gate_on_happy_path(tmp_path: Path) -> None:
    """Full pipeline: MockExecutor + attestor + comparator → RunReport.
    trust_gate_report should be present and PASS/WARN/FAIL consistent with
    the attestation+comparison inputs."""
    from unittest.mock import MagicMock

    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )
    from src.task_runner import TaskRunner

    # Write a clean solver log so attestor returns ATTEST_PASS.
    log_dir = tmp_path / "solver_output"
    log_dir.mkdir()
    (log_dir / "log.simpleFoam").write_text(
        "Time = 1\nExecutionTime = 1 s\nEnd\n", encoding="utf-8"
    )

    class _CleanExecutor:
        def execute(self, task_spec):
            return ExecutionResult(
                success=True,
                is_mock=False,
                key_quantities={"u_centerline": [0.025]},
                raw_output_path=str(log_dir),
                exit_code=0,
            )

    stub_notion = MagicMock()
    stub_notion.write_execution_result = MagicMock()
    stub_db = MagicMock()
    stub_db.load_gold_standard = MagicMock(return_value=None)  # no gold → no comparison
    stub_db.save_correction = MagicMock()

    runner = TaskRunner(
        executor=_CleanExecutor(),
        notion_client=stub_notion,
        knowledge_db=stub_db,
    )
    task = TaskSpec(
        name="lid_driven_cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )

    report = runner.run_task(task)

    # With no gold → no comparison. Only attestation contributes.
    # ATTEST_PASS → overall PASS.
    assert report.trust_gate_report is not None
    assert report.trust_gate_report.overall is MetricStatus.PASS
    assert len(report.trust_gate_report.reports) == 1
    assert (
        report.trust_gate_report.reports[0].name
        == "lid_driven_cavity_convergence_attestation"
    )


# ---------------------------------------------------------------------------
# Codex V61-056 finding #1: ATTEST_NOT_APPLICABLE with no concerns must still
# surface the WARN reason — previously silently dropped.
# ---------------------------------------------------------------------------


def test_attestor_not_applicable_surfaces_explicit_note() -> None:
    attestation = _FakeAttestation(overall="ATTEST_NOT_APPLICABLE", checks=[])
    tg = _build_trust_gate_report(
        task_name="x", comparison=None, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.WARN
    assert len(tg.reports) == 1
    residual = tg.reports[0]
    assert residual.notes is not None
    assert "not applicable" in residual.notes.lower()
    # And the formatted note flows through to TrustGateReport.notes tuple
    assert any("not applicable" in n.lower() for n in tg.notes)


# ---------------------------------------------------------------------------
# Codex V61-056 finding #2: Deviation-extraction edge case when comparison
# has deviations but all relative_error values are None.
# ---------------------------------------------------------------------------


def test_comparison_with_none_relative_errors_yields_no_deviation() -> None:
    attestation = _FakeAttestation(overall="ATTEST_PASS", checks=[])
    # Comparison with deviations but none carrying relative_error (legacy
    # comparator code paths existed that produced abstract-deviation records
    # without numeric error). Wrapper must not crash and must leave
    # MetricReport.deviation = None.
    comparison = ComparisonResult(
        passed=False,
        deviations=[
            DeviationDetail(
                quantity="x",
                expected=1.0,
                actual=None,
                relative_error=None,
                tolerance=0.05,
            ),
        ],
        summary="Quantity x not found in execution result",
        gold_standard_id="x",
    )
    tg = _build_trust_gate_report(
        task_name="x", comparison=comparison, attestation=attestation
    )
    assert tg is not None
    assert tg.overall is MetricStatus.FAIL  # comparison.passed=False
    gold_report = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    assert gold_report.deviation is None  # no relative_error available
    assert gold_report.status is MetricStatus.FAIL


# ---------------------------------------------------------------------------
# Codex V61-056 finding #2b: E2E TaskRunner with gold present (comparison
# branch actually exercised, not just attestation-only).
# ---------------------------------------------------------------------------


def test_run_report_populates_trust_gate_with_comparison_present(
    tmp_path: Path,
) -> None:
    from unittest.mock import MagicMock

    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )
    from src.task_runner import TaskRunner

    log_dir = tmp_path / "solver_output"
    log_dir.mkdir()
    (log_dir / "log.simpleFoam").write_text(
        "Time = 1\nExecutionTime = 1 s\nEnd\n", encoding="utf-8"
    )

    class _Executor:
        def execute(self, task_spec):
            return ExecutionResult(
                success=True,
                is_mock=False,
                key_quantities={"u_centerline": 0.98},
                raw_output_path=str(log_dir),
                exit_code=0,
            )

    # Gold declares quantity=u_centerline, ref=1.0, tolerance=0.05. Actual=0.98,
    # deviation=0.02 < tolerance → comparison PASSes.
    gold = {
        "quantity": "u_centerline",
        "reference_values": [{"value": 1.0}],
        "tolerance": 0.05,
        "id": "lid_driven_cavity",
    }
    stub_notion = MagicMock()
    stub_notion.write_execution_result = MagicMock()
    stub_db = MagicMock()
    stub_db.load_gold_standard = MagicMock(return_value=gold)
    stub_db.save_correction = MagicMock()

    runner = TaskRunner(
        executor=_Executor(),
        notion_client=stub_notion,
        knowledge_db=stub_db,
    )
    task = TaskSpec(
        name="lid_driven_cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )
    report = runner.run_task(task)

    # ATTEST_PASS + comparison PASS → overall PASS, 2 reports
    assert report.trust_gate_report is not None
    assert report.trust_gate_report.overall is MetricStatus.PASS
    assert len(report.trust_gate_report.reports) == 2
    names = {r.name for r in report.trust_gate_report.reports}
    assert names == {
        "lid_driven_cavity_convergence_attestation",
        "lid_driven_cavity_gold_comparison",
    }
