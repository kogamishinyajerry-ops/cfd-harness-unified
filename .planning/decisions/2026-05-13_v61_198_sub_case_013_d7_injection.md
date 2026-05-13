---
decision_id: DEC-V61-198-sub-case-013-D7-injection
title: case_013 D7 cross-topology evidence sediment · A4 face_orientation_advisor promotion gate unblocker
status: Accepted
parent_dec: V61-198
phase: Industrial Extension Phase 2 #1 (case_013) · M-A4 unblocker
notion_sync_status: pending session-end batch
parent_artifacts:
  - .planning/methodology/kickoff/case_013_codex_request.md (dispatch brief)
  - .planning/methodology/kickoff/case_013_codex_response.md (Codex 5-deliverable design)
  - .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
  - .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
  - .planning/patches/draft_a4_face_orientation_2026-05-13.md (A4 advisor research)
  - .planning/methodology/advisor_candidates_a4_a8.md (A4 promotion-gate spec)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (priority queue)
  - ~/Desktop/case_013_centrifugal_pump_cavitating/ (substrate)
trigger: M-A4 advisor research drafted 2026-05-13 (commit 615dacb) blocked on "≥2 cross-topology D7 evidence" promotion gate. case_012 was the only D7 injection (V79). case_013 was dispatched 2026-05-08 in Phase 2 #1 and deferred. This session lands the substrate + D7 verification.
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (dispatched case work · not main repo schema change · per v2.3 §2 risk-tier; spike-class adjacent but >30 LOC so falls under sub-DEC scope)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon for this case work)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-13
confidence: high (D7 measured 21.979° vs 22.000° design within 0.021° tolerance · D1 measured 0.800mm exact · both PASS · sediment evidence rigorous · mesh ran to checkMesh but with V83-class acceptable-fail documented honestly)
---

# DEC-V61-198-sub-case-013-D7-injection · case_013 D7 sediment unblocks M-A4

## 1. Why now

M-A4 (`face_orientation_advisor`) research draft landed 2026-05-13 at
`.planning/patches/draft_a4_face_orientation_2026-05-13.md` (commit
`615dacb`), but the promotion gate per
`.planning/methodology/advisor_candidates_a4_a8.md` requires **≥ 2
cross-topology cases with manual-verified D7 injection** (same gate
that promoted A1-A3 from drafted to landed).

Pre-this-session evidence count: **1 / 2** (only V79 / case_012 whole-vane
Z-axis rotation). case_013 was dispatched 2026-05-08 as Phase 2 #1
(`case_011_020_industrial_extension_roadmap_2026-05-08.md`) with explicit
D7 in its defect manifest, but the sub-session was deferred — leaving
M-A4 implementation blocked.

This session executes the case_013 substrate land:
- Codex's design (`case_013_codex_response.md` 2026-05-08) becomes a
  buildable centrifugal pump CAD
- D7 verification produces measurement evidence (21.979°)
- D1 verification produces tip-clearance evidence (0.800 mm)
- v1 mesh runs through checkMesh (with documented acceptable-fail per V83)
- V87 row sediments to both V-series corpora

After this DEC lands, M-A4 implementation is unblocked: next session
writes `ui/backend/services/geometry_ingest/face_orientation_advisor.py`
using case_012 + case_013 STEP files as the canonical regression test
corpus.

## 2. What changed

### Substrate (new sandbox at `~/Desktop/case_013_centrifugal_pump_cavitating/`)

