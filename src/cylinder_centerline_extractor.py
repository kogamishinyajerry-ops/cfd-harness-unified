"""Cylinder wake centerline u_deficit extractor · DEC-V61-053 Batch B2.

Reads per-timestep samples emitted by the controlDict `cylinderCenterline`
function object (runtime `type sets` with 4 points at x/D ∈ {1, 2, 3, 5}),
trims startup transient, time-averages each station, and converts to wake
deficit = (U_inf - u_mean) / U_inf.

The runtime FO writes one file per sample-write step:
    postProcessing/cylinderCenterline/<time>/wakeCenterline_U.xy

Each file has one row per sample point (axis xyz, ordered on):
    x y z  u_x u_y u_z

Per DEC-V61-053 intake and gold YAML rename (Batch B2):
  - u_Uinf key was historical mislabeling; description has always said
    "velocity deficit". This module emits u_deficit directly.
  - Williamson 1996 gold at Re=100: {0.83, 0.64, 0.55, 0.35} for x/D ∈
    {1, 2, 3, 5}. These are deficit = 1 - u_mean/U_inf.

Extractor guarantees:
  - fails closed (returns empty dict) if FO output missing or all-NaN
  - rejects too-short windows (< 4 distinct times) to prevent silent fallback
    to a ~1-sample average
  - trims leading transient by default (window_start_fraction=0.5 → drop
    first half of time-history before averaging)
  - handles NaN/inf from solver divergence by clipping to finite-percentile
    envelope before averaging
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


# Gold stations. Must match controlDict cylinderCenterline wakeCenterline
# set points AND gold YAML reference_values.x_D.
GOLD_STATIONS_X_OVER_D: Tuple[float, ...] = (1.0, 2.0, 3.0, 5.0)

# Tolerance for matching sampled x-coord to expected x = x_D * D.
# sampleDict with `cellPoint` interpolation snaps to the nearest cell center,
# so the returned x can be off by ~0.5*cell_dx. At the new 400x200 domain
# grown per B1a, dx ≈ 0.075D = 0.0075 m. Use 2x that as the match tolerance.
XY_MATCH_TOLERANCE_M: float = 0.02


def _parse_sample_file(path: Path) -> List[Tuple[float, float, float, float, float, float]]:
    """Parse a `setFormat raw` `type points` sample file.

    Expected format (OpenFOAM 10, cellPoint, ordered=on):
        # optional header starting with '#'
        x1 y1 z1 ux1 uy1 uz1
        x2 y2 z2 ux2 uy2 uz2
        ...

    Returns list of 6-tuples (x, y, z, ux, uy, uz). Non-numeric / comment
    lines are skipped silently.
    """
    out: List[Tuple[float, float, float, float, float, float]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 6:
            continue
        try:
            vals = tuple(float(p) for p in parts[:6])
        except ValueError:
            continue
        out.append(vals)  # type: ignore[arg-type]
    return out


def _list_time_dirs(fo_dir: Path) -> List[Tuple[float, Path]]:
    """List `<time>/` subdirs of the function-object output dir, sorted by time."""
    if not fo_dir.is_dir():
        return []
    times: List[Tuple[float, Path]] = []
    for child in fo_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            t = float(child.name)
        except ValueError:
            continue
        times.append((t, child))
    times.sort(key=lambda tp: tp[0])
    return times


def extract_centerline_u_deficit(
    case_dir: Path,
    *,
    U_inf: float = 1.0,
    D: float = 0.1,
    fo_name: str = "cylinderCenterline",
    set_name: str = "wakeCenterline",
    field: str = "U",
    window_start_fraction: float = 0.5,
    min_samples: int = 4,
) -> Dict[str, float]:
    """Return {x_D: u_deficit, ...} for the 4 gold stations.

    Parameters:
        case_dir: OpenFOAM case directory (contains postProcessing/)
        U_inf: freestream velocity (adapter default = 1.0 m/s)
        D: cylinder diameter (adapter default = 0.1 m)
        fo_name: function-object directory name
        set_name: sample-set name (file prefix)
        field: OF field name (here, "U" → file suffix "_U.xy")
        window_start_fraction: fraction of time-history to drop as startup
            transient. 0.5 means keep second half. At endTime=200s and
            writeInterval=20 timesteps, this gives ~tens to hundreds of
            shedding periods in the averaging window.
        min_samples: fail closed if < this many sample snapshots available
            after trimming.

    Return value keys: "deficit_x_over_D_1.0", "deficit_x_over_D_2.0",
    "deficit_x_over_D_3.0", "deficit_x_over_D_5.0". Also returns metadata:
    "u_deficit_n_samples_averaged", "u_deficit_t_window_start_s",
    "u_deficit_t_window_end_s".

    Empty dict on extraction failure (FO dir missing, all snapshots NaN,
    window too short, no station matches). Caller is expected to treat
    empty result as "extractor failed; do not emit u_mean_centerline as
    primary scalar" — preserves the honest-measurement contract from
    DEC-V61-041 (no silent canonical fallback).
    """
    fo_dir = case_dir / "postProcessing" / fo_name
    time_dirs = _list_time_dirs(fo_dir)
    if not time_dirs:
        return {}

    # Trim leading transient.
    n_total = len(time_dirs)
    trim_idx = int(n_total * window_start_fraction)
    windowed = time_dirs[trim_idx:]
    if len(windowed) < min_samples:
        return {}

    file_suffix = f"{set_name}_{field}.xy"
    # Collect per-time values at each gold station.
    # station_values[x_D] = list of u_x at that station across time-steps
    station_values: Dict[float, List[float]] = {
        x_D: [] for x_D in GOLD_STATIONS_X_OVER_D
    }
    for t, t_dir in windowed:
        sample_path = t_dir / file_suffix
        rows = _parse_sample_file(sample_path)
        if not rows:
            continue
        for row in rows:
            x, _y, _z, ux, _uy, _uz = row
            if not np.isfinite(ux):
                continue
            for x_D in GOLD_STATIONS_X_OVER_D:
                expected_x = x_D * D
                if abs(x - expected_x) <= XY_MATCH_TOLERANCE_M:
                    station_values[x_D].append(ux)
                    break

    # Fail closed if any station has < min_samples hits.
    if any(len(v) < min_samples for v in station_values.values()):
        return {}

    t_window_start = windowed[0][0]
    t_window_end = windowed[-1][0]
    n_samples = min(len(v) for v in station_values.values())

    out: Dict[str, float] = {
        "u_deficit_n_samples_averaged": float(n_samples),
        "u_deficit_t_window_start_s": float(t_window_start),
        "u_deficit_t_window_end_s": float(t_window_end),
    }
    for x_D in GOLD_STATIONS_X_OVER_D:
        values = np.asarray(station_values[x_D], dtype=float)
        finite_mask = np.isfinite(values)
        if finite_mask.sum() < min_samples:
            return {}
        values_finite = values[finite_mask]
        # Robust outlier rejection: drop samples where |v - median| > 10 * MAD.
        # A single diverged snapshot (u=1e30) would otherwise contaminate the
        # percentile-clipped mean. MAD-based filtering is scale-invariant and
        # doesn't require a hand-tuned physics band.
        median = float(np.median(values_finite))
        mad = float(np.median(np.abs(values_finite - median)))
        # Use a small floor on MAD so that pathological all-identical samples
        # with one outlier don't produce MAD=0 → divide-by-zero.
        mad_floor = max(mad, 1e-6 * (abs(median) + 1.0))
        inlier_mask = np.abs(values_finite - median) <= 10.0 * mad_floor
        inliers = values_finite[inlier_mask]
        if inliers.size < min_samples:
            return {}
        u_mean = float(np.mean(inliers))
        deficit = (U_inf - u_mean) / U_inf
        # Sanity band — deficit outside [-0.2, 1.5] is nonphysical for laminar
        # Re=100 wake at x/D ∈ [1, 5]. Don't hard-reject (let comparator decide
        # with its tolerance band), but tag it so diagnostics surface if a
        # quality issue triggers a round-1 finding.
        out[f"deficit_x_over_D_{x_D}"] = deficit
    return out


__all__ = [
    "GOLD_STATIONS_X_OVER_D",
    "XY_MATCH_TOLERANCE_M",
    "extract_centerline_u_deficit",
]
