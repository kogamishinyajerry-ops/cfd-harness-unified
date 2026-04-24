"""ResidualMetric tests · P1-T1d.

Covers the full AttestVerdict → MetricStatus mapping:
  ATTEST_PASS           → PASS
  ATTEST_HAZARD         → WARN
  ATTEST_FAIL           → FAIL
  ATTEST_NOT_APPLICABLE → WARN (cannot silently PASS on missing log)

Log fixtures replicate the patterns used in tests/test_task_runner.py
(`_write_solver_log` — `log.simpleFoam` inside tmp_path/solver_output/).
The attestor itself is exercised in its own (upstream) tests; here we
verify the ResidualMetric wrapper correctly dispatches + aggregates.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.metrics import MetricClass, MetricStatus, ResidualMetric
from src.models import ExecutionResult


def _write_solver_log(tmp_path: Path, content: str, solver: str = "simpleFoam") -> Path:
    d = tmp_path / "solver_output"
    d.mkdir(exist_ok=True)
    (d / f"log.{solver}").write_text(content, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# Happy path — ATTEST_PASS
# ---------------------------------------------------------------------------


def test_residual_pass_on_clean_log(tmp_path: Path) -> None:
    case_dir = _write_solver_log(
        tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n"
    )
    m = ResidualMetric(name="convergence_attestation")
    exec_result = ExecutionResult(
        success=True,
        is_mock=False,
        raw_output_path=str(case_dir),
        exit_code=0,
    )
    report = m.evaluate(
        artifacts=exec_result,
        observable_def={"case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.PASS
    assert report.metric_class is MetricClass.RESIDUAL
    assert report.provenance["attest_verdict"] == "ATTEST_PASS"
    assert report.provenance["delegate_module"] == "src.convergence_attestor"
    assert report.reference_value is None
    assert report.deviation is None
    assert report.tolerance_applied is None
    assert report.notes is None


# ---------------------------------------------------------------------------
# FAIL — A1 solver crash
# ---------------------------------------------------------------------------


def test_residual_fail_on_foam_fatal_error(tmp_path: Path) -> None:
    case_dir = _write_solver_log(
        tmp_path,
        "Time = 1\nFOAM FATAL ERROR: missing dict\nExiting\n",
    )
    m = ResidualMetric(name="convergence_attestation")
    exec_result = ExecutionResult(
        success=True,
        is_mock=False,
        raw_output_path=str(case_dir),
        exit_code=0,
    )
    report = m.evaluate(
        artifacts=exec_result,
        observable_def={"case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.FAIL
    assert report.provenance["attest_verdict"] == "ATTEST_FAIL"
    assert report.notes is not None
    assert "A1" in report.notes or "SOLVER_CRASH" in report.notes


# ---------------------------------------------------------------------------
# WARN — A2 continuity hazard
# ---------------------------------------------------------------------------


def test_residual_warn_on_continuity_hazard(tmp_path: Path) -> None:
    # sum_local above A2 floor (1e-4) → HAZARD
    case_dir = _write_solver_log(
        tmp_path,
        (
            "Time = 1\n"
            "time step continuity errors : "
            "sum local = 5e-04, global = 1e-06, cumulative = 1e-06\n"
            "ExecutionTime = 1 s\n"
            "End\n"
        ),
    )
    m = ResidualMetric(name="convergence_attestation")
    exec_result = ExecutionResult(
        success=True,
        is_mock=False,
        raw_output_path=str(case_dir),
        exit_code=0,
    )
    report = m.evaluate(
        artifacts=exec_result,
        observable_def={"case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.WARN
    assert report.provenance["attest_verdict"] == "ATTEST_HAZARD"
    assert report.notes is not None
    assert "A2" in report.notes or "CONTINUITY" in report.notes


# ---------------------------------------------------------------------------
# WARN — ATTEST_NOT_APPLICABLE (no log)
# ---------------------------------------------------------------------------


def test_residual_warn_on_missing_log() -> None:
    m = ResidualMetric(name="convergence_attestation")
    exec_result = ExecutionResult(
        success=True, is_mock=False, raw_output_path=None
    )
    report = m.evaluate(
        artifacts=exec_result,
        observable_def={"case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.WARN
    assert report.provenance["attest_verdict"] == "ATTEST_NOT_APPLICABLE"
    assert report.notes is not None
    assert "not applicable" in report.notes.lower()


def test_residual_warn_on_dict_artifacts_without_log() -> None:
    m = ResidualMetric(name="convergence_attestation")
    report = m.evaluate(
        artifacts={"some_other_key": "value"},
        observable_def={},
    )
    assert report.status is MetricStatus.WARN
    assert report.provenance["attest_verdict"] == "ATTEST_NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# Artifact-shape coercion
# ---------------------------------------------------------------------------


def test_residual_resolves_log_via_observable_def_override(tmp_path: Path) -> None:
    log_path = tmp_path / "custom.log"
    log_path.write_text("Time = 1\nExecutionTime = 1 s\nEnd\n", encoding="utf-8")
    m = ResidualMetric(name="convergence_attestation")
    report = m.evaluate(
        artifacts={},  # empty artifacts
        observable_def={"log_path": str(log_path), "case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.PASS
    assert report.provenance["log_path"] == str(log_path)


def test_residual_resolves_log_via_dict_case_dir(tmp_path: Path) -> None:
    case_dir = _write_solver_log(
        tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n"
    )
    m = ResidualMetric(name="convergence_attestation")
    report = m.evaluate(
        artifacts={"case_dir": str(case_dir)},
        observable_def={"case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.PASS


def test_residual_resolves_log_via_direct_file_path(tmp_path: Path) -> None:
    case_dir = _write_solver_log(
        tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n"
    )
    log_file = case_dir / "log.simpleFoam"
    m = ResidualMetric(name="convergence_attestation")
    report = m.evaluate(
        artifacts=log_file,
        observable_def={"case_id": "lid_driven_cavity"},
    )
    assert report.status is MetricStatus.PASS


# ---------------------------------------------------------------------------
# Provenance structure — per-check breakdown for UI consumption
# ---------------------------------------------------------------------------


def test_residual_provenance_includes_all_six_checks_on_pass(tmp_path: Path) -> None:
    case_dir = _write_solver_log(
        tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n"
    )
    m = ResidualMetric(name="convergence_attestation")
    exec_result = ExecutionResult(
        success=True, is_mock=False, raw_output_path=str(case_dir), exit_code=0
    )
    report = m.evaluate(
        artifacts=exec_result,
        observable_def={"case_id": "lid_driven_cavity"},
    )
    check_ids = {c["check_id"] for c in report.provenance["checks"]}
    assert check_ids == {"A1", "A2", "A3", "A4", "A5", "A6"}


def test_residual_case_id_surfaced_in_provenance(tmp_path: Path) -> None:
    case_dir = _write_solver_log(
        tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n"
    )
    m = ResidualMetric(name="x")
    report = m.evaluate(
        artifacts=ExecutionResult(
            success=True, is_mock=False, raw_output_path=str(case_dir)
        ),
        observable_def={"case_id": "circular_cylinder_wake"},
    )
    assert report.provenance["case_id"] == "circular_cylinder_wake"
