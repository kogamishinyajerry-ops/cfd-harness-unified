"""DEC-V61-043: tests for src/plane_channel_uplus_emitter.py.

Covers:
- Analytic log-law U(y) + known τ_w → emitter recovers u_plus within 1%
  at y+={5, 30, 100} anchor points.
- Parsers accept OpenFOAM-10 .dat / .xy file shapes (headers, comments,
  trailing whitespace, blank tail lines).
- Half-channel fold: cells past centerline are dropped (not mirrored).
- Missing postProcessing/ → emit_uplus_profile returns None (caller
  falls back, per DEC-V61-043 graceful-absence contract).
- Malformed .dat / .xy → PlaneChannelEmitterError raised (per
  DEC-V61-040 round-2 fail-loud-on-corruption pattern).
- Invalid inputs (τ_w ≤ 0, ν ≤ 0, half_height ≤ 0) raise.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.plane_channel_uplus_emitter import (
    PlaneChannelEmitterError,
    PlaneChannelNormalizedProfile,
    _parse_parenthesized_vectors,
    _read_uline_profile,
    _read_wall_shear_stress,
    compute_normalized_profile,
    emit_uplus_profile,
)


# --- helpers ---------------------------------------------------------------


def _write_wall_shear_stress(
    case_dir: Path, time: str, tau_vec: tuple[float, float, float]
) -> None:
    d = case_dir / "postProcessing" / "wallShearStress" / time
    d.mkdir(parents=True, exist_ok=True)
    vx, vy, vz = tau_vec
    (d / "wallShearStress.dat").write_text(
        f"""# Wall shear stress
