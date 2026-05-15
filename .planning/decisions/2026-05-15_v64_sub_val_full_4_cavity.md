---
decision_id: DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY
title: case_024 Lid-Driven Cavity FULL validation report · 4th FULL attempt · simplest possible canonical (Ghia 1982 · laminar incompressible · 3 Re query points) · PARTIAL (strong) · Done #1 stays 0/3 strict
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-VAL-FULL-4-CAVITY (4th FULL attempt · simplest possible canonical · incompressible · laminar · no transition / shock / rotation / heat / STL)
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed81d0b4ddecbc24eefd62)
confidence: med
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope under existing
V64-A charter (`DEC-V64-A-charter` Accepted 2026-05-15).

**Verdict: PARTIAL (strong) per task brief strict reverse condition.**

Distinguishing across the 4 V64-A FULL attempts to date:

| Attempt | Case | Verdict | Strongest failure mode |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation-induced span-distribution Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup instability after iter 2860 |
| #3 (B63) | case_021 NASA TMR turbulent flat plate | PARTIAL (soft) | kOmegaSST transitional-region under-prediction at low Re_x |
| **#4 (B65) · this DEC** | **case_024 lid-driven cavity** | **PARTIAL (strong)** | **discretization-grid limitation only (5% right-wall jet band on uniform 129×129)** |

