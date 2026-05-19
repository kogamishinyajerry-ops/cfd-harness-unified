# case_027 · RUN_LOG · simpleFoam laminar Hagen-Poiseuille pipe

> Commit 3 of 4 — solver run + sampling + analytical comparison
> Build: opencfd/openfoam-default:2312 · linuxARM64GccDPInt32Opt · macOS Apple Silicon host

## Invocation (verbatim · re-runnable)

```bash
# Bootstrap sandbox (from commit 2)
mkdir -p ~/Desktop/case_027_hagen_poiseuille_pipe/case
cp -r .planning/case_profiles/case_027_v64_pipe_dicts/{system,constant,0} \
      ~/Desktop/case_027_hagen_poiseuille_pipe/case/

# Mesh (from commit 2)
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_027_hagen_poiseuille_pipe/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && blockMesh' > BLOCKMESH_LOG.txt 2>&1

# Solver (non-root for codedFixedValue compile · per case_025 F-NEW-A)
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_027_hagen_poiseuille_pipe/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && simpleFoam' > SIMPLEFOAM_LOG.txt 2>&1

# Write cell-centers for direct field-parsing extraction
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_027_hagen_poiseuille_pipe/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && postProcess -func writeCellCentres -latestTime' \
    >> POSTPROCESS_LOG.txt 2>&1

# Sample u(r) + p(x) via cloud type (NOT uniform/midPoint · F-NEW-B candidate)
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_027_hagen_poiseuille_pipe/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && postProcess -func sampleDict -latestTime -dict system/sampleDict' \
    >> POSTPROCESS_LOG.txt 2>&1

# Extract + compare to Hagen-Poiseuille analytical (Q1 LLM-offline pure-stdlib)
# Reads /case/5000/{C,U,p,wallShearStress} directly · no sampleDict dependency
env -i HOME=$HOME PATH=/usr/bin:/bin python3 extract_hagen_poiseuille.py
```

## Codex sync status

**Skipped**. Same justification as case_025 sub-DEC: no security boundary
(read-only solver + analysis · no auth / signing / authz / operator endpoint).
No byte-reproducibility-sensitive path. No Phase E2E batch. Within v2.3
spike-class-adjacent scope per V64-A charter; sub-DEC executed by main session
with confidence:med.

## codedFixedValue setup (case_025 F-NEW-A re-applied)

Same `--user $(id -u):$(id -g)` flag required for codedFixedValue compile under
Docker (OpenFOAM rejects UID 0). The hagenPoiseuilleProfile profile compiled
successfully; the `dynamicCode/hagenPoiseuilleProfile/` directory persists for
subsequent runs.

This is the **first sqrt(y²+z²) radial computation in codedFixedValue in this
repo**. case_025 plane Poiseuille computed u(y) directly; pipe needs full
radial r-coordinate. F-NEW candidate (low-impact methodology · pattern transfers
to any future axisymmetric inlet BC).

## Convergence summary (5000-iter run · SIMPLE did NOT auto-exit)

| Iter | Ux (init) | Uy (init) | Uz (init · wedge) | p (init) | Notes |
|---|---|---|---|---|---|
| 1 | 4.4e+00 | 1.3e-02 | 3.3e-03 (startup) | 1.0e+00 | initial transient · field uniform 0.1 vs codedFixedValue 0.2-max |
| 500 | (steep) | 5.0e-05 | 5.1e-02 (wedge plateau ~iter 50) | 7.3e-08 | settling · Uz quickly hits wedge plateau |
| 1000 | (steep) | 3.8e-06 | 3.3e-02 | 6.5e-08 | physical convergence advanced; Uz plateaued |
| 2000 | 1.0e-11 | 2.2e-06 | 3.3e-02 | 5.5e-08 | Ux at machine precision; Uy oscillating |
| 3000 | (machine) | 1.6e-06 | 3.3e-02 | 4.1e-08 | Uy plateau emerging |
| 4000 | (machine) | 1.7e-06 | 3.3e-02 | 4.2e-08 | Uy oscillating in 1e-6 band |
| 5000 | **2.95e-12** | **9.06e-07** | **3.32e-02** | **2.69e-08** | endTime reached · SIMPLE auto-exit not fired |

**Final residuals at iter 5000** (verbatim from SIMPLEFOAM_LOG.txt):
```
DILUPBiCGStab:  Solving for Ux, Initial residual = 2.954352553e-12, ...
DILUPBiCGStab:  Solving for Uy, Initial residual = 9.062859092e-07, ...
DILUPBiCGStab:  Solving for Uz, Initial residual = 0.03324559402, ...
GAMG:          Solving for p,  Initial residual = 2.685903838e-08, ...
time step continuity errors : sum local = 1.733741404e-10
```

