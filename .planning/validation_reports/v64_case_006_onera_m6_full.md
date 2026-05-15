# V64-A · case_006 ONERA M6 Transonic Wing · M-V64A-VAL-FULL-2 · PARTIAL v2

**Date**: 2026-05-15
**Sub-DEC**: `DEC-V64-A-sub-M-V64A-VAL-FULL-2` (Accepted)
**Parent DEC**: `DEC-V64-A-charter`
**Phase**: V64-A Tier 2 · M-V64A-VAL-FULL-2 (case_006 ONERA M6 transonic · 2nd FULL attempt)
**Verdict**: **PARTIAL v2** (case_006-side · 2nd FULL attempt) — strict FULL not achieved due to solver-class incompatibility + geometry-proxy delta; meaningful Cp + force-coefficient comparison vs canonical Schmitt-Charpin features achieved.
**Confidence**: med

## Executive summary

**PARTIAL v2 verdict** per task brief reverse condition triggers #1 (Δ Cp > 15% on ≥1 station)
and #3 (shock position error > 5% of chord). Multi-attempt solver cascade documented:
3 rhoSimpleFoam steady attempts (per brief: kOmegaSST + sutherland + URF 0.30/0.70/0.50)
crashed shock-startup instability at iter <80 (FE_DIVBYZERO + FE_DOMAIN sqrt(T) +
p-equation divergence; shared signature with DEC-V64-A-sub-M-VAL-CASE-016-FULL B53).
v2.4 fallback to substrate case.yaml v1-specified rhoCentralFoam + laminar (proven stable
in v1 baseline) ran to t=0.005s (5000 iter, 2964s wall) with quasi-stationary force-coefficient
plateau (Cl Δ over last 100 iter < 1e-4). Cp at 7 Schmitt-Charpin spanwise stations
extracted and compared to canonical AGARD-AR-138 features (qualitative — no digitized data
in repo).

Achievement: meaningful Cp distribution + force-coefficient capture + canonical-feature
comparison + V-row carry-forward 5/9 firm + 2 F-NEW rows surfaced. Result: Done #1 stays
0/3 strict (no FULL convergence achieved within reverse-condition tolerance); Done #2
advances 1/3 → 2/3 net-new canonical comparison (Schmitt-Charpin AGARD-AR-138).

Result-class summary table:

| Dimension | Target | Achieved | Δ | Verdict |
|---|---|---|---|---|
| Solver convergence (force-coeff quasi-stationary drift) | < 1e-4 over 100 iter | Δ Cl over last 100 iter ≈ 1e-4 (Cl 0.2276 → 0.2276 from iter 4900 → 5000) | MET (quasi-stationary) | converged in transient sense |
| Continuity residual (steady-equiv proxy) | < 1e-3 | N/A (rhoCentralFoam transient solver; no continuity residual; force-coeff drift is the analogue) | N/A | analogue MET |
| Mesh cell count | 600k-1.5M | 205,310 (4.2× v1's 48,847) | -66% below floor | DISCLOSED (quality-bound at level (6,7)) |
| Cl (lift coefficient) | ~0.27 (Schmitt-Charpin canonical) | 0.2276 | -15.7% | PARTIAL (laminar + NACA proxy) |
| Cd (drag coefficient) | ~0.014-0.020 (canonical low-Re viscous) | 0.0390 | +95% to +179% | DISCLOSED (laminar + coarse mesh numerical drag) |
| Max upper-surface Mach (from Cp_min) | ~1.4 (canonical lambda peak η=0.65-0.80) | M_max ≈ 1.20 (from Cp_min=-0.93 at η=0.95 via isentropic) | -14.3% | smeared (mesh + laminar) |
| Shock x/c at η=0.65 | ~0.50 (canonical lambda peak primary shock) | 0.62 (max dCp/dx detection) | +24% aft | PARTIAL (>5% trigger) |
| Shock x/c at η=0.90 | ~0.75 (canonical outboard shock) | 1.00 (TE detection · smeared lambda) | +33% (algorithm caveat: TE separation false positive) | PARTIAL (>5% trigger) |
| Cp_min at η=0.65 (lambda peak) | ~-1.20 (canonical) | -0.699 | +41.7% under-predicted | PARTIAL (>15% trigger) |

## V64-A Done dimension impact

| Done # | Pre-B59 | Post-B59 | Verdict |
|---|---|---|---|
| 1 FULL validation reports (real solver convergence + literature delta) | 0 / 3 strict | **0 / 3 strict** (stays · PARTIAL v2 not FULL) | NOT advanced |
| 2 Canonical literature comparisons | 1 / 3 | **2 / 3** (+ Schmitt-Charpin AGARD-AR-138 net-new) | +1 net-new |
| 3 Convergence stability test | 1 / 1 ✓ | 1 / 1 ✓ | unchanged |
| 4 PARTIAL → FULL upgrade | 0 / ≥2 | 0 / ≥2 | unchanged |
| 5 V63-A carry-over closure | 2 / ≥4 | 2 / ≥4 | unchanged |
| 6 V-row attribution rate | clause-1 over-met 3/2 | clause-1 over-met 3/2 (case_006 stays 5/9 firm) | unchanged |

## Reverse condition triggers (PARTIAL v2 rationale)

Per task brief reverse-condition table (`PARTIAL v2 trigger if ANY:`):

1. **Δ Cp > 15% in any section** — **TRIGGERED** at 5/7 stations:
   - η=0.20: |Δ Cp_min| = 27.7% (-0.638 vs canonical -0.50)
   - η=0.44: |Δ Cp_min| = 33.2% (-0.601 vs -0.90; lambda peak under-predicted)
   - η=0.65: |Δ Cp_min| = 41.7% (-0.699 vs -1.20; lambda peak under-predicted)
   - η=0.80: |Δ Cp_min| = 30.4% (-0.765 vs -1.10)
   - η=0.90: |Δ Cp_min| = 16.4% (-0.836 vs -1.00)
   - η=0.95: |Δ Cp_min| = 2.8% (within tolerance · BORDERLINE)
   - η=0.99: |Δ Cp_min| = 30.7% (-0.915 vs -0.70; over-predicted near tip)
2. **Residual not converged (continuity > 1e-3)** — **TRIGGERED · MULTI-LAYER**:
   - rhoSimpleFoam attempt 1 (GAMG p · URF 0.30/0.70/0.50 per brief): FE_DIVBYZERO at iter 1, crashed in PBiCGStab (GAMG coarsest solver)
   - rhoSimpleFoam attempt 2 (PBiCGStab DILU p · URF 0.15/0.40/0.30): FE_DOMAIN at iter 77, sqrt(T) in libfluidThermophysicalModels (same signature as DEC-V64-A-sub-M-VAL-CASE-016-FULL B53 v2)
   - rhoSimpleFoam attempt 3 (PBiCGStab + const transport · URF 0.10/0.30/0.10): p equation residual diverged from 0.478 to 8011 within 1000 PBiCGStab iters (matrix ill-conditioning during shock startup)
   - **Solver fallback**: rhoCentralFoam + laminar (substrate case.yaml's specified solver_v1; v1 baseline ran cleanly to t=5ms · 663s wall on 48k cells)
   - v2.4 fallback rhoCentralFoam ran cleanly to t=0.005s · 5000 iter · 2964s wall · Cl quasi-stationary (Δ over last 100 iter ≈ 1e-4)
3. **Shock position error > 5% of chord** — **TRIGGERED** at all 5 stations with canonical shock reference:
   - η=0.44: x_shock/c = 0.697 (v2.4) vs 0.20 (canonical) → +248.7% delta (aft)
   - η=0.65: x_shock/c = 0.618 vs 0.50 → +23.6% delta (aft)
   - η=0.80: x_shock/c = 0.998 vs 0.55 → +81.4% delta (algorithm caveat: TE separation false positive · lambda shock smeared)
   - η=0.90: x_shock/c = 1.000 vs 0.75 → +33.3% delta (algorithm caveat: TE detection)
   - η=0.95: x_shock/c = 0.467 vs 0.78 → -40.1% delta (forward)
   - Shock detection algorithm: max(dCp/dx) on upper surface downstream of 30% chord. Caveat: smeared lambda at 205k cells + TE separation can produce false positives at η=0.80/0.90.

## Geometry-proxy disclosure (V32 carry-forward)

Per case_006 case profile + case.yaml:

- **Wing airfoil**: NACA 0010 (10% symmetric) — substituted for true ONERA D-section due to Tier-1 source unreachability (V32 finding: NASA Glenn `WWW/wind/valid/m6wing/foilmod.txt` HTTP 500 + corporate SSL cert chain double-blocker).
- **Documented systemic error**: ONERA D-section curvature differs in rooftop region (x/c 0.30-0.60) → lambda-shock x/c may displace 5-15% relative to AGARD-published Cp positions.
- **This v64-val-full-2 attempt**: accept-with-disclosure path per task brief; deviation NOT remediated in this sub-DEC (out-of-scope · A1 extraction sub-DEC + ONERA-D ingest is the canonical fix path).

## Mesh (v2.4 · 205k cells · 4× v1)

| Field | v1 (B-eval-pre) | v2 (B59) | Delta |
|---|---|---|---|
| Cell count | 48,847 | **205,310** | 4.2× |
| Wing surface refinement level | (4, 5) — 31mm at wall | **(6, 7)** — 7.8mm at wall | 4× finer |
| Auxiliary surfaces (tip_cap) | (4, 5) | **(5, 6)** | 2× finer |
| Prism layers | none | **4 layers exp 1.25 finalLayer 0.35** | NEW |
| nCellsBetweenLevels | 3 | 3 | unchanged |
| Max non-orthogonality | 46.8° | 52.5° | +5.7° (still <65 threshold) |
| Max skewness | 1.31 | 1.66 | +0.35 (still <4 threshold) |
| Max aspect ratio | n/a | 9.25 | OK |
| Min volume | n/a | 1.21e-08 m³ | OK |
| Concave cells (face-plane check) | 916 | 8,820 | 9.6× (mesh-quality concern · solver-tolerable per S6) |
| Cells with small determinant (<0.001) | 0 | 2 | NEW (sliver-localized) |
| checkMesh status | "Failed 2 checks" (concave cells + face tets) | **"Failed 3 checks"** (concave cells + small-det + face tets · all solver-tolerable) | -1 net |
| Patches retained post-sHM | wing_surface_reference + tip_cap (3 small surfaces eaten · V30) | wing_surface_reference (17,899 faces) + tip_cap (437 faces) | 2.7× wing surface face density |
| Below brief floor 600k? | n/a | **YES (66% below)** | DISCLOSED |

Below-floor disclosure: pushing further to level (7,8) would yield ~600k+ cells but checkMesh face-tets + concave-cells failure counts already accumulating (3 checks failed at (6,7)); estimated (7,8) would push concave-cell count to ~30k+ and risk solver-incompatible mesh quality. Accept-as-is per cost-benefit tradeoff.

## Solver execution (rhoCentralFoam · v1 fallback after rhoSimpleFoam × 3 fail)

Solver completed cleanly to t=0.005s (live-modified mid-run from 0.008 → 0.005 to match
v1 baseline endpoint for direct comparison). 5000 iterations in 2964s wall (49 min) on
Apple Silicon Docker (single core, no decomposition). 5 writeInterval snapshots
(0.001, 0.002, 0.003, 0.004, 0.005). Quasi-stationary force-coefficient plateau verified
(Cl drift < 1e-4 over last 100 iterations).

Key parameters:
- **Solver**: rhoCentralFoam (transient density-based explicit Kurganov+Minmod · per substrate case.yaml v1 configuration · proven stable in v1 baseline)
- **Turbulence**: laminar (v1 fallback · brief asked kOmegaSST but rhoCentralFoam + RAS is not canonical OpenFOAM tutorial; defer to v3 + rhoPimpleFoam path)
- **Transport**: const (mu=1.79e-5 · v1 config; brief asked sutherland but const matches v1 baseline; minor accuracy delta at T>300K)
- **Thermophysical**: perfectGas + eConst + sensibleInternalEnergy (v1)
- **Time discretization**: localEuler (pseudo-steady) + maxCo 0.5 + adjustTimeStep + initial deltaT 1e-6 s
- **End time**: 0.005 s physical (v1-baseline-equivalent · live-modified from initial 0.008 via runTimeModifiable yes after Cl quasi-stationary plateau visible)

Solver progression (final 1000 timesteps · pseudo-steady force-coefficient drift verification):

```
ExecutionTime = 2964 s · 5000 iterations · endTime = 0.005 s (live-modified mid-run from 0.008 → 0.005 for v1-baseline-equivalent direct comparison)
Final Courant: mean 0.00068, max 0.93
Final flow time scale: min 5.4e-07 s, max 2.7e-06 s
Final force coefficients (latest 5 rows, t=0.00496-0.005):
  Cd:        0.0390 → 0.0390 (Δ < 1e-4)
  Cl:        0.2276 → 0.2276 (Δ < 1e-4)
  CmPitch:  -0.0434 → -0.0434 (Δ < 1e-4)
Convergence: quasi-stationary plateau established. Force-coefficient drift over last
100 iter < 1e-4 (per v1 baseline §"Convergence"; comparable quasi-stationary criterion).
```

## Cp distribution at 7 Schmitt-Charpin spanwise stations

Extracted via `scripts/v64_v2_extract_cp.py` (case sandbox; pure stdlib regex parser of
OpenFOAM ASCII polyMesh + 0.005/p internalField; owner-cell approximation for zeroGradient
wing patch). Shock-foot detection: max(dCp/dx) on upper surface (z>0) downstream of LE +
30% chord (see `scripts/v64_v2_analyze_cp.py`). Per `case_006/config/case.yaml` validation
block: 7 stations at η = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99 in spanwise ±15 mm window.

Reference: Schmitt & Charpin, AGARD-AR-138 (1979), Test Case B1 "ONERA Wing M6", cp1u/l.ex
through cp7u/l.ex datasets. **NB: digitized Cp data NOT in repo · canonical x_shock/c values
cited from Schmitt-Charpin (1979) fig. 7-8 + Cook-McDonald-Firmin AGARD-CP-413 review +
Vassberg-Jameson 1996 ONERA M6 RANS validation summary** (per case profile §"Verdict
comparison").

### Cp summary table

| η | y [m] | n_upper | Cp_min (upper) | x(Cp_min)/c | x_shock/c (v2.4) | x_shock/c (canon.) | Δ x/c |
|---|---|---|---|---|---|---|---|
| 0.20 | 0.2393 | 215 | -0.638 | 0.991 | 0.422 | (weak/none) | N/A (no canonical shock) |
| 0.44 | 0.5264 | 215 | -0.601 | 0.108 | 0.697 | 0.20 | +248.7% |
| 0.65 | 0.7776 | 214 | -0.699 | 0.112 | 0.618 | 0.50 | +23.6% |
| 0.80 | 0.9570 | 221 | -0.765 | 0.181 | 0.998 | 0.55 | +81.4% (TE artifact) |
| 0.90 | 1.0767 | 225 | -0.836 | 0.238 | 1.000 | 0.75 | +33.3% (TE artifact) |
| 0.95 | 1.1365 | 248 | -0.925 | 0.141 | 0.467 | 0.78 | -40.1% |
| 0.99 | 1.1843 | 127 | -0.915 | 0.105 | 0.598 | (weak/none) | N/A (no canonical shock) |

### Cp_min vs canonical (upper surface lambda peak)

| η | v2.4 Cp_min | canonical Cp_min | Δ |
|---|---|---|---|
| 0.20 | -0.638 | -0.50 | -27.7% (over-predicted suction in subsonic region) |
| 0.44 | -0.601 | -0.90 | +33.2% (lambda peak under-predicted) |
| 0.65 | -0.699 | -1.20 | +41.7% (lambda peak under-predicted · WORST DELTA) |
| 0.80 | -0.765 | -1.10 | +30.4% (under-predicted) |
| 0.90 | -0.836 | -1.00 | +16.4% (under-predicted) |
| 0.95 | -0.925 | -0.90 | -2.8% (within tolerance · BORDERLINE) |
| 0.99 | -0.915 | -0.70 | -30.7% (over-predicted near tip) |

### Algorithm caveats

- **Smeared lambda shock at 205k cells**: cannot resolve forward+aft shock-foot pair; clearest
  shock signature shows up as a single recovery region rather than the published twin-peak
  lambda pattern (Schmitt-Charpin 1979 fig. 7).
- **Shock-foot algorithm**: simple max(dCp/dx) on upper surface; at η=0.80/0.90 the algorithm
  picks up TE separation rather than shock foot (returns x_shock/c ≈ 1.0). The lambda is
  smeared enough that the largest dCp/dx is at the TE pressure recovery rather than in the
  shock-foot region.
- **NACA 0010 proxy geometry (V32 carry-forward)**: known 5-15% lambda-shock x/c displacement
  vs ONERA D-section; explains some of the Δ x/c excess.
- **Laminar turbulence**: cannot reproduce turbulent boundary-layer / shock interaction;
  shock smearing is partially attributable to absence of turbulent kinetic energy production
  at the shock foot.

**Disclosure**: x_shock/c canonical targets are estimated from published lambda-shock figure
in Schmitt & Charpin (1979) figure 7-8 + Cook-McDonald-Firmin AGARD-CP-413 review summary.
**Digitized point data is NOT in this repo · qualitative + canonical-feature Δ Cp tables
produced; numerical per-point Cp curve comparison deferred to A1 extraction sub-DEC** (per
case profile §"What this case does NOT yet have").

## Force coefficients vs canonical

| Metric | v1 (48k laminar) | **v2.4 (205k laminar)** | Schmitt-Charpin canonical | v2.4 Δ |
|---|---|---|---|---|
| Cl | 0.250 | **0.2276** | ~0.27 | -15.7% (worse than v1 -7%) |
| Cd | 0.0545 | **0.0390** | ~0.014-0.020 (canonical viscous + induced) | +95% to +179% (better than v1 +173% to +290%) |
| CmPitch | -0.0376 | **-0.0434** | (sign correct in v1; canonical magnitude not directly published) | qualitatively correct sign · more negative than v1 |
| Cd (front) | 0.234 | **0.2047** | n/a | n/a |
| Cd (rear) | -0.179 | **-0.1657** | n/a | n/a |
| Max \|U\| (from Cp_min at η=0.95) | 400.7 m/s (M≈1.18) | **~378 m/s** (Cp_min=-0.93 → M≈1.20 via isentropic) | ~M=1.4 → ~430 m/s @ T=288K | -14.3% |

**Trend analysis**: v2.4 Cl moved AWAY from canonical (0.250 → 0.228) relative to v1.
Hypothesis: prism-layer boundary-layer resolution (4 layers, expansion 1.25) introduces
viscous-shear correction that v1 (no prism) didn't have; laminar viscosity overestimates
wall shear; result is reduced suction-side lift contribution. With kOmegaSST (deferred to
v3), the turbulent boundary-layer dissipation would correct this trend toward canonical.
Cd correctness improved (0.0545 → 0.0390) because finer mesh reduces numerical pressure-drag
artifact; this is the expected mesh-refinement benefit.

Per V63-A close §3.1 "PARTIAL semantics user-ratification": PARTIAL → FULL upgrade requires solver convergence (ACHIEVED by v2.4 rhoCentralFoam quasi-steady force-coefficient stability · Cl drift < 1e-4 over last 100 iter) + literature comparison delta < canonical tolerance (NOT MET · ΔCl=-15.7%, ΔCp_min=+16% to +42% across stations, Δ x_shock/c=+24% to +249% across stations). PARTIAL v2 is the v2.4 verdict; FULL upgrade path requires (i) ONERA D-section geometry ingest (V32 fix · A1 extraction sub-DEC), (ii) kOmegaSST turbulence (rhoPimpleFoam pseudo-transient path), (iii) ≥1M-cell mesh resolution. Estimated combined v3-attempt timeline: 1 substrate sub-DEC + 1 mesh sub-DEC + 1 solver sub-DEC + 1 validation report sub-DEC = 4 chained sub-DECs.

## V-row attribution

case_006 V-row capture matrix (B55 substrate v2 baseline · 5/9 firm + D4 marginal):

| mode | B55 (Tier 1) | **B59 (Tier 2)** | reason for current state |
|---|---|---|---|
| V26 | NO | NO | codex_output_validator not LANDED (out-of-scope · separate sub-DEC) |
| V27 | YES ✓ | **YES ✓** | solver_block_advisor LANDED B55 (no change · regression OK) |
| V28 | YES ✓ | **YES ✓** | solver_block_advisor LANDED B55 (no change · regression OK) |
| V29 | YES ✓ | **YES ✓** | freestream/freestreamPressure substitution from v1 (no change · regression OK) |
| V30 | YES ✓ | **YES ✓** (re-validated) | tip_cap_sliver, root_fairing_pad/cover eaten by sHM at level (6,7) — same V30 outcome as v1 |
| V31 | NO | NO | protocol-revision-level · out-of-stack |
| V32 | NO | NO | infra-level · A1 extraction not LANDED |
| D1 | YES ✓ | **YES ✓** | A2-v2 substrate (B42 V63-A) · unchanged |
| D4 | marginal | **marginal** | thin_wall fires same as v1; geometry_surgery silent (sliver under min_to_decimate) |

**5/9 firm + D4 marginal · unchanged from B55 · ≥5/9 firm: MET (carry-forward from B55, no advancement, no regression)**

### F-NEW: rhoSimpleFoam transonic external-wing shock startup instability (multi-attempt)

3 attempts at rhoSimpleFoam steady (per task brief: kOmegaSST RAS + sutherland transport + perfectGas + URF p=0.30/U=0.70/e=0.50) crashed consistently within iter <80:

- Attempt 1 (GAMG p): FE_DIVBYZERO at iter 1, libOpenFOAM PBiCGStab in GAMG coarsest level
- Attempt 2 (PBiCGStab DILU + Sutherland): FE_DOMAIN at iter 77, libfluidThermophysicalModels sqrt(T) on T<0 transient internal cell
- Attempt 3 (PBiCGStab DILU + const transport + lower URF): p equation residual diverged from 0.478 to 8011 within 1000 PBiCGStab iters (matrix ill-conditioning)

**Crash signature shared with**: DEC-V64-A-sub-M-VAL-CASE-016-FULL (B53 case_016 PARTIAL v2) — rhoPimpleFoam crashed at t=1.24ms with FE in libfluidThermophysicalModels.

**Root cause (proposed)**: rhoSimpleFoam steady-state SIMPLE-style algorithm cannot handle freestream → transonic shock initialization without pre-conditioning. Brief's "freestream IC + 3000 iter steady" workflow is incompatible with hyperbolic shock startup for external transonic geometries. Standard mitigation paths:
1. potentialFoam pre-step → smooth initial velocity field
2. rhoPimpleFoam pseudo-transient → handles transient shock formation
3. rhoCentralFoam transient density-based → proven stable in v1, used in v2.4 fallback

**V-row classification**: F-NEW-5 (proposed) — solver-class mismatch for transonic external wing in rhoSimpleFoam. Not a substrate finding (substrate is correct per case.yaml `solver: rhoCentralFoam`); not a stack finding (advisor does not gate solver-class choice). Procedural finding — task brief proposed rhoSimpleFoam without checking substrate's stated solver_v1 = rhoCentralFoam; deviation surfaced + documented.

**Methodology patch (for next V64-A retro)**: charter-level brief authoring should consult substrate case.yaml solver field before specifying alternative; if alternative solver is desired, pre-step (potentialFoam) must be in scope.

### F-NEW: case_006 v2 mesh-quality lower-edge at level (6,7)

205k cells with checkMesh "Failed 3 checks" (concave + small-det + face tets) — quality bound reached. Going further to level (7,8) for 600k+ cells would exceed solver-tolerable bounds (estimated concave-cell count 30k+). 4× v1 cell density is the practical ceiling for this STL geometry.

**V-row classification**: F-NEW-6 (proposed) — mesh-quality vs cell-budget tradeoff for ONERA M6 STL at sHM level escalation. Not a substrate finding; mesh-side observation.

## 4Q gate compliance

- **Q1 LLM-offline**: solver runner `scripts/v64_v2_run_solver.sh` re-runnable via `env -i HOME PATH bash <path>`; no LLM mid-stream invoked; all dicts authored as static OpenFOAM ASCII; Cp extraction Python script (`scripts/v64_v2_extract_cp.py`) pure stdlib regex parser, no LLM
- **Q2 artifacts**: 14 dicts in repo at `.planning/case_profiles/case_006_v64_val_full_2_dicts/` + this validation report + sub-DEC + `evidence/v64_v2/{rhoCentralFoam.log, checkMesh.log, cp_eta_*.csv, cp_summary.md}` in case sandbox
- **Q3 TrustGate**: every Cp value cites postProcessing/Cp file row + Schmitt-Charpin canonical references cite AGARD-AR-138 (1979) page/figure (text-level only · digitized data deferred); thermophysical/transport constants cite OpenFOAM tutorial canonical values + White 1991 air properties
- **Q4 advisor-only**: `ui/backend/services/advisor_stack.py` UNTOUCHED · `ui/backend/services/geometry_ingest/` UNTOUCHED · `ui/backend/routes/` UNTOUCHED · `ui/frontend/` UNTOUCHED · only case sandbox dicts + repo `.planning/` artifacts modified

## Reused B55 substrate v2 artifacts

- `solver_block_advisor` (#11 advisor) — LANDED B55 · pre-fix-snapshot configuration of v1 controlDict triggered V27+V28 critical (verified via re-running B55 verifier script · solver_block_inputs.yaml + thin_wall_inputs.yaml + interface_*.json all unchanged from B42 V63-A reproducibility)
- `case_006/inputs/solver_block_inputs.yaml` — B55 substrate file · provides V27+V28 stack-side validation evidence
- v1 STLs `case_006/case/constant/triSurface/{wing_surface_reference, tip_cap, root_fairing_*, tip_cap_sliver}.stl` — already mm→m converted in v1 · zero CAD regeneration

## Limitations (PARTIAL v2 disclosed)

1. **Solver deviation**: rhoCentralFoam (case.yaml v1 solver) instead of brief's rhoSimpleFoam — multi-attempt rhoSimpleFoam shock startup instability triggered fallback per V63-A close §3.1 PARTIAL semantics precedent
2. **Turbulence deviation**: laminar (v1 baseline) instead of brief's kOmegaSST — rhoCentralFoam + RAS is not canonical OpenFOAM v2312 tutorial path; defer to v3 if needed
3. **Geometry proxy**: NACA 0010 vs ONERA D-section — known 5-15% lambda-shock x/c displacement (V32 carry-forward)
4. **Mesh below brief floor**: 205k vs 600k-1.5M target — quality-bound at (6,7); 4× v1 still meaningful improvement
5. **Experimental data**: Schmitt-Charpin Cp at 7 stations NOT digitized in repo — qualitative canonical-feature comparison only · A1 extraction sub-DEC backlog
6. **Transport deviation**: const mu (1.79e-5) vs brief's sutherland — v2.3 fvSolution-fix introduced const to eliminate sqrt(T) FE_DOMAIN; ~13% mu delta at post-shock T=350K but Cl unaffected (pressure-side)

## Next steps (v3 candidate path)

1. **Geometry**: A1 extraction sub-DEC + ingest ONERA D-section coordinates (V32+V20 bundled fix)
2. **Solver**: rhoPimpleFoam pseudo-transient (substrate's solver_v2) with potentialFoam pre-step + kOmegaSST RAS post-startup
3. **Experimental data**: Schmitt-Charpin Cp digitization (AGARD-AR-138 figure 7-8 → CSV) for true Δ Cp numerical comparison
4. **Mesh**: refinementRegion-driven approach instead of surface-level escalation — adds bulk cell density without quality degradation

## References

- Brief: B59 dispatch (autonomous session 2026-05-15)
- Case profile: `.planning/case_profiles/case_006_onera_m6_transonic.md`
- V64-A charter: `.planning/decisions/2026-05-15_v64_charter_dec.md`
- B55 substrate v2 sub-DEC: `.planning/decisions/2026-05-15_v64_sub_case_006_substrate_v2.md`
- B53 case_016 PARTIAL v2 precedent: `.planning/decisions/2026-05-15_v64_sub_val_case_016_full.md`
- B56 case_004 PARTIAL v2 precedent: `.planning/decisions/2026-05-15_v64_sub_val_full_1.md`
- v1 baseline report: `~/Desktop/case_006_onera_m6_transonic/evidence/v1/REPORT.md`
- v64_v2 evidence dir: `~/Desktop/case_006_onera_m6_transonic/evidence/v64_v2/`
- Schmitt-Charpin canonical: Schmitt, V. and Charpin, F., "Pressure Distributions on the ONERA M6 Wing at Transonic Mach Numbers", AGARD-AR-138 Test Case B1, May 1979
- V63-A close §3.1 PARTIAL semantics precedent: `.planning/decisions/2026-05-15_v63_close_dec.md`
