#!/usr/bin/env python3
"""
case_027 · Hagen-Poiseuille pipe validation extraction
======================================================

Reads OpenFOAM 5000/{C, U, p, wallShearStress} directly and compares cell-
centered values to analytical Hagen-Poiseuille (Schlichting §5.1.2).

Why direct field-parsing instead of postProcess sampleSet:
- OpenFOAM v2312 uniformSet/midPointSet uses particle tracking that sigFpe's
  on wedge degenerate axis faces (No base point for tet decomposition).
- cloud sampleSet works but cell-finder maps multiple sample points to the
  axis cell (geometric confusion near wedge axis).
- Direct field parsing reads cell-centered values for the actual mesh cells,
  bypassing both issues. F-NEW-B candidate.

Pure stdlib (no numpy / no pandas) for Q1 LLM-offline gate compliance.

Run:
    env -i HOME=$HOME PATH=/usr/bin:/bin python3 extract_hagen_poiseuille.py

Outputs:
    results/exit_profile_delta.csv    (40 cell-centered r-points · Δ vs analytical)
    results/mid_profile_delta.csv     (parallel · cross-check fully-developed)
    results/dpdx_extraction.csv       (axis-near p(x) cells · linear-fit dp/dx)
    results/tau_wall_delta.csv        (500 wall-face τ_w values · Δ vs analytical)
    results/summary.json              (strict-gate verdict)
    stdout: human-readable summary
"""
import csv
import json
import math
import os
import re
import sys

# Physical parameters (must match transportProperties + 0/U)
NU      = 1.5e-5
U_MEAN  = 0.1
R       = 0.005
L       = 0.5
U_MAX   = 2.0 * U_MEAN
DPDX_ANALYTICAL_KIN = -8.0 * NU * U_MEAN / (R * R)        # -0.48 m²/s²/m
TAU_WALL_ANALYTICAL_KIN = 4.0 * NU * U_MEAN / R            # 1.2e-3 m²/s²

# Mesh structure (must match blockMeshDict)
NX = 500    # x-cells
NR = 40     # r-cells
NTH = 1     # azimuthal cells
N_CELLS = NX * NR * NTH

# Strict FULL gate thresholds (per briefing)
GATE_DU_PCT     = 1.0    # max |Δu| < 1% (normalized by u_max)
GATE_DPDX_PCT   = 1.0    # |Δ dp/dx| < 1%
GATE_TAU_PCT    = 1.0    # |Δ τ_w| < 1%

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, "results")
SANDBOX_T = os.path.expanduser(
    "~/Desktop/case_027_hagen_poiseuille_pipe/case/5000"
)
SANDBOX_PP = os.path.expanduser(
    "~/Desktop/case_027_hagen_poiseuille_pipe/case/postProcessing/sampleDict/5000"
)
os.makedirs(RESULTS, exist_ok=True)

# ----------------------------------------------------------------
# OpenFOAM ascii field parser (pure-stdlib · tolerates v2312/v2512)
# ----------------------------------------------------------------
def parse_openfoam_field(path, expect_vector=False):
    """Parse OpenFOAM ascii field. Returns list of scalars or list of (vx,vy,vz)."""
    with open(path) as f:
        text = f.read()
    # Find "internalField" line then "nonuniform List<...>"
    m = re.search(r"internalField\s+nonuniform\s+List<(\w+)>\s*\n(\d+)\s*\n\(\s*\n", text)
    if not m:
        # Try "uniform <value>"
        m_uni = re.search(r"internalField\s+uniform\s+(\S+(?:\s+\S+\s+\S+)?)\s*;", text)
        if m_uni:
            val = m_uni.group(1)
            if expect_vector:
                # "(vx vy vz)" form
                m_v = re.match(r"\(([\d\.eE\+\-]+)\s+([\d\.eE\+\-]+)\s+([\d\.eE\+\-]+)\)", val)
                if m_v:
                    v = (float(m_v.group(1)), float(m_v.group(2)), float(m_v.group(3)))
                    return [v] * N_CELLS
            else:
                return [float(val)] * N_CELLS
        raise RuntimeError(f"Cannot parse internalField in {path}")
    n = int(m.group(2))
    start = m.end()
    out = []
    if expect_vector:
        # Lines like "(1.234e-3 5.678e-4 9.012e-5)"
        for line in text[start:].split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(")"):
                break
            mv = re.match(r"\(([\-\d\.eE\+]+)\s+([\-\d\.eE\+]+)\s+([\-\d\.eE\+]+)\)", line)
            if mv:
                out.append((float(mv.group(1)), float(mv.group(2)), float(mv.group(3))))
                if len(out) >= n:
                    break
    else:
        # Lines like "1.234e-3"
        for line in text[start:].split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(")"):
                break
            try:
                out.append(float(line))
                if len(out) >= n:
                    break
            except ValueError:
                continue
    assert len(out) == n, f"Expected {n} entries, got {len(out)} in {path}"
    return out

