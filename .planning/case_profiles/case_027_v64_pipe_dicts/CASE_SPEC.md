# case_027 · Hagen-Poiseuille Pipe Flow · CASE_SPEC

> V64-A Tier 2 · M-V64A-VAL-FULL-PIPE · axisymmetric 1D-equivalent analytical canonical
> Parent DEC: DEC-V64-A-charter
> Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-PIPE (in flight · B70 dispatch · companion to B68 plane Poiseuille FULL · companion to B69 Couette dispatch · all 1D analytical class)

## §1 Strategic context

V64-A Tier 2 attempts to date (post-B67 + B68 reconcile · commit 83f544b):

| Attempt | Case | Verdict | Strongest issue |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup |
| #3 (B63) | case_021 NASA TMR flat plate | PARTIAL (soft) | residuals plateau 3-5e-5 |
| #4 (B65) | case_024 lid-driven cavity Re=1000 | PARTIAL (strong) | 129² uniform-grid v-discrepancy |
| #5 (B66) | case_022 Driver-Seegmiller BFS | PARTIAL · x_R/h 5.44 vs 6.26 | uniform inlet δ/h gap |
| #6 (B67) | case_024 cavity v2 (stretched) | PARTIAL v2 | physics regression v 4.10 → 6.49% |
| #7 (B68) | case_025 plane Poiseuille | **FULL ✓** | (none · clean PASS · max 0.0425%) |
| **#8 (B70) · this CASE_SPEC** | **case_027 Hagen-Poiseuille pipe** | TBD | **axisymmetric 1D · companion to B68 plane Poiseuille FULL** |

**Why Hagen-Poiseuille pipe after B68 plane Poiseuille FULL**:
- B68 empirically calibrated that 1D analytical canonicals are the strict-FULL-attainable path in V64-A (2D canonicals 5/6 PARTIAL · 1D analytical 1/1 FULL pre-B70)
- Hagen-Poiseuille pipe is the 3D-axisymmetric homologue of plane Poiseuille:
  - Plane: u(y) = (3/2)·u_mean·(1 - (y/H)²) · 2D · 1 hex block · 4 quad patches
  - Pipe : u(r) = 2·u_mean·(1 - (r/R)²)   · 3D wedge · 1 hex degenerate-edge block · 5 patches (incl. 2 wedge symmetry)
- Pressure-gradient factor differs (8 vs 3) due to geometry (cylindrical vs planar)
- Wall-shear factor differs (4 vs 3) due to geometry (cylindrical 4-coefficient vs planar 3-coefficient)
- If pipe also strict-FULL → confirms 1D-analytical empirical evidence robust across geometry (planar → cylindrical) · Done #1 1/3 → 2/3 strict (standalone) OR 1→3/3 ✓ MET (if B69 Couette also PASS) → V64-A close path unblocked

## §2 Canonical selection · Hagen-Poiseuille pipe (Schlichting §5.1.2)

**Source**: Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed. Springer, §5.1.2 "Circular pipe flow / Hagen-Poiseuille"; also White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.3.3 "Laminar flow in a long circular tube".

**Analytical solution** (steady · incompressible · Newtonian · cylindrical-axisymmetric · no body force · fully-developed):

```
u(r) = 2 · u_mean · (1 - (r/R)²)        for r ∈ [0, R]
```

with derived quantities:

```
u_max     = u(0)        = 2 · u_mean              [centerline]
dp/dx     = -8·μ·u_mean / R²                      [streamwise pressure gradient · Hagen-Poiseuille]
τ_wall    = μ · |du/dr|_{r=R} = 4·μ·u_mean/R      [wall shear stress]
        = -R/2 · dp/dx                            [also force-balance identity]
Re_D      = ρ · u_mean · D / μ  = u_mean·D/ν      [Reynolds number based on diameter D=2R]
```

In kinematic OpenFOAM convention (p_kin = p/ρ; ρ absorbed into ν=μ/ρ):

