# case_021 · NASA TMR Turbulent Flat Plate · CASE_SPEC

> V64-A Tier 2 · M-V64A-VAL-FULL-3-INCOMP · 3rd FULL attempt
> Parent DEC: DEC-V64-A-charter
> Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP

## §1 Strategic context

V64-A Tier 1 / Tier 2 progress per ARC-GOAL d8a22d1:

| Done | Status | Distance |
|---|---|---|
| #1 FULL validation reports | 0 / 3 strict | -3 |
| #2 Canonical literature comparisons | 2 / 3 (NREL Seq S + Schmitt-Charpin AGARD-AR-138) | -1 |
| #3 Mesh convergence study | ✓ MET (B58 case_004) | — |
| #5 V63-A carry-over closure | ✓ MET (4/4) | — |

Three FULL attempts to date all PARTIAL'd:
- **B56/B57 case_004 NREL Phase VI** — case-spec bug (blade fed feathered, not axial) — multi-day blade CAD repair queued
- **B53/B61 case_016 multi-window** — thermo-FPE crash @ rhoPimpleFoam — Layer 3 PIMPLE p-coupling axes revealed after thermo fix
- **B59/B61 case_006 ONERA M6** — rhoSimpleFoam solver-class incompat with shock startup — needs rhoCentralFoam transient

**Pivot rationale** (post-B61 retro): three different compressible/rotating axes have each shown multi-layer engineering depth incompatible with single-session FULL closure. V64-A strategic move = bypass compressible gating entirely via **incompressible canonical** where the AI-advisor / mesh / BC / solver stack is mature and the comparison reference is unambiguous.

## §2 Canonical selection · NASA TMR Turbulent Flat Plate

**Rationale (vs candidate B Driver-Seegmiller BFS / candidate C Moser DNS channel)**:

1. **Cleanest geometry**: 2D flat plate has zero geometric ambiguity. No CAD bug exposure (case_004 lesson). No solver-class compatibility risk (case_006 lesson).
2. **5 query stations vs 1**: Cf at Re_x = 2e6, 4e6, 6e6, 8e6, 9.58e6 → 5-row Δ table per V63 close §3.1 cross-reference precedent. BFS gives one scalar (x_R/h) plus profiles; less canonical statistics for the cost.
3. **Reference availability**: Prandtl-Schlichting 1/7-power law eq 21.11 (analytical · primary) AND Coles & Wadcock 1979 + Mansour-Kim-Moin 1988 DNS (experimental · secondary). Both NASA TMR-website tabulated.
4. **Solver stack maturity**: simpleFoam + kOmegaSST + bounded upwind 2nd-order is the most-validated OF incompressible RANS path. Zero thermo-physics layer (transportProperties Newtonian only).
5. **Reference grid matches briefing**: NASA TMR fine grid = 545×385 = 209,825 cells (≈210k · within briefing 200k-800k window).

## §3 Geometry

- Domain: x ∈ [0, 2.0] m × y ∈ [0, 0.3] m × z ∈ [0, dz] (single-layer wedge for 2D)
- Plate: y=0, x ∈ [0, 2] m, no-slip wall
- Inlet: x=0 (also plate leading edge — no upstream development region; canonical BCs developed at LE)
- Outlet: x=2 (zeroGradient)
- Top: y=0.3 (freestream / slip · 0.15× plate length to avoid blockage; matches NASA TMR `y_max/L = 0.15`)
- Front/back (z): `empty` patches (2D)

No STL · blockMesh-native quadrilateral. **No `parts_manifest.yaml`** required (no body-class faces; geometry encoded in blockMeshDict). This is canonical-by-construction.

## §4 Inflow conditions

- U_inf = 70 m/s (x-direction)
- ρ = 1.225 kg/m³
- ν = 1.4612e-5 m²/s (incompressible Newtonian air @ 15 °C, p_atm)
- Re_x at x = 2 m: 70 × 2 / 1.4612e-5 = **9.58 × 10⁶** ≈ canonical "Re_x = 1e7 at trailing edge" within 4.2% (acknowledged honest deviation — not cherry-picked to make Δ look small)
- Turbulence inlet: I = 0.5%, L = 0.05 m
  - k_inlet = 1.5 × (0.005 × 70)² = **0.1838 m²/s²**
  - ω_inlet = √k / (C_μ^0.25 × L) = 0.4287 / (0.5477 × 0.05) = **15.66 1/s**
  - nut_inlet = computed (compute via initial nut field zero; kOmegaSST will populate)

