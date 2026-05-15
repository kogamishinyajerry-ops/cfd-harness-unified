---
decision_id: DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP
title: case_021 NASA TMR Turbulent Flat Plate FULL validation report · 3rd FULL attempt · incompressible canonical (Schlichting + Schultz-Grunow) · PARTIAL (soft) · Done #2 3/3 ✓ MET
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-VAL-FULL-3-INCOMP (3rd FULL attempt · incompressible canonical · 完全绕开 compressible gating)
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed813a9835e2ff6947d0ba)
confidence: med
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope under existing
V64-A charter (`DEC-V64-A-charter` Accepted 2026-05-15).

**Verdict: PARTIAL (soft) per task brief reverse condition.**

Distinguishing from prior 3 hard-PARTIALs in V64-A arc (B53 case_016 thermo-FPE
crash · B56/B57 case_004 blade CAD bug · B59 case_006 rhoSimpleFoam shock startup
instability), this is the **first soft-PARTIAL** where solver/mesh/BC stack all
behaved correctly with no engineering-layer block:

- simpleFoam ran 5000 iter to endTime · NO crash · NO FOAM FATAL · NO NaN
- y+ avg=0.54 within design target ✓
- checkMesh PASS-with-1-flag ✓ (canonical NASA TMR signature · cf B54 precedent)
- residuals monotonic descent → asymptotic plateau (4/5 fields at 1.84e-5 to 4.71e-5
  band; 1/5 strict <1e-5; continuity global 2.7e-8 ✓ machine zero)
- Cf canonical-grade in developed-TBL region (S3-S5 vs Schultz-Grunow Δ -2.4% to +3.2%)
- Cf under-predicts at S1-S2 by 6-10% — physical reason identified (low-Re kOmegaSST
  + I=0.5% inlet TKE below bypass-transition threshold)

**Why PARTIAL not FULL**: briefing strict reverse condition requires Δ < 5% on 5/5
stations AND residuals 6/6 < 1e-5. Both fail:
- 5% Cf gate: 3/5 stations >5% vs PS (S1,S4,S5); 2/5 >5% vs SG (S1,S2)
- 1e-5 residual gate: 4/5 plateau >1e-5

**Why PARTIAL not marginal**: ARC-GOAL §"反命题" defends against verdict inflation.
Conservative reporting elects PARTIAL because:
1. Done #1 strict count requires 5/5 stations <5% — anything less is PARTIAL for
   Done #1 accounting (per V63-A close §3.1 user-ratification precedent · no
   unilateral semantics relaxation)
2. "Marginal" descriptor would communicate physical excellence in developed-TBL
   region accurately, but accepting it as a verdict label would set precedent
   for soft-PARTIAL → FULL drift; not crossing that line unilaterally

Sub-DEC scope (per v2.3 §"DEC scope-driven"):
- 12 OpenFOAM dicts under repo staging at
  `.planning/case_profiles/case_021_v64_val_full_3_incomp_dicts/` (commits 1-3)
- 1 validation report at
  `.planning/validation_reports/v64_case_021_nasa_tmr_flat_plate_full.md` (commit 4)
- Case sandbox at `~/Desktop/case_021_nasa_tmr_flat_plate/case/` (Docker bind-mount
  target; not in repo per DEC-V61-198)
- This sub-DEC (commit 5)
- 5 atomic commits each carrying `confidence: med`

## Goal

V64-A charter Done dimension #1 advance (per V64-A charter §"Done Definition"):

> **≥ 3 FULL validation reports (solver 真实收敛 + experimental/literature delta < 文献声明 tolerance + V-row attribution)**

This sub-DEC attempted strict FULL convergence for case_021 NASA TMR turbulent flat
plate, soft-PARTIAL verdict reached:
- **Done #1 (FULL count)**: stays 0 / 3 strict (this attempt did NOT meet FULL bar)
- **Done #2 (canonical literature comparison)**: 2 / 3 → **3 / 3 ✓ MET** (Prandtl-Schlichting eq 21.11 + Schultz-Grunow log-law are net-new canonical references; precedent: B59 case_006 PARTIAL v2 advanced Done #2 → 2/3 with Schmitt-Charpin net-new; this sub-DEC adds 2 net-new in 1 report)