```
dp_kin/dx = -8·ν·u_mean / R²                      [kinematic pressure gradient]
τ_kin     = 4·ν·u_mean / R                        [kinematic wall shear stress]
```

**Rationale (vs alternatives plane Couette / annular Poiseuille / turbulent pipe)**:
1. **Direct geometric homologue of B68 plane Poiseuille FULL** — minimizes infrastructure risk; isolates "planar → cylindrical" geometry-change variable
2. **Analytical exactness**: closed-form u(r) is exact to machine precision · no experimental uncertainty band
3. **Standard OpenFOAM axisymmetric wedge convention**: 1 hex block with degenerate axis edge · 5° wedge canonical · documented in OpenFOAM v2512 user guide
4. **Pure diagnostic**: any deviation isolates wedge-mesh / discretization / BC error · NO physics ambiguity
5. **Cross-validates 1D-analytical empirical evidence**: if both plane (B68) + pipe (B70) FULL → "1D analytical path strict-FULL-attainable" is robust empirical finding across geometry classes

## §3 Geometry

Single 3D axisymmetric wedge (single hex block with degenerate axis edge):
- Pipe radius **R = 0.005 m** (diameter D = 0.01 m)
- Pipe length **L = 0.5 m** = **100·R** = **50·D** (≥ 3·L_entrance buffer · L_entrance ≈ 0.04 m for Re_D=66.7)
- Wedge half-angle **θ/2 = 2.5°** (full wedge 5° · OpenFOAM canonical convention)

Coordinate origin: pipe-inlet on axis (x=0, y=0, z=0). Pipe centerline = x-axis. Radial coordinate r = sqrt(y² + z²).

8-vertex hex block with 2 coincident pairs on axis:
- v0 = v4 = (0, 0, 0)                                                  inlet · axis (degenerate)
- v1 = v5 = (L, 0, 0)                                                  outlet · axis (degenerate)
- v2 = (L, R·cos(2.5°), -R·sin(2.5°))                                  outlet · wall · back wedge
- v3 = (0, R·cos(2.5°), -R·sin(2.5°))                                  inlet · wall · back wedge
- v6 = (L, R·cos(2.5°), +R·sin(2.5°))                                  outlet · wall · front wedge
- v7 = (0, R·cos(2.5°), +R·sin(2.5°))                                  inlet · wall · front wedge

(8 vertices with v0=v4 and v1=v5 coincident — OpenFOAM blockMesh accepts this for wedge meshes; the degenerate edge along the axis is handled natively.)

## §4 Inflow conditions

| Variable | Value | Source |
|---|---|---|
| u_mean (cross-section average) | 0.1 m/s | per briefing target |
| u_max (centerline) | 0.2 m/s | = 2·u_mean (analytical) |
| ρ (effective) | 1.0 kg/m³ | normalized incompressible |
| ν | 1.5e-5 m²/s | per briefing (air @ 15°C · matches case_025) |
| Re_D = u_mean·D/ν | 0.1·0.01/1.5e-5 = **66.67** | calculated · deep laminar (Re_D < 2300) |
| L_entrance ≈ 0.06·Re_D·D | 0.06·66.67·0.01 = **0.04 m** | classical Boussinesq estimate |
| L/L_entrance | 0.5/0.04 = **12.5×** | development buffer · very large margin |
| dp/dx (kinematic) | -8·ν·u_mean/R² = **-0.48 m²/s²/m** | analytical · gives Δp_kin total over L = -0.24 m²/s² |
| τ_wall (kinematic) | 4·ν·u_mean/R = **1.2e-3 m²/s²** | analytical · 2.67× plane Poiseuille τ_w |

**Inlet BC**: `codedFixedValue` parabolic radial profile u(r) = u_max·(1 - (r/R)²) with r computed from sqrt(y²+z²) per face center. The inlet IS the analytical solution.

**Outlet BC**: p = 0 fixedValue (gauge zero), U zeroGradient (allows flow to extrapolate naturally).

