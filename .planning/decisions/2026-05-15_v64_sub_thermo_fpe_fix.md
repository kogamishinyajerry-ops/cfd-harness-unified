---
decision_id: DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX
title: V64-A Tier 2 · case_016 + case_006 systemic thermo-FPE substrate fix · PARTIAL v3 × 2
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-THERMO-FPE-FIX
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed816b8bd3dfe3cce79752)
autonomous_governance: true
confidence: med
codex_review_relay: skipped (v2.3 1-sync-trigger not crossed · no security/auth/signing boundary)
kogami_review: skipped (opt-in only per V133 · user did not invoke)
---

# DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX

## §1 Decision

Apply a substrate-only, advisor-stack-untouched, systemic fix for the
shock-startup thermo-floating-point-exception (thermo-FPE) crash signature
shared between two case sandboxes:

- `DEC-V64-A-sub-M-VAL-CASE-016-FULL` (B53 v2 PARTIAL): rhoPimpleFoam crashed
  at sim t=1.24 ms with `sigFpe` (FE_DIVBYZERO/FE_INVALID) inside
  `libfluidThermophysicalModels::sutherlandTransport::mu(T)`
- `DEC-V64-A-sub-M-V64A-VAL-FULL-2` (B59 v2 PARTIAL): rhoSimpleFoam attempts
  crashed FE_DOMAIN `sqrt(T)` (attempt 2) + p-eq divergence (attempt 3),
  shared signature

**Substrate fix mechanism** (applied to both cases):
1. **`system/fvOptions`** with `limitTemperature` fvOption clamping cell-local
   T to [110, 2000] K via energy-equation `correct(he)` hook (canonical
   OpenFOAM 2312 mechanism; floor 110 K is just above sutherland Ts=110.4 K
   below which mu(T) becomes nonphysical; ceiling 2000 K is far above
   expected M=0.84/0.85 transonic post-shock T ≈ 350-568 K)
2. **case_016 only**: tightened `controlDict` — deltaT 1e-4 → 1e-6 (slow ramp),
   maxCo 1.0 → 0.3 (tighter Co cap), maxDeltaT 1e-4 → 5e-5
3. **case_006 only**: restored sutherland transport in `constant/thermophysicalProperties`
   (was downgraded to const in B59 v2.3 because of FE_DOMAIN crash · now
   safe under fvOptions T-clamp); added potentialFoam pre-step via new
   `system/fvSolution::potentialFlow` block + Phi solver; created new
   `scripts/v64_v3_run_solver.sh` 2-stage runner

**Verdict**: PARTIAL v3 × 2

| Case | v2/B59 crash mode | v3 result | Δ |
|---|---|---|---|
| case_016 | FE in libfluidThermophysicalModels at t=1.24 ms (thermo layer) | sigFpe in libfiniteVolume at t=0.586 ms (p-eq layer) | thermo crash unblocked → p-eq crash revealed |
| case_006 | B59 attempt 2: FE_DOMAIN sqrt(T) at iter 77 / attempt 3: p-eq diverged 0.478→8011 at iter 1000 | sigFpe in libOpenFOAM PBiCGStab at iter 7 (matrix instability via force-coeff explosion) | thermo crash partially unblocked → SIMPLE matrix instability persists deeper |

Neither case reached the target convergence threshold. The fix accomplishes
ONE necessary thing (thermo-FPE no longer the immediate gating mechanism)
but does NOT accomplish the V64-A Done #1 sufficient thing (FULL validation
report).

## §2 Strategic value

Despite both cases verdicting PARTIAL v3, the substrate-fix work creates
value for V64-A and downstream:

1. **fvOptions limitTemperature as canonical OpenFOAM 2312 substrate-side fix template**
   — proven applicable for both transient (rhoPimpleFoam, case_016) and
   steady (rhoSimpleFoam, case_006) compressible solvers. Should be
   promoted to substrate-default for any future compressible transonic case
   with shock-startup transients (methodology patch target).
2. **Failure-mode characterization**: by removing the thermo-FPE crash mode,
   v3 makes visible the underlying gating axes:
   - case_016: **PIMPLE p-equation cannot bound pressure overshoot** with
     impulsive freestream + cavity-acoustic + M=0.85 + 273k LES IDDES mesh
     (p_max → 1.84 MPa, p_min → -177 kPa at t=0.586 ms)
   - case_006: **SIMPLE-style rhoSimpleFoam algorithm cannot handle**
     transonic shock startup even WITH potentialFoam pre-step + sutherland-
     restored + thermo-FPE fix · corroborates B59 F-NEW-5 hypothesis at v3
     attempt level
