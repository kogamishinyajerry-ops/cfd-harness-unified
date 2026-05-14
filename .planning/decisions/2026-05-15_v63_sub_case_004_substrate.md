---
decision_id: DEC-V63-A-sub-M-CASE-004-SUBSTRATE
title: case_004 NREL Phase VI MRF input-manifest substrate extension · thin_wall + A2-v2 inputs · V-row capture 1/9 → 5/9 firm · Done dim #6 cross-case clause 1 → 2
status: Accepted
parent_dec: DEC-V63-A-charter
phase: V63-A Tier 2 supplement · M-CASE-004-SUBSTRATE (cross-case extension #2 · driven by Done dim #6 "≥3/9 on ≥3 cases" cross-case clause · mirror of B42 case_006 substrate)
notion_sync_status: pending
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope:
3 substrate-side input files synthesized under `case_004/inputs/` + 1
verification runner under `scripts/v63_case_004_substrate/` + this DEC +
the accompanying retro. Substrate edits limited to additive files; no
case_dir / STEP / STL / existing manifest changes.

## Goal

Advance V63-A Done dim #6 ("≥5/9 on ≥1 canonical case + **≥3/9 on ≥3
cases**") cross-case clause from `1 case ≥3/9` (case_006 post-B42) to
`2 cases ≥3/9` (case_006 + case_004). Mirror the B42 case_006 substrate
playbook on case_004 by landing the same three substrate-side input
artifacts that `thin_wall_advisor` (V10) and A2-v2
`virtual_interface_detector` (V20 + 7 cross-case V-rows) need to dispatch
end-to-end on case_004. Target reached: **5 / 9 firm (V22, V23, V29,
V30, D1)** — exceeds the ≥3/9 floor.

## Scope

Three new input files under `~/Desktop/case_004_nrel_phase_vi_mrf/inputs/`:

1. `thin_wall_inputs.yaml` (≈ 50 LOC incl. derivation comment) —
   `patches[]` (5 entries: nacelle_body, nacelle_service_cover,
   yaw_sensor_shim, hub_spinner, rotor_blade_trailing_edge_sliver) +
   `refinement_levels` (5 mappings) + `background_cell_size: 20.0` +
   `min_cells_per_thickness: 2`.
2. `interface_bodies.json` (~140 LOC) — BodyGeometry dicts for
   `nacelle_body` + `nacelle_service_cover` with 6 axis-aligned face
   entries each, reconstructed from `_freecad_extract.json` bbox extremes.
3. `interface_specs.json` (~24 LOC) — single InterfaceSpec
   `nacelle_d1_interface` (mode=shared, body_a=nacelle_body,
   body_b=nacelle_service_cover) targeting the documented D1 0.30 mm gap.

One verification runner under repo `scripts/v63_case_004_substrate/`:

- `run_extended.py` — mirrors the B42
  `scripts/v63_case_006_substrate/run_extended.py` runner. Imports
  case_004 baseline from `scripts.stack_track_c_case_ext_1.build_inputs`
  rather than case_006's `stack_track_c_session_3_rerun.build_inputs`;
  loaders for the 3 new input files reconstruct
  `virtual_interface_detector.{BodyGeometry,FaceGeometry,InterfaceSpec}`
  and `thin_wall_advisor.PatchGeometry` dataclasses for the dispatch.

Out of scope (explicitly per dispatch):

- `assemble_stack` source edits
- advisor / catalog source edits
- case_dir CAD / STL / existing manifest edits
- Notion sync (v2.3 round-1 loosen — only Accepted DECs sync at session-end)
- Codex review (substrate YAML/JSON additions are not auth / signing /
  operator endpoint; not a v2.2 1-sync-trigger)
- Kogami invocation (v2.3 opt-in; not requested)
- ARC-GOAL.md edits (main session reconciles to avoid parallel B44/B45
  rebase contention)

## Synthesis trace

The 3 input files are *derived*, not authored from scratch. Provenance
chain for every numeric value:

| input file | numeric values | source |
|---|---|---|
| `thin_wall_inputs.yaml` patches.nacelle_body | `[1800.0, 900.0, 820.0]` | `_freecad_extract.json::bodies['nacelle_body'].bbox_dims_mm` verbatim |
| ditto nacelle_service_cover | `[620.0, 35.0, 320.0]` | `_freecad_extract.json::bodies['nacelle_service_cover'].bbox_dims_mm` verbatim |
| ditto yaw_sensor_shim | `[320.0, 0.75, 220.0]` | `_freecad_extract.json::bodies['yaw_sensor_shim'].bbox_dims_mm` verbatim; D8 thin shim per `defect_manifest.yaml::D8.measurement.claimed_thickness_mm: 0.75` |
| ditto hub_spinner | `[820.0, 720.0, 720.0]` | `_freecad_extract.json::bodies['hub_spinner'].bbox_dims_mm` verbatim |
| ditto rotor_blade_trailing_edge_sliver | `[0.50, 20.0, 358.0]` | derived from NREL Phase VI S809 airfoil tip station (chord_tip ≈ 358 mm, blunt-TE ≈ 0.50 mm per NREL/TP-500-29955 manufacturing-drawing convention, last spanwise station ≈ 20 mm) — informed estimate; advisor result is CRITICAL substrate hint for V62-A v2 mesh sub-session |
| `thin_wall_inputs.yaml` refinement_levels | `[3,4]/[1,2]/[4,5]` | follows case_006 background-vs-aero-surface convention; aero (hub_spinner) at [4,5], semi-aero (nacelle bodies, TE sliver) at [3,4], aux instrumentation (yaw_sensor_shim) at [1,2] |
| `thin_wall_inputs.yaml` background_cell_size | `20.0` | matches case_006; effective cell at level-5 = 20/2^5 = 0.625 mm targets chord/1100 wing-resolution for NREL Phase VI rotor force monitors |
| `interface_bodies.json` nacelle_body faces | 6 axis-aligned faces | reconstructed from `_freecad_extract.json::bodies['nacelle_body'].{bbox_min_mm, bbox_max_mm}`; area = cross-product of bbox dims (geometrically exact for axis-aligned hull) |
| ditto nacelle_service_cover faces | 6 axis-aligned faces | reconstructed from `_freecad_extract.json::bodies['nacelle_service_cover'].{bbox_min_mm, bbox_max_mm}` |
| `interface_specs.json` nacelle_d1_interface | gap 0.30 mm | `_freecad_extract.json::distances['nacelle_body__nacelle_service_cover'] = 0.30000000000001137` verbatim; matches `defect_manifest.yaml::D1.measurement.claimed_gap_mm: 0.30` verbatim; geometric verification: nacelle_body +Y face at y=450.0 vs nacelle_service_cover -Y face at y=450.3, \|Δy\| = 0.30 mm ✓ |

## Before / After V-row capture matrix

| failure mode | pre-substrate | post-substrate | mechanism |
|---|---|---|---|
| V22 A2-v2 rotating-machinery field-validation | partial (referenced in case profile) | **YES ✓ firm** | virtual_interface_detector fires on nacelle_d1_interface; A2-v2 returns gap=0.30 → classifier critical |
| V23 thin_wall_advisor rotating-machinery aux | partial (referenced in case profile) | **YES ✓ firm** | thin_wall_advisor fires on yaw_sensor_shim 0.75 mm → CRITICAL |
| V24 FreeCAD sentinel-bbox + compound fragment | NO | NO | out-of-stack (substrate hides datum frames; `_freecad_extract.py` is the upstream catcher) |
| V29 BC-name catalog | YES ✓ firm | YES ✓ firm | bc_type_name_validity_advisor (3 findings, unchanged from B43 baseline) |
| V30 thin_wall sliver class | NO ← input-stranded | **YES ✓ firm** | thin_wall_advisor fires on yaw_sensor_shim 0.75 mm + rotor_blade_trailing_edge_sliver 0.50 mm → both CRITICAL |
| V94 face-label loss (D11 coverage) | NO | NO | out-of-stack (D11 stl_face_label_validator needs `shm_stl_face_normals`; case_004 has no STL yet) |
| D1 sub-mm nacelle gap | partial (defect manifest only) | **YES ✓ firm** | A2-v2 inter_face_gap_mm=0.30; classifier should_have_been_shared_with_unintended_gap(threshold=1.0) flags critical |
| D8 thin shim 0.75 mm | partial (defect manifest only) | **YES ✓ firm (covered by V30 mechanism row)** | thin_wall_advisor catches yaw_sensor_shim CRITICAL |
| MRF-class hypotheses | NO | NO | out-of-stack (07b_audit_mrf is case-local; not stack-registered until A6/A7 extraction) |

**Catch rate: 1 / 9 firm (V29 only) → 5 / 9 firm (V22 V23 V29 V30 D1 + D8 shares V30 row). ≥ 3 / 9 target MET.**

**Done dim #6 cross-case clause progress: 1 case ≥3/9 (case_006 post-B42) → 2 cases ≥3/9 (case_006 + case_004); ≥3-case distance = 1 remaining.**

## Verification evidence

`assemble_stack(...)` pre/post on case_004 (path b, LLM-keys-popped):

| metric | pre (`stack_track_c_case_ext_1/stack_report_python.json`) | post (`v63_case_004_substrate/stack_report_python_extended.json`) | delta |
|---|---|---|---|
| advisor_count | 4 | 6 | +2 (`thin_wall_advisor`, `virtual_interface_detector`) |
| finding_count | 3 | 6 | +3 |
| critical_count | 0 | 3 | +3 |
| warning_count | 3 | 3 | 0 |
| failed_advisor_count | 0 | 0 | 0 |
| evidence_refs (V-row union) | 6 | 14 | +8 (V10, V22, V25, V33, V36, V42, V43, V50) |
| env_keys_present (V130 Q1) | all false | all false | invariant ✓ |

New findings (delta = 3):

```
[virtual_interface_detector] critical · d1_unintended_gap · nacelle_d1_interface · V22 V25 V33 V36 V42 V43 V50
[thin_wall_advisor]          critical · thin_wall_at_risk  · yaw_sensor_shim     · V10
[thin_wall_advisor]          critical · thin_wall_at_risk  · rotor_blade_trailing_edge_sliver · V10
```

Reports serialized to:

- `scripts/stack_track_c_case_ext_1/stack_report_python.json` (pre · unchanged from B43 land)
- `scripts/v63_case_004_substrate/stack_report_python_extended.json` (post · new)

## Backward-compat

- `scripts/stack_track_c_case_ext_1/run_python_path.py` re-runs unchanged:
  still 4 advisors / 3 findings / 6 V-rows. `assemble_stack`'s keyword-only-
  with-`None`-default signature means the old call site silently skips the
  new dispatches.
- `scripts/stack_track_c_case_ext_1/run_http_path.py` untouched; HTTP-path
  auto-discovery probes `case_dir/` root, not `case_dir/inputs/`, so path-a
  remains stranded until a follow-up sub-DEC canonicalizes the loader's
  probe locations (carry-over from case_006 sub-DEC §10 #3).
- `case/` directory contents untouched (OpenFOAM run artifacts intact).
- `parts_manifest.yaml`, `defect_manifest.yaml`, `cad_codex_v1.step` —
  unchanged.
- D11 stl_face_label_validator gate (DEC-V63-A-sub-D11) unaffected — its
  dispatch precondition reads `shm_stl_face_normals` / `parts_manifest`
  face_labels / `shm_dict` refinementSurfaces; the new YAML/JSON inputs
  feed `thin_wall_advisor` + `virtual_interface_detector` exclusively.

## Surface scan

```
$ ls ~/Desktop/case_004_nrel_phase_vi_mrf/inputs/ | grep -E "thin_wall_inputs|interface_bodies|interface_specs"
(empty — none exist pre-land)
$ ls scripts/v63_case_004_substrate/
(directory did not exist pre-land)
```

`Surface-scan: clean` on all 3 commits.

## v2.3 compliance

- **Scope class**: sub-DEC (3 input files + 1 runner + 1 retro + 1 DEC =
  6 files; not crossing ≥3 shared code paths; no schema break; no security
  boundary). Below charter threshold; full DEC frontmatter limited to the
  6 required fields above.
- **Cadence floor (30)**: not triggered — documented cross-case extension,
  not a new direction; net new LOC under 350 across all files.
- **Codex review**: not required. 1-sync-trigger is auth/signing/operator-
  endpoint only; substrate YAML/JSON additions do not qualify. Round
  count: 0.
- **Kogami invocation**: not requested (v2.3 opt-in; substrate work is
  not a strategic-narrative event).
- **Notion sync**: pending (per v2.3 round-1 loosen, only Status=Accepted
  DECs sync at session-end; this DEC moves Proposed → Accepted within the
  same dispatch so will sync in next session-end batch if the user
  triggers `notion-sync-cfd-harness`).
- **4Q gate**: all four pillars confirmed in retro §9 (LLM-offline ✓ /
  artifacts emitted ✓ / TrustGate explanation ✓ / AI advisory-only ✓).
- **Confidence**: med. Bbox values are FreeCAD-verbatim for 4/5 thin-wall
  patches; the 5th (rotor_blade_trailing_edge_sliver) is an informed
  estimate that advisor flags CRITICAL — the V63-A v2 mesh sub-session
  will refine this number when the trailing-edge boundary layer template
  is authored. Interface body face reconstruction is axis-aligned box
  from bbox extremes (geometrically exact for the nacelle bodies since
  both are simplified hulls). D1 gap 0.30 mm matches
  `_freecad_extract.json::distances` verbatim + defect_manifest verbatim.
  Stack diff matches the case_006 B42 closure pattern (V30 + D1
  input-stranded → firm).

## Open follow-ups (deferred · not blocking Accepted)

1. **ARC-GOAL.md Done-dim-#6 update** — main session reconciles between
   this land and parallel B44 (whichever new case is dispatched).
   Recommended language: `2 / ≥3 cases ≥3/9 covered (case_006 + case_004);
   1 remaining`.
2. **rotor_blade_trailing_edge_sliver bbox refinement** — current 0.50 mm
   estimate is a substrate hint, not measured. V62-A v2 mesh sub-session
   should re-emit `_freecad_extract.json` after a finer-tessellation STEP
   export and replace this entry with a measured value. Until then the
   CRITICAL finding is a "look here" marker, not a quantitative claim.
3. **HTTP-path auto-discovery (carry-over from case_006 sub-DEC §10 #3)** —
   `scripts/v63_case_004_substrate/run_extended.py` uses path b only;
   HTTP path-a route would probe `case_dir/` root for
   `interface_bodies.json` + `manifest.json`, missing the
   `case_dir/inputs/` location entirely. A future follow-up sub-DEC to
   canonicalize the loader's probe locations would close both case_004 +
   case_006 path-a stranding in one motion.
4. **MRF-class advisor extraction** — `scripts/07b_audit_mrf.py` is
   case-local (case_004 only); after 1-2 more rotating cases share the
   pattern, A6 + A7 extraction is the right move per case_004 profile.
5. **D11 stl_face_label_validator land on case_004** — case_004 has no
   STL yet (v2 mesh sub-session scope); V94 coverage deferred.

## Commits

1. `feat(v63-case004): synthesize thin_wall_inputs + interface_bodies + interface_specs from _freecad_extract.json + defect_manifest` — adds the 3 input files under `case_004/inputs/` + the verification runner under `scripts/v63_case_004_substrate/`.
2. `docs(v63-case004): retro substrate extension · V-row capture 1/9 → 5/9 firm verified` — adds `.planning/retrospectives/2026-05-15_case_004_substrate_extension.md`.
3. `docs(v63-case004): sub-DEC DEC-V63-A-sub-M-CASE-004-SUBSTRATE Accepted` — this file.

Each commit carries `confidence: med` and `Surface-scan: clean` trailers.
