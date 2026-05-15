#!/usr/bin/env python3
"""case_024 · Lid-Driven Cavity · Ghia 1982 comparison

Reads OpenFOAM sampleDict output (.xy) from 3 sandbox case dirs
(case_re100, case_re400, case_re1000), interpolates to Ghia 1982 Tables I/II
canonical y/L (or x/L) points, computes Δ% per point, and emits:
  - centerline_Re{Re}_u.csv     : 17-row Ghia y vs u_OF vs u_Ghia vs Δ%
  - centerline_Re{Re}_v.csv     : 17-row Ghia x vs v_OF vs v_Ghia vs Δ%
  - summary.json                : per-Re max|Δu|%, max|Δv|%, max-point identifiers

Q1 LLM-offline: pure stdlib + .venv/bin/python; no external state.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# --- Ghia, Ghia & Shin (1982) JCP 48:387-411 Tables I & II ---
# Table I: u-velocity at vertical centerline x=0.5
# rows: (y/L, u_Re=100, u_Re=400, u_Re=1000)
GHIA_TABLE_I = [
    (1.0000,  1.00000,  1.00000,  1.00000),
    (0.9766,  0.84123,  0.75837,  0.65928),
    (0.9688,  0.78871,  0.68439,  0.57492),
    (0.9609,  0.73722,  0.61756,  0.51117),
    (0.9531,  0.68717,  0.55892,  0.46604),
    (0.8516,  0.23151,  0.29093,  0.33304),
    (0.7344,  0.00332,  0.16256,  0.18719),
    (0.6172, -0.13641,  0.02135,  0.05702),
    (0.5000, -0.20581, -0.11477, -0.06080),
    (0.4531, -0.21090, -0.17119, -0.10648),
    (0.2813, -0.15662, -0.32726, -0.27805),
    (0.1719, -0.10150, -0.24299, -0.38289),
    (0.1016, -0.06434, -0.14612, -0.29730),
    (0.0703, -0.04775, -0.10338, -0.22220),
    (0.0625, -0.04192, -0.09266, -0.20196),
    (0.0547, -0.03717, -0.08186, -0.18109),
    (0.0000,  0.00000,  0.00000,  0.00000),
]

# Table II: v-velocity at horizontal centerline y=0.5
# rows: (x/L, v_Re=100, v_Re=400, v_Re=1000)
GHIA_TABLE_II = [
    (1.0000,  0.00000,  0.00000,  0.00000),
    (0.9688, -0.05906, -0.12146, -0.21388),
    (0.9609, -0.07391, -0.15663, -0.27669),
    (0.9531, -0.08864, -0.19254, -0.33714),
    (0.9453, -0.10313, -0.22847, -0.39188),
    (0.9063, -0.16914, -0.23827, -0.51550),
    (0.8594, -0.22445, -0.44993, -0.42665),
    (0.8047, -0.24533, -0.38598, -0.31966),
    (0.5000,  0.05454,  0.05186,  0.02526),
    (0.2344,  0.17527,  0.30174,  0.32235),
    (0.2266,  0.17507,  0.30203,  0.33075),
    (0.1563,  0.16077,  0.28124,  0.37095),
    (0.0938,  0.12317,  0.22965,  0.32627),
    (0.0781,  0.10890,  0.20920,  0.30353),
    (0.0703,  0.10091,  0.19713,  0.29012),
    (0.0625,  0.09233,  0.18360,  0.27485),
    (0.0000,  0.00000,  0.00000,  0.00000),
]


def parse_xy(path: Path) -> list[tuple[float, float, float, float]]:
    """Parse OpenFOAM sampleDict .xy output: '<coord> <Ux> <Uy> <Uz>\\n'."""
    rows: list[tuple[float, float, float, float]] = []
    with path.open() as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 4:
                continue
            try:
                rows.append(tuple(float(p) for p in parts))  # type: ignore[arg-type]
            except ValueError:
                continue
    return rows


def linterp(rows: list[tuple[float, float, float, float]], target_coord: float, value_col: int) -> float:
    """Linear interpolation: find target_coord in column 0, return interpolated value_col.

    rows is sorted ascending by column 0.
    """
    if not rows:
        raise ValueError("empty rows")
    coords = [r[0] for r in rows]
    vals = [r[value_col] for r in rows]
    if target_coord <= coords[0]:
        return vals[0]
    if target_coord >= coords[-1]:
        return vals[-1]
    # binary search
    lo, hi = 0, len(coords) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if coords[mid] <= target_coord:
            lo = mid
        else:
            hi = mid
    # lerp between coords[lo] and coords[hi]
    t = (target_coord - coords[lo]) / (coords[hi] - coords[lo])
    return vals[lo] + t * (vals[hi] - vals[lo])


def find_latest(case_dir: Path, set_name: str) -> Path:
    """Find postProcessing/sampleDict/<latestTime>/<set_name>_U.xy."""
    sd = case_dir / "postProcessing" / "sampleDict"
    times = sorted(
        (d for d in sd.iterdir() if d.is_dir() and d.name.replace(".", "").replace("-", "").isdigit()),
        key=lambda d: float(d.name),
    )
    if not times:
        raise FileNotFoundError(f"no time dirs in {sd}")
    latest = times[-1]
    target = latest / f"{set_name}_U.xy"
    if not target.exists():
        raise FileNotFoundError(f"missing {target}")
    return target


def compute_centerline_delta(case_dir: Path, re: int, ghia_col: int):
    """Compute u-centerline and v-centerline Δ vs Ghia for one Re case.

    Returns:
        (u_records, v_records, max_du_pct, max_dv_pct, max_du_y, max_dv_x)
    """
    u_path = find_latest(case_dir, "u_vertical_centerline")
    v_path = find_latest(case_dir, "v_horizontal_centerline")

    u_rows = parse_xy(u_path)   # cols: y, Ux, Uy, Uz
    v_rows = parse_xy(v_path)   # cols: x, Ux, Uy, Uz

    # u-centerline: at x=0.5, sample u (Ux) vs y. Column 1 is Ux.
    u_records = []
    for y_L, *_ in GHIA_TABLE_I:
        u_OF = linterp(u_rows, y_L, value_col=1)  # Ux is column index 1
        u_Ghia = GHIA_TABLE_I[[r[0] for r in GHIA_TABLE_I].index(y_L)][ghia_col]
        if abs(u_Ghia) < 1e-10:
            d_pct = float("nan")  # avoid div by zero at endpoints
        else:
            d_pct = (u_OF - u_Ghia) / u_Ghia * 100.0
        u_records.append((y_L, u_OF, u_Ghia, d_pct))

    # v-centerline: at y=0.5, sample v (Uy) vs x. Column 2 is Uy.
    v_records = []
    for x_L, *_ in GHIA_TABLE_II:
        v_OF = linterp(v_rows, x_L, value_col=2)  # Uy is column index 2
        v_Ghia = GHIA_TABLE_II[[r[0] for r in GHIA_TABLE_II].index(x_L)][ghia_col]
        if abs(v_Ghia) < 1e-10:
            d_pct = float("nan")
        else:
            d_pct = (v_OF - v_Ghia) / v_Ghia * 100.0
        v_records.append((x_L, v_OF, v_Ghia, d_pct))

    # Max |Δ%| (skipping endpoint nans where Ghia ref is 0)
    u_d_abs = [(abs(r[3]), r[0]) for r in u_records if not (r[3] != r[3])]  # nan-check
    v_d_abs = [(abs(r[3]), r[0]) for r in v_records if not (r[3] != r[3])]
    max_du, max_du_y = max(u_d_abs)
    max_dv, max_dv_x = max(v_d_abs)

    return u_records, v_records, max_du, max_dv, max_du_y, max_dv_x


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", required=True, type=Path,
                        help="path to ~/Desktop/case_024_lid_driven_cavity/")
    parser.add_argument("--out", required=True, type=Path,
                        help="output dir for CSV + summary.json")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    summary = {}

    re_to_ghia_col = {100: 1, 400: 2, 1000: 3}
    for re, ghia_col in re_to_ghia_col.items():
        case_dir = args.sandbox / f"case_re{re}"
        if not case_dir.exists():
            print(f"WARN: {case_dir} missing", file=sys.stderr)
            continue

        u_records, v_records, max_du, max_dv, max_du_y, max_dv_x = (
            compute_centerline_delta(case_dir, re, ghia_col)
        )

        # write u CSV
        u_csv = args.out / f"centerline_Re{re}_u.csv"
        with u_csv.open("w") as f:
            w = csv.writer(f)
            w.writerow(["y_L", "u_OF", "u_Ghia", "delta_pct"])
            for row in u_records:
                w.writerow([f"{row[0]:.4f}", f"{row[1]:.6f}", f"{row[2]:.5f}",
                            "nan" if row[3] != row[3] else f"{row[3]:+.2f}"])

        # write v CSV
        v_csv = args.out / f"centerline_Re{re}_v.csv"
        with v_csv.open("w") as f:
            w = csv.writer(f)
            w.writerow(["x_L", "v_OF", "v_Ghia", "delta_pct"])
            for row in v_records:
                w.writerow([f"{row[0]:.4f}", f"{row[1]:.6f}", f"{row[2]:.5f}",
                            "nan" if row[3] != row[3] else f"{row[3]:+.2f}"])

        summary[f"Re{re}"] = {
            "max_du_pct": round(max_du, 3),
            "max_du_at_y_L": round(max_du_y, 4),
            "max_dv_pct": round(max_dv, 3),
            "max_dv_at_x_L": round(max_dv_x, 4),
        }
        print(f"Re={re}: max |Δu|={max_du:+.2f}% @ y/L={max_du_y:.4f} · "
              f"max |Δv|={max_dv:+.2f}% @ x/L={max_dv_x:.4f}")

    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote: {args.out}/summary.json + 6 CSVs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
