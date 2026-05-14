---
decision_id: DEC-V63-A-sub-M-CASE-006-SUBSTRATE
title: case_006 ONERA M6 input-manifest substrate extension · thin_wall + A2-v2 inputs · V-row capture 1/9 → 3/9 firm
status: Accepted
parent_dec: DEC-V63-A-charter
phase: V63-A Tier 2 · M-CASE-006-SUBSTRATE (carry-over #3 · driven by TRACK-3-rerun §V-row truth-capture rate)
notion_sync_status: pending
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope:
3 substrate-side input files synthesized under `case_006/inputs/` + 1
verification runner under `scripts/v63_case_006_substrate/` + this DEC +
the accompanying retro. Substrate edits limited to additive files; no
case_dir / STEP / STL / existing manifest changes.

## Goal

Close V63-A Tier 2 carry-over #3 documented in
`.planning/retrospectives/2026-05-14_stack_track_c_session_3_rerun_case_006.md`
§"V-row truth-capture rate": push case_006's documented-failure-mode
catch rate from 1 / 9 (V29 only, post-D10 LANDED) to ≥ 3 / 9 by adding
the substrate-side input artifacts that `thin_wall_advisor` (V10) and
A2-v2 `virtual_interface_detector` (V20 + 7 cross-case V-rows) need to
dispatch on case_006. Target reached: **3 / 9 firm (V29, V30, D1) + D4
marginal**.

## Scope

Three new input files under `~/Desktop/case_006_onera_m6_transonic/inputs/`:

1. `thin_wall_inputs.yaml` (≈ 60 LOC incl. derivation comment) —
   `patches[]` (5 entries) + `refinement_levels` (5 mappings) +
   `background_cell_size: 20.0` + `min_cells_per_thickness: 2`.
2. `interface_bodies.json` (≈ 120 LOC) — BodyGeometry dicts for
   `root_fairing_pad` + `root_fairing_cover` with 6 face entries each,
   copied verbatim from `evidence/v1/face_geometry.json`.
3. `interface_specs.json` (~20 LOC) — single InterfaceSpec
   `root_fairing_d1_interface` (mode=shared, body_a=pad, body_b=cover)
   targeting the documented D1 0.35 mm gap.

One verification runner under repo `scripts/v63_case_006_substrate/`:

- `run_extended.py` — mirrors the TRACK-3-rerun path-b runner
  (`scripts/stack_track_c_session_3_rerun/run_python_path.py`) and adds
  loaders for the 3 new input files, reconstructing
  `virtual_interface_detector.{BodyGeometry,FaceGeometry,InterfaceSpec}`
  and `thin_wall_advisor.PatchGeometry` dataclasses for the dispatch.

Out of scope (explicitly per dispatch):

- `assemble_stack` source edits
- advisor / catalog source edits
- case_dir CAD / STL / existing manifest edits
- Notion sync (v2.3 round-1 loosen — only Accepted DECs sync at session-end)
- Codex review (substrate YAML/JSON additions are not auth / signing /
  operator endpoint; not a v2.2 sync trigger)
- Kogami invocation (v2.3 opt-in; not requested)
- ARC-GOAL.md edits (main session reconciles to avoid parallel B43
  rebase contention)

## Synthesis trace

The 3 input files are *derived*, not authored from scratch. Provenance
chain for every numeric value:

| input file | numeric values | source |
|---|---|---|
| `thin_wall_inputs.yaml` patches.root_fairing_pad | `[22.0, 16.0, 7.0]` | `face_geometry.json::bodies['root_fairing_pad'].bbox_xyz` verbatim |
| ditto root_fairing_cover | `[22.0, 16.0, 7.0]` | `face_geometry.json::bodies['root_fairing_cover'].bbox_xyz` verbatim |
| ditto tip_cap_sliver | `[0.18, 3.0, 0.45]` | `face_geometry.json::bodies['tip_cap_sliver'].bbox_xyz` verbatim |
| ditto wing_surface_reference | `[826.9, 1196.3, 82.7]` | derived from `parts_manifest.yaml::geometry_reference` (span_mm 1196.3, mac_mm 646.07, taper_ratio 0.562); chord_root = 2·MAC/(1+λ) = 826.9; thickness = 0.10·chord_root = 82.7 (ONERA M6 nominal t/c) |
| ditto tip_cap | `[50.0, 50.0, 8.0]` | derived from chord_tip = chord_root·λ = 464.7; closure planform conservatively ~50 mm; thickness 8 mm (t/c ≈ 0.10 at tip)  — informed estimate; advisor result for this patch is "no risk", correctness invariant to ±50 % bbox |
| `thin_wall_inputs.yaml` refinement_levels | `[4,5]/[3,4]/[1,2]` | mirrors `scripts/stack_track_c_session_3_rerun/build_inputs.py::build_shm_dict::refinementSurfaces` (lines 64-93); the YAML is the dataclass-form mirror |
| `thin_wall_inputs.yaml` background_cell_size | `20.0` | derived: effective cell at level-5 = 20/2^5 = 0.625 mm targets chord/1000 wing-resolution for transonic Cp on MAC 646 mm |
| `interface_bodies.json` root_fairing_pad faces | 6 face dicts | `face_geometry.json::bodies['root_fairing_pad'].faces` verbatim |
| ditto root_fairing_cover faces | 6 face dicts | `face_geometry.json::bodies['root_fairing_cover'].faces` verbatim |
| `interface_specs.json` root_fairing_d1_interface | gap 0.35 mm | `defect_manifest.yaml::defects.D1.measurement.claimed_gap_mm` verbatim; geometric verification: pad +x face at x=91.61 vs cover -x face at x=91.96 (face_geometry.json), |Δx| = 0.35 mm ✓ |

## Before / After V-row capture matrix

| V-row / D-defect | TRACK-3 | TRACK-3-rerun | post-substrate (this) | mechanism |
|---|---|---|---|---|
| V26 Codex CAD off-by-half-width | NO | NO | NO | out-of-stack (Codex protocol) |
| V27 rhoCentralFoam adjustTimeStep | NO | NO | NO | out-of-stack (no fvSchemes advisor) |
| V28 rhoCentralFoam DILU preconditioner | NO | NO | NO | out-of-stack (no matrix-solver advisor) |
| V29 BC-name validity | NO | YES ✓ | YES ✓ | D10 catalog (TRACK-3-rerun) |
| V30 thin_wall 0.18 mm sliver | NO | NO ← input-stranded | **YES ✓** | thin_wall_inputs.yaml lands; advisor fires on tip_cap_sliver |
| V31 Codex defect→advisor mapping | NO | NO | NO | out-of-stack (protocol revision) |
| V32 Tier-1 NASA Glenn HTTP 500 | NO | NO | NO | out-of-stack (infra) |
| D1 root_fairing sub-mm gap | partial | partial ← input-stranded | **YES ✓** | interface_bodies + interface_specs land; A2-v2 returns gap=0.35 → classifier critical |
| D4 tip_cap_sliver 0.18 mm | partial | partial ← input-stranded | **YES ✓ (marginal)** | thin_wall_advisor catches substrate-level failure; canonical geometry_surgery advisor not yet LANDED |

**Catch rate: 1 / 9 firm → 3 / 9 firm + D4 marginal. ≥ 3 / 9 target MET.**

## Verification evidence

`assemble_stack(...)` pre/post on case_006 (path b, LLM-keys-popped):

| metric | pre (TRACK-3-rerun re-run 2026-05-15) | post (substrate-extended) | delta |
|---|---|---|---|
| advisor_count | 6 | 8 | +2 (`thin_wall_advisor`, `virtual_interface_detector`) |
| finding_count | 10 | 12 | +2 |
| critical_count | 10 | 12 | +2 |
| warning_count | 0 | 0 | 0 |
| failed_advisor_count | 0 | 0 | 0 |
| evidence_refs (V-row union) | 12 | 20 | +8 (V10, V22, V25, V33, V36, V42, V43, V50) |
| env_keys_present (V130 Q1) | all false | all false | invariant ✓ |

New findings (delta = 2):

```
[virtual_interface_detector] critical · d1_unintended_gap · root_fairing_d1_interface · V22 V25 V33 V36 V42 V43 V50
[thin_wall_advisor]          critical · thin_wall_at_risk  · tip_cap_sliver           · V10
```

Reports serialized to:

- `scripts/stack_track_c_session_3_rerun/stack_report_python.json` (pre · unchanged)
- `scripts/v63_case_006_substrate/stack_report_python_extended.json` (post · new)

## Backward-compat

- `scripts/stack_track_c_session_3_rerun/run_python_path.py` re-runs
  unchanged: still 6 advisors / 10 findings / 12 V-rows. `assemble_stack`'s
  keyword-only-with-`None`-default signature means the old call site
  silently skips the new dispatches.
- `case/` directory contents untouched (OpenFOAM run artifacts intact).
- `parts_manifest.yaml`, `defect_manifest.yaml`, `cad_codex_v1.step` —
  unchanged.
- D11 stl_face_label_validator gate (DEC-V63-A-sub-D11) unaffected — its
  dispatch precondition reads `shm_stl_face_normals` / `parts_manifest`
  face_labels / `shm_dict` refinementSurfaces; the new YAML/JSON inputs
  feed `thin_wall_advisor` + `virtual_interface_detector` exclusively.

## Surface scan

```
$ ls ~/Desktop/case_006_onera_m6_transonic/inputs/ | grep -E "thin_wall_inputs|interface_bodies|interface_specs"
(empty — none exist)
```

`Surface-scan: clean` on all 3 commits.

## v2.3 compliance

- **Scope class**: sub-DEC (3 input files + 1 runner + 1 retro + 1 DEC =
  6 files; not crossing ≥3 shared code paths; no schema break; no security
  boundary). Below charter threshold; full DEC frontmatter limited to the
  6 required fields above.
- **Cadence floor (30)**: not triggered — this is a documented carry-over,
  not a new direction; net new LOC under 250 across all files.
- **Codex review**: not required. 1-sync-trigger is auth/signing/operator-
  endpoint only; substrate YAML/JSON additions do not qualify. Round
  count: 0.
- **Kogami invocation**: not requested (v2.3 opt-in; substrate work is
  not a strategic-narrative event).
- **Notion sync**: pending (per v2.3 round-1 loosen, only Status=Accepted
  DECs sync at session-end; this DEC moves Proposed → Accepted within the
  same dispatch so will sync in next session-end batch if the user
  triggers `notion-sync-cfd-harness`).
- **4Q gate**: all four pillars confirmed in retro §6 (LLM-offline ✓ /
  artifacts emitted ✓ / TrustGate explanation ✓ / AI advisory-only ✓).
- **Confidence**: med. Wing/tip_cap bbox values are informed estimates
  (correctness preserved because advisor returns "no risk" for both;
  ±50 % bbox would not flip the verdict). All other values are verbatim
  from existing case artifacts. Stack diff matches the TRACK-3-rerro retro's
  predicted closure mode for V30 / D1 input-stranded gaps.

## Open follow-ups (deferred · not blocking Accepted)

1. ARC-GOAL.md Done-dim-#6 update — main session reconciles between this
   land and parallel B43 (M-CASE-EXT-1). Recommended language in retro §7.
2. D4 marginal → firm: requires `geometry_surgery.decimate_to_tier` advisor
   land; out-of-scope for this sub-DEC; tracked as candidate for V63-A
   later Tier 2 slot.
3. `_meta` block convention (leading-underscore key in JSON maps) used in
   `interface_bodies.json` + `interface_specs.json`; project-wide schema
   doc deferred until N≥2 cases use the pattern.

## Commits

1. `feat(v63-case006): synthesize thin_wall_inputs + interface_bodies + interface_specs from evidence/v1/face_geometry.json` — adds the 3 input files under `case_006/inputs/` + the verification runner under `scripts/v63_case_006_substrate/`.
2. `docs(v63-case006): retro substrate extension · V-row capture 1/9 → ≥3/9 verified` — adds `.planning/retrospectives/2026-05-15_case_006_substrate_extension.md`.
3. `docs(v63-case006): sub-DEC DEC-V63-A-sub-M-CASE-006-SUBSTRATE Accepted` — this file.

Each commit carries `confidence: med` and `Surface-scan: clean` trailers.
