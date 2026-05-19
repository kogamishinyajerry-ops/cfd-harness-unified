"""Backend tests for case_visualize.residual_series + parser.

Covers Codex R6 M-3 finding: the parser path and source-priority
resolution must be pinned with real tests, not left to source-regex
contract tests only.

R7 (Codex R6.1 M-3 closure): adds the two positive end-to-end pins
the prior coverage missed —
  * ``source='runs'`` with real ``write_run_artifacts`` fixtures
  * full-chain ``source='log'`` *beats* a valid runs history

Test surfaces:
    _parse_log               — OpenFOAM-style log → series dict
    _try_log                 — disk-walk path discovery
    build_residual_series    — full priority chain (log → runs → empty)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ui.backend.services.case_visualize.residual_chart import _parse_log
from ui.backend.services.case_visualize.residual_series import (
    _parse_log_file,
    _try_log,
    build_residual_series,
)
from ui.backend.services.run_history import write_run_artifacts


class _FakeEnum:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeTaskSpec:
    """Minimal stand-in matching run_history._task_spec_to_excerpt expectations."""

    def __init__(self, *, name: str = "LDC", Re: float = 100.0) -> None:
        self.name = name
        self.Re = Re
        self.Ra = None
        self.Re_tau = None
        self.Ma = None
        self.geometry_type = _FakeEnum("SIMPLE_GRID")
        self.flow_type = _FakeEnum("INTERNAL")
        self.steady_state = _FakeEnum("STEADY")
        self.compressibility = _FakeEnum("INCOMPRESSIBLE")


# ──────────────────────── _parse_log ────────────────────────


def test_parse_log_empty_text():
    """No Time markers → empty series."""
    parsed = _parse_log("")
    for name in ("Ux", "Uy", "Uz", "p"):
        assert parsed[name] == []


def test_parse_log_picks_first_U_and_first_p_per_step():
    """One timestep with all 3 U components + p → one point per series."""
    log = """\
Time = 1
smoothSolver:  Solving for Ux, Initial residual = 1.0e-2, Final residual = 5e-3,
smoothSolver:  Solving for Uy, Initial residual = 1.1e-2, Final residual = 5.5e-3,
smoothSolver:  Solving for Uz, Initial residual = 1.2e-2, Final residual = 6e-3,
DICPCG:  Solving for p, Initial residual = 5.0e-2, Final residual = 1e-5,
Time = 2
smoothSolver:  Solving for Ux, Initial residual = 8.0e-3, Final residual = 4e-3,
DICPCG:  Solving for p, Initial residual = 4.0e-2, Final residual = 8e-6,
"""
    parsed = _parse_log(log)
    # Step 1: all four series
    assert parsed["Ux"] == [(1, 1.0e-2), (2, 8.0e-3)]
    assert parsed["Uy"] == [(1, 1.1e-2)]
    assert parsed["Uz"] == [(1, 1.2e-2)]
    assert parsed["p"] == [(1, 5.0e-2), (2, 4.0e-2)]


def test_parse_log_picks_LAST_p_per_step():
    """PISO solves p multiple times per step; we want the converged
    value (last), not the gradient-initial (first)."""
    log = """\
Time = 1
DICPCG:  Solving for p, Initial residual = 5.0e-2, Final residual = 1e-3,
DICPCG:  Solving for p, Initial residual = 1.0e-3, Final residual = 1e-5,
DICPCG:  Solving for p, Initial residual = 1.0e-5, Final residual = 1e-7,
"""
    parsed = _parse_log(log)
    # _parse_log keeps the FIRST initial residual per step... let me re-read.
    # Actually per the docstring: "captures the FIRST initial-residual per
    # quantity within that block." So the FIRST is 5.0e-2.
    # But the comment at line 96-104 says: "FIRST has the highest initial
    # residual; the LAST has the lowest; ... The convergence-tracking value
    # is the LAST one — that's what the user sees as 'p has settled'".
    # And the code (line 102-104) uses p_matches[-1] = last. So the LAST.
    assert parsed["p"] == [(1, 1.0e-5)]


def test_parse_log_skips_non_residual_lines():
    """Noise lines between Time markers don't crash the parser."""
    log = """\
Create mesh for time = 0
Time = 1
   nProcs : 1
smoothSolver:  Solving for Ux, Initial residual = 1.0e-2, Final residual = 5e-3,
Some unrelated diagnostic line
DICPCG:  Solving for p, Initial residual = 5.0e-2, Final residual = 1e-5,
ExecutionTime = 0.5 s
"""
    parsed = _parse_log(log)
    assert parsed["Ux"] == [(1, 1.0e-2)]
    assert parsed["p"] == [(1, 5.0e-2)]


# ──────────────────────── _parse_log_file ────────────────────────


def test_parse_log_file_returns_none_for_missing(tmp_path: Path):
    """Path that doesn't exist → None (not an exception)."""
    assert _parse_log_file(tmp_path / "log.icoFoam") is None