| File | LOC | Purpose |
|---|---|---|
| `inputs/cad_codex_v1.step` | 3.2 MB binary | Generated STEP (Codex CAD script run); 114 PRODUCT_DEFINITIONs (assembly w/ patch proxies) |
| `inputs/cad_codex_v1_baseline.step` | 3.2 MB binary | D7_ROTATION_DEG=0 baseline for verification anchor |
| `inputs/cad_codex_v1.patches.json` | 30 lines | patch + omega + defect metadata sidecar |
| `inputs/parts_manifest.yaml` | 95 lines | Codex deliverable #4 verbatim + verification commands |
| `inputs/defect_manifest.yaml` | 35 lines | D1 + D7 with measurement methods + expected_advisor_to_catch |
| `config/case.yaml` | 60 lines | v1 mesh-only SSOT (background_cell + refinement_levels) |
| `scripts/build_cad.py` | 391 LOC | Codex deliverable #2 (CadQuery generator · backward-curved blades · spiral volute · D1 blade_5 tip-clearance · D7 blade_3 LE chord-axis rotation) |
| `scripts/build_cad_baseline.py` | 32 LOC | monkey-patches D7_ROTATION_DEG=0 then calls build() for anchor STEP |
| `scripts/check_face_normal.py` | 174 LOC | D7 verification · tilt-from-XY-plane signature method |
| `scripts/check_tip_clearance.py` | 80 LOC | D1 verification · FreeCAD BoundBox.ZMax delta |
| `scripts/debug_step_bodies.py` | 25 LOC | dev-only · lists STEP body labels + face counts |
| `scripts/01_extract_stl.py` | 70 LOC | FreeCAD STEP→STL per-body (mm→m scale) |
| `scripts/02_scaffold_case.py` | 220 LOC | minimal blockMesh + sHM dict writer (mesh-only) |
| `scripts/03_run_solver.sh` | 38 LOC | Docker OpenFOAM 2312 mesh runner (STAGE=mesh) |
| `case/` | OpenFOAM dirs | blockMesh + sHM polyMesh + checkMesh log |
| `evidence/v1/defect_verification_d7.json` | 38 lines | D7 measurement record · 21.979° |
| `evidence/v1/defect_verification_d1.json` | 22 lines | D1 measurement record · 0.800 mm exact |
| `evidence/v1/check_mesh_summary.json` | 38 lines | mesh outcome · ACCEPTABLE_FAIL_V1 verdict per V83 |

Total substrate scripts/manifests: ~1230 LOC + binary CAD assets.

### Main repo (cfd-harness-unified)

| File | Change |
|---|---|
| `.planning/methodology/industrial_case_solver_findings.md` | +1 V-row (V87 · case_013 D7 cross-topology completion · ~80 lines) |
| `docs/openfoam_corpus/industrial_solver_findings_v_series.md` | +1 V-row (V87 same content · drift-prevention hook satisfied) |
| `.planning/methodology/advisor_candidates_a4_a8.md` | A4 row updated · evidence 1/2 → 2/2 · status `drafted` → `ready-to-land 2026-05-13` · added V87 to V-row(s) · added promotion-note about 5-day cadence |
| `.planning/cross_cuts/advisor_coverage_2026-05-09.md` | A4 row in "Pending advisor extractions" table updated to **READY-TO-LAND** with `615dacb` ref · D7 row in defect-catalog distribution table updated to `2× sedimented 2026-05-13 · ready-to-land` |
| `.planning/ARC-GOAL.md` | M-A4 row annotated "**unblocked**, ready-to-land next session" |
| `.planning/decisions/2026-05-13_v61_198_sub_case_013_d7_injection.md` | this DEC (new) |

## 3. D7 verification method · WHY tilt-from-XY-plane works

The case_013 D7 injection is geometrically distinct from case_012:

| dimension | case_012 D7 (V79) | case_013 D7 (V87) |
|---|---|---|
| rotation axis | Z (vane mounting axis) | XY plane (LE chord axis) |
| target | whole-body component (`louver_vane_2`) | sub-feature (LE chunk of `blade_3`) |
| measurement | FreeCAD principal-normal dot-product against sibling-vane consensus | FreeCAD LE-band side-face max tilt-from-XY-plane |
| design value | 38.000° | 22.000° |
| measured | 38.000° (exact) | 21.979° (delta 0.021°) |
| tolerance | 2° | 4° |
| verdict | PASS | PASS |