# Time          patch      min(Wss)      max(Wss)      average(Wss)
0               walls      ({vx} {vy} {vz}) ({vx} {vy} {vz}) ({vx} {vy} {vz})
{time}          walls      ({vx} {vy} {vz}) ({vx} {vy} {vz}) ({vx} {vy} {vz})
""",
        encoding="utf-8",
    )


def _write_uline(
    case_dir: Path, time: str, rows: list[tuple[float, float, float, float]]
) -> None:
    d = case_dir / "postProcessing" / "uLine" / time
    d.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{y} {ux} {uy} {uz}" for y, ux, uy, uz in rows)
    (d / "channelCenter_U.xy").write_text(
        "# y Ux Uy Uz\n" + body + "\n",
        encoding="utf-8",
    )


def _loglaw_u(y_plus: float, u_tau: float) -> float:
    """Classic log law: u+ = (1/κ) ln(y+) + B for y+ > ~30, with a
    linear-layer patch u+ = y+ for y+ < 5. Returns dimensional U."""
    if y_plus <= 0.0:
        return 0.0
    if y_plus < 5.0:
        u_plus = y_plus
    elif y_plus < 30.0:
        # Buffer layer: interpolate linearly between 5 and 30 for
        # simple synthetic data (Spalding is closer to reality but
        # overkill for a test fixture).
        kappa = 0.41
        B = 5.5
        u_plus_low = 5.0
        u_plus_high = (1.0 / kappa) * math.log(30.0) + B
        alpha = (y_plus - 5.0) / 25.0
        u_plus = (1 - alpha) * u_plus_low + alpha * u_plus_high
    else:
        kappa = 0.41
        B = 5.5
        u_plus = (1.0 / kappa) * math.log(y_plus) + B
    return u_plus * u_tau


# --- compute_normalized_profile -------------------------------------------


def test_compute_profile_recovers_known_u_tau() -> None:
    """Feed a known kinematic τ_w and simple linear U(y); verify u_tau,
    Re_tau, and the u+/y+ tuple."""
    tau_w = 4.0  # → u_tau = 2
    nu = 1e-5
    h = 0.5
    # Build a 5-point half-channel profile: y_wall ∈ {0, 0.1, 0.2, 0.3, 0.4, 0.5}
    # Channel y ∈ [-0.5, 0.5]; take lower half y = y_bottom + y_wall.
    y_bottom = -0.5
    y_top = 0.5
    rows = []
    for y_wall in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        y = y_bottom + y_wall
        y_plus_expected = y_wall * math.sqrt(tau_w) / nu
        ux = y_plus_expected * math.sqrt(tau_w)  # u+ = y+ for this linear test
        rows.append((y, ux))
    profile = compute_normalized_profile(
        wall_shear_stress=tau_w,
        u_line=rows,
        nu=nu,
        half_height=h,
        y_bottom=y_bottom,
        y_top=y_top,
    )
    assert profile.u_tau == pytest.approx(2.0, abs=1e-12)
    assert profile.Re_tau == pytest.approx(2.0 * 0.5 / 1e-5)
    # All 6 lower-half points retained; centerline kept (y_wall=0.5=h).
    assert len(profile.y_plus) == 6
    # Linear model: u+ = y+ exactly.
    for yp, up in zip(profile.y_plus, profile.u_plus):
        assert up == pytest.approx(yp, abs=1e-9)


def test_compute_profile_half_channel_fold_keeps_lower_half_only() -> None:
    """Codex DEC-V61-043 round-1 FLAG fix: "half-channel fold" means
    actually drop the upper half, NOT double-fold both halves to the
    same y_wall coords (which gave duplicate y_plus entries). For a
    symmetric 7-point full-channel input, emitter must return exactly
    4 entries (y_wall ∈ {0, 0.2, 0.4, 0.5}) from the lower half only."""
    tau_w = 1.0  # u_tau = 1
    nu = 1e-5
    h = 0.5
    rows = [(y, 1.0) for y in [-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5]]
    profile = compute_normalized_profile(
        wall_shear_stress=tau_w,
        u_line=rows,
        nu=nu,
        half_height=h,
        y_bottom=-0.5,
        y_top=0.5,
    )
    # Lower half (y ≤ 0): y=-0.5 → y_wall=0, y=-0.3 → 0.2,
    # y=-0.1 → 0.4, y=0 → 0.5 (centerline kept exactly once).
    # Upper half dropped.
    assert len(profile.y_plus) == 4
    expected_y_wall = [0.0, 0.2, 0.4, 0.5]
    for yp, y_wall_expected in zip(profile.y_plus, expected_y_wall):
        assert yp == pytest.approx(y_wall_expected * 1.0 / nu, abs=1e-6)


def test_compute_profile_rejects_nonpositive_tau() -> None:
    with pytest.raises(PlaneChannelEmitterError, match="wall_shear_stress must be positive"):
        compute_normalized_profile(
            wall_shear_stress=0.0,
            u_line=[(0.0, 1.0), (0.1, 1.1)],
            nu=1e-5,
            half_height=0.5,
        )


def test_compute_profile_rejects_nonpositive_nu() -> None:
    with pytest.raises(PlaneChannelEmitterError, match="nu must be positive"):
        compute_normalized_profile(
            wall_shear_stress=1.0,
            u_line=[(0.0, 1.0), (0.1, 1.1)],
            nu=0.0,
            half_height=0.5,
        )


def test_compute_profile_rejects_nonpositive_half_height() -> None:
    with pytest.raises(PlaneChannelEmitterError, match="half_height must be positive"):
        compute_normalized_profile(
            wall_shear_stress=1.0,
            u_line=[(0.0, 1.0), (0.1, 1.1)],
            nu=1e-5,
            half_height=-0.1,
        )


# --- parser tests ----------------------------------------------------------


def test_parse_parenthesized_vectors_handles_multiple() -> None:
    line = "50 walls (1.0 2.0 3.0) (4.0 5.0 6.0) (7.0 8.0 9.0)"
    vecs = _parse_parenthesized_vectors(line)
    assert vecs == [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0), (7.0, 8.0, 9.0)]


def test_parse_parenthesized_vectors_skips_non_3_tuples() -> None:
    line = "50 (1.0 2.0) (3.0 4.0 5.0) (a b c)"
    vecs = _parse_parenthesized_vectors(line)
    assert vecs == [(3.0, 4.0, 5.0)]


def test_read_wall_shear_stress_latest_time(tmp_path: Path) -> None:
    _write_wall_shear_stress(tmp_path, "50", (-0.01, 0.0, 0.0))
    # Also drop an earlier time dir that should be ignored.
    _write_wall_shear_stress(tmp_path, "10", (-0.5, 0.0, 0.0))
    tau = _read_wall_shear_stress(tmp_path)
    assert tau == pytest.approx(0.01, abs=1e-9)


def test_read_wall_shear_stress_returns_none_when_absent(tmp_path: Path) -> None:
    # No postProcessing dir at all.
    assert _read_wall_shear_stress(tmp_path) is None


def test_read_wall_shear_stress_raises_on_empty_file(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "wallShearStress" / "50"
    d.mkdir(parents=True)
    (d / "wallShearStress.dat").write_text("# only comments\n")
    with pytest.raises(PlaneChannelEmitterError, match="no data rows"):
        _read_wall_shear_stress(tmp_path)


def test_read_wall_shear_stress_raises_on_no_vectors(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "wallShearStress" / "50"
    d.mkdir(parents=True)
    (d / "wallShearStress.dat").write_text("# hdr\n50 walls novectorshere\n")
    with pytest.raises(PlaneChannelEmitterError, match="no .* vector tokens"):
        _read_wall_shear_stress(tmp_path)


def test_read_uline_profile_reads_129_points(tmp_path: Path) -> None:
    rows = [(i * 0.01, i * 0.1, 0.0, 0.0) for i in range(-64, 65)]
    _write_uline(tmp_path, "50", rows)
    loaded = _read_uline_profile(tmp_path)
    assert loaded is not None
    assert len(loaded) == 129
    # Sorted ascending by y.
    assert loaded[0][0] == pytest.approx(-0.64)
    assert loaded[-1][0] == pytest.approx(0.64)


def test_read_uline_profile_returns_none_when_absent(tmp_path: Path) -> None:
    assert _read_uline_profile(tmp_path) is None


def test_read_uline_profile_reads_of10_filename(tmp_path: Path) -> None:
    """Stage B post-R3 fix: OpenFOAM 10's `sets` FO writes
    `<set_name>.xy` (single packed file with all components),
    not the legacy `<set_name>_<field>.xy` per-field naming.
    The reader MUST find the OF10 form first; otherwise the case
    dies with `uLine output absent` even though the file exists.
    """
    d = tmp_path / "postProcessing" / "uLine" / "50"
    d.mkdir(parents=True)
    rows = [(i * 0.01, i * 0.1, 0.0, 0.0) for i in range(-64, 65)]
    body = "\n".join(f"{y} {ux} {uy} {uz}" for y, ux, uy, uz in rows)
    # OF10 form: `channelCenter.xy` (no _U suffix)
    (d / "channelCenter.xy").write_text("# y Ux Uy Uz\n" + body + "\n", encoding="utf-8")
    loaded = _read_uline_profile(tmp_path)
    assert loaded is not None
    assert len(loaded) == 129


def test_read_uline_profile_does_not_silently_return_u_when_pressure_requested(
    tmp_path: Path,
) -> None:
    """Codex round-5 F7 regression: the OF10-form file
    `channelCenter.xy` packs only `U` (columns: y Ux Uy Uz). If the
    caller asks for `field="p"` with both files present, the reader
    must NOT silently parse Ux out of the packed file and pretend
    that's pressure — that's a wrong-field/wrong-column read. The
    only correct source for non-U fields is the legacy
    `<set_name>_<field>.xy` per-field file. If neither exists for
    the requested field, return None.
    """
    d = tmp_path / "postProcessing" / "uLine" / "50"
    d.mkdir(parents=True)
    rows = [(i * 0.01, i * 0.1, 0.0, 0.0) for i in range(-64, 65)]
    body = "\n".join(f"{y} {ux} {uy} {uz}" for y, ux, uy, uz in rows)
    # Both files present, but the caller wants `p` — the OF10 packed
    # file holds U only.
    (d / "channelCenter.xy").write_text("# y Ux Uy Uz\n" + body + "\n", encoding="utf-8")
    # No `channelCenter_p.xy` — pressure data is unavailable.
    assert _read_uline_profile(tmp_path, field="p") is None, (
        "Reader must not return Ux from the packed-U file when caller "
        "explicitly requested `field=\"p\"`."
    )


def test_read_uline_profile_field_p_uses_legacy_per_field_file(
    tmp_path: Path,
) -> None:
    """Companion to F7: when the legacy `<set_name>_p.xy` exists,
    the reader should use it (and parse y + p columns)."""
    d = tmp_path / "postProcessing" / "uLine" / "50"
    d.mkdir(parents=True)
    rows = [(i * 0.01, 1.5 * i * 0.1) for i in range(-64, 65)]
    body = "\n".join(f"{y} {p}" for y, p in rows)
    (d / "channelCenter_p.xy").write_text("# y p\n" + body + "\n", encoding="utf-8")
    loaded = _read_uline_profile(tmp_path, field="p")
    assert loaded is not None
    assert len(loaded) == 129


def test_read_uline_profile_coexistence_routes_field_correctly(
    tmp_path: Path,
) -> None:
    """Codex round-6 F9 regression: the original round-5 bug was a
    mixed-file precedence issue (both `<set>.xy` and `<set>_p.xy`
    present in the same time directory). Lock down that with both
    files coexisting, `field="U"` → packed `<set>.xy` (column 2 =
    Ux ≈ 0.1) and `field="p"` → legacy `<set>_p.xy` (pressure
    column ≈ 0.15). Without F7's gating, the `p` request would
    silently return the same Ux value from the packed file.
    """
    d = tmp_path / "postProcessing" / "uLine" / "50"
    d.mkdir(parents=True)
    n = 129
    half = n // 2
    u_rows = [(i * 0.01, i * 0.1, 0.0, 0.0) for i in range(-half, half + 1)]
    p_rows = [(i * 0.01, i * 0.15) for i in range(-half, half + 1)]
    (d / "channelCenter.xy").write_text(
        "# y Ux Uy Uz\n" + "\n".join(f"{y} {ux} {uy} {uz}" for y, ux, uy, uz in u_rows) + "\n",
        encoding="utf-8",
    )
    (d / "channelCenter_p.xy").write_text(
        "# y p\n" + "\n".join(f"{y} {p}" for y, p in p_rows) + "\n",
        encoding="utf-8",
    )

    u_loaded = _read_uline_profile(tmp_path, field="U")
    p_loaded = _read_uline_profile(tmp_path, field="p")
    assert u_loaded is not None and p_loaded is not None

    # u-loaded came from packed `<set>.xy` (column 2 = i * 0.1).
    # p-loaded came from legacy `<set>_p.xy` (column 2 = i * 0.15).
    # Pick the same y-coordinate (i=10 → y=0.1) and verify the
    # second-column values diverge per the source semantics.
    by_y_u = {y: ux for y, ux in u_loaded}
    by_y_p = {y: p for y, p in p_loaded}
    target_y = 0.1
    assert abs(by_y_u[target_y] - 1.0) < 1e-9, (
        f"`field='U'` must read Ux from packed file → 1.0 at y=0.1, got {by_y_u[target_y]}"
    )
    assert abs(by_y_p[target_y] - 1.5) < 1e-9, (
        f"`field='p'` must read pressure from legacy file → 1.5 at y=0.1, got {by_y_p[target_y]}"
    )


def test_read_uline_profile_raises_on_sparse(tmp_path: Path) -> None:
    """Codex DEC-V61-043 round-1 FLAG fix: threshold raised from 4 to
    64 (half the generator's 129-point default) to catch gross
    truncation of the line-uniform sampler output."""
    _write_uline(tmp_path, "50", [(0.0, 1.0, 0.0, 0.0), (0.1, 1.1, 0.0, 0.0)])
    with pytest.raises(PlaneChannelEmitterError, match="expected ≥64"):
        _read_uline_profile(tmp_path)


def test_read_uline_profile_raises_on_nonnumeric(tmp_path: Path) -> None:
    d = tmp_path / "postProcessing" / "uLine" / "50"
    d.mkdir(parents=True)
    (d / "channelCenter_U.xy").write_text(
        "# y Ux Uy Uz\n0.0 1.0 0 0\n0.1 1.1 0 0\n0.2 BAD 0 0\n0.3 1.3 0 0\n"
    )
    with pytest.raises(PlaneChannelEmitterError, match="non-numeric"):
        _read_uline_profile(tmp_path)


# --- end-to-end emit_uplus_profile ----------------------------------------


def test_emit_uplus_profile_returns_none_when_postprocessing_absent(
    tmp_path: Path,
) -> None:
    """No postProcessing → None (caller falls back — graceful absence)."""
    result = emit_uplus_profile(tmp_path, nu=1e-5, half_height=0.5)
    assert result is None


def test_emit_uplus_profile_roundtrip_loglaw(tmp_path: Path) -> None:
    """Build a realistic synthetic case: τ_w → u_τ=0.05, log-law U(y),
    129-point line sampler. Verify emitted u+ matches analytical ±1%
    at y+∈{5, 30, 100}."""
    u_tau_true = 0.05
    tau_w_kinematic = u_tau_true ** 2  # = 2.5e-3
    nu = 1e-5
    h = 0.5

    # Write FO output.
    _write_wall_shear_stress(tmp_path, "50", (tau_w_kinematic, 0.0, 0.0))
    rows: list[tuple[float, float, float, float]] = []
    n_points = 129
    for i in range(n_points):
        alpha = i / (n_points - 1)
        y = -h + 2 * h * alpha  # y ∈ [-0.5, 0.5]
        y_wall = min(abs(y - (-h)), abs(y - h))
        y_plus = y_wall * u_tau_true / nu
        ux = _loglaw_u(y_plus, u_tau_true)
        rows.append((y, ux, 0.0, 0.0))
    _write_uline(tmp_path, "50", rows)

    result = emit_uplus_profile(tmp_path, nu=nu, half_height=h)
    assert result is not None
    assert result["u_tau"] == pytest.approx(u_tau_true, abs=1e-6)
    assert result["Re_tau"] == pytest.approx(u_tau_true * h / nu)
    assert result["u_mean_profile_source"] == "wallShearStress_fo_v1"

    y_plus_list = result["u_mean_profile_y_plus"]
    u_plus_list = result["u_mean_profile"]
    assert len(y_plus_list) == len(u_plus_list) > 10

    # Verify u+ matches analytic log-law within 2% at the canonical points.
    # (Tolerance >1% here because the sampled y+ values don't hit {5, 30,
    # 100} exactly; pick the nearest sampled y+ and compare.)
    def _find_nearest(target: float) -> tuple[float, float]:
        nearest_idx = min(
            range(len(y_plus_list)),
            key=lambda j: abs(y_plus_list[j] - target),
        )
        return y_plus_list[nearest_idx], u_plus_list[nearest_idx]

    for y_plus_target in (30.0, 100.0):  # skip 5 — log+linear hybrid crude
        y_p, u_p = _find_nearest(y_plus_target)
        # u+ = (1/0.41) ln(y_p) + 5.5  for log-law region
        expected = (1.0 / 0.41) * math.log(y_p) + 5.5
        assert abs(u_p - expected) / expected < 0.05, (
            f"y+={y_p:.2f}: got u+={u_p:.4f}, expected ≈{expected:.4f}"
        )


def test_emit_uplus_profile_raises_on_partial_fo_output_wss_only(
    tmp_path: Path,
) -> None:
    """Codex DEC-V61-043 round-1 BLOCKER: wallShearStress present but
    uLine absent means the run emitted half the required evidence.
    Must raise (not return None) so the comparator sees
    MISSING_TARGET_QUANTITY rather than silently falling back."""
    _write_wall_shear_stress(tmp_path, "50", (0.01, 0.0, 0.0))
    # No uLine output.
    with pytest.raises(PlaneChannelEmitterError, match="uLine output absent"):
        emit_uplus_profile(tmp_path, nu=1e-5, half_height=0.5)


def test_emit_uplus_profile_raises_on_partial_fo_output_uline_only(
    tmp_path: Path,
) -> None:
    """Symmetric: uLine present but wallShearStress absent must raise."""
    rows = [
        (-0.5 + 0.01 * i, 0.0, 0.0, 0.0) for i in range(100)
    ]
    _write_uline(tmp_path, "50", rows)
    with pytest.raises(PlaneChannelEmitterError, match="wallShearStress output absent"):
        emit_uplus_profile(tmp_path, nu=1e-5, half_height=0.5)


def test_emit_uplus_profile_propagates_malformed_error(tmp_path: Path) -> None:
    """Malformed FO input must raise (fail loud), not silently return None."""
    # Empty wallShearStress.dat — comment-only.
    d1 = tmp_path / "postProcessing" / "wallShearStress" / "50"
    d1.mkdir(parents=True)
    (d1 / "wallShearStress.dat").write_text("# only comments\n")
    # uLine is fine.
    _write_uline(tmp_path, "50", [
        (-0.5, 0.0, 0.0, 0.0),
        (-0.25, 0.5, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.25, 0.5, 0.0, 0.0),
        (0.5, 0.0, 0.0, 0.0),
    ])
    with pytest.raises(PlaneChannelEmitterError):
        emit_uplus_profile(tmp_path, nu=1e-5, half_height=0.5)
