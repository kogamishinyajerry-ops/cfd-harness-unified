"""DEC-V61-044: tests for src/airfoil_surface_sampler.py.

Coverage:
- Parser: 4-column raw format, comments, blank lines, blank file
  (raises), sparse/malformed rows (raise).
- Dedup: spanwise thin-2D duplicates collapse to one (x, z) pair.
- Cp normalization: exact against hand-computed stagnation Cp=1,
  trailing-edge near-zero, negative Cp on upper surface.
- Side classification: upper (z>0), lower (z<0), trailing_edge
  (x/c > 0.995).
- Integration: emit_cp_profile returns comparator-shaped dict
  with upper-surface-only scalar lists + full profile + source flag.
- Fail-closed: malformed raw input raises; absent returns None.
- Input validation: zero chord / U_inf / negative rho all raise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.airfoil_surface_sampler import (
    AirfoilSurfaceSamplerError,
    CpPoint,
    compute_cp,
    emit_cp_profile,
    read_patch_raw,
)


# --- helpers ---------------------------------------------------------------


def _write_fo_raw(
    case_dir: Path,
    time: str,
    rows: list[tuple[float, float, float, float]],
    *,
    fo_name: str = "airfoilSurface",
    surface_name: str = "aerofoil",
    field: str = "p",
) -> None:
    d = case_dir / "postProcessing" / fo_name / time
    d.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{x} {y} {z} {p}" for x, y, z, p in rows)
    (d / f"{field}_{surface_name}.raw").write_text(
        "# x y z p\n" + body + "\n",
        encoding="utf-8",
    )


# --- parser tests ----------------------------------------------------------


def test_read_patch_raw_parses_4col_format(tmp_path: Path) -> None:
    rows = [
        (0.0, 0.001, 0.0, 0.5),
        (0.0, -0.001, 0.0, 0.5),
        (0.5, 0.001, 0.03, -0.2),
    ]
    _write_fo_raw(tmp_path, "2000", rows)
    loaded = read_patch_raw(tmp_path)
    assert loaded is not None
    assert len(loaded) == 3
    assert loaded[0] == (0.0, 0.001, 0.0, 0.5)


def test_read_patch_raw_returns_none_when_absent(tmp_path: Path) -> None:
    assert read_patch_raw(tmp_path) is None


def test_read_patch_raw_raises_on_sparse_row(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "airfoilSurface" / "2000"
    d.mkdir(parents=True)
    (d / "p_aerofoil.raw").write_text("# hdr\n0.5 0.0 0.03\n")  # 3 cols
    with pytest.raises(
        AirfoilSurfaceSamplerError, match="expected 4 columns"
    ):
        read_patch_raw(tmp_path)


def test_read_patch_raw_raises_on_nonnumeric(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "airfoilSurface" / "2000"
    d.mkdir(parents=True)
    (d / "p_aerofoil.raw").write_text("# hdr\n0.5 BAD 0.03 -0.2\n")
    with pytest.raises(AirfoilSurfaceSamplerError, match="non-numeric"):
        read_patch_raw(tmp_path)


def test_read_patch_raw_raises_on_empty_data(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "airfoilSurface" / "2000"
    d.mkdir(parents=True)
    (d / "p_aerofoil.raw").write_text("# header only\n\n")
    with pytest.raises(AirfoilSurfaceSamplerError, match="no data rows"):
        read_patch_raw(tmp_path)


def test_read_patch_raw_picks_latest_time_dir(tmp_path: Path) -> None:
    _write_fo_raw(tmp_path, "200", [(0.0, 0.001, 0.0, 0.1)])
    _write_fo_raw(tmp_path, "2000", [(0.0, 0.001, 0.0, 0.9)])
    _write_fo_raw(tmp_path, "1000", [(0.0, 0.001, 0.0, 0.5)])
    loaded = read_patch_raw(tmp_path)
    assert loaded is not None and loaded[0][3] == 0.9


# --- compute_cp tests -----------------------------------------------------


def test_compute_cp_stagnation_cp_equals_one() -> None:
    """At the leading edge (x/c=0), stagnation Cp = 1 for an
    inviscid flow with p = 0.5·ρ·U_inf² at the stagnation point.
    With U_inf=1, ρ=1, p_inf=0 → q_ref=0.5 and p_stag=0.5 → Cp=1."""
    points = [(0.0, 0.0, 0.0, 0.5)]  # (x, y, z, p)
    cp = compute_cp(points, chord=1.0, U_inf=1.0)
    assert len(cp) == 1
    assert cp[0].Cp == pytest.approx(1.0, abs=1e-9)


def test_compute_cp_dedups_spanwise_duplicates() -> None:
    """Thin 2D mesh produces faces at y=+0.001 and y=-0.001 with
    identical (x, z, p). Must collapse to ONE (x_over_c, Cp) point."""
    points = [
        (0.5, 0.001, 0.03, -0.2),   # upper, y=+ span
        (0.5, -0.001, 0.03, -0.2),  # upper, y=- span (duplicate)
        (0.5, 0.001, -0.03, -0.1),  # lower, y=+ span
        (0.5, -0.001, -0.03, -0.1), # lower, y=- span (duplicate)
    ]
    cp = compute_cp(points, chord=1.0, U_inf=1.0)
    # After dedup: 2 points (one upper at z=0.03, one lower at z=-0.03).
    assert len(cp) == 2
    sides = {p.side for p in cp}
    assert sides == {"upper", "lower"}


def test_compute_cp_side_classification() -> None:
    points = [
        (0.5, 0.0, 0.03, -0.2),    # upper
        (0.5, 0.0, -0.03, -0.2),   # lower
        (0.999, 0.0, 0.001, 0.15), # trailing_edge (x/c>0.995, even
                                    # though z>0)
        (0.999, 0.0, -0.001, 0.15),
    ]
    cp = compute_cp(points, chord=1.0, U_inf=1.0)
    # 4 distinct (x, z) buckets (TE x=0.999 with z=±0.001 → both become
    # trailing_edge, keyed separately).
    by_side = {p.side for p in cp}
    assert "upper" in by_side
    assert "lower" in by_side
    assert "trailing_edge" in by_side


def test_compute_cp_negative_cp_on_suction_side() -> None:
    """Upper-surface suction peak has p < p_inf → Cp < 0."""
    points = [
        (0.3, 0.0, 0.05, -0.25),  # p < 0, z > 0 (upper)
    ]
    cp = compute_cp(points, chord=1.0, U_inf=1.0)
    assert cp[0].Cp == pytest.approx(-0.5, abs=1e-9)
    assert cp[0].side == "upper"


def test_compute_cp_scales_with_U_inf() -> None:
    """Cp = p / (0.5 U²). Same p but different U_inf → different Cp."""
    points = [(0.0, 0.0, 0.0, 2.0)]
    cp_u1 = compute_cp(points, chord=1.0, U_inf=1.0)
    cp_u2 = compute_cp(points, chord=1.0, U_inf=2.0)
    # q1 = 0.5, q2 = 2.0 → Cp1 = 4, Cp2 = 1
    assert cp_u1[0].Cp == pytest.approx(4.0)
    assert cp_u2[0].Cp == pytest.approx(1.0)


def test_compute_cp_rejects_zero_chord() -> None:
    with pytest.raises(
        AirfoilSurfaceSamplerError, match="chord must be positive"
    ):
        compute_cp([(0.5, 0.0, 0.03, -0.2)], chord=0.0, U_inf=1.0)


def test_compute_cp_rejects_zero_U_inf() -> None:
    with pytest.raises(
        AirfoilSurfaceSamplerError, match="U_inf must be nonzero"
    ):
        compute_cp([(0.5, 0.0, 0.03, -0.2)], chord=1.0, U_inf=0.0)


def test_compute_cp_rejects_nonpositive_rho() -> None:
    with pytest.raises(
        AirfoilSurfaceSamplerError, match="rho must be positive"
    ):
        compute_cp(
            [(0.5, 0.0, 0.03, -0.2)], chord=1.0, U_inf=1.0, rho=0.0
        )


def test_compute_cp_empty_points_returns_empty() -> None:
    assert compute_cp([], chord=1.0, U_inf=1.0) == []


def test_compute_cp_output_sorted_by_side_then_xoverC() -> None:
    """Output ordering: upper → lower → trailing_edge; within a side,
    ascending x/c."""
    points = [
        (0.7, 0.0, 0.05, -0.1),
        (0.3, 0.0, 0.08, -0.3),
        (0.5, 0.0, -0.05, -0.15),  # lower
        (0.1, 0.0, -0.08, 0.2),     # lower
        (0.999, 0.0, 0.001, 0.1),   # trailing_edge
    ]
    cp = compute_cp(points, chord=1.0, U_inf=1.0)
    # Upper first, ascending x/c.
    upper = [p for p in cp if p.side == "upper"]
    lower = [p for p in cp if p.side == "lower"]
    te = [p for p in cp if p.side == "trailing_edge"]
    assert [p.x_over_c for p in upper] == sorted(p.x_over_c for p in upper)
    assert [p.x_over_c for p in lower] == sorted(p.x_over_c for p in lower)
    # Order in the returned list: upper → lower → trailing_edge.
    idx_upper_last = max(i for i, p in enumerate(cp) if p.side == "upper")
    idx_lower_first = min(i for i, p in enumerate(cp) if p.side == "lower")
    assert idx_upper_last < idx_lower_first
    if te:
        idx_te_first = min(i for i, p in enumerate(cp) if p.side == "trailing_edge")
        idx_lower_last = max(i for i, p in enumerate(cp) if p.side == "lower")
        assert idx_lower_last < idx_te_first


# --- emit_cp_profile (end-to-end) -----------------------------------------


def test_emit_cp_profile_returns_none_when_absent(tmp_path: Path) -> None:
    assert emit_cp_profile(tmp_path, chord=1.0, U_inf=1.0) is None


def test_emit_cp_profile_produces_comparator_shape(tmp_path: Path) -> None:
    """End-to-end: write synthetic FO output, emit, verify keys match
    the comparator-expected schema."""
    rows = [
        (0.0, 0.001, 0.0, 0.5),     # stagnation, shared between sides
        (0.0, -0.001, 0.0, 0.5),    # dup
        (0.3, 0.001, 0.05, -0.25),  # upper x/c=0.3 Cp=-0.5
        (0.3, -0.001, 0.05, -0.25),
        (0.3, 0.001, -0.05, -0.25), # lower x/c=0.3 (symmetric)
        (0.3, -0.001, -0.05, -0.25),
        (1.0, 0.001, 0.0, 0.1),     # trailing edge (x/c=1.0 → TE bucket)
        (1.0, -0.001, 0.0, 0.1),
    ]
    _write_fo_raw(tmp_path, "2000", rows)
    result = emit_cp_profile(tmp_path, chord=1.0, U_inf=1.0)
    assert result is not None
    assert result["pressure_coefficient_source"] == "surface_fo_direct"
    # Upper-surface Cp list (x/c in {0, 0.3} — TE goes to trailing_edge
    # bucket, z=0 point goes to upper).
    assert result["pressure_coefficient_x"] == [0.0, 0.3]
    assert result["pressure_coefficient"] == pytest.approx([1.0, -0.5])
    # Full profile includes lower + TE too.
    profile = result["pressure_coefficient_profile"]
    sides = {p["side"] for p in profile}
    assert "upper" in sides
    assert "lower" in sides
    assert "trailing_edge" in sides


def test_emit_cp_profile_raises_on_malformed(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "airfoilSurface" / "2000"
    d.mkdir(parents=True)
    (d / "p_aerofoil.raw").write_text("# hdr\n0.5 BAD 0.03 -0.2\n")
    with pytest.raises(AirfoilSurfaceSamplerError):
        emit_cp_profile(tmp_path, chord=1.0, U_inf=1.0)


def test_emit_cp_profile_raises_on_zero_faces(tmp_path: Path) -> None:
    """Guard against silent returns if the patch emits no faces at all —
    would typically mean patch-name mismatch (e.g. `airfoil` vs
    `aerofoil`). Should fail loud so the runtime surface problem is
    visible."""
    d = tmp_path / "postProcessing" / "airfoilSurface" / "2000"
    d.mkdir(parents=True)
    (d / "p_aerofoil.raw").write_text("# x y z p\n\n\n")
    with pytest.raises(AirfoilSurfaceSamplerError, match="no data rows"):
        emit_cp_profile(tmp_path, chord=1.0, U_inf=1.0)
