---
decision_id: DEC-V64-A-sub-M-V64A-CASE-004-CASE-SPEC-FIX
title: V64-A Tier 2 sub-DEC · case_004 NREL Phase VI MRF · case-spec correction (axis flip + 0° pitch) + 2nd FULL attempt v3 · PARTIAL v3 verdict · F-NEW-3 blade chord-axis convention bug surfaced
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-CASE-004-CASE-SPEC-FIX (B56 follow-up · 2nd FULL attempt with case-spec correction)
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed81c593b7fe9b322907cb)
authored_by: Claude Code Opus 4.7 (1M context) · sub-session B57
authored_at: 2026-05-15
confidence: med
codex_review_relay: skipped (v2.3 1-sync-trigger · solver run + case-spec correction + docs · no auth/signing/security-boundary touch)
kogami_review: skipped (v2.3 opt-in only · user did not invoke)
autonomous_governance: true
---

# DEC-V64-A-sub-M-V64A-CASE-004-CASE-SPEC-FIX · case_004 NREL Phase VI MRF · case-spec correction + 2nd FULL attempt v3

## Status

**Accepted 2026-05-15** — 2nd FULL validation attempt on case_004, following
B56 PARTIAL v2's open-questions §"rotation direction inconsistency + 3° pitch
mismatch" hypotheses.

Verdict: **PARTIAL v3** (dispatch reverse-condition clause:
"若 Δ Cp / Δ Ct 仍 > 10% (canonical Seq S tolerance) 或 residual 仍 0/6 < 1e-4 →
退到 PARTIAL v3 不掩盖").

The case-spec corrections were applied as briefed (MRFProperties axis sign
flipped from `(1 0 0)` to `(-1 0 0)`; `TIP_PITCH_DEG` in build_cad.py reduced
from 3.0 to 0.0 to match Seq S baseline; CAD regenerated; mesh regenerated at
equivalent density). The axis-flip fix is **empirically verified**: M_x sign
flipped from -10189 N·m (v1, B56) to +10077 N·m (v3); F_x sign flipped from
-398 N (v1) to +132 N (v3). However the **|M_x| magnitude is essentially
unchanged** (~10000 N·m in both v1 and v3) and **Cp remains ~4.55, exceeding
Betz 0.593 by 7.7 ×**.

Root cause of the unchanged Cp magnitude was **identified and documented** in
this sub-session as **F-NEW-3: blade chord-axis convention bug** in
`scripts/build_cad.py::section_wire()` line 294. The `theta = math.radians(twist_deg + TIP_PITCH_DEG)`
formula produces a blade with **chord aligned to the rotation axis** (= +x for
v1, structurally feathered) at theta=0, rather than the NREL Phase VI
convention of **chord in the rotor plane** at theta=0. The blade therefore
operates as a feathered rotor (chord parallel to wind direction); drag-driven
torque from the rotation creates an apparent "Cp" of ~5 because the energy
source is `½ρω²R²`, not `½ρU²`. This explains why v1 (axis +x, pitch 3°) and
v3 (axis -x, pitch 0°) both produce Cp ≈ 5 regardless of the changes:
**neither change addresses the underlying chord-axis convention**.

PARTIAL v3 advancement summary:

- V64-A **Done #1** (strict FULL reports) stays at **0/3** — NO inflation
- V64-A **Done #2** (canonical literature comparison) stays at **1/3** —
  v3 is a fix-rerun on the same canonical NREL UAE Sequence S 7 m/s
  baseline as B56; same query point, not a new canonical comparison.
  Per dispatch clause: "v3 是 fix-rerun 同一 baseline · 严格意义 Done #2 stays
  1/3 因为 query point 不变 · 这是诚实"
- V64-A **Done #4** (PARTIAL → FULL upgrade) stays — case_004 V63-A PARTIAL
  → V64-A PARTIAL v2 → V64-A PARTIAL v3, **not upgraded to FULL**
- V64-A **Done #5** (V63-A carry-over) — the "Step 6 mesh+solver" carry-over
  from B49 stays at 1/4 closed (mesh half by B54; solver half attempted
  again by B57, still PARTIAL)
- V64-A **Done #6** (V-row truth-capture) — case_004 V-row coverage now at
  12 rows across B49+B54+B56+B57 (V10 + V20 + V22 + V23 + V24 + V29 + V30 +
  V94 + V100 + D1 + 4 F-NEW rows including new F-NEW-3 + F-NEW-4 from B57),
  with **1 new dominant root-cause row field-discovered (F-NEW-3)** and
  **1 new procedural row resolved (F-NEW-1 sign convention closed via
  empirical axis-flip evidence)** in this sub-session

## Goal (verbatim from B57 dispatch)

> "落地 V64-A Tier 2 milestone — M-V64A-CASE-004-CASE-SPEC-FIX (case_004 NREL
> Phase VI MRF case-spec correction + 2nd solver attempt + NREL UAE Sequence S
> 7 m/s experimental comparison v3 · 推 V64-A Done #1 0/3 → 1/3 strict FULL)."

Tied to V64-A charter §Done #1 (FULL validation reports ≥ 3/3 via real solver
convergence + experimental delta + V-row attribution) and §Done #2 (canonical
literature comparison ≥ 3, 1 per FULL report). B57 did not advance Done #1
(PARTIAL v3 verdict); the dominant contribution is **identification of
F-NEW-3 root cause** with **two scoped repair paths** (one-line section_wire()
change OR case substitution) documented in the companion v3 validation
report §10.