### Field-count transparency + wedge-residual diagnosis

case_025 plane Poiseuille had 3 prognostic fields (p, Ux, Uy · no Uz because
`frontAndBack` empty 2D). All 3 hit < 1e-8 strict at iter 1375.

case_027 wedge has 4 prognostic fields (p, Ux, Uy, Uz). Detailed diagnosis:

1. **Ux: 2.95e-12 ✓** — at machine precision, ×3,400× margin under strict 1e-8.
   This is the physically-dominant velocity component; the residual proves the
   axial flow is fully solved.

2. **Uy: 9.06e-7 ✗** (90× over strict 1e-8). Plateau bound from ~iter 2000
   onwards. Physically Uy is the radial velocity, which should be exactly 0
   for axisymmetric Hagen-Poiseuille flow. The actual cell-center Uy values
   ARE near-zero (O(1e-15), see `exit_profile_delta.csv` Uy column), but the
   normalized residual stays at 1e-6 because of the wedge BC's vector-rotation
   constraint on Uy/Uz coupling — a known OpenFOAM artifact for 3D axisymmetric
   wedge meshes. Continuation experiment (iter 5000 → 7340) confirmed plateau
   (Uy oscillating 0.5e-6 to 3e-6 with no monotonic decrease; Uy = 1.34e-6 at
   iter 7340 vs 9.06e-7 at iter 5000 — within noise band, not converging
   further).

3. **Uz: 3.32e-2 ✗** (3.3M× over strict 1e-8). **Wedge artifact** — Uz exists
   in the wedge mesh purely to satisfy azimuthal symmetry BC (cell-center Uz
   values O(1e-15), see exit_profile_delta.csv Uz column). Residual is
   normalized inflation, NOT physical Uz error. This is the case_025
   §field-count-transparency situation: case_025 had 3-field count (no Uz);
   case_027 has 4-field count but Uz is wedge-degenerate.

4. **p: 2.69e-8 ✗** (2.7× over strict 1e-8). Slowly decreasing trajectory
   (iter 1000: 6.5e-8 → iter 5000: 2.7e-8 · factor 2.4 reduction in 4000 iter).
   Extrapolated: ~10,000 more iter needed to reach 1e-8. Continuation
   experiment did NOT show monotonic improvement (p oscillated between 2.7e-8
   and 4.2e-8 over iter 5000-7340).

**Strict 4/4 < 1e-8 pass count**: **1/4** (Ux only)
**Strict 3/3 < 1e-8 adjusted (excl Uz wedge artifact)**: **1/3** (Ux only)

This is fundamentally a wedge-mesh-Hagen-Poiseuille convergence limit. Solver
settings (URF, relTol, scheme order) and mesh refinement could push Uy/p
lower but the Uz plateau is intrinsic. We accept the residual gate as
sub-strict and rely on the 3 physics gates (u, dp/dx, τ_w) for verdict.

## Strict-gate verdict (per CASE_SPEC §7 + briefing reverse condition)

| Criterion | Target | Achieved | Status | Margin |
|---|---|---|---|---|
| max \|Δu\| at exit station (40 radial cells) | < 1% u_max | **0.1807%** | ✓ **PASS** | ×5.5 |
| Exit-station strict 1% pass count | ≥17/40 | **40/40** | ✓ **OVER-PASS** | full |
| Mid-station strict 1% pass count (cross-check) | 40/40 | **40/40** (max 0.1807%) | ✓ **OVER-PASS** | identical to exit · confirms fully-developed |
| \|Δ dp/dx\| linear fit on j=0 row x ∈ [0.05, 0.45] | < 1% | **+0.3623%** | ✓ **PASS** | ×2.8 |
| \|Δ τ_w\| developed region x ∈ [0.05, 0.45] (400 faces) | < 1% | **+0.2686%** max | ✓ **PASS** | ×3.7 |
| τ_w developed-region strict 1% pass count | ≥majority | **400/400** | ✓ **OVER-PASS** | full |
| residuals (4-field strict 1e-8) | 4/4 < 1e-8 | **1/4** (Ux only) | ✗ **FAIL** | -- |
| residuals (3-field adjusted excl Uz wedge) | 3/3 < 1e-8 | **1/3** (Ux only) | ✗ **FAIL** | -- |
| NO solver crash | always | iter 5000 endTime hit (no crash) | ✓ **PASS** | -- |
| NO turbulence model | always | laminar (Re_D=66.67) | ✓ **PASS** | -- |
| advisor stack untouched | always | ui/backend/ not modified | ✓ **PASS** | -- |

