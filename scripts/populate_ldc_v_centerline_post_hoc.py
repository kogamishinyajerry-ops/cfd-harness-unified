"""DEC-V61-050 batch 1 — one-time post-hoc v_centerline fixture populator.

Background: the existing LDC audit fixture at
    reports/phase5_fields/lid_driven_cavity/20260421T082340Z/
was produced by an older generator that only wrote an uCenterline sample
line in controlDict. v_centerline data therefore does not exist in the
fixture's postProcessing/sets/<time>/ directories.

Rather than re-running simpleFoam (expensive; would change the fixture
timestamp and break upstream pinning of commit-sha-to-fixture), this
script interpolates the v field from the already-written VTK volume
data at iter 1024 onto the two sample lines the updated generator
would have emitted:

    vCenterline_U.xy:      129-point uniform lineUniform along y=0.05
                           (for the dense profile render + convergence)
    vCenterlineGold_U.xy:  17-point gold-anchored at Ghia's native
                           non-uniform x coordinates (for the
                           point-by-point comparator)

Both files are written under postProcessing/sets/1024/ in the same
OpenFOAM raw xy format the native sample function object would write
(header lines with # prefix, then "x U_x U_y U_z" rows; the comparator
code at ui/backend/services/comparison_report.py:_load_sample_xy reads
cols [0, 1] so our files must put the sampling-axis coordinate in col 0
and the field value of interest (v = U_y) in col 1).

Idempotent: running twice just overwrites the same files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "reports/phase5_fields/lid_driven_cavity/20260421T082340Z"

# Physical mesh: convertToMeters 0.1 → domain 0.1m × 0.1m × 0.01m.
# y=0.5·L in normalized units → physical y = 0.05m.
L_PHYS = 0.1
Y_CENTERLINE_PHYS = 0.05
Z_MID_PHYS = 0.005

# Ghia 1982 Table II Re=100 native non-uniform x coordinates (normalized, [0,1])
# Cross-verified: scripts/flow-field-gen/generate_contours.py:103-110
GHIA_X_NATIVE = np.array([
    0.0, 0.0625, 0.0703, 0.0781, 0.0938, 0.1563, 0.2266, 0.2344,
    0.5, 0.8047, 0.8594, 0.9063, 0.9453, 0.9531, 0.9609, 0.9688, 1.0,
])

# Dense uniform sampling for render / convergence evidence.
N_UNIFORM = 129


def _write_xy(path: Path, x_norm: np.ndarray, U: np.ndarray, header_note: str) -> None:
    """Write an OpenFOAM-style raw sample xy file.

    Col 0: sampling-axis coordinate (physical meters, matches what the
           native sample function object would write — the comparator
           normalizes by dividing by max(x) so normalized vs physical
           xy inputs both work, but physical is more conservative).
    Cols 1-3: U_x, U_y, U_z.
    """
    x_phys = x_norm * L_PHYS
    lines = [
        "# post-hoc fixture populator · DEC-V61-050 batch 1",
        f"# {header_note}",
        "# columns: x U_x U_y U_z",
    ]
    for xp, u in zip(x_phys, U):
        lines.append(f"{xp:.12g} {u[0]:.12g} {u[1]:.12g} {u[2]:.12g}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[populate] wrote {path.relative_to(REPO_ROOT)} · {len(x_norm)} pts")


def main() -> int:
    vtk_candidates = list((FIXTURE_DIR / "VTK").glob("*.vtk"))
    vtk_candidates = [p for p in vtk_candidates if "allPatches" not in p.parent.name]
    if not vtk_candidates:
        print("[populate] FATAL: no VTK volume file under fixture")
        return 1
    vtk_path = sorted(vtk_candidates, key=lambda p: int(p.stem.rsplit("_", 1)[1]))[-1]
    print(f"[populate] reading {vtk_path.relative_to(REPO_ROOT)}")

    grid = pv.read(str(vtk_path))

    def _sample_at(x_norm: np.ndarray) -> np.ndarray:
        points = np.column_stack([
            x_norm * L_PHYS,
            np.full_like(x_norm, Y_CENTERLINE_PHYS),
            np.full_like(x_norm, Z_MID_PHYS),
        ])
        probe = pv.PolyData(points).sample(grid)
        return np.asarray(probe["U"])

    # 1. Dense uniform 129-point line (for render + convergence evidence).
    x_uniform = np.linspace(0.0, 1.0, N_UNIFORM)
    U_uniform = _sample_at(x_uniform)
    # Write to legacy `sample/<iter>/<setname>.xy` path (matches where
    # the existing comparator reads uCenterline from for this fixture)
    # AND the modern `postProcessing/sets/<iter>/<setname>_U.xy` path
    # (matches where newer runs produced by the updated generator would
    # write). Keeps both readers happy.
    _write_xy(
        FIXTURE_DIR / "sample/1000/vCenterline.xy",
        x_uniform, U_uniform,
        f"lineUniform on y=0.05, {N_UNIFORM} points, interpolated from VTK iter 1024 "
        f"(placed at sample/1000/ to match the legacy uCenterline sibling).",
    )
    _write_xy(
        FIXTURE_DIR / "postProcessing/sets/1024/vCenterline_U.xy",
        x_uniform, U_uniform,
        f"lineUniform on y=0.05, {N_UNIFORM} points, interpolated from VTK iter 1024",
    )

    # 2. Gold-anchored 17-point set at Ghia's native x coords.
    U_gold = _sample_at(GHIA_X_NATIVE)
    _write_xy(
        FIXTURE_DIR / "postProcessing/sets/1024/vCenterlineGold_U.xy",
        GHIA_X_NATIVE, U_gold,
        "Ghia 1982 Table II Re=100 native 17-point non-uniform x grid",
    )

    # 3. Print a quick sanity summary of gold vs measured v.
    from textwrap import indent
    GHIA_V = np.array([
        0.0, 0.09233, 0.10091, 0.10890, 0.12317, 0.16077, 0.17507, 0.17527,
        0.05454, -0.24533, -0.22445, -0.16914, -0.10313, -0.08864, -0.07391, -0.05906, 0.0,
    ])
    measured_v = U_gold[:, 1]  # U_y
    denom = np.where(np.abs(GHIA_V) < 1e-3, 1e-3, np.abs(GHIA_V))
    dev_pct = 100.0 * np.abs(measured_v - GHIA_V) / denom
    n_pass = int((dev_pct < 5.0).sum())
    print("\n[populate] v_centerline sanity at Ghia native x:")
    print(indent(
        "\n".join(
            f"x/L={x:.4f}  gold_v={g:+.5f}  measured_v={m:+.5f}  |dev|%={d:.2f}"
            for x, g, m, d in zip(GHIA_X_NATIVE, GHIA_V, measured_v, dev_pct)
        ),
        "  ",
    ))
    print(f"\n[populate] {n_pass}/{len(GHIA_V)} gold points within ±5% tolerance")
    print(f"[populate] max |dev| = {dev_pct.max():.2f}%  · L2 = {np.sqrt(np.mean((measured_v - GHIA_V)**2)):.5f}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