# ----------------------------------------------------------------
# Parse wallShearStress (boundary field on `wall` patch)
# Format: boundaryField { wall { type calculated; value nonuniform List<vector> NNN (... ); } }
# ----------------------------------------------------------------
def parse_wall_shear_stress(path):
    """Parse wallShearStress boundary 'wall' patch · returns list of (tx,ty,tz)."""
    with open(path) as f:
        text = f.read()
    # Find "wall" entry then "value nonuniform"
    m = re.search(
        r"wall\s*\{[^}]*?value\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(\s*\n",
        text, re.DOTALL)
    if not m:
        # alt format · maybe "value uniform"
        raise RuntimeError(f"Cannot parse wall boundary in {path}")
    n = int(m.group(1))
    start = m.end()
    out = []
    for line in text[start:].split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(")"):
            break
        mv = re.match(r"\(([\-\d\.eE\+]+)\s+([\-\d\.eE\+]+)\s+([\-\d\.eE\+]+)\)", line)
        if mv:
            out.append((float(mv.group(1)), float(mv.group(2)), float(mv.group(3))))
            if len(out) >= n:
                break
    assert len(out) == n, f"Expected {n} wall vectors, got {len(out)}"
    return out

# ----------------------------------------------------------------
# Load cell-centers + U + p
# ----------------------------------------------------------------
print(f"Parsing OpenFOAM fields from {SANDBOX_T}/")
C_field   = parse_openfoam_field(os.path.join(SANDBOX_T, "C"),  expect_vector=True)
U_field   = parse_openfoam_field(os.path.join(SANDBOX_T, "U"),  expect_vector=True)
p_field   = parse_openfoam_field(os.path.join(SANDBOX_T, "p"),  expect_vector=False)
tau_field = parse_wall_shear_stress(os.path.join(SANDBOX_T, "wallShearStress"))
print(f"  C:  {len(C_field)} cells")
print(f"  U:  {len(U_field)} cells")
print(f"  p:  {len(p_field)} cells")
print(f"  τ:  {len(tau_field)} wall faces\n")

def u_analytical(r):
    """Hagen-Poiseuille: u(r) = 2·u_mean·(1 - (r/R)²)"""
    return U_MAX * (1.0 - (r / R) ** 2)

def linfit(xs, ys):
    """Pure-stdlib least-squares slope/intercept"""
    n = len(xs)
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-30:
        return 0.0, 0.0
    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n
    return m, b

# ----------------------------------------------------------------
# Exit profile: cells at i=NX-1 (last x-column), j=0..NR-1
# Cell index in OpenFOAM polyMesh: idx = i + j*NX + k*NX*NR (k=0)
# ----------------------------------------------------------------
def cell_index(i, j, k=0):
    return i + j * NX + k * NX * NR

print("Building exit-station profile (last x-column, all 40 radial cells)...")
exit_rows = []
i_exit = NX - 1   # x ≈ 0.4995
for j in range(NR):
    idx = cell_index(i_exit, j)
    cx, cy, cz = C_field[idx]
    r = math.sqrt(cy * cy + cz * cz)
    ux = U_field[idx][0]
    pv = p_field[idx]
    u_anal = u_analytical(r)
    delta_pct = (ux - u_anal) / U_MAX * 100.0
    exit_rows.append((j, r, ux, u_anal, delta_pct, pv, cx))

# CSV
exit_csv = os.path.join(RESULTS, "exit_profile_delta.csv")
with open(exit_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["j_radial_index", "r_m", "r_over_R", "u_sampled_m_s",
                "u_analytical_m_s", "delta_pct_of_umax", "p_kinematic_m2_s2",
                "cx_m"])
    for j, r, ux, u_anal, dp, pv, cx in exit_rows:
        w.writerow([j, f"{r:.6e}", f"{r/R:.6f}", f"{ux:.6e}",
                    f"{u_anal:.6e}", f"{dp:.4f}", f"{pv:.4e}", f"{cx:.6f}"])

