#!/usr/bin/env python3
"""Extract Driver-Seegmiller BFS validation metrics from simpleFoam case.

Computes:
  1. x_R/h: reattachment length via wallShearStress.x sign change on
     bottomDownstream patch (positive in recirculation → negative downstream
     of reattachment).
  2. Cp at 5 stations (x/h = 1, 4, 8, 12, 16): from postProcessing/sampleDict
     output (run via OF postProcess utility, see RUN_LOG).
  3. Cf at 5 stations: from wallShearStress on bottomDownstream patch, nearest-
     face lookup by x.
  4. Δ% vs Driver-Seegmiller 1985 NASA TM 86658 canonical values.

Canonical values (NASA TM 86658 Driver & Seegmiller 1985):
  - x_R/h = 6.26 ± 0.10 (Fig 7)
  - Cp on downstream wall: Fig 8
  - Cf on downstream wall: Fig 9

Sign convention (CRITICAL):
  - OpenFOAM wallShearStress = -ν_eff · dev(twoSymm(grad(U))) · n_wall
  - For forward flow (U_x > 0 near wall): τ_w_OF.x < 0 (wall drags fluid in -x)
  - For reverse flow (U_x < 0 in recirculation): τ_w_OF.x > 0
  - Driver-Seegmiller convention: Cf > 0 for forward flow → Cf = -2·τ_w_OF.x/U_ref²

Geometry (Block 2/3 x-grading):
  nx = 400, L = 0.254 m, R = simpleGrading 5 (cells expand 5× from x=x_step)
  r = 5^(1/399) ≈ 1.00405
  δx_first ≈ 2.560e-4 m at x_step
  δx_last ≈ 1.279e-3 m at x_outlet

Usage:
  python3 extract_bfs.py <case_path>

Outputs:
  - stdout: x_R/h, 5-station Cp/Cf Δ tables
  - <case_path>/BFS_results.csv: machine-readable
  - <case_path>/BFS_results.md: human-readable

LLM-offline; pure stdlib (re, csv, pathlib).
"""

import sys
import os
import re
import csv
from pathlib import Path

# --- physical constants & case parameters ---
U_REF = 44.2      # m/s
RHO = 1.0         # kg/m³ (normalized; pressures are kinematic)
NU = 1.5e-5       # m²/s
H_STEP = 0.0127   # m (step height)
X_STEP = 0.254    # m (step x-location)
H_IN = 0.1016     # m (inlet channel height, 8·h)

# Geometry / mesh for Block 2/3 x-grading
L_X_BLOCK23 = 0.254    # m (x from step to outlet)
N_X_BLOCK23 = 400
R_X_BLOCK23 = 5.0

# 5 query stations · canonical Cp/Cf digitized from Driver-Seegmiller 1985
# NASA TM 86658 Figures 8 & 9 (also tabulated on NASA TMR backstep_val page)
STATIONS = [
    # (id, x/h, x_abs[m], Cp_canonical, Cf_canonical)
    # x/h=1: in primary recirculation just past step, low pressure minimum,
    #        reverse-flow Cf magnitude small
    ("S1",  1.0, X_STEP + 1.0  * H_STEP, -0.140, -0.00110),
    # x/h=4: peak recirculation magnitude · Cp slowly recovering · Cf peak negative
    ("S2",  4.0, X_STEP + 4.0  * H_STEP, -0.110, -0.00193),
    # x/h=8: post-reattachment (DS x_R/h=6.26) · Cp near zero · Cf small positive
    ("S3",  8.0, X_STEP + 8.0  * H_STEP, -0.022, +0.00069),
    # x/h=12: recovery underway · positive Cp · forward flow restored
    ("S4", 12.0, X_STEP + 12.0 * H_STEP, +0.067, +0.00140),
    # x/h=16: pressure recovery continuing toward downstream channel
    ("S5", 16.0, X_STEP + 16.0 * H_STEP, +0.119, +0.00185),
]

# Canonical reattachment length (Driver-Seegmiller Fig 7, NASA TM 86658 p. 18)
XR_OVER_H_CANONICAL = 6.26
XR_TOL_STRICT = 0.04   # ±5% → [6.0, 6.5] for FULL gate
XR_TOL_MARGINAL = 0.12  # ±12% → [5.5, 7.0] for marginal


