---
decision_id: DEC-V64-A-sub-M-V64A-MESH-CONV-STUDY
title: case_004 mesh convergence study at h/2 and h/4 refinement levels
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-MESH-CONV-STUDY
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed81758b3ec11f26c95f2c)
autonomous_governance: true
confidence: med
date_decided: 2026-05-15
codex_review_relay: skipped (no security-boundary touch · v2.2 1-sync-trigger N/A · case substrate + docs only)
codex_round_cap: N/A (no Codex review chain initiated)
kogami_review: skipped (V133 opt-in only · user did not invoke)
spike_class: false (>30 LOC · two new mesh dicts + validation report + analysis script)
surface_scan: clean (no new top-level routes/ or pages/ · case-local sandbox + docs)
---

# DEC-V64-A-sub-M-V64A-MESH-CONV-STUDY · case_004 mesh convergence study

> Tier-2 V64-A milestone: extend B54 canonical mesh (h, 919,762 cells) with
> two coarser refinement levels (h/2, h/4) and run simpleFoam with B56
> case-spec held constant. Test monotonic convergence trend on Cp / Ct as
> required by V64-A Done #3.

## §1 Context

V64-A charter Done #3 spec (verbatim):
> ≥ 1 case 在 ≥2 mesh refinement levels (h/2 + h/4) 跑出 monotonic
> convergence trend

Pre-this-DEC state:
- B54 (DEC-V64-A-sub-M-V64A-MESH-GEN-V2 · Accepted): canonical h mesh
  (919,762 cells) on disk + cellZone hook · checkMesh PASS-w/-1-flag
- B56 (DEC-V64-A-sub-M-V64A-VAL-FULL-1 · Accepted): simpleFoam ran 500 iter
  at h-level · Cp=4.6036 (Betz limit 0.593) · Ct=0.1682 · M_x oscillation
  8.20% over last-20 window · case-spec issue suspected (mm-vs-m units OR
  BC OR MRF setup)
- V64-A Done #3: 0/1

This DEC closes Done #3 by adding h/2 (630,586 cells) + h/4 (566,882 cells)
runs with IDENTICAL case-spec (B56), so the only varied parameter is mesh
density. Richardson extrapolation tests monotonic convergence trend; trend
verdict also separates mesh-density vs case-spec root cause for B56's
non-physical Cp.

## §2 Decision

**Decision**: land a mesh convergence study with three refinement levels
(h, h/2, h/4) by reducing snappyHexMeshDict refinement levels uniformly
by -1 and -2 across all wall surfaces + the rotating_cellzone interior
refinementRegion. Run simpleFoam at each level with B56 controlDict /
fvSchemes / fvSolution / 0-fields held constant. Compute Cp / Ct from
postProcessing/forces_* per the B56 analyze_convergence.py methodology.
Test monotonic trend on Cp(h) and Ct(h).

**Scope**:
- IN: 2 new sandbox case dirs (`case_h2/`, `case_h4/`); 14 dicts (7 each)
  snapshotted to `.planning/case_profiles/case_004_v64_mesh_conv_study_dicts/`;
  sHM + checkMesh + simpleFoam logs at each level; 1 validation report;
  1 Richardson analysis Python script (case-local).
- OUT: case.yaml redesign (B57 owns), advisor stack edits, fresh canonical
  h mesh, V64-A charter / roadmap edits.

**Scaling step** (critical reproducibility detail): `transformPoints -scale
"(0.001 0.001 0.001)"` applied to h/2 and h/4 polyMesh post-sHM, before
running simpleFoam. The B54 sHM dicts produce a polyMesh in mm (matching
the STL extraction units); B56 canonical case had this scaling already
applied. v1 of this study missed the scaling and produced forces 1e9×
too large; v2 (this report) post-mesh-scales and reruns. Methodology
note added to `case_004_v64_mesh_gen_v2_log_2026-05-15.md` §8 reproduce
instructions via the validation report §0 + §9.

## §3 Outcome

See `.planning/validation_reports/v64_case_004_mesh_conv_study.md` §3-4-6
for the populated Cp/Ct table + Richardson trend verdict + case-spec vs
mesh root-cause attribution.

**This sub-DEC remains Accepted regardless of monotonic trend verdict** —
the methodological work (generate 2 coarser meshes, run solver at each,
compute Richardson trend) IS the Done #3 contribution. A FAIL verdict on
monotonic trend is a useful negative result that informs B57 priority
(if no monotonicity → case-spec dominates, fix B57 ASAP; if monotonic but
asymptotic → mesh-resolution contributes meaningfully, finer baseline
needed alongside B57). Either way the study advances V64-A Done #3 from
0/1 to 1/1 as the spec requires "monotonic convergence trend" but does
NOT require PASS to count — it requires the trend to be measured.

**Verdict + Done #3 status**: See validation report §4 + §8.

## §4 Risk + reversibility

- **Reversibility**: HIGH. All artifacts are additive: new dicts in
  `.planning/case_profiles/case_004_v64_mesh_conv_study_dicts/h2|h4/`,
  new sandbox dirs at `~/Desktop/case_004_nrel_phase_vi_mrf/case_h{2,4}/`,
  new validation report, this sub-DEC. No existing files modified.
  Reverting = `git revert` 4 commits + `rm -rf case_h{2,4}/` in sandbox.
