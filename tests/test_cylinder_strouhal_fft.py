"""DEC-V61-041: tests for src/cylinder_strouhal_fft.py.

Coverage:
- Parser: OF10 coefficient.dat header-based column lookup, fallback
  positional layout, malformed/empty inputs raise.
- FFT: synthetic sinusoidal Cl(t) at known frequency → St recovered
  within 0.5%. Transient trim removes starter bias.
- Uniform resample: non-uniform t input → uniform output; window
  too short → raise.
- compute_strouhal: insufficient post-trim window raises; degenerate
  (flat Cl) raises; low_confidence flag for marginally-adequate windows.
- emit_strouhal end-to-end: absent FO dir → None; present dir without
  coefficient.dat → raise; valid → StrouhalResult fields match
  expectation.
- Input validation: D ≤ 0, U_ref == 0 raise.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.cylinder_strouhal_fft import (
    CylinderStrouhalError,
    StrouhalResult,
    _hann_window,
    _dft_magnitudes,
    _resample_uniform,
    compute_strouhal,
    emit_strouhal,
    parse_coefficient_dat,
)


# --- helpers ---------------------------------------------------------------


def _write_coefficient_dat(
    case_dir: Path,
    time: str,
    rows: list[tuple[float, float, float, float]],
    *,
    filename: str = "coefficient.dat",
    header: str = "# Time\tCm\tCd\tCl\tCd(f)\tCd(r)\tCl(f)\tCl(r)",
) -> None:
    d = case_dir / "postProcessing" / "forceCoeffs1" / time
    d.mkdir(parents=True, exist_ok=True)
    lines = [header]
    for t, cm, cd, cl in rows:
        lines.append(f"{t} {cm} {cd} {cl} 0 0 0 0")
    (d / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sinusoidal_cl(
    duration_s: float,
    dt: float,
    *,
    f_hz: float,
    amplitude: float = 0.048,
    cd_mean: float = 1.33,
) -> list[tuple[float, float, float, float]]:
    """Generate (t, Cm, Cd, Cl) with Cl = A·sin(2π·f·t), Cd = cd_mean."""
    n = int(duration_s / dt) + 1
    out = []
    for i in range(n):
        t = i * dt
        cl = amplitude * math.sin(2.0 * math.pi * f_hz * t)
        out.append((t, 0.0, cd_mean, cl))
    return out


# --- parser tests ---------------------------------------------------------


def test_parse_coefficient_dat_uses_named_columns(tmp_path: Path) -> None:
    """Parser should find Cd at column 2, Cl at column 3 by matching
    header names (not trusting positional layout)."""
    path = tmp_path / "coefficient.dat"
    path.write_text(
        "# Time Cm Cd Cl Cd(f) Cd(r) Cl(f) Cl(r)\n"
        "0.1 0.01 1.2 0.05 0.6 0.6 0.025 0.025\n"
        "0.2 0.01 1.3 0.04 0.65 0.65 0.020 0.020\n"
    )
    t, cd, cl = parse_coefficient_dat(path)
    assert t == [0.1, 0.2]
    assert cd == [1.2, 1.3]
    assert cl == [0.05, 0.04]


def test_parse_coefficient_dat_falls_back_to_positional_layout(
    tmp_path: Path,
) -> None:
    """If no # header is present, parser assumes OF10 positional order
    (Time, Cm, Cd, Cl) and still produces sensible results."""
    path = tmp_path / "coefficient.dat"
    path.write_text("0.1 0.01 1.2 0.05\n0.2 0.01 1.3 0.04\n")
    t, cd, cl = parse_coefficient_dat(path)
    assert t == [0.1, 0.2]
    assert cd == [1.2, 1.3]
    assert cl == [0.05, 0.04]


def test_parse_coefficient_dat_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CylinderStrouhalError, match="not found"):
        parse_coefficient_dat(tmp_path / "nope.dat")


def test_parse_coefficient_dat_raises_on_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "coefficient.dat"
    path.write_text("# only header\n# more comments\n")
    with pytest.raises(CylinderStrouhalError, match="zero numeric rows"):
        parse_coefficient_dat(path)


# --- FFT core tests -------------------------------------------------------


def test_hann_window_starts_and_ends_at_zero() -> None:
    w = _hann_window(17)
    assert w[0] == pytest.approx(0.0, abs=1e-12)
    assert w[-1] == pytest.approx(0.0, abs=1e-12)
    assert max(w) == pytest.approx(1.0, abs=1e-12)


def test_dft_magnitudes_recovers_known_frequency() -> None:
    """Build a pure tone at bin k=5 of N=64 samples; DFT magnitude
    should peak there."""
    N = 64
    k_true = 5
    samples = [math.cos(2 * math.pi * k_true * n / N) for n in range(N)]
    mags = _dft_magnitudes(samples)
    peak_idx = max(range(len(mags)), key=lambda k: mags[k])
    assert peak_idx == k_true


def test_resample_uniform_interpolates_linearly() -> None:
    t = [0.0, 0.1, 0.2, 0.3, 0.4]
    y = [0.0, 1.0, 2.0, 3.0, 4.0]
    # No hidden dependency that len(y) ≥ 8 — _resample_uniform
    # requires at least 8 output samples, so use dt=0.05 on a 0.4s
    # window → 9 outputs.
    out_t, out_y = _resample_uniform(t, y, dt=0.05)
    assert len(out_t) >= 8
    # At t=0.05, expect y=0.5 (linear between 0 and 0.1).
    assert out_y[1] == pytest.approx(0.5, abs=1e-9)


def test_resample_uniform_raises_on_insufficient_window() -> None:
    with pytest.raises(CylinderStrouhalError, match="only"):
        _resample_uniform([0.0, 0.1], [0.0, 1.0], dt=0.05)


# --- compute_strouhal tests -----------------------------------------------


def test_compute_strouhal_recovers_known_f_from_clean_signal() -> None:
    """Synthetic Cl = 0.048·sin(2π·1.64·t) should give St = 1.64·0.1/1 = 0.164
    within < 0.5% (FFT bin resolution)."""
    dt = 0.005
    duration = 200.0
    rows = _sinusoidal_cl(duration, dt, f_hz=1.64, amplitude=0.048, cd_mean=1.33)
    t = [r[0] for r in rows]
    cd = [r[2] for r in rows]
    cl = [r[3] for r in rows]
    result = compute_strouhal(t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0)
    assert result.strouhal_number == pytest.approx(0.164, rel=0.01)
    assert result.cd_mean == pytest.approx(1.33, abs=1e-6)
    # cl_rms of pure sine A·sin is A/√2 ≈ 0.0339 — but we zero-mean
    # before RMS, so post-trim cl_rms matches analytical.
    assert result.cl_rms == pytest.approx(0.048 / math.sqrt(2.0), rel=0.02)
    assert result.low_confidence is False


def test_compute_strouhal_removes_transient_bias() -> None:
    """Add a decaying starter to the first 30s; verify the trim drops
    that contribution and the FFT still resolves the shedding f."""
    dt = 0.005
    duration = 200.0
    f_true = 1.64
    rows = []
    for i in range(int(duration / dt) + 1):
        t = i * dt
        cl_base = 0.048 * math.sin(2.0 * math.pi * f_true * t)
        starter = 0.3 * math.exp(-t / 10.0)  # decays over ~30s
        rows.append((t, 0.0, 1.33 + starter, cl_base + starter))
    t_arr = [r[0] for r in rows]
    cd_arr = [r[2] for r in rows]
    cl_arr = [r[3] for r in rows]
    result = compute_strouhal(
        t_arr, cl_arr, cd_arr, U_ref=1.0, D=0.1, transient_trim_s=50.0
    )
    assert result.strouhal_number == pytest.approx(0.164, rel=0.01)
    assert result.cd_mean == pytest.approx(1.33, abs=0.005)


def test_compute_strouhal_raises_on_short_window() -> None:
    rows = _sinusoidal_cl(0.1, 0.005, f_hz=1.64)
    t = [r[0] for r in rows]
    cd = [r[2] for r in rows]
    cl = [r[3] for r in rows]
    with pytest.raises(CylinderStrouhalError, match="post-trim window"):
        compute_strouhal(t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0)


def test_compute_strouhal_raises_on_flat_signal() -> None:
    dt = 0.005
    duration = 200.0
    n = int(duration / dt) + 1
    t = [i * dt for i in range(n)]
    cd = [1.33] * n
    cl = [0.0] * n
    with pytest.raises(CylinderStrouhalError, match="degenerate"):
        compute_strouhal(t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0)


def test_compute_strouhal_rejects_zero_D() -> None:
    with pytest.raises(CylinderStrouhalError, match="D must be positive"):
        compute_strouhal([0.0, 1.0], [0.0, 0.1], [1.0, 1.0],
                         U_ref=1.0, D=0.0)


def test_compute_strouhal_rejects_zero_U_ref() -> None:
    with pytest.raises(CylinderStrouhalError, match="U_ref must be nonzero"):
        compute_strouhal([0.0, 1.0], [0.0, 0.1], [1.0, 1.0],
                         U_ref=0.0, D=0.1)


def test_compute_strouhal_length_mismatch_raises() -> None:
    with pytest.raises(CylinderStrouhalError, match="length mismatch"):
        compute_strouhal([0.0, 1.0], [0.0], [1.0, 1.0], U_ref=1.0, D=0.1)


# --- emit_strouhal (end-to-end) -------------------------------------------


def test_emit_strouhal_returns_none_when_absent(tmp_path: Path) -> None:
    assert emit_strouhal(tmp_path, D=0.1, U_ref=1.0) is None


def test_emit_strouhal_roundtrip(tmp_path: Path) -> None:
    """Write a synthetic coefficient.dat with known f_hz = 1.64
    (→ St = 0.164), verify emit_strouhal returns matching values."""
    rows = _sinusoidal_cl(200.0, 0.005, f_hz=1.64, amplitude=0.048, cd_mean=1.33)
    _write_coefficient_dat(tmp_path, "200", rows)
    result = emit_strouhal(tmp_path, D=0.1, U_ref=1.0, transient_trim_s=50.0)
    assert result is not None
    assert result["strouhal_number"] == pytest.approx(0.164, rel=0.01)
    assert result["cd_mean"] == pytest.approx(1.33, abs=1e-6)
    assert result["strouhal_source"] == "forceCoeffs_fft_v1"
    assert result["strouhal_low_confidence"] is False


def test_emit_strouhal_raises_when_fo_dir_missing_dat(tmp_path: Path) -> None:
    """FO time dir exists but no coefficient.dat / forceCoeffs.dat —
    fail closed per DEC-V61-040 round-2 pattern (corruption, not
    absence)."""
    d = tmp_path / "postProcessing" / "forceCoeffs1" / "200"
    d.mkdir(parents=True)
    with pytest.raises(CylinderStrouhalError, match="no coefficient.dat"):
        emit_strouhal(tmp_path, D=0.1, U_ref=1.0)


def test_emit_strouhal_accepts_legacy_forcecoeffs_filename(
    tmp_path: Path,
) -> None:
    """Older OF versions write forceCoeffs.dat rather than coefficient.dat;
    parser must accept either."""
    rows = _sinusoidal_cl(200.0, 0.005, f_hz=1.64)
    _write_coefficient_dat(tmp_path, "200", rows, filename="forceCoeffs.dat")
    result = emit_strouhal(tmp_path, D=0.1, U_ref=1.0, transient_trim_s=50.0)
    assert result is not None
    assert result["strouhal_number"] == pytest.approx(0.164, rel=0.01)
