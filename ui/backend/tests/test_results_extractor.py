"""Unit tests for ``ui.backend.services.case_solve.results_extractor``.

Focuses on the NaN/Inf detection branch added under DEC-V61-106 — the
DEC's analytical comparator suite raised the bar on what "the solver
ran" means. Previously the extractor silently parsed an all-NaN U
field as 0 entries and surfaced the confusing "0 entries but declared
N" error. Now it short-circuits with a clear "solver diverged"
message that flows through to the smoke verdict.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.case_solve.results_extractor import (
    ResultsExtractError,
    _parse_internal_field,
    extract_results_summary,
)


_HEADER = """\
FoamFile
{
    format      ascii;
    class       volVectorField;
    location    "1";
    object      U;
}

dimensions      [0 1 -1 0 0 0 0];

"""


def _write_u(tmp_path: Path, body: str, name: str = "U") -> Path:
    p = tmp_path / name
    p.write_text(_HEADER + body)
    return p


def test_finite_nonuniform_field_parses(tmp_path: Path):
    body = (
        "internalField   nonuniform List<vector> \n"
        "3\n(\n(1.0 0.0 0.0)\n(2.0 0.5 0.0)\n(0.5 -0.1 0.0)\n)\n;\n"
    )
    p = _write_u(tmp_path, body)
    vels = _parse_internal_field(p)
    assert len(vels) == 3
    assert vels[0] == (1.0, 0.0, 0.0)


def test_uniform_field_parses(tmp_path: Path):
    body = "internalField   uniform (0.8 0.0 0.0);\n"
    p = _write_u(tmp_path, body)
    vels = _parse_internal_field(p)
    assert vels == [(0.8, 0.0, 0.0)]


def test_nan_filled_field_raises_with_divergence_message(tmp_path: Path):
    body = (
        "internalField   nonuniform List<vector> \n"
        "5\n(\n(nan nan -nan)\n(nan nan -nan)\n(nan nan -nan)\n"
        "(nan nan -nan)\n(nan nan -nan)\n)\n;\n"
    )
    p = _write_u(tmp_path, body)
    with pytest.raises(ResultsExtractError) as exc:
        _parse_internal_field(p)
    msg = str(exc.value)
    assert "diverged" in msg.lower()
    assert "5 NaN/Inf" in msg or "NaN" in msg


def test_inf_filled_field_raises_with_divergence_message(tmp_path: Path):
    body = (
        "internalField   nonuniform List<vector> \n"
        "2\n(\n(inf inf -inf)\n(inf inf -inf)\n)\n;\n"
    )
    p = _write_u(tmp_path, body)
    with pytest.raises(ResultsExtractError) as exc:
        _parse_internal_field(p)
    assert "diverged" in str(exc.value).lower()


def test_partially_nan_field_still_raises(tmp_path: Path):
    """Even one NaN in the body should trigger the divergence guard
    rather than silently dropping the bad entry."""
    body = (
        "internalField   nonuniform List<vector> \n"
        "3\n(\n(1.0 0.0 0.0)\n(nan nan -nan)\n(0.5 0.1 0.0)\n)\n;\n"
    )
    p = _write_u(tmp_path, body)
    with pytest.raises(ResultsExtractError) as exc:
        _parse_internal_field(p)
    assert "diverged" in str(exc.value).lower()


def test_extract_results_summary_propagates_nan_diagnosis(tmp_path: Path):
    """End-to-end: the divergence guard surfaces through the public
    ``extract_results_summary`` API so smoke runners and other
    consumers get the actionable message rather than a generic parse
    failure."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "0").mkdir()
    final = case_dir / "100"
    final.mkdir()
    (final / "U").write_text(
        _HEADER
        + "internalField   nonuniform List<vector> \n"
        "1\n(\n(nan nan -nan)\n)\n;\n"
    )
    with pytest.raises(ResultsExtractError) as exc:
        extract_results_summary(case_dir, case_id="test")
    assert "diverged" in str(exc.value).lower()


def test_finite_field_summary_round_trips(tmp_path: Path):
    """Sanity check that the divergence guard does NOT regress the
    happy path — finite fields still produce a valid ResultsSummary."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "0").mkdir()
    final = case_dir / "10"
    final.mkdir()
    (final / "U").write_text(
        _HEADER
        + "internalField   nonuniform List<vector> \n"
        "3\n(\n(1.0 0.0 0.0)\n(2.0 0.0 0.0)\n(-0.5 0.1 0.0)\n)\n;\n"
    )
    summary = extract_results_summary(case_dir, case_id="test")
    assert summary.cell_count == 3
    assert summary.u_magnitude_max == pytest.approx(2.0)
    assert summary.u_x_min == pytest.approx(-0.5)
    assert summary.u_x_max == pytest.approx(2.0)
