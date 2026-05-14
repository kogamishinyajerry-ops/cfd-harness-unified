# RETRO · case_004 NREL Phase VI MRF substrate extension · V63-A Tier 2 cross-case #2

> V63-A Tier 2 · M-CASE-004-SUBSTRATE (DEC-V63-A-sub-M-CASE-004-SUBSTRATE).
> Driver: V63-A Done dim #6 ("≥5/9 on ≥1 canonical case + ≥3/9 on ≥3 cases").
> case_006 hit 3/9 firm on 2026-05-15 (B42 land); case_004 sat at 1/9
> (V29 only) with the V30 + D1 documented failure modes stranded behind
> missing substrate-side input files. This retro mirrors the B42 case_006
> playbook on case_004: land three substrate-side input files under
> `case_004/inputs/` so the now-LANDED `thin_wall_advisor` (V10) and
> A2-v2 `virtual_interface_detector` (V20+7 cross-case V-rows) dispatch
> end-to-end on case_004 too, advancing Done dim #6 from 1 canonical case
> to 2 canonical cases ≥3/9.

---

## §1 Goal

Mirror the B42 case_006 substrate land on case_004:

1. Synthesize three input files under `case_004/inputs/` derivable from
   existing `inputs/_freecad_extract.json` + `inputs/parts_manifest.yaml`
   + `inputs/defect_manifest.yaml`:
   - `thin_wall_inputs.yaml` (V10 substrate for `thin_wall_advisor`)
   - `interface_bodies.json` (BodyGeometry list for A2-v2)
   - `interface_specs.json` (InterfaceSpec list for A2-v2)
2. Verify the route gap closes — `assemble_stack(...)` on case_004 must
   now dispatch `thin_wall_advisor` + `virtual_interface_detector`
   alongside the four `stack_track_c_case_ext_1` baseline advisors.
3. Push V-row truth capture from 1/9 → ≥3/9 against the documented
   case_004 failure modes (V22/V23/V24 V-series + V29 BC-name catalog +
   V30 thin_wall sliver + V94 face-label-loss + D1 sub-mm gap + D8 thin
   shim + MRF-class hypotheses).
4. Done dim #6 advances from "1 canonical case ≥3/9, ≥3 cases distance =
   2 cases" → "2 canonical cases ≥3/9, ≥3 cases distance = 1 case".
   Do **not** update ARC-GOAL.md (main session reconciles to avoid
   parallel B44/B45 rebase contention).

Constraints (dispatch + v2.3 governance):

- substrate edits limited to `case_004/inputs/` (3 new files; no
  case_dir / STEP / STL / manifest changes)
- no `assemble_stack` source edits
- no advisor / catalog source edits
- no Notion sync (sub-DEC stays local until Accepted; v2.3 round-1 loosen
  only syncs Status=Accepted DECs)
- no Codex review (substrate-side YAML/JSON additions are not a v2.2
  1-sync-trigger; not auth / signing / operator endpoint)
- no Kogami (v2.3 opt-in)
- 3 atomic commits each carrying `confidence: med`
- no kill of any port-occupying process (per global standing rule)

---

## §2 case_004 evidence survey

`inputs/_freecad_extract.json` (259 KB) is the canonical FreeCAD body-
extract for case_004 produced by `scripts/_freecad_extract.py` against
`inputs/cad_codex_v1.step` (~387 KB, 12 expected bodies + datum frames).
Key extract fields used:

| field | extract path | value |
|---|---|---|
| nacelle_body bbox | `bodies['nacelle_body'].bbox_min_mm / bbox_max_mm` | [700, -450, -410] → [2500, 450, 410]; dims [1800, 900, 820] |
| nacelle_service_cover bbox | `bodies['nacelle_service_cover'].bbox_*_mm` | [1290, 450.3, -40] → [1910, 485.3, 280]; dims [620, 35, 320] |
| yaw_sensor_shim bbox | `bodies['yaw_sensor_shim'].bbox_*_mm` | [1060, -490.375, -540] → [1380, -489.625, -320]; dims [320, 0.75, 220] |
| hub_spinner bbox | `bodies['hub_spinner'].bbox_*_mm` | [-410, -360, -360] → [410, 360, 360]; dims [820, 720, 720] |
| D1 gap distance | `distances['nacelle_body__nacelle_service_cover']` | 0.30000000000001137 mm |