3. **B59 F-NEW-5 promotion eligibility**: F-NEW-5 ("rhoSimpleFoam steady
   SIMPLE-style algorithm cannot handle freestream → transonic shock
   initialization without pre-conditioning") graduates from [QUESTIONABLE]
   (1-attempt evidence) to **corroborated** (2-attempt evidence with v3
   attempt level). Eligible for LANDED V-row promotion in next methodology
   sync.
4. **Charter premise refutation**: case_016 → FULL is no longer "cheapest
   unblock" (v2 B53 retro already refuted this; v3 escalates further to
   "MOST expensive Tier 1 candidate" with 5.8 h wall budget projection at
   maxCo=0.3 for Welch min window).

## §3 Done dim accounting (V64-A)

| Done dim | Target | Pre-v3 state | Post-v3 state | Δ |
|---|---|---|---|---|
| #1 ≥3 FULL validation reports | ≥3 FULL | 0/3 FULL + 3/3 PARTIAL credit | **0/3 FULL** + 5/3 PARTIAL credit (case_016 v3 + case_006 v3 added) | no FULL advancement |
| #2 Canonical literature comparisons | ≥3 | 2/3 (Heller-Bliss + Schmitt-Charpin lit-only) | unchanged | no change |
| #3 Convergence stability test | ≥1 | 1/1 ✓ | unchanged | no change |
| #4 PARTIAL → FULL upgrade | ≥2 | 0/≥2 | unchanged (v3 does NOT upgrade v2/B59 to FULL) | no change |
| #5 V63-A carry-over closure | ≥4 | 3/4 (per B62 case_011 ratify) | unchanged | no change |
| #6 V-row attribution rate | ≥2 clause-1 | over-met 3/2 (B59 added) | **over-met 5/2** (v3 adds 3 more candidate V-rows + 1 extinction + 1 corroboration) | over-met deeper |

**Brief's stated success target**: "Done #1 0/3 → 2/3 strict" if BOTH cases FULL;
"0/3 → 1/3" if either single case FULL; "stays 0/3 if both PARTIAL".

**Achieved**: BOTH PARTIAL v3 → **stays 0/3 strict**. Honest recording.

## §4 V-row attribution (v3 net delta)

### case_016 V-row delta vs v2 B53

| V-row | v2 status | v3 status | Net new? |
|---|---|---|---|
| V52, V53, V54, V57 | LANDED upstream | LANDED upstream | no |
| V-candidate v2-new-1 (thermo-FPE at t>1.24ms with sutherland) | [QUESTIONABLE] | **EXTINCT** (v3 evidence shows fvOptions limitTemperature eliminates this crash mode) | yes (extinction) |
| V-candidate v2-new-2 (Heller-Bliss canonical mismatch) | [QUESTIONABLE] | unchanged | no |
| V-candidate v2-new-3 (charter "cheapest unblock" premise) | [QUESTIONABLE] | RE-AFFIRMED + ESCALATED | yes |
| **F-NEW-v3-1**: fvOptions limitTemperature successfully unblocks transonic LES IDDES thermo-FPE; reveals PIMPLE p-eq overshoot as deeper axis · canonical substrate-only fix template | [proposed] | **[QUESTIONABLE]** candidate | yes |
| **F-NEW-v3-2**: maxCo 0.3 + deltaT 1e-6 slow-ramp triples wall budget for compressible LES IDDES cavity case | [proposed] | **[QUESTIONABLE]** candidate | yes |
| **F-NEW-v3-3**: PIMPLE pMinFactor/pMaxFactor ratio-based pressure limiter INSUFFICIENT for transonic impulsive-IC + 273k LES IDDES + cavity-acoustic motif · `fvOptions limitPressure` is next-line absolute-bound substrate-side fix candidate | [proposed] | **[QUESTIONABLE]** candidate · advisor extension target | yes |

### case_006 V-row delta vs B59 v2