def test_parse_log_file_returns_none_for_unparseable(tmp_path: Path):
    """File exists but no recognisable residual lines → None."""
    log = tmp_path / "log.simpleFoam"
    log.write_text("garbage\nno residuals here\n")
    assert _parse_log_file(log) is None


def test_parse_log_file_converts_points(tmp_path: Path):
    log = tmp_path / "log.simpleFoam"
    log.write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1.0e-2, Final residual = 5e-3,\n"
        "DICPCG:  Solving for p, Initial residual = 5.0e-2, Final residual = 1e-5,\n"
    )
    out = _parse_log_file(log)
    assert out is not None
    assert "Ux" in out
    assert "p" in out
    assert out["Ux"][0].x == 1.0
    assert out["Ux"][0].y == 1.0e-2


# ──────────────────────── _try_log ────────────────────────


def test_try_log_finds_log_in_imported_root(tmp_path: Path):
    """Codex R6 M-2 closure: real solver runs put the log in
    ``imported/{case_id}/log.{solver}``, NOT in the runs report dir.
    The discovery walk must inspect imported_root first."""
    case_id = "test_case"
    case_dir = tmp_path / "imported" / case_id
    case_dir.mkdir(parents=True)
    log = case_dir / "log.simpleFoam"
    log.write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 9.0e-6, Final residual = 1e-7,\n"
    )

    out = _try_log(
        case_id,
        runs_root=tmp_path / "reports",  # missing
        imported_root=tmp_path / "imported",
    )
    assert out is not None
    assert "Ux" in out
    assert out["Ux"][0].y == 9.0e-6


def test_try_log_fallback_to_run_dir(tmp_path: Path):
    """When the imported root has no log, walk reports/<case>/runs."""
    case_id = "test_case"
    runs_dir = tmp_path / "reports" / case_id / "runs" / "2026-01-01T00-00-00Z"
    runs_dir.mkdir(parents=True)
    (runs_dir / "log.icoFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 5.0e-5, Final residual = 1e-7,\n"
    )

    out = _try_log(
        case_id,
        runs_root=tmp_path / "reports",
        imported_root=tmp_path / "no_such_imported",
    )
    assert out is not None
    assert out["Ux"][0].y == 5.0e-5


def test_try_log_returns_none_when_no_logs(tmp_path: Path):
    out = _try_log(
        case_id="any",
        runs_root=tmp_path / "reports",
        imported_root=tmp_path / "imported",
    )
    assert out is None


def test_try_log_prefers_imported_over_runs(tmp_path: Path):
    """When both locations have logs, imported wins (newer / canonical)."""
    case_id = "test_case"
    imported = tmp_path / "imported" / case_id
    imported.mkdir(parents=True)
    (imported / "log.simpleFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1.0e-9, Final residual = 1e-10,\n"
    )
    runs = tmp_path / "reports" / case_id / "runs" / "2026-01-01T00-00-00Z"
    runs.mkdir(parents=True)
    (runs / "log.simpleFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 9.9e-3, Final residual = 1e-4,\n"
    )

    out = _try_log(
        case_id,
        runs_root=tmp_path / "reports",
        imported_root=tmp_path / "imported",
    )
    assert out is not None
    # Imported version (1e-9) should win, not runs (9.9e-3).
    assert out["Ux"][0].y == pytest.approx(1.0e-9)


# ──────────────────────── build_residual_series ────────────────────────


def test_build_residual_series_source_log(tmp_path: Path):
    """Log present → source="log", achieved tied to target_floor."""
    case_id = "test_case"
    case_dir = tmp_path / "imported" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "log.simpleFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 9.0e-6, Final residual = 1e-7,\n"
        "smoothSolver:  Solving for Uy, Initial residual = 9.0e-6, Final residual = 1e-7,\n"
        "DICPCG:  Solving for p, Initial residual = 9.0e-6, Final residual = 1e-7,\n"
    )

    payload = build_residual_series(
        case_id,
        runs_root=tmp_path / "reports",  # missing
        imported_root=tmp_path / "imported",
    )
    assert payload.source == "log"
    assert payload.sample_count == 1
    assert set(payload.series.keys()) == {"Ux", "Uy", "p"}
    # All below 1e-5 but above 1e-6 → achieved should be False since
    # target_floor defaults to 1e-6. Last sample of each is 9.0e-6 > 1e-6.
    assert payload.achieved is False


def test_build_residual_series_source_runs_fallback(tmp_path: Path):
    """No log, no runs → source="empty" (the trivial fallback).

    The positive runs-fallback path (no log + valid runs → source="runs"
    with real residual values) is pinned by
    ``test_build_residual_series_source_runs_with_real_artifacts`` below.
    """
    payload = build_residual_series(
        "test_case",
        runs_root=tmp_path / "no_runs",
        imported_root=tmp_path / "no_imported",
    )
    assert payload.source == "empty"


