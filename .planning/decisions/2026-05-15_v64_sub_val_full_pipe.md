---
decision_id: DEC-V64-A-sub-M-V64A-VAL-FULL-PIPE
title: case_027 Hagen-Poiseuille pipe MARGINAL validation report · 8th FULL attempt · axisymmetric 1D-equivalent canonical (Schlichting §5.1.2 · r-parabolic u(r) · Re_D=66.67 deep laminar) · physics-strict-PASS 3/3 (u + dp/dx + τ_w all < 1%) · residual-stricture-FAIL · wedge-floor · user-ratifiable as FULL
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-VAL-FULL-PIPE (B70 dispatch · companion to B68 plane Poiseuille FULL · companion to B69 Couette dispatch · all 1D analytical canonical class · disjoint scope)
notion_sync_status: pending (session-end batch · only Accepted DECs sync per v2.3 round-1)
confidence: med
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope under existing V64-A charter (`DEC-V64-A-charter` Accepted 2026-05-15).

**Verdict: MARGINAL** per briefing strict-letter reading (physics-strict-PASS 3/3 · residual-stricture-FAIL 1/4 strict).

User-ratifiable as **FULL** under case_025 §field-count-transparency extension to wedge-floor-residual-plateau exemption (Ux machine-precision + Uy/p plateau at wedge BC vector-rotation floor + Uz wedge artifact · all physics gates strict-PASS).

This is the **8th FULL attempt** in the V64-A Tier 2 arc:

| Attempt | Case | Verdict | Strongest issue |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup |
| #3 (B63) | case_021 NASA TMR flat plate | PARTIAL (soft) | residuals plateau 3-5e-5 |
| #4 (B65) | case_024 lid-driven cavity Re=1000 | PARTIAL (strong) | 129² uniform-grid v-discrepancy |
| #5 (B66) | case_022 Driver-Seegmiller BFS | PARTIAL | uniform inlet δ/h gap |
| #6 (B67) | case_024 cavity v2 | PARTIAL v2 | physics regression v 4.10→6.49% |
| #7 (B68) | case_025 plane Poiseuille | **FULL ✓** | (none · clean PASS · max 0.0425%) |
| **#8 (B70) · this DEC** | **case_027 Hagen-Poiseuille pipe** | **MARGINAL** | physics-strict-PASS 3/3 · residual-stricture-FAIL · wedge-floor |

Strict trifecta on physics achieved cleanly:
- ✓ max |Δu| = 0.1807% at exit station (margin ×5.5 below 1% gate · 40/40 strict-PASS)
- ✓ |Δ dp/dx| = +0.3623% from linear fit (margin ×2.8 below 1% gate)
- ✓ |Δ τ_w| developed region = +0.2686% max (margin ×3.7 · 400/400 strict-PASS)

Strict residual gate sub-strict:
- ✗ Ux: 2.95e-12 ✓ machine precision (×3,400× margin under strict)
- ✗ Uy: 9.06e-7 (90× over strict · plateau on wedge BC vector-rotation floor)
- ✗ Uz: 3.32e-2 (wedge artifact · cell-center Uz values ~1e-15 · residual is BC normalization inflation)
- ✗ p:  2.69e-8 (2.7× over strict · slowly decreasing)
- Strict 4/4: 1/4
- Strict 3/3 adjusted (excl Uz wedge artifact per case_025 §field-count): 1/3 (Uy + p still sub-strict)

Mid-pipe cross-check (x = 50·R) confirms fully-developed flow: max |Δu| identical 0.1807%, 40/40 strict.

## Decision

**1. Done #1 verdict**: 