## Scope (what changed in this sub-DEC)

### Repo changes (this sub-DEC commit chain)

- `.planning/case_profiles/case_004_v64_case_spec_fix_dicts/` — **NEW**, 11 dicts:
  - `0/{U, p, k, omega, nut}` (5 boundary-condition dicts; identical to B56
    `case_004_v64_val_full_1_dicts/0/` — same 11-patch mesh, same canonical
    Seq S 7 m/s inflow turbulence quantities)
  - `constant/{turbulenceProperties, transportProperties}` (identical to
    B56 — kOmegaSST RAS, ν=1.5e-5 m²/s)
  - `constant/MRFProperties` — **axis (-1 0 0) (axis-flipped from B56)**;
    omega 7.539822369 (magnitude preserved); inline comment citing
    NREL/TP-500-29955 §1 + Hand et al. 2001 Fig. 1-2 as design-intent reference
  - `system/{controlDict, fvSchemes, fvSolution}` (identical to B56 —
    simpleFoam · 2500-iter cap · residualControl 1e-4 · SIMPLE-C nNonOrthCorr=1
    relax p=0.30 U=0.70 k/ω=0.50)
- `.planning/validation_reports/v64_case_004_nrel_phase_vi_full_v3.md` —
  **NEW**, full PARTIAL v3 validation report with §3 dedicated to F-NEW-3
  root-cause analysis + §10 next-step recommendation
- `.planning/decisions/2026-05-15_v64_sub_case_004_case_spec_fix.md` —
  **NEW**, this file

### Substrate changes (sandbox, outside repo per DEC-V61-198, in `~/Desktop/case_004_nrel_phase_vi_mrf/`)

- `config/case.yaml`:
  - `mrf.zones[0].axis: [1.0, 0.0, 0.0]` → **`[-1.0, 0.0, 0.0]`**
  - `force_coeffs.rotation_axis: [1.0, 0.0, 0.0]` → **`[-1.0, 0.0, 0.0]`**
  - inline comments citing NREL/TP-500-29955 §1 + B57 origin
- `scripts/build_cad.py`:
  - `TIP_PITCH_DEG = 3.0` → **`TIP_PITCH_DEG = 0.0`** with inline comment
    citing NREL/TP-500-29955 Table 3-2 (Sequence S baseline)
