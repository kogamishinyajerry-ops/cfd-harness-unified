---
decision_id: DEC-V61-198-sub-case-011-v2-fix-verification
title: case_011 v2 sub-session · V85 + V86 narrow-criterion fix verification · surfaces V89 + V90 in dict-orchestration family
status: Accepted
parent_dec: V61-198
phase: Industrial Extension Phase 2 #1 (case_011) · V85/V86 narrow-criterion fix verification · Track C session 2 retro §9 closure
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed81df8a3efed9fade86cf)
parent_artifacts:
  - .planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md (retro §9 v2 fix path spec; §10 pacing notes)
  - .planning/case_profiles/case_011_plate_fin_compact_hx.md (case profile + v2 recommendations)
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V85, V86, V89-NEW, V90-NEW)
  - .planning/methodology/industrial_case_solver_findings.md (corpus mirror)
  - ~/Desktop/case_011_plate_fin_compact_hx/ (substrate)
  - ~/Desktop/case_011_plate_fin_compact_hx/evidence/v2/REPORT.md (this session's deliverable)
trigger: Track C session 2 retro 2026-05-13 §9 scoped V85+V86 fix-verification to a case_011 v2 sub-session. Briefing 5 dispatched the verification work this session. Outcome:V85 narrow §9 criterion verified (region_hot_fluid present, retention 142%) but verification exhaustively surfaced two NEW dict-orchestration defects (V89, V90) that the original V85/V86 sediment did not name; the v2 path required 3 syntactic attempts (v2/v3/v4) to converge — each surfacing additional defect class.
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (case-level substrate change · no main-repo schema modification · per v2.3 §2 risk-tier; corpus appends are evidence sediment not governance schema)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon for this case work)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-13
confidence: high (V85 narrow §9 criterion measured + verified; V89+V90 root-cause analysis grounded in 4 sequential sHM attempts with diagnostic logs preserved; verification surfaces honestly distinguish "narrow criterion PASS" from "comprehensive 3-region retention PASS" — solver run deferred per user gate to avoid running on imbalanced cellZones)
---

# DEC-V61-198-sub-case-011-v2-fix-verification · V85/V86 narrow PASS + V89/V90 sediment

## 1. Why now

Track C session 2 retro `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md`
§9 left V85 + V86 in `open · per-case v2 fix scoped` status, with explicit
verification criterion: `region_hot_fluid.present=true` and retention ≥80% of
geometric-expected cell count. The retro deferred actual fix application to a
"case_011 v2 sub-session" — dispatched this session (2026-05-13) via Briefing 5.

The dispatch chose this work over the alternative (M-TRACK-3 Track C session 3
case_004 NREL MRF) because it (a) closes the V85+V86 narrow criterion on the
existing case, (b) was scoped 半天-1天 (~5h budget acceptable), and (c) had
explicit retro §9 fix-path specification.

## 2. What changed (substrate-only · no main-repo source code)

### 2.1 case_011 substrate at `~/Desktop/case_011_plate_fin_compact_hx/`

- `case/system/snappyHexMeshDict` — v4 (final landed; v1 dict not preserved separately, diff visible in REPORT.md §1 attempts table)
- `case/v1_baseline/{polyMesh/, 01_blockMesh.log, 02_surfaceFeatureExtract.log, 03_snappyHexMesh.log, 04_splitMeshRegions.log, mesh_summary.json}` — preserved v1 baseline
- `case/log/01_blockMesh.log, 02_surfaceFeatureExtract.log, 03_snappyHexMesh.log, 04_splitMeshRegions.log` — v4 logs (overwrote v2/v3 intermediate)
- `case/constant/region_{hot_fluid, cold_fluid, solid}/polyMesh/` — v4 per-region meshes (all 3 present, vs v1 missing region_hot_fluid)
- `case/constant/domain0/polyMesh/`, `domain4/polyMesh/`, `domain5/polyMesh/` — split orphan regions (catch-all, not used by solver)
- `scripts/04_mesh_summary.py` — updated schema v2.0: per-region checkMesh integration, FAIL-on-absent + FAIL-on-retention<80% semantics (replaces v1's silent PARTIAL_FRAGMENTED that downplayed a missing expected region)
- `evidence/v2/mesh_summary.json` — verdict FAIL (cold + solid retention deficits) but `region_hot_fluid` present with 142% retention
- `evidence/v2/REPORT.md` — verification deliverable; §1 attempts table v1→v2→v3→v4, §2 diagnostic comparison, §3 V85 §9 narrow criterion PASS, §4 V89+V90 candidates, §5 solver deferral

### 2.2 cfd-harness-unified corpus (this commit)

- `docs/openfoam_corpus/industrial_solver_findings_v_series.md` — V85 Status `open` → `fix-verified · 1 case (case_011 v4 · 2026-05-13)` + verification appendix; V86 same; **V89 new row** + **V90 new row** appended before `## References`
- `.planning/methodology/industrial_case_solver_findings.md` — mirror of above (corpus drift hook compliance)

## 3. Decisions

### 3.1 V85 + V86 narrow criterion PASS — confirmed status flip

The retro §9 verification criterion was "region_hot_fluid present + ≥80% retention". v4 measured: hot_fluid present (3.34M cells, own polyMesh) with retention 142% (over-100% because mesh includes manifolds beyond analytic-channel baseline). V85 + V86 statuses flip to `fix-verified · 1 case`. Cross-case advisor-enumeration extension (thin_wall_advisor expansion to region-bounding plates) and `shm_dict_validator` (M-A8 umbrella for V86 features-wiring check) remain deferred per retro §9 — Pillar-2 promotion requires N≥2 case evidence.

### 3.2 V89 + V90 surfaced — both `open · per-case fix landed · cross-case deferred`

The v2 sub-session's 3-attempt convergence (v2 failed → v3 attempt with different syntax failed worse → v4 succeeded by combining v2's old-syntax with corrected fluid insidePoints) exhaustively surfaced two NEW dict-orchestration defects that the original V85/V86 sediment did not name:

