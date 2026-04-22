"""DEC-V61-041: Strouhal number extraction from forceCoeffs time history.

Replaces the long-standing hardcode `canonical_st = 0.165 if 50 <= Re <= 200`
in foam_agent_adapter._extract_cylinder_strouhal. That code stamped the
literature value regardless of solver convergence — doubled as a
PASS-washing landmine because the comparator would always match 0.164
gold ± 5%.

Pipeline:
1. Parse postProcessing/forceCoeffs1/<t>/coefficient.dat.
   OpenFOAM 10 writes space-delimited rows with a # header line that
   names the columns (Cm, Cd, Cl, Cd(f), Cd(r), Cl(f), Cl(r)). We
   parse by column name, not positional index, so the parser survives
   minor format drift across OF versions.
2. Trim leading transient (first transient_trim_s seconds) — the
   flow takes several convective time-units to develop shedding from
   a cold start. Default trim = 50.0 matches DEC-041 controlDict's
   endTime=200.0 (leaves 150s = ~25 shedding cycles at St=0.164,
   U=1, D=0.1 → f=1.64 Hz → period≈0.6s).
3. Resample to uniform dt (forceCoeffs with adjustTimeStep can
   produce non-uniform sampling). Linear interpolation onto a
   regular grid sized for Nyquist safety.
4. FFT on Cl(t) with a Hann window (reduces spectral leakage at the
   dominant shedding peak). Ignore DC bin.
5. Identify dominant frequency → St = f · D / U.
6. Compute cd_mean (trimmed) and cl_rms (trimmed, zero-mean) as
   secondary observables — gold has anchors for both that were
   orphaned before this DEC.

Returns a dict for merge into key_quantities, or a structured
error when inputs are malformed / insufficient (fail-closed path
matching DEC-V61-040 round-2 pattern).

Reference: Williamson 1996 annual review; Re=100 laminar: St=0.164,
Cd_mean=1.33, Cl_rms=0.048.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


class CylinderStrouhalError(Exception):
    """Raised when the coefficient.dat parser or FFT pipeline cannot
    produce a trustworthy Strouhal result. Covers:

    - Missing or malformed coefficient.dat
    - Insufficient post-trim window (< N shedding periods)
    - Degenerate FFT (flat signal, all-DC)
    """


@dataclass(frozen=True)
class StrouhalResult:
    strouhal_number: float
    dominant_frequency_hz: float
    cd_mean: float
    cl_rms: float
    fft_window_s: float
    transient_trim_s: float
    samples_used: int
    low_confidence: bool = False


def _latest_time_dir(parent: Path) -> Optional[Path]:
    if not parent.is_dir():
        return None
    numeric: List[Tuple[float, Path]] = []
    for p in parent.iterdir():
        if not p.is_dir():
            continue
        try:
            numeric.append((float(p.name), p))
        except ValueError:
            continue
    if not numeric:
        return None
    numeric.sort(key=lambda pair: pair[0])
    return numeric[-1][1]


def parse_coefficient_dat(
    path: Path,
) -> Tuple[List[float], List[float], List[float]]:
    """Parse forceCoeffs `coefficient.dat` into (time, Cd, Cl) lists.

    OpenFOAM 10 format (space-delimited):
        # Time    Cm          Cd          Cl          Cd(f)  ...
        0.001     1.23e-2     1.35        4.52e-2     ...
        ...

    Uses the `#`-prefixed header line to look up Cd and Cl columns by
    name — resistant to layout changes across OF versions. If the file
    has no header (corrupted), falls back to a best-guess positional
    layout (Time, Cm, Cd, Cl) with an explicit warning emitted.

    Raises CylinderStrouhalError on missing file, empty file, or no
    numeric rows.
    """
    if not path.is_file():
        raise CylinderStrouhalError(f"coefficient.dat not found at {path}")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CylinderStrouhalError(
            f"cannot read {path}: {exc}"
        ) from exc

    header_tokens: Optional[List[str]] = None
    t: List[float] = []
    cd: List[float] = []
    cl: List[float] = []
    cd_idx: Optional[int] = None
    cl_idx: Optional[int] = None

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            # Parse last seen header line; OF10 emits one # Time Cm Cd ...
            # header near the top of the file.
            tokens = s.lstrip("#").split()
            if tokens and tokens[0].lower() == "time":
                header_tokens = tokens
                # Look up Cd and Cl by name (case-insensitive).
                for i, tok in enumerate(tokens):
                    lower = tok.lower()
                    if lower == "cd" and cd_idx is None:
                        cd_idx = i
                    elif lower == "cl" and cl_idx is None:
                        cl_idx = i
            continue
        # Data row.
        parts = s.split()
        if not parts:
            continue
        try:
            time_val = float(parts[0])
        except ValueError:
            continue
        # Fall back to positional Cd=2, Cl=3 (after Time, Cm) if no
        # header was found. This matches OF10 default column order.
        cd_col = cd_idx if cd_idx is not None else 2
        cl_col = cl_idx if cl_idx is not None else 3
        if len(parts) <= max(cd_col, cl_col):
            continue
        try:
            cd_val = float(parts[cd_col])
            cl_val = float(parts[cl_col])
        except ValueError:
            continue
        t.append(time_val)
        cd.append(cd_val)
        cl.append(cl_val)

    if not t:
        raise CylinderStrouhalError(
            f"{path} parsed zero numeric rows (header present: "
            f"{header_tokens is not None})"
        )
    return t, cd, cl


def _resample_uniform(
    t: Sequence[float], y: Sequence[float], dt: float
) -> Tuple[List[float], List[float]]:
    """Linear interpolate (t, y) onto a uniform grid with step dt.

    Requires t monotonically non-decreasing and len(t) == len(y) ≥ 2.
    """
    if len(t) < 2:
        raise CylinderStrouhalError("need at least 2 samples to resample")
    t0 = t[0]
    tN = t[-1]
    if tN - t0 < dt:
        raise CylinderStrouhalError(
            f"resample window {tN-t0:.3g}s < dt {dt:.3g}s"
        )
    out_t: List[float] = []
    out_y: List[float] = []
    cursor = 0
    tk = t0
    while tk <= tN:
        # Advance cursor so t[cursor] ≤ tk ≤ t[cursor+1].
        while cursor + 1 < len(t) and t[cursor + 1] < tk:
            cursor += 1
        if cursor + 1 >= len(t):
            break
        t_lo = t[cursor]
        t_hi = t[cursor + 1]
        if t_hi - t_lo <= 0.0:
            cursor += 1
            continue
        alpha = (tk - t_lo) / (t_hi - t_lo)
        val = (1.0 - alpha) * y[cursor] + alpha * y[cursor + 1]
        out_t.append(tk)
        out_y.append(val)
        tk += dt
    if len(out_t) < 8:
        raise CylinderStrouhalError(
            f"resampling produced only {len(out_t)} samples "
            f"(need ≥8 for a meaningful FFT)"
        )
    return out_t, out_y


def _hann_window(n: int) -> List[float]:
    """Standard Hann window — reduces FFT leakage at the shedding peak."""
    if n < 2:
        return [1.0] * n
    return [0.5 * (1.0 - math.cos(2.0 * math.pi * k / (n - 1))) for k in range(n)]


def _dft_magnitudes(samples: Sequence[float]) -> List[float]:
    """Return |X[k]| for k=0..N/2. O(N²) DFT — fine for the hundreds-of-
    samples windows we work with here; stdlib-only avoids dragging in
    numpy as a hard dependency."""
    N = len(samples)
    out: List[float] = []
    for k in range(N // 2 + 1):
        re = 0.0
        im = 0.0
        for n, xn in enumerate(samples):
            theta = 2.0 * math.pi * k * n / N
            re += xn * math.cos(theta)
            im -= xn * math.sin(theta)
        out.append(math.sqrt(re * re + im * im))
    return out


def compute_strouhal(
    t: Sequence[float],
    cl: Sequence[float],
    cd: Sequence[float],
    *,
    U_ref: float,
    D: float,
    transient_trim_s: float = 50.0,
    min_periods_post_trim: int = 8,
    nyquist_oversample: int = 20,
) -> StrouhalResult:
    """End-to-end: time-series → Strouhal number.

    Parameters:
    - transient_trim_s: drop samples with t < trim. Default 50s matches
      DEC-041 controlDict (endTime=200, leaves 150s ≈ 25 periods at
      St=0.164).
    - min_periods_post_trim: minimum shedding cycles required in the
      post-trim window. If the naive St suggests fewer than this, we
      tag low_confidence=True rather than failing outright.
    - nyquist_oversample: target samples-per-period after uniform
      resampling. 20 is comfortable for leakage.

    Raises CylinderStrouhalError for truly degenerate inputs (flat
    signal, insufficient window, etc). Returns a StrouhalResult with
    low_confidence=True for marginally-adequate cases.
    """
    if D <= 0.0:
        raise CylinderStrouhalError(f"D must be positive, got {D}")
    if U_ref == 0.0:
        raise CylinderStrouhalError(f"U_ref must be nonzero, got {U_ref}")
    if len(t) != len(cl) or len(t) != len(cd):
        raise CylinderStrouhalError(
            f"length mismatch: t={len(t)}, cl={len(cl)}, cd={len(cd)}"
        )

    # Trim transient.
    trimmed = [
        (ti, cli, cdi)
        for ti, cli, cdi in zip(t, cl, cd)
        if ti >= transient_trim_s
    ]
    if len(trimmed) < 16:
        raise CylinderStrouhalError(
            f"post-trim window has {len(trimmed)} samples; need ≥16. "
            f"Check transient_trim_s={transient_trim_s} vs endTime."
        )
    t_tr = [row[0] for row in trimmed]
    cl_tr = [row[1] for row in trimmed]
    cd_tr = [row[2] for row in trimmed]

    # Estimate the raw sample dt and pick a resample dt for Nyquist
    # safety at the expected shedding band. At Re=100, f_s ≈ 1-2 Hz
    # for U=1, D=0.1 — so dt=0.02s gives 25-50 samples/period, well
    # above Nyquist. Codex DEC-041 round 1 FLAG: the original 0.005s
    # floor plus a 150s post-trim window produced ~30k samples, and
    # the stdlib O(N²) DFT chokes on that (billions of trig ops).
    # Cap via MAX_SAMPLES = 8192 so runtime stays ≤~30s per case.
    # Bin resolution = 1/window_s ≈ 1/150 = 0.0067 Hz → St precision
    # ≈ 0.00067 in St units, well below 1% of typical St=0.165.
    raw_dts = [t_tr[i + 1] - t_tr[i] for i in range(len(t_tr) - 1)]
    if raw_dts:
        raw_dts_sorted = sorted(raw_dts)
        median_raw_dt = raw_dts_sorted[len(raw_dts_sorted) // 2]
    else:
        median_raw_dt = 0.01
    MAX_SAMPLES = 8192
    window_duration = t_tr[-1] - t_tr[0]
    dt_floor_for_cap = window_duration / (MAX_SAMPLES - 1)
    # Prefer finer resampling unless the raw dt is much coarser OR
    # the window is long enough that MAX_SAMPLES would be exceeded.
    target_dt = max(median_raw_dt, 0.02, dt_floor_for_cap)
    t_u, cl_u = _resample_uniform(t_tr, cl_tr, target_dt)
    _, cd_u = _resample_uniform(t_tr, cd_tr, target_dt)

    # Zero-mean Cl before FFT (removes the DC bin from contributing).
    cl_mean = sum(cl_u) / len(cl_u)
    cl_zm = [v - cl_mean for v in cl_u]

    # Apply Hann window.
    w = _hann_window(len(cl_zm))
    cl_windowed = [xi * wi for xi, wi in zip(cl_zm, w)]

    # FFT magnitudes.
    mags = _dft_magnitudes(cl_windowed)
    if len(mags) < 2 or max(mags[1:]) <= 0.0:
        raise CylinderStrouhalError(
            "FFT spectrum is degenerate (flat Cl signal — "
            "cylinder didn't shed?)"
        )
    # Dominant non-DC bin.
    peak_idx = 1 + max(range(len(mags) - 1), key=lambda k: mags[k + 1])
    N = len(cl_u)
    window_s = target_dt * (N - 1)
    f_bin = peak_idx / window_s  # Hz
    St = f_bin * D / abs(U_ref)

    # Secondary observables: cd_mean and cl_rms (trimmed, post-
    # resample for consistency with the FFT window).
    cd_mean = sum(cd_u) / len(cd_u)
    cl_rms = math.sqrt(sum(v * v for v in cl_zm) / len(cl_zm))

    # Confidence check: do we have at least min_periods_post_trim
    # shedding cycles? If window_s · f_bin < min_periods, mark
    # low_confidence but still emit the result (degraded signal is
    # still more honest than the old hardcode).
    n_periods_resolved = window_s * f_bin
    low_conf = n_periods_resolved < min_periods_post_trim

    return StrouhalResult(
        strouhal_number=St,
        dominant_frequency_hz=f_bin,
        cd_mean=cd_mean,
        cl_rms=cl_rms,
        fft_window_s=window_s,
        transient_trim_s=transient_trim_s,
        samples_used=N,
        low_confidence=low_conf,
    )


def emit_strouhal(
    case_dir: Path,
    *,
    D: float,
    U_ref: float,
    transient_trim_s: float = 50.0,
) -> Optional[Dict[str, object]]:
    """End-to-end read+compute. Returns a key_quantities-ready dict, or
    None when postProcessing/forceCoeffs1 is absent (caller's choice
    whether to fall back). Raises CylinderStrouhalError on corruption
    / insufficient-evidence, matching DEC-V61-040 round-2 fail-loud
    pattern.
    """
    fo_root = case_dir / "postProcessing" / "forceCoeffs1"
    latest = _latest_time_dir(fo_root)
    if latest is None:
        return None
    # OF10 emits coefficient.dat; some older versions write
    # forceCoeffs.dat. Accept either.
    candidate_names = ("coefficient.dat", "forceCoeffs.dat")
    path: Optional[Path] = None
    for name in candidate_names:
        p = latest / name
        if p.is_file():
            path = p
            break
    if path is None:
        raise CylinderStrouhalError(
            f"forceCoeffs1 time dir {latest} has no coefficient.dat or "
            f"forceCoeffs.dat — check forceCoeffs FO writeControl."
        )
    t, cd, cl = parse_coefficient_dat(path)
    result = compute_strouhal(
        t, cl, cd,
        U_ref=U_ref,
        D=D,
        transient_trim_s=transient_trim_s,
    )
    return {
        "strouhal_number": result.strouhal_number,
        "cd_mean": result.cd_mean,
        "cl_rms": result.cl_rms,
        "strouhal_source": "forceCoeffs_fft_v1",
        "strouhal_dominant_frequency_hz": result.dominant_frequency_hz,
        "strouhal_fft_window_s": result.fft_window_s,
        "strouhal_transient_trim_s": result.transient_trim_s,
        "strouhal_samples_used": result.samples_used,
        "strouhal_low_confidence": result.low_confidence,
    }