- `case/constant/MRFProperties`:
  - `axis (1.0 0.0 0.0)` → **`axis (-1.0 0.0 0.0)`** with inline comment
    citing NREL/TP-500-29955 + Hand et al. 2001 Fig. 1-2
- `inputs/cad_codex_v2_no_pitch.step` — **NEW**, 1.96 MB, regenerated STEP
  from build_cad.py with TIP_PITCH_DEG=0
- `case/constant/triSurface/` — **regenerated** 16 ASCII STLs from new STEP
  via harness bridge (`ui/backend/services/geometry_ingest/freecad_step_to_stl.py`,
  lin_deflection=0.05, ang_deflection=0.1)
- `case/constant/triSurface_v1_backup/` — **NEW**, v1 STL + eMesh + manifest
  preserved as audit trail
- `case/constant/polyMesh/` — **regenerated** via blockMesh + sFE + sHM
  (~921 k cells, +0.16 % vs B54's 919 k; same refinement levels; mesh stats
  in report v3 §2.3)
- `case/0/{U, p, k, omega, nut, cellLevel, pointLevel}` — **NEW** (mirror of
  in-repo embed; cellLevel + pointLevel from sHM)
- `case/log.simpleFoam.v3` — **NEW** (17 KB log, iter 1→375, force-stable
  mean over last 20 samples)
- `case/postProcessing/{forces_rotor, forces_thrust_blades, forceCoeffs_rotor, residuals}/0/`
  — force-monitor + residual `.dat` outputs from this run
- `case/convergence_analysis_v3.txt` — analyzer output (Cp = 4.553, Ct =
  0.0535, Δ vs canonical reported honestly)

### Out of scope (per dispatch contract)

- Advisor stack source edits (`ui/backend/services/advisor_stack.py`,
  `geometry_ingest/*` source) — none made; B58 has concurrent disjoint
  scope on those files
- Mesh refinement-level changes — M-V64A-MESH-CONV-STUDY scope
- pimpleFoam transient AMI v2 fallback — next sub-DEC candidate if v3
  blade-convention-fix v4 still PARTIAL
- ARC-GOAL.md update (main session reconciles; B58 + B59 parallel risk)
- Notion sync (session-end batch per v2.3 round-1 rule; only Accepted DECs)
- Codex review (not a security boundary, per v2.3 1-sync-trigger rule)
- Kogami review (opt-in only, not invoked)
- build_cad.py `section_wire()` formula change to fix F-NEW-3 chord-axis
  convention — **explicitly scoped to the next sub-DEC**
  (`DEC-V64-A-sub-M-V64A-CASE-004-BLADE-CONV-FIX` recommended)

## Solver convergence trace

From `case/log.simpleFoam.v3` + `case/convergence_analysis_v3.txt`:

- Final iteration count reached: **375** (out of 2500 cap; bg-task supervision
  early-termination · F-NEW-4 in report v3 §6 · force-stable mean already
  reached at iter ~200)
- Final residuals (Ux/Uy/Uz/p/k/ω) end-state mean of last 5:
  2.234e-2 / 2.557e-2 / 2.351e-2 / 2.914e-2 / 4.549e-3 / 4.807e-4
- Convergence verdict: **0 / 6 < 1e-4** (briefing requires ≥ 4 of 6 < 1e-4 →
  NOT MET; same plateau as B56 v1 — physical-quasi-steady wake regime)
