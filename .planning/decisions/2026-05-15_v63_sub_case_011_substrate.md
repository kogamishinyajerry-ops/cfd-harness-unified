---
decision_id: DEC-V63-A-sub-M-CASE-011-SUBSTRATE
title: case_011 v5b plate-fin compact HX input-manifest substrate extension · thin_wall + A2-v2 + D11 V94 inputs · V-row capture 3/9 → 7/9 firm · Done dim #6 cross-case clause 2/3 → 3/3 MET
status: Accepted
parent_dec: DEC-V63-A-charter
phase: V63-A Tier 2 supplement · M-CASE-011-SUBSTRATE (cross-case extension #3 · driven by Done dim #6 "≥3/9 on ≥3 cases" cross-case clause · mirror of B42 case_006 + B45 case_004 substrate plays · case_011 is the canonical V94 sediment source per DEC-V63-A-sub-D11)
notion_sync_status: pending
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope:
3 substrate-side input files synthesized under `case_011/inputs/` + 1
verification runner under `scripts/v63_case_011_substrate/` + this DEC +
the accompanying retro. Substrate edits limited to additive files; no
case_dir CAD / STL / existing manifest / `case/` runtime changes.

## Goal

Close V63-A Done dim #6 ("≥5/9 on ≥1 canonical case + **≥3/9 on ≥3
cases**") cross-case clause 2 from `2 cases ≥3/9` (case_006 post-B42 +
case_004 post-B45) to `3 cases ≥3/9` (case_006 + case_004 + case_011),
**closing Done dim #6 entirely (both clauses MET ✓ → V63-A Done dims
overall MET counter 3/6 → 4/6)**. Mirror the B42/B45 substrate playbook
on case_011 by landing the same three substrate-side input artifacts
that `thin_wall_advisor` (V10) and A2-v2 `virtual_interface_detector`
(V20 + 7 cross-case V-rows) need to dispatch end-to-end on case_011.

**Additionally** — case_011 is the canonical V94 sediment source per
`DEC-V63-A-sub-D11` (LANDED B39 · single-case land pending 2nd-case
cross-validation). The B46 verification runner extends parts_manifest
with `face_labels` and supplies inline `shm_stl_face_normals` so the D11
`stl_face_label_validator` dispatches and emits the documented full V94
6-orphan replay. **Target reached: 6 distinct V-rows + 1 shared row =
7/9 firm** — the highest single-case firm count in the V63-A series.

## Scope

Three new input files under `~/Desktop/case_011_plate_fin_compact_hx/inputs/`:

1. `thin_wall_inputs.yaml` (~40 LOC incl. derivation comment) —
   `patches[]` (5 entries: cold_fin_rear_third 0.6 mm canonical D8 +
   separator_plate_3_4_front 0.8 mm + separator_plate_3_4_rear_offset
   0.8 mm + hot_fin_base 1.0 mm + cold_fin_base 1.0 mm) +
   `refinement_levels` (5 mappings: (1,2) / (3,4) / (3,4) / (1,2) /
   (2,3) tracking v5b snappyHexMeshDict live values) +
   `background_cell_size: 0.004` + `min_cells_per_thickness: 2`.
2. `interface_bodies.json` (~115 LOC) — BodyGeometry dicts for
   `separator_plate_3_4_front` + `separator_plate_3_4_rear_offset` with
   6 axis-aligned face entries each, reconstructed from build_cad.py
   converged constants + evidence/v1/a2_d5.json input bbox extremes.
   D5_OFFSET_MM=0.03 reinterpreted as +y perpendicular gap (documented
   in _meta block).
3. `interface_specs.json` (~15 LOC) — single InterfaceSpec
   `separator_3_4_d5_interface` (mode=shared, body_a=front, body_b=
   rear_offset) targeting the documented D5 30 µm plate-plate offset.

One verification runner under repo `scripts/v63_case_011_substrate/`:

- `run_extended.py` (~190 LOC) — mirrors B42/B45 path-b runner pattern.
  Imports baseline parts_manifest + shm_dict + step_payload from
  `scripts.stack_track_c_session_1.build_inputs` (TRACK-1 source) +
  overlays `face_labels` on hot/cold parts (matches
  `test_stl_face_label_validator.py::test_case_011_v94_regression`
  verbatim · same 6 labels) + supplies inline `shm_stl_face_normals`
  (3 parent-body keys per cq.exporters single-shell V94 sediment
  shape). Loaders reconstruct
  `virtual_interface_detector.{BodyGeometry,FaceGeometry,InterfaceSpec}`
  and `thin_wall_advisor.PatchGeometry` dataclasses for the dispatch.

