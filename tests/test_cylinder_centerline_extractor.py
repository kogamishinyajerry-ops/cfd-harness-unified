"""Unit tests for src/cylinder_centerline_extractor.py · DEC-V61-053 Batch B2.

Tests run against mocked postProcessing/cylinderCenterline/<time>/wakeCenterline_U.xy
outputs, covering:
  - happy path: 4 stations × N snapshots → 4 deficit values + metadata
  - window-too-short (< min_samples snapshots after trim) → {} (fail closed)
  - NaN at one station → {} (partial fail closed)
  - missing FO dir → {} (no postProcessing/cylinderCenterline/)
  - outlier clipping (one 1e30 value) doesn't explode the mean
  - transient trim respects window_start_fraction
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.cylinder_centerline_extractor import (
    GOLD_STATIONS_X_OVER_D,
    extract_centerline_u_deficit,
)


# ---------------------------------------------------------------------------
# Fixture helpers — build a synthetic case directory tree with N timestep
# snapshots. Each snapshot has 4 rows (one per gold station) in the format
# the adapter writes via controlDict cylinderCenterline.
# ---------------------------------------------------------------------------


def _write_snapshot(
    case_dir: Path,
    t: float,
    u_values: dict,
    *,
    D: float = 0.1,
    fo_name: str = "cylinderCenterline",
    set_name: str = "wakeCenterline",
) -> None:
    """Write one <time>/wakeCenterline_U.xy file with 4 rows.

    u_values maps x_D → u_x (float). Missing stations are skipped (produces
    a file with < 4 rows, simulating a partial-sample failure).
    """
    t_dir = case_dir / "postProcessing" / fo_name / f"{t:g}"
    t_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    rows.append("# x y z u_x u_y u_z")
    for x_D in GOLD_STATIONS_X_OVER_D:
        if x_D not in u_values:
            continue
        x = x_D * D
        ux = u_values[x_D]
        rows.append(f"{x:.6f}  0.000000  0.000000  {ux:.6f}  0.000000  0.000000")
    (t_dir / f"{set_name}_U.xy").write_text("\n".join(rows) + "\n")


def _build_case_with_snapshots(
    tmp_path: Path,
    snapshots: list,
) -> Path:
    """Write a sequence of snapshots. snapshots = [(t, {x_D: u_x}), ...]."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    for t, u_values in snapshots:
        _write_snapshot(case_dir, t, u_values)
    return case_dir


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_4_stations_average_to_gold(tmp_path: Path) -> None:
    """8 snapshots, each with u_x at all 4 stations matching gold Williamson
    deficit values → extractor returns 4 deficit entries close to gold."""
    # Invert gold deficit to synthetic u_x: u = U_inf * (1 - deficit)
    gold_deficit = {1.0: 0.83, 2.0: 0.64, 3.0: 0.55, 5.0: 0.35}
    snapshots = []
    for t in (100.0, 120.0, 140.0, 160.0, 180.0, 190.0, 195.0, 200.0):
        snapshots.append((t, {x_D: 1.0 * (1 - d) for x_D, d in gold_deficit.items()}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    # All snapshots are "stationary" in this test, so window_start_fraction
    # can be 0 to keep all 8.
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.0)

    for x_D, expected in gold_deficit.items():
        key = f"deficit_x_over_D_{x_D}"
        assert key in result
        assert math.isclose(result[key], expected, rel_tol=1e-3)
    assert result["u_deficit_n_samples_averaged"] == 8.0
    assert result["u_deficit_t_window_start_s"] == 100.0
    assert result["u_deficit_t_window_end_s"] == 200.0


# ---------------------------------------------------------------------------
# Fail-closed paths
# ---------------------------------------------------------------------------


def test_no_postprocessing_dir_returns_empty(tmp_path: Path) -> None:
    """Extractor must fail closed when postProcessing/cylinderCenterline/
    doesn't exist (FO never ran; solver crashed before first write).
    """
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    result = extract_centerline_u_deficit(case_dir)
    assert result == {}


def test_fewer_than_min_samples_returns_empty(tmp_path: Path) -> None:
    """min_samples=4 with window_start_fraction=0.5 → need ≥8 total snapshots.
    Only 4 snapshots total → windowed slice has 2 → fail closed."""
    snapshots = [(t, {1.0: 0.2, 2.0: 0.4, 3.0: 0.5, 5.0: 0.7}) for t in (10.0, 20.0, 30.0, 40.0)]
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    result = extract_centerline_u_deficit(case_dir)
    assert result == {}


def test_all_nan_at_one_station_returns_empty(tmp_path: Path) -> None:
    """If all sample rows for one station are NaN (e.g. sample point lands
    in cylinder body due to coordinate bug), extractor fails closed for the
    whole call — refuses to emit 3/4 deficit values when the 4th is missing.
    """
    snapshots = []
    for t in (100.0, 120.0, 140.0, 160.0, 180.0, 190.0, 195.0, 200.0):
        snapshots.append((t, {1.0: float("nan"), 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.0)
    assert result == {}


# ---------------------------------------------------------------------------
# Robustness paths
# ---------------------------------------------------------------------------


def test_outlier_single_1e30_is_clipped(tmp_path: Path) -> None:
    """A single diverged snapshot with u_x=1e30 at one station should not
    destroy the mean for that station — clipping at 1/99 percentile is the
    defense."""
    # 9 snapshots: 8 physical, 1 outlier at x_D=1.0
    snapshots = []
    # Use deficit 0.83 → u_x = 0.17
    for t in (100.0, 120.0, 140.0, 160.0, 180.0, 190.0, 195.0, 198.0):
        snapshots.append((t, {1.0: 0.17, 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    # Spike at the end
    snapshots.append((200.0, {1.0: 1e30, 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.0)
    assert "deficit_x_over_D_1.0" in result
    # Without clipping the mean would be (8*0.17 + 1e30)/9 ≈ 1e29 → deficit
    # would be -1e29. With clipping, deficit stays close to 0.83.
    assert 0.75 < result["deficit_x_over_D_1.0"] < 0.9


def test_transient_trim_drops_startup(tmp_path: Path) -> None:
    """Early snapshots with startup transient (different u values) should
    be dropped when window_start_fraction=0.5 — i.e. discard first half
    of PHYSICAL time range per Codex round-1 HIGH-1 fix. The reported
    deficit reflects only the stationary window."""
    snapshots = []
    # Transient samples with u=0 at t ∈ [0, 100] (deficit would be 1.0).
    for t in (1.0, 10.0, 20.0, 50.0, 80.0, 99.0):
        snapshots.append((t, {1.0: 0.0, 2.0: 0.0, 3.0: 0.0, 5.0: 0.0}))
    # Stationary samples at t ∈ [120, 200] (deficit 0.83 at x_D=1).
    for t in (120.0, 140.0, 160.0, 180.0, 190.0, 195.0, 200.0):
        snapshots.append((t, {1.0: 0.17, 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    # t_span = 199, window_start_fraction=0.5 → t_trim = 1 + 99.5 = 100.5.
    # Post-trim window: t ≥ 100.5 → 7 stationary samples, ≥ min_samples=4.
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.5)
    # Averaged only over post-t=100.5 samples → deficit 0.83, not 0.915.
    assert math.isclose(result["deficit_x_over_D_1.0"], 0.83, rel_tol=0.01)
    # First post-trim sample is t=120, not any transient time.
    assert result["u_deficit_t_window_start_s"] == 120.0
    assert result["u_deficit_t_window_end_s"] == 200.0


def test_time_based_trim_rejects_tiny_window_even_with_many_samples(tmp_path: Path) -> None:
    """Codex round-1 HIGH-1: 20 samples clustered in a 2-second post-trim
    window is physically inadequate (needs MIN_AVERAGING_WINDOW_SECONDS=10s).
    Assert we fail closed on duration, not let count-based logic pass."""
    snapshots = []
    # 10 startup samples over t ∈ [0, 99]
    for t in (1.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 99.0):
        snapshots.append((t, {1.0: 0.0, 2.0: 0.0, 3.0: 0.0, 5.0: 0.0}))
    # 20 samples packed into t ∈ [101, 103] (post-trim but tiny duration)
    for i in range(20):
        t = 101.0 + 0.1 * i
        snapshots.append((t, {1.0: 0.17, 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    # t_trim = 1 + 0.5*(103-1) = 52 → post-trim = {60,70,80,99, then 20 packed}
    # Actually post-trim includes t=60 etc since they're ≥52. Let me use higher
    # fraction to force the tight-window case.
    result = extract_centerline_u_deficit(
        case_dir, window_start_fraction=0.99,
    )
    # At fraction=0.99: t_trim = 1 + 0.99*102 = 101.98. Post-trim = 11 samples
    # all in t ∈ [102, 103.9], duration ~1.9s < MIN_AVERAGING_WINDOW_SECONDS=10.
    # Must fail closed despite having 11 > min_samples=4.
    assert result == {}


def test_y_or_z_off_centerline_row_rejected(tmp_path: Path) -> None:
    """Codex round-1 MED-3: sample rows with |y| > tol or |z| > tol are
    NOT on the wake centerline; accepting them would bias u_x. Assert the
    extractor filters them out."""
    snapshots = []
    # 8 snapshots, all with y=0.05 (above CENTERLINE_YZ_TOLERANCE_M=0.02).
    # All 4 stations will be rejected → fail closed.
    for t in (100.0, 120.0, 140.0, 160.0, 180.0, 190.0, 195.0, 200.0):
        # Write a synthetic snapshot where all rows have y=0.05.
        t_dir = tmp_path / "case" / "postProcessing" / "cylinderCenterline" / f"{t:g}"
        t_dir.mkdir(parents=True, exist_ok=True)
        D = 0.1
        rows = ["# x y z u_x u_y u_z"]
        for x_D in (1.0, 2.0, 3.0, 5.0):
            x = x_D * D
            rows.append(f"{x:.6f}  0.050000  0.000000  0.170000  0.000000  0.000000")
        (t_dir / "wakeCenterline_U.xy").write_text("\n".join(rows) + "\n")
    case_dir = tmp_path / "case"
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.0)
    # All rows filtered out → no station matches → fail closed.
    assert result == {}


def test_coordinate_match_tolerance_handles_cell_snapping(tmp_path: Path) -> None:
    """cellPoint interpolation snaps sample point to nearest cell center.
    A sampled x=0.102 (instead of target 0.1) for x_D=1.0 station should
    still match within XY_MATCH_TOLERANCE_M (0.02 m).
    """
    snapshots = []
    for t in (100.0, 150.0, 200.0, 250.0, 280.0, 290.0, 295.0, 300.0):
        # Write the canonical file, then overwrite x of x_D=1.0 row to 0.108
        snapshots.append((t, {1.0: 0.17, 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    # Manually bump the first row's x in every snapshot to simulate cell snap.
    for child in (case_dir / "postProcessing" / "cylinderCenterline").iterdir():
        f = child / "wakeCenterline_U.xy"
        text = f.read_text()
        # Replace the 0.100000 x coord on the first data row with 0.108
        text = text.replace("0.100000  0.000000", "0.108000  0.000000", 1)
        f.write_text(text)
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.0)
    assert "deficit_x_over_D_1.0" in result
    assert math.isclose(result["deficit_x_over_D_1.0"], 0.83, rel_tol=0.01)


def test_coordinate_out_of_tolerance_rejects_station(tmp_path: Path) -> None:
    """Sampled x=0.15 for x_D=1.0 station (target 0.1) is outside the
    0.02 m tolerance → station gets 0 matches → fail closed."""
    snapshots = []
    for t in (100.0, 150.0, 200.0, 250.0, 280.0, 290.0, 295.0, 300.0):
        snapshots.append((t, {1.0: 0.17, 2.0: 0.36, 3.0: 0.45, 5.0: 0.65}))
    case_dir = _build_case_with_snapshots(tmp_path, snapshots)
    for child in (case_dir / "postProcessing" / "cylinderCenterline").iterdir():
        f = child / "wakeCenterline_U.xy"
        text = f.read_text()
        text = text.replace("0.100000  0.000000", "0.150000  0.000000", 1)
        f.write_text(text)
    result = extract_centerline_u_deficit(case_dir, window_start_fraction=0.0)
    assert result == {}
