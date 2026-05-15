# case_022 · Driver-Seegmiller Backward-Facing Step · CASE_SPEC

> V64-A Tier 2 · M-V64A-VAL-FULL-5-BFS · 5th FULL attempt
> Parent DEC: DEC-V64-A-charter
> Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS

## §1 Strategic context

V64-A Tier 1 / Tier 2 progress (per ARC-GOAL post-B64 reconcile · commit 1aab3c8):

| Done | Status | Distance |
|---|---|---|
| #1 FULL validation reports | 0 / 3 strict | -3 |
| #2 Canonical literature comparisons | 3 / 3 ✓ MET (NREL Seq S + Schmitt-Charpin AGARD-AR-138 + Prandtl-Schlichting + Schultz-Grunow) | — |
| #3 Mesh convergence study | ✓ MET (B58 case_004) | — |
| #5 V63-A carry-over closure | ✓ MET (4/4) | — |

Four FULL attempts to date all PARTIAL/marginal:
- **B56/B57 case_004 NREL Phase VI** — blade CAD bug → multi-day repair
- **B53/B61 case_016 multi-window** — thermo-FPE crash + PIMPLE coupling axes
- **B59/B61 case_006 ONERA M6** — rhoSimpleFoam shock startup incompat
- **B63 case_021 NASA TMR flat plate** — PARTIAL (soft) · 4/5 residuals plateau'd ~3-5e-5