- **V89**: `cellZoneInside insidePoint` coordinate authored against an STL volume that doesn't contain the coordinate (case-author's "envelope center" heuristic fails at sub-pitch fin geometry). Same defect family as V85 (insidePoint geometric error) but for fluid regions and at sub-pitch (1mm fin) scale instead of stack-margin (5.9mm) scale.
- **V90**: Modern `locationsInMesh ((point) zoneName)` syntax produces empty named cellZones when applied to separate-STL multi-region cases (3+ watertight STLs each defining one region). The modern syntax is designed for single-STL multi-region (`tutorials/heatTransfer/chtMultiRegionHeater`); separate-STL cases require the old syntax (per-surface `cellZoneInside insidePoint` + top-level `locationInMesh`).

Both V89 and V90 are sub-rows in the dict-orchestration family (alongside V85/V86) and both have per-case fixes landed in v4. Cross-case validator extraction (`insidePoint_validator` advisor for V89; `shm_dict_validator` topology-mismatch check for V90) is deferred to N≥2 case evidence (Pillar-2 promotion gate).

### 3.3 Solver run deferred — preserves ARC-GOAL counter integrity

The v4 mesh, while satisfying V85 narrow §9 criterion, has cold fluid retention 3% (74k cells out of ~173k analytic-expected channels) and solid retention 37% (5.86M cells out of 5.44e-4 m³ analytic; missing 63% in `domain0`). Running chtMultiRegionFoam on this mesh would produce a thermal solution that under-represents cold-side convection by ~30×, not a usable KPI baseline. Per dispatch protocol "如果 solver 跑不通...sediment 新 V-row · 不要硬上 hack", the solver was deferred rather than forced — ARC-GOAL e2e numerics class counter remains 1/3, not bumped to 2/3.

A case_011 v3 sub-session (future dispatch) would address the cold/solid retention deficits (likely path: bump cold-fluid surface to level (2, 3) for 5-cells-per-channel resolution; fix `locationInMesh` to a position that disconnects bbox exterior from active stack), then run solver.

## 4. ARC-GOAL counter delta

| metric | pre-session | post-session | net |
|---|---|---|---|
| #1 Track C session 通过 case 数 | 2 | 2 | +0 (this is a sub-session of case_011, not a new Track C case) |
| #2 LANDED advisor count | 4 | 4 | +0 |
| #3 V-series 行数 | 88 | **90** | +2 (V89 + V90) |
| #4 End-to-end solver 跑通 numerics class 数 | 1 | 1 | +0 (solver deferred; CHT-multi-stream not advanced) |
| #5 radar left half | 6.4 | 6.4 | +0 |
| #6 radar right half | 8.7 | 8.7 | +0 |

V85 + V86 status flips (`open` → `fix-verified · 1 case`) are NOT new V-rows — they are sediment-row updates. The +2 to V-series count comes from V89 + V90 as genuinely new findings surfaced this session.

## 5. Files modified (corpus drift hook will validate)

Both staged in same commit per `scripts/governance/check_corpus_sync.py`:

- `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (V85 status, V86 status, +V89, +V90)
- `.planning/methodology/industrial_case_solver_findings.md` (mirror)

Plus:

- `.planning/ARC-GOAL.md` (V-series count 88→90; e2e numerics class explanation updated)
- `.planning/decisions/2026-05-13_v61_198_sub_case_011_v2_fix_verification.md` (this file)

Substrate files at `~/Desktop/case_011_plate_fin_compact_hx/` are NOT committed (case substrate is outside main repo).

## 6. Cross-references

- **Retro spec**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md` §9 (v2 fix path), §10 (pacing notes)
- **V-rows**: V85 (status flip + verification appendix), V86 (status flip), V89 (new), V90 (new)
- **Substrate evidence**: `~/Desktop/case_011_plate_fin_compact_hx/evidence/v2/REPORT.md` (full v1↔v4 diagnostic table)
- **Case profile**: `.planning/case_profiles/case_011_plate_fin_compact_hx.md` (cross-case status will be updated session-end to reflect v4 outcome)
- **Companion session**: Track C session 1 V82 §9 in-place fix verification on case_010 sandbox 2026-05-13 (same retro+verification protocol pattern)

## 7. Outcome summary (executive)

**V85 fix-verified · 1 case · 2026-05-13** (narrow §9 criterion: region_hot_fluid present + retention ≥80% — measured 142%). **V86 fix-verified · 1 case · 2026-05-13** (`.eMesh` wired, sHM consumes them). **V89 + V90 surfaced** as candidate cross-case patterns in the dict-orchestration family. **Solver deferred** to preserve ARC-GOAL e2e-numerics-class counter integrity. Substrate preserved for future case_011 v3 sub-session.

— EOF —
