#!/usr/bin/env python3
"""case_024 v2 · Lid-Driven Cavity Re=1000 · stretched 257x257 grid
   Ghia 1982 Table I/II comparison · single-Re v2

Reads OpenFOAM sampleDict output (.xy) from the v2 sandbox
(case_re1000_v2_stretched), interpolates to Ghia 1982 Tables I/II
canonical y/L (or x/L) points, computes Delta% per point.

Q1 LLM-offline: pure stdlib + .venv/bin/python; no external state.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# --- Ghia, Ghia & Shin (1982) JCP 48:387-411 Tables I & II ---
# Re=1000 column extracted directly (B65 retained Re=100 and Re=400 columns;
# this v2 script keeps only Re=1000 for clarity).
# Table I row: (y/L, u_Re1000)
GHIA_RE1000_U = [
    (1.0000,  1.00000),
    (0.9766,  0.65928),
    (0.9688,  0.57492),
    (0.9609,  0.51117),
    (0.9531,  0.46604),
    (0.8516,  0.33304),
    (0.7344,  0.18719),
    (0.6172,  0.05702),
    (0.5000, -0.06080),
    (0.4531, -0.10648),
    (0.2813, -0.27805),
    (0.1719, -0.38289),
    (0.1016, -0.29730),
    (0.0703, -0.22220),
    (0.0625, -0.20196),
    (0.0547, -0.18109),
    (0.0000,  0.00000),
]
# Table II row: (x/L, v_Re1000)
GHIA_RE1000_V = [
    (1.0000,  0.00000),
    (0.9688, -0.21388),
    (0.9609, -0.27669),
    (0.9531, -0.33714),
    (0.9453, -0.39188),
    (0.9063, -0.51550),
    (0.8594, -0.42665),
    (0.8047, -0.31966),
    (0.5000,  0.02526),
    (0.2344,  0.32235),
    (0.2266,  0.33075),
    (0.1563,  0.37095),
    (0.0938,  0.32627),
    (0.0781,  0.30353),
    (0.0703,  0.29012),
    (0.0625,  0.27485),
    (0.0000,  0.00000),
]


def parse_xy(path: Path) -> list[tuple[float, float, float, float]]:
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
    if not rows:
        raise ValueError("empty rows")
    coords = [r[0] for r in rows]
    vals = [r[value_col] for r in rows]
    if target_coord <= coords[0]:
        return vals[0]
    if target_coord >= coords[-1]:
        return vals[-1]
    lo, hi = 0, len(coords) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if coords[mid] <= target_coord:
            lo = mid
        else:
            hi = mid
    t = (target_coord - coords[lo]) / (coords[hi] - coords[lo])
    return vals[lo] + t * (vals[hi] - vals[lo])


def find_latest(case_dir: Path, set_name: str) -> Path:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", required=True, type=Path,
                        help="path to case_re1000_v2_stretched/")
    parser.add_argument("--out", required=True, type=Path,
                        help="output dir for CSV + summary.json")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    u_path = find_latest(args.case_dir, "u_vertical_centerline")
    v_path = find_latest(args.case_dir, "v_horizontal_centerline")

    u_rows = parse_xy(u_path)
    v_rows = parse_xy(v_path)

    # u-centerline at x=0.5: column 1 is Ux
    u_records = []
    for y_L, u_Ghia in GHIA_RE1000_U:
        u_OF = linterp(u_rows, y_L, value_col=1)
        if abs(u_Ghia) < 1e-10:
            d_pct = float("nan")
        else:
            d_pct = (u_OF - u_Ghia) / u_Ghia * 100.0
        u_records.append((y_L, u_OF, u_Ghia, d_pct))

    # v-centerline at y=0.5: column 2 is Uy
    v_records = []
    for x_L, v_Ghia in GHIA_RE1000_V:
        v_OF = linterp(v_rows, x_L, value_col=2)
        if abs(v_Ghia) < 1e-10:
            d_pct = float("nan")
        else:
            d_pct = (v_OF - v_Ghia) / v_Ghia * 100.0
        v_records.append((x_L, v_OF, v_Ghia, d_pct))

    u_d_abs = [(abs(r[3]), r[0]) for r in u_records if not (r[3] != r[3])]
    v_d_abs = [(abs(r[3]), r[0]) for r in v_records if not (r[3] != r[3])]
    max_du, max_du_y = max(u_d_abs)
    max_dv, max_dv_x = max(v_d_abs)

    u_csv = args.out / "centerline_Re1000_u.csv"
    with u_csv.open("w") as f:
        w = csv.writer(f)
        w.writerow(["y_L", "u_OF", "u_Ghia", "delta_pct"])
        for row in u_records:
            w.writerow([f"{row[0]:.4f}", f"{row[1]:.6f}", f"{row[2]:.5f}",
                        "nan" if row[3] != row[3] else f"{row[3]:+.2f}"])

    v_csv = args.out / "centerline_Re1000_v.csv"
    with v_csv.open("w") as f:
        w = csv.writer(f)
        w.writerow(["x_L", "v_OF", "v_Ghia", "delta_pct"])
        for row in v_records:
            w.writerow([f"{row[0]:.4f}", f"{row[1]:.6f}", f"{row[2]:.5f}",
                        "nan" if row[3] != row[3] else f"{row[3]:+.2f}"])

    # Strict 3% gate counts
    u_strict_pass = sum(1 for r in u_records if r[3] == r[3] and abs(r[3]) < 3.0)
    v_strict_pass = sum(1 for r in v_records if r[3] == r[3] and abs(r[3]) < 3.0)
    u_total = sum(1 for r in u_records if r[3] == r[3])
    v_total = sum(1 for r in v_records if r[3] == r[3])

    summary = {
        "Re1000": {
            "max_du_pct": round(max_du, 3),
            "max_du_at_y_L": round(max_du_y, 4),
            "max_dv_pct": round(max_dv, 3),
            "max_dv_at_x_L": round(max_dv_x, 4),
            "u_strict_3pct_pass": f"{u_strict_pass}/{u_total}",
            "v_strict_3pct_pass": f"{v_strict_pass}/{v_total}",
        }
    }
    print(f"Re=1000 v2 stretched: max |delta u|={max_du:+.2f}% @ y/L={max_du_y:.4f} | "
          f"max |delta v|={max_dv:+.2f}% @ x/L={max_dv_x:.4f}")
    print(f"  u strict-3%: {u_strict_pass}/{u_total} | v strict-3%: {v_strict_pass}/{v_total}")

    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote: {args.out}/summary.json + 2 CSVs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
