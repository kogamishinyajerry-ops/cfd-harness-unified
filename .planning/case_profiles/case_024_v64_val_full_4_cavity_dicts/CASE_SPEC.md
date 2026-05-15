# case_024 · Lid-driven Cavity · CASE_SPEC

**Canonical reference**: Ghia, Ghia & Shin (1982) "High-Re Solutions for Incompressible Flow Using the Navier-Stokes Equations and a Multigrid Method", *Journal of Computational Physics* **48**, 387-411. Tables I/II/III provide the canonical DNS u/v centerline values at Re=100/400/1000/3200/5000/7500/10000.

This sub-DEC validates against Re ∈ {100, 400, 1000} only — the three lowest Re cases where laminar flow assumption holds without question. Higher Re (≥3200) requires very fine grids and longer convergence and was deferred per briefing scope.

---

## §1 Physical setup

- **Domain**: 2D unit square cavity, x ∈ [0, 1] m, y ∈ [0, 1] m
- **Depth (z)**: 0.01 m single-layer (`empty` BC on frontAndBack — 2D)
- **Lid (y=1)**: moving wall, tangential velocity U_lid = (1, 0, 0) m/s
- **Bottom (y=0) + Left (x=0) + Right (x=1)**: no-slip walls (U=0)
- **Front (z=0) + Back (z=0.01)**: empty (2D constraint)
- **Pressure reference**: cell index 0, p_ref = 0 (enforced via `pRefCell` / `pRefValue` in fvSolution)

## §2 Re scaling (3 query points)

| Case | Re_L | U_lid [m/s] | L [m] | ν [m²/s] | Regime |
|---|---|---|---|---|---|
| case_re100  |   100 | 1.0 | 1.0 | **0.01**    | deep laminar, single primary vortex + 2 small corner eddies |
| case_re400  |   400 | 1.0 | 1.0 | **0.0025**  | laminar, secondary corner vortices growing |
| case_re1000 |  1000 | 1.0 | 1.0 | **0.001**   | laminar, near-transition (Re_crit ≈ 7,500 per Auteri et al. 2002) |

Re = U_lid · L / ν · All cases incompressible, isothermal, no body force.

## §3 Mesh (Ghia canonical 129×129)

- Single hex block: 129 × 129 × 1 cells = **16,641 hexahedra**
- Uniform spacing (`simpleGrading (1 1 1)`) — matches Ghia 1982 §3 baseline grid
- Cell size: Δx = Δy = 1/129 ≈ 7.752e-3 m
- z-thickness: 0.01 m single-layer (front/back `empty`)
- Allowed checkMesh signature: max non-orthogonality ≤ 5° (uniform Cartesian grid), max skewness ≤ 0.05

> Higher-resolution 257×257 was considered but rejected — Ghia's reference table values are at 129×129 nominal resolution; using a finer grid introduces a discretization-bias confound vs the published canonical values. Match the reference grid.

## §4 Numerical scheme set

| Component | Choice | Justification |
|---|---|---|
| ddt | `steadyState` | simpleFoam is steady RANS solver |
| div(phi, U) | `bounded Gauss linearUpwindV grad(U)` | 2nd-order upwind, bounded for stability |
| grad(default) | `Gauss linear` | 2nd-order central |
| grad(U) | `cellLimited Gauss linear 1` | limited gradient for high-Re |
| laplacian | `Gauss linear corrected` | 2nd-order central + non-ortho correction |
| sn-grad | `corrected` | non-ortho correction |
| solver p | GAMG + GaussSeidel, tol 1e-8 | matches NASA TMR canonical p solver |
| solver U | PBiCGStab + DILU, tol 1e-8 | matches NASA TMR canonical U solver |
| URF (p, U) | 0.30, 0.70 | NASA TMR canonical SIMPLE relaxation |
| residualControl | 1e-7 (strict per briefing) | strict FULL gate: deep laminar convergence |

## §5 Sandbox layout

```
~/Desktop/case_024_lid_driven_cavity/
├── case_re100/
│   ├── 0/{U,p}           (BC, shared template)
│   ├── constant/
│   │   ├── transportProperties     (ν=0.01)
│   │   └── turbulenceProperties    (laminar)
│   └── system/{blockMeshDict, controlDict, fvSchemes, fvSolution,
│               decomposeParDict, sampleDict}
├── case_re400/                      (same, ν=0.0025)
└── case_re1000/                     (same, ν=0.001)
```

All three cases share identical mesh, BCs, schemes, and solver tolerances. **Only `constant/transportProperties` differs across cases.** This makes case-to-case comparison clean — any Δ vs Ghia reference is attributable to Re alone, not to mesh or scheme bias.

## §6 Sampling strategy

`system/sampleDict` defines two line probes per case:

- `u_vertical_centerline`: x=0.5, y ∈ [0, 1], z=0.005 — extracts u-velocity along Ghia's Table I axis
- `v_horizontal_centerline`: y=0.5, x ∈ [0, 1], z=0.005 — extracts v-velocity along Ghia's Table II axis

