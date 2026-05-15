#!/usr/bin/env python3
"""Extract Cf at 5 NASA TMR canonical Re_x stations from wallShearStress.

Reads the final-time wallShearStress volVectorField from an OpenFOAM
case, identifies the plate patch boundaryField, and reports:
  - x_face_center, τ_w (kinematic m²/s²), τ_w (dynamic Pa),
    Cf = 2*|τ_w_kin|/U_inf², Δ% vs canonical Prandtl-Schlichting
    eq 21.11 (Cf = 0.0592 × Re_x^(-1/5))

Face centers derived from blockMeshDict grading parameters:
  N_x = 545, L_x = 2.0 m, R_x = 10 (simpleGrading)
  per-cell ratio r = R_x^(1/(N_x-1)) = 10^(1/544) ≈ 1.004245
  δx_first = L_x × (r-1)/(r^N_x - 1)

Usage:
  python3 extract_cf.py <case_path>

Outputs:
  - stdout: 5-station Δ table
  - <case_path>/Cf_results.csv: machine-readable
  - <case_path>/Cf_results.md: human-readable

LLM-offline; runs purely on file IO + numeric stdlib.
"""

import sys
import os
import re
import csv
from pathlib import Path

# --- physical constants & case parameters ---
U_INF = 140.0  # m/s
RHO = 1.225   # kg/m³
NU = 1.4612e-5  # m²/s

# Geometry / mesh
L_X = 2.0  # plate length [m]
N_X = 545
R_X = 10.0

# 5 query stations (Re_x targets and Re_x-based x)
STATIONS = [
    ("S1", 4.0e6, 0.418),
    ("S2", 8.0e6, 0.835),
    ("S3", 1.2e7, 1.253),
    ("S4", 1.6e7, 1.670),
    ("S5", 1.92e7, 2.000),
]


def compute_face_centers_x(L_x=L_X, n_x=N_X, R_x=R_X):
    """Geometric grading face centers in x for a plate block.

    Returns list of n_x face-center x-coordinates.
    """
    r = R_x ** (1.0 / (n_x - 1))
    dx_first = L_x * (r - 1.0) / (r**n_x - 1.0)
    centers = []
    x_face = 0.0  # left face of cell i=0
    for i in range(n_x):
        dx_i = dx_first * (r**i)
        centers.append(x_face + 0.5 * dx_i)
        x_face += dx_i
    # Sanity: last x_face should be ≈ L_x
    assert abs(x_face - L_x) < 1e-6, f"grading total {x_face} != L {L_x}"
    return centers


def find_latest_time(case_path):
    """Return the largest-time time-directory in the case."""
    times = []
    for entry in os.listdir(case_path):
        full = os.path.join(case_path, entry)
        if os.path.isdir(full):
            try:
                t = int(entry)
                times.append((t, entry))
            except ValueError:
                pass
    if not times:
        raise SystemExit(f"No time directories found in {case_path}")
    times.sort()
    return times[-1][1]


def parse_wall_shear_stress(filepath, patch_name="plate"):
    """Parse OpenFOAM wallShearStress volVectorField file and return list of (tau_x, tau_y, tau_z) for plate.

    OF ASCII format for the patch entry looks like:
      plate
      {
          type            calculated;
          value           nonuniform List<vector>
          545
          (
          (tau_x tau_y tau_z)
          (tau_x tau_y tau_z)
          ...
          )
          ;
      }
    """
    with open(filepath, "r") as fh:
        text = fh.read()

    # find the plate boundary block
    patch_pattern = re.compile(
        rf"\b{patch_name}\b\s*\{{[^}}]*?"
        r"value\s+(?:uniform\s+\(([^)]+)\)|nonuniform\s+List<vector>\s*\d+\s*\((.*?)\))"
        r"\s*;",
        re.DOTALL,
    )
    m = patch_pattern.search(text)
    if not m:
        raise SystemExit(f"Could not parse '{patch_name}' boundaryField in {filepath}")

    uniform_part = m.group(1)
    nonuniform_part = m.group(2)
    if uniform_part:
        tau_x, tau_y, tau_z = map(float, uniform_part.split())
        return [(tau_x, tau_y, tau_z)] * N_X
    # nonuniform: parse each (x y z) triple
    triples = re.findall(r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)", nonuniform_part)
    return [(float(a), float(b), float(c)) for (a, b, c) in triples]


def canonical_cf_prandtl_schlichting(Re_x):
    """Cf = 0.0592 × Re_x^(-1/5) (Schlichting Boundary Layer Theory eq 21.11).

    Valid for Re_x ≲ 10⁷; derived from 1/7-power velocity profile +
    integral momentum balance. Known to under-predict Cf at high Re_x
    (the local Cf decay is steeper than reality, esp. above 5e6).
    """
    return 0.0592 * (Re_x ** -0.2)


def canonical_cf_schultz_grunow(Re_x):
    """Cf = (2 log₁₀ Re_x − 0.65)^(−2.3) (Schultz-Grunow log-law fit).

    More accurate at high Re_x (10⁶–10⁹). NASA TMR validation manual
    references this as the preferred high-Re canonical. Derived from
    Coles' log-law u+ = (1/κ) ln y+ + B, with κ=0.41, B=5.0.
    """
    import math
    return (2.0 * math.log10(Re_x) - 0.65) ** -2.3