Default (this sub-DEC's position absent user ratification): **Done #1 stays 1/3 strict** (case_025 plane Poiseuille FULL only · per briefing rule "PARTIAL = stays" extended to MARGINAL).

User-ratifiable path: If user ratifies under case_025 §field-count-transparency extension to wedge-floor (Ux machine-precision + Uy/p plateau-at-mesh-floor + Uz wedge artifact + physics-gates strict-PASS 3/3), then Done #1 advances **1/3 strict → 2/3 strict**.

**Recommendation to main session**: Present this verdict to user for explicit
ratification decision. Two evidence sets:
- **Physics evidence** (suggests FULL-equivalent): u 0.18% + dp/dx 0.36% + τ_w 0.27% all far under 1% strict · 40/40 + 400/400 strict pass counts · zero solver crash · canonical-textbook-physics-correct
- **Residual evidence** (suggests MARGINAL strict-letter): 1/4 strict 1e-8 met · Uy + Uz + p sub-strict due to wedge geometry · continuation experiment confirmed plateau · not "diverging" but not strict-letter

This sub-DEC takes the conservative default position: **MARGINAL · Done #1 stays 1/3**. Main session can update on user ratification.

**2. Methodological inflection (calibration signal for V64-A retro)**:

The 8th attempt at THE simplest analytical canonical for axisymmetric flow has revealed:

- **1D-analytical-canonical → physics-strict-PASS is robust across geometry class** (plane B68 0.04% u-error + pipe B70 0.18% u-error · both well under 1% gate)
- **1D-analytical-canonical → residual-strict-PASS is fragile when geometry introduces wedge artifacts** (plane B68 reached 3/3 < 1e-8 trivially in 1375 iter; pipe B70 cannot reach 4/4 < 1e-8 at any iter count due to wedge BC's Uz normalization + Uy/p plateau)
- **case_025 §field-count-transparency precedent needs extension** from "Uz doesn't exist (2D)" to "Uz exists but is wedge artifact (3D axisymmetric)" — a softer interpretation requiring user ratification

V-row F-NEW-pipe-D documents this calibration insight (med-impact physics F-NEW).

**3. Done #2 status**: Stays **3/3 ✓ MET** (already met post-B64; Schlichting §5.1.2 is additional canonical ref but doesn't add to filled 3/3 quota — per case_024/025 precedent).

**4. V-row knowledge update**: **+3 firm carry-forward + 5 net-new V-rows = +8 deltas** this sub-DEC (parity with case_025; signature distinctness verified):

  - Firm carry-forward (3): V100 (incompressible canonical advisor stack baseline) · V47 (incompressible inlet BC convention · extended to sqrt-radial) · case_025 F-NEW-A (codedFixedValue Docker `--user` flag · directly reused)
  - F-NEW-pipe-A (med-impact methodology): OpenFOAM wedge requires `defaultPatch { name axis; type empty; }` in blockMeshDict to route degenerate axis faces (else type-patch defaultFaces · solver errors)
  - F-NEW-pipe-B (**HIGH-impact methodology**): OpenFOAM v2312 sampleSet `uniform`/`midPoint` types sigFpe FE_DIVBYZERO inside `particle::trackToStationaryTri` on wedge axisymmetric mesh · workaround = `cloud` sampleSet type
  - F-NEW-pipe-C (med-impact methodology): cloud sampleSet cell-finder confusion near wedge axis (first 4 sample points map to axis cell · independent of cellPoint vs cell interpolation) · workaround = direct OpenFOAM ASCII field-parsing in Python
  - F-NEW-pipe-D (med-impact physics): Hagen-Poiseuille axisymmetric wedge residual 4/4 strict 1e-8 unattainable due to combined Uz wedge artifact + Uy/p plateau · case_025 §field-count-transparency needs extension to "wedge-floor-residual-plateau" concept
  - F-NEW-pipe-E (low-impact methodology): codedFixedValue with `sqrt(y²+z²)` radial coordinate works correctly · pattern reusable for axisymmetric inlet BC

All 5 F-NEWs are wedge-mesh-axisymmetric-specific. Zero overlap with case_025 F-NEW set (which was 2D plane mesh + math bug). Distinct signatures verified.

**5. Sandbox preservation**: `~/Desktop/case_027_hagen_poiseuille_pipe/case/` retained (postProcessing/ + dynamicCode/ compiled .so + time dirs 0, 4500, 5000 · continuation time dirs 6500/7000/7500/8000 explicitly deleted to keep canonical state at iter 5000 reproducible · sandbox controlDict restored to original endTime=5000). Scope-deferred (not committed to repo · ephemeral).

## Strict-gate compliance table

| Strict criterion | Target | Achieved | Margin |
|---|---|---|---|
| max \|Δu\| at exit station (40 radial cells) | < 1% u_max | **0.1807%** | ×5.5 |
| Exit station strict 1% pass count | 40/40 | **40/40** | full |
| Mid-station strict 1% pass count (cross-check) | 40/40 | **40/40** (max 0.1807%) | over-PASS |
| \|Δ dp/dx\| linear fit | < 1% | **+0.3623%** | ×2.8 |
| \|Δ τ_w\| developed region max | < 1% | **+0.2686%** | ×3.7 |
| τ_w developed strict 1% pass count | 400/400 | **400/400** | full |
| residuals 4/4 strict | all < 1e-8 | **1/4** | -- |
| residuals 3/3 adjusted (excl Uz wedge) | all < 1e-8 | **1/3** | -- |
| NO solver crash | always | iter 5000 endTime (no crash) | met |
| NO turbulence model | always | laminar Re_D=66.67 | met |
| ARC-GOAL + advisor stack untouched | always | untouched | met |

**Strict trifecta on physics** (u + dp/dx + τ_w): ✓✓✓ **3/3 strict-PASS**
**Strict 4/4 residual**: 1/4 (Ux machine-precision · Uy + Uz + p sub-strict)

→ **MARGINAL** (briefing strict-letter · physics-strict-PASS 3/3 + residual-stricture-FAIL)

## Field-count transparency (case_025 §3 + §field-count-transparency extension)

Briefing reverse condition: "residuals 4/4 < 1e-8". Laminar simpleFoam on 3D
axisymmetric wedge has 4 prognostic fields (p, Ux, Uy, Uz).

case_025 plane Poiseuille had 3 fields (no Uz · frontAndBack empty 2D) and
case_025 sub-DEC §"Field-count transparency" honored "4/4 → 3/3" as field-
count-adjusted under "2D field-count" precedent (NOT gate-relaxation).

case_027 wedge has 4 fields but Uz is a wedge artifact:
- Cell-center Uz values are O(1e-15) (essentially zero)
- Residual at 3.3e-2 is normalization inflation from wedge BC's azimuthal
  symmetry constraint, not physical Uz error
- Physically axisymmetric flow has NO Uz degree of freedom

Under case_025 precedent extended to wedge, residual gate could be "3/3 (p, Ux, Uy)"
treating Uz as field-count-artifact. But case_027's Uy and p are also sub-strict
(plateau on wedge BC vector-rotation floor), so even adjusted 3/3 is 1/3 met
(only Ux).

This is a **harder case than case_025** at residual strictness. Two interpretations:

- **Strict-letter** (briefing literal · case_027 verdict default): MARGINAL · residual gate FAIL · 1/4 or 1/3 adjusted
- **Physics-converged-evidence** (case_025 §field-count-transparency extended): FULL-equivalent · Ux machine-precision + Uy/p plateau at wedge floor is "physically converged" (cell-center Uy ~1e-15 m/s, residual norm 9e-7 is normalized to inlet's Uy=0 baseline which makes the relative residual high but absolute value is 0)

Default this sub-DEC: **MARGINAL**. User can ratify alternative.

## Wedge geometric bias transparency (intrinsic ~0.2% peak |Δ|)

The wedge mesh's wall face is a flat quad chord-approximating the curved
pipe wall. At the wedge bisector plane (z=0), the wall is at radial position
r = R·cos(2.5°) = 0.004995 (NOT r = R = 0.005). This is a 0.1%-R geometric
bias intrinsic to the 5° wedge approximation.

Effect on u(r) — the observed +0.13% to -0.18% smooth Δ% gradient (positive
near axis, negative near wall, zero crossing at r/R≈0.72) — matches the
predicted wedge-chord geometric bias pattern. The peak |Δ| (0.18%) occurs at
the wall-adjacent cell, exactly matching CASE_SPEC §10 risk flag
`wedge_axis_discretization` prediction.

This bias is **intrinsic geometric approximation**, not solver/discretization
error. Would persist at infinite mesh refinement. Could be reduced by smaller
wedge angle (e.g., 1° giving 0.004%-R bias) but at cost of more skewed cells.
Out-of-scope for this sub-DEC.

## Reverse-condition compliance (no cheating)

- ❌ Did NOT cherry-pick r-points — full 40 cell-centered radial values reported at both exit and mid stations (80 data points · zero hidden)
- ❌ Did NOT modify ARC-GOAL.md (main session reconciles per briefing)
- ❌ Did NOT modify advisor stack (ui/backend/ untouched · entire sub-session)
- ❌ Did NOT touch prior cases (case_004/006/011/016/021/022/024/025 untouched)
- ❌ Did NOT touch B69 case_026 Couette work (disjoint scope · NOT touched)
- ❌ Did NOT inflate Done #1 (MARGINAL default = stays 1/3 absent user ratification)
- ❌ Did NOT introduce turbulence model (Re_D=66.67 laminar)
- ❌ Did NOT use 2D-plane-Poiseuille substitute (per briefing fallback "若 wedge BC 实在 broken: 简化为 2D variant · 仍可 push FULL") — wedge BC works · physics correct · only residual stricture issue · no fallback needed (would be claim-inflation)
- ❌ Did NOT modify Schlichting reference values (used canonical Hagen-Poiseuille formulae verbatim from §5.1.2)
- ❌ Did NOT hide wedge geometric bias — disclosed quantitatively in validation report §4.2 with prediction matching observed Δ-pattern
- ❌ Did NOT hide residual stricture — disclosed transparently in validation report §5.5 with full diagnosis + continuation experiment honest-failure documentation
- ❌ Did NOT hide F-NEW-B/C sampleSet sigFpe/cell-finder issues — disclosed + worked around with direct field-parsing methodology in extract_hagen_poiseuille.py
- ❌ Did NOT hide CASE_SPEC §5 numeric typo (committed earlier) — disclosed in MESH_PREP_LOG + validation report

## Artifacts

Repo (`.planning/case_profiles/case_027_v64_pipe_dicts/`):
- 1 parts_manifest.yaml + 1 CASE_SPEC.md + 1 MESH_PREP_LOG.md + 1 RUN_LOG.md
- 5 system/ dicts (blockMeshDict + controlDict + fvSchemes + fvSolution + sampleDict)
- 2 constant/ dicts (transportProperties + turbulenceProperties laminar)
- 2 0/ BC fields (U codedFixedValue sqrt-radial + p)
- 1 BLOCKMESH_LOG.txt + 1 CHECKMESH_LOG.txt + 1 SIMPLEFOAM_LOG_TRIMMED.txt + 1 POSTPROCESS_LOG.txt
- 2 analytical scripts (analytical_reference.py 110 LOC + extract_hagen_poiseuille.py 340 LOC · pure-stdlib · Q1 LLM-offline rerunnable)
- 3 results/raw_samples/ .xy files (cloud sampleSet output · evidence of F-NEW-B/C · NOT used for verdict)
- 4 results/ CSV (exit_profile_delta + mid_profile_delta + dpdx_extraction + tau_wall_delta) + analytical_reference.csv
- 2 results/ stdout text (EXTRACT_STDOUT + ANALYTICAL_REFERENCE_STDOUT)
- 1 results/summary.json

Sandbox (`~/Desktop/case_027_hagen_poiseuille_pipe/case/`, NOT committed):
- Full OpenFOAM case dir with polyMesh/, postProcessing/, dynamicCode/.so, time dirs 0/, 4500/, 5000/ (preserved for retro rerun)
- controlDict restored to original endTime=5000 after continuation experiment discarded

Validation report: `.planning/validation_reports/v64_case_027_hagen_poiseuille_full.md` (~700 LOC · §1-§12)

## Codex sync status

**Skipped**. No security boundary (read-only solver + analysis · no auth / signing / authz / operator endpoint). No byte-reproducibility-sensitive path (no canonical manifest bytes / HMAC / zip serialization). No Phase E2E batch (single sub-DEC). Within v2.3 spike-class-adjacent scope per V64-A charter; sub-DEC executed by main session with confidence:med. Same skip justification as case_025 sub-DEC (B68).

## counter

`autonomous_governance: true` — counter +1 (B70; this sub-DEC). Per v2.3 cadence_floor=30, counter remains pure telemetry not a STOP signal. Latest counter value to be reconciled by main session in V64-A arc retro (Done #1 1/3 → 1/3 stays OR → 2/3 strict on user ratification).

## Next action (main session reconciles)

V64-A arc B70 → main-session-reconcile → B71 path:

1. **Reconcile ARC-GOAL with verdict**: 
   - Default (no user input): Done #1 stays 1/3, add MARGINAL row for B70 case_027
   - User-ratified FULL: Done #1 → 2/3 strict, update progress counter
   
2. **Present user ratification decision** with two evidence sets (physics-strict-PASS 3/3 vs residual-stricture-FAIL 1/4) — see §11 of validation report for recommended framing

3. **Update Notion DEC sync** (session-end batch per v2.3 round-1 · only Status=Accepted DECs sync) — this sub-DEC + commit hashes

4. **B71 candidate path** depends on user ratification:
   - **If ratified FULL**: Done #1 2/3 → B71 = M-V64A-CLOSE-DEC + Done #4 ratify (if B69 Couette also PASS for 3/3 total) OR another 1D analytical canonical for safety (e.g., Couette analytical separate from B69 if disjoint)
   - **If MARGINAL stands**: Done #1 stays 1/3 → B71 = (a) tune solver to push case_027 residuals below strict 1e-8 (URF + relTol + agglomerator changes · ~2-3× iter cost · uncertain if Uy plateau breakable) OR (b) different 1D analytical canonical class (e.g., circular Couette · annular Poiseuille) OR (c) B69 Couette + accept B70 as MARGINAL and aim for 2/3 if B69 PASS + 1 more

5. **V64-A close path remains viable** under both ratification outcomes; only the iteration count to 3/3 strict differs.

6. **Methodological wedge-mesh-knowledge captured**: F-NEW-pipe-A/B/C/D/E corpus is a substantial methodology contribution. Future axisymmetric work in V64-A or V65+ can reuse the direct-field-parsing methodology and avoid the sampleSet pitfalls.