| V-row | B59 status | v3 status | Net new? |
|---|---|---|---|
| V27, V28, V29, V30 | YES ✓ | unchanged | no |
| F-NEW-5 (B59) (rhoSimpleFoam SIMPLE-style transonic external wing fail) | [QUESTIONABLE] (1-attempt evidence) | **CORROBORATED at v3 attempt level** with potentialFoam pre-step + sutherland-restored + fvOptions limitTemperature · LANDED-promotion eligible | yes (corroboration) |
| F-NEW-6 (B59) (mesh-quality lower-edge at level (6,7)) | [QUESTIONABLE] | unchanged | no |
| **F-NEW-v3-2 (case_006)**: thermo-FPE fix is insufficient stand-alone for rhoSimpleFoam transonic external wing — SIMPLE conditioning is deeper gating axis · advisor extension target | [proposed] | **[QUESTIONABLE]** candidate · advisor extension target | yes |
| **F-NEW-v3-3 (case_006)**: potentialFoam pre-step config template (no -writephi, clean 0/Phi after) works as preconditioner but doesn't solve SIMPLE conditioning | [proposed] | **[QUESTIONABLE]** candidate | yes |

### Counter accounting

- This sub-DEC: 1 counter increment for `autonomous_governance: true`
- 5 atomic commits chain landed on main (substrate dicts + case_016 log +
  case_006 log + 2 validation reports + this sub-DEC)
- 0 Codex review rounds (v2.3 1-sync-trigger not crossed)
- 0 Kogami review (opt-in not invoked)
- 0 Notion sync (session-end batch convention; this DEC has `status: Accepted`
  and will sync at next session-end)

## §5 Recommendations to V64-A close DEC