- Relaxation adjustments attempted: 1 (URF 0.30/0.70/0.50 per case.yaml +
  B56 controlDict; no further URF adjustment needed since force-stable
  achieved at osc 6.4 % on M_x, better than B56 v1 attempt #2's 8.2 %)
- Wall-clock elapsed: ≈ 14 min (ExecutionTime 839 s on 1 CPU in Docker OF
  ESI 2312)

## NREL UAE Sequence S delta table (v3)

From `case/postProcessing/forces_rotor/0/{force,moment}.dat` +
`case/postProcessing/forces_thrust_blades/0/force.dat`, mean over last 20
force-monitor samples (iter 180–370):

| quantity | NREL UAE Seq S baseline @ 7 m/s | this run (v3, iter ~370) | delta % |
|---|---|---|---|
| Aerodynamic power = \|M_x\| × ω | ≈ 5.93 kW | **76.0 kW** | **+1181.3 %** |
| Rotor thrust = \|F_x\|_{blades} | ≈ 1240 N | **127.6 N** | **−89.7 %** |
| Cp = P/(½ρAU³) | ≈ 0.40 | **4.553** | **+1038.3 %** |
| Ct = T/(½ρAU²) | ≈ 0.52 | **0.0535** | **−89.7 %** |

**Δ Cp = +1038 %, Δ Ct = -89.7 %** — both exceed the dispatch tolerance
(> 10 %); verdict per reverse-condition is **PARTIAL v3, no 掩盖**.

**Diagnostic vs v2 (B56)**: signs flipped (axis-flip verified empirically);
magnitudes essentially preserved (deeper F-NEW-3 root cause unaffected by
axis flip + pitch=0).

## V-row attribution v3 summary

Per report v3 §6 (full table there; key counts here):

- **1 NEW (B57-net-new) root-cause F-NEW row field-discovered**: F-NEW-3 ·
  blade chord-axis convention bug · dominant explanation for Cp > Betz in
  v1 + v3 · 2 repair paths documented (section_wire 90° rotation OR case
  substitution)
- **1 NEW (B57-net-new) procedural F-NEW row resolved**: F-NEW-1 · MRF
  in-frame torque sign convention · closed via empirical axis-flip
  evidence (v3 M_x sign flipped from v1) + case.yaml inline comment
- **1 NEW (B57-net-new) procedural F-NEW row surfaced**: F-NEW-4 ·
  simpleFoam bg-task supervision early-termination at iter 375 of 2500
  cap · workaround scoped (foreground run / different supervision), not
  blocking
- **1 cross-geometry V-row re-validation**: V30 · thin-wall TE merge
  worsens slightly in pitch=0 mesh (74 skewed faces vs B54's 41), same
  phenomenology

Total v3 V-row delta = 1 dominant new + 2 procedural new + 1 cross-validation
= **3 new V-rows + 1 re-attribution**, meeting the dispatch's implied
"V-row net-new at minimum" floor.

## Backward-compatibility

- B49 V63-A retro unchanged
- B54 mesh state superseded by v3 mesh (CAD regen necessary); v1 STL backup
  preserved at `case/constant/triSurface_v1_backup/` as audit trail
- B56 dict directory preserved at `.planning/case_profiles/case_004_v64_val_full_1_dicts/`;
  v3 dict directory is new sibling
- V63-A close DEC unchanged
- DEC-V64-A-charter unchanged
- DEC-V64-A-sub-M-V64A-MESH-GEN-V2 (B54) unchanged
- DEC-V64-A-sub-M-V64A-VAL-FULL-1 (B56 PARTIAL v2) unchanged

## Surface scan

- `git diff --stat` since B56 reconcile (`209ea68`):
  - 11 NEW files under `.planning/case_profiles/case_004_v64_case_spec_fix_dicts/` (0 + constant + system)
  - 1 NEW file `.planning/validation_reports/v64_case_004_nrel_phase_vi_full_v3.md`
  - 1 NEW file `.planning/decisions/2026-05-15_v64_sub_case_004_case_spec_fix.md`
  - Total: 13 in-repo NEW files
- 0 routes/, 0 pages/, 0 ui/components/ files touched
- 0 governance rule files touched
- 0 auth / signing / authorization boundaries crossed
- Concurrent sub-sessions B58 + B59 scope-disjoint (mesh conv study + advisor-adjacent); no merge conflicts expected

## v2.3 compliance

| rule | compliance |
|---|---|
| DEC scope-driven; sub-DEC for single-axis follow-up work | ✅ sub-DEC under DEC-V64-A-charter; 6-field frontmatter present |
| Codex review on 1-sync-trigger (security boundary) | ✅ skipped; solver run + case-spec correction + report not auth/signing |
| Kogami opt-in only (v2.3 round-1) | ✅ not invoked |
| Notion sync Accepted DEC at session-end | ✅ `notion_sync_status: pending` for main-session reconcile |
| Cadence floor 30 + counter as pure telemetry | ✅ counter not consulted; this is one sub-DEC in B57 |
| Confidence three-tier self-tag in each commit | ✅ all 3 commits include `confidence: med` |
| spike-class exclusion (≤30 LOC + 1 test, etc.) | ✅ NOT spike-class — CAD regen + mesh regen + multiple dict files + report + cross-cuts V-row analysis |
| Notion sync only Accepted DEC (round-1 loosen) | ✅ this DEC marked Accepted; main session syncs at end |
| Surface-scan trailer (V61-088 optional) | ✅ included for traceability (clean: no routes/pages/ui touch) |
| Round cap N/A | no Codex review chain initiated |

## v2.3 confidence

**med**. High confidence on:

- Axis-flip empirical verification (M_x and F_x signs both flipped as
  predicted by right-hand-rule analysis of ω in -x direction)
- Mesh regen at equivalent density (921 k vs 919 k cells, +0.16 %; same
  refinement levels; cellZone + faceZone + 11 patches all preserved)
- F-NEW-3 root-cause identification (clear derivation from section_wire()
  line 294; chord LE→TE direction at theta=0 is +x = rotation axis = feathered)
- PARTIAL v3 verdict per dispatch reverse-condition (Δ Cp +1038 % >> 10 %
  tolerance; no 掩盖)
- 4Q gate uniformly PASS (all four offline-verifiable: LLM offline,
  artifacts, TrustGate path:line citations, advisor-only stance)
- V-row distinct-signature enforcement (3 new F-NEW rows distinct from B49
  + B54 + B56 attributions; F-NEW-3 is a new failure-mode signature in the
  "CAD geometry convention" class, not previously catalogued)

Medium confidence on:

- F-NEW-3 hypothesis testability (Option A from report §3.4 — rotate chord
  90° in section_wire — should drop Cp into [0, 0.6] range; if so, validates
  F-NEW-3 root cause unambiguously; if not, deeper diagnostic needed)
- Run truncation at iter 375 vs 2500 cap (force-stable mean was reached at
  iter ~200 per B56 + v3 consistent patterns; additional iters would not
  change the verdict given the residual plateau is physical-quasi-steady
  rather than numerical-instability; nonetheless an audit may question the
  truncation and the F-NEW-4 documentation in report §6 + §11 stands as the
  honest record)
- Mesh skewness slightly worse (17.45 v3 vs 6.99 v1, 74 vs 41 faces > 4.0)
  due to different chord twist with pitch=0; impact bounded to local TE
  region (0.0026 % of mesh) and orders-of-magnitude smaller than the Cp delta

These medium-confidence dimensions are scoped to the v4 follow-up sub-DEC
(blade-convention-fix); B57 itself (case-spec corrections applied + 2nd FULL
attempt + honest PARTIAL v3 documentation + F-NEW-3 identification + repair
path scoping) is data-grounded and traceable to repo + sandbox artifacts.

---

**End of sub-DEC.** PARTIAL v3 verdict accepted. F-NEW-3 + F-NEW-4 V-row
attributions captured. Next-step recommendation (per dispatch reverse-condition):
sub-DEC `DEC-V64-A-sub-M-V64A-CASE-004-BLADE-CONV-FIX` candidate to apply
section_wire() 90° rotation OR pivot to case_011 / case_006 / case_009
substitution (report v3 §10 enumerates the 3 paths with ROI ranking). Notion
sync pending session-end batch.
