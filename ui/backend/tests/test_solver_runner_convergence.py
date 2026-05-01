"""Unit tests for the solver_runner convergence heuristic.

Defect 9 (adversarial-loop iter04/05/06 follow-up): the original
``_is_converged`` hardcoded ``end_time_reached >= 1.99`` matching the
LDC demo's endTime=2.0. When DEC-V61-103 made endTime configurable
per case, the smoke runner started passing per-case overrides like
end_time=0.5 — perfectly converged 0.5s runs were then mis-classified
as ``converged=false`` because end_time_reached=0.5 < 1.99. The fix
reads endTime from controlDict and tolerates 0.5% floating-point slop.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.case_solve.solver_runner import (
    _is_converged,
    _read_configured_end_time,
)


def _good_parse(end_time: float = 2.0) -> dict[str, object]:
    return {
        "end_time_reached": end_time,
        "continuity": 1.0e-7,
        "p": 1.0e-6,
        "Ux": 1.0e-7,
        "Uy": 1.0e-7,
        "Uz": 1.0e-7,
    }


def test_is_converged_default_end_time_legacy_ldc_value():
    """Pre-V61-103 callers (and bare _is_converged calls in tests) get
    the legacy LDC defaults endTime=2.0 + deltaT=0.01 — preserved for
    backward compat."""
    assert _is_converged(_good_parse(end_time=2.0)) is True
    # Tolerance window is 0.5 * dt = 0.005; 1.0 is way below.
    assert _is_converged(_good_parse(end_time=1.0)) is False


def test_is_converged_honors_configured_end_time():
    """V61-103 introduced per-case endTime. The heuristic now compares
    against the configured value, not the hardcoded 2.0."""
    assert (
        _is_converged(_good_parse(end_time=0.5), configured_end_time=0.5,
                      configured_delta_t=0.002)
        is True
    )
    # Stopped early at 0.4 vs configured 0.5: way outside half-step window.
    assert (
        _is_converged(_good_parse(end_time=0.4), configured_end_time=0.5,
                      configured_delta_t=0.002)
        is False
    )


def test_is_converged_rejects_one_step_early_stop():
    """Codex post-merge HIGH (this commit's reason): the previous 0.5%
    relative tolerance let endTime=0.5 + dt=0.002 read as converged at
    end_t=0.498 — a genuine 1-step early stop. The new 0.5*dt absolute
    tolerance rejects this case."""
    # 1 timestep short: end_t = 0.498 < 0.5 - 0.5*0.002 = 0.499.
    assert (
        _is_converged(_good_parse(end_time=0.498), configured_end_time=0.5,
                      configured_delta_t=0.002)
        is False
    )
    # Exactly the half-step boundary: 0.499 = 0.5 - 0.5*0.002 → converged.
    assert (
        _is_converged(_good_parse(end_time=0.499), configured_end_time=0.5,
                      configured_delta_t=0.002)
        is True
    )


def test_is_converged_tolerates_writeinterval_rounding():
    """OpenFOAM writeInterval rounding can land at 1.999998 for endTime
    2.0 + dt=0.01; the half-timestep tolerance (0.005) prevents a
    false-FAIL on legitimate end-time-reached values just under target."""
    parsed = _good_parse(end_time=1.99999)
    assert _is_converged(parsed, configured_end_time=2.0,
                         configured_delta_t=0.01) is True


def test_is_converged_rejects_nan_continuity():
    """iter01 (interior obstacle plenum) hits NaN residuals while the
    solver still 'completes' to end_time. The heuristic must reject
    NaN as not-converged."""
    parsed = _good_parse(end_time=2.0)
    parsed["continuity"] = float("nan")
    assert _is_converged(parsed, configured_end_time=2.0) is False


def test_is_converged_rejects_huge_continuity():
    """Smoke iter05 first run had cont_err ~1e+86 before the per-case
    override fix. Continuity error > 1e-3 must read as diverged."""
    parsed = _good_parse(end_time=2.0)
    parsed["continuity"] = 1.5e+10
    assert _is_converged(parsed, configured_end_time=2.0) is False


def test_is_converged_rejects_missing_continuity():
    parsed = _good_parse(end_time=2.0)
    del parsed["continuity"]
    assert _is_converged(parsed, configured_end_time=2.0) is False


def test_is_converged_rejects_non_numeric_end_time():
    parsed = _good_parse(end_time=2.0)
    parsed["end_time_reached"] = "string"
    assert _is_converged(parsed, configured_end_time=2.0) is False


def test_read_configured_end_time_parses_controldict(tmp_path: Path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(
        "FoamFile { format ascii; }\n"
        "application icoFoam;\n"
        "endTime         0.5;\n"
        "deltaT          0.002;\n"
    )
    end_t, dt = _read_configured_end_time(case)
    assert end_t == pytest.approx(0.5)
    assert dt == pytest.approx(0.002)


def test_read_configured_end_time_handles_missing_file(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    # No controlDict — falls back to (2.0, 0.01) legacy LDC defaults.
    assert _read_configured_end_time(case) == (pytest.approx(2.0), pytest.approx(0.01))


def test_read_configured_end_time_handles_unparseable_value(tmp_path: Path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(
        "FoamFile { format ascii; }\n"
        "endTime         not_a_number;\n"
        "deltaT          also_garbage;\n"
    )
    end_t, dt = _read_configured_end_time(case)
    assert end_t == pytest.approx(2.0)
    assert dt == pytest.approx(0.01)


def test_read_configured_end_time_partial_parse(tmp_path: Path):
    """endTime parses, deltaT missing → endTime taken, dt falls back."""
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(
        "FoamFile { format ascii; }\n"
        "endTime         3.7;\n"
    )
    end_t, dt = _read_configured_end_time(case)
    assert end_t == pytest.approx(3.7)
    assert dt == pytest.approx(0.01)
