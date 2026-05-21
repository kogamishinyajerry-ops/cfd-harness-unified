"""Tests for trust_report generation and honesty constraints."""
from __future__ import annotations

import json
from pathlib import Path

from cfdtrust.cli import cmd_report


REQUIRED_GATES = {
    "geometry_contract",
    "mesh_contract",
    "bc_contract",
    "solver_execution",
    "qoi_extraction",
    "reference_comparison",
}


def _generate(sample_case_dir: Path) -> dict:
    rc = cmd_report(str(sample_case_dir))
    assert rc == 0
    report_path = sample_case_dir / "artifacts" / "trust_report.json"
    assert report_path.exists(), "trust_report.json must exist after report command"
    return json.loads(report_path.read_text())


def test_trust_report_has_case_id(sample_case_dir: Path):
    report = _generate(sample_case_dir)
    assert report["case_id"] == "flat_plate_rans_sst"


def test_trust_report_has_overall_status(sample_case_dir: Path):
    report = _generate(sample_case_dir)
    assert report["overall_status"] in {"PASS", "WARN", "FAIL", "BLOCKED", "MOCKED"}


def test_trust_report_has_solver_execution(sample_case_dir: Path):
    report = _generate(sample_case_dir)
    assert report["solver_execution"] in {"real", "mocked", "skipped"}


def test_mocked_solver_does_not_claim_validation(sample_case_dir: Path):
    """If the solver is mocked, validation_status must NOT be 'validated' and overall must NOT be PASS."""
    report = _generate(sample_case_dir)
    if report["solver_execution"] == "mocked":
        assert report["validation_status"] != "validated", (
            "Mocked solver may NEVER carry validation_status: validated"
        )
        assert report["overall_status"] != "PASS", (
            "Mocked solver may NEVER produce overall_status: PASS"
        )


def test_mocked_solver_carries_explicit_limitation(sample_case_dir: Path):
    report = _generate(sample_case_dir)
    if report["solver_execution"] == "mocked":
        joined = " ".join(report.get("limitations", []))
        assert "No real CFD solver" in joined or "did not constitute validation" in joined or "does not constitute validation" in joined


def test_all_required_gates_present(sample_case_dir: Path):
    report = _generate(sample_case_dir)
    assert REQUIRED_GATES.issubset(report["gates"].keys())


def test_each_referenced_artifact_exists(sample_case_dir: Path):
    report = _generate(sample_case_dir)
    for key, rel in report["artifacts"].items():
        p = sample_case_dir / rel
        assert p.exists(), f"trust_report references missing artifact {key}: {rel}"