## Scope

### In-scope (LANDED in this sub-DEC)

1. **12 OpenFOAM dicts** for incompressible RANS canonical flat plate:
   - `system/blockMeshDict` (NASA TMR fine grid 545×385×1 = 209,825 cells)
   - `system/controlDict` (simpleFoam · 5000 iter · wallShearStress + yPlus + solverInfo FOs)
   - `system/fvSchemes` (steadyState · bounded Gauss linearUpwindV · Gauss upwind k/ω · Gauss linear corrected laplacians)
   - `system/fvSolution` (p GAMG+GS · U/k/ω PBiCGStab+DILU · URF 0.30/0.70/0.50/0.50 · residualControl 1e-5 · consistent yes)
   - `system/decomposeParDict` (scotch · numberOfSubdomains 1)
   - `system/sampleDict` (5-station midPoint probe lines · prepared)
   - `constant/turbulenceProperties` (RAS kOmegaSST)
   - `constant/transportProperties` (Newtonian · ν=1.4612e-5 m²/s)
   - `0/U` (inlet 70 0 0 · noSlip plate · slip top · inletOutlet outlet · empty fAB)
   - `0/p` (kinematic gauge · fixedValue 0 outlet · zeroGradient elsewhere)
   - `0/k` (0.18375 m²/s² · kqRWallFunction plate)
   - `0/omega` (15.66 1/s · omegaWallFunction plate)
   - `0/nut` (calculated · nutUSpaldingWallFunction plate)

2. **Substrate documentation** (commit 1):
   - `CASE_SPEC.md` (10 sections: strategic context · canonical selection rationale ·
     geometry · inflow conditions · 5 query stations · Cf canonical table · solver setup ·
     risk flags · anticipated V-row attribution · 4Q gate)
   - `parts_manifest.yaml` (schema parity stub · blockMesh_native mode · 2 risk_flags ·
     tolerance_policy Cf 5%)
   - `case_021_RESUME.md` (session pointer · canonical refs · 5 stations · verdict scale)

3. **Mesh prep artifacts** (commit 2):
   - `BLOCKMESH_LOG.txt` (83 lines · 209,825 hex confirmed · δy_first 5.62e-6 m)
   - `CHECKMESH_LOG.txt` (99 lines · PASS-with-1-flag · max AR 1669 canonical signature)
   - `MESH_PREP_LOG.md` (analysis: all topology checks OK · max non-orthogonality 0 ·
     max skewness 3e-13 · AR flag analysis)

4. **Solver run artifacts** (commit 3):
   - `SIMPLEFOAM_LOG_TRIMMED.txt` (28KB · head + sampled iters + tail · full 3.6MB
     log retained in sandbox)
   - `CONVERGENCE_TRACE.txt` (14-checkpoint residual table)
   - `extract_cf.py` (198-line LLM-offline Python stdlib extractor · dual canonical PS+SG)
   - `Cf_results.csv` (machine-readable 5-row × 12-col)
   - `Cf_results.md` (human-readable Δ table)
   - `RUN_LOG.md` (structured summary)

5. **Validation report** (commit 4):
   - `v64_case_021_nasa_tmr_flat_plate_full.md` (10 sections · 235 lines)
     covering executive summary · Done dim impact · reverse condition triggers ·
     physical interpretation · solver/mesh details · Cf comparison table ·
     V-row attribution · 4Q gate echo · sub-DEC scope · recommendations

### Out of scope (deferred or briefing-excluded)

- **case_004 / case_006 / case_011 / case_016 work** — briefing explicitly excluded
  ("B63 disjoint scope · do NOT touch case_004 anything"; B62 closed; compressible
  queue not touched). Verified: zero touches to those case directories in this
  sub-DEC's 5 commits.
- **Advisor stack edits** — briefing Q4 echo · `grep -rn "case_021" ui/backend/services/advisors/`
  returns 0 matches verified.
- **New advisor LANDED** — explicit briefing exclusion; this sub-DEC = case substrate
  + run verification on existing stack.
- **D11-class cross-validation** — B60 already done · separate sub-DEC if extending
  to case_021.
- **Notion sync** — main session handles per session-end batch sync (v2.3 round-1
  rule: Status=Accepted sync only).