**Strict trifecta** (u + dp/dx + τ_w developed): **3/3 strict PASS ✓✓✓**
**Strict 4/4 residual gate**: 1/4 (Ux machine-precision, Uy plateau, Uz wedge artifact, p slowly decreasing)

## τ_w boundary effect transparency

Full-wall (500 faces) τ_w range: [−0.82%, +3.01%] · 498/500 within 1% strict.
The 2 outliers (faces 0 and 1, at x ≈ 0.5 mm and 1.5 mm) are within the inlet
entrance region. From face 4 onwards (x > 4 mm), τ_w stabilizes to +0.27%.
Developed-region τ_w (x ∈ [0.05, 0.45]) is essentially uniform: 400/400 within
1% strict, max |Δ| = 0.27%.

This entrance-region exclusion is the SAME convention as `dp/dx`-strict
(case_025 §6 precedent applies x ∈ [0.05, 0.45] for both linear-fit p(x) and
strict-gate τ_w). Reporting both full-wall and developed-region transparently
in `tau_wall_delta.csv` summary.

## sampleDict + extract methodology surprise

Encountered two related issues with OpenFOAM v2312 `postProcess -func sampleDict`
on the wedge axisymmetric mesh:

**Issue 1 (F-NEW-B candidate · sigFpe in midPoint/uniform sampleSet)**: Both
midPoint and uniform sampleSet types failed with sigFpe FE_DIVBYZERO inside
`particle::trackToStationaryTri` during line-set construction. Root cause:
particle tracker walks through cells via tet decomposition, which fails on
zero-area axis faces. Switched to `cloud` sampleSet type (uses
`meshSearch::findCell` directly · no particle tracking). cloud works.

**Issue 2 (F-NEW-C candidate · cell-finder confusion near axis)**: cloud
sampleSet with cellPoint interpolation returned the SAME (axis-cell) value
for the first 4 sample points (y up to 0.000615), then correct values from
y=0.000736 onwards. Cell-finder confusion in OpenFOAM near wedge axis.

**Workaround**: bypassed sampleDict entirely for u(r) and dp/dx extraction.
Wrote `extract_hagen_poiseuille.py` that:
- Uses `postProcess -func writeCellCentres` to write cell centers as `C` field
- Parses `5000/{C, U, p, wallShearStress}` ASCII directly
- Maps cell indices via `idx = i + j*NX + k*NX*NR` (block topology)
- Extracts the exit-station radial profile from cell-centered Ux at `i=NX-1`
- Computes Δ% vs analytical u(r) = 2·u_mean·(1 - (r/R)²) per cell

This gives 40 clean radial samples (all 40 cells, no cell-finder confusion).
Pure-stdlib OpenFOAM ASCII parser (regex-based) · Q1 LLM-offline rerunnable.

This direct-field-parsing approach is a methodology contribution — works
robustly on wedge meshes where OpenFOAM's standard sampleSet types have known
particle-tracking / cell-finder issues. Reusable for future axisymmetric
substrate work in V64-A or V65+.

## Continuation experiment (iter 5000 → 7340 · discarded)