## §5 Five query stations (Re_x targets)

| Station | Target Re_x | x [m] | Notes |
|---|---|---|---|
| S1 | 2.0 × 10⁶ | 0.418 | Coles-Wadcock primary |
| S2 | 4.0 × 10⁶ | 0.835 | Coles-Wadcock primary |
| S3 | 6.0 × 10⁶ | 1.253 | Coles-Wadcock primary |
| S4 | 8.0 × 10⁶ | 1.670 | Coles-Wadcock primary |
| S5 | 9.58 × 10⁶ | 2.000 | Trailing edge (honest Re_x_max, near canonical 1e7) |

## §6 Canonical Cf reference (Prandtl-Schlichting 1/7-power · eq 21.11)

```
Cf_x = 0.0592 × Re_x^(-1/5)
```

| Station | Re_x | Cf_canonical |
|---|---|---|
| S1 | 2.0e6 | 0.003270 |
| S2 | 4.0e6 | 0.002846 |
| S3 | 6.0e6 | 0.002643 |
| S4 | 8.0e6 | 0.002477 |
| S5 | 9.58e6 | 0.002382 |

**FULL tolerance** (per briefing): Δ% < 5% on 5/5 stations. Marginal: 5-10% on any. PARTIAL: ≥10% on any OR residual not converged.

Secondary reference: Coles & Wadcock 1979 (experimental momentum-thickness Re_θ vs Re_x) for plausibility cross-check at Re_x ≈ 5e6.

## §7 Solver setup

- Solver: `simpleFoam` (incompressible steady RANS · canonical for ZPG turbulent BL)
- Turbulence: kOmegaSST (RAS)
- Schemes: `bounded Gauss upwind` div terms (steady-state safe), Gauss linear corrected for laplacians
- p-solver: GAMG + GaussSeidel smoother
- U / k / ω solvers: PBiCGStab + DILU preconditioner
- URF: p = 0.30, U = 0.70, k = 0.50, ω = 0.50 (NASA TMR canonical URF set)
- Convergence: residualControl 1e-5 on all 6 (p, Ux, Uy, k, ω, plus continuity inferred); maxIter 5000

## §8 Risk flags

- **mesh_density_on_domain_change**: low — fixed canonical domain, no prior version
- **solver_stability_on_novel_geometry**: low — kOmegaSST + ZPG TBL is THE most-validated topology
- **executable_smoke_test**: med — blockMesh + simpleFoam executed via Docker container; mitigation = full run log in Commit 3
- **canonical_reference_drift**: low — Prandtl-Schlichting eq 21.11 is textbook analytic, zero ambiguity

## §9 V-row attribution (anticipated)

Reuse from prior V64-A sub-DECs:
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — expected to firm
- **V47** (NREL UAE-style BC documentation conventions) — may not apply (no rotation)
- **V94** (substrate-bridge manifest mapping) — may apply if parts_manifest synthesis attempted

F-NEW candidates if surfaced:
- F-NEW: kOmegaSST inlet ω scaling convention drift (C_μ^0.25 vs C_μ^0.5)
- F-NEW: 2D wedge empty-patch z-thickness sensitivity
- F-NEW: y+-1 simpleGrading large-ratio (>4000) numerical stability

## §10 4Q gate

- **Q1 LLM-offline**: env -i HOME PATH .venv/bin/python re-runnable via Docker `docker exec dreamy_hoover bash -c 'cd /case && simpleFoam'`
- **Q2 artifacts**: 11+ dict files + RUN_LOG.md + validation report + sub-DEC
- **Q3 TrustGate**: every Cf value cites `postProcessing/wallShearStress/<time>/wallShearStress.dat` row + canonical Prandtl-Schlichting eq 21.11 with calculation shown
- **Q4 advisor-only**: NO advisor stack edits this sub-session