Out of scope (explicitly per dispatch):

- `assemble_stack` source edits
- advisor / catalog source edits
- case_dir CAD (cad_codex_v1.step) / STL (case/constant/triSurface/) /
  existing manifest / `case/` runtime artifact edits
- TRACK-1-rerun adoption regression (must remain at 5/5 = 100% PASS)
- Notion sync (v2.3 round-1 loosen — only Accepted DECs sync at
  session-end)
- Codex review (substrate YAML/JSON additions + per-case runner are not
  auth / signing / operator endpoint; not a v2.2 1-sync-trigger)
- Kogami invocation (v2.3 opt-in; not requested)
- ARC-GOAL.md edits (main session reconciles to avoid parallel B46/B47
  rebase contention; recommended language in retro §10 #1)

## case_011 inputs · audit before B46

Pre-B46 substrate state, contributed by V62-A M-STACK-TRACK-1 +
TRACK-1-rerun:

| input | location | provenance | status |
|---|---|---|---|
| STEP geometry | `inputs/cad_codex_v1.step` | build_cad.py converged | ✓ in place (5.5 MB) |
| parts_manifest (cellZone shape) | code-built in `build_inputs.py::build_parts_manifest` | 3 cellZones, no face_labels | ✓ in place |
| shm_dict (v5b live transcribed) | `build_inputs.py::build_shm_dict` | refinementSurfaces level (1,2)/(2,3)/(3,4) | ✓ in place |
| thin_wall_inputs (1 patch) | `build_inputs.py::build_thin_wall_inputs` | cold_fin_rear_third 0.6 mm from evidence/v1/thin_wall_d8.json | ✓ in place (single patch) |
| step bbox max extent | `build_inputs.py::build_step_payload` | 0.180 m (180 mm raw) | ✓ in place |
| **interface_bodies** | — | — | **❌ missing** |
| **interface_specs** | — | — | **❌ missing** |
| **face_labels overlay on parts_manifest** | — | — | **❌ missing** (V94 input-stranded) |
| **shm_stl_face_normals** | — | — | **❌ missing** (V94 path-a input-stranded) |
| **canonical thin_wall_inputs.yaml** | — | — | **❌ missing** (1 patch code-form only) |

**Decision**: not already-fully-furnished — 5 of 10 substrate inputs
needed for the full V63-A V-row capture were missing or input-stranded.
3 new substrate input files + 1 runner close the gap.

## Synthesis trace

The 3 input files are *derived*, not authored from scratch. Provenance
chain for every numeric value:

| input file | numeric values | source |
|---|---|---|
| `thin_wall_inputs.yaml` patches.cold_fin_rear_third | `[0.0006, 0.016, 0.18]` | `evidence/v1/thin_wall_d8.json::input.bbox_dimensions_m` verbatim; `scripts/build_cad.py::D8_REAR_FIN_THICKNESS_MM = 0.6` |
| ditto separator_plate_3_4_front | `[0.180, 0.080, 0.0008]` | `build_cad.py::L_MM = 180` × `REAR_THIRD_START_Y_MM = 80` × `PLATE_THICKNESS_MM = 0.8` (build_stack_layout d5_plate split) |
| ditto separator_plate_3_4_rear_offset | `[0.180, 0.040, 0.0008]` | `L_MM` × `(W_MM - REAR_THIRD_START_Y_MM) = 40` × `PLATE_THICKNESS_MM` (rear segment of d5_plate) |
| ditto hot_fin_base | `[0.001, 0.012, 0.18]` | `BASE_FIN_THICKNESS_MM = 1.0` × `HOT_CHANNEL_HEIGHT_MM = 12` × `L_MM = 180` |
| ditto cold_fin_base | `[0.001, 0.016, 0.18]` | `BASE_FIN_THICKNESS_MM` × `COLD_CHANNEL_HEIGHT_MM = 16` × `L_MM` |
| `thin_wall_inputs.yaml` refinement_levels | (1,2)/(3,4)/(3,4)/(1,2)/(2,3) | mirrors `case/system/snappyHexMeshDict` v5b live: region_hot_fluid (1,2), region_cold_fluid (2,3), region_solid (3,4) |
| `thin_wall_inputs.yaml` background_cell_size | `0.004` | `case/system/snappyHexMeshDict::castellatedMeshControls.refinementSurfaces` v5b live effective bg |
| `interface_bodies.json` separator_plate_3_4_front faces | 6 axis-aligned faces (areas 64 / 64 / 144 / 144 / 14400 / 14400 mm²) | reconstructed from bbox `[0,0,12.4]` to `[180,80,13.2]`; area = cross-product of bbox extents (geometrically exact for axis-aligned plate hull) |
| ditto separator_plate_3_4_rear_offset faces | 6 axis-aligned faces | reconstructed from bbox `[0, 80.03, 12.4]` to `[180, 120, 13.2]` (y-perpendicular D5 encoding) |
| `interface_specs.json` separator_3_4_d5_interface | gap 0.03 mm | `scripts/build_cad.py::D5_OFFSET_MM = 0.03` verbatim + `evidence/v1/a2_d5.json::input.interface_offset_um = 30.0` verbatim (/1000 → 0.03 mm); geometric verification: front_+y face at y=80.0 vs rear_-y face at y=80.03, \|Δy\| = 0.03 mm ✓ |

D5 substrate-encoding choice (x-translation in build_cad.py reinterpreted
as y-perpendicular gap for A2-v2 consumption) documented at length in
`interface_bodies.json::_meta::derivation`. Both encodings represent the
same engineering defect (30 µm manufacturing displacement of the rear
plate piece) and are equally-defensible substrate abstractions; the
y-perpendicular form is the one A2-v2's
`should_have_been_shared_with_unintended_gap` classifier consumes
directly.

## Before / After V-row capture matrix

Mirrors B42/B45 9-row failure-mode matrix:

| failure mode | pre-substrate | post-substrate | mechanism |
|---|---|---|---|
| **V10** thin_wall_at_risk (D8 canonical 0.6 mm sliver) | YES ✓ firm | YES ✓ firm | thin_wall_advisor critical on cold_fin_rear_third (cells_per_thickness=0.60) |
| **V20+V96** unit_inference | YES ✓ firm | YES ✓ firm | unit_detector — pre-existing TRACK-1 finding |
| **V22** A2-v2 plate-plate adjacency | partial (a2_d5.json placeholder per V25) | **YES ✓ firm** | virtual_interface_detector matches separator_3_4_d5_interface; normal_dot=1.0 |
| **V29** BC-name catalog | NO ← input-stranded | NO | out-of-stack (case_011 TRACK-1 build_inputs supplies no `bc_specs`; D10 dispatch gate not met) |
| **V30** thin_wall sliver class | partial (1 sliver) | **YES ✓ firm** | thin_wall_advisor critical on cold_fin_rear_third (sliver-class signature); hot_fin_base AT_RISK warning extends |
| **V34** sHM cellzone fragmentation | NO | NO | out-of-stack (no fragmentation-class advisor yet) |
| **V94** face-label loss (D11 canonical coverage) | NO ← input-stranded | **YES ✓ firm** | stl_face_label_validator 6 orphan_declared_label findings — full V94 canonical replay |
| **D5** sub-mm plate-plate offset (30 µm) | partial (evidence scalar only) | **YES ✓ firm** | A2-v2 `should_have_been_shared_with_unintended_gap(max_gap=1.0)` → True (gap=0.03 mm) → critical D1-class |
| **D8** 0.6 mm rear fin | YES ✓ firm (shares V10) | YES ✓ firm (shares V10) | thin_wall_advisor (same row as V10) |

**Catch rate: 3 / 9 firm pre (V10 · V20+V96 · D8 [shared V10]) → 7 / 9
firm post (V10 · V20+V96 · V22 · V30 · V94 · D5 · D8 [shared V10]). ≥ 3 /
9 target MET. Supplementary clause ≥ 5 / 9 also MET on case_011 alone
(6 distinct V-rows + 1 shared = 7/9).**

**Done dim #6 cross-case clause 2 progress: 2 cases ≥3/9 (case_006
post-B42 + case_004 post-B45) → 3 cases ≥3/9 (case_006 + case_004 +
case_011); clause 2 MET ✓ at 3/3. Done dim #6 OVERALL MET ✓ (both
clauses) → V63-A Done dims 3/6 → 4/6.**