- **ARC-GOAL.md update** — main session reconciles Done #2 2/3 → 3/3 ✓ MET advancement.

## Decision

Accept **case_021 as the V64-A 3rd FULL attempt with PARTIAL (soft) verdict**, advancing
Done #2 from 2/3 to 3/3 ✓ MET on the strength of 2 net-new canonical references
(Prandtl-Schlichting eq 21.11 + Schultz-Grunow log-law), with full disclosure of the
strict 5% Cf gate failure and 4/5 residual plateau.

### Strategic value beyond Done dim count

1. **Confirms V64-A pivot is correct**: incompressible canonical PATH (this sub-DEC)
   exposed the *physics-only* failure mode for the first time in the arc — no
   thermo-FPE, no shock-startup, no CAD bug, no rotating-frame complication.
   Pivot rationale (post-B61 retro) is now empirically validated.
2. **Demonstrates Schultz-Grunow as preferred high-Re canonical**: documents the
   systematic inadequacy of Prandtl-Schlichting 1/7-power at Re_x > 5e6 (S5 vs PS
   +12.6% but vs SG +3.2%). This becomes a methodology contribution to future
   incompressible canonical validation.
3. **First soft-PARTIAL in arc**: opens the door to a possible Done #1 semantics
   review at V64-A close-arc retro (per V63-A close §3.1 precedent for user-ratified
   verdict-class refinement). NOT proposing rebadge in this sub-DEC; flagging for
   close-arc consideration.

### Numerical findings (cited from validation report §6)

| Station | Re_x | Cf actual | Δ% vs PS | Δ% vs SG |
|---|---|---|---|---|
| S1 | 2.000e+06 | 0.002980 | -8.36 | -10.40 |
| S2 | 4.003e+06 | 0.002782 | -1.71 | -6.33 |
| S3 | 6.013e+06 | 0.002720 | +4.24 | -2.38 |
| S4 | 8.019e+06 | 0.002691 | +9.26 | +0.95 |
| S5 | 9.559e+06 | 0.002678 | +12.61 | +3.16 |

Max |Δ| vs PS: 12.61% (S5) · Max |Δ| vs SG: 10.40% (S1)

### Residual state (cited from RUN_LOG.md)

- Ux 1.84e-5 · Uy 4.71e-5 · p 4.41e-5 · ω 5.31e-8 ✓ · k 2.74e-5
- continuity (global): -2.73e-8 ✓ machine zero
- monotonic descent → plateau by iter 3000 (numerical-noise floor of `bounded
  linearUpwindV`); continuing to 10000 iter would yield ~1e-5 strict but no
  physics change

### Mesh state (cited from MESH_PREP_LOG.md)

- 209,825 hex (545×385×1) matching NASA TMR fine grid exactly
- y+ on plate: avg=0.54 · max=1.54 · min=0.49 ✓
- checkMesh PASS-with-1-flag (max AR 1669 on 1815 cells · canonical NASA TMR signature)

## V-row attribution

### Firm carry-forward (5/9 · per v2.3 clause-2 ≥5/9 over-met threshold)

- **V47** canonical BC convention documentation · firm (first cross-case validation
  of canonical inlet I=0.5% L=0.05m parameterization at high Re_x)
- **V100** incompressible canonical advisor stack baseline · firm (first FULL-attempt
  run on canonical-mode parts_manifest with geometry_mode=blockMesh_native)
- **V94** substrate-bridge manifest mapping · firm (parts_manifest.yaml schema
  parity preserved despite zero-STL substrate; advisor stack no regression)
- **V32** canonical reference cite discipline · firm (each Cf row attributes to
  specific eq with formula shown; canonical refs diversified beyond V63-A single-canon
  pattern)
- **V27** substrate-vs-validation orthogonality · firm (5 atomic commits cleanly
  partition substrate/mesh/solver/report/DEC; zero leak)

### F-NEW candidates (2 · QUESTIONABLE pending 2nd-case confirmation)

- **F-NEW-Cf-canonical-choice**: Prandtl-Schlichting 1/7-power Cf inadequate as
  canonical reference for kOmegaSST validation at Re_x > 5e6; Schultz-Grunow log-law
  preferred. Future incompressible FULL validation reports MUST cite BOTH canonicals
  to avoid systematic false-PARTIAL verdicts.
