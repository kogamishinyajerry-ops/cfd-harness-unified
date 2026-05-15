#!/usr/bin/env python3
"""
case_027 · Hagen-Poiseuille pipe flow · analytical reference
============================================================

Closed-form analytical solution for steady, incompressible, Newtonian,
fully-developed laminar flow in a circular pipe of radius R (Hagen-Poiseuille).

Source: Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed.
Springer, §5.1.2 "Circular pipe flow / Hagen-Poiseuille".
Also: White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.3.3.

Pure stdlib (no numpy / no pandas) for Q1 LLM-offline gate compliance.

Run:
    env -i HOME=$HOME PATH=/usr/bin:/bin python3 analytical_reference.py

Outputs:
    results/analytical_reference.csv     (17+ r-points · u_analytical reference table)
    stdout: human-readable canonical-values dump
"""
import csv
import os
import sys

# Physical parameters (must match transportProperties + 0/U)
NU      = 1.5e-5       # kinematic viscosity [m²/s]
U_MEAN  = 0.1          # cross-section mean velocity [m/s]
R       = 0.005        # pipe radius [m]
L       = 0.5          # pipe length [m]
U_MAX   = 2.0 * U_MEAN # Hagen-Poiseuille centerline u_max = 2·u_mean
D       = 2.0 * R      # diameter

# Derived canonical quantities (kinematic OpenFOAM convention)
RE_D                 = U_MEAN * D / NU                  # Reynolds = 66.67 (laminar < 2300)
DPDX_ANALYTICAL_KIN  = -8.0 * NU * U_MEAN / (R * R)     # -0.48 m²/s²/m
TAU_WALL_ANALYTICAL_KIN = 4.0 * NU * U_MEAN / R          # 1.2e-3 m²/s²

# Length-scale checks
L_ENTRANCE           = 0.06 * RE_D * D                  # ≈ 0.04 m · classical Boussinesq
L_BUFFER_RATIO       = L / L_ENTRANCE                   # ≈ 12.5×

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RESULTS, exist_ok=True)

def u_analytical(r):
    """Hagen-Poiseuille: u(r) = 2·u_mean·(1 - (r/R)²) for r ∈ [0, R]"""
    return U_MAX * (1.0 - (r / R) ** 2)

def dudr_analytical(r):
    """du/dr = -2·u_max·r / R² · used for τ_w cross-derivation"""
    return -2.0 * U_MAX * r / (R * R)

# ----------------------------------------------------------------
# Generate 17+ r-point reference table at uniform r spacing
# (will be compared to non-uniform simpleGrading sampled values later)
# ----------------------------------------------------------------
N_REF_POINTS = 21  # ≥ 17+ requirement · uniform spacing for canonical reference
ref_csv = os.path.join(RESULTS, "analytical_reference.csv")
with open(ref_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["r_m", "r_over_R", "u_analytical_m_s", "u_over_umax",
                "du_dr_analytical_per_s"])
    for i in range(N_REF_POINTS):
        r = R * i / (N_REF_POINTS - 1)
        u = u_analytical(r)
        dudr = dudr_analytical(r)
        w.writerow([f"{r:.6e}", f"{r/R:.4f}", f"{u:.6e}",
                    f"{u/U_MAX:.6f}", f"{dudr:.6e}"])

# ----------------------------------------------------------------
# Stdout summary
# ----------------------------------------------------------------
print(f"==== case_027 · Hagen-Poiseuille pipe · analytical reference ====\n")
print(f"Physical parameters:")
print(f"  ν       = {NU:.3e} m²/s")
print(f"  u_mean  = {U_MEAN} m/s")
print(f"  R       = {R} m")
print(f"  D = 2·R = {D} m")
print(f"  L       = {L} m")
print(f"  u_max   = 2·u_mean = {U_MAX} m/s\n")
print(f"Reynolds:")
print(f"  Re_D = u_mean·D/ν = {RE_D:.2f} (laminar < 2300 ✓)\n")
print(f"Entrance length:")
print(f"  L_entrance ≈ 0.06·Re·D = {L_ENTRANCE:.4f} m")
print(f"  L/L_entrance         = {L_BUFFER_RATIO:.2f}× (≥ 3× buffer ✓)\n")
print(f"Analytical derived quantities (kinematic OpenFOAM convention):")
print(f"  dp_kin/dx (Hagen-Poiseuille) = -8·ν·u_mean/R² = {DPDX_ANALYTICAL_KIN:.6e} m²/s²/m")
print(f"  τ_wall_kin                   =  4·ν·u_mean/R  = {TAU_WALL_ANALYTICAL_KIN:.6e} m²/s²")
print(f"  → Δp_kin over L = {DPDX_ANALYTICAL_KIN*L:.6e} m²/s² (linear pressure drop)\n")
print(f"Velocity profile sample (uniform r grid · {N_REF_POINTS} points):")
print(f"  {'r [m]':>12} {'r/R':>8} {'u [m/s]':>12} {'u/u_max':>10}")
for i in range(N_REF_POINTS):
    r = R * i / (N_REF_POINTS - 1)
    u = u_analytical(r)
    print(f"  {r:>12.4e} {r/R:>8.4f} {u:>12.4e} {u/U_MAX:>10.6f}")
print(f"\nReference table written: {ref_csv}\n")
print(f"==== Strict FULL gate thresholds (per briefing) ====")
print(f"  max |Δu|     < 1%  of u_max ({U_MAX} m/s) → < {0.01*U_MAX:.4e} m/s")
print(f"  |Δ dp/dx|    < 1%  of {DPDX_ANALYTICAL_KIN:.4e}")
print(f"  |Δ τ_w|      < 1%  of {TAU_WALL_ANALYTICAL_KIN:.4e}")
print(f"  residuals    < 1e-8 on p, Ux, Uy, Uz (4/4 · laminar 3D wedge)")
