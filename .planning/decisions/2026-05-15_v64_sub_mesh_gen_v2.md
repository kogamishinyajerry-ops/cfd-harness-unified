---
decision_id: DEC-V64-A-sub-M-V64A-MESH-GEN-V2
title: V64-A Tier 1 sub-DEC · case_004 NREL Phase VI MRF mesh gen v2 · blockMesh + snappyHexMesh + cellZone extraction · 919k cells · unblocks solver execution
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 1 · M-V64A-MESH-GEN-V2
notion_sync_status: synced 2026-05-15 (https://www.notion.so/360c68942bed81cab120c458d0c58c77)
authored_by: Claude Code Opus 4.7 (1M context) · sub-session B54
authored_at: 2026-05-15
confidence: med
codex_review_relay: skipped (v2.3 1-sync-trigger · case substrate + documentation · no auth/signing/security-boundary touch)
kogami_review: skipped (v2.3 opt-in only · user did not invoke)
autonomous_governance: true
---

# DEC-V64-A-sub-M-V64A-MESH-GEN-V2 · case_004 NREL Phase VI MRF mesh gen v2

## Status

**Accepted 2026-05-15** — V64-A first Tier-1 sub-DEC closing the V63-A B49 PARTIAL §4 "Step 6 · Mesh + solver run · DEFERRED to v2" gate.

Verdict on **mesh gen** itself: **PASS** (mesh successfully generated · cellZone extracted · checkMesh validates topology). Verdict on **plan-file cell-budget target (5-10 M)**: **under** (919k cells; v2 tuning iteration scope). The "Accepted" status records the **executable pipeline + cellZone hook + V63-A carry-over closure**, not a claim of 5-10M-cell budget achievement.

## Goal (verbatim from B54 dispatch)

> "落地 V64-A Tier 1 sub-DEC — M-V64A-MESH-GEN-V2 (case_004 NREL Phase VI MRF mesh gen v2 · 解锁 solver execution · 推 V64-A 接下来 M-V64A-VAL-FULL-1 可启动 · 闭 V63-A carry-over #2 first half)"

Tied to V64-A charter §Done #5 (V63-A carry-over closure ≥ 4/8) and unblocks §Done #1 (FULL validation reports ≥ 3/3 via M-V64A-VAL-FULL-1).

## Scope (what changed in this sub-DEC)

**Substrate change** (sandbox, outside repo per DEC-V61-198, in `~/Desktop/case_004_nrel_phase_vi_mrf/`):
- `case/constant/triSurface/*.stl` (16 NEW ASCII STL · 50.9 MB total · from harness `freecad_step_to_stl.py` bridge)
- `case/constant/triSurface/*.eMesh` (8 NEW feature-edge meshes · from `surfaceFeatureExtract`)
- `case/constant/triSurface/manifest.json` (NEW · STL ↔ STEP-label mapping)
- `case/constant/extendedFeatureEdgeMesh/*.extendedFeatureEdgeMesh` (8 NEW)
- `case/constant/polyMesh/{points,faces,owner,neighbour,boundary,cellZones,faceZones,pointZones,sets,cellLevel,pointLevel,surfaceIndex,level0Edge}` (NEW · 919,762 cells · cellZone `rotating_cellzone` 300,057 cells)
- `case/system/blockMeshDict` (NEW · 70 LOC)
- `case/system/snappyHexMeshDict` (NEW · 200 LOC)
- `case/system/meshQualityDict` (NEW · 60 LOC)
- `case/system/surfaceFeatureExtractDict` (NEW · 80 LOC)
- `case/system/controlDict` (NEW · 25 LOC)
- `case/system/fvSchemes` (NEW · 20 LOC)
- `case/system/fvSolution` (NEW · 25 LOC)

**Repo changes** (this sub-DEC commit chain):
- `.planning/case_profiles/case_004_v64_mesh_gen_v2_log_2026-05-15.md` (NEW · full mesh-gen run log + dict snapshots + reproduce instructions + advisor findings)
- `.planning/decisions/2026-05-15_v64_sub_mesh_gen_v2.md` (NEW · this file)

**Out of scope** (per dispatch contract):
- No solver run (`simpleFoam` execution is M-V64A-VAL-FULL-1 scope)
- No validation report (M-V64A-VAL-FULL-1 scope)
- No advisor source change (`ui/backend/services/...` untouched; 07b_audit_mrf case-local script untouched too)
- No ARC-GOAL.md update (main session reconciles · race-safe vs B55)
- No Notion sync (main session session-end batch)
- No Codex review (case substrate + docs · no security boundary per v2.3 1-sync-trigger)
- No Kogami review (opt-in only per V133)
- No advisor parser fix for F-NEW-1 / F-NEW-2 (recorded as V-row candidates for V101+ landing · separate sub-DEC scope)

## Mesh stats (summary · full inventory in run log §2-§3)

- **Cells**: 919,762 (background 512,302 · cellZone interior 300,057 · refinement levels 1-5 distributed)
- **Faces**: 2,853,333 · **Points**: 1,016,949
- **Patches**: 11 (rotor_blade_A, rotor_blade_B, hub_spinner_1, hub_spinner_2, nacelle_body, nacelle_service_cover, tower_body, yaw_sensor_shim, bg_inlet, bg_outlet, bg_tunnel_walls)
- **cellZones**: 1 (`rotating_cellzone` · 300,057 cells · 32.6 % of total · matches `MRFProperties::MRF1::cellZone` reference)
- **faceZones**: 1 (`rotating_cellzone_faces` · 19,710 faces · closed singly connected · MRF interface)
- **checkMesh verdict**: PASS with 1 quality flag (max skewness 6.99 > target 4.0 on 41/2.85M faces = 0.0014 %). All other checks PASS (aspect ratio 7.60 < 1000; non-orthogonality max 65.31° < 70°; min volume +267.77 mm³; boundary openness 1.2e-17; face/cell pyramids OK; 1 region OK; all patches singly-connected; faceZone closed-singly-connected).
- **11 illegal faces** from sHM (concave / zero-pyramid) consistent with V10 thin-wall merge pattern on yaw_sensor_shim (0.75 mm) + nacelle_service_cover D1 gap (0.30 mm) — pre-mesh thin_wall_advisor warnings (V23/V30) materialize as expected.

## Pipeline wall time

| step | tool | wall time |
|---|---|---|
| STEP → STL | FreeCAD 1.1 + harness bridge | 6.1 s |
| blockMesh | OF ESI 2312 (Docker) | 1.3 s |
| surfaceFeatureExtract | OF ESI 2312 | 0.4 s |
| snappyHexMesh -overwrite | OF ESI 2312 | 159.8 s |
| foamFormatConvert (binary→ASCII) | OF ESI 2312 | 6.6 s |
| checkMesh | OF ESI 2312 | 2.1 s |
| 07b_audit_mrf (case-local) | Python | < 1 s |
| **Total wall time** | | **≈ 3 min** |

This is the first executable mesh gen run on case_004 in the V63/V64 arc. Per V63-A B49 §4: prior PARTIAL estimated 15-30 min mesh + simpleFoam on macOS; the mesh-only fraction lands at 3 min via Docker OpenFOAM (no local OF install required).

## Cell budget vs plan-file target

Plan-file V64-A §North Star: NREL Phase VI typical mesh budget **5-10 M cells**. Achieved: **919,762** (under target by 5×).

**Trade-off**: v2 establishes the executable pipeline + cellZone hook + advisor field-validation. Refinement levels tuned conservatively for a first-pass functional mesh; achieving 5-10 M is a one-knob tune (rotor blade `(4,5)→(5,6)`; rotating cellzone region `2→3`; `addLayers true` for boundary-layer prism). Plan-file path: bundle the bump into M-V64A-VAL-FULL-1 grid-convergence study (charter §Done #3 "≥ 1 case 在 ≥2 mesh refinement levels h/2 + h/4 跑出 monotonic convergence trend") — the bumped mesh is then the second point of the h-refinement study.

## NET-NEW V-row candidates (out of scope for landing this session)

Two distinct-signature findings emerge from the **first time advisor was field-tested against actual OpenFOAM emission**:

### F-NEW-1 · advisor cellZones parser expects literal `List<label>` tag

`07b_audit_mrf.py::parse_cellzones` regex expects `cellLabels List<label> N (...)` ; OF ESI 2312 emits `cellLabels N (...)` (type tag omitted when inferable). Returns false-negative `cellzones_present = []` despite cellZone present in polyMesh. Candidate for V101+ sediment as a distinct V-row class (advisor-parser format-tolerance gap · OF ESI 2312 cellZones emission · first industrial field-test against real OF output).

### F-NEW-2 · advisor patch-name expects parts_manifest literal (no fragment-split tolerance)

`parts_manifest.yaml` declares `hub_spinner` (one part); STEP extraction produced 2 fragments (`hub_spinner` + `hub_spinner001`); sHM emitted patches `hub_spinner_1` + `hub_spinner_2`. Advisor's `expected_walls` doesn't tolerate the suffix split → false-negative WARN. Candidate for V101+ sediment as distinct V-row class (surface-name-to-patch-name canonicalization on multi-fragment STEP bodies).

Both findings preserve mesh validity (the polyMesh itself is correct · verified by checkMesh + raw inspection). Both findings are advisor parser/naming layer concerns, properly out of scope for this mesh-gen sub-DEC.

## V63-A carry-over closure

V64-A charter §Done #5 ledger:

| carry-over | status before this session | status after this session | scope |
|---|---|---|---|
| **#2 first half** "case_004 mesh gen v2 · unblock solver execution" | open · DEFERRED in B49 PARTIAL §4 | **CLOSED** · polyMesh + cellZone validated; 07b advisor no longer exits on precondition gate; M-V64A-VAL-FULL-1 unblocked | this sub-DEC |
| #2 second half "simpleFoam convergence + NREL UAE Sequence S delta" | open | unchanged · M-V64A-VAL-FULL-1 scope | downstream |
| #1, #3-#8 | open | unchanged | B55 (case_006) + other Tier-1 sub-DECs |

Pushes Done #5 from 0/8 → 1/8. If B55 (case_006 substrate v2) ratifies in same B52-reconcile chain, Done #5 → ≥ 2/8.

## v2.3 governance compliance

- **DEC scope**: sub-DEC (single shared code path `case_*/system/*` per V64-A charter §Cross-cutting #2) · 6-field frontmatter satisfied (decision_id / status / parent_dec / phase / notion_sync_status / authored_by + authored_at + confidence + autonomous_governance · 9 fields filled, 6 required)
- **Codex review**: skipped (v2.3 1-sync-trigger does NOT fire — case substrate + docs only; no auth/signing/security-boundary touch)
- **Kogami review**: skipped (V133 opt-in only · user did not invoke)
- **Notion sync**: `pending` — main session session-end batch (per v2.3 round-1 rule: only Accepted DECs sync; this DEC is Accepted so qualifies; ID `DEC-V64-A-sub-M-V64A-MESH-GEN-V2` queued)
- **Counter**: `autonomous_governance: true` · +1 to V64-A counter (pure telemetry per V133)
- **Spike-class check**: ≈ 320 LOC of new dict + 350 LOC run log + this sub-DEC ≈ 670+ LOC total — far exceeds spike-class envelope (≤ 30 LOC); sub-DEC required (this file)
- **Surface-scan**: clean (no new `routes/` or `pages/`; substrate sandbox + 2 in-repo docs only) · per V61-088 surface-scan is optional in this commit shape
- **Round cap N/A**: no Codex review chain initiated
- **Race condition with B55**: 0 file conflicts predicted (B54 touches `.planning/case_profiles/case_004_v64_mesh_gen_v2_log_*.md` + `.planning/decisions/2026-05-15_v64_sub_mesh_gen_v2.md` + sandbox-only case_004; B55 touches case_006 substrate + sub-DEC `2026-05-15_v64_sub_case_006_substrate_v2.md`). Push contention resolved via `git pull --rebase` per dispatch.
- **ARC-GOAL.md**: not touched (main session reconciles · race-safe vs B55)

## Confidence

**med**. High confidence on:
- Mesh actually generated · verified by independent OF `checkMesh` PASS-with-1-quality-flag + `polyMesh/{cellZones, faceZones, boundary}` raw inspection + 7-tool wall-time inventory
- cellZone `rotating_cellzone` extracted with correct cell count (300,057 · 32.6% of total · interior of cylindrical zone marker STL · matches `MRFProperties::MRF1::cellZone` reference byte-stably)
- 4Q gate PASS (Q1 LLM offline · Q2 artifacts · Q3 TrustGate · Q4 advisory-only) · 6th empirical V63-A+V64-A confirmation
- Pipeline wall-time concrete (3 min total · Docker OF · no local install required)
- 11 illegal faces traced to V10 thin-wall merge pattern (consistent with pre-mesh thin_wall_advisor warnings on yaw_sensor_shim 0.75 mm + D1 0.30 mm gap)

Medium confidence on:
- **Cell budget under plan target**. 919k vs 5-10 M plan-file target — operable for first-pass simpleFoam MRF but undersized for proper boundary-layer-resolved rotor torque. Tuning iteration well-scoped (one knob bump rotor refinement (4,5)→(5,6) + cellzone region 2→3 + addLayers); deferred to M-V64A-VAL-FULL-1 grid-convergence study scope.
- **Max skewness 6.99 on 41 faces**. Above target 4.0 internal; concentrated at refinement-level 4→5 boundary on rotor TE; OF's relaxed unrelaxed-non-orthogonality 65° + skewness handler will accept this for simpleFoam, but high-skew faces are known wake-region error sources. v3 fix path: `meshQualityDict.maxInternalSkewness 4 → 8 (relaxed)` to formally accept OR rotor TE surfaceMesh refinement.
- **F-NEW-1 / F-NEW-2 advisor findings**. Recorded as V-row candidates; need V101+ corpus extension to fix. The advisor's false-negatives don't impair mesh validity — they're documentation gaps in the advisor layer.

These medium-confidence dimensions are scoped forward (cell budget tune, skewness fix, advisor-parser fix). The **mesh gen v2 itself** (cellZone extraction + executable pipeline + V63-A carry-over closure) is data-grounded.

---

**End of DEC-V64-A-sub-M-V64A-MESH-GEN-V2.** V63-A carry-over #2 first half **CLOSED**. M-V64A-VAL-FULL-1 (solver execution + NREL UAE Sequence S comparison) is **unblocked**. Companion run log at `.planning/case_profiles/case_004_v64_mesh_gen_v2_log_2026-05-15.md`.
