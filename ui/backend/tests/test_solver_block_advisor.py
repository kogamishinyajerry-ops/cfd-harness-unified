"""Unit tests for ``geometry_ingest.solver_block_advisor``.

DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2 · V27 + V28 evidence rows.
Mirrors the test pattern used for D10 ``test_bc_type_name_validity_advisor``
+ thin-wall advisor: small focused cases per rule branch + a "clean
config emits nothing" baseline + a "non-target solver class emits
nothing" baseline.
"""
from __future__ import annotations

import pytest

from ui.backend.services.geometry_ingest.solver_block_advisor import (
    SolverBlockFinding,
    SolverBlockReport,
    SolverBlockSnapshot,
    check_solver_block,
)


def test_case_006_v1_pre_fix_emits_v27_and_v28():
    """case_006 v1 (2026-05-08 pre-fix) emits V27 + V28 criticals."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=False,
        delta_t=1.0,
        preconditioners={"U": "DILU", "e": "DILU", "k": "DILU", "omega": "DILU"},
    )
    report = check_solver_block(snap)

    # V27 + 4 × V28 = 5 findings; V27 first by emission order
    assert len(report.findings) == 5
    codes = [f.code for f in report.findings]
    assert codes[0] == "v27_adjusttimestep_required"
    assert codes[1:] == ["v28_dilu_on_symmetric"] * 4
    assert all(f.severity == "critical" for f in report.findings)

    # V27 location + message detail
    v27 = report.findings[0]
    assert v27.location == "controlDict.adjustTimeStep"
    assert "rhoCentralFoam" in v27.detail
    assert "deltaT=1.0" in v27.detail

    # V28 locations follow sorted field name order
    v28_locations = [f.location for f in report.findings[1:]]
    assert v28_locations == [
        "fvSolution.solvers.U.preconditioner",
        "fvSolution.solvers.e.preconditioner",
        "fvSolution.solvers.k.preconditioner",
        "fvSolution.solvers.omega.preconditioner",
    ]
    for v28 in report.findings[1:]:
        assert "symmetric matrix path" in v28.detail
        assert "DILU" in v28.detail


def test_adjusttimestep_yes_skips_v27():
    """``adjustTimeStep yes`` suppresses V27 but V28 still fires."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1e-6,
        preconditioners={"U": "DILU"},
    )
    report = check_solver_block(snap)
    assert len(report.findings) == 1
    assert report.findings[0].code == "v28_dilu_on_symmetric"


def test_adjusttimestep_none_treated_as_no():
    """Absent ``adjustTimeStep`` key → V27 fires (OpenFOAM default is no)."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=None,
        delta_t=None,
        preconditioners={},
    )
    report = check_solver_block(snap)
    assert len(report.findings) == 1
    assert report.findings[0].code == "v27_adjusttimestep_required"
    # deltaT absent → no deltaT detail snippet
    assert "deltaT=" not in report.findings[0].detail


def test_valid_symmetric_preconditioners_emit_nothing():
    """DIC / FDIC / GAMG / diagonal / smoothSolver → no V28 finding."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1e-6,
        preconditioners={
            "U": "symGaussSeidel",  # canonical rhoCentralFoam tutorial
            "e": "DIC",
            "p": "GAMG",
        },
    )
    report = check_solver_block(snap)
    assert report.findings == ()


def test_fdilu_also_flagged_as_asymmetric():
    """FDILU is asymmetric-only too; same V28 flag."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        preconditioners={"U": "FDILU"},
    )
    report = check_solver_block(snap)
    assert len(report.findings) == 1
    assert report.findings[0].code == "v28_dilu_on_symmetric"
    assert "FDILU" in report.findings[0].detail


def test_non_density_based_solver_emits_nothing():
    """Solver class outside the density-based-symmetric set → silent."""
    snap = SolverBlockSnapshot(
        solver="rhoSimpleFoam",  # pressure-based; asymmetric U matrix → DILU OK
        adjust_time_step=False,
        delta_t=1.0,
        preconditioners={"U": "DILU"},
    )
    report = check_solver_block(snap)
    assert report.findings == ()


def test_rho_central_dym_foam_also_dispatched():
    """rhoCentralDyMFoam is the dynamic-mesh variant; same matrix class."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralDyMFoam",
        adjust_time_step=False,
        preconditioners={"U": "DILU"},
    )
    report = check_solver_block(snap)
    codes = [f.code for f in report.findings]
    assert codes == ["v27_adjusttimestep_required", "v28_dilu_on_symmetric"]


