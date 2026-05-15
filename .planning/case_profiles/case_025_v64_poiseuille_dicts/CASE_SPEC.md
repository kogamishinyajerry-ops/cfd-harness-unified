# case_025 · Plane Poiseuille Channel · CASE_SPEC

> V64-A Tier 2 · M-V64A-VAL-FULL-POISEUILLE · simplest possible CFD validation
> Parent DEC: DEC-V64-A-charter
> Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-POISEUILLE (in flight · B67 dispatch)

## §1 Strategic context

V64-A Tier 2 attempts to date (post-B66 reconcile · commit 1f8850a):

| Attempt | Case | Verdict | Strongest issue |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup |
| #3 (B63) | case_021 NASA TMR flat plate | PARTIAL (soft) | residuals plateau 3-5e-5 |
| #4 (B65) | case_024 lid-driven cavity Re=1000 | first 17/17 strict PASS in arc; v 4.10% | 129×129 uniform grid floor |
| #5 (B66) | case_022 Driver-Seegmiller BFS | PARTIAL · x_R/h 5.44 vs 6.26 | uniform inlet δ/h gap |
| **#6 (B67) · this CASE_SPEC** | **case_025 plane Poiseuille** | TBD | **analytical 1D · no transition / no rotation / no shock / no separation** |

**Why Poiseuille after 5 PARTIAL attempts**:
- 4/4 prior PARTIAL pattern (B56-B65) plus B66's PARTIAL points to "real-physics-complexity-driven failure modes"
- Poiseuille is THE simplest analytical canonical · zero physics complexity
- If Poiseuille STRICT-PASSES → confirms the V64-A pipeline (mesh + solver + extraction + comparison) is sound; PARTIAL track is geometry/physics-specific, not infrastructure-specific
- If Poiseuille also PARTIAL → reveals systematic infrastructure issue (rare; would be a major finding)
- Per briefing: standalone strict PASS = Done #1 0→1/3; cavity-v2 + Poiseuille both strict PASS = 0→2/3

## §2 Canonical selection · Plane Poiseuille (Schlichting §5.1.1)

**Source**: Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed. Springer, §5.1.1 "Plane Channel Flow"; also White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.3.1.

**Analytical solution** (steady · incompressible · Newtonian · 2D · no body force):

```
u(y) = (3/2) · u_mean · (1 - (y/H)²)        for y ∈ [-H, +H]
```

with derived quantities:

```
u_max     = u(0)        = (3/2) · u_mean              [centerline]
dp/dx     = -3·μ·u_mean / H²                          [streamwise pressure gradient]
τ_wall    = μ · |du/dy|_{y=±H} = 2·μ·u_mean / H       [wall shear stress]
Re_h      = ρ · u_mean · (2H) / μ                     [Reynolds number based on hydraulic dia]
```

In kinematic OpenFOAM convention (p_kin = p/ρ; ρ absorbed into ν=μ/ρ):

```
dp_kin/dx = -3·ν·u_mean / H²                          [kinematic pressure gradient]
τ_kin     = 2·ν·u_mean / H                            [kinematic wall shear stress]
```

**Rationale (vs candidate B Couette / candidate C circular Poiseuille)**:
1. **Geometric simplicity**: 2D channel · 1 hex block · 4 named patches · zero geometric ambiguity
2. **Analytical exactness**: closed-form u(y) is exact to machine precision · no experimental uncertainty band
3. **Computational triviality**: ≤20k cells suffices; ≤1000 simpleFoam iter to converge
4. **Pure diagnostic**: any deviation isolates discretization / BC / solver error · NO physics ambiguity
5. **Universal benchmark**: standard test in every CFD textbook · zero literature dispute on canonical values

## §3 Geometry

Single 2D rectangular channel:
- Channel half-height **H = 0.01 m** (full height 2H = 0.02 m = 20 mm)
- Channel length **L = 0.5 m** = **50·H** (≥ 3·L_entrance for fully-developed exit verification)
- 2D wedge thickness z_thick = 0.001 m (single empty-patch cell layer)

Coordinate origin: channel-inlet bottom-front corner (x=0, y=-H, z=0). Channel centerline at y=0.

## §4 Inflow conditions

| Variable | Value | Source |
|---|---|---|
| u_mean (mean over y) | 0.1 m/s | per briefing target |
| u_max (centerline) | 0.15 m/s | = (3/2)·u_mean (analytical) |
| ρ (effective) | 1.0 kg/m³ | normalized incompressible |
| ν | 1.5e-5 m²/s | per briefing (air @ 15°C) |
| Re_h = u_mean·(2H)/ν | 0.1·0.02/1.5e-5 = **133.33** | calculated · deep laminar |
| dp/dx (kinematic) | -3·ν·u_mean/H² = **-0.045 m²/s²/m** | analytical · gives Δp_kin total over L = -0.0225 m²/s² |
| τ_wall (kinematic) | 2·ν·u_mean/H = **3.0e-4 m²/s²** | analytical |

**Inlet BC**: `codedFixedValue` parabolic profile u(y) = u_max·(1 - (y/H)²), v=w=0. The inlet IS the analytical solution.

**Outlet BC**: p = 0 fixedValue (gauge zero), U zeroGradient (allows flow to extrapolate naturally).

**Wall BC**: noSlip on both top and bottom (y=±H).

**Front/back BC**: empty (2D wedge).

## §5 17+ y-point query at exit station

Sample line at x_exit = 0.5 m (channel outlet just upstream of fixed-p outlet face), spanning y ∈ [-H, +H]:

```
exitProfile
{
    type        midPoint;
    axis        y;
    start       (0.4995 -0.01 0.0005);
    end         (0.4995 +0.01 0.0005);
}
```

With ny=40 cells (y-grading symmetric 3:1 toward both walls) → midPoint sampling returns 40 cell-centered y-values → 40 ≥ 17+ ✓

Sample line at mid-channel (x=0.25 m) for fully-developed verification:

```
midProfile
{
    type        midPoint;
    axis        y;
    start       (0.25 -0.01 0.0005);
    end         (0.25 +0.01 0.0005);
}
```

Sample line along centerline for dp/dx extraction:

```
centerlinePressure
{
    type        midPoint;
    axis        x;
    start       (0.05 0.0 0.0005);
    end         (0.45 0.0 0.0005);
}
```

dp/dx extracted via linear fit p(x) over x ∈ [0.05, 0.45] (excludes inlet/outlet boundary perturbations).

## §6 Canonical comparison points

For each of N≥17 y-values y_i sampled at x=0.4995:

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| u(y_i) | (3/2)·0.1·(1 - (y_i/0.01)²) | from postProcessing/sets | (u_sampled - u_analytical) / u_max × 100% |

For dp/dx:

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| dp/dx (kinematic) | -0.045 m²/s²/m | linear fit over x ∈ [0.05, 0.45] | (slope_fit - slope_analytical) / slope_analytical × 100% |

For τ_wall (cross-check):

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| τ_wall (kinematic) | 3.0e-4 m²/s² | from wallShearStress functionObject | (τ_sampled - τ_analytical) / τ_analytical × 100% |

## §7 Strict FULL gate (per briefing)

- **max |Δu| < 1%** across 17+ y-points at exit station (normalized by u_max = 0.15 m/s)
- **|Δ dp/dx| < 1%** vs analytical -0.045 m²/s²/m
- **residuals 4/4 < 1e-8** (laminar regime → fields are p, Ux, Uy + continuity = 4 quantities; matches case_024 cavity convention)

**Marginal**: max |Δu| ∈ [1%, 3%] · document & user ratifies
**PARTIAL**: max |Δu| > 3% OR residuals not converged OR setup unfeasible

## §8 Solver setup

- Solver: `simpleFoam` (incompressible steady-state)
- Turbulence: **laminar** (Re_h = 133 deep laminar · no model required)
- Schemes: 2nd-order bounded upwind for div(phi,U); Gauss linear for grad/laplacian
- p-solver: GAMG + GaussSeidel
- U-solver: PBiCGStab + DILU
- URF: p = 0.30, U = 0.70 (standard NASA TMR set)
- Convergence: residualControl 1e-8 on all 4 quantities; maxIter 5000

## §9 Mesh design

Single hex block:

| Block | Region | nx × ny × nz | Grading (x, y, z) | Cells |
|---|---|---|---|---|
| 1 | full channel (x ∈ [0, 0.5], y ∈ [-H, +H]) | 500 × 40 × 1 | (1, bilinear-3, 1) | 20,000 |

- x: uniform · Δx = 1e-3 m
- y bilinear: simpleGrading ((0.5 0.5 3) (0.5 0.5 0.333)) · finer near both walls, coarser at centerline; 3:1 ratio
  - y_first ≈ 2.7e-4 m at wall, y_last ≈ 8.1e-4 m at centerline
- z: 1 (uniform single layer, empty patches)

Aspect ratio:
- max cell at wall: Δx / y_first ≈ 1e-3 / 2.7e-4 ≈ 3.7 (acceptable)
- max cell at centerline: Δx / y_last ≈ 1e-3 / 8.1e-4 ≈ 1.23 (excellent)

## §10 Risk flags

- **executable_smoke_test**: med — first Poiseuille substrate, full local invocation in RUN_LOG.md
- **solver_stability_on_novel_geometry**: low — plane Poiseuille is THE textbook canonical
- **canonical_reference_drift**: zero — analytical solution; no literature dispute
- **inlet_bc_developed_profile**: low — codedFixedValue uses the analytical profile directly
- **codedFixedValue_compile**: med — if v2512 dynamic-code compile fails, fall back to uniform inlet + sample at x = 0.5 (which is 3.1·L_entrance · fully-developed)

## §11 V-row attribution (anticipated)

Reuse from prior V64-A sub-DECs:
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse
- **V47** (incompressible inlet BC conventions) — partial reuse for codedFixedValue patch convention

F-NEW candidates if surfaced:
- F-NEW: codedFixedValue v2512 compile path on macOS (host-OpenFOAM-v2512)
- F-NEW: simpleGrading bilinear convention symmetric-grading single-block (different from BFS multi-region case_022)
- F-NEW: residualControl 1e-8 on laminar plane Poiseuille (vs 1e-7 in cavity case_024) — actual residual depth attainable on simplest canonical

## §12 4Q gate

- **Q1 LLM-offline**: env -i HOME PATH source ~/OpenFOAM-v2512/etc/bashrc && blockMesh && simpleFoam re-runnable
- **Q2 artifacts**: 5 dict files (blockMeshDict + controlDict + fvSchemes + fvSolution + sampleDict) + transportProperties + turbulenceProperties + 2 BC files (U, p) + run log + analytical script + validation report + sub-DEC
- **Q3 TrustGate**: every u(y) value cites postProcessing file row + analytical formula explicit; every Δ% computed in extract_poiseuille.py with formula trace
- **Q4 advisor-only**: NO advisor stack edits this sub-session (ui/backend/ untouched)