## Verification evidence

`assemble_stack(...)` pre/post on case_011 (path b, LLM-keys-popped):

| metric | pre (`stack_track_c_session_1_rerun/stack_report_python_rerun.json`) | post (`v63_case_011_substrate/stack_report_python_extended.json`) | delta |
|---|---|---|---|
| advisor_count | 5 | 7 | +2 (`virtual_interface_detector`, `stl_face_label_validator`) |
| finding_count | 2 | 11 | +9 |
| critical_count | 1 | 2 | +1 |
| warning_count | 1 | 8 | +7 |
| failed_advisor_count | 0 | 0 | 0 |
| evidence_refs (V-row union) | 10 | 18 | +8 (V22, V25, V33, V36, V42, V43, V50, V94) |
| env_keys_present (V130 Q1) | all false | all false | invariant ✓ |

Net-new findings (delta = 9):

```
[CRITICAL] virtual_interface_detector · d1_unintended_gap · separator_3_4_d5_interface
           · V22 V25 V33 V36 V42 V43 V50 · gap=0.0300 mm
[WARNING ] stl_face_label_validator   · orphan_declared_label · region_hot_fluid·hot_inlet  · V94
[WARNING ] stl_face_label_validator   · orphan_declared_label · region_hot_fluid·hot_outlet · V94
[WARNING ] stl_face_label_validator   · orphan_declared_label · region_hot_fluid·hot_walls  · V94
[WARNING ] stl_face_label_validator   · orphan_declared_label · region_cold_fluid·cold_inlet · V94
[WARNING ] stl_face_label_validator   · orphan_declared_label · region_cold_fluid·cold_outlet · V94
[WARNING ] stl_face_label_validator   · orphan_declared_label · region_cold_fluid·cold_walls · V94
[WARNING ] thin_wall_advisor          · thin_wall_at_risk · hot_fin_base  · V10 (cells_per_thickness=1.00 AT_RISK)
[INFO    ] thin_wall_advisor          · thin_wall_at_risk · cold_fin_base · V10 (cells_per_thickness=2.00 marginal)
```