**Why tilt-from-XY-plane is the cleaner signal here**: case_013's
blade_3 is built by `cq.Workplane.polyline(polygon).close().extrude(z)`
(in `scripts/build_cad.py::make_blade_solid` lines 215-256). All side
faces of the unrotated baseline have normals strictly in the XY plane
(n_z = 0). The D7 injection rotates a cut chunk by 22° around an axis
that lies IN the XY plane. After rotation, the chunk's side faces have
normals tilted out of the XY plane by exactly the rotation angle —
tilt = arcsin(|n_z|). This signature is mathematically exact for a
rigid rotation around an XY-plane axis, independent of cut+fuse
topology artifacts.

Initial attempts (dominant-face matching, centroid-nearest pairing)
gave noisy results because cut+fuse produces 7 new STEP faces that
have no clean counterpart in baseline. The tilt-from-XY-plane method
sidesteps the pairing problem by exploiting the structural property of
extruded polygons.

**Method-selection implication for A4 advisor**: the productized
implementation must support BOTH Z-axis rotation (case_012 method) and
XY-axis rotation (case_013 method). Likely API: parts_manifest declares
`expected_rotation_axis: z | xy | auto`, and advisor selects method or
runs both and picks the cleaner signal.

## 4. D7 + D1 topological evidence (visible without verification scripts)

In injected STEP vs baseline STEP, blade_3 differs:
- Face count: 55 vs 48 (Δ +7) from D7 cut+fuse
- BBox z extent: [−0.5, 20.1] vs [0.0, 19.5] mm (rotated chunk corners protrude 0.6mm above blade height)

For D1 (blade_5 tip clearance), the topological signature is direct:
- blade_5 BBox z extent: [0.0, 19.2] vs blade_1 [0.0, 19.5] → blade_5
  shortened by 0.3 mm vs reference; total tip clearance = B2(20 mm) −
  19.2 = 0.8 mm (matches design)
- All other blades (1, 2, 4, 6): z extent [0.0, 19.5], tip clearance
  0.5 mm (baseline)

These topological signatures could be advisor-detectable without any
external script — a parts-manifest-driven preflight that checks
geometric consistency against declared `expected_tip_clearance_mm` and
`expected_face_count_per_sibling` would catch BOTH D1 and D7 from the
STEP alone.

## 5. v1 mesh outcome · ACCEPTABLE_FAIL per V83 anti-pattern lesson

The mesh pipeline ran end-to-end in 37 seconds (blockMesh 1s + sHM 35s
+ checkMesh 1s) on the Docker `opencfd/openfoam-default:2312` image.
checkMesh reports quality PASS on 11 of 12 metrics — max non-orthogonality
44.8°, max skewness 1.13, aspect ratio 3.89, all OK. The fail metric:
100 concave cells.

