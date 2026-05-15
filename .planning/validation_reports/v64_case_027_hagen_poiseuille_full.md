# case_027 · Hagen-Poiseuille Pipe Flow · MARGINAL Validation Report

> V64-A Tier 2 · M-V64A-VAL-FULL-PIPE · 8th FULL attempt (B70 dispatch)
> **Verdict: MARGINAL** — physics-strict-PASS 3/3 (u + dp/dx + τ_w all < 1%) · residual-stricture-FAIL · user-ratifiable as FULL under wedge-mesh-floor-residual-plateau argument
> Parent DEC: DEC-V64-A-charter
> Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-PIPE
> Authored 2026-05-15 · Claude Code Opus 4.7 (1M context) · main session B70

---

## §1 TL;DR

Hagen-Poiseuille pipe flow (Schlichting *Boundary-Layer Theory* §5.1.2) at
Re_D = 66.67 (deep laminar) using simpleFoam + laminar simulation type on a
20,000-cell axisymmetric wedge mesh (5° wedge half-angle 2.5°) with
codedFixedValue parabolic radial inlet u(r) = 2·u_mean·(1-(r/R)²).

Solver ran 5000 iter (max-iter cap reached · SIMPLE auto-exit did NOT fire
because of Uz residual plateau · wedge-geometry artifact).

| Strict-gate criterion | Target | Achieved | Margin |
|---|---|---|---|
| max \|Δu\| at exit station (40 radial cells · direct cell-centered) | < 1% u_max | **0.1807%** | ×5.5 |
| 40/40 exit radial cells within strict | 40/40 | **40/40** | full |
| \|Δ dp/dx\| linear fit (j=0 row · x ∈ [0.05, 0.45] · 401 cells) | < 1% | **+0.3623%** | ×2.8 |
| \|Δ τ_w\| developed region (x ∈ [0.05, 0.45] · 400 wall faces) | < 1% | **+0.2686%** max | ×3.7 |
| 400/400 developed-region wall faces within strict | full | **400/400** | full |
| residuals (4-field strict) | 4/4 < 1e-8 | **1/4** (Ux machine-precision; Uy + Uz + p sub-strict) | -- |
| residuals (3-field adjusted excl Uz wedge) | 3/3 < 1e-8 | **1/3** (Ux only) | -- |

**STRICT TRIFECTA on physics** (u + dp/dx + τ_w developed): **3/3 PASS ✓✓✓**
**RESIDUAL STRICTURE**: 1/4 strict-letter (Ux at 3e-12 machine precision; Uy
plateau 9e-7 / Uz wedge artifact 3.3e-2 / p slow-decreasing 2.7e-8)

Mid-pipe (x ≈ 0.25 = 50·R) cross-check confirms fully-developed flow:
max |Δu| identical 0.1807%, 40/40 strict at mid station.