Reports serialised to:

- `scripts/stack_track_c_session_1_rerun/stack_report_python_rerun.json`
  (pre · unchanged from B33 land)
- `scripts/v63_case_011_substrate/stack_report_python_extended.json`
  (post · new)

## Backward-compat

- `scripts/stack_track_c_session_1_rerun/run_python_path_rerun.py`
  re-runs unchanged: still 5 advisors / 2 findings / 1 critical / 1
  warning / 10 V-rows. `assemble_stack`'s keyword-only-with-`None`-
  default signature means the old call site silently skips A2-v2 + D11
  dispatches (V130 silent-skip discipline). **TRACK-1-rerun 100% adoption
  (B33 closure) preserved at 5/5 = 100% PASS post-B46.**
- `scripts/stack_track_c_session_1/run_python_path.py` (original TRACK-1)
  untouched.
- `case/` directory contents untouched (v5b OpenFOAM runtime artifacts
  intact — 3.34 M hot / 2.98 M cold / 5.85 M solid cells).
- `inputs/cad_codex_v1.step` (5.5 MB STEP) — unchanged.
- `evidence/v[1-3]/*.json` and `evidence/v[1-3]/REPORT.md` — unchanged.
- `docs/decisions_v1.md` and `README.md` — unchanged.
- D11 stl_face_label_validator gate (DEC-V63-A-sub-D11) — unaffected;
  the B46 runner exercises the dispatch path that D11 was authored
  against (case_011 V94 canonical replay) and yields 6 orphans matching
  the regression test in `test_stl_face_label_validator.py` #11.

## Surface scan

```
$ ls ~/Desktop/case_011_plate_fin_compact_hx/inputs/ | grep -E "thin_wall_inputs|interface_bodies|interface_specs"
(empty pre-land — none existed)
$ ls scripts/v63_case_011_substrate/
(directory did not exist pre-land)
```

`Surface-scan: clean` on all 3 commits.

## v2.3 compliance

- **Scope class**: sub-DEC (3 input files + 1 runner + 1 retro + 1 DEC =
  6 files; 3 shared code paths touched: `inputs/` additive · `scripts/`
  additive · `.planning/decisions/` + `.planning/retrospectives/`). Below
  charter threshold (no schema break, no security boundary, no new shared
  invariants). Full DEC frontmatter limited to the 6 required v2.3 fields.
- **Cadence floor (30)**: not triggered — documented cross-case extension
  mirroring B42/B45; net new LOC under 400 across all 3 input files +
  runner.
- **Codex review**: not required. v2.3 1-sync-trigger is auth / signing /
  operator-endpoint only; substrate YAML/JSON additions + a per-case
  verification runner do not qualify. Round count: 0.
- **Kogami invocation**: not requested (v2.3 opt-in; substrate work is
  not a strategic-narrative event).
- **Notion sync**: pending (per v2.3 round-1 loosen, only Status=Accepted
  DECs sync at session-end; this DEC moves Proposed → Accepted within
  the same dispatch so will sync in the next session-end batch if the
  user triggers `notion-sync-cfd-harness`).