**Cross-class pivot** (post-B63 retro · 2026-05-15): incompressible canonical SUCCEEDED on physics + Cf comparison (Done #2 → 3/3 ✓ MET) but residuals plateau prevented strict FULL. Move to a SECOND incompressible canonical to test whether the residual-plateau pattern is solver-specific or geometry-specific:
- case_021 = ZPG turbulent BL (closed-mode, smooth-wall, attached flow)
- case_022 = backward-facing step (open-mode, sharp corner, **separation/reattachment**)

If both canonicals plateau at same magnitude → systematic kOmegaSST + bounded-upwind convergence floor.
If case_022 strict-converges → case_021 had geometry-specific extreme aspect-ratio at TE corner cell.

Cross-validation with **B65 lid-driven cavity (laminar closed-flow)**:
- Cavity = closed-flow laminar canonical
- BFS = open-flow turbulent separation/reattachment canonical
- Both NO compressibility · NO transition · NO rotor · NO blade CAD
- If both PASS → Done #1 0→2/3 strict (large advancement)

## §2 Canonical selection · Driver-Seegmiller 1985 BFS

**Source**: Driver, D.M. & Seegmiller, H.L. (1985). "Features of a Reattaching Turbulent Shear Layer in Divergent Channel Flow." NASA TM 86658 (also AIAA Journal Vol 23 No 2 pp 163-171 February 1985).

**Rationale (vs candidate B Vogel-Eaton BFS / candidate C Le-Moin-Kim DNS BFS)**:

1. **Cleanest geometry**: 2D BFS — minimal geometric ambiguity. Expansion ratio 1.125 is sufficiently small that streamwise pressure-recovery is well-defined.
2. **Multiple comparison metrics**: x_R/h (scalar) + Cp(x) (5 stations) + Cf(x) (5 stations) = 11 data points, more than case_021's 5.
3. **Experimental DB availability**: Driver-Seegmiller is THE canonical reference in NASA TMR validation manual for separation/reattachment; ERCOFTAC test case 30.
4. **Solver stack maturity**: simpleFoam + kOmegaSST is widely benchmarked on this exact case (Menter 1992 paper used BFS as primary validation).
5. **Reattachment is sensitive to BL state**: x_R/h is THE strictest separation/reattachment validation metric. Catches BL-state, mesh-density, and turbulence-model effects in one number.

## §3 Geometry

Driver-Seegmiller 1985 nominal dimensions (NASA TM 86658, p. 4):
- Step height h = 0.0127 m (12.7 mm = 0.5 inch)
- Inlet channel height H_in = 8·h = 0.1016 m (101.6 mm)
- Downstream channel height H_in + h = 9·h = 0.1143 m (114.3 mm)
- Expansion ratio ER = (H_in + h) / H_in = 1.125
- Test section downstream length: 20·h = 0.254 m (canonical x_R coverage = ~30% domain at strict tolerance)

**Inlet section (this substrate)**: **20·h = 0.254 m** (doubled from briefing's 10·h per reverse-condition "长 inlet section" sanction · honest BL pre-step δ/h ≈ 0.4 vs canonical 1.5 — see §8)

Total domain:
- x ∈ [0, 0.508 m] = 40·h streamwise (20·h inlet + 20·h downstream)
- y ∈ [0, 0.1143 m] = 9·h vertical (post-step) or [h, 0.1143] = 8·h (pre-step)
- z ∈ [0, 0.01 m] = single-layer 2D wedge (empty patches)

Coordinate origin: step bottom-front corner (canonical x_step = 0.254 m, y_step = 0).

## §4 Inflow conditions

| Variable | Value | Source |
|---|---|---|
| U_ref | 44.2 m/s | Driver-Seegmiller 1985, p. 5 |
| ρ | 1.0 kg/m³ | normalized incompressible |
| ν | 1.5e-5 m²/s | air @ 15 °C |
| Re_h = U·h/ν | 37,419 ≈ **37,500** | per briefing target |
| Inlet turbulence I | 0.5% | per briefing |
| Inlet length scale L_t | h/10 = 1.27e-3 m | per briefing |
| k_inlet = 1.5·(I·U)² | 1.5·(0.005·44.2)² = **0.07326 m²/s²** | calculated |
| ω_inlet = √k / (C_μ^0.25 · L_t) | √0.07326 / (0.5477·1.27e-3) = **389.1 1/s** | C_μ=0.09 convention |

**Honest deviation from canonical** (per briefing reverse condition):
- Canonical Driver-Seegmiller had inlet BL with δ/h ≈ 1.5 (thick, fully-developed)
- Reproducing exactly requires L_dev > 100·h with codedFixedValue or fixedProfile BC (BC complexity overshoot)
- This substrate uses **uniform inlet + 20·h inlet section**
- Expected pre-step BL δ/h ≈ 0.4-0.5 (from Schlichting 1/7-power with L_dev = 0.254 m)
- **x_R/h sensitivity**: literature shows thinner inlet BL → smaller x_R/h. Expected actual x_R/h ≈ 5.4-6.0
- This is documented honestly; not cherry-picked to satisfy gate

## §5 Five query stations (downstream wall, x/h relative to step)

| Station | x/h | x_absolute [m] | Driver-Seegmiller reference figure |
|---|---|---|---|
| S1 | 1.0 | 0.2667 | Fig 8 Cp & Fig 9 Cf |
| S2 | 4.0 | 0.3048 | Fig 8 Cp & Fig 9 Cf |
| S3 | 8.0 | 0.3556 | Fig 8 Cp & Fig 9 Cf |
| S4 | 12.0 | 0.4064 | Fig 8 Cp & Fig 9 Cf (~ near reattachment) |
| S5 | 16.0 | 0.4572 | Fig 8 Cp & Fig 9 Cf (post-reattachment) |

x_absolute = x_step + (x/h) · h = 0.254 + (x/h) · 0.0127

## §6 Canonical comparison data (Driver-Seegmiller 1985)

**Reattachment length** (NASA TM 86658 Fig 7):
- x_R/h = **6.26 ± 0.10** (experimental uncertainty band)

**Cp on downstream wall** (NASA TM 86658 Fig 8, digitized from text values):
- x/h = 1:  Cp ≈ **-0.10** (just downstream of step, low pressure)
- x/h = 4:  Cp ≈ **-0.05**
- x/h = 8:  Cp ≈ **+0.08** (recovery onset)
- x/h = 12: Cp ≈ **+0.15** (near reattachment)
- x/h = 16: Cp ≈ **+0.20** (downstream recovery)

Driver-Seegmiller definition: Cp = (p - p_ref) / (0.5·ρ·U_ref²), p_ref taken just upstream of step.

**Cf on downstream wall** (NASA TM 86658 Fig 9):
- x/h = 1:  Cf ≈ **-0.0010** (reverse flow, negative)
- x/h = 4:  Cf ≈ **-0.0018** (peak reverse flow)
- x/h = 8:  Cf ≈ **-0.0008** (decaying reverse flow)
- x/h = 12: Cf ≈ **+0.0005** (post-reattachment, small positive)
- x/h = 16: Cf ≈ **+0.0020** (recovery)

Cf = τ_w / (0.5·ρ·U_ref²).

## §7 Strict FULL gate (per briefing §canonical)

- x_R/h ∈ [6.0, 6.5] ↔ canonical 6.26 ± 4.2% (briefing's "± 5%" relaxed to inclusive 6.0)
- Cp |Δ| < 10% at all 5 stations
- residuals 6/6 < 1e-5 (steady simpleFoam practical convergence)

**Marginal** (per briefing): x_R/h ∈ [5.5, 7.0] OR Cp 4/5 within tol
**PARTIAL**: x_R/h outside [5.5, 7.0] OR residuals not converged OR solver crash

## §8 Solver setup

- Solver: `simpleFoam` (incompressible steady RANS)
- Turbulence: kOmegaSST (RAS) — Menter 1992 BFS validation reference model
- Schemes: `bounded Gauss linearUpwindV grad(U)` for div(phi,U), `bounded Gauss upwind` for k/ω (case_021 parity)
- p-solver: GAMG + GaussSeidel
- U / k / ω solvers: PBiCGStab + DILU
- URF: p = 0.30, U = 0.70, k = 0.50, ω = 0.50 (NASA TMR canonical)
- Convergence: residualControl 1e-5 on all 6; maxIter 5000

## §9 Mesh design

3-block topology · ≈116k cells (within 100-300k briefing window):

| Block | Region | nx × ny × nz | Grading (x, y, z) | Cells |
|---|---|---|---|---|
| 1 | upstream channel (x ∈ [0, 0.254], y ∈ [h, H_in+h]) | 200 × 140 × 1 | (0.5, bilinear-1000, 1) | 28,000 |
| 2 | downstream upper (x ∈ [0.254, 0.508], y ∈ [h, H_in+h]) | 400 × 140 × 1 | (5, bilinear-1000, 1) | 56,000 |
| 3 | recirculation (x ∈ [0.254, 0.508], y ∈ [0, h]) | 400 × 80 × 1 | (5, bilinear-200, 1) | 32,000 |
| **Total** | | | | **116,000** |

- y-bilinear-1000: finer toward both top and bottom walls of upper channel
- y-bilinear-200: finer toward both step-shear-layer (y=h) and recirculation-floor (y=0)
- x-grading 0.5/5: fine near step on both sides
- Target wall-normal δy_first ≈ 5e-6 m → y+ ≈ 1 on bottom + step + downstream + top walls

## §10 Risk flags

- **mesh_density_on_domain_change**: low — fixed Driver-Seegmiller domain
- **solver_stability_on_novel_geometry**: low — BFS + kOmegaSST is textbook canonical
- **executable_smoke_test**: med — first-time BFS substrate, full Docker invocation in RUN_LOG.md
- **canonical_reference_drift**: low — NASA TM 86658 is decades-old reference; published Cp/Cf values are stable
- **inlet_bc_developed_profile**: **HIGH** — uniform inlet at 20·h is shorter than canonical experimental BL development. Mitigated by §8 honest documentation; x_R/h offset toward 5.4-6.0 expected

## §11 V-row attribution (anticipated)

Reuse from prior V64-A sub-DECs:
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — expected to firm
- **V47** (NREL UAE-style BC documentation conventions) — partial reuse for inlet I, L_t conventions

F-NEW candidates if surfaced:
- F-NEW: BFS x_R/h sensitivity to inlet δ/h (literature 5.5-6.5 spread)
- F-NEW: kOmegaSST F1/F2 blending sensitivity at sharp-corner separation
- F-NEW: simpleGrading bilinear convention (multi-region) — first time used in this repo

## §12 4Q gate

- **Q1 LLM-offline**: env -i HOME PATH .venv/bin/python re-runnable via Docker `docker run --rm -v ~/Desktop/case_022_driver_seegmiller_bfs/case:/case opencfd/openfoam-default:2312 bash -c 'cd /case && simpleFoam'`
- **Q2 artifacts**: 11+ dict files + RUN_LOG.md + extract_bfs.py + validation report + sub-DEC
- **Q3 TrustGate**: every x_R/h, Cp, Cf value cites postProcessing file row + canonical cites NASA TM 86658 figure/page
- **Q4 advisor-only**: NO advisor stack edits this sub-session
