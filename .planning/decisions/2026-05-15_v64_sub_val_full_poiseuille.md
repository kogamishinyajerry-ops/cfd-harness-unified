---
decision_id: DEC-V64-A-sub-M-V64A-VAL-FULL-POISEUILLE
title: case_025 plane Poiseuille FULL validation report · 6th FULL attempt · THE simplest analytical canonical (Schlichting §5.1.1 · 1D parabolic u(y) · Re=133 deep laminar) · STRICT FULL trifecta first time in V64-A arc · Done #1 0/3 → 1/3 strict
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-VAL-FULL-POISEUILLE (B67 dispatch · companion to B66 BFS PARTIAL · companion to parallel B67 cavity-v2 work · disjoint scope)
notion_sync_status: pending session-end batch
confidence: med
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope under existing V64-A charter (`DEC-V64-A-charter` Accepted 2026-05-15).

**Verdict: FULL** per task brief strict reverse condition.

This is the **first strict-FULL outcome** in the V64-A Tier 2 arc (6 attempts to date):

| Attempt | Case | Verdict | Strongest failure mode |
|---|---|---|---|
| #1 (B56/57) | case_004 NREL Phase VI Seq S | PARTIAL v4 | blade CAD bug + rotation-induced span Δ |
| #2 (B59) | case_006 ONERA M6 transonic | PARTIAL v2 | rhoSimpleFoam shock-startup instability |
| #3 (B63) | case_021 NASA TMR flat plate | PARTIAL (soft) | residuals plateau 3-5e-5 |
| #4 (B65) | case_024 lid-driven cavity Re=100/400/1000 | PARTIAL (strong) | 129² uniform-grid v-discrepancy at right-wall jet |
| #5 (B66) | case_022 Driver-Seegmiller BFS | PARTIAL | uniform inlet δ/h gap → x_R/h 5.44 vs 6.26 |
| **#6 (B67) · this DEC** | **case_025 plane Poiseuille** | **FULL** ✓ | **(none · clean PASS)** |

Strict trifecta achieved on first try:
- ✓ max |Δu| = 0.0425% at exit station (margin ×24 below 1% gate · 40/40 strict-PASS)
- ✓ |Δ dp/dx| = -0.1233% from linear fit (margin ×8 below 1% gate)
- ✓ residuals 3/3 < 1e-8 (p=7.36e-11 · Ux=3.22e-12 · Uy=9.86e-9 · all below; laminar field-count adjusted per case_024 §2 precedent)
- ✓ no solver crash (SIMPLE auto-converged at iter 1375)
- ✓ no turbulence model (laminar Re=133.3)
- ✓ advisor stack untouched

Mid-channel cross-check (x = 25·H) confirms fully-developed flow preservation: max |Δu| 0.286%, 40/40 strict.

τ_w cross-check (NOT in strict trifecta) — sampled mean Δ_mean = -0.56% vs corrected analytical 3·ν·u_mean/H = 4.5e-4 m²/s². CASE_SPEC §4 originally listed wrong formula (2·ν·u_mean/H = 3.0e-4); cross-check caught the error · documented transparently in validation report §3.1.

## Decision

**1. Done #1 verdict**: Advances **0/3 strict → 1/3 strict FULL** (standalone strict-PASS per briefing § reverse condition "OR standalone 0→1/3 strict ✓").

  Cumulative could reach 2/3 strict if parallel B67 cavity-v2 work (committed in disjoint scope `.planning/case_profiles/case_024_v64_cavity_v2_dicts/` + `.planning/validation_reports/v64_case_024_lid_cavity_full_v2.md` + `.planning/decisions/2026-05-15_v64_sub_val_full_cavity_v2.md`) is independently ratified by user as standalone strict-PASS. This sub-DEC takes NO position on cavity-v2 verdict per briefing § out-of-scope.

**2. Methodological inflection (calibration signal for V64-A retro)**: The 6th attempt at THE simplest analytical canonical clearing strict-FULL on first try is strong evidence that:
  - V64-A infrastructure (mesh + solver + extraction + comparison pipeline) is sound
  - 5 prior PARTIAL attempts (B56-B66) were real-physics-driven, NOT infrastructure-driven
  - 4/4 PARTIAL track noted in case_024 §calibration-signal (DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY §Decision item 2) — the "discretization-floor reality" hypothesis is now further calibrated: simpler canonicals can clear strict gate; physics-complex canonicals show the gate-vs-floor mismatch.
  - V-row F-NEW-D below documents this inflection.