**Wall BC**: noSlip at r=R.

**Front/back BC**: type `wedge` (OpenFOAM axisymmetric symmetry).

**Axis**: degenerate edge (no patch · handled by wedge convention).

## §5 17+ r-point query at exit station

Sample line at x_exit = 0.4995 m (just upstream of fixed-p outlet face), from axis (y=0, z=0) to wall (y=R·cos(2.5°), z=0). Because the wedge is symmetric about z=0, the y-axis line at z=0 spans the full radius.

```
exitProfile
{
    type        midPoint;
    axis        y;
    start       (0.4995 0.0                          0.0);
    end         (0.4995 0.004990480935  0.0);   // y = R·cos(2.5°) = 0.005·0.999048
}
```

With ny=40 cells (radial grading 1/3 toward wall i.e. axis cells coarser) → midPoint sampling returns 40 cell-centered r-values → 40 ≥ 17+ ✓

Sample line at mid-pipe (x=0.25 m) for fully-developed verification:

```
midProfile
{
    type        midPoint;
    axis        y;
    start       (0.25 0.0                          0.0);
    end         (0.25 0.004990480935  0.0);
}
```

Sample line along axis for dp/dx extraction:

```
axisPressure
{
    type        midPoint;
    axis        x;
    start       (0.05 0.0 0.0);
    end         (0.45 0.0 0.0);
}
```

dp/dx extracted via linear fit p(x) over x ∈ [0.05, 0.45] (excludes inlet/outlet boundary perturbations · 10·R buffer each side).

## §6 Canonical comparison points

For each of N≥17 r-values r_i sampled at x=0.4995:

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| u(r_i) | 2·0.1·(1 - (r_i/0.005)²) | from postProcessing/sets | (u_sampled - u_analytical) / u_max × 100% |

For dp/dx:

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| dp/dx (kinematic) | -0.48 m²/s²/m | linear fit over x ∈ [0.05, 0.45] | (slope_fit - slope_analytical) / slope_analytical × 100% |

For τ_wall (strict-gate criterion per briefing):

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| τ_wall (kinematic) | 1.2e-3 m²/s² | from wallShearStress functionObject | (τ_sampled - τ_analytical) / τ_analytical × 100% |

## §7 Strict FULL gate (per briefing)

- **max |Δu| < 1%** across 17+ r-points at exit station (normalized by u_max = 0.2 m/s)
- **|Δ dp/dx| < 1%** vs analytical -0.48 m²/s²/m
- **|Δ τ_w| < 1%** vs analytical 1.2e-3 m²/s²
- **residuals 4/4 < 1e-8** (laminar regime → fields are p, Ux, Uy, Uz = 4 quantities in 3D wedge; will report all 4)

**Marginal**: max |Δu| ∈ [1%, 3%] · document & user ratifies
**PARTIAL**: max |Δu| > 3% OR residuals not converged OR wedge setup fails

## §8 Solver setup

- Solver: `simpleFoam` (incompressible steady-state)
- Turbulence: **laminar** (Re_D = 66.7 deep laminar · no model required)
- Schemes: 2nd-order bounded upwind for div(phi,U); Gauss linear for grad/laplacian (matches case_025)
- p-solver: GAMG + GaussSeidel
- U-solver: PBiCGStab + DILU
- URF: p = 0.30, U = 0.70 (standard set, matches case_025)
- Convergence: residualControl 1e-8 on all 4 quantities; maxIter 5000

## §9 Mesh design

Single wedge block:

| Block | Region | nx × nr × nθ | Grading (x, r, θ) | Cells |
|---|---|---|---|---|
| 1 | full pipe (x ∈ [0, 0.5], r ∈ [0, R], azimuth ∈ [-2.5°, +2.5°]) | 500 × 40 × 1 | (1, 0.333, 1) | 20,000 |