n_exit = len(exit_rows)
max_du_exit_pct = max(abs(row[4]) for row in exit_rows)
strict_pass_count_exit = sum(1 for row in exit_rows if abs(row[4]) < GATE_DU_PCT)

# ----------------------------------------------------------------
# Mid-pipe profile: cells at i=NX/2 (mid x), all radial
# ----------------------------------------------------------------
print("Building mid-pipe profile (x≈0.25, all 40 radial cells)...")
mid_rows = []
i_mid = NX // 2   # x ≈ 0.2495
for j in range(NR):
    idx = cell_index(i_mid, j)
    cx, cy, cz = C_field[idx]
    r = math.sqrt(cy * cy + cz * cz)
    ux = U_field[idx][0]
    pv = p_field[idx]
    u_anal = u_analytical(r)
    delta_pct = (ux - u_anal) / U_MAX * 100.0
    mid_rows.append((j, r, ux, u_anal, delta_pct, pv, cx))

mid_csv = os.path.join(RESULTS, "mid_profile_delta.csv")
with open(mid_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["j_radial_index", "r_m", "r_over_R", "u_sampled_m_s",
                "u_analytical_m_s", "delta_pct_of_umax", "p_kinematic_m2_s2",
                "cx_m"])
    for j, r, ux, u_anal, dp, pv, cx in mid_rows:
        w.writerow([j, f"{r:.6e}", f"{r/R:.6f}", f"{ux:.6e}",
                    f"{u_anal:.6e}", f"{dp:.4f}", f"{pv:.4e}", f"{cx:.6f}"])

n_mid = len(mid_rows)
max_du_mid_pct = max(abs(row[4]) for row in mid_rows)
strict_pass_count_mid = sum(1 for row in mid_rows if abs(row[4]) < GATE_DU_PCT)

# ----------------------------------------------------------------
# dp/dx: axis-nearest j=0 row across x ∈ [0.05, 0.45]
# ----------------------------------------------------------------
print("Building axis pressure profile (j=0, x ∈ [0.05, 0.45])...")
xs_p = []
ps   = []
j_pres = 0   # axis-nearest cell row (most representative of axial p)
for i in range(NX):
    idx = cell_index(i, j_pres)
    cx, cy, cz = C_field[idx]
    pv = p_field[idx]
    if 0.05 <= cx <= 0.45:
        xs_p.append(cx)
        ps.append(pv)

slope_kin, intercept_kin = linfit(xs_p, ps)
dpdx_delta_pct = (slope_kin - DPDX_ANALYTICAL_KIN) / DPDX_ANALYTICAL_KIN * 100.0

dpdx_csv = os.path.join(RESULTS, "dpdx_extraction.csv")
with open(dpdx_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["x_m", "p_kinematic_m2_s2"])
    for x, p in zip(xs_p, ps):
        w.writerow([f"{x:.6e}", f"{p:.6e}"])
    w.writerow([])
    w.writerow(["LINEAR FIT (cells at j=0 · axis-nearest row · x ∈ [0.05, 0.45])"])
    w.writerow([f"slope_fit_kin = {slope_kin:.6e} m²/s²/m"])
    w.writerow([f"slope_analytical_kin = {DPDX_ANALYTICAL_KIN:.6e} m²/s²/m"])
    w.writerow([f"delta_pct = {dpdx_delta_pct:.4f}%"])
    w.writerow([f"intercept_fit_kin = {intercept_kin:.6e} m²/s²"])
    w.writerow([f"n_points = {len(xs_p)}"])

# ----------------------------------------------------------------
# τ_wall comparison (from wallShearStress field · all 500 wall faces)
# Spatial structure: wall faces are ordered streamwise (face_i ≈ x_i = (i+0.5)·Δx).
# Strict gate is applied over the fully-developed region: x ∈ [0.05, 0.45]
# (10·R buffer from inlet/outlet · same convention as dp/dx · case_025 §6 precedent).
# Faces 0-49 (x < 0.05) excluded as inlet entrance region · faces 450+ (x > 0.45)
# excluded as outlet end region.
# ----------------------------------------------------------------
print("Computing τ_wall comparison (500 wall faces · all + developed region)...")
DX_WALL = 1e-3
N_BUFFER_INLET = int(0.05 / DX_WALL)   # 50 faces
N_BUFFER_OUTLET = int(0.05 / DX_WALL)  # 50 faces
i_dev_start = N_BUFFER_INLET
i_dev_end   = NX - N_BUFFER_OUTLET