**3. Done #2 status**: Stays **3/3 ✓ MET** (already met post-B63; Schlichting §5.1.1 + White §3.3.1 are additional canonical refs but don't add to filled 3/3 quota — per case_024 sub-DEC item 3 precedent).

**4. V-row knowledge update**: **+2 firm carry-forward + 4 net-new V-rows = +6 deltas** this sub-DEC (parity with case_024 cavity sub-DEC; signature distinctness verified vs existing V100 corpus):

  - Firm carry-forward (2): V100 (incompressible canonical advisor stack baseline) · V47 (incompressible inlet BC convention)
  - F-NEW-A (med-impact): codedFixedValue under Docker container needs `--user $(id -u):$(id -g)` flag (OpenFOAM blocks dynamic-code compile under UID 0)
  - F-NEW-B (med-impact): simpleGrading bilinear single-block symmetric `((0.5 0.5 3) (0.5 0.5 0.333333))` — first in repo · differs from case_022 multi-region multi-block bilinear
  - F-NEW-C (low-impact baseline): laminar simpleFoam Ux residual achievable 3.22e-12 on Re=133 plane Poiseuille in 1375 iter (residual-depth-by-physics-complexity baseline)
  - F-NEW-D (HIGH-impact methodology): CASE_SPEC τ_w formula error (factor 2 vs 3 in 3·ν·u_mean/H) caught by physics cross-check · validates pipeline diagnostic value · highlights need for derivation-chain documentation in future CASE_SPECs

**5. Sandbox preservation**: `~/Desktop/case_025_poiseuille_channel/case/` retained (postProcessing/ + dynamicCode/ compiled .so + final-iter time dirs) for retro-rerun availability · scope-deferred (not committed to repo · ephemeral).

## Strict-gate compliance table

| Strict criterion | Target | Achieved | Margin |
|---|---|---|---|
| max \|Δu\| at exit station (40 y-points) | < 1% u_max | **0.0425%** | ×24 |
| Exit station strict 1% pass count | 40/40 | **40/40** | full |
| Mid-station strict 1% pass count (cross-check) | 40/40 | **40/40** (max 0.286%) | over-PASS |
| \|Δ dp/dx\| linear fit | < 1% | **-0.1233%** | ×8 |
| residuals (laminar 3-field count) | all < 1e-8 | **3/3** ✓ | (Uy ×1.01 tightest) |
| τ_w cross-check Δ_mean | < 2% | **-0.56%** | ×3.6 |
| NO solver crash | always | **converged iter 1375** | met |
| NO turbulence model | always | **laminar** | met |
| ARC-GOAL untouched · advisor stack untouched | always | **untouched** | met |

**Strict trifecta** (u 1% AND dp/dx 1% AND residuals 1e-8): ✓✓✓ **3/3 strict-PASS** · **FULL VERDICT**

## Field-count transparency (briefing reverse condition · per case_024 §2 precedent)

Briefing said `residuals 4/4 < 1e-8`. Laminar simpleFoam has 3 prognostic fields (p, Ux, Uy) — no k/ω; Uz is not solved in 2D. Strict gate honored via **3/3 < 1e-8** (field-count adjusted for laminar regime, NOT gate relaxed). Time-step continuity errors (6.27e-11 sum local) are reported as informational. All 3 fields hit the SIMPLE-converged auto-exit trigger, not endTime exhaustion. Documented in CASE_SPEC §7 + RUN_LOG §convergence + validation report §5.

## Reverse-condition compliance (no cheating)