def compute_face_centers_x_block23(L_x=L_X_BLOCK23, n_x=N_X_BLOCK23, R_x=R_X_BLOCK23,
                                    x_offset=X_STEP):
    """Geometric grading face centers in x for Block 2/3.

    simpleGrading R_x → per-cell ratio r = R_x^(1/(n_x-1)).
    Returns list of n_x face-center x-coordinates (absolute, in [x_offset, x_offset+L_x]).
    """
    r = R_x ** (1.0 / (n_x - 1))
    dx_first = L_x * (r - 1.0) / (r**n_x - 1.0)
    centers = []
    x_face = 0.0
    for i in range(n_x):
        dx_i = dx_first * (r**i)
        centers.append(x_offset + x_face + 0.5 * dx_i)
        x_face += dx_i
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


def parse_wall_shear_stress_patch(filepath, patch_name):
    """Parse OpenFOAM wallShearStress volVectorField file, return list of
    (tau_x, tau_y, tau_z) for the named patch (one tuple per face).

    Tolerates both uniform and nonuniform List<vector> forms.
    """
    with open(filepath, "r") as fh:
        text = fh.read()

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
        return [(tau_x, tau_y, tau_z)]
    triples = re.findall(r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)",
                         nonuniform_part)
    return [(float(a), float(b), float(c)) for (a, b, c) in triples]


def find_reattachment(face_centers, wss_bottomDownstream, persist_n=20):
    """Scan τ_w_OF.x along bottomDownstream patch (sorted by x).

    Identify MAIN reattachment via "last + → - sign change with persistent
    negative downstream". Sub-bubble sign changes (corner vortex, secondary
    counter-rotating vortices near step face) are filtered out by requiring
    the negative side to persist for at least `persist_n` consecutive faces.

    Returns (x_R, x_R/h, x_R_face_index_after_change).
    """
    if len(face_centers) != len(wss_bottomDownstream):
        raise SystemExit(
            f"Face center / WSS face count mismatch: "
            f"{len(face_centers)} vs {len(wss_bottomDownstream)}"
        )
    # Find all +→- sign changes
    candidates = []
    for i in range(1, len(face_centers)):
        tau_prev = wss_bottomDownstream[i - 1][0]
        tau_curr = wss_bottomDownstream[i][0]
        if tau_prev > 0 and tau_curr < 0:
            # Check persistence: all subsequent persist_n faces must be negative
            end = min(i + persist_n, len(face_centers))
            persists = all(
                wss_bottomDownstream[j][0] < 0
                for j in range(i, end)
            )
            if persists:
                candidates.append(i)
    if not candidates:
        # No persistent reattachment in domain
        return None, None, None
    # Take the LAST candidate (main reattachment downstream of sub-bubbles)
    i = candidates[-1]
    tau_prev = wss_bottomDownstream[i - 1][0]
    tau_curr = wss_bottomDownstream[i][0]
    x_prev = face_centers[i - 1]
    x_curr = face_centers[i]
    # Linear-interpolate to find zero crossing
    frac = tau_prev / (tau_prev - tau_curr)
    xR = x_prev + frac * (x_curr - x_prev)
    return xR, (xR - X_STEP) / H_STEP, i


def parse_sample_value(sample_dir, station_name, field_name="p"):
    """Read a sampled scalar `p` value from
    postProcessing/sampleDict/<time>/<station>_<combined>.xy

    OF sampleDict combines all sampled fields into one .xy file
    named like `s1_xh1_p_yPlus_U_wallShearStress.xy` with columns:
      col 0: coordinate (e.g. z)
      col 1: p (scalar)
      col 2: yPlus (scalar)
      col 3-5: U vector (Ux, Uy, Uz)
      col 6-8: wallShearStress vector (τw_x, τw_y, τw_z)

    Returns the scalar p value at the midPoint (first row), or None.
    """
    # Look for any .xy file starting with station_name
    matches = list(sample_dir.glob(f"{station_name}_*.xy"))
    if not matches:
        return None
    target = matches[0]
    with open(target, "r") as fh:
        lines = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    if not lines:
        return None
    parts = lines[0].split()
    if len(parts) < 2:
        return None
    # Column 1 is p (kinematic, m²/s²)
    return float(parts[1])


