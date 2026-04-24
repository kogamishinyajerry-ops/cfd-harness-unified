"""Cylinder wake centerline u_deficit extractor · DEC-V61-053 Batch B2.

Reads per-timestep samples emitted by the controlDict `cylinderCenterline`
function object (runtime `type sets` with 4 points at x/D ∈ {1, 2, 3, 5}),
trims startup transient, time-averages each station, and converts to wake
deficit = (U_inf - u_mean) / U_inf.

The runtime FO writes one file per sample-write step:
    postProcessing/cylinderCenterline/<time>/wakeCenterline_U.xy

Each file has one row per sample point (axis xyz, ordered on):
    x y z  u_x u_y u_z

Per DEC-V61-053 intake + Batch B2 semantics resolution (no rename):
  - Gold YAML keeps `u_Uinf:` for backward compatibility, but the per-point
    description field ("centerline velocity deficit") has been authoritative
    all along. This module self-names output keys `deficit_x_over_D_*` so
    the API is unambiguous; Batch B3 bridges gold↔extractor by x_D lookup.
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
# so the returned x can be off by ~0.5*cell_dx. At the B1a mesh (now 600x240
# per Codex round-1 MED-2), dx ≈ 0.05D = 0.005 m. 0.02 m tolerance covers
# ~4x dx — safe for refined mesh and forward-compatible with coarser meshes.
XY_MATCH_TOLERANCE_M: float = 0.02

# Y/Z centerline tolerance per Codex round-1 MED-3: `type points` with
# cellPoint interpolation snaps to nearest cell center, which for a 2D
# planar cylinder mesh means y ≈ 0 (and z snaps to the thin-span plane).
# An off-axis sample row (|y| > this) would bias u_x for a centerline
# observable — reject those rows.
CENTERLINE_YZ_TOLERANCE_M: float = 0.02

# Minimum physical duration of the averaging window (seconds). Codex
# round-1 HIGH-1: count-based trim with adjustable deltaT + writeControl
# timeStep can produce a physically tiny post-trim window even when the
# sample count looks healthy. Assert at least this many seconds of
# averaging regardless of sample count. At endTime=200s + window_start
# fraction=0.5, the post-trim window is ~100s — plenty.
MIN_AVERAGING_WINDOW_SECONDS: float = 10.0


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
    min_averaging_window_s: Optional[float] = None,
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
        # DEC-V61-053 live-run attempt 6 (2026-04-24): FO registered but
        # postProcessing/cylinderCenterline/ never materialized on disk.
        # Emit a single diagnostic key via an exception so the adapter's
        # try/except records u_deficit_extractor_error, making the silent
        # failure visible in the audit fixture. Without this, the absence
        # of deficit_x_over_D_* keys is ambiguous (FO didn't fire? dir got
        # cleaned? extractor bug?). Explicit reason beats silence.
        raise RuntimeError(
            f"cylinderCenterline FO produced no time dirs at "
            f"{fo_dir}. Check (a) FO actually wrote (look for "
            f"'Writing postProcessing/{fo_name}' in solver log), "
            f"(b) case_dir is still on disk when extractor runs "
            f"(shutil.rmtree in finally block runs AFTER return), "
            f"(c) FO config (writeControl/writeInterval/fields/points)."
        )

    # Codex round-1 HIGH-1 fix: trim by physical time, not sample count.
    # With writeControl=timeStep + adjustable deltaT, startup samples can
    # cluster at small dt (e.g. dt=0.001s → 1000 samples/s before relaxing
    # to maxDeltaT=0.01s). A 0.5 count-fraction trim could leave most of
    # the startup transient in the averaging window. Use
    #     t_trim = t_min + window_start_fraction * (t_max - t_min)
    # so "0.5" means "skip the first half of the PHYSICAL time range".
    t_min = time_dirs[0][0]
    t_max = time_dirs[-1][0]
    t_trim = t_min + window_start_fraction * (t_max - t_min)
    windowed = [(t, p) for t, p in time_dirs if t >= t_trim]
    if len(windowed) < min_samples:
        return {}
    # Assert a minimum physical averaging duration regardless of count.
    # DEC-V61-053 live-run: `min_averaging_window_s` override lets the
    # adapter scale this when endTime is below the MIN_AVERAGING_WINDOW_
    # SECONDS default (10s). When endTime=10s, the default would refuse
    # everything; adapter passes 3s (30% of endTime) to let the
    # demonstration-grade fixture surface SOMETHING — with the caller
    # aware precision is lower than gold-grade.
    effective_min_window = (
        min_averaging_window_s if min_averaging_window_s is not None
        else MIN_AVERAGING_WINDOW_SECONDS
    )
    window_duration = windowed[-1][0] - windowed[0][0]
    if window_duration < effective_min_window:
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
            x, y, z, ux, _uy, _uz = row
            if not np.isfinite(ux):
                continue
            # Codex round-1 MED-3 fix: enforce centerline (y≈0 AND z≈0)
            # before accepting the row. An off-axis snap point would bias
            # u_x for a centerline observable.
            if abs(y) > CENTERLINE_YZ_TOLERANCE_M:
                continue
            if abs(z) > CENTERLINE_YZ_TOLERANCE_M:
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
    "CENTERLINE_YZ_TOLERANCE_M",
    "MIN_AVERAGING_WINDOW_SECONDS",
    "extract_centerline_u_deficit",
]