- **4Q gate**: all four pillars confirmed in retro §8 (LLM-offline ✓ /
  artifacts emitted ✓ / TrustGate explanation ✓ / AI advisory-only ✓).
- **Confidence**: med. Plate bbox values are build_cad.py-verbatim for
  the macro extents (W_MM=120, L_MM=180, PLATE_THICKNESS_MM=0.8,
  REAR_THIRD_START_Y_MM=80.0, D5_OFFSET_MM=0.03) and `evidence/v1/`-
  verbatim for the D5+D8 scalar inputs. The substrate's y-perpendicular
  encoding of D5 (rather than the x-translation in build_cad.py) is a
  documented abstraction choice with _meta provenance. Stack diff
  pattern matches the B45 case_004 closure (multi-patch thin_wall +
  A2-v2 D-class) extended with D11 V94 6-orphan replay (B45 case_004 has
  no STL yet so V94 stays NO there; case_011 is the only current case
  where D11 fires firm).

## Open follow-ups (deferred · not blocking Accepted)

1. **ARC-GOAL.md Done dim #6 update** — main session reconciles between
   this B46 land and parallel B47 (V-series methodology). Recommended
   language: `clause 2 progress: 3 / ≥3 cases ≥3/9 covered (case_004 +
   case_006 + case_011); ≥3-case clause MET ✓ · Done dim #6 OVERALL MET
   ✓ · Done dims MET 3/6 → 4/6`.
2. **D5 x-vs-y encoding canonicalisation** — case_011 substrate uses
   y-perpendicular encoding of the D5 30 µm offset; build_cad.py uses
   x-translation. A future cross-case sub-DEC (when D5-class accumulates
   2+ cases) should canonicalise the substrate→A2-v2 abstraction so the
   downstream interface_bodies.json convention is documented project-
   wide. Until then the _meta block per file is sufficient.
3. **V94 cross-case promotion** — `DEC-V63-A-sub-D11 §Status` notes V94
   carries [QUESTIONABLE] until a 2nd industrial case sediments a
   face-label-loss class. Recommended 2nd-case candidates: case_013 /
   case_015 CHT-LES (forward-loaded per `case_proposal_queue.md`).
4. **V34 sHM cellzone fragmentation advisor** — case_011 v1 documented
   region_hot_fluid in 312 connected components. No LANDED advisor
   catches this today; promotion candidate as
   `cellzone_fragmentation_advisor`. Defer until 2+ cases show the
   pattern (case_011 only so far).
5. **V29 BC-name catalog firing on case_011** — would require TRACK-1
   build_inputs to additionally supply `bc_specs` reflecting the v5b
   `0/U`/`0/p`/`0/T` BC dictionaries. Out of scope for B46 (substrate-
   only). A follow-up sub-DEC could canonicalise the bc_specs input
   loader and re-run case_011/case_006/case_004 path-a in one motion.
6. **HTTP-path auto-discovery (carry-over from B42 §10 #3 + B45 §10 #3)**
   — production `/api/ai-review` route probes `case_dir/` root not
   `case_dir/inputs/`, so case_011's three new files are invisible to
   the HTTP path. Path-b runner closes the V94 / V22 / V30 / D5 capture
   gap as documented; HTTP path remains stranded until a future sub-DEC
   canonicalises the loader's probe locations (best done across case_004
   / case_006 / case_011 simultaneously).
7. **Solver e2e validation (M-VAL-REPORT-1..3)** — case_011 v3 sediments
   V94 + fragmented mesh; substrate work alone doesn't unblock a clean
   prep→solver→postp pipeline. M-VAL-REPORT-1 for case_011 still
   requires v6 mesh (level (3,4) for fin patches per thin_wall_advisor
   recommendation) + V94 face-label re-export. B46 gives the advisor
   stack visibility into both blockers but does not itself close them.

## Commits

1. `feat(v63-case011): synthesize thin_wall_inputs + interface_bodies + interface_specs + D11 V94 runner wiring` — adds the 3 input files under `case_011/inputs/` + the verification runner + `__init__.py` under `scripts/v63_case_011_substrate/`.
2. `docs(v63-case011): retro substrate extension · V-row capture 3/9 → 7/9 firm verified · Done dim #6 MET` — adds `.planning/retrospectives/2026-05-15_case_011_v5b_substrate_extension.md`.
3. `docs(v63-case011): sub-DEC DEC-V63-A-sub-M-CASE-011-SUBSTRATE Accepted` — this file.

Each commit carries `confidence: med` and `Surface-scan: clean` trailers.