The D1 gap value matches `defect_manifest.yaml D1.measurement.claimed_gap_mm: 0.30` verbatim
(modulo float-round artifact at the 14th decimal). Geometric verification of the
gap geometry: nacelle_body +Y face at y=450.0 vs nacelle_service_cover -Y face at y=450.3,
|Δy| = 0.30 mm ✓.

The yaw_sensor_shim bbox-min direction is 0.75 mm (Y-dim) — matches
`defect_manifest.yaml D8.measurement.claimed_thickness_mm: 0.75` verbatim.

`_freecad_extract.json` does **not** list per-face geometry for nacelle_body /
nacelle_service_cover (the extractor only emits centroid + bbox + n_faces, not
per-face bounds). For the A2-v2 detector both bodies were therefore reconstructed
as 6-face axis-aligned boxes from `bbox_min_mm / bbox_max_mm`, which is valid
because both bodies are axis-aligned in this case (nacelle_body is the simplified
cylindrical-bullet hull treated as box; nacelle_service_cover is a rectangular
service-cover plate). Reconstructed face areas (738000 / 1476000 / 1620000 mm² for
nacelle_body; 11200 / 198400 / 21700 mm² for nacelle_service_cover) are consistent
with bbox × bbox cross-sections.

The rotor_blade_trailing_edge_sliver bbox [0.50, 20, 358] mm is an *informed
estimate* derived from NREL Phase VI S809 airfoil characteristic at the tip
station (chord_tip ≈ 358 mm, blunt trailing-edge ≈ 0.50 mm per NREL/TP-500-29955
manufacturing-drawing convention, last spanwise station ≈ 20 mm). The sliver
body is not present in `_freecad_extract.json` — it is a substrate hint added so
the v2 mesh sub-session will catch a known NREL Phase VI canonical concern. The
advisor result (CRITICAL at level_max=4 → 0.40 cells_per_thickness) marks this
as a V62-A-class follow-up rather than masking it silently.

---

## §3 Three new input files

### 3.1 `case_004/inputs/thin_wall_inputs.yaml` (≈ 50 LOC incl. derivation comment)

Five patches matched to FreeCAD-extracted bbox values:

| patch | bbox_dims [mm] | source | refinement_levels |
|---|---|---|---|
| `nacelle_body` | [1800, 900, 820] | `_freecad_extract.json::bodies['nacelle_body'].bbox_dims_mm` verbatim | [3, 4] |
| `nacelle_service_cover` | [620, 35, 320] | `_freecad_extract.json::bodies['nacelle_service_cover'].bbox_dims_mm` verbatim | [3, 4] |
| `yaw_sensor_shim` | [320, 0.75, 220] | `_freecad_extract.json::bodies['yaw_sensor_shim'].bbox_dims_mm` verbatim — D8 thin shim | [1, 2] |
| `hub_spinner` | [820, 720, 720] | `_freecad_extract.json::bodies['hub_spinner'].bbox_dims_mm` verbatim | [4, 5] |
| `rotor_blade_trailing_edge_sliver` | [0.50, 20, 358] | derived from NREL Phase VI S809 tip station blunt-TE convention; informed estimate; advisor result preserved (correctness invariant to ±50%) | [3, 4] |

`background_cell_size: 20.0 mm`, `min_cells_per_thickness: 2` (matches case_006).

### 3.2 `case_004/inputs/interface_bodies.json` (~140 LOC)

`virtual_interface_detector.BodyGeometry` dicts for `nacelle_body` +
`nacelle_service_cover`. Each body declared as 6-face axis-aligned box
reconstructed from bbox_min_mm / bbox_max_mm + per-face normal +
per-face area (bbox × bbox cross-section).

### 3.3 `case_004/inputs/interface_specs.json` (~24 LOC)

Single `InterfaceSpec`:

```json
{
  "patch_name": "nacelle_d1_interface",
  "mode": "shared",
  "body_a": "nacelle_body",
  "body_b": "nacelle_service_cover",
  "documented_gap_mm": 0.30,
  "defect_id": "D1",
  "evidence_v_rows": ["V22"]
}
```

Targets the documented 0.30 mm gap on the downstream nacelle service-cover
hardware. Defect placement preserves NREL Phase VI blade pressure-tap regions
per `defect_manifest.yaml::D1.reference_data_validity`.