Sampling resolution: 1001 points per line (full-resolution OpenFOAM `uniform` interpolation), then post-processed to Ghia's 17 canonical y/L (or x/L) points via linear interpolation.

## §7 Strict FULL gate (per briefing reverse condition)

3/3 Re cases must satisfy ALL THREE:

1. **max |Δ% u-centerline|** across 17 Ghia points < **3%** (strict)
2. **max |Δ% v-centerline|** across 17 Ghia points < **3%** (strict)
3. **residuals**: 4/4 fields < **1e-7** at final iter (laminar field count: p, Ux, Uy, continuity)

Verdict scale:
- **FULL**: 3/3 Re cases pass all 3 gates → Done #1 advances 0/3 → 1/3 strict
- **marginal**: 2/3 cases pass; 1 case just outside (3-5% Δ or residuals plateau 1e-6 to 1e-7) → user裁决 promote OR PARTIAL with disclosure
- **PARTIAL**: ≤1/3 cases pass OR mesh fail OR solver divergence → Done #1 stays 0/3

## §8 Reverse-condition transparency

- All 17 Ghia points reported (not 5 cherry-picked) — see validation report Δ table
- ν per case explicitly tabled
- Final residuals per case explicitly tabled
- Ghia 1982 Table I/II values embedded verbatim from JCP 48:387-411
- max |Δ%| computed honestly across ALL 17 points (no point-skipping)
- Done #1 advancement gated on STRICT gate only; partial-success does NOT count toward Done #1

## §9 Canonical Ghia 1982 reference values (Tables I & II)

### Table I — u-velocity along vertical centerline at x=0.5

| y/L | Re=100 | Re=400 | Re=1000 |
|---:|---:|---:|---:|
| 1.0000 |  1.00000 |  1.00000 |  1.00000 |
| 0.9766 |  0.84123 |  0.75837 |  0.65928 |
| 0.9688 |  0.78871 |  0.68439 |  0.57492 |
| 0.9609 |  0.73722 |  0.61756 |  0.51117 |
| 0.9531 |  0.68717 |  0.55892 |  0.46604 |
| 0.8516 |  0.23151 |  0.29093 |  0.33304 |
| 0.7344 |  0.00332 |  0.16256 |  0.18719 |
| 0.6172 | -0.13641 |  0.02135 |  0.05702 |
| 0.5000 | -0.20581 | -0.11477 | -0.06080 |
| 0.4531 | -0.21090 | -0.17119 | -0.10648 |
| 0.2813 | -0.15662 | -0.32726 | -0.27805 |
| 0.1719 | -0.10150 | -0.24299 | -0.38289 |
| 0.1016 | -0.06434 | -0.14612 | -0.29730 |
| 0.0703 | -0.04775 | -0.10338 | -0.22220 |
| 0.0625 | -0.04192 | -0.09266 | -0.20196 |
| 0.0547 | -0.03717 | -0.08186 | -0.18109 |
| 0.0000 |  0.00000 |  0.00000 |  0.00000 |

### Table II — v-velocity along horizontal centerline at y=0.5

| x/L | Re=100 | Re=400 | Re=1000 |
|---:|---:|---:|---:|
| 1.0000 |  0.00000 |  0.00000 |  0.00000 |
| 0.9688 | -0.05906 | -0.12146 | -0.21388 |
| 0.9609 | -0.07391 | -0.15663 | -0.27669 |
| 0.9531 | -0.08864 | -0.19254 | -0.33714 |
| 0.9453 | -0.10313 | -0.22847 | -0.39188 |
| 0.9063 | -0.16914 | -0.23827 | -0.51550 |
| 0.8594 | -0.22445 | -0.44993 | -0.42665 |
| 0.8047 | -0.24533 | -0.38598 | -0.31966 |
| 0.5000 |  0.05454 |  0.05186 |  0.02526 |
| 0.2344 |  0.17527 |  0.30174 |  0.32235 |
| 0.2266 |  0.17507 |  0.30203 |  0.33075 |
| 0.1563 |  0.16077 |  0.28124 |  0.37095 |
| 0.0938 |  0.12317 |  0.22965 |  0.32627 |
| 0.0781 |  0.10890 |  0.20920 |  0.30353 |
| 0.0703 |  0.10091 |  0.19713 |  0.29012 |
| 0.0625 |  0.09233 |  0.18360 |  0.27485 |
| 0.0000 |  0.00000 |  0.00000 |  0.00000 |

**Source verbatim**: Ghia U., Ghia K.N., Shin C.T. (1982) JCP 48:387-411, Tables I & II pp. 398-399.

## §10 Strategic context

Per briefing: V64-A 4th FULL attempt. Prior 3 attempts (case_004 NREL Phase VI Seq S / case_006 ONERA M6 / case_021 NASA TMR flat plate) yielded 3 PARTIAL verdicts. Cavity is the **simplest possible canonical** in CFD — if FULL is achievable anywhere in V64-A, it's here. If cavity 0/3 → still PARTIAL after Ghia comparison, that's a strong signal about the strict-3% gate's calibration vs OpenFOAM's discretization floor on uniform 129×129, not about solver bugs.