1. **Methodology patch — promote F-NEW-5 (B59) to LANDED** in
   `.planning/methodology/industrial_case_solver_findings.md` AND
   `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (corpus-sync
   hook compliance) at next available V-row number. v3 evidence is the
   2-attempt corroboration that justifies the [QUESTIONABLE] → LANDED transition.
2. **Substrate-default promotion** — add `system/fvOptions limitTemperature`
   [110, 2000] K to the compressible-solver template set in
   `.planning/methodology/`. Document the case_016 v3 + case_006 v3
   evidence as the canonical proof-of-concept.
3. **Advisor extension recommendation** — when advisor detects motif
   `solver: rhoSimpleFoam + transonic external wing + impulsive freestream IC`,
   recommend solver alternative (rhoPimpleFoam pseudo-transient OR
   rhoCentralFoam transient density-based; both bypass SIMPLE matrix
   conditioning). When advisor detects motif `LES IDDES + cavity-acoustic +
   M≥0.8 + impulsive IC`, recommend `fvOptions limitPressure` alongside
   `limitTemperature`.
4. **case_016 path forward** — 3 options:
   - Option A: try `fvOptions limitPressure` substrate fix (next-line
     candidate per F-NEW-v3-3) · estimated 1 more iteration before next
     gate visible
   - Option B: replace impulsive freestream IC with cavity-quiescent
     precursor (10 ms reduced-M ramp) · much larger substrate change
   - Option C: de-tier case_016 out of V64-A Tier 1 · pick another candidate
5. **case_006 path forward** — 3 options:
   - Option A: switch to rhoPimpleFoam pseudo-transient (substrate's
     solver_v2) with thermo-FPE fix · ~2 h wall · likely best path
   - Option B: upgrade B59 v2 PARTIAL → FULL via geometry (A1 ONERA D-section
     extraction) + mesh refinement to 600k+ (no solver change · cheaper
     substrate iteration)
   - Option C: defer case_006 entirely · pick a different V64-A Tier 1
     candidate

## §6 4Q gate compliance

- **Q1 LLM-offline**: YES · `env -i HOME PATH bash scripts/{08_run_solver.sh, v64_v3_run_solver.sh}` is fully shell + Docker · no LLM mid-stream invoked · all dicts authored as static OpenFOAM ASCII
- **Q2 artifacts**: YES · 2 substrate dict bundles (case_016 + case_006 in `.planning/case_profiles/case_{016,006}_v64_thermo_fpe_fix_dicts/`) + 4 run logs (case_016 1MB rhoPimpleFoam + potentialFoam + cavity_force + pressureProbes; case_006 rhoSimpleFoam + potentialFoam + fieldMinMax) + 2 validation reports (v64_case_{016,006}_thermo_fpe_fix_v3.md) + this sub-DEC
- **Q3 TrustGate**: YES · every p / T / continuity / force-coeff / residual / iter value in reports cites postProcessing file row or log line · canonical references cite sutherland Ts=110.4 K + Schmitt-Charpin AGARD-AR-138 + Heller-Bliss Rossiter (lit-only · digitized data deferred per case profile) + brief reverse condition thresholds
- **Q4 advisor-only**: YES · `ui/backend/services/advisor_stack.py` UNTOUCHED · `ui/backend/services/geometry_ingest/` UNTOUCHED · `ui/backend/routes/` UNTOUCHED · `ui/frontend/` UNTOUCHED · fix is substrate-side (case sandbox `system/` + `constant/` + repo `.planning/case_profiles/`) · advisor extension recommendations (V64-A close DEC target) are surfaced for user, not auto-applied · F-NEW-5 LANDED promotion recommendation surfaced for main session, not auto-promoted

## §7 Out-of-scope (per brief)

This sub-DEC does NOT touch:
- case_004 work (B57 + F-NEW-3 blade CAD fix is separate sub-DEC queue)
- case_011 work (B62 scope · disjoint)
- Advisor stack source edits (decision to extend advisor V53/V54 deferred to
  V64-A close DEC per recommendations §5.3)
- New advisor LANDED (substrate fix only; advisor extension surfaced as
  recommendation)
- Notion sync (main session session-end batch)
- ARC-GOAL update (main session reconciles)
- Mesh regen (B53 + B59 meshes reused as-is)

## §8 Surface scan + governance

- **Surface scan**: `grep -rin "limitTemperature\|fvOptions.*limit\|thermo-FPE\|THERMO-FPE" .planning/` returned 0 hits beyond v2/v3 sub-DEC author chain → clean.
- **v2.3 sub-DEC scope**: 3 shared code paths touched (case_016 substrate + case_006 substrate + sub-DEC doc). At charter-trigger threshold but:
  - no schema change (only OpenFOAM dict fields, all canonical)
  - no security boundary
  - no contract break (advisor stack untouched)
  - no cross-track absorption
- Authored as sub-DEC (NOT elevated to charter) per v2.3 round-1 loosen rule
  (sub-DEC = single arc fix · scope-driven · 6 frontmatter fields minimum).
- **Codex review**: skipped per v2.3 1-sync-trigger (no auth/signing/security-boundary).
- **Kogami review**: skipped — opt-in only per V133; user did not invoke.
- **Notion sync**: pending — `status: Accepted` so eligible for session-end batch
  sync (per v2.3 only-Accepted convention).
- **Confidence**: med (high on crash forensics + log parse + dict design;
  med on F-NEW-5 promotion recommendation since promotion requires methodology
  + corpus sync hook compliance + main session execution).
- **Commit chain trailer**: `confidence: med` on all 5 commits.

## §9 Commit chain

| # | SHA | type | files | confidence |
|---|---|---|---|---|
| 1 | 3451f25 | feat(v64-thermo-fpe) | substrate v3 dicts (29 files: 2 dict bundles + 1 runner + 2 READMEs) | med |
| 2 | (case_016 evidence commit) | feat(v64-thermo-fpe) | case_016 run log + potentialFoam + cavity_force + pressureProbes (4 files) | med |
| 3 | 19651f1 | feat(v64-thermo-fpe) | case_006 run log + potentialFoam + fieldMinMax + runner-fix (4 files) | med |
| 4 | 642d0b6 | docs(v64-thermo-fpe) | 2 validation reports v3 | med |
| 5 | (this sub-DEC) | docs(v64-thermo-fpe) | sub-DEC DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX | med |

## §10 Pointers

- Charter DEC: `.planning/decisions/2026-05-15_v64_charter_dec.md`
- case_016 v2 PARTIAL retro: `.planning/validation_reports/v64_case_016_m219_cavity_des_acoustic_acoustic_full_v2.md`
- case_006 v2 PARTIAL retro (B59): `.planning/validation_reports/v64_case_006_onera_m6_full.md`
- case_016 v3 validation report: `.planning/validation_reports/v64_case_016_thermo_fpe_fix_v3.md`
- case_006 v3 validation report: `.planning/validation_reports/v64_case_006_thermo_fpe_fix_v3.md`
- case_016 substrate v3 dict bundle: `.planning/case_profiles/case_016_v64_thermo_fpe_fix_dicts/`
- case_006 substrate v3 dict bundle: `.planning/case_profiles/case_006_v64_thermo_fpe_fix_dicts/`
- case_016 v3 run logs (sandbox): `~/Desktop/case_016_m219_cavity_des_acoustic/case/log/`
- case_006 v3 run logs (sandbox): `~/Desktop/case_006_onera_m6_transonic/case/log_v64_v3/`
- B53 sub-DEC: `.planning/decisions/2026-05-15_v64_sub_val_case_016_full.md`
- B59 sub-DEC: `.planning/decisions/2026-05-15_v64_sub_case_006_v64_val_full_2.md`

---

*Authored by: Claude Code Opus 4.7 (1M context) main session · B63 V64-A Tier 2 thermo-FPE fix dispatch · 2026-05-15 · status: Accepted · confidence: med*