def test_clean_rho_central_foam_canonical_emits_nothing():
    """Canonical rhoCentralFoam (S15 playbook compliant) emits nothing."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1e-6,
        preconditioners={
            "U": "symGaussSeidel",
            "e": "symGaussSeidel",
            "k": "symGaussSeidel",
            "omega": "symGaussSeidel",
        },
    )
    report = check_solver_block(snap)
    assert report.findings == ()


def test_finding_dataclass_is_frozen():
    """Findings cannot be mutated (V130 advisory-only contract)."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=False,
        preconditioners={"U": "DILU"},
    )
    report = check_solver_block(snap)
    with pytest.raises((AttributeError, TypeError)):
        report.findings[0].severity = "warning"  # type: ignore[misc]


def test_adjusttimestep_yes_with_oversized_deltat_emits_v27_partial_fix():
    """R1b · adjustTimeStep yes but initial deltaT 1.0 still trips V27."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1.0,
        preconditioners={},
    )
    report = check_solver_block(snap)
    assert len(report.findings) == 1
    assert report.findings[0].code == "v27_initial_deltat_too_large"
    assert report.findings[0].severity == "critical"
    assert "deltaT=1.0" in report.findings[0].detail
    assert "S15 fix #2" in report.findings[0].detail


def test_adjusttimestep_yes_with_small_deltat_clean():
    """R1b · adjustTimeStep yes + small initial deltaT (1e-6) → silent."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1e-6,
        preconditioners={},
    )
    report = check_solver_block(snap)
    assert report.findings == ()


def test_v28_skips_non_symmetric_path_fields():
    """V28 only fires on symmetric-path field set; stray DILU on p/rho/
    rhoU/rhoE is dead config (direct-update path · not a V28 runtime
    failure)."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1e-6,
        preconditioners={
            "U": "DILU",        # symmetric path · V28 critical
            "p": "DILU",        # dead config · skip
            "rho": "DILU",      # dead config · skip
            "rhoU": "DILU",     # dead config · skip
            "rhoE": "DILU",     # dead config · skip
        },
    )
    report = check_solver_block(snap)
    assert len(report.findings) == 1
    assert report.findings[0].code == "v28_dilu_on_symmetric"
    assert report.findings[0].location == "fvSolution.solvers.U.preconditioner"


def test_v28_covers_full_symmetric_path_set():
    """V28 fires on all 7 symmetric-path fields (U/e/k/omega/epsilon/
    nuTilda/T) — RANS / DES forward-coverage."""
    snap = SolverBlockSnapshot(
        solver="rhoCentralFoam",
        adjust_time_step=True,
        delta_t=1e-6,
        preconditioners={
            "U": "DILU", "e": "DILU", "k": "DILU", "omega": "DILU",
            "epsilon": "DILU", "nuTilda": "DILU", "T": "DILU",
        },
    )
    report = check_solver_block(snap)
    codes = [f.code for f in report.findings]
    assert codes == ["v28_dilu_on_symmetric"] * 7
    locations = [f.location for f in report.findings]
    assert locations == sorted(locations)


def test_report_is_frozen():
    """SolverBlockReport itself is frozen."""
    snap = SolverBlockSnapshot(
        solver="rhoSimpleFoam",
        adjust_time_step=True,
        preconditioners={},
    )
    report = check_solver_block(snap)
    with pytest.raises((AttributeError, TypeError)):
        report.findings = (SolverBlockFinding("critical", "x", "y", "z"),)  # type: ignore[misc]