Attempt #4 cleared every prior failure mode:
- ✓ no rotation (vs #1)
- ✓ no shock startup (vs #2)
- ✓ no turbulence-model transition zone (vs #3)
- ✓ residuals strict 4/4 < 1e-7 on **3/3** Re cases (best of arc; #3 hit 1/5 strict; #2 unreached)
- ✓ first strict-17/17 in arc: Re=1000 u-centerline max |Δu| = 2.24%
- ✓ aggregate < 1.1% U_lid absolute on 3/3 cases (best of arc)

Remaining strict-gate gap (briefing reverse: max |Δu| < 3% AND max |Δv| < 3% AND res < 1e-7 on 3/3):

1. **Re=1000 v-centerline max 4.10% at x/L=0.9688** — just 1.10 pp outside strict 3% gate, in the right-wall descending-jet band. 13/17 strict-PASS. Cause: uniform 129×129 grid is at the floor for 2nd-order upwind in the steep-gradient region; Ghia 1982's stretched grid would close this gap.
2. **Re=100 v-centerline 5% magnitude over-prediction band** (8/17 strict-PASS, max 5.49%). Same root cause: under-resolution of right-wall jet + corner eddies on uniform grid vs Ghia's stretched.
3. **Re=400 v-centerline one-point 62.29% Δ at x/L=0.9063** — almost certainly **transcription error in our embedded Ghia reference table** (our -0.23827 violates profile monotonicity between -0.22847 @ 0.9453 and -0.44993 @ 0.8594). Without this single point, Re=400 v-centerline is 16/17 strict-PASS with max <2.5%. Honestly recorded; flagged for verification in V64-A retro (V-row V54-new).
4. **Re=100/400 u-centerline small-denominator outliers** at vortex-sign-change y/L points where Ghia value is near-zero (0.00332 / 0.02135) — absolute |Δu| ≤ 0.001 = 0.1% of U_lid; only the relative % metric is inflated.

## Decision

**1. Done #1 verdict**: Stays **0/3 strict FULL** (PARTIAL not FULL per strict reverse condition). Honest stay-at-0/3. 4/4 V64-A FULL attempts now PARTIAL.

**2. Strategic insight (calibration signal for V64-A retro)**: Strict 3%-relative-error gate appears empirically harder to clear than 5% CFD-convention floor at 100k-cell scale with 2nd-order upwind. 4/4 PARTIAL track across very different failure modes (rotation / shock / transition / discretization) suggests the gate is calibration-mismatched with discretization-floor reality, not with solver/physics correctness. Flagged as F-NEW-2 V-row.

**3. Done #2 status**: Stays **3/3 ✓ MET** (already met post-B64; Ghia 1982 + Botella-Peyret 1998 are additional canonical refs but don't add to a 3/3 quota that's already filled).

**4. V-row knowledge update**: +4 firm carry-forward + 4 net-new V-rows + 2 open F-NEW questions documented in validation report §5. V-series knowledge expansion: **+6 deltas this sub-DEC**.

**5. Sandbox preservation**: `~/Desktop/case_024_lid_driven_cavity/case_re{100,400,1000}/` retained for hypothesis-test rerun on stretched grid (V64-A retro candidate B66 work · scope deferred).

## Strict-gate compliance table

| Strict criterion | Target | Achieved | gap |
|---|---|---|---|
| 3/3 cases: max \|Δu\| < 3% across 17 Ghia points | strict | 1/3 (Re=1000 17/17 @ max 2.24%) | -2 cases |
| 3/3 cases: max \|Δv\| < 3% across 17 Ghia points | strict | 0/3 (Re=1000 closest @ max 4.10% on 13/17) | -3 cases |
| 3/3 cases: residuals 4/4 < 1e-7 (laminar field count) | strict | **3/3 ✓** | met |
| 3/3 cases: NO solver crash | always | **3/3 ✓** | met |
| 3/3 cases: NO turbulence model | always | **3/3 ✓ (laminar)** | met |
| 3/3 cases: ARC-GOAL untouched · advisor stack untouched | always | **3/3 ✓** | met |

**Strict trifecta on all 3 Re cases**: 0/3 — Done #1 stays 0/3. **Residual criterion**: 3/3 ✓ (best-of-arc).

## Field-count transparency (briefing reverse condition)

Briefing said `residuals 6/6 < 1e-7`. Laminar simpleFoam has 3 prognostic fields (p, Ux, Uy) + continuity = 4 quantities; no k/omega exists. Strict gate honored via **4/4 < 1e-7** (field-count adjusted for laminar regime, NOT gate relaxed). All 3 cases hit the SIMPLE-converged exit trigger, not endTime exhaustion. Documented in CASE_SPEC §7, RUN_LOG §2, validation report §1 + §8.

## Reverse-condition compliance (no cheating)

- ❌ Did NOT cherry-pick 17 Ghia points — full 17 reported per Re per axis (102 data points, no point skipped, no point hidden)
- ❌ Did NOT modify ARC-GOAL.md
- ❌ Did NOT modify advisor stack (ui/backend/ untouched this entire sub-DEC)
- ❌ Did NOT touch prior cases (case_004 / case_006 / case_011 / case_016 / case_021 / case_022 — all untouched)
- ❌ Did NOT inflate Done #1 (stays 0/3 strict, recorded honestly)
- ❌ Did NOT introduce turbulence model (Re=100/400/1000 laminar regime; turbulenceProperties = laminar)
- ❌ Did NOT modify Ghia 1982 reference values (transcription concern at one point disclosed transparently in report §3.4-note, kept as-is)
- ❌ Did NOT touch BFS work (B66 disjoint scope · case_022 untouched)

## Artifacts

Repo (`.planning/case_profiles/case_024_v64_val_full_4_cavity_dicts/`):
- 1 parts_manifest.yaml + 1 CASE_SPEC.md + 1 MESH_PREP_LOG.md + 1 RUN_LOG.md
- 6 system/ dicts (blockMeshDict + controlDict + fvSchemes + fvSolution + decomposeParDict + sampleDict)
- 2 constant/ dicts (transportProperties template + turbulenceProperties)
- 2 0/ BC fields (U + p)
- 1 BLOCKMESH_LOG.txt + 1 CHECKMESH_LOG.txt
- 3 SIMPLEFOAM_LOG_RE{100,400,1000}_TRIMMED.txt
- 3 CONVERGENCE_TRACE_RE{100,400,1000}.txt
- 1 extract_centerlines.py (180 LOC pure-stdlib)
- 6 results/centerline_Re{100,400,1000}_{u,v}.csv + 1 results/summary.json

Sandbox (`~/Desktop/case_024_lid_driven_cavity/case_re{100,400,1000}/`):
- Full OpenFOAM case dirs with polyMesh/, postProcessing/, time-step output dirs, log.* (preserved for retro rerun)

Validation report: `.planning/validation_reports/v64_case_024_lid_cavity_full.md` (350+ LOC)

RESUME: `.planning/case_profiles/case_024_RESUME.md`

## Codex sync status

**Skipped**. No security boundary (read-only solver + analysis · no auth / signing / authz / operator endpoint). No byte-reproducibility-sensitive path (no canonical manifest bytes / HMAC / zip serialization). No Phase E2E batch (single sub-DEC). Within v2.3 spike-class-adjacent scope per V64-A charter; sub-DEC executed by main session with confidence:med.

## counter

`autonomous_governance: true` — counter +1 (B65; this sub-DEC). Per v2.3 cadence_floor=30, counter remains pure telemetry not a STOP signal. Latest counter value to be reconciled by main session in V64-A arc retro.

## Next action

V64-A arc B65 → B66 transition:
- Reconcile ARC-GOAL with Done #1 stays 0/3 (not advanced)
- Update Notion DEC sync (this DEC + commit hashes)
- Decide V64-A retro timing: 4/4 PARTIAL track is strong calibration signal worth landing in a dedicated retrospective doc (V-row F-NEW-2 → retro candidate B66)
- B66 candidate work: case_022 BFS (disjoint scope · separate substrate already in flight)
