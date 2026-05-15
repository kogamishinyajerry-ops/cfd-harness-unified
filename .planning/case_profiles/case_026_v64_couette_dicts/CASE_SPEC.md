# case_026 · Plane Couette Channel · CASE_SPEC

> V64-A Tier 2 · M-V64A-VAL-FULL-COUETTE · 1D LINEAR analytical canonical · pure shear-driven (no pressure gradient)
> Parent DEC: DEC-V64-A-charter
> Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-COUETTE (in flight · B69 dispatch · companion to B68 Poiseuille FULL)

## §1 Strategic context

V64-A Tier 2 attempts to date (post-B68 reconcile · commit 83f544b):

| Attempt | Case | Verdict | Strongest issue |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup |
| #3 (B63) | case_021 NASA TMR flat plate | PARTIAL (soft) | residuals plateau 3-5e-5 |
| #4 (B65) | case_024 lid-driven cavity Re=1000 | first 17/17 strict PASS in arc; v 4.10% | 129×129 uniform grid floor |
| #5 (B66) | case_022 Driver-Seegmiller BFS | PARTIAL · x_R/h 5.44 vs 6.26 | uniform inlet δ/h gap |
| #6 (B67) | case_025 plane Poiseuille | **FULL** strict trifecta ✓ | (none · clean) |
| **#7 (B69) · this CASE_SPEC** | **case_026 plane Couette** | TBD | **1D LINEAR · even simpler than Poiseuille** |

**Why Couette after B68 Poiseuille FULL**:
- B68 Poiseuille proved V64-A infrastructure is sound (5 prior PARTIALs were real-physics-driven)
- Couette is the natural companion canonical · 1D LINEAR (one degree simpler than parabolic) · no dp/dx
- Independent strict-PASS on Couette pushes Done #1 1/3 → 2/3 strict ✓ (per briefing reverse condition)
- Couette differs from Poiseuille in 3 axes: BC source (wall motion vs inlet pressure), pressure gradient (zero vs nonzero), profile shape (linear vs parabolic) — so it's a genuine second canonical, not a rebadge.
- Expected outcome: machine-precision strict-PASS · since the solution is degree-1 polynomial in y, 2nd-order schemes should converge to discretization-floor (typically O(1e-6) or below) trivially.

## §2 Canonical selection · Plane Couette (Schlichting §5.1.0)

**Source**: Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed. Springer, §5.1.0 "Couette Flow"; also White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.2.1.

**Analytical solution** (steady · incompressible · Newtonian · 2D · no body force · no pressure gradient · upper wall moving at U_top · lower wall stationary):

```
u(y) = U_top · y/H        for y ∈ [0, +H]    (linear · 0 at bottom, U_top at top)
```

with derived quantities:

```
du/dy     = U_top / H                                  [constant gradient · 1D linear]
dp/dx     = 0                                          [pure shear-driven · NO pressure gradient]
τ_wall    = μ · U_top / H                              [wall shear stress · same at both walls]
Re_h      = U_top · H / ν                              [Reynolds based on gap height]
```

In kinematic OpenFOAM convention (p_kin = p/ρ; ρ absorbed into ν=μ/ρ):

```
dp_kin/dx = 0                                          [zero · pure shear-driven]
τ_kin     = ν · U_top / H                              [kinematic wall shear stress]
```

**Rationale (vs candidate B Poiseuille / candidate C Couette-Poiseuille hybrid)**:
1. **Geometric simplicity**: 2D channel · 1 hex block · 4 named patches · zero geometric ambiguity (same as B68 Poiseuille)
2. **Analytical exactness**: closed-form u(y) is exact to machine precision · no experimental uncertainty band
3. **Linear profile**: degree-1 polynomial · 2nd-order linearUpwindV scheme should resolve exactly (discretization error O(machine precision) for linear field)
4. **Pure shear**: no pressure-driven mechanism · isolates wall-momentum-injection physics
5. **Companion to Poiseuille**: 3-axis distinction (BC source / dp_dx / profile shape) makes it a genuine second canonical

## §3 Geometry

Single 2D rectangular channel:
- Channel height **H = 0.01 m** (single gap from bottom y=0 to top y=H)
- Channel length **L = 0.5 m** = **50·H** (≥3·L_entrance buffer · matches B68 Poiseuille convention)
- 2D wedge thickness z_thick = 0.001 m (single empty-patch cell layer)

Coordinate origin: channel-inlet bottom-front corner (x=0, y=0, z=0). Top wall at y=H, bottom wall at y=0.

**KEY DIFFERENCE FROM B68 POISEUILLE**: gap is [0, H] not [-H, +H] — Couette has asymmetric BCs (top moving, bottom stationary) so a symmetric domain is unnatural; a single-sided [0, H] domain makes the linear profile align trivially with one wall.

## §4 Inflow conditions