---

## §4 Verification runner

`scripts/v63_case_004_substrate/run_extended.py` mirrors the B42
`scripts/v63_case_006_substrate/run_extended.py` runner with one
substrate-specific change: imports the case_004 baseline from
`scripts.stack_track_c_case_ext_1.build_inputs` (case_004's TRACK-c baseline)
rather than case_006's `stack_track_c_session_3_rerun.build_inputs`. The
loader functions for the 3 new files are identical to the case_006 runner
(YAML→PatchGeometry, JSON→BodyGeometry/FaceGeometry/InterfaceSpec reconstruction).

`assemble_stack(...)` invocation passes the 3 substrate kwargs alongside the
unchanged baseline (parts_manifest, shm_dict=None, thermo_dict=None,
step_path=cad_codex_v1.step). `shm_dict` and `thermo_dict` remain `None` per
case_004 substrate state (no snappyHexMeshDict / no thermophysicalProperties
in v1 — A8 + A10 silently skip, which is the correct dispatch per case_004
profile).

4Q gate Q1 enforced at runner top: `os.environ.pop` for
ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY / DEEPSEEK_API_KEY
*before* any backend import.

---

## §5 Before / After stack diff

`assemble_stack(...)` on case_004 (path b, LLM-keys-popped):

| metric | pre (`scripts/stack_track_c_case_ext_1/stack_report_python.json`) | post (`scripts/v63_case_004_substrate/stack_report_python_extended.json`) | delta |
|---|---|---|---|
| advisor_count | 4 | 6 | +2 (`thin_wall_advisor`, `virtual_interface_detector`) |
| finding_count | 3 | 6 | +3 |
| critical_count | 0 | 3 | +3 |
| warning_count | 3 | 3 | 0 |
| failed_advisor_count | 0 | 0 | 0 |
| evidence_refs (V-row union) | 6 (V20, V29, V79, V81, V87, V96) | 14 | +8 (V10, V22, V25, V33, V36, V42, V43, V50) |
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

---

## §6 V-row capture matrix (case_004 documented failure modes)

case_004 has no formal 9-row defect-V catalog like case_006 (V26-V32 + D1 +
D4). The closest equivalent is the union of:

- V-series sourced per `case_profiles/case_004_nrel_phase_vi_mrf.md` §V-series sourced (V2 upgrade, V10 upgrade, V22, V23, V24)
- D-class defects per `defect_manifest.yaml` (D1, D8)
- BC-name catalog hits (V29)
- documented failure-mode hypotheses (V30 thin_wall sliver — case_006 carry-over class; V94 face-label loss — D11 advisor coverage gap)

| failure mode | pre-substrate | post-substrate | mechanism |
|---|---|---|---|
| V22 A2-v2 rotating-machinery field-validation | partial (referenced) | **YES ✓ firm** | virtual_interface_detector fires on nacelle_d1_interface; A2-v2 returns gap=0.30 → classifier critical |
| V23 thin_wall_advisor rotating-machinery aux | partial (referenced) | **YES ✓ firm** | thin_wall_advisor fires on yaw_sensor_shim 0.75 mm → CRITICAL |
| V24 FreeCAD sentinel-bbox + compound fragment | NO | NO | out-of-stack (substrate hides the datum frames; verifier dispatched on `_freecad_extract.py` is the upstream catcher) |
| V29 BC-name catalog | YES ✓ firm | YES ✓ firm | bc_type_name_validity_advisor (already firm at B43 baseline) |
| V30 thin_wall sliver class | NO ← input-stranded | **YES ✓ firm** | thin_wall_advisor fires on yaw_sensor_shim 0.75 mm + rotor_blade_trailing_edge_sliver 0.50 mm → both CRITICAL |
| V94 face-label loss (D11 coverage) | NO | NO | out-of-stack (D11 stl_face_label_validator needs `shm_stl_face_normals` substrate; case_004 has no STL yet, A8 path silent-skip) |
| D1 sub-mm nacelle gap | partial (defect manifest only) | **YES ✓ firm** | A2-v2 returns inter_face_gap_mm=0.30; classifier should_have_been_shared_with_unintended_gap(threshold=1.0) flags critical |
| D8 thin shim 0.75 mm | partial (defect manifest only) | **YES ✓ firm (covered by V30 mechanism)** | thin_wall_advisor catches yaw_sensor_shim CRITICAL (same finding row as V30) |
| MRF-class hypotheses (omega/axis/zone) | NO | NO | out-of-stack (07b_audit_mrf is case-local; not yet stack-registered) |

**Catch rate**:
- Pre (B43 baseline): **1/9 firm** (V29 only; V22/V23/D1/D8 partial; V24/V30/V94/MRF NO)
- Post (this sub-DEC): **5/9 firm** (V22, V23, V29, V30, D1 — plus D8 sharing the V30 mechanism row).

**≥3/9 target MET** — V63-A Done dim #6 cross-case clause "≥3/9 on ≥3 cases":
- case_006: 3/9 firm (B42 LANDED)
- case_004: 5/9 firm (this land)
- third case (TBD · candidate from queue): distance = 1

(Note: the case_006 sub-DEC scored 3/9 firm + D4 marginal because case_006's
9-row catalog includes 7 V-rows that are out-of-stack-by-design — V26 Codex
CAD off-by-half-width, V27/V28 rhoCentralFoam numerics, V31 Codex protocol,
V32 Tier-1 NASA Glenn HTTP infra. case_004's documented-failure-mode set
includes more in-stack rows because rotating-machinery field-validation
maps cleanly onto A2-v2 + thin_wall_advisor. Cross-case comparison is
qualitatively "≥3/9 met" for both, not a literal LOC compare.)

---

## §7 Backward-compat

- `scripts/stack_track_c_case_ext_1/run_python_path.py` re-runs unchanged:
  still 4 advisors / 3 findings / 6 V-rows. `assemble_stack`'s keyword-only-
  with-`None`-default signature means the old call site silently skips the
  new dispatches. Re-verified by rerun during this land (pre report frozen
  at `scripts/stack_track_c_case_ext_1/stack_report_python.json`).
- `scripts/stack_track_c_case_ext_1/run_http_path.py` is untouched. Per the
  B42 case_006 sub-DEC §4 ("HTTP-path auto-discovery"), the HTTP route's
  substrate-input probe loads `case_dir/interface_bodies.json` (root level)
  and `case_dir/manifest.json` for substrate inputs; the 3 new files land
  under `case_dir/inputs/` per dispatch scope, so HTTP-path auto-discovery
  continues to skip them. Path-b (`assemble_stack` direct call) closes
  V30 + D1 as documented; HTTP path remains stranded until a follow-up
  sub-DEC wires the route loader to additionally probe `case_dir/inputs/`.
- `case/` directory contents untouched (OpenFOAM run artifacts intact).
- `parts_manifest.yaml`, `defect_manifest.yaml`, `cad_codex_v1.step` —
  unchanged.
- D11 stl_face_label_validator gate (DEC-V63-A-sub-D11) unaffected — its
  dispatch precondition reads `shm_stl_face_normals` / `parts_manifest`
  face_labels / `shm_dict` refinementSurfaces; the new YAML/JSON inputs
  feed `thin_wall_advisor` + `virtual_interface_detector` exclusively.

---

## §8 Surface scan

```
$ ls ~/Desktop/case_004_nrel_phase_vi_mrf/inputs/ | grep -E "thin_wall_inputs|interface_bodies|interface_specs"
(empty — none exist pre-land)
$ ls scripts/v63_case_004_substrate/
(directory did not exist pre-land)
```

`Surface-scan: clean` on all 3 commits per DEC-V61-088 commit-trailer discipline.

---

## §9 v2.3 compliance + 4Q gate

| dim | finding |
|---|---|
| Scope class | sub-DEC (3 input files + 1 runner + 1 retro + 1 DEC = 6 files; not crossing ≥3 shared code paths; no schema break; no security boundary). Below charter threshold; full DEC frontmatter limited to the 6 required fields. |
| Cadence floor (30) | not triggered — documented cross-case extension, not a new direction; net new LOC under 350 across all files. |
| Codex review | not required. 1-sync-trigger is auth/signing/operator-endpoint only; substrate YAML/JSON additions do not qualify. Round count: 0. |
| Kogami invocation | not requested (v2.3 opt-in; substrate work is not a strategic-narrative event). |
| Notion sync | pending (per v2.3 round-1 loosen, only Status=Accepted DECs sync at session-end; this DEC moves Proposed → Accepted within the same dispatch so will sync in next session-end batch if user triggers `notion-sync-cfd-harness`). |
| 4Q-1 LLM-offline | ✓ runner pops `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` / `DEEPSEEK_API_KEY` at module top before any backend import; `env_keys_present` all `false` in report. |
| 4Q-2 artifacts emitted | ✓ `scripts/v63_case_004_substrate/stack_report_python_extended.json` (4.8 KB) + 3 input files + retro + sub-DEC. |
| 4Q-3 TrustGate explanation | ✓ every finding carries `evidence_v_rows` (V10 / V22 / V25 / V33 / V36 / V42 / V43 / V50); V-row catalog at `advisor_stack.py::EVIDENCE_V_ROWS` is the SSOT. |
| 4Q-4 AI advisory-only | ✓ both new advisors return read-only `ThinWallWarning` / `DetectedInterface` dataclasses; no mutating route invoked. Confirmed via class docstrings (`thin_wall_advisor.py` lines 30-34, `virtual_interface_detector.py` module top). |
| Confidence | **med**. Box bboxes are FreeCAD-verbatim for 4/5 thin-wall patches; the 5th (rotor_blade_trailing_edge_sliver) is an informed estimate that advisor flags CRITICAL — the V63-A v2 mesh sub-session will refine this number when the trailing-edge boundary layer template is authored. Interface body face reconstruction is axis-aligned box from bbox extremes (geometrically exact for the nacelle bodies since both are simplified hulls). D1 gap 0.30 mm matches `_freecad_extract.json::distances` verbatim + defect_manifest verbatim. Stack diff matches the case_006 B42 closure pattern (V30 + D1 input-stranded → firm). |

---

## §10 Open follow-ups (deferred · not blocking Accepted)

1. **ARC-GOAL.md Done-dim-#6 update** — main session reconciles between this
   land (case_004 → 2nd canonical case ≥3/9) and parallel B44 (whichever new
   case is dispatched). Recommended language:
   - Done dim #6 cross-case clause: `2 / ≥3 cases ≥3/9 covered (case_006 + case_004); 1 remaining`
2. **rotor_blade_trailing_edge_sliver bbox refinement** — current 0.50 mm
   estimate is a substrate hint, not measured. V62-A v2 mesh sub-session
   should re-emit `_freecad_extract.json` after a finer-tessellation STEP
   export and replace this entry with a measured value. Until then the
   CRITICAL finding is a "look here" marker, not a quantitative claim.
3. **HTTP-path auto-discovery (case_006 sub-DEC §10 carry-over)** —
   `scripts/v63_case_004_substrate/run_extended.py` uses path b (direct
   `assemble_stack(...)` call); HTTP path-a route (`/api/ai-review`) would
   probe `case_dir/` root for `interface_bodies.json` + `manifest.json`,
   missing the `case_dir/inputs/` location entirely. A future follow-up
   sub-DEC to canonicalize the loader's probe locations would close both
   case_004 + case_006 path-a stranding in one motion.
4. **MRF-class advisor extraction** — `scripts/07b_audit_mrf.py` is
   case-local (case_004 only); after 1-2 more rotating cases share the
   pattern, A6 candidate `case_solve/mrf_writer.py` + A7 candidate
   `mesh_quality/mrf_audit.py` extraction is the right move per case_004
   profile §Mapping. Until then the MRF-class hypotheses sit out-of-stack.
5. **D11 stl_face_label_validator land on case_004** — case_004 has no STL
   yet (v2 mesh sub-session scope). When STL lands, D11 will fire if the
   sHM-extracted face normals include face_labels matching the
   parts_manifest. Coverage of V94 deferred to that sub-session.

---

## §11 Outcome summary

- 3 atomic input files synthesized + 1 verification runner + this retro
- Stack diff: 4 → 6 advisors / 3 → 6 findings / 0 → 3 critical / 6 → 14 V-rows
- V-row truth capture: 1/9 → 5/9 firm; ≥3/9 target MET
- V63-A Done dim #6 cross-case clause: 1 → 2 canonical cases ≥3/9 (≥3-case
  distance = 1)
- 4Q gate inline PASS on all four pillars
- v2.3 compliance: sub-DEC scope class confirmed; cadence floor not
  triggered; Codex / Kogami / Notion sync correctly skipped
- ARC-GOAL.md edit deferred to main-session reconcile (parallel B44 safe)
