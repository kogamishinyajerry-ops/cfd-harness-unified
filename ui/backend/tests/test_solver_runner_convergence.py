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
    the legacy LDC default endTime=2.0 — preserved for backward compat."""
    assert _is_converged(_good_parse(end_time=2.0)) is True
    assert _is_converged(_good_parse(end_time=1.0)) is False  # 1.0 < 0.995 * 2.0


def test_is_converged_honors_configured_end_time():
    """V61-103 introduced per-case endTime. The heuristic now compares
    against the configured value, not the hardcoded 2.0."""
    # Half-second smoke run with all-good residuals: should converge.
    assert _is_converged(_good_parse(end_time=0.5), configured_end_time=0.5) is True
    # Stopped early at 0.4 vs configured 0.5 (just above 0.5%-tolerance window): diverged.
    assert _is_converged(_good_parse(end_time=0.4), configured_end_time=0.5) is False


def test_is_converged_tolerates_writeinterval_rounding():
    """OpenFOAM writeInterval rounding can land at 1.999998 for endTime
    2.0; the 0.5% tolerance prevents a false-FAIL."""
    parsed = _good_parse(end_time=1.99999)
    assert _is_converged(parsed, configured_end_time=2.0) is True


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
    assert _read_configured_end_time(case) == pytest.approx(0.5)


def test_read_configured_end_time_handles_missing_file(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    # No controlDict — falls back to 2.0 (legacy LDC default).
    assert _read_configured_end_time(case) == pytest.approx(2.0)


def test_read_configured_end_time_handles_unparseable_value(tmp_path: Path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(
        "FoamFile { format ascii; }\n"
        "endTime         not_a_number;\n"
    )
    assert _read_configured_end_time(case) == pytest.approx(2.0)