def main(case_path):
    case_path = Path(case_path)

    # 1. Find latest time
    latest = find_latest_time(case_path)
    print(f"Latest time: {latest}")

    # 2. Parse wallShearStress on bottomDownstream
    wss_path = case_path / latest / "wallShearStress"
    if not wss_path.exists():
        raise SystemExit(
            f"wallShearStress not found at {wss_path}; "
            "ensure 'writeFields true' on the wallShearStress functionObject "
            "and run completed past first writeInterval."
        )
    wss_down = parse_wall_shear_stress_patch(wss_path, "bottomDownstream")
    print(f"Parsed {len(wss_down)} bottomDownstream face wallShearStress values")
    assert len(wss_down) == 400, f"Expected 400 bottomDownstream faces, got {len(wss_down)}"

    # 3. Compute Block 2/3 x face centers
    x_centers = compute_face_centers_x_block23()

    # 4. Reattachment length
    xR, xR_over_h, xR_idx = find_reattachment(x_centers, wss_down)
    if xR is None:
        print("ERROR: No sign change in τ_w_x on bottomDownstream — no reattachment in domain")
        xR_over_h = None
        xR_delta_pct = None
    else:
        xR_delta_pct = 100.0 * (xR_over_h - XR_OVER_H_CANONICAL) / XR_OVER_H_CANONICAL
        print()
        print(f"=== Reattachment ===")
        print(f"x_R                 = {xR:.5f} m")
        print(f"x_R/h               = {xR_over_h:.3f}")
        print(f"Canonical x_R/h     = {XR_OVER_H_CANONICAL:.2f} (DS Fig 7)")
        print(f"Δ%                  = {xR_delta_pct:+.2f}%")
        print(f"FULL gate [6.0, 6.5]: "
              f"{'✓ MET' if 6.0 <= xR_over_h <= 6.5 else '✗ NOT MET'}")
        print(f"Marginal [5.5, 7.0] : "
              f"{'✓ MET' if 5.5 <= xR_over_h <= 7.0 else '✗ NOT MET'}")

    # 5. Cp & Cf at 5 stations via nearest-face on bottomDownstream
    print()
    print("=== Cp & Cf at 5 stations (from bottomDownstream τ_w + sampled p) ===")

    # p_ref from sampleDict: average p over upstream window x ∈ [0.10, 0.20]
    # in Block 1 mid-channel (canonical p_ref convention: upstream of step,
    # outside BL, outside step-front pressure-rise zone)
    sample_dir = case_path / "postProcessing" / "sampleDict" / latest
    p_ref_val = None
    p_ref_line_file = sample_dir / "p_ref_line_p_yPlus_U_wallShearStress.xy"
    if p_ref_line_file.exists():
        ps_in_window = []
        with open(p_ref_line_file, "r") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) < 2:
                    continue
                try:
                    x = float(parts[0])
                    p = float(parts[1])
                except ValueError:
                    continue
                if 0.10 <= x <= 0.20:
                    ps_in_window.append(p)
        if ps_in_window:
            p_ref_val = sum(ps_in_window) / len(ps_in_window)
            print(f"p_ref (kinematic m²/s²) = average over {len(ps_in_window)} "
                  f"cells in x ∈ [0.10, 0.20] at y=0.05: {p_ref_val:.4f}")
    if p_ref_val is None:
        # Fallback: try old p_ref_station naming
        p_ref_val = parse_sample_value(sample_dir, "p_ref_station", "p")
    if p_ref_val is None:
        print("WARNING: p_ref_line sampleDict output not available; "
              "using p_ref=0 (outlet gauge) — Cp values will be RELATIVE to outlet")
        p_ref_val = 0.0

    rows = []
    print()
    header = (f"{'Stn':<4} {'x/h':>5} {'x_abs[m]':>10} {'idx':>5} "
              f"{'τw_x_OF':>11} {'Cf_actual':>10} {'Cf_DS':>10} {'Δ_Cf':>8} "
              f"{'p_kin':>11} {'Cp_act':>9} {'Cp_DS':>9} {'Δ_Cp':>8}")
    print(header)
    print("-" * len(header))
    for sid, xh, x_abs, cp_canon, cf_canon in STATIONS:
        idx = min(range(len(x_centers)), key=lambda i: abs(x_centers[i] - x_abs))
        x_act = x_centers[idx]
        tau_x, tau_y, tau_z = wss_down[idx]
        # Cf with DS sign convention (positive for forward flow)
        cf_signed = -2.0 * tau_x / (U_REF ** 2)
        # Cp from sampleDict p value (if available)
        p_val = None
        if sample_dir.exists():
            station_glob = f"{sid.lower()}_xh{int(xh)}"
            p_val = parse_sample_value(sample_dir, station_glob)
        if p_val is None:
            cp_actual = None
        else:
            cp_actual = (p_val - p_ref_val) / (0.5 * U_REF ** 2)

        cf_delta = (100.0 * (cf_signed - cf_canon) / abs(cf_canon)
                    if abs(cf_canon) > 1e-8 else 0.0)
        cp_delta = (100.0 * (cp_actual - cp_canon) / abs(cp_canon)
                    if cp_actual is not None and abs(cp_canon) > 1e-8 else None)

        rows.append({
            "station": sid,
            "x_over_h": xh,
            "x_abs_m": x_abs,
            "x_actual_m": x_act,
            "face_idx": idx,
            "tau_x_OF_kin": tau_x,
            "cf_actual_signed": cf_signed,
            "cf_canonical_DS": cf_canon,
            "cf_delta_pct": cf_delta,
            "p_kinematic": p_val,
            "cp_actual": cp_actual,
            "cp_canonical_DS": cp_canon,
            "cp_delta_pct": cp_delta,
        })
        p_str = f"{p_val:>11.4f}" if p_val is not None else f"{'N/A':>11}"
        cp_act_str = f"{cp_actual:>+9.4f}" if cp_actual is not None else f"{'N/A':>9}"
        cp_delta_str = f"{cp_delta:>+8.2f}" if cp_delta is not None else f"{'N/A':>8}"
        print(f"{sid:<4} {xh:>5.1f} {x_abs:>10.4f} {idx:>5} "
              f"{tau_x:>+11.6f} {cf_signed:>+10.6f} {cf_canon:>+10.6f} {cf_delta:>+8.1f} "
              f"{p_str} {cp_act_str} {cp_canon:>+9.4f} {cp_delta_str}")

    # 6. Write CSV + Markdown
    csv_path = case_path / "BFS_results.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {csv_path}")

    md_path = case_path / "BFS_results.md"
    with open(md_path, "w") as fh:
        fh.write(f"# case_022 · BFS validation metrics · t={latest}\n\n")
        fh.write(f"Source files:\n")
        fh.write(f"- `{wss_path.relative_to(case_path)}` (wallShearStress on bottomDownstream)\n")
        if sample_dir.exists():
            fh.write(f"- `{sample_dir.relative_to(case_path)}/` (sampleDict outputs)\n")
        fh.write(f"\nReference: NASA TM 86658 Driver & Seegmiller 1985\n\n")
        fh.write(f"U_ref={U_REF} m/s · ν={NU} m²/s · h={H_STEP} m · x_step={X_STEP} m\n\n")

        # Reattachment block
        fh.write("## Reattachment length (DS Fig 7)\n\n")
        if xR_over_h is not None:
            fh.write(f"- x_R         = {xR:.5f} m\n")
            fh.write(f"- **x_R/h     = {xR_over_h:.3f}** (face idx {xR_idx} in bottomDownstream patch)\n")
            fh.write(f"- Canonical   = {XR_OVER_H_CANONICAL:.2f} ± 0.10\n")
            fh.write(f"- **Δ%        = {xR_delta_pct:+.2f}%**\n")
            fh.write(f"- FULL gate [6.0, 6.5]:    "
                     f"{'✓ MET' if 6.0 <= xR_over_h <= 6.5 else '✗ NOT MET'}\n")
            fh.write(f"- Marginal [5.5, 7.0]:     "
                     f"{'✓ MET' if 5.5 <= xR_over_h <= 7.0 else '✗ NOT MET'}\n\n")
        else:
            fh.write("- **No reattachment in domain** — τ_w_x did not change sign\n\n")

        # 5-station table
        fh.write("## Cp & Cf at 5 stations (DS Figs 8 & 9)\n\n")
        fh.write("| Station | x/h | x_abs [m] | face_idx | τ_w_x_OF [m²/s²] | Cf actual | Cf DS | Δ%_Cf | p_kin [m²/s²] | Cp actual | Cp DS | Δ%_Cp |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            cp_act = f"{r['cp_actual']:+.4f}" if r['cp_actual'] is not None else "N/A"
            cp_d = f"{r['cp_delta_pct']:+.2f}" if r['cp_delta_pct'] is not None else "N/A"
            p_v = f"{r['p_kinematic']:.4f}" if r['p_kinematic'] is not None else "N/A"
            fh.write(f"| {r['station']} | {r['x_over_h']:.1f} | {r['x_actual_m']:.4f} | "
                     f"{r['face_idx']} | {r['tau_x_OF_kin']:+.6f} | "
                     f"{r['cf_actual_signed']:+.6f} | {r['cf_canonical_DS']:+.6f} | "
                     f"{r['cf_delta_pct']:+.2f} | "
                     f"{p_v} | {cp_act} | {r['cp_canonical_DS']:+.4f} | {cp_d} |\n")
        fh.write("\n")
        fh.write("Sign convention: τ_w_x_OF is OpenFOAM's `wallShearStress.x` (kinematic).\n")
        fh.write("Cf_actual = -2·τ_w_x_OF/U_ref² (DS convention: positive for forward flow).\n")
        fh.write("Cp_actual = (p_kin - p_kin_ref) / (0.5·U_ref²) (kinematic).\n")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: extract_bfs.py <case_path>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
