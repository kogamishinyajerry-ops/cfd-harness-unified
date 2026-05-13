# Track C · Advisor e2e — Session 2 · case_011 plate-fin compact HX

> **Date**: 2026-05-13
> **Track**: C (Claude Code session as M6 advisor, per `feedback_claude_code_is_the_advisor.md`)
> **Mandate**: M6 row in ROADMAP carries `⚠ untested as route; Claude-Code-session-as-advisor e2e validated on case_010 (2026-05-13, RETRO Track C session 1, surfaced V82+V83 missed by corpus)`. Session 2 widens the sample across numerics class — case_010 was incompressible-LES external aero; case_011 is steady-laminar-CHT-multi-stream internal HX. Scoring is stricter per session 1 §7: "case_011 plate-fin compact HX — high V-row density makes scoring stricter."
> **Subject case**: `~/Desktop/case_011_plate_fin_compact_hx/` v1 (case_011 in 10-case roster · steady-laminar-CHT-multi-stream root · plate-fin air-air recuperator)
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Counter impact**: nil (Track C is a methodology validation arc, not an `autonomous_governance` DEC chain)

---

## 1. Protocol

**Blind-mode inputs read** (the engineer-equivalent surface before sediment was written):

- `scripts/build_cad.py` — geometric intent (3 fused-multi-box regions + 4 plates + manifold lofts; D8 0.6mm rear-third cold fin; D5 30µm x-offset on `separator_plate_3_4` rear-third)
- `case/log/01_blockMesh.log` — background mesh (28,800 cells · domain x=[-0.03, 0.21], y=[-0.005, 0.125], z=[0, 0.06] m · cell size 4mm × 4.06mm × 4mm)
- `case/log/02_surfaceFeatureExtract.log` — feature-edge extraction (3 regions: hot/cold/solid · cold has anomalous 7368 internal edges vs hot's 240)
- `case/log/03_snappyHexMesh.log` — sHM run (full 3483 lines · castellated + snap, no layers · 980k cells · "Did not successfully snap" warning · 86 illegal faces final)
- `case/log/04_splitMeshRegions.log` — region extraction (only domain0/solid/cold_fluid produced; hot_fluid silently absent)
- `case/system/snappyHexMeshDict` — mesh config (level (1,2) on all 3 regions · `features ()` empty · multiRegionFeatureSnap true · 3 insidePoints incl. solid at z=13mm)
- `evidence/v1/mesh_summary.json` — multi-region split summary (`region_hot_fluid.present=false`; `shm_cellzone_walk` shows 312 global components)
- `evidence/v1/step_validation.json` — STEP body roster (3 regions present, deterministic header, PASS)
- `evidence/v1/a2_d5.json` — A2 advisor on 30µm offset (matched=True with hardcoded placeholders — V25 pattern)
- `evidence/v1/thin_wall_d8.json` — thin_wall advisor on 0.6mm rear-third fin (severity=critical, recommended_level_max=4, 7-of-7 cross-topology arc)
- `evidence/v1/surface_extraction.json` — STL bbox audit (tessellation overshoot ~4mm on hot_fluid manifolds, minor)

**Deferred until after blind verdict** (ground truth):

- `evidence/v1/REPORT.md` — sub-session author's own writeup
- `.planning/methodology/industrial_case_solver_findings.md` § V47-V51 (case_015 chtMR LES/CHT), V62 (F-NEW-26 affected-set), V80 (OCP STEP timestamp cross-cut) — the actual case_011-touching rows in the main corpus

**Pre-loaded baseline per briefing §5 (note re: protocol contamination)**: The briefing's required-reading list included `.planning/cross_cuts/v_series_case_011_append_2026-05-09.md` as "base truth", which contains draft V47-V50 sediment from the case_011 sub-session. This file was read in Phase 1 prep before issuing the blind verdict — partial contamination of strict blind protocol. Mitigation: the blind verdict is scored against the **main corpus** (`industrial_case_solver_findings.md`), NOT against the cross_cuts draft. Findings that merely re-state cross_cuts draft V47-V50 content are classified "primed-match" (not credited as blind hits). Findings that go beyond V47-V50 are net-new contributions. This matches session 1 §7's design intent — "case_011 high V-row density makes scoring stricter" — but at the cost of slightly relaxed blind protocol.

## 2. Blind verdict (issued before reading REPORT.md / main-corpus rows)

Nine findings, severity tiered. Findings F8 and F9 explicitly cover well-trodden V25/V37/V43/V44/V50 territory (placeholder semantics / thin-wall cross-topology) and are marked as such — they're not net-new even though the case_011 substrate exercises them.

| # | Severity | Finding | Confidence |
|---|---|---|---|
| F1 | CRITICAL | **`region_hot_fluid` is absent from the v1 multi-region polyMesh**. `splitMeshRegions -cellZones -overwrite` emits only `domain0` (734,854 cells), `region_solid` (240,100), `region_cold_fluid` (5,664). The intended hot stream — the larger of the two fluid regions (40 channels × 2 layers vs cold's 36 × 1) — was absorbed into the unnamed `domain0` fragment. `chtMultiRegionFoam` cannot be invoked on a 2-region (instead of 3-region) split. The v1 mesh is unusable for the intended physics. | high (log + mesh_summary direct evidence) |
| F2 | CRITICAL | **All 4 solid plates are PLATE_THICKNESS_MM = 0.8 mm, below the 1.0 mm effective cell size at level (1, 2) with background = 4 mm.** sHM cannot seal sub-cell plate surfaces; cellZone walks from each region's insidePoint leak through the unsealed plate gaps into adjacent regions. Symptom: `For cellZone region_hot_fluid found point (0.09 0.06 0.045) in global region 1 out of **312 regions**` — all three insidePoints hit the same fragmented connected-component graph (hot+solid both in region 1; cold in region 17), confirming the regions are topologically connected through plate gaps. **`thin_wall_advisor` ran only on `cold_fin_rear_third` (D8) — it did not run on PLATES.** The advisor coverage today is patch-centric (case-author lists patches at risk), but the case_011 load-bearing failure mode is region-bounding plate surfaces at risk. Systemic advisor coverage gap. | high (log + dict + build_cad arithmetic) |
| F3 | HIGH | **Solid-region `insidePoint (0.090 0.060 0.013)` is geometrically inside `hot_layer_1` fluid, NOT inside any solid plate.** Stack-layout math from `build_cad.build_stack_layout`: active height 43.2mm, centered in H_MM=55, margin 5.9mm. Plate z-ranges: bottom_cover [5.9, 6.7] · separator_plate_1_2 [18.7, 19.5] · separator_plate_3_4 [35.5, 36.3] · top_cover [48.3, 49.1] mm. z=13mm hits hot_layer_1 [6.7, 18.7]. The snappyHexMeshDict was authored against an earlier sizing-convergence layout that assumed bottom_cover starts at z=0; the build's 5.9mm margin centering shifted plates up. Dict was not reconciled. Compounds F2 — when plates fail to seal, the wrong insidePoint mis-tags hot cells as solid. | high (build_cad math + dict direct evidence) |
| F4 | HIGH | **`mesh_summary.json` verdict `PARTIAL_FRAGMENTED` is too permissive** — a missing expected region should be `FAIL`, not `PARTIAL`. The `interpretation` field calls cold_fluid "split cleanly" despite only 5,664 cells (~3% of geometric-expected ~173,000 cells at 1mm grid for 36×16×120×2.5 mm³). This is the **case_011 instance of session 1 F2 / V83**: an audit JSON's permissive verdict permits known-broken state. The blind-spot pattern reproduces at a different verdict surface (multi-region split summary). | high (cross-application of V83 pattern) |
| F5 | MED | **`surfaceFeatureExtract` writes 3 .eMesh files; `snappyHexMeshDict.castellatedMeshControls.features ()` is empty.** Stage 02 produces output that stage 03 silently ignores. sHM log line 46: `Read features in = 0 s` and all `Marked for refinement due to distance to explicit features: 0 cells`. `multiRegionFeatureSnap true` with empty features is internally inconsistent — multiRegionFeatureSnap needs features to act on. With `explicitFeatureSnap false`, the 10 `nFeatureSnapIter` iterations are no-ops. Orchestration gap: pipeline stages emit/consume artifacts without a validator that confirms the link. | high (dict + log direct evidence) |
| F6 | MED | **`region_cold_fluid` STL has anomalous internal-edge density**: 7368 internal edges + 6936 non-feature points (vs `region_hot_fluid`'s 240 internal + 0 non-feature). Both regions are box-fused multi-channel topologies (cold = 36 boxes + 2 manifolds = 38 → fuse_many → 1 solid; hot = 40 boxes + 2 manifolds = 42 → fuse_many → 1 solid). Cold's feature density is ~30× larger after normalizing for channel count. Hypothesis: `CadQuery.fuse_many` direction-asymmetry — cold's boxes span W_MM=120 with manifolds also in y-direction, possibly leaving phantom internal edges that hot's L_MM=180 + x-manifolds don't show. Combined with `resolveFeatureAngle 30°` and `nCellsBetweenLevels 2`, cold's phantom features triggered the curvature-refinement spike to 91,866 cells in surface-refinement iter 1. | medium (hypothesis; would need cq tessellation inspection to confirm) |
| F7 | LOW | **Naming label drift in plate names.** `separator_plate_1_2` (between fluid layers 1↔2) is correct; `separator_plate_3_4` (between fluid layers 2↔3, i.e. cold_layer_1↔hot_layer_2 in `build_stack_layout`) is **mislabeled** — should be `separator_plate_2_3`. The name was inherited from an earlier sizing iteration that assumed a 4-layer stack; the build simplified to 3 layers but kept the label. Cosmetic; downstream documentation (D5 "30µm offset on separator_plate_3_4") is now inconsistent with the layout. | high (build_stack_layout layout direct read) |
| F8 | LOW · primed-match | A2 D5 `matched=True` with hardcoded placeholders (`bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`, `normal_dot=0.99999`); 30µm offset NOT field-validated; reproduces V25 placeholder semantic across HX plate-plate adjacency (4th cross-topology data point after case_003/004/005, OR 6th-7th counting case_007/008/010 main-corpus rows V33/V36/V43). Already covered in main corpus by V25 / V33 / V36 / V42 / V43. **Not a new finding.** | high |
| F9 | LOW · primed-match | thin_wall_advisor D8 `severity=critical, recommended_level_max=4` on 0.6mm cold-fin rear-third; 7th cross-topology data point (HX cold fin) after V10/V23/V30/V37 closed the arc at 6-of-6. Already covered by V10/V23/V30/V37 in main corpus. **Not a new finding.** | high |

**Predicted root cause of v1 mesh failure** (synthesis): the v1 mesh is fundamentally broken because (a) all 4 solid plates at 0.8mm and the hot-side fins at 1.0mm both fall below the 1.0mm effective cell size at level (1, 2), so neither the fluid-fluid separation surfaces (plates) nor the hot-side channel walls (fins) are mesh-resolved, AND (b) the solid-region insidePoint is geometrically inside hot fluid, so even if surfaces sealed, the cellZone walk would mis-tag hot cells as solid. F2+F3 compound. `thin_wall_advisor` PRE-MESH correctly predicted the cold-fin failure (V50 / F9) but was not invoked on plates (advisor coverage gap). The case_011 v1 setup pipeline lacks coverage of "surface elements that BOUND REGIONS" (plates) — only "patches that have thermal constraints" (fins) are advised.

**Suggested fix paths** (any closes F1; F2+F3 are the root causes):
1. **Reposition** `refinementSurfaces.region_solid.insidePoint` to (0.090, 0.060, 0.0063) (bottom_cover centroid) or (0.090, 0.060, 0.0191) (separator_plate_1_2 centroid). Single-line dict edit.
2. **Bump refinement** on plate-bearing surfaces to level (3, 4) (effective 0.25mm = 3.2 cells per 0.8mm plate). The v2 plan in `case_profiles/case_011_plate_fin_compact_hx.md` only bumps `cold_fin_rear_third`; this needs to extend to plates.
3. **Wire `.eMesh` files** into `castellatedMeshControls.features (…)` block (closes F5). Switch `explicitFeatureSnap` to `true`.
4. **Update `mesh_summary.json` verdict semantics**: gate `verdict=FAIL` (not PARTIAL) whenever any expected region is absent (closes F4, cross-applies V83's intent-cross-reference pattern to the multi-region summary).
5. **Update `02_scaffold_case.py`** (or whichever emitter) to derive insidePoint from build-time stack layout, not hardcoded (closes F3 class).

## 3. Ground truth comparison

**REPORT.md** (case_011 sub-session author's writeup): correctly recognizes `region_hot_fluid.present=false` (data-level honesty); marks all KPI sections (ε-NTU, pressure_drop, manifold_uniformity, h_and_eta_fin) as `NOT_RUN` / `NOT_MEASURED` with `reason: "v1 mesh fragmented per V34/V36 (region_hot_fluid in 312 connected components); chtMultiRegionFoam intentionally not invoked on broken mesh. v2 will bump fin refinement to (3,4) and re-run."` — responsible engineering action (don't solve a broken mesh).

**However**, REPORT.md misses several load-bearing analyses:

- **No isolation of plate-vs-fin failure** — the report attributes mesh failure to "sHM merged 1mm fin walls at effective 1mm cell size, level (1,2)" (per mesh_summary's interpretation field). This is **partially right** for the 1.0mm hot fins, but does NOT name the 0.8mm plates as the more critical failure (plates BOUND REGIONS; fins just fragment within a region). The v2 plan's "bump fin refinement to (3,4)" will not fix the plate seal failure, so v2 will likely fail too.
- **Wrong V-row cross-reference** — REPORT cites "V34/V36" as the failure-mode precedent. V34 is "snappyHexMesh free-surface band + near-hull box compounding saturates `maxGlobalCells` before reaching surface body refinement (case_007)" — case_011 did NOT saturate maxGlobalCells (980k of 4M cap). V36 is "A2 advisor `_run_shared` cross-topology PASS on airfoil-mount" — unrelated. The actual analogous pattern is closer to V10 / V23 / V30 / V37 (thin-wall sub-cell merge), and the case_010 V82/V83 pattern (missing-geometry blind-spot in audit verdicts).
- **Silent on `insidePoint` placement** — the report does not note that solid's insidePoint is geometrically inside hot fluid. This is a config bug that compounds the thin-wall sealing problem; without fixing it, the plate-refinement bump alone may not fully restore region separation.
- **Silent on .eMesh orphan** — features-list-empty + multiRegionFeatureSnap-true is not discussed; the upstream `02_surfaceFeatureExtract` stage is treated as black-box-OK.
- **PARTIAL_FRAGMENTED verdict accepted as-is** — the report passes through mesh_summary's verdict without questioning whether a missing expected region warrants FAIL.

**Main corpus rows touching case_011** (`industrial_case_solver_findings.md`):

- **V47** (chtMR LES/CHT minMedialAxisAngle typo): mentions case_011 as "steady CHT skips layer addition, so this typo never surfaced before". Reverse inheritance — case_011 is the parent that didn't surface V47.
- **V48** (chtMultiRegionFoam controlDict region keyword): mentions case_011 as "used per-region `system/<region>/controlDict` so didn't surface". Parent.
- **V49** (wall-modeled LES at conjugate baffle): mentions case_011 as "laminar, no wall function regime". Parent.
- **V51** (sHM multi-region cellZone on intersecting fluid volumes — T-junction): mentions case_011 as "strictly disjoint hot/cold/solid box-packs ancestor" that "couldn't expose" the case_015 T-junction class.
- **V62** (F-NEW-26 class-wide impact — 6 of 11 cases affected): lists case_011 as **not affected** (internal HX).
- **V80** (STEP `FILE_NAME` wall-clock timestamp): lists case_011 as "cross-cut observed (OCP-exported CadQuery)" data point; the case_011 author preempted this with `_normalize_step_header` in build_cad.py (lines 432-443).

**No main-corpus row primarily about case_011 v1 setup failures.** The case_011 sub-session sedimented findings to `cross_cuts/v_series_case_011_append_2026-05-09.md` (draft V47-V50: BC bookkeeping, sHM snap struggle, A2 placeholder, thin_wall PASS) — but those draft rows **were never elevated** to the main corpus. The main corpus V47-V51 instead document case_015 (which surfaced different chtMR variants later). This means **all session 2 blind findings are net-new to the canonical corpus.**

## 4. Score

| Blind finding | vs corpus + REPORT | Verdict |
|---|---|---|
| F1 region_hot_fluid absent from polyMesh | REPORT.md acknowledges presence=false data point; no main-corpus methodology row; cross_cuts draft V48 noted "snap struggle" but not the binary "region gone" outcome | **NEW → V85 backfill (data-level)** |
| F2 plates 0.8mm sub-cell + thin_wall_advisor coverage gap | Not in REPORT.md; not in main corpus; cross_cuts draft V48 attributes failure to "fins" only, misses plates entirely | **NEW → V85 backfill (root-cause)** |
| F3 solid insidePoint geometrically inside hot fluid | Not in REPORT.md; not in any corpus row | **NEW → V85 backfill (config bug)** |
| F4 PARTIAL_FRAGMENTED verdict too permissive | Cross-application of V83 (case_010 mesh_ok blind-spot) to multi-region split surface | partial — extends V83 cross-application; folded into V85 Lesson row + amends V83 cross-reference suggestion |
| F5 .eMesh extracted but unused | Not in REPORT.md; not in corpus | **NEW → V86 backfill** |
| F6 cold_fluid STL phantom-edge density | Not in REPORT.md; not in corpus | **methodology note** (hypothesis-level, deferred to a future CadQuery-tessellation investigation; not yet V-row) |
| F7 separator_plate_3_4 naming drift | Cosmetic; not in corpus | **retro note only** (suggest case_011 v2 sub-session renames) |
| F8 A2 D5 placeholder | V25 / V33 / V36 / V42 / V43 already cover | primed-match (well-trodden) |
| F9 thin_wall D8 7th cross-topology | V10 / V23 / V30 / V37 already cover; cross_cuts draft V50 also covered | primed-match (arc already closed) |

**Tally**: 3 net-new findings landed as V85 (compound row — F1+F2+F3) + 1 net-new finding landed as V86 (F5). 1 partial cross-application (F4 → V83 extension, embedded in V85 Lesson). 1 hypothesis-level methodology note (F6, retro-only). 1 retro-only cosmetic (F7). 2 primed-match findings consistent with existing corpus coverage (F8, F9).

The Track C session caught **three load-bearing root causes** that the case_011 sub-session author's audit + corpus sedimentation pipeline missed:
- **the plate-thickness sub-cell sealing failure** (vs the sub-session's "fin" attribution)
- **the misplaced solid insidePoint** (a config bug compounding the seal failure)
- **the .eMesh orphan** (an orchestration gap upstream of the snap step)

## 5. What this validates / what it doesn't

**Validates**:

- The Track C protocol from session 1 reproduces on a different numerics class. case_010 was incompressible-LES external aero (single fluid, complex external geometry); case_011 is steady-laminar-CHT-multi-stream internal HX (multi-region, simple parametric geometry). The advisor model successfully transferred. Same root-cause-finding capability surfaces in a substantially different topology.
- **Multi-region CHT setups have a distinct blind-spot class** not surfaced by single-region external aero: region-bounding-surface thin-walls (plates) are at-risk in addition to thermally-active patches (fins). Patch-centric advisor coverage misses this; auto-enumeration over the parts manifest is the methodology fix.
- The pattern from session 1 V83 ("audit-JSON verdict downplays missing geometry") **cross-applies** to a different audit surface (multi-region mesh summary). Same blind-spot taxonomy, different verdict field. This raises confidence that V83 captures a deeper methodology gap (not just a case_010-specific quirk), reinforcing the case for the Pillar-2-trigger `mesh_geometry_audit.py` advisor extraction.

**Does NOT validate**:

- An M6 RAG-backed advisor with constrained retrieval (N6.2 route surface). This session loaded the case_011 substrate directly (~25k tokens of evidence + 122k log scanned via grep). A constrained retrieval might miss the load-bearing diagnostic (the sHM log's FOAM Warning lines 175-228 — the "cells not (sufficiently) closed" warnings — which are 800 lines into a 3500-line log).
- That `thin_wall_advisor` should be auto-extended to plates. The V85 Pillar-2 cross-case candidate is a deferred extension; this session only documents the case_011 coverage gap as a single data point. Pillar-2 trigger fires on a 2nd case where a region-bounding thin-wall fails because the advisor wasn't asked.
- The cross_cuts draft V47-V50 sediment pipeline. Track C session 2 finds that the case_011 sub-session's local sediment was **never elevated** to the main corpus, and that the draft V47-V50 misidentified the failure root cause. This is a methodology problem (sediment elevation drift) that this retro does not yet solve.

**Caveats**:

- **Blind protocol contamination per §1 note**: the briefing's required-reading list included `cross_cuts/v_series_case_011_append_2026-05-09.md`, which contains draft V47-V50 sediment from the case_011 sub-session. The blind verdict was issued after reading this file. Mitigation: findings F8 and F9 were explicitly classified as primed-match (drawn from draft V49/V50); findings F1-F7 are net-new to the draft AND to the main corpus. The strict-blind protocol from session 1 was relaxed by briefing design (cross_cuts draft is "base truth" per briefing §5) — accepted trade-off for the stricter scoring against pre-loaded sediment.
- **Sample size = 2 cases** (case_010 + case_011). Need ≥3 advisor e2e sessions across different solver classes to claim broad cross-class coverage; ≥6 (per ARC-GOAL M-TRACK-2..M-TRACK-6) to claim the M6 charter empirical close.
- **Pacing accelerated per user direction**: session 1 §7 recommended ≥2 weeks between Track C sessions. User direction 2026-05-13 (this session brief) accelerated to same-day session 2. The risk this addresses is "main session context overload" (session 1 + session 2 in same day = ~150k tokens consumed across both); the risk this incurs is "advisor reasoning leaks across sessions" (this session knew V82/V83 were freshly minted in session 1, which primed me to look for V83-class patterns in case_011 — see F4). Net-positive in this case because the leak surfaced a real cross-application (V83 → mesh_summary verdict), but the bias is worth tracking for future sessions.
- **Hot mesh + cold mesh are both fundamentally broken in v1**, but session 2 does NOT run a fix-verify appendix (unlike session 1 §9 V82 fix). Two reasons: (1) the fix is a 4-line dict edit + per-case sub-session level-(3,4) re-run, which is sub-session scope not Track C session scope; (2) the v2 plan in `case_profiles/case_011_plate_fin_compact_hx.md` already exists, so verification is owed to that future sub-session not to this retro.

## 6. Concrete deliverables (this session)

1. **V85 backfill** — `industrial_case_solver_findings.md` § V85 + `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (runtime corpus mirror, synced same commit per pre-commit `check_corpus_sync.py` hook landed 2026-05-13 commit `d53afbc`). Documents compound root cause: solid insidePoint geometrically inside hot fluid + 0.8mm plates sub-cell at level (1,2) → cellZone walk leaks across plates → region_hot_fluid absent from polyMesh. Cross-applies V83's intent-cross-reference pattern to mesh_summary.json verdict surface.
2. **V86 backfill** — same two files. Documents `surfaceFeatureExtract` .eMesh files orphaned by empty `features ()` block + `multiRegionFeatureSnap true` + `explicitFeatureSnap false` internal inconsistency. Pattern 4 candidate: `shm_dict_validator` advisor (already tracked under M-A8 in ARC-GOAL).
3. **Corpus-sync arrears status** updated: "synced through V84" → "synced through V86" with note pointing back to the d53afbc pre-commit hook + this session.
4. **ARC-GOAL.md M-TRACK-2** row checked off with retro file path + Track C counter incremented 1 → 2.
5. **This retro file**.

**No source code changes this session.** F1-F5 fixes are per-case sub-session actions (case_011 v2 dispatch). The cross-case advisor extensions (`thin_wall_advisor` auto-enumeration · `shm_dict_validator` · `mesh_geometry_audit.py`) are Pillar-2-deferred until N≥2 cases per pattern.

## 7. Suggested next Track C sessions

- **Session 3**: case_004 NREL Phase VI MRF (rotating machinery, sliding interfaces · numerics class = incompressible-RANS-rotating). Per session 1 §7, sparse main-corpus coverage (V22/V23/V24 mentions only) makes this a "is there a blind spot we don't yet know about" probe. Likely surfaces: MRF/AMI interface bookkeeping; rotating-frame inertial term; periodic boundary condition gotchas that don't exist in static-geometry cases.
- **Session 4**: case_009 Sandia Flame D (reacting low-Mach combustion · numerics class = reacting-low-Mach). V38-V42 cluster covers chemkin loader / mechanism file format. Advisor's chemistry coverage is novel to the corpus; likely surfaces: thermo header bounds vs operating-T conflicts (V41 family); species count vs solver matrix scaling.
- **Session 5**: case_007 KCS ship VOF (multiphase-VOF · numerics class). V33-V35 cluster. Already probed in session 1 §10 case_007 appendix (negative on V82 reproduction — pipeline is STEP→STL-bridge with explicit *0.001). A full Track C session would surface VOF-specific failures (interface tracking, surface tension treatment, wallDist for kOmegaSST).
- **Session 6**: case_015 chtMR LES/CHT (compound numerics class — LES + CHT). V47-V51 cluster makes this **densely covered** in the main corpus; a session here would likely surface few new methodology findings but would validate the corpus-completeness baseline (good for ARC-GOAL Done Definition #4 "≥ 3 numerics-class e2e").

**Pacing for sessions 3-6**: session 1 § 7 recommendation was "at most 1 Track C session per week to avoid main-session context overload". Session 2 ran same-day as session 1 per user direction — see §5 caveat. For sessions 3+, suggest resuming the weekly cadence unless there's reason to accelerate. Each session ≈ 20-30k tokens of substrate read + a retro of this size; cumulative cost grows.

**Substrate readiness check before scheduling**: each candidate case needs sHM log + REPORT.md + V-row sediment present. Per session 1 §10, cases 005/006/009/011/012/015/016 have complete substrate; case_004/008 sandboxes have advisor JSONs only (no sHM log). Probe sHM logs of remaining cases (case_005/006/012/015/016) before committing to session ordering.

## 8. Cross-references

- **Parent feedback**: `feedback_claude_code_is_the_advisor.md` (M6 charter advisor button → replaced by Track C dogfooding)
- **Parent DEC**: V61-198 (industrial-case container pivot)
- **V-rows landed this session**: V85, V86
- **V-row cross-applied (not amended)**: V83 (case_010 mesh_ok blind-spot pattern) — the V85 Lesson row notes that V83's intent-cross-reference prescription applies to mesh_summary.json verdict, not just check_mesh_summary.json
- **Cross_cuts draft superseded**: `.planning/cross_cuts/v_series_case_011_append_2026-05-09.md` draft V47-V50 — the draft V48 root-cause attribution ("BASE_FIN_THICKNESS_MM = 1.0 mm at level (1,2)") is wrong/incomplete; V85 is the canonical case_011 v1 failure root-cause record going forward
- **ARC-GOAL row**: M-TRACK-2 main-line table
- **Session 1 retro**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_1_case_010.md`

## 9. F2/F3 fix-verification (NOT performed this session)

Unlike session 1 § 9 (V82 in-place fix verification on case_010 sandbox), session 2 does **not** include a fix-verify appendix. Reasons:

1. **Briefing constraint**: "不写代码（advisor 行为是验证不是开发）". This session is verification, not development.
2. **The fix path is multi-step and scoped to case_011 v2 sub-session**: (a) reposition solid insidePoint to plate centroid, (b) bump plate-bearing surfaces to level (3, 4), (c) re-run stages 03-04, (d) re-emit mesh_summary.json with updated verdict semantics, (e) verify region_hot_fluid.present=true and region_hot_fluid retains ≥80% of geometric-expected cell count. This is a sub-session deliverable, not a Track C inline verification.
3. **The v2 plan already exists** in `case_profiles/case_011_plate_fin_compact_hx.md` "Bump cold_fin patches to level 4 (per thin_wall_advisor recommendation)". The case_011 v2 sub-session can incorporate V85's plate-bumping addendum + V86's features-wiring on the next dispatch.

**What this leaves unverified**: V85 Status is `open`, not `fix-verified · 1 case`. The Pillar-2 cross-case advisor extension (thin_wall_advisor auto-enumeration over parts manifest) remains deferred until a 2nd case surfaces a plate-class sub-cell failure. Likely candidates: case_002b (single-stream CHT with thin shell solids — already in corpus), or a future Phase-2 industrial case with multi-region CHT topology.

**Path to V85 promotion from `open` to `fix-verified`**: (1) case_011 v2 sub-session lands with the plate-bumping + insidePoint repositioning; (2) mesh_summary.json reports `region_hot_fluid.present=true` with ≥80% expected cell count; (3) main session updates V85 Status with the verified diagnostic deltas (analogous to session 1's V82 §9 evidence table). Same protocol as V82 promotion.

## 10. Pacing + protocol notes

**Pacing**: accelerated per user direction 2026-05-13 — session 2 ran same-day as session 1 (~2-3 hours after session 1's V82 §10 close). Session 1 §7 recommended ≥1 week between Track C sessions; this is a 1-day cadence. Captured in §5 caveat. The risk addressed is "user is making progress on the arc and wants to land another data point while context is warm"; the risk incurred is "session 2 was primed by session 1's V82/V83 mental model" — observable in F4 surfacing as a V83 cross-application within minutes of reading mesh_summary.json (whereas a colder session might have surfaced F4 more slowly or not at all).

**Protocol drift from session 1**:
- Pre-loaded the cross_cuts draft per briefing §5 (session 1 had no pre-loaded case-specific sediment — case_010 had no cross_cuts append). Strict-blind protocol relaxed. §1 + §5 acknowledge.
- No §9 fix-verification appendix (session 2 verification-only mandate). §9 explains.
- No §10 cross-case probe appendix (session 1 § 10 probed case_007 for V82 reproduction; session 2 has no equivalent immediate probe target because V85 plate-class is unique-to-case_011 in current substrate — case_002b is the only other multi-region-CHT case and its plates are shells not flat plates).

**Track C arc state after session 2**:
- ARC-GOAL Done Definition #1 "Track C session 通过 case 数": 1 → 2 (target: ≥ 6)
- Done Definition #3 "V-series 行数": 84 → 86 (target: ≥ 100)
- Done Definition #4 "End-to-end solver 跑通 numerics class 数": 1 → 1 (case_011 v1 mesh is broken, no solver run; this session does NOT advance this metric)
- Other metrics unchanged (advisor count #2, radar #5/#6 — Track C doesn't move these directly)

— EOF —