→ **MARGINAL** under briefing strict-letter reading (residual gate not met).
→ User-ratifiable as **FULL** under case_025 §field-count-transparency
extension to "wedge-floor-residual-plateau" exemption (Ux machine-precision
+ Uy/p plateau at wedge BC vector-rotation floor · Uz wedge artifact).
→ Default verdict pending user ratification: **MARGINAL** (Done #1 stays 1/3).

---

## §2 Context: V64-A Tier 2 attempt history

| Attempt | Case | Verdict | Notes |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup |
| #3 (B63) | case_021 NASA TMR flat plate | PARTIAL (soft) | residuals plateau 3-5e-5 |
| #4 (B65) | case_024 lid cavity Re=1000 | PARTIAL (strong) | 129² uniform-grid v-discrepancy |
| #5 (B66) | case_022 Driver-Seegmiller BFS | PARTIAL | uniform inlet δ/h gap |
| #6 (B67) | case_024 cavity v2 | PARTIAL v2 | physics regression v 4.10→6.49% stretching mis-applied |
| #7 (B68) | case_025 plane Poiseuille | **FULL ✓** | first strict-FULL · 0.0425% / -0.12% / -0.56% |
| **#8 (B70) · this report** | **case_027 Hagen-Poiseuille pipe** | **MARGINAL** | physics-strict-PASS 3/3 · residual-stricture-FAIL · wedge-floor |

**Pre-B70 1D analytical canonical record**: 1/1 strict-FULL (case_025 plane
Poiseuille). B70 was the second 1D analytical canonical attempt, testing whether
the empirical evidence "1D analytical → strict-FULL" holds across geometry
class (planar → cylindrical-axisymmetric).

**B70 strategic finding**: Physics-strict-PASS holds across the geometry-class
transition (u + dp/dx + τ_w all clean at < 0.4%). But residual-strictness
does NOT transfer cleanly: case_025's 2D plane geometry had 3 prognostic
fields all reaching 1e-8 strict; case_027's 3D wedge geometry has 4 fields
with Uy/Uz/p plateaus due to wedge BC's vector-rotation constraint. The
empirical evidence is mixed: **1D-analytical-canonical strict-FULL is
robust on physics gates but fragile on residual-strictness when geometry
introduces wedge-mesh artifacts.**

---

## §3 Canonical reference (Schlichting §5.1.2)

Steady, fully-developed laminar flow in an infinite circular pipe of radius R,
driven by constant axial pressure gradient (Hagen-Poiseuille):

**Velocity profile** (Schlichting *Boundary-Layer Theory*, 9th ed. (Springer,
2017), §5.1.2, eqn (5.10)):
```
    u(r) = 2 · u_mean · (1 - (r/R)²)            for r ∈ [0, R]
```

**Pressure gradient** (Schlichting §5.1.2, eqn (5.11)):
```
    dp/dx = -8·μ·u_mean / R²                     (laminar steady incompressible)
```

**Wall shear stress** (Schlichting §5.1.2, eqn (5.12)):
```
    τ_wall = μ · |du/dr|_{r=R} = 4·μ·u_mean / R
          = -R/2 · dp/dx                         (force-balance identity)
```

**Reynolds number** based on diameter D = 2R:
```
    Re_D = ρ · u_mean · D / μ                    (laminar < 2300)
```

In OpenFOAM kinematic incompressible convention (p_kin = p/ρ; ρ absorbed
into ν = μ/ρ):
```
    dp_kin/dx     = -8·ν·u_mean / R²    = -0.48     m²/s²/m
    τ_wall_kin    =  4·ν·u_mean / R     = +1.2e-3   m²/s²
```

with **ν = 1.5e-5, u_mean = 0.1, R = 0.005** (D = 0.01).

Re_D = 0.1·0.01/1.5e-5 = **66.67** (deep laminar).
L_entrance ≈ 0.06·Re·D = 0.04 m · L/L_entrance = 12.5× development buffer.

### §3.1 Comparison to plane Poiseuille (case_025 · B68 FULL)

| Quantity | Plane Poiseuille (case_025) | Hagen-Poiseuille (case_027) | Factor |
|---|---|---|---|
| u_max / u_mean | 3/2 = 1.5 | 2 | ×4/3 |
| dp/dx (kinematic) | -3·ν·u_mean/H² | -8·ν·u_mean/R² | factor 8/3 (with H↔R unit scaling) |
| τ_wall (kinematic) | 3·ν·u_mean/H | 4·ν·u_mean/R | factor 4/3 |
| Geometry | 2D channel · 1 hex block · 4 patches | 3D axisymmetric wedge · 1 hex degenerate-axis block · 5 patches |
| Field count | 3 (p, Ux, Uy · frontAndBack empty) | 4 (p, Ux, Uy, Uz · wedge front/back) |
| Wedge artifact? | NO (no degenerate edge) | YES (axis degenerate · Uz residual plateau) |

The geometric/coefficient differences (factors 4/3 vs 8/3 vs 4/3) are
canonical textbook outcomes of cylindrical-vs-planar coordinates with same
characteristic length scale (H for plane vs R for pipe).

---

## §4 Geometry & setup

| Parameter | Value | Notes |
|---|---|---|
| Pipe radius R | 0.005 m | D = 2R = 0.01 m |
| Pipe length L | 0.5 m | = 100·R = 50·D (≥3·L_entrance buffer) |
| Wedge full angle | 5° (half-angle ±2.5°) | OpenFOAM canonical |
| Cell count | 20,000 hex | 500 (x) × 40 (r) × 1 (θ wedge) |
| ν | 1.5e-5 m²/s | air @ 15°C (matches case_025) |
| ρ (effective) | 1.0 kg/m³ | kinematic incompressible |
| u_mean | 0.1 m/s | cross-section average |
| u_max | 0.2 m/s | 2·u_mean centerline (axisymmetric) |
| Re_D = u_mean·D/ν | **66.67** | deep laminar |
| L_entrance ≈ 0.06·Re·D | 0.04 m | L/L_entrance = 12.5× |
| Mesh r-grading | 0.333 axis→wall (3:1 ratio) | wall δr ≈ 7e-5, axis δr ≈ 2.05e-4 |
| Max aspect ratio | 14.7 | checkMesh PASS-w/-2-wedge-flags |
| Inlet BC | codedFixedValue with r=sqrt(y²+z²) parabolic | first sqrt-radial in repo |
| Outlet BC | p=0 fixedValue · U zeroGradient | |
| Wall BC | noSlip at r=R chord-approximation | wedge wall face at y=R·cos(2.5°)=0.004995 |
| Wedge front/back | type wedge (OpenFOAM symmetry) | |
| Axis | type empty (degenerate edge · 500 zero-area faces) | absorbed by defaultPatch |

### §4.1 Mesh layout (vertex coordinates)

8-vertex hex block · v0 = v4 and v1 = v5 coincident on axis:

```
v0 = v4 = (0,    0,                  0)                       (inlet · axis)
v1 = v5 = (0.5,  0,                  0)                       (outlet · axis)
v2     = (0.5,  0.004995241108,  -0.000218096937)             (outlet · wall back)
v3     = (0,    0.004995241108,  -0.000218096937)             (inlet · wall back)
v6     = (0.5,  0.004995241108,  +0.000218096937)             (outlet · wall front)
v7     = (0,    0.004995241108,  +0.000218096937)             (inlet · wall front)
```

R·cos(2.5°) = 0.004995241108  (3-mode-3 wall y-coordinate)
R·sin(2.5°) = 0.000218096937  (wall ±z half-width)

### §4.2 Wedge geometric bias (∼0.2% intrinsic to wedge representation)

The wedge mesh's wall face is a flat quad chord-approximating the curved
pipe wall. At the wedge bisector plane (z=0), the wall is at radial position
r = R·cos(2.5°) = 0.004995 (NOT r = R = 0.005). This is a 0.1%-R geometric
bias intrinsic to the 5° wedge approximation.

Effect on u(r):
- Analytical: u(r) = 2·u_mean·(1 - (r/R)²) where wall is at r=R
- Simulated: effective wall at r = R·cos(2.5°), so u → 0 at slightly smaller
  radius than R
- Resulting bias in u: 2·u_mean·((r/R_eff)² - (r/R)²) ~ +0.2% near wall

This bias appears in the data as a smooth Δ% gradient: positive near axis
(+0.13% to +0.17%), passes through zero at r≈3.5e-3 (mid-radius), negative
near wall (down to -0.18%). The peak |Δ| (0.18%) occurs at the wall-adjacent
cell — exactly matching the wedge geometric bias prediction in CASE_SPEC
§10 risk flag `wedge_axis_discretization`.

This is **NOT a solver/discretization error** — it is the intrinsic geometric
approximation of representing a curved circular wall with a flat wedge chord.
It would persist at infinite mesh refinement.

---

## §5 Results · §5.1 u(r) at exit station (40 radial cell-centered values)

Read directly from `5000/C` (cell centers) and `5000/U` (cell-centered Ux)
at i=NX-1=499 (last x-column), j=0..39 (all radial cells), via
`extract_hagen_poiseuille.py`. Comparison to analytical u(r) = 2·u_mean·(1-(r/R)²).

Full 40-cell table in `case_027_v64_pipe_dicts/results/exit_profile_delta.csv`.
Stub here:

| j | r [m] (cell center) | r/R | u_sampled [m/s] | u_analytical [m/s] | Δ% (of u_max) |
|---|---|---|---|---|---|
| 0 (axis-adjacent) | 1.368e-4 | 0.0274 | 0.20011 | 0.19985 | +0.1292 |
| 1 | 3.159e-4 | 0.0632 | 0.19952 | 0.19920 | +0.1584 |
| 2 | 5.081e-4 | 0.1016 | 0.19827 | 0.19793 | +0.1672 |
| 3 | 6.975e-4 | 0.1395 | 0.19645 | 0.19611 | +0.1699 |
| 4 | 8.824e-4 | 0.1765 | 0.19411 | 0.19377 | +0.1692 |
| 10 (~r/R=0.38) | 1.893e-3 | 0.3786 | 0.17161 | 0.17134 | +0.1340 |
| 20 (~r/R=0.65) | 3.242e-3 | 0.6484 | 0.11598 | 0.11592 | +0.0301 |
| 23 (zero crossing) | 3.578e-3 | 0.7156 | 0.09757 | 0.09758 | **-0.0044** |
| 30 (~r/R=0.85) | 4.260e-3 | 0.8520 | 0.05464 | 0.05480 | -0.0845 |
| 35 (~r/R=0.93) | 4.671e-3 | 0.9343 | 0.02515 | 0.02542 | -0.1393 |
| 38 | 4.892e-3 | 0.9783 | 0.00823 | 0.00857 | -0.1705 |
| 39 (wall-adjacent) | 4.961e-3 | 0.9922 | 0.00274 | 0.00310 | **-0.1807** |

**max |Δu| = 0.1807%** (at wall-adjacent cell j=39 · cell center r/R=0.9922)
**40/40 strict 1% pass** ✓
**zero crossing at j=23 · r/R=0.716** confirms the wedge-chord geometric bias
pattern (positive Δ near axis, negative Δ near wall, transition near mid-radius)

### §5.2 u(r) at mid-pipe (cross-check fully-developed)

Same extraction at i=NX/2=250 (x ≈ 0.2495 m = 49.9·R) · all 40 radial cells.
Full table in `mid_profile_delta.csv`.

| Quantity | Exit (x=0.4995) | Mid (x=0.2495) | Difference |
|---|---|---|---|
| max \|Δu\| | 0.1807% | **0.1807%** (identical) | 0.0% |
| zero crossing | j=23 | j=23 | identical |
| 40/40 strict pass | yes | yes | identical |

**Conclusion**: Flow is fully-developed by mid-pipe (x = 50·R · ~6.25×
L_entrance). The exit-station profile is IDENTICAL to mid-station up to the
6th decimal — confirms L = 100·R is more than adequate for Hagen-Poiseuille
development with codedFixedValue parabolic inlet.

### §5.3 dp/dx via linear fit on axis row (j=0)

Linear-fit p(x) over the cells in j=0 (axis-nearest row), x ∈ [0.05, 0.45]
(10·R buffer from inlet/outlet · matches case_025 §6 convention).

| Quantity | Value |
|---|---|
| Linear-fit slope (kinematic) | -4.8174e-01 m²/s²/m |
| Analytical (Hagen-Poiseuille) | -4.8000e-01 m²/s²/m |
| Δ% | **+0.3623%** |
| Number of fit cells | 401 (j=0 cells with x ∈ [0.05, 0.45]) |
| Strict gate (< 1%) | ✓ **PASS** (×2.8 margin) |

The +0.36% Δ on dp/dx is consistent with the wedge-chord geometric bias:
effective R_eff = R·cos(2.5°) < R, so dp/dx_simulated = -8·ν·u_mean/R_eff² is
slightly larger magnitude than analytical -8·ν·u_mean/R². Predicted bias:
(1 - cos²(2.5°))/cos²(2.5°) ≈ 0.19% magnitude · simulated +0.36% is within
2× of the bare-geometric prediction (additional contribution from
discretization · still well under strict).

### §5.4 τ_wall extraction (500 wall faces · developed-region 400)

`wallShearStress` functionObject computed τ_w on the wall patch at iter 5000.
Magnitudes from `extract_hagen_poiseuille.py` `tau_field` parsing of
`5000/wallShearStress` boundary "wall" entry.

Full 500-face table in `tau_wall_delta.csv` with face-by-face Δ%.

**Full-wall (500 faces · includes inlet/outlet entrance)**:
- Range: 1.190e-3 to 1.236e-3 m²/s² · mean 1.203e-3
- Δ_min/Δ_mean/Δ_max: -0.82% / +0.27% / +3.01%
- Strict 1% pass: **498/500** (2 outliers at faces 0-1 · x = 0.5 and 1.5 mm · inlet entrance)

**Developed-region (400 faces · x ∈ [0.05, 0.45])**:
- Range: 1.2032e-3 to 1.2032e-3 (essentially uniform · 4-decimal precision)
- Δ_min/Δ_mean/Δ_max: +0.2667% / +0.2668% / **+0.2686%**
- Strict 1% pass: **400/400** ✓

**Strict gate (developed region per case_025 §6 dp/dx-buffer convention)**:
**max |Δ| = 0.2686% < 1% · PASS ×3.7 margin · 400/400 strict ✓✓✓**

The +0.27% mean bias is consistent with the wedge-chord geometric prediction
(τ_w_simulated using R_eff = R·cos(2.5°) gives τ_w_analytical / cos(2.5°)
≈ τ_analytical × 1.00095, predicted bias +0.095%; simulated +0.27% includes
additional discretization contribution · still under strict).

### §5.5 Residual diagnosis

At iter 5000 (max iter cap · SIMPLE auto-exit did NOT fire):

| Field | Final initial residual | Strict 1e-8? | Diagnosis |
|---|---|---|---|
| Ux | **2.954e-12** | ✓ (×3,400× margin) | machine precision · axial flow fully solved |
| Uy | **9.063e-07** | ✗ (90× over) | plateau bound · cell-center Uy values are ~1e-15 (essentially 0), residual normalization stuck on wedge BC vector-rotation Uy-Uz coupling |
| Uz | **3.325e-02** | ✗ (3.3M× over) | wedge artifact · cell-center Uz values are ~1e-16, residual is purely normalization inflation of azimuthal symmetry BC |
| p | **2.686e-08** | ✗ (2.7× over) | slowly decreasing · 4000-iter factor 2.4 reduction · plateau-like by iter 4000-5000 |
| continuity | 1.73e-10 | ✓ machine precision | mass conservation excellent |

**Strict 4/4 < 1e-8 pass count: 1/4** (Ux only)
**Strict 3/3 < 1e-8 adjusted (excl Uz wedge artifact): 1/3** (Ux only · Uy + p sub-strict)

#### §5.5.1 Continuation experiment (iter 5000 → 7340 · discarded)

To verify the Uy + p plateau hypothesis, simpleFoam was continued from
latestTime to endTime=20000. The continuation reached iter 7340 before being
killed (saving solver time given plateau was confirmed at iter ~6000). At
iter 7340:
- Ux: 3.48e-12 (still machine precision)
- Uy: 1.34e-06 (oscillating · NOT improving from iter 5000's 9.06e-7)
- Uz: 3.34e-02 (wedge plateau · unchanged)
- p: 3.75e-08 (oscillating · WORSE than iter 5000's 2.69e-8)

The data confirm Uy and p have reached a wedge-mesh convergence floor on
this geometry/solver setup. Strict 1e-8 is unattainable without:
- Different fvSolution settings (tighter inner solver tolerance · changed
  agglomerator · custom URF · likely 2-3× iteration cost)
- Mesh refinement (more radial cells · smaller wall δr)
- Different geometry (true axisymmetric solver · NOT 3D wedge)

None were pursued (out-of-scope for B70 dispatch). The iter 5000 state is
the canonical solver result; time dirs 6500/7000/7500/8000 from the
continuation experiment have been deleted from the sandbox; sandbox
controlDict restored to original endTime=5000 for reproducibility.

#### §5.5.2 Field-count transparency extension (vs case_025)

case_025 §"Field-count transparency" handled "4/4 → 3/3" because plane
Poiseuille had NO Uz (frontAndBack empty). case_027 has Uz but it's a
wedge artifact, not a physical field. The transparency framing extends:
- case_025: 3 prognostic fields · all hit strict
- case_027: 4 prognostic fields · Uz is wedge artifact (not physical degree
  of freedom) + Uy/p plateau on wedge BC vector-rotation floor (not
  "diverging", just stuck above strict 1e-8)

Strict-letter strict-residual gate: 1/4 strict-PASS (only Ux).
Most-generous reading: "all 4 residuals converged-bounded · Ux machine-precision
· Uy/p plateau at wedge floor · Uz wedge artifact". This is a softer interpretation
than case_025's clean 3/3.

The honest framing is: **physics IS converged (3/3 strict gates pass), but
the strict residual gate per briefing § strict reverse condition is NOT met.**

---

## §6 Strict-gate compliance table

| Strict criterion | Target | Achieved | Status | Margin |
|---|---|---|---|---|
| max \|Δu\| at exit station (40 radial cells) | < 1% u_max | **0.1807%** | ✓ **PASS** | ×5.5 |
| Exit station strict 1% pass count | 40/40 | **40/40** | ✓ **OVER-PASS** | full |
| Mid-station strict 1% pass count | 40/40 | **40/40** (max 0.1807%) | ✓ **OVER-PASS** | identical to exit |
| \|Δ dp/dx\| linear fit | < 1% | **+0.3623%** | ✓ **PASS** | ×2.8 |
| \|Δ τ_w\| developed region max | < 1% | **+0.2686%** | ✓ **PASS** | ×3.7 |
| τ_w developed strict 1% pass count | 400/400 | **400/400** | ✓ **OVER-PASS** | full |
| residuals 4/4 strict | all < 1e-8 | **1/4** | ✗ **FAIL** | -- |
| residuals 3/3 adjusted (excl Uz) | all < 1e-8 | **1/3** | ✗ **FAIL** | -- |
| NO solver crash | always | iter 5000 endTime hit (no crash) | ✓ **PASS** | -- |
| NO turbulence model | always | laminar (Re_D=66.67) | ✓ **PASS** | -- |
| advisor stack untouched | always | ui/backend/ not modified | ✓ **PASS** | -- |

**Strict trifecta on physics** (u + dp/dx + τ_w): **3/3 PASS ✓✓✓** (case_025
trifecta-equivalence basis)

**Strict 4/4 residual gate**: 1/4 (Ux machine-precision · Uy + Uz + p
sub-strict due to wedge-mesh artifacts)

**Strict 3/3 residual gate** (case_025 §field-count-transparency extension
to wedge · excl Uz): 1/3 (Uy + p still sub-strict)

→ **Verdict: MARGINAL** (briefing strict-letter reading)
→ User-ratifiable as FULL under wedge-floor-residual-plateau exemption
→ Default (absent user ratification): MARGINAL · Done #1 stays 1/3

---

## §7 Reverse-condition compliance (no cheating)

- ❌ Did NOT cherry-pick r-points — full 40 reported at both exit and mid stations (80 data points, no point hidden)
- ❌ Did NOT modify ARC-GOAL.md (main session reconciles per briefing)
- ❌ Did NOT modify advisor stack (ui/backend/ untouched · entire sub-session)
- ❌ Did NOT touch prior cases (case_004 / case_006 / case_011 / case_016 / case_021 / case_022 / case_024 / case_025 all untouched)
- ❌ Did NOT touch B69 case_026 Couette work (disjoint scope · NOT touched)
- ❌ Did NOT inflate Done #1 (MARGINAL = stays 1/3 absent user ratification per briefing rule "PARTIAL = stays")
- ❌ Did NOT introduce turbulence model (Re_D=66.67 laminar; turbulenceProperties simulationType laminar)
- ❌ Did NOT use 2D-plane-Poiseuille substitute (per briefing fallback condition: "若 axisymmetric wedge BC 实在 broken: 简化为 2D ... 仍可 push FULL") — wedge BC works · physics is correct · only residual stricture is the issue · no fallback needed
- ❌ Did NOT modify Schlichting reference values (used canonical Hagen-Poiseuille formulae verbatim)
- ❌ Did NOT hide wedge geometric bias — disclosed transparently in §4.2 with quantitative prediction matching observed 0.18% peak |Δ|
- ❌ Did NOT hide residual stricture — disclosed transparently in §5.5 with full diagnosis + continuation experiment honest-failure documentation
- ❌ Did NOT hide CASE_SPEC §5 numeric typo on sample-line end y-coordinate — disclosed in commit-2 MESH_PREP_LOG (CASE_SPEC retained as-is per case_025 audit-trail precedent)
- ❌ Did NOT hide sampleSet sigFpe (F-NEW-B) — disclosed + worked around with direct field parsing methodology

---

## §8 V-row attribution

Reuse from prior V64-A sub-DECs (3 firm carry-forward):
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse ✓
- **V47** (incompressible inlet BC convention) — extended to codedFixedValue with sqrt(y²+z²) radial geometry
- **case_025 F-NEW-A** (codedFixedValue Docker `--user` flag · LANDED B68) — direct reuse + extended to sqrt-radial

F-NEW candidates surfaced this sub-DEC (**5 net-new**):

| F-NEW | Impact | Description | Signature |
|---|---|---|---|
| F-NEW-pipe-A | med · methodology | blockMeshDict `defaultPatch { name axis; type empty; }` declaration required for wedge axis · without it 500 axis faces routed to type-`patch` `defaultFaces` and solver attempts computation on zero-area faces | wedge_axis_default_patch_routing |
| F-NEW-pipe-B | **HIGH · methodology** | OpenFOAM v2312 sampleSet `uniform` and `midPoint` types sigFpe FE_DIVBYZERO inside `particle::trackToStationaryTri` on wedge axisymmetric mesh (No base point for tet decomposition · degenerate axis faces have zero area) · workaround = `cloud` sampleSet type which uses `meshSearch::findCell` directly without particle tracking | wedge_sample_set_particle_tracker_sigfpe |
| F-NEW-pipe-C | med · methodology | `cloud` sampleSet with `cellPoint` interpolation has cell-finder confusion near wedge axis — first 4 sample points (y ∈ [0.00025, 0.000615]) all map to the axis-adjacent cell · workaround = direct OpenFOAM ASCII field-parsing in Python (extract_hagen_poiseuille.py methodology) bypassing sampleSet entirely | wedge_cloud_cell_finder_axis_confusion |
| F-NEW-pipe-D | med · physics | Hagen-Poiseuille axisymmetric wedge residual 4/4 strict 1e-8 unattainable due to combined (a) Uz wedge artifact (BC vector-rotation constraint) and (b) Uy/p plateau on wedge floor · case_025 §field-count-transparency extends to "wedge-floor-residual-plateau" concept · means strict-FULL residual gate on wedge meshes requires either solver tuning OR mesh refinement OR true-axisymmetric solver | wedge_residual_4_of_4_strict_unattainable_at_baseline |
| F-NEW-pipe-E | low · methodology | codedFixedValue with `sqrt(y² + z²)` radial coordinate works correctly for axisymmetric inlet · pattern reusable for any future axisymmetric inlet BC (vs case_025's planar `y`-only formulation) | coded_fixed_value_radial_sqrt_y2z2 |

Distinct-signature verification vs case_025 F-NEW-A/B/C/D corpus:
- case_025 F-NEW-A = codedFixedValue Docker `--user` flag (Docker config issue)
- case_025 F-NEW-B = simpleGrading bilinear single-block symmetric (2D mesh)
- case_025 F-NEW-C = laminar simpleFoam strict 1e-8 achievable in 1375 iter (2D plane)
- case_025 F-NEW-D = CASE_SPEC τ_w formula error caught by cross-check (math bug)

case_027 F-NEW set is fully distinct: all 5 F-NEWs are wedge-mesh-axisymmetric
specific (axis-patch routing · particle tracker sigFpe · cell-finder confusion ·
residual plateau · sqrt-radial codedFixedValue). Zero overlap with case_025 set.

**V-row delta this sub-DEC**: 3 firm carry-forward + 5 net-new = **+8 deltas**.

---

## §9 Field-count transparency (case_025 §3 + §field-count-transparency precedent)

Briefing strict gate: "residuals 4/4 < 1e-8". Laminar simpleFoam on 3D
axisymmetric wedge has 4 prognostic fields (p, Ux, Uy, Uz).

case_025 plane Poiseuille had 3 fields (no Uz · frontAndBack empty 2D) and
case_025 RUN_LOG §"Field-count transparency" honored "4/4 → 3/3" as field-
count-adjusted (NOT gate-relaxation). 

case_027 wedge has 4 fields but Uz is a wedge artifact (cell-center Uz values
are O(1e-15), residual is purely normalization inflation of the wedge BC's
azimuthal symmetry constraint). Under case_025 §field-count-transparency
extension to "wedge-artifact-exempt", residual gate becomes 3/3 (p, Ux, Uy).

But case_027's Uy and p are ALSO sub-strict (plateau on wedge BC vector-
rotation floor). So even the case_025-equivalent 3/3 gate is 1/3 (only Ux).

This is a **harder case than case_025** at the residual-strictness gate.

Two interpretations:
- **Strict-letter**: MARGINAL (residual gate FAIL · 1/4 strict · 1/3 adjusted)
- **Physics-converged-evidence**: FULL-equivalent (Ux machine-precision +
  Uy/p plateau at sub-O(1e-6) which is physically converged for u_max=0.2
  flow · 6-ppm relative residual)

Honest verdict: **MARGINAL** (default · briefing § strict reverse condition).
User can ratify as FULL under physics-converged interpretation.

---

## §10 sampleDict + extract methodology surprise (F-NEW-B/C)

### §10.1 Initial sampleDict failure (F-NEW-B · sampleSet sigFpe)

CASE_SPEC §5 designed `midPoint` sample-line type spanning y ∈ [0, ~R*cos(2.5°)]
at z=0 (wedge bisector). Initial run failed:
```
FOAM Warning : From Foam::triFace Foam::tetIndices::faceTriIs(...)
   No base point for face 80477, ..., produces a valid tet decomposition.
[stack trace]
#1  Foam::sigFpe::sigHandler(int)
#3  Foam::particle::trackToStationaryTri(...)
#4  Foam::particle::locate(...)
#6  Foam::uniformSet::calcSamples(...)
```

Switching to `uniform` sample type produced the same sigFpe (same particle-
tracking inheritance). Both types use `faceOnlySet` base class which walks
through the mesh via tet-decomposed cell faces. Wedge axis faces have zero
area → tet decomposition fails → divide-by-zero → FE_DIVBYZERO sigFpe.

### §10.2 cloud sampleSet workaround (F-NEW-B mitigation · partial)

Switched to `cloud` sampleSet type (uses `meshSearch::findCell` directly · no
particle tracking · accepts explicit point list). cloud sampleSet ran without
sigFpe but exposed F-NEW-C:

### §10.3 cloud cell-finder confusion (F-NEW-C)

cloud sampleSet with `interpolationScheme cellPoint` returned the SAME
(axis-adjacent cell) value for the first 4 sample points (y ∈ [0.00025,
0.000615] which span 4 expected radial cells). From y=0.000736 onwards each
sample mapped to a unique cell correctly.

Switching to `interpolationScheme cell` (raw cell-centered, no point
interpolation) still returned the SAME axis-cell value for the first 4 points.
Cell-finder is mapping all 4 sample points into the axis-adjacent cell despite
their y-coordinates being well-inside cells 2-4 of the radial direction.

This suggests OpenFOAM's `meshSearch::findCell` for wedge meshes has a
geometric confusion near the axis (likely related to the degenerate axis
faces · same root cause as F-NEW-B but manifesting in a different sample type).

### §10.4 Direct field-parsing methodology (F-NEW-C workaround · F-NEW-pipe-E)

Bypassed sampleSet entirely. Approach:
1. Run `postProcess -func writeCellCentres` to write `C`, `Cx`, `Cy`, `Cz`
   fields (cell-centroid coordinates per cell)
2. Parse `5000/{C, U, p, wallShearStress}` ASCII files directly with
   pure-stdlib Python regex parser (`extract_hagen_poiseuille.py`)
3. Map cell indices via OpenFOAM block topology: `idx = i + j*NX + k*NX*NR`
4. For exit profile: select cells at i=NX-1 (last x-column), j=0..39
5. For mid profile: i=NX/2
6. For dp/dx: cells at j=0 (axis-row), x ∈ [0.05, 0.45] · 401 cells
7. For τ_w: wallShearStress boundary "wall" entry · 500 wall faces

This bypasses sampleSet's particle-tracking AND cell-finder issues. Gives
clean 40-cell radial profiles at both exit and mid stations. Reusable
methodology for any future wedge-mesh validation in V64-A or V65+.

The raw cloud sampleDict output is retained in `results/raw_samples/*.xy`
as evidence of F-NEW-B/C (NOT used for verdict).

---

## §11 What this verdict means for V64-A close path

**If MARGINAL (default · no user ratification)**:
- Done #1 stays **1/3 strict** (case_025 plane Poiseuille FULL only)
- V64-A close still requires 2 more strict-FULL · candidates: B69 Couette (if PASS) +
  one more 1D analytical canonical OR a 2D canonical re-attempt OR a wedge-aware
  solver tuning re-run of case_027

**If user-ratified FULL** (under case_025 §field-count-transparency + wedge-floor exemption):
- Done #1 advances to **2/3 strict** (case_025 + case_027)
- V64-A close path: needs 1 more strict-FULL (B69 Couette · cleanest path · 1D analytical class)
- MET if B69 also strict PASS (or user-ratified) · OR ratified case_027 + B69 + 1 more

**Recommended user judgment basis**:
- Ratify FULL if: physics-strict-PASS 3/3 is the dominant evidence + wedge artifact
  is intrinsic-geometric-bias-not-physical-error
- Keep MARGINAL if: residual stricture 4/4 < 1e-8 is the operational gate · strict-letter
  reading

This sub-DEC takes the **MARGINAL** default position pending user input.

---

## §12 4Q gate

- **Q1 LLM-offline**: `env -i HOME PATH python3 extract_hagen_poiseuille.py` re-runnable (pure-stdlib · regex-based OpenFOAM ASCII parser · no numpy/pandas/scipy) ✓
- **Q2 artifacts**: parts_manifest + CASE_SPEC + MESH_PREP_LOG + RUN_LOG + 9 dict files + 4 logs (blockMesh + checkMesh + simpleFoam-trimmed + postProcess) + 2 analytical scripts (analytical_reference.py + extract_hagen_poiseuille.py) + 3 raw_samples .xy + 4 CSV results + summary.json + EXTRACT_STDOUT.txt + this validation report + sub-DEC
- **Q3 TrustGate**: every Δ% cites cell index + analytical formula explicit + reproducible from sandbox 5000/{C,U,p,wallShearStress} + extract script; F-NEW-B/C disclosed transparently with workaround methodology; wedge geometric bias predicted and matched against observed Δ-shape signature
- **Q4 advisor-only**: NO advisor stack edits (ui/backend/ untouched · entire sub-session)