To verify the residual plateau hypothesis, the solver was continued from
latestTime to endTime=20000. The continuation reached iter 7340 before being
killed (saving solver time given the plateau was confirmed). At iter 7340:
- Ux: 3.48e-12 (still machine precision)
- Uy: 1.34e-06 (plateau region · not better than iter 5000's 9.06e-7)
- Uz: 3.34e-02 (wedge plateau · unchanged)
- p:  3.75e-08 (oscillating · NOT monotonically improving from iter 5000's 2.69e-8)

**Conclusion**: Uy and p convergence has reached the solver/mesh floor on
this wedge geometry. Strict 1e-8 is unattainable without different
fvSolution settings or mesh refinement (both out-of-scope for this commit).
The iter 5000 state is taken as canonical for validation reporting; time
dirs 6500/7000/7500/8000 from the continuation experiment have been deleted
from the sandbox. controlDict in sandbox restored to original endTime=5000
for reproducibility.

## Verdict

**MARGINAL** (per briefing reverse condition).

Three physics-strict gates PASS:
- u(r) profile max |Δ| 0.1807% < 1% · 40/40 strict at both exit and mid stations
- dp/dx linear-fit Δ +0.36% < 1%
- τ_w developed-region max |Δ| 0.27% < 1% · 400/400 strict

One residual gate FAILS:
- strict 4/4 < 1e-8 only 1/4 met (Ux machine precision; Uy plateau due to
  wedge BC; Uz wedge artifact; p slow convergence)
- Even field-count adjusted (3/3 excl Uz): only 1/3 met (Uy and p sub-strict)

Per briefing: "max |Δu| < 1% AND residuals 4/4 < 1e-8 AND ..." → not FULL.
Per briefing: "max |Δu| > 3% OR residuals 不收敛 OR wedge BC fail" — none met
(residuals are bounded/converged, just don't reach strict 1e-8 due to wedge
geometry constraint). Falls into a "physics-strict-PASS · residual-stricture-FAIL"
intermediate verdict best classified as **MARGINAL** awaiting user ratification.

Under case_025 §field-count-transparency precedent, an argument could be made
for FULL: Ux machine-precision + Uy/p plateau at wedge-mesh floor + physics
gates all strict-PASS. But this stretches beyond case_025's "Uz doesn't exist"
case (case_027 has Uz that DOES exist · just stuck on wedge artifact). Most
honest verdict: **MARGINAL · user ratifies**.

## Done #1 advancement (anticipated · user ratifies)

- **MARGINAL → Done #1 stays 1/3 strict** (default · briefing rule "PARTIAL = stays" implies MARGINAL also stays absent user ratification)
- **User-ratified FULL → Done #1 → 2/3 strict** (path: ratify Δ residuals as wedge-bounded-convergence, not "不收敛")
- **MET if B69 Couette also strict PASS · OR standalone 1→2/3 strict**

## V-row attribution (anticipated · finalized in validation report)

Reuse from prior V64-A sub-DECs (≥2):
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse ✓
- **V47** (incompressible inlet BC convention) — partial reuse via codedFixedValue radial extension
- **case_025 F-NEW-A** (codedFixedValue Docker `--user` flag) — direct reuse + extended to sqrt-radial geometry

F-NEW candidates surfaced this run:
- **F-NEW-A (med-impact · methodology)**: OpenFOAM wedge requires
  `defaultPatch { name axis; type empty; }` in blockMeshDict to route degenerate
  axis faces (else `defaultFaces` with type patch → solver error)
- **F-NEW-B (HIGH-impact · methodology)**: OpenFOAM v2312 sampleSet `uniform`
  and `midPoint` types sigFpe on wedge mesh degenerate axis (No base point
  for tet decomposition); workaround = `cloud` sampleSet type
- **F-NEW-C (med-impact · methodology)**: cloud sampleSet with cellPoint
  interpolation has cell-finder confusion near wedge axis (first 4 sample
  points map to axis cell). Workaround = direct field-parsing
  (extract_hagen_poiseuille.py methodology)
- **F-NEW-D (med-impact · physics)**: Hagen-Poiseuille wedge residual
  4/4 strict 1e-8 unattainable due to Uz wedge artifact AND Uy/p plateau
  from wedge BC vector-rotation; case_025 §field-count-transparency
  needs extension to "wedge-floor-residual-plateau" concept
- **F-NEW-E (low-impact · methodology)**: codedFixedValue with sqrt(y²+z²)
  radial computation works · pattern reusable for any axisymmetric inlet BC

These F-NEWs receive V-row IDs in validation report (commit 4) §V-row
attribution after distinct-signature verification against existing V100
corpus + case_025 F-NEW-A/B/C/D set.

## 4Q gate

- **Q1 LLM-offline**: `env -i HOME PATH python3 extract_hagen_poiseuille.py`
  re-runnable (pure-stdlib · regex-based OpenFOAM ASCII parser · no numpy/
  pandas/scipy) ✓
- **Q2 artifacts**: SIMPLEFOAM_LOG_TRIMMED.txt + POSTPROCESS_LOG.txt + 3
  postProcessing/sampleDict/.xy raw samples (exitProfile + midProfile +
  axisPressure cloud-typed · NOT USED in final analysis due to F-NEW-B/C
  · retained for transparency) + 4 5000/ field files (C + U + p +
  wallShearStress copied to results/) + extract_hagen_poiseuille.py
  (340 LOC pure-stdlib) + 4 CSV results (exit_profile_delta +
  mid_profile_delta + dpdx_extraction + tau_wall_delta) + summary.json +
  EXTRACT_STDOUT.txt + RUN_LOG.md (this file)
- **Q3 TrustGate**: every u(r), dp/dx, τ_w cites postProcessing/5000/ field
  row + analytical formula explicit (extract_hagen_poiseuille.py · u_analytical
  line 95 + dpdx_kin constant line 49 + tau_wall_kin constant line 50);
  comparison reproducible from 5000/{C,U,p,wallShearStress} alone
- **Q4 advisor-only**: NO advisor stack edits (ui/backend/ untouched · entire
  sub-session)

## Next action

Commit 4: write validation report + sub-DEC frontmatter+body · update RESUME
with MARGINAL verdict + Done #1 stays 1/3 (absent user ratification) · main
session reconciles ARC-GOAL + Notion sync (only sync if user ratifies as FULL
or accepts MARGINAL as Accepted DEC).