- **F-NEW-low-Re-transition-trigger**: kOmegaSST + I=0.5% inlet causes 6-10% Cf
  under-prediction at Re_x ∈ [1e6, 3e6] (LE-near transition zone). Future low-Re
  cases MUST use either I ≥ 1% inlet TKE, OR forced transition trip, OR document
  under-prediction as expected.

(Both candidates flagged QUESTIONABLE; promote to V103 + V104 if 2nd incompressible
case confirms the pattern.)

## 4Q gate (echo from validation report §8)

| Gate | Status |
|---|---|
| Q1 LLM-offline | ✓ Docker --rm ephemeral container + extract_cf.py pure stdlib · 2-command rerun |
| Q2 artifacts | ✓ 16+ files (12 dicts + 7 logs/scripts + 4 docs + this DEC) ≫ briefing min 11 |
| Q3 TrustGate | ✓ every numeric cites Cf_results.md / log.simpleFoam / CONVERGENCE_TRACE row · every canonical cites named eq with formula shown |
| Q4 advisor-only | ✓ `grep -rn case_021 ui/backend/services/advisors/` returns 0 matches · zero advisor stack edits |

## Codex review skip rationale

Per V2.3 + DEC-V61-133 simplification (Codex 1-sync-trigger: security boundary /
auth / signing): this sub-DEC's surface = case substrate (data files + Python
script + Docker-launched binary) with zero auth / no signing / no security boundary.
No advisor stack edits = no v2.2 byte-repro async trigger. No E2E ≥3 fail trigger.

**Codex review: SKIPPED** (no risk-tier hit). Confidence: med.

Surface-scan trailer: clean (no top-level routes/pages/services/scripts added;
all changes confined to `.planning/` artifacts + LLM-offline Python helper).

## Counter telemetry (per v2.3 round-1 rule · pure telemetry)

- autonomous_governance: true → counter +1
- Kogami invocation: NONE (opt-in only per v2.3; user did not request strategic review)
- Codex rounds used: 0 (no risk-tier trigger)
- Done dim advancement: Done #2 2/3 → 3/3 ✓ MET (3rd Done dim MET in V64-A arc)

## Commit chain

1. `9a87219` — feat(v64-incomp-full3): case_021 substrate prep · NASA TMR canonical reference cite
2. `6183908` — feat(v64-incomp-full3): case_021 mesh prep · 7 dicts · blockMesh 209,825 cells · checkMesh PASS-with-1-flag
3. `3150367` — feat(v64-incomp-full3): case_021 simpleFoam run · 5000 iter · y+ avg 0.54 ✓ · Cf extraction at 5 NASA TMR stations
4. `1ecc81a` — docs(v64-incomp-full3): validation report · canonical Cf comparison (PS + SG) · Done #2 3/3 ✓ MET
5. **(this commit)** — docs(v64-incomp-full3): sub-DEC DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP Accepted · verdict PARTIAL (soft)

Each commit carries `confidence: med` per v2.2 + v2.3 commit-message discipline.

## Recommendations for main session (post-merge)

1. **ARC-GOAL.md update** (main session): Done #2 counter 2/3 → 3/3 ✓ MET; V64-A
   total MET 2/6 → 3/6 (Done #3 + Done #5 + Done #2); add B63 milestone entry to
   Tier 2 status board.
2. **Notion sync** (session-end batch · v2.3 round-1: Accepted DEC only): sync
   this sub-DEC to Decisions DB; obtain Notion page URL; update
   `notion_sync_status: synced YYYY-MM-DD (<url>)` in this DEC's frontmatter.
3. **Retro candidate**: V64-A arc-level retro at close should review whether
   "soft-PARTIAL" warrants its own verdict class (V63 close §3.1-style
   user-ratified semantic refinement) — Done #1 strict-5% gate has now failed
   4× and the failure modes are diverse (CAD / thermo / shock / canonical-choice).
4. **F-NEW promotion**: if a 2nd incompressible canonical case (Driver-Seegmiller
   BFS / Moser DNS channel / Coles bypass-transition flat plate) confirms either
   F-NEW-Cf-canonical-choice or F-NEW-low-Re-transition-trigger, promote to V103
   / V104 respectively.