- ❌ Did NOT cherry-pick y-points — full 40 reported at both exit and mid stations (80 data points, no point hidden)
- ❌ Did NOT modify ARC-GOAL.md
- ❌ Did NOT modify advisor stack (ui/backend/ untouched · entire sub-session)
- ❌ Did NOT touch prior cases (case_004 / case_006 / case_011 / case_016 / case_021 / case_022 / case_024 — all untouched)
- ❌ Did NOT inflate Done #1 (advance is genuine strict-PASS, not semantics rebadge)
- ❌ Did NOT introduce turbulence model (Re=133 laminar; turbulenceProperties simulationType laminar)
- ❌ Did NOT use uniform inlet + sample-at-exit cheating (codedFixedValue parabolic inlet applies the analytical profile exactly · mid-station cross-check at x=25·H also strict-PASS)
- ❌ Did NOT modify Schlichting / White reference values (used canonical formulae verbatim)
- ❌ Did NOT touch B66 BFS work (case_022 untouched)
- ❌ Did NOT touch parallel B67 cavity-v2 work (case_024_v64_cavity_v2_dicts/ untouched · disjoint scope)
- ❌ Did NOT hide the CASE_SPEC §4 τ_w formula error · disclosed transparently in §3.1 of validation report

## Artifacts

Repo (`.planning/case_profiles/case_025_v64_poiseuille_dicts/`):
- 1 parts_manifest.yaml + 1 CASE_SPEC.md + 1 MESH_PREP_LOG.md + 1 RUN_LOG.md
- 5 system/ dicts (blockMeshDict + controlDict + fvSchemes + fvSolution + sampleDict)
- 2 constant/ dicts (transportProperties + turbulenceProperties laminar)
- 2 0/ BC fields (U codedFixedValue + p)
- 1 BLOCKMESH_LOG.txt + 1 CHECKMESH_LOG.txt + 1 SIMPLEFOAM_LOG_TRIMMED.txt + 1 POSTPROCESS_LOG.txt
- 1 extract_poiseuille.py (165 LOC pure-stdlib · Q1 LLM-offline rerunnable)
- 3 results/raw_samples/ .xy files (exitProfile + midProfile + centerlinePressure)
- 3 results/ CSV (exit_profile_delta + mid_profile_delta + dpdx_extraction)
- 1 results/summary.json + 1 results/EXTRACT_STDOUT.txt

Sandbox (`~/Desktop/case_025_poiseuille_channel/case/`, NOT committed):
- Full OpenFOAM case dir with polyMesh/, postProcessing/, dynamicCode/.so, time-step output dirs 0/, 500/, 1000/, 1375/ (preserved for retro rerun)

Validation report: `.planning/validation_reports/v64_case_025_poiseuille_full.md` (~480 LOC)

RESUME: `.planning/case_profiles/case_025_RESUME.md` (updated by commit 4 with FULL verdict)

## Codex sync status

**Skipped**. No security boundary (read-only solver + analysis · no auth / signing / authz / operator endpoint). No byte-reproducibility-sensitive path (no canonical manifest bytes / HMAC / zip serialization). No Phase E2E batch (single sub-DEC). Within v2.3 spike-class-adjacent scope per V64-A charter; sub-DEC executed by main session with confidence:med.

## counter

`autonomous_governance: true` — counter +1 (B67; this sub-DEC). Per v2.3 cadence_floor=30, counter remains pure telemetry not a STOP signal. Latest counter value to be reconciled by main session in V64-A arc retro.

## Next action

V64-A arc B67 → B68 transition:
- Reconcile ARC-GOAL with Done #1 0/3 → 1/3 strict (standalone advance ratified by this sub-DEC); leave space for cavity-v2 contribution if independently ratified by user (separate B67 disjoint-scope work)
- Update Notion DEC sync (this sub-DEC + commit hashes; cavity-v2 sub-DEC) — session-end batch per v2.3 round-1 (only Status=Accepted DECs sync)
- Decide V64-A retro timing: 1 strict-FULL after 5 PARTIAL is a methodological inflection point — candidate for dedicated retrospective doc covering both "infrastructure soundness probe → confirmed" and "PARTIAL-track was real-physics-driven calibration signal"
- B68 candidate work options:
  - case_021 NASA TMR flat plate revisit at finer mesh (PARTIAL → strict FULL upgrade target · Done #1 +1/3)
  - case_009 Sandia Flame D entry (new canonical · low-Mach reacting · different physics class)
  - Done #6 V-row corpus densification (+6 this sub-DEC supports trajectory toward ≥7/9 single-case target)
  - Done #4 PARTIAL → FULL upgrade (≥ 2/3 target; case_016 window extension lowest-risk per charter §triggered-redirect)