def main(case_path):
    case_path = Path(case_path)

    # 1. Find latest time
    latest = find_latest_time(case_path)
    wss_path = case_path / latest / "wallShearStress"
    if not wss_path.exists():
        raise SystemExit(
            f"wallShearStress not found at {wss_path}; "
            "ensure 'writeFields true' set on the wallShearStress functionObject "
            "and run completed past first writeInterval."
        )

    # 2. Parse plate face values
    wss = parse_wall_shear_stress(wss_path)
    print(f"Parsed {len(wss)} plate face wallShearStress values from time={latest}")

    # 3. Compute face center x-coords
    x_centers = compute_face_centers_x()
    assert len(x_centers) == len(wss), f"face count mismatch: x={len(x_centers)} wss={len(wss)}"

    # 4. For each station, find nearest face
    rows = []
    print()
    print(f"{'Station':<6} {'Re_x':>12} {'x_tgt[m]':>10} {'x_act[m]':>10} "
          f"{'τw_kin':>11} {'Cf_act':>11} {'Cf_PS':>11} {'Δ%_PS':>8} {'Cf_SG':>11} {'Δ%_SG':>8}")
    print("-" * 115)
    for sid, Re_x_target, x_target in STATIONS:
        # Find nearest face by x distance
        idx = min(range(len(x_centers)), key=lambda i: abs(x_centers[i] - x_target))
        x_act = x_centers[idx]
        tau_x, tau_y, tau_z = wss[idx]
        tau_w_kin_mag = (tau_x**2 + tau_y**2 + tau_z**2) ** 0.5  # m²/s²
        tau_w_dyn = RHO * tau_w_kin_mag                            # Pa
        cf_act = 2.0 * tau_w_kin_mag / (U_INF**2)
        Re_x_act = U_INF * x_act / NU
        cf_ps = canonical_cf_prandtl_schlichting(Re_x_act)
        cf_sg = canonical_cf_schultz_grunow(Re_x_act)
        delta_ps = 100.0 * (cf_act - cf_ps) / cf_ps
        delta_sg = 100.0 * (cf_act - cf_sg) / cf_sg
        rows.append({
            "station": sid,
            "re_x_target": Re_x_target,
            "re_x_actual": Re_x_act,
            "x_target": x_target,
            "x_actual": x_act,
            "tau_w_kinematic": tau_w_kin_mag,
            "tau_w_dynamic_Pa": tau_w_dyn,
            "cf_actual": cf_act,
            "cf_prandtl_schlichting": cf_ps,
            "delta_pct_ps": delta_ps,
            "cf_schultz_grunow": cf_sg,
            "delta_pct_sg": delta_sg,
            "face_index": idx,
        })
        print(f"{sid:<6} {Re_x_target:>12.3e} {x_target:>10.4f} {x_act:>10.4f} "
              f"{tau_w_kin_mag:>11.5f} "
              f"{cf_act:>11.6f} {cf_ps:>11.6f} {delta_ps:>+8.2f} "
              f"{cf_sg:>11.6f} {delta_sg:>+8.2f}")

    # 5. Write CSV + Markdown
    csv_path = case_path / "Cf_results.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {csv_path}")

    md_path = case_path / "Cf_results.md"
    with open(md_path, "w") as fh:
        fh.write(f"# case_021 · Cf extraction at 5 stations · t={latest}\n\n")
        fh.write(f"Source: `{wss_path}`\n\n")
        fh.write(f"U_inf={U_INF} m/s · ν={NU} m²/s · ρ={RHO} kg/m³\n\n")
        fh.write("Canonical references:\n")
        fh.write("- **PS** = Prandtl-Schlichting eq 21.11: Cf = 0.0592 × Re_x^(-1/5) "
                 "(classical 1/7-power; under-predicts at high Re)\n")
        fh.write("- **SG** = Schultz-Grunow log-law: Cf = (2 log₁₀ Re_x − 0.65)^(−2.3) "
                 "(preferred at high Re; NASA TMR validation manual reference)\n\n")
        fh.write("| Station | Re_x | x [m] | τ_w (kin) [m²/s²] | Cf actual | "
                 "Cf PS | Δ% PS | Cf SG | Δ% SG |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['station']} | {r['re_x_actual']:.3e} | {r['x_actual']:.4f} | "
                     f"{r['tau_w_kinematic']:.5f} | {r['cf_actual']:.6f} | "
                     f"{r['cf_prandtl_schlichting']:.6f} | {r['delta_pct_ps']:+.2f} | "
                     f"{r['cf_schultz_grunow']:.6f} | {r['delta_pct_sg']:+.2f} |\n")
    print(f"Wrote {md_path}")

    # 6. Verdict summary (against BOTH canonical references)
    max_abs_ps = max(abs(r["delta_pct_ps"]) for r in rows)
    max_abs_sg = max(abs(r["delta_pct_sg"]) for r in rows)
    print(f"\nMax |Δ%| vs Prandtl-Schlichting: {max_abs_ps:.2f}%")
    print(f"Max |Δ%| vs Schultz-Grunow     : {max_abs_sg:.2f}%")
    if max_abs_ps < 5.0 and max_abs_sg < 5.0:
        print("VERDICT TENTATIVE (Δ check only): FULL (5/5 < 5% on both canonicals)")
    elif max_abs_ps < 10.0 or max_abs_sg < 10.0:
        print("VERDICT TENTATIVE (Δ check only): marginal (5-10% on best canonical)")
    else:
        print("VERDICT TENTATIVE (Δ check only): PARTIAL (≥10% on both canonicals)")
    print("(final verdict requires residual convergence check separately)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: extract_cf.py <case_path>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