| Variable | Value | Source |
|---|---|---|
| U_top (top wall velocity) | 0.1 m/s | per briefing target |
| ρ (effective) | 1.0 kg/m³ | normalized incompressible |
| ν | 1.5e-5 m²/s | per briefing (air @ 15°C) · matches B68 Poiseuille |
| Re_h = U_top·H/ν | 0.1·0.01/1.5e-5 = **66.67** | calculated · deep laminar (half of B68 Poiseuille's Re_h=133.3, since here H is gap not half-gap) |
| dp_kin/dx | **0.0 m²/s²/m** | analytical · pure shear · NO pressure gradient |
| du/dy | U_top/H = **10.0 1/s** | analytical · constant linear-profile slope |
| τ_wall (kinematic) | ν·U_top/H = 1.5e-5 · 0.1 / 0.01 = **1.5e-4 m²/s²** | analytical · same at both walls · **CORRECTED post-run** (original CASE_SPEC had 1.5e-5 · arithmetic error · forgot /H division · simpleFoam output ±1.5e-4 confirmed corrected value · see validation report §3.1) |

**Inlet BC**: `codedFixedValue` linear profile u(y) = U_top · y/H, v=w=0. The inlet IS the analytical solution.

**Outlet BC**: p = 0 fixedValue (gauge zero), U zeroGradient (matches B68 Poiseuille convention).

**Wall BC**:
- Top wall (y=H): `fixedValue uniform (U_top 0 0)` — sliding wall on stationary mesh, same convention as lid-driven cavity (case_024). Note: `movingWallVelocity` is for actual moving-mesh use; not applicable here.
- Bottom wall (y=0): `noSlip`.

**Front/back BC**: empty (2D wedge).

## §5 17+ y-point query at exit station

Sample line at x_exit = 0.5 m (channel outlet just upstream of fixed-p outlet face), spanning y ∈ [0, H]:

```
exitProfile
{
    type        midPoint;
    axis        y;
    start       (0.4995 0     0.0005);
    end         (0.4995 0.01  0.0005);
}
```

With ny=40 cells (uniform-y grading) → midPoint sampling returns 40 cell-centered y-values → 40 ≥ 17+ ✓

Sample line at mid-channel (x=0.25 m) for fully-developed verification:

```
midProfile
{
    type        midPoint;
    axis        y;
    start       (0.25 0     0.0005);
    end         (0.25 0.01  0.0005);
}
```

Sample line along centerline for dp/dx cross-check (expected ≈ 0):

```
centerlinePressure
{
    type        midPoint;
    axis        x;
    start       (0.05 0.005 0.0005);
    end         (0.45 0.005 0.0005);
}
```

dp/dx extracted via linear fit p(x) over x ∈ [0.05, 0.45] · expected slope ≈ 0 (pure shear has no streamwise pressure gradient · this is a sanity cross-check, NOT a strict trifecta gate).

## §6 Canonical comparison points

For each of N≥17 y-values y_i sampled at x=0.4995:

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| u(y_i) | 0.1 · y_i/0.01 = 10·y_i | from postProcessing/sets | (u_sampled - u_analytical) / U_top × 100% |

For τ_wall (cross-check — STRICT TRIFECTA component for this case since dp/dx is trivially zero):

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| τ_wall (kinematic) | 1.5e-5 m²/s² | from wallShearStress functionObject | (τ_sampled - τ_analytical) / τ_analytical × 100% |

For dp/dx (sanity cross-check · not in strict trifecta):

| Quantity | Canonical | Sampled | Δ% |
|---|---|---|---|
| dp/dx (kinematic) | 0.0 m²/s²/m | linear fit over x ∈ [0.05, 0.45] | abs(slope_fit) reported · expected ≈ 1e-5 numerical floor |

## §7 Strict FULL gate (per briefing)

For plane Couette, the strict trifecta is:
- **max |Δu| < 1%** across 17+ y-points at exit station (normalized by U_top = 0.1 m/s)
- **|Δ τ_w| < 1%** vs analytical ν·U_top/H = 1.5e-5 m²/s² (replaces |Δ dp/dx| since pure shear has dp/dx ≡ 0 analytically · using τ_w as the second physical observable per briefing intent)
- **residuals 4/4 < 1e-8** (laminar regime → fields are p, Ux, Uy = 3 prognostic quantities; matches B68 Poiseuille convention with field-count transparency per case_024 §2)

**Field-count transparency note** (preserved from B68 precedent): Briefing says "residuals 4/4 < 1e-8". Laminar simpleFoam has 3 prognostic fields (p, Ux, Uy) — Uz is not solved in 2D, and no k/ω. Strict gate honored via **3/3 < 1e-8** (field-count adjusted for laminar regime · NOT gate relaxed). Time-step continuity errors reported as informational.

**Strict-trifecta substitution rationale** (briefing §strict FULL gate explicitly lists `|Δ τ_w| < 1%`): The briefing's reverse condition reads "max |Δ u| < 1% AND residuals 4/4 < 1e-8 AND |Δ τ_w| < 1%" — so τ_w replaces dp/dx as the second physical observable for Couette. No relaxation; just trifecta-axis substitution natural to the canonical (pure shear = wall-momentum-injection = τ_w is THE physical observable).

**Marginal**: max |Δu| ∈ [1%, 3%] · document & user ratifies
**PARTIAL**: max |Δu| > 3% OR residuals not converged OR setup unfeasible

## §8 Solver setup

- Solver: `simpleFoam` (incompressible steady-state)
- Turbulence: **laminar** (Re_h = 66.67 deep laminar · no model required)
- Schemes: 2nd-order bounded upwind for div(phi,U); Gauss linear for grad/laplacian (identical to B68 Poiseuille fvSchemes)
- p-solver: GAMG + GaussSeidel
- U-solver: PBiCGStab + DILU
- URF: p = 0.30, U = 0.70 (NASA TMR canonical set)
- Convergence: residualControl 1e-8 on all quantities; maxIter 5000

## §9 Mesh design

Single hex block:

| Block | Region | nx × ny × nz | Grading (x, y, z) | Cells |
|---|---|---|---|---|
| 1 | full channel (x ∈ [0, 0.5], y ∈ [0, H]) | 500 × 40 × 1 | (1, 1, 1) | 20,000 |

- x: uniform · Δx = 1e-3 m
- y: **uniform** · Δy = 2.5e-4 m (NO grading — Couette has zero wall-BL gradient curvature; linear profile is uniform-resolution friendly. This is a key difference from B68 Poiseuille's 3:1 bilinear grading.)
- z: 1 (uniform single layer, empty patches)

Aspect ratio:
- max cell: Δx / Δy = 1e-3 / 2.5e-4 = 4.0 (acceptable · uniform throughout)

**Rationale for uniform y (vs B68 Poiseuille bilinear)**: For Poiseuille u(y) = (3/2)·u_mean·(1 - (y/H)²) the gradient |du/dy| = 3·u_mean·|y|/H² varies from zero at center to maximum at walls — so wall refinement helps resolve high-gradient zones. For Couette u(y) = U_top·y/H the gradient du/dy = U_top/H is CONSTANT everywhere — wall refinement provides no benefit · uniform y is the natural mesh choice.

## §10 Risk flags

- **executable_smoke_test**: med — first Couette substrate, full local invocation in RUN_LOG.md
- **solver_stability_on_novel_geometry**: low — plane Couette is THE second-simplest textbook canonical (after Poiseuille)
- **canonical_reference_drift**: zero — analytical solution; no literature dispute
- **inlet_bc_developed_profile**: low — codedFixedValue uses the analytical linear profile directly
- **sliding_top_wall_BC**: low — `fixedValue uniform (U_top 0 0)` is canonical for sliding-tangentially walls on stationary meshes (lid-driven cavity convention · case_024 used same BC type)
- **codedFixedValue_compile**: med — if v2512 dynamic-code compile fails, fall back to fixedValue uniform U=(U_top·0.5,0,0) at inlet + sample at x = 0.5 (≥3·L_entrance buffer for Re_h=66.7)

## §11 V-row attribution (anticipated)

Reuse from prior V64-A sub-DECs:
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse ✓
- **V47** (incompressible inlet BC conventions) — partial reuse for codedFixedValue patch convention
- **F-NEW-A from B68** (codedFixedValue under Docker container needs `--user` flag) — direct reuse if codedFixedValue path used

F-NEW candidates if surfaced:
- **F-NEW** (case_026): movingWallVelocity BC on 2D plane channel — first time in this repo for canonical-validation use (case_024 cavity used uniform fixedValue lid)
- **F-NEW** (case_026): linear-profile codedFixedValue analytical inlet — companion variant to B68's parabolic; same compile pattern, different code body
- **F-NEW** (case_026): uniform-y single-block simpleGrading 1 (no grading at all) on plane channel · first time in repo for laminar validation
- **F-NEW** (case_026): pure-shear-driven simpleFoam without pressure gradient — `dp/dx ≡ 0` canonical · residual behavior expectation: p field stays near machine-precision zero throughout iteration

## §12 4Q gate

- **Q1 LLM-offline**: env -i HOME PATH source ~/OpenFOAM-v2512/etc/bashrc && blockMesh && simpleFoam re-runnable (or docker-run equivalent if codedFixedValue requires Linux compile path)
- **Q2 artifacts**: 5 dict files (blockMeshDict + controlDict + fvSchemes + fvSolution + sampleDict) + transportProperties + turbulenceProperties + 2 BC files (U, p) + run log + analytical script + validation report + sub-DEC
- **Q3 TrustGate**: every u(y) value cites postProcessing file row + analytical formula explicit; every Δ% computed in extract_couette.py with formula trace
- **Q4 advisor-only**: NO advisor stack edits this sub-session (ui/backend/ untouched)
