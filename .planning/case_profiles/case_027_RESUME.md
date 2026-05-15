# case_027 · Hagen-Poiseuille pipe · RESUME

> Case ID: case_027_hagen_poiseuille_pipe
> Status: **MARGINAL** (B70 · 2026-05-15) · physics-strict-PASS 3/3 · residual-stricture-FAIL · user-ratifiable as FULL
> Parent: V64-A · Sub-DEC: DEC-V64-A-sub-M-V64A-VAL-FULL-PIPE (Accepted)
> Validation report: `.planning/validation_reports/v64_case_027_hagen_poiseuille_full.md`

## TL;DR

8th FULL attempt in V64-A Tier 2 · axisymmetric 1D-equivalent canonical
(Schlichting BLT §5.1.2 Hagen-Poiseuille pipe flow) on 20,000-cell 5° wedge
mesh, simpleFoam laminar.

| Strict gate | Achieved | Status |
|---|---|---|
| u(r) max \|Δ\| | 0.1807% | ✓ PASS (×5.5 margin · 40/40) |
| dp/dx \|Δ\| | +0.3623% | ✓ PASS (×2.8 margin) |
| τ_w developed-region max \|Δ\| | +0.2686% | ✓ PASS (×3.7 margin · 400/400) |
| residuals 4/4 < 1e-8 | 1/4 (Ux only) | ✗ FAIL (Uy + p plateau · Uz wedge artifact) |

**Verdict: MARGINAL** · Done #1 stays 1/3 strict absent user ratification.
User-ratifiable as FULL under case_025 §field-count-transparency extension
to wedge-floor-residual-plateau.

## Commits (4 atomic · 2026-05-15)

1. `de1fe86` · feat(v64-pipe): case_027 substrate prep
2. `39fb784` · feat(v64-pipe): case_027 mesh prep · blockMesh + checkMesh
3. `ffc376c` · feat(v64-pipe): simpleFoam run + 40-cell extraction · verdict MARGINAL
4. (this commit) · docs(v64-pipe): validation report + sub-DEC

## Artifacts

Repo `.planning/case_profiles/case_027_v64_pipe_dicts/`:
- parts_manifest.yaml · CASE_SPEC.md · MESH_PREP_LOG.md · RUN_LOG.md
- system/{blockMeshDict, controlDict, fvSchemes, fvSolution, sampleDict}
- constant/{transportProperties, turbulenceProperties}
- 0/{U codedFixedValue sqrt-radial, p}
- BLOCKMESH_LOG.txt · CHECKMESH_LOG.txt · SIMPLEFOAM_LOG_TRIMMED.txt · POSTPROCESS_LOG.txt
- analytical_reference.py (110 LOC pure-stdlib) · extract_hagen_poiseuille.py (340 LOC pure-stdlib)
- results/{exit,mid}_profile_delta.csv · dpdx_extraction.csv · tau_wall_delta.csv
- results/raw_samples/ (cloud sampleSet output · F-NEW-B/C evidence)
- results/summary.json · EXTRACT_STDOUT.txt · ANALYTICAL_REFERENCE_STDOUT.txt

Sandbox `~/Desktop/case_027_hagen_poiseuille_pipe/case/` (NOT committed):
- polyMesh/ · postProcessing/ · dynamicCode/.so · time dirs 0, 4500, 5000
- controlDict restored to original endTime=5000 after continuation experiment

Validation report: `.planning/validation_reports/v64_case_027_hagen_poiseuille_full.md` (~700 LOC)

## V-row attribution

- 3 firm carry-forward: V100 · V47 (extended sqrt-radial) · case_025 F-NEW-A (Docker --user)
- 5 net-new F-NEW: F-NEW-pipe-A (axis defaultPatch) · F-NEW-pipe-B HIGH (sampleSet sigFpe) · F-NEW-pipe-C (cloud cell-finder confusion) · F-NEW-pipe-D (wedge residual 4/4 strict unattainable) · F-NEW-pipe-E (sqrt-radial codedFixedValue)
- Distinct signatures vs case_025 F-NEW corpus (zero overlap)
- **+8 V-row deltas** this sub-DEC

## Done dim advancement (anticipated · main session reconciles)

- **Default (no user ratification)**: Done #1 stays **1/3 strict** (case_025 plane Poiseuille FULL only · case_027 = MARGINAL)
- **User-ratified FULL**: Done #1 → **2/3 strict** (case_025 + case_027) · path to V64-A close becomes: needs 1 more strict-FULL (B69 Couette is the obvious candidate)
- Done #2 stays 3/3 ✓ MET (Schlichting §5.1.2 is additional reference, doesn't add to quota)
- Done #6 V-row gain: +8 deltas this sub-DEC

## Counter

`autonomous_governance_counter_v61` += 1 (B70 case_027 · this sub-DEC). Pure
telemetry per v2.3.

## Next action (main session)

1. Reconcile ARC-GOAL with B70 verdict (MARGINAL default · Done #1 stays 1/3)
2. Present user ratification decision (FULL vs MARGINAL) with evidence summary
3. Notion sync (session-end batch · only Accepted DECs · this sub-DEC qualifies)
4. B71 routing depends on B69 outcome + B70 user ratification:
   - Both PASS / B70 ratified FULL → Done #1 2-3/3 → V64-A close path
   - Both MARGINAL/PARTIAL → Done #1 stays 1/3 → more strict-FULL attempts needed