- x: uniform · Δx = 1e-3 m
- r: simpleGrading 0.333 (radial cells shrink from axis to wall · last cell at wall ≈ 7e-5 m · first cell at axis ≈ 2.1e-4 m)
  - This is INVERTED from case_025 plane Poiseuille (which had bilinear-3 symmetric grading) because here there's only ONE wall (at r=R · the other "side" is the axis where degeneracy is fine)
  - Wall-side fine resolves the steep ∂u/∂r near wall (important for τ_w accuracy)
  - Axis-side coarse acceptable because analytical u is smooth quadratic with ∂u/∂r = 0 at axis
- θ: 1 single cell across 5° wedge (axisymmetric convention)

Aspect ratio:
- max cell at wall: Δx / δr_wall ≈ 1e-3 / 7e-5 ≈ 14.3 (high but standard for wall-resolved wedge meshes)
- max cell at axis: Δx / δr_axis ≈ 1e-3 / 2.1e-4 ≈ 4.8 (acceptable)
- max cell tangential (wall): R·sin(2.5°)·2 / 1 cell × Δx ≈ 2·0.005·0.0436·1e-3 ≈ 4.36e-4 m → Δx / δθ_wall ≈ 1e-3/4.36e-4 ≈ 2.3 (excellent)

## §10 Risk flags

- **executable_smoke_test**: med — first axisymmetric wedge in repo · solver-class identical to case_025
- **solver_stability_on_novel_geometry**: low — Hagen-Poiseuille pipe is THE textbook canonical for axisymmetric internal flow
- **canonical_reference_drift**: zero — analytical solution; no literature dispute
- **inlet_bc_developed_profile**: low — codedFixedValue uses the analytical profile directly
- **codedFixedValue_compile**: low — solved in case_025 (`docker --user $(id -u):$(id -g)` flag · re-applied here)
- **wedge_axis_discretization**: low-med — axis cell width shrinks to ~0 azimuthal extent · OpenFOAM blockMesh handles natively; cell center at r ≈ 1.05e-4 m gives analytical u-bias ~0.04% << strict 1% gate
- **codedFixedValue_radial_geometry**: med — first time computing r = sqrt(y²+z²) inside codedFixedValue (case_025 used u(y) directly · pipe needs u(r))

## §11 V-row attribution (anticipated)

Reuse from prior V64-A sub-DECs:
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse
- **V47** (incompressible inlet BC conventions) — partial reuse for codedFixedValue
- **F-NEW from case_025**:
  - F-NEW-A (codedFixedValue Docker `--user` flag) — direct reuse (same path)
  - F-NEW-C (laminar simpleFoam strict 1e-8 residual achievable on 1D-analytical canonical) — reused; expect parallel residual depth

F-NEW candidates if surfaced:
- F-NEW: OpenFOAM axisymmetric wedge blockMesh 8-vertex-with-2-coincident-pairs convention (first in repo)
- F-NEW: codedFixedValue with sqrt(y²+z²) radial computation (first in repo · case_025 used u(y) only)
- F-NEW: r-grading single-direction toward-wall simpleGrading 0.333 (first in repo · differs from case_025 bilinear-symmetric)
- F-NEW: Hagen-Poiseuille τ_w cross-check strict gate compliance (case_025 had this as informational; brief makes it strict here)

## §12 4Q gate

- **Q1 LLM-offline**: `env -i HOME PATH source ~/OpenFOAM-v2512/etc/bashrc && blockMesh && simpleFoam` re-runnable inside Docker container (mirrors case_025 path)
- **Q2 artifacts**: 5 dict files (blockMeshDict + controlDict + fvSchemes + fvSolution + sampleDict) + 2 constant/ (transportProperties + turbulenceProperties laminar) + 2 0/ BC files (U codedFixedValue + p) + run log + analytical extract script + validation report + sub-DEC
- **Q3 TrustGate**: every u(r), dp/dx, τ_w cites postProcessing file row + analytical formula explicit in extract_hagen_poiseuille.py; every Δ% computed with formula trace
- **Q4 advisor-only**: NO advisor stack edits this sub-session (ui/backend/ untouched)