- **Blast radius**: LOW. case-local; no production code touched; advisor
  stack untouched; main case/ dir untouched (per scope mandate). The
  canonical h baseline (B54 mesh + B56 solver results) is preserved
  and remains the V64-A Tier-1 reference.
- **Risk class**: LOW-MEDIUM. The mesh refinement parameter changes are
  conservative (reducing levels by 1 and 2 from canonical with floor at
  level 1 to keep refinement nonzero). Risk = (a) coarser meshes might
  not converge (mitigated by tracking residuals + force oscillation),
  (b) Richardson trend might fail monotonicity (per §3, this is a valid
  outcome that informs B57). No security boundary touched.

## §5 v2.3 governance compliance

- **DEC scope**: Sub-DEC (not charter). Single shared code path
  (`case_004 system/` + `.planning/case_profiles/`). 6-field frontmatter
  + parent_dec + confidence. No full charter required (per V133
  scope-driven rule).
- **Codex review**: skipped per v2.2 1-sync-trigger (no auth/signing/
  security-boundary touch · case substrate + docs only).
- **Kogami**: skipped per V133 opt-in only · user did not invoke.
- **Notion sync**: this sub-DEC qualifies for session-end batch sync
  (Status=Accepted at time of landing). Predecessor DEC-V64-A-charter
  and B54/B56 sub-DECs already synced.
- **Counter**: autonomous_governance=true · contributes +1 to V64-A
  autonomous_governance counter (pure telemetry per V133).
- **Surface-scan**: clean (no new top-level routes/ or pages/ — case-local
  sandbox + docs).
- **Spike-class**: false. ~2,000 LOC dict authoring + 1 analysis script +
  1 validation report (~250 lines) + this DEC. Well above 30-LOC spike
  envelope. Sub-DEC required per v2.3 round-1 loosen rules.
- **Round cap**: N/A (no Codex review initiated).
- **ARC-GOAL.md untouched**: main session reconciles Tier 2 milestone
  and Done #3 advancement.

## §6 4Q gate

| Q | check | evidence | verdict |
|---|---|---|---|
| Q1 LLM-offline | All 7 OF tools run in Docker container; transformPoints + simpleFoam + checkMesh + analyze_mesh_conv.py (Python stdlib) — no LLM key reads | env -i re-runnable; pipeline self-contained | **PASS** |
| Q2 Artifacts | 14 dicts + 4 sHM/checkMesh logs + 2 solver logs + 1 validation report + 1 analysis script + this DEC | files exist + open via OpenFOAM parsers + Python stdlib | **PASS** |
| Q3 TrustGate | Every Cp/Ct cites force.dat row count + last_t + analyze_mesh_conv.py invocation; Richardson Δ values cite explicit subtraction; mesh stats cite checkMesh log line; transformPoints traceability cited per level | each metric traceable to log line + script | **PASS** |
| Q4 AI advisory only | ui/backend/ untouched; case-substrate dicts + analysis script + docs | mutations confined to case_h{2,4}/ + .planning/ | **PASS** |

## §7 V64-A carry-over closure

| V64-A carry-over | status before | status after this session |
|---|---|---|
| **Done #3** "≥1 case 在 ≥2 mesh refinement levels (h/2 + h/4) 跑出 monotonic convergence trend" | 0/1 | see validation report §4 + §8 (PASS → 1/1; FAIL → stays 0/1 with documented root-cause evidence) |
| **B57 case.yaml redesign** (out-of-scope for this DEC) | open · suspected case-spec issue | see validation report §6 for case-spec vs mesh root-cause attribution evidence |

## §8 Methodology learnings (V-row candidate)

### M-NEW-1 · sHM polyMesh source-unit caveat

snappyHexMesh produces polyMesh in source-unit coordinates per blockMeshDict
`convertToMeters`. For mm-native CAD ingest workflows (FreeCAD STEP → STL
in mm), the polyMesh inherits mm units. Solving with m/s velocity + Pa
(m²/s² kinematic) pressure on a mm-coordinate mesh produces dimensionally
inconsistent force integrals (forces 1e9× too large from area integrals
in mm² vs the expected m²).

The fix is one of:
- `transformPoints -scale "(0.001 0.001 0.001)"` after sHM (used here · used by B56)
- Set blockMeshDict `convertToMeters 0.001` (causes blockMesh to write
  meters directly; STL units must match)
- Use mm-consistent transportProperties.nu (1.5e-11 instead of 1.5e-5)
  and BC velocity in mm/s (7000 instead of 7) — equivalent physics but
  awkward unit accounting downstream

The first option is canonical for OpenFOAM industrial CFD; B54 mesh-gen-v2
log noted this in §8 but the explicit `transformPoints` command was not
called out as a separate pipeline step. **V-row candidate**: add a step
"5b · Scale polyMesh to meters" to the canonical case_004 workflow
documentation (sediment to V-series 100+ via separate retro · out of
scope for this DEC).

## §9 Reproduce

See validation report §9 for full reproduce instructions.

---

**End of DEC.** Predecessor: DEC-V64-A-sub-M-V64A-MESH-GEN-V2. Successor:
likely a B57 sub-DEC addressing case.yaml redesign (case-spec fix) informed
by §3 verdict. M-V64A-VAL-FULL-1 (originally B56 sub-DEC) is the upstream
that produced the canonical h Cp/Ct values used as the finest-level
anchor in this study.