def test_build_residual_series_source_runs_with_real_artifacts(tmp_path: Path):
    """R7 Codex R6.1 M-3 closure: no log on disk + valid run-history
    artifacts → source="runs" with real residual values."""
    case_id = "lid_driven_cavity"
    reports_root = tmp_path / "reports"

    # Two consecutive runs · oldest → newest (build_residual_series sorts
    # by started_at ascending, so run_a becomes x=1, run_b becomes x=2).
    write_run_artifacts(
        case_id=case_id,
        run_id="run_a",
        started_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=100.0),
        source_origin="whitelist",
        success=True,
        exit_code=0,
        verdict_summary="converged",
        duration_s=20.0,
        key_quantities={"u_max": 0.61},
        residuals={"Ux": 1.4e-5, "Uy": 3.5e-5, "p": 1.0e-5},
        root=reports_root,
    )
    write_run_artifacts(
        case_id=case_id,
        run_id="run_b",
        started_at=datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=400.0),
        source_origin="draft",
        success=True,
        exit_code=0,
        verdict_summary="converged",
        duration_s=22.0,
        key_quantities={"u_max": 0.74},
        residuals={"Ux": 9.0e-6, "Uy": 1.5e-5, "p": 8.0e-6},
        root=reports_root,
    )

    payload = build_residual_series(
        case_id,
        runs_root=reports_root,
        imported_root=tmp_path / "no_imported",
    )

    assert payload.source == "runs"
    assert payload.latest_run_id == "run_b"
    assert payload.sample_count == 2
    # Newest run = last sample of each series.
    assert payload.series["Ux"][-1].y == pytest.approx(9.0e-6)
    assert payload.series["Uy"][-1].y == pytest.approx(1.5e-5)
    assert payload.series["p"][-1].y == pytest.approx(8.0e-6)
    # Newest is below 1e-5 but not below 1e-6 target_floor → not achieved.
    assert payload.achieved is False


def test_build_residual_series_log_beats_runs(tmp_path: Path):
    """R7 Codex R6.1 M-3 closure: when BOTH a log and a valid runs
    history exist, the log wins (priority chain log → runs → empty).
    The asserted series values must come from the log (1e-9 Ux), not
    the runs (9.9e-3 Ux), to prove no silent fallthrough."""
    case_id = "test_case"
    reports_root = tmp_path / "reports"
    imported = tmp_path / "imported" / case_id
    imported.mkdir(parents=True)

    # Log on disk · Ux residual = 1.0e-9 (the truth signal).
    (imported / "log.icoFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1.0e-9, Final residual = 1e-10,\n"
        "DICPCG:  Solving for p, Initial residual = 1.0e-9, Final residual = 1e-10,\n"
    )

    # ALSO a valid run-history artifact · Ux = 9.9e-3 (the trap signal —
    # must NOT show up if priority chain is correct).
    write_run_artifacts(
        case_id=case_id,
        run_id="run_a",
        started_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=100.0),
        source_origin="whitelist",
        success=True,
        exit_code=0,
        verdict_summary="converged",
        duration_s=20.0,
        key_quantities=None,
        residuals={"Ux": 9.9e-3, "p": 5.0e-3},
        root=reports_root,
    )

    payload = build_residual_series(
        case_id,
        runs_root=reports_root,
        imported_root=tmp_path / "imported",
    )

    # Source must be log, not runs.
    assert payload.source == "log"
    assert payload.latest_run_id is None  # log path is run-agnostic.
    # Values must come from log (1e-9), not from runs (9.9e-3).
    assert payload.series["Ux"][-1].y == pytest.approx(1.0e-9)
    assert payload.series["p"][-1].y == pytest.approx(1.0e-9)
    # Log Ux = 1e-9 < target_floor 1e-6 → achieved.
    assert payload.achieved is True


def test_build_residual_series_empty_path(tmp_path: Path):
    payload = build_residual_series(
        case_id="nonexistent",
        runs_root=tmp_path / "reports",
        imported_root=tmp_path / "imported",
    )
    assert payload.source == "empty"
    assert payload.series == {}
    assert payload.sample_count == 0
    assert payload.achieved is False
    assert "No runs" in payload.note


def test_build_residual_series_achieved_when_all_below_floor(tmp_path: Path):
    case_id = "test_case"
    case_dir = tmp_path / "imported" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "log.simpleFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1.0e-7, Final residual = 1e-8,\n"
        "smoothSolver:  Solving for Uy, Initial residual = 1.0e-7, Final residual = 1e-8,\n"
        "DICPCG:  Solving for p, Initial residual = 1.0e-7, Final residual = 1e-8,\n"
    )
    payload = build_residual_series(
        case_id,
        runs_root=tmp_path / "reports",
        imported_root=tmp_path / "imported",
    )
    assert payload.source == "log"
    assert payload.achieved is True  # all 1e-7 < target_floor 1e-6