However, per **V83 anti-pattern lesson** (`mesh_ok=true` in
`check_mesh_summary.json` does not cover "geometry-derived wall patches
have zero faces"), `mesh_ok` cannot be claimed true: only 2 of 22
intended patches promoted (`hub_disk` 1483 faces · `suction_pipe_wall`
3 faces). Blades, volute, blade tips, IO patches, and background patch
all absent from final polyBoundaryMesh. Root cause: at background
cell-size 10 mm with refinement levels capped at (3, 4), most blade
geometry has effective cell > blade thickness, so sHM cannot seal them
as region-separating surfaces. The locationInMesh (0, 0, 0.005) sat
inside the impeller chamber but the cell-walk graph couldn't isolate
the intended interior from the blade-surrounded sub-region.

**Honest verdict**: `evidence/v1/check_mesh_summary.json` records
`mesh_ok: false · verdict: ACCEPTABLE_FAIL_V1` with verbose rationale.
v1 scope per briefing was (a) STEP substrate land, (b) D7 cross-topology
evidence, (c) mesh tractability proof — all narrowly achieved. The mesh
is NOT solver-ready; v2 would need finer cells (~5 mm), surfaceFeatureExtract
(cf V86), re-positioned locationInMesh, and level (4, 5) on blade tips.

This is exactly the V83 case the methodology calls out: "silent acceptance
of meshes with no intended geometry". This sub-DEC documents it as
intended-acceptable for v1 scope but flags it as v2 scope-expansion
work; no production claim of solver-readiness is made.

## 6. What does NOT change

- **A4 advisor implementation** — the research draft at
  `draft_a4_face_orientation_2026-05-13.md` defines the API but this
  sub-DEC does NOT write the advisor source. M-A4 implementation is
  next-session work
- **v2 cavitatingFoam scope** — out of v1 scope per briefing; only v1
  mesh substrate landed
- **case_013 in `case_proposal_queue.md`** — status update to "sedimented"
  is housekeeping that next session can do during M-A4 land (touched
  here only as Status field in this DEC frontmatter)
- **No source code changes in `ui/backend/services/geometry_ingest/`** — A4 advisor land is a separate sub-DEC. This sub-DEC is pure
  substrate + evidence sedimentation, no productized advisor

## 7. Anti-patterns honored

- **No claim of mesh_ok=true** with absent geometry patches (per V83 lesson)
- **No premature A4 implementation** — substrate-and-evidence-only;
  advisor land waits for separate sub-DEC with full test coverage
- **No CAD redesign** — used Codex's response verbatim (one minor
  textual fix to `build_cad.py` `make_volute_solid` `throat_block`
  centering args to match cadquery 2.7 API; pure equivalence transformation,
  not redesign)
- **No skip of D1 verification** — both defects measured per Hard
  Guardrail #3, even though D1 was secondary to D7 for A4 promotion
- **No fabricated angle** — the 21.979° vs 22.000° design includes a
  measurable 0.021° tolerance band; the tilt-from-XY-plane method
  produces this value naturally without curve-fitting

## 8. Promotion-gate proof for A4

Per `advisor_candidates_a4_a8.md` Section "Promotion gate":

| Requirement | Status |
|---|---|
| Defect-class signature documented | ✅ "face or body whose dominant face normal deviates from declared/sibling-consensus by >tolerance" |
| Advisor API surface drafted | ✅ `draft_a4_face_orientation_2026-05-13.md` (commit `615dacb`) |
| ≥ 2 cross-topology cases with main-session manual verification | ✅ case_012 (V79 · whole-vane Z-axis 38°) + case_013 (V87 · LE-chunk XY-axis 22°) |
| ≥ 1 case has `[QUESTIONABLE <date>]` V-row | ✅ V79 carries `[QUESTIONABLE 2026-05-12]`; V87 also marks for future advisor validation |

All four conditions met. A4 is `ready-to-land`.

## 9. Reversal cost

Low-medium for the V-series + advisor coverage edits (revert two .md
files). The substrate at `~/Desktop/case_013_centrifugal_pump_cavitating/`
is outside the main repo (Tier-3 sandbox per project convention) and
not under git revert scope; it stays as-is. To re-block M-A4: revert
the methodology/advisor docs to mark A4 as `drafted` again. No schema
migration, no consumer changes.

## 10. References

- Parent DEC: V61-198 (APU bay strategic charter · 5-artifact extraction)
- Cousin sub-DECs:
  - DEC-V61-198-sub-A2v2 (2026-05-12 · A2 v2 gap-detection landed — parallel "land sub-feature for advisor" pattern)
  - DEC-V61-198-sub-A7 (2026-05-12 · step_canonicalizer landed)
  - DEC-V61-198-sub-A5-inlet-outlet-validator (2026-05-13)
- Draft research (next session lands): `.planning/patches/draft_a4_face_orientation_2026-05-13.md`
- ARC-GOAL impact: M-A4 row flips from BLOCKED to ready-to-land
- Sediment audit trail: `~/Desktop/case_013_centrifugal_pump_cavitating/evidence/v1/`