# For each wall face, τ_w_kinematic magnitude = sqrt(tx²+ty²+tz²)
tau_mags = [math.sqrt(t[0]**2 + t[1]**2 + t[2]**2) for t in tau_field]
tau_min_all  = min(tau_mags)
tau_max_all  = max(tau_mags)
tau_mean_all = sum(tau_mags) / len(tau_mags)
tau_delta_min_all_pct  = (tau_min_all  - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
tau_delta_max_all_pct  = (tau_max_all  - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
tau_delta_mean_all_pct = (tau_mean_all - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
tau_delta_max_abs_all_pct = max(abs(tau_delta_min_all_pct), abs(tau_delta_max_all_pct))
strict_pass_count_tau_all = sum(
    1 for tm in tau_mags
    if abs((tm - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0) < GATE_TAU_PCT
)

# Developed-region subset (x ∈ [0.05, 0.45] · matches dp/dx convention)
tau_mags_dev = tau_mags[i_dev_start:i_dev_end]
tau_min_dev  = min(tau_mags_dev)
tau_max_dev  = max(tau_mags_dev)
tau_mean_dev = sum(tau_mags_dev) / len(tau_mags_dev)
tau_delta_min_dev_pct  = (tau_min_dev  - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
tau_delta_max_dev_pct  = (tau_max_dev  - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
tau_delta_mean_dev_pct = (tau_mean_dev - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
tau_delta_max_abs_dev_pct = max(abs(tau_delta_min_dev_pct), abs(tau_delta_max_dev_pct))
strict_pass_count_tau_dev = sum(
    1 for tm in tau_mags_dev
    if abs((tm - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0) < GATE_TAU_PCT
)
n_dev = len(tau_mags_dev)

# Strict gate uses developed-region max (consistent with dp/dx exclusion convention)
tau_min  = tau_min_dev
tau_max  = tau_max_dev
tau_mean = tau_mean_dev
tau_delta_min_pct  = tau_delta_min_dev_pct
tau_delta_max_pct  = tau_delta_max_dev_pct
tau_delta_mean_pct = tau_delta_mean_dev_pct
tau_delta_max_abs_pct = tau_delta_max_abs_dev_pct
strict_pass_count_tau = strict_pass_count_tau_dev

tau_csv = os.path.join(RESULTS, "tau_wall_delta.csv")
with open(tau_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["face_index", "x_approx_m", "tau_magnitude_kin_m2_s2",
                "delta_pct_vs_analytical", "in_developed_region"])
    for i, tm in enumerate(tau_mags):
        d = (tm - TAU_WALL_ANALYTICAL_KIN) / TAU_WALL_ANALYTICAL_KIN * 100.0
        x_approx = (i + 0.5) * DX_WALL
        in_dev = i_dev_start <= i < i_dev_end
        w.writerow([i, f"{x_approx:.4f}", f"{tm:.6e}", f"{d:.4f}", str(in_dev)])
    w.writerow([])
    w.writerow(["SUMMARY · full wall (500 faces · includes inlet/outlet entrance)"])
    w.writerow([f"n_wall_faces_all = {len(tau_mags)}"])
    w.writerow([f"tau_min_all  kin = {tau_min_all:.6e} ({tau_delta_min_all_pct:+.4f}%)"])
    w.writerow([f"tau_max_all  kin = {tau_max_all:.6e} ({tau_delta_max_all_pct:+.4f}%)"])
    w.writerow([f"tau_mean_all kin = {tau_mean_all:.6e} ({tau_delta_mean_all_pct:+.4f}%)"])
    w.writerow([f"max |Δ|_all     = {tau_delta_max_abs_all_pct:.4f}%"])
    w.writerow([f"strict pass_all (|Δ|<1%) = {strict_pass_count_tau_all}/{len(tau_mags)}"])
    w.writerow([])
    w.writerow([f"SUMMARY · developed region · x ∈ [0.05, 0.45] · {n_dev} faces"])
    w.writerow([f"(same convention as dp/dx · case_025 §6 precedent · 10·R inlet/outlet buffer)"])
    w.writerow([f"tau_min_dev  kin = {tau_min_dev:.6e} ({tau_delta_min_dev_pct:+.4f}%)"])
    w.writerow([f"tau_max_dev  kin = {tau_max_dev:.6e} ({tau_delta_max_dev_pct:+.4f}%)"])
    w.writerow([f"tau_mean_dev kin = {tau_mean_dev:.6e} ({tau_delta_mean_dev_pct:+.4f}%)"])
    w.writerow([f"max |Δ|_dev     = {tau_delta_max_abs_dev_pct:.4f}%"])
    w.writerow([f"strict pass_dev (|Δ|<1%) = {strict_pass_count_tau_dev}/{n_dev}"])
    w.writerow([f"tau_analytical_kin = {TAU_WALL_ANALYTICAL_KIN:.6e}"])

# ----------------------------------------------------------------
# Strict-gate verdict
# ----------------------------------------------------------------
u_pass     = max_du_exit_pct < GATE_DU_PCT
dpdx_pass  = abs(dpdx_delta_pct) < GATE_DPDX_PCT
tau_pass   = tau_delta_max_abs_pct < GATE_TAU_PCT

# Residuals at iter 5000 (from SIMPLEFOAM_LOG.txt grep):
#   Ux: 2.954352553e-12     ✓
#   Uy: 9.062859092e-07     ✗ (90× over)
#   Uz: 3.324559402e-02     ✗ wedge artifact
#   p:  2.685903838e-08     ✗ (2.7× over · slowly decreasing)
RESIDUALS_FINAL = {
    "Ux": 2.954352553e-12,
    "Uy": 9.062859092e-07,
    "Uz": 3.324559402e-02,
    "p":  2.685903838e-08,
}
residuals_strict_pass_count = sum(1 for v in RESIDUALS_FINAL.values() if v < 1e-8)
residuals_pass = (residuals_strict_pass_count == 4)

# Field-count adjusted (laminar axisymmetric · Uz is wedge artifact per case_025 §3 precedent):
residuals_adjusted_pass_count = sum(
    1 for k, v in RESIDUALS_FINAL.items() if k != "Uz" and v < 1e-8
)
residuals_adjusted_pass = (residuals_adjusted_pass_count == 3)

verdict = "FULL" if (u_pass and dpdx_pass and tau_pass and residuals_pass) else (
    "MARGINAL" if (max_du_exit_pct < 3.0 and abs(dpdx_delta_pct) < 3.0 and tau_delta_max_abs_pct < 3.0) else "PARTIAL"
)

summary = {
    "case_id": "case_027_hagen_poiseuille_pipe",
    "solver_time_step_at_convergence": 5000,
    "solver_auto_exit": False,
    "n_radial_cells_exit": n_exit,
    "n_radial_cells_mid":  n_mid,
    "n_pressure_cells":    len(xs_p),
    "n_wall_faces":        len(tau_mags),
    "max_du_exit_pct":     round(max_du_exit_pct, 4),
    "max_du_mid_pct":      round(max_du_mid_pct, 4),
    "strict_pass_count_exit": f"{strict_pass_count_exit}/{n_exit}",
    "strict_pass_count_mid":  f"{strict_pass_count_mid}/{n_mid}",
    "dpdx_fit_kin_m2_s2_per_m": slope_kin,
    "dpdx_analytical_kin_m2_s2_per_m": DPDX_ANALYTICAL_KIN,
    "dpdx_delta_pct": round(dpdx_delta_pct, 4),
    "tau_wall_all_min_kin":  tau_min_all,
    "tau_wall_all_max_kin":  tau_max_all,
    "tau_wall_all_mean_kin": tau_mean_all,
    "tau_wall_dev_min_kin":  tau_min_dev,
    "tau_wall_dev_max_kin":  tau_max_dev,
    "tau_wall_dev_mean_kin": tau_mean_dev,
    "tau_wall_analytical_kin": TAU_WALL_ANALYTICAL_KIN,
    "tau_delta_all_min_pct":  round(tau_delta_min_all_pct,  4),
    "tau_delta_all_max_pct":  round(tau_delta_max_all_pct,  4),
    "tau_delta_all_mean_pct": round(tau_delta_mean_all_pct, 4),
    "tau_delta_all_max_abs_pct": round(tau_delta_max_abs_all_pct, 4),
    "tau_delta_dev_min_pct":  round(tau_delta_min_dev_pct,  4),
    "tau_delta_dev_max_pct":  round(tau_delta_max_dev_pct,  4),
    "tau_delta_dev_mean_pct": round(tau_delta_mean_dev_pct, 4),
    "tau_delta_dev_max_abs_pct": round(tau_delta_max_abs_dev_pct, 4),
    "tau_strict_pass_count_all": f"{strict_pass_count_tau_all}/{len(tau_mags)}",
    "tau_strict_pass_count_dev": f"{strict_pass_count_tau_dev}/{n_dev}",
    "tau_strict_gate_applied_to": "developed region (x ∈ [0.05, 0.45]) per case_025 §6 dp/dx exclusion convention",
    "residuals_final": RESIDUALS_FINAL,
    "residuals_strict_4_4_pass_count": f"{residuals_strict_pass_count}/4",
    "residuals_adjusted_3_3_pass_count": f"{residuals_adjusted_pass_count}/3",
    "strict_gate_u_pass": u_pass,
    "strict_gate_dpdx_pass": dpdx_pass,
    "strict_gate_tau_pass": tau_pass,
    "strict_gate_residuals_pass_4_4": residuals_pass,
    "strict_gate_residuals_pass_3_3_adjusted": residuals_adjusted_pass,
    "verdict": verdict,
}

with open(os.path.join(RESULTS, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

# ----------------------------------------------------------------
# Stdout
# ----------------------------------------------------------------
print(f"\n==== case_027 · Hagen-Poiseuille pipe validation ====\n")
print(f"Solver final iter: 5000 (SIMPLE auto-exit did NOT fire · max iter hit)")
print(f"Cell counts: {N_CELLS} total, {n_exit} radial cells at exit\n")
print(f"--- u(r) exit station x≈0.4995 ---")
print(f"  max |Δu| = {max_du_exit_pct:.4f}% (of u_max=0.2 m/s)")
print(f"  strict (<1%) pass: {strict_pass_count_exit}/{n_exit}")
print(f"  gate: {'PASS' if u_pass else 'FAIL'}\n")
print(f"--- u(r) mid station x≈0.25 (cross-check) ---")
print(f"  max |Δu| = {max_du_mid_pct:.4f}%")
print(f"  strict pass: {strict_pass_count_mid}/{n_mid}\n")
print(f"--- dp/dx (from j=0 cell linear fit over x ∈ [0.05, 0.45]) ---")
print(f"  slope_fit_kin       = {slope_kin:.6e} m²/s²/m")
print(f"  slope_analytical_kin = {DPDX_ANALYTICAL_KIN:.6e} m²/s²/m")
print(f"  Δ = {dpdx_delta_pct:+.4f}%   gate: {'PASS' if dpdx_pass else 'FAIL'}\n")
print(f"--- τ_w cross-check (500 wall faces) ---")
print(f"  Full wall (incl entrance · 500 faces):")
print(f"    range = {tau_min_all:.4e} to {tau_max_all:.4e} (mean {tau_mean_all:.4e})")
print(f"    Δ_min/Δ_mean/Δ_max = {tau_delta_min_all_pct:+.4f}% / {tau_delta_mean_all_pct:+.4f}% / {tau_delta_max_all_pct:+.4f}%")
print(f"    strict pass (|Δ|<1%): {strict_pass_count_tau_all}/{len(tau_mags)}")
print(f"  Developed region x∈[0.05,0.45] ({n_dev} faces · case_025 §6 convention):")
print(f"    range = {tau_min_dev:.4e} to {tau_max_dev:.4e} (mean {tau_mean_dev:.4e})")
print(f"    Δ_min/Δ_mean/Δ_max = {tau_delta_min_dev_pct:+.4f}% / {tau_delta_mean_dev_pct:+.4f}% / {tau_delta_max_dev_pct:+.4f}%")
print(f"    max |Δ| = {tau_delta_max_abs_dev_pct:.4f}%   gate: {'PASS' if tau_pass else 'FAIL'}")
print(f"    strict pass (|Δ|<1%): {strict_pass_count_tau_dev}/{n_dev}")
print(f"  τ_w analytical (4·ν·u_mean/R) = {TAU_WALL_ANALYTICAL_KIN:.4e} m²/s²\n")
print(f"--- Residuals final (iter 5000) ---")
for k, v in RESIDUALS_FINAL.items():
    flag = "✓" if v < 1e-8 else "✗"
    print(f"  {k}: {v:.4e}  {flag} ({'< 1e-8' if v < 1e-8 else '> 1e-8'})")
print(f"  strict 4/4 < 1e-8: {residuals_strict_pass_count}/4 {'PASS' if residuals_pass else 'FAIL'}")
print(f"  adjusted 3/3 (excl Uz wedge artifact): {residuals_adjusted_pass_count}/3 {'PASS' if residuals_adjusted_pass else 'FAIL'}\n")
print(f"==== VERDICT: {verdict} ====")
print(f"  u_PASS={u_pass}  dpdx_PASS={dpdx_pass}  tau_PASS={tau_pass}  res4/4_PASS={residuals_pass}  res3/3adj_PASS={residuals_adjusted_pass}")
