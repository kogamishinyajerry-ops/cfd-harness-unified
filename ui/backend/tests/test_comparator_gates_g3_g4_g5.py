"""DEC-V61-036b tests: hard comparator gates G3 (velocity overflow),
G4 (turbulence negativity), G5 (continuity divergence).

Evidence sources:
  * BFS audit log shows catastrophic blowup (sum_local=5.24e+18,
    cumulative=-1434.64, k min=-6.41e+30). Synthetic logs in this file
    reproduce those markers for deterministic unit testing.
  * LDC audit log shows clean convergence (sum_local ≈ 1e-6, k laminar
    skipped). Synthetic clean logs assert G3/G4/G5 all pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import comparator_gates as cg
from ui.backend.main import app


# ---------------------------------------------------------------------------
# Shared synthetic log fixtures
# ---------------------------------------------------------------------------

_CLEAN_LDC_LOG = """\
Time = 500

DICPCG:  Solving for p, Initial residual = 1e-08, Final residual = 1e-09, No Iterations 2
time step continuity errors : sum local = 4.5e-08, global = -1.2e-09, cumulative = 3.1e-08
ExecutionTime = 12.3 s  ClockTime = 14 s

End
"""

_BFS_BLOWUP_TAIL = """\
Time = 50

smoothSolver:  Solving for Ux, Initial residual = 0.9, Final residual = 0.6, No Iterations 12
smoothSolver:  Solving for Uy, Initial residual = 0.8, Final residual = 0.5, No Iterations 12
GAMG:  Solving for p, Initial residual = 0.99, Final residual = 0.9, No Iterations 25
time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
smoothSolver:  Solving for epsilon, Initial residual = 0.8, Final residual = 0.4, No Iterations 3
bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
smoothSolver:  Solving for k, Initial residual = 0.7, Final residual = 0.4, No Iterations 4
bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
ExecutionTime = 0.6 s  ClockTime = 0 s
"""


def _write_log(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "log.simpleFoam"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

def test_parse_solver_log_extracts_continuity_and_bounding(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    stats = cg.parse_solver_log(log)
    assert stats.final_continuity_sum_local == pytest.approx(5.24523e18)
    assert stats.final_continuity_cumulative == pytest.approx(-1434.64)
    assert "k" in stats.bounding_last
    assert stats.bounding_last["k"]["min"] == pytest.approx(-6.41351e30)
    assert stats.bounding_last["epsilon"]["max"] == pytest.approx(1.03929e30)
    assert stats.fatal_detected is False


def test_parse_solver_log_detects_foam_fatal(tmp_path: Path) -> None:
    content = _CLEAN_LDC_LOG + "\nFOAM FATAL IO ERROR: missing dictionary key\n"
    log = _write_log(tmp_path, content)
    stats = cg.parse_solver_log(log)
    assert stats.fatal_detected is True


# ---------------------------------------------------------------------------
# G5 — continuity divergence
# ---------------------------------------------------------------------------

def test_g5_fails_on_sum_local_overflow(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert len(g5) == 1
    assert g5[0].concern_type == "CONTINUITY_DIVERGED"
    assert g5[0].evidence["sum_local"] == pytest.approx(5.24523e18)


def test_g5_fails_on_cumulative_only(tmp_path: Path) -> None:
    # sum_local within threshold, cumulative huge — second branch.
    content = (
        "time step continuity errors : "
        "sum local = 1e-04, global = 0.001, cumulative = 2.5\n"
    )
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert len(g5) == 1
    assert g5[0].evidence["cumulative"] == pytest.approx(2.5)


def test_g5_passes_on_clean_ldc_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert g5 == []


# ---------------------------------------------------------------------------
# G4 — turbulence negativity
# ---------------------------------------------------------------------------

def test_g4_fails_on_negative_k_at_last_iter(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    # BFS log shows k min=-6.4e30 AND epsilon max=1.03e30 — both fire G4
    # (negative branch for k, overflow branch for epsilon).
    concern_fields = {v.evidence["field"] for v in g4}
    assert "k" in concern_fields
    assert any(v.evidence.get("min", 1.0) < 0 for v in g4)


def test_g4_fails_on_epsilon_overflow_without_negative(tmp_path: Path) -> None:
    content = (
        "bounding epsilon, min: 1e-5 max: 1e+30 average: 1e+26\n"
        "bounding k, min: 1e-6 max: 0.5 average: 0.01\n"
    )
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    assert len(g4) == 1
    assert g4[0].evidence["field"] == "epsilon"
    assert g4[0].evidence["max"] == pytest.approx(1e30)


def test_g4_passes_on_clean_ldc_log(tmp_path: Path) -> None:
    # LDC is laminar — no bounding lines emitted. G4 should return no violations.
    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    assert g4 == []


# ---------------------------------------------------------------------------
# G3 — velocity overflow (log-proxy branch; VTK branch gated by pyvista)
# ---------------------------------------------------------------------------

def test_g3_proxy_fails_on_epsilon_overflow(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g3 = [v for v in violations if v.gate_id == "G3"]
    assert len(g3) == 1
    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
    # BFS epsilon max=1.03e30 → inferred u ~ (1e30)^(1/3) = 1e10
    assert g3[0].evidence["epsilon_max"] == pytest.approx(1.03929e30)


def test_g3_passes_on_clean_ldc_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g3 = [v for v in violations if v.gate_id == "G3"]
    assert g3 == []


# ---------------------------------------------------------------------------
# NaN/Inf safety (Codex DEC-036b round-1 nit)
# ---------------------------------------------------------------------------

def test_g5_fires_on_nan_sum_local(tmp_path: Path) -> None:
    """OpenFOAM overflowed → prints `nan` for continuity; gate must fire."""
    content = (
        "time step continuity errors : "
        "sum local = nan, global = 0.01, cumulative = -0.5\n"
    )
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert len(g5) == 1, f"expected G5 on nan sum_local, got {violations}"


def test_g4_fires_on_inf_k_max(tmp_path: Path) -> None:
    """+inf in bounding line must fire G4 (not silently skip)."""
    content = "bounding k, min: 1e-5 max: inf average: 1e+20\n"
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    assert len(g4) == 1
    assert g4[0].evidence["field"] == "k"


# ---------------------------------------------------------------------------
# BFS integration — all three gates fire on the real BFS audit log
# ---------------------------------------------------------------------------

_REAL_BFS_LOG = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/"
    "backward_facing_step/20260421T125637Z/log.simpleFoam"
)


@pytest.mark.skipif(not _REAL_BFS_LOG.is_file(), reason="BFS phase7a log absent")
def test_gates_fire_on_real_bfs_audit_log() -> None:
    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
    gate_ids = {v.gate_id for v in violations}
    # BFS must trigger G5 (continuity) + G4 (turbulence) + G3 (velocity proxy).
    assert {"G3", "G4", "G5"}.issubset(gate_ids)


# ---------------------------------------------------------------------------
# Integration with validation_report verdict engine
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_validation_report_hard_fails_on_velocity_overflow_concern() -> None:
    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
    from ui.backend.schemas.validation import (
        AuditConcern,
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="friction_factor",
        ref_value=0.0185,
        unit="dimensionless",
        tolerance_pct=0.10,
        citation="Colebrook 1939",
    )
    # Value IS inside the tolerance band — would normally PASS.
    m = MeasuredValue(
        value=0.0185,
        source="fixture",
        quantity="friction_factor",
        extraction_source="comparator_deviation",
    )
    concerns = [
        AuditConcern(
            concern_type="VELOCITY_OVERFLOW",
            summary="|U|_max=1e10",
        )
    ]
    status, deviation, within, _, _ = _derive_contract_status(
        gs, m, preconditions=[], audit_concerns=concerns
    )
    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
    # Codex round-1 nit applied: within_tolerance is nulled when hard-fail
    # concern fires, so the UI doesn't render "Within band: yes" under FAIL.
    assert status == "FAIL"
    assert deviation == pytest.approx(0.0, abs=1e-9)
    assert within is None  # nulled per Codex nit (value IS inside band, but trust is null)


def test_validation_report_hard_fails_on_continuity_diverged() -> None:
    from ui.backend.schemas.validation import (
        AuditConcern,
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="reattachment_length",
        ref_value=6.26,
        unit="Xr/H",
        tolerance_pct=0.10,
        citation="Driver 1985",
    )
    m = MeasuredValue(value=6.28, source="fixture", quantity="reattachment_length")
    concerns = [AuditConcern(concern_type="CONTINUITY_DIVERGED", summary="cum=-1434")]
    status, _, _, _, _ = _derive_contract_status(gs, m, [], concerns)
    assert status == "FAIL"


def test_validation_report_preserves_pass_without_gate_concerns() -> None:
    """No gate concerns + value within band → PASS still works."""
    from ui.backend.schemas.validation import (
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="u_centerline",
        ref_value=-0.2058,
        unit="dimensionless",
        tolerance_pct=0.05,
        citation="Ghia 1982",
    )
    m = MeasuredValue(value=-0.2050, source="fixture", quantity="u_centerline")
    status, _, within, _, _ = _derive_contract_status(gs, m, [], [])
    assert status == "PASS"
    assert within is True
