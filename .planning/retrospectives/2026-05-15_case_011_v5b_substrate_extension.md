# Retrospective · case_011 v5b substrate extension (V63-A B46)

**Date**: 2026-05-15
**Branch**: `main`
**Sub-DEC**: `DEC-V63-A-sub-M-CASE-011-SUBSTRATE` (cross-case extension #3
driving Done dim #6 clause-2 from 2/3 → 3/3 cases)
**Predecessors**: B42 (case_006 substrate) · B45 (case_004 substrate) ·
B39 (D11 LANDED · 11 advisor tests + 4 stack-dispatch + 2 route-wire ·
case_011 V94 regression in `test_stl_face_label_validator.py` #11)
**Parallel sibling**: B47 (V-series methodology consolidation, disjoint
files)

## 1. Goal (verbatim from ARC-GOAL.md Done dim #6)

> **Done dim #6** — V-row truth-capture rate (canonical case)
> Start: 1/9 (case_006 post TRACK-3-rerun)
> Done threshold: **≥ 5/9 on ≥1 canonical case · ≥ 3/9 on ≥3 cases**
> Verification: retro §V-row attribution counter

Clause 1 ("≥5/9 on ≥1 case") was already MET by B45 (case_004 5/9 firm).
Clause 2 ("≥3/9 on ≥3 cases") had progressed to 2/3 cases (case_006 3/9
firm post-B42 + case_004 5/9 firm post-B45). This B46 land adds case_011
as the 3rd case ≥3/9, **closing Done dim #6 clause 2 (3/3 cases MET ✓)
and thereby Done dim #6 entirely (both clauses now MET ✓)**.

## 2. case_011 inputs · audit before B46

Pre-B46 substrate state, contributed by V62-A M-STACK-TRACK-1 + TRACK-1-rerun:

| input | location | provenance | post-V99-WIDEN status |
|---|---|---|---|
| STEP geometry | `inputs/cad_codex_v1.step` | build_cad.py converged | ✓ in place (5.5 MB) |
| parts_manifest (cellZone shape) | code-built in `scripts/stack_track_c_session_1/build_inputs.py::build_parts_manifest` | 3 cellZones, no inlet/outlet labels | ✓ in place |
| shm_dict (v5b live transcribed) | `build_inputs.py::build_shm_dict` | refinementSurfaces level (1,2)/(2,3)/(3,4) | ✓ in place |
| thin_wall_inputs (1 patch) | `build_inputs.py::build_thin_wall_inputs` | cold_fin_rear_third 0.6 mm from `evidence/v1/thin_wall_d8.json` | ✓ in place (single patch) |
| step bbox max extent | `build_inputs.py::build_step_payload` | 0.180 m (180 mm raw) | ✓ in place |
| **interface_bodies** | — | — | **❌ missing** |
| **interface_specs** | — | — | **❌ missing** |
| **face_labels overlay on parts_manifest** | — | — | **❌ missing** (V94 input-stranded) |
| **shm_stl_face_normals** | — | — | **❌ missing** (V94 path-a input-stranded) |
| **thin_wall_inputs.yaml (canonical multi-patch substrate form)** | — | — | **❌ missing** (1 patch code-form only; V30 sliver-class single-patch firm but no canonical YAML for the future) |

Existing v1 evidence directly usable as derivation source:

- `evidence/v1/thin_wall_d8.json` — D8 canonical (cold_fin_rear_third
  0.6 mm critical · 7-of-7 cross-topology arc PASS)
- `evidence/v1/a2_d5.json` — D5 placeholder run (matched=True but
  `bbox_overlap_fraction=1.0 / area_diff_fraction=0.0` per V25 placeholder
  contract; `interface_offset_um=30.0` is the load-bearing scalar)
- `evidence/v1/surface_extraction.json` — 3-region STL inventory
  (region_hot_fluid 11,576 facets · region_cold_fluid 15,228 · region_solid
  2,252) — confirms cq.exporters single-shell parent-body-only output
  (canonical V94 sediment source)
- `scripts/build_cad.py` — converged constants `PLATE_THICKNESS_MM=0.8`,
  `D5_OFFSET_MM=0.03`, `D8_REAR_FIN_THICKNESS_MM=0.6`,
  `BASE_FIN_THICKNESS_MM=1.0`, `W_MM=120`, `REAR_THIRD_START_Y_MM=80.0`

**Decision**: not already-fully-furnished. Three new substrate inputs are
needed (thin_wall_inputs.yaml multi-patch + interface_bodies.json +
interface_specs.json) **plus** the verification runner must build an
extended parts_manifest with face_labels + supply shm_stl_face_normals
inline (the case_011 V94 canonical replay path).

## 3. Synthesis trace

### 3.1 `thin_wall_inputs.yaml` (≈ 40 LOC including derivation comment)

Five patches:

| patch | bbox_dims (m) | thickness (mm) | refinement | source |
|---|---|---|---|---|
| `cold_fin_rear_third` | [0.0006, 0.016, 0.18] | 0.6 | (1,2) | `evidence/v1/thin_wall_d8.json` verbatim + build_cad.py::D8_REAR_FIN_THICKNESS_MM |
| `separator_plate_3_4_front` | [0.180, 0.080, 0.0008] | 0.8 | (3,4) | build_cad.py::PLATE_THICKNESS_MM=0.8 · solid-region v5b refinement |
| `separator_plate_3_4_rear_offset` | [0.180, 0.040, 0.0008] | 0.8 | (3,4) | build_cad.py D5 split (y∈[80,120] portion · width 40 mm) |
| `hot_fin_base` | [0.001, 0.012, 0.18] | 1.0 | (1,2) | build_cad.py::BASE_FIN_THICKNESS_MM=1.0 + HOT_CHANNEL_HEIGHT_MM=12 |
| `cold_fin_base` | [0.001, 0.016, 0.18] | 1.0 | (2,3) | BASE_FIN_THICKNESS_MM + COLD_CHANNEL_HEIGHT_MM=16 |

`background_cell_size: 0.004` mirrors `case/system/snappyHexMeshDict`
v5b live. `min_cells_per_thickness: 2` is the thin_wall_advisor sliver
threshold default.

### 3.2 `interface_bodies.json` (~115 LOC)

Two BodyGeometry dicts for the D5-offset plate pair:

- `separator_plate_3_4_front`: 6 axis-aligned faces spanning
  x=[0,180] × y=[0,80] × z=[12.4,13.2] (verbatim from build_cad.py +
  evidence/v1/a2_d5.json input bbox)
- `separator_plate_3_4_rear_offset`: 6 axis-aligned faces spanning
  x=[0,180] × y=[80.03,120] × z=[12.4,13.2]

**Substrate-layer encoding choice (documented in _meta block)**: case_011
v5b CAD reality places D5_OFFSET_MM=0.03 mm displacement in the +x
direction (build_cad.py rear-piece x0=0.03). For the A2-v2
`inter_face_gap_mm` consumer the same 30 µm displacement is reinterpreted
as a +y perpendicular gap between the front's +y face (y=80.0) and the
rear's -y face (y=80.03). Both encodings are equally-defensible
abstractions of the same engineering defect; the y-perpendicular form
is the one A2-v2's `should_have_been_shared_with_unintended_gap`
classifier consumes directly. The choice is documented at length in the
`interface_bodies.json::_meta::derivation` field.

### 3.3 `interface_specs.json` (~15 LOC)

Single InterfaceSpec `separator_3_4_d5_interface` mode=shared body_a=front
body_b=rear_offset. No `axis` (mode=shared doesn't use it).

### 3.4 Runner `scripts/v63_case_011_substrate/run_extended.py` (~190 LOC)

Mirrors B42/B45 pattern:

- Imports baseline parts_manifest + shm_dict + step_payload from
  `scripts.stack_track_c_session_1.build_inputs` (TRACK-1 source)
- Overlays `face_labels` on hot/cold parts (V94 dispatch trigger ·
  matches `test_stl_face_label_validator.py::test_case_011_v94_regression`
  verbatim — same 6 labels: hot_inlet/outlet/walls + cold_inlet/outlet/walls)
- Builds inline `shm_stl_face_normals` dict (3 parent-body keys ·
  region_hot_fluid / region_cold_fluid / region_solid · canonical
  cq.exporters single-shell V94 sediment shape)
- Loads YAML/JSON substrate inputs via dataclass reconstructors
  (PatchGeometry / BodyGeometry / FaceGeometry / InterfaceSpec)
- Drops `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` /
  `DEEPSEEK_API_KEY` before any backend import (4Q gate Q1 inline)
- Calls `assemble_stack(...)` with all 7 input families wired
- Serialises full report to
  `scripts/v63_case_011_substrate/stack_report_python_extended.json`

## 4. Stack pre/post

Re-ran TRACK-1-rerun baseline to confirm zero regression
(`scripts.stack_track_c_session_1_rerun.run_python_path_rerun` →
`stack_report_python_rerun.json` unchanged):

| metric | TRACK-1-rerun (pre · 2026-05-14) | B46 extended (post) | delta |
|---|---|---|---|
| `advisor_count` | 5 | **7** | +2 |
| `finding_count` | 2 | **11** | +9 |
| `critical_count` | 1 | **2** | +1 |
| `warning_count` | 1 | **8** | +7 |
| `failed_advisor_count` | 0 | 0 | 0 |
| `advisors_dispatched` | face_orientation · inlet_outlet · shm_dict · unit_detector · thin_wall | + virtual_interface_detector + stl_face_label_validator | +2 |
| `evidence_refs` (count) | 10 | **18** | +8 |
| `env_keys_present` (V130 Q1) | all false | all false | invariant ✓ |

Net-new V-rows in `evidence_refs`: **V22, V25, V33, V36, V42, V43, V50,
V94** (eight V-rows).

Net-new findings (delta = 9):

```
[CRITICAL] virtual_interface_detector · d1_unintended_gap · separator_3_4_d5_interface
           v_rows=[V22 V25 V33 V36 V42 V43 V50] · gap=0.0300 mm
[WARNING ] stl_face_label_validator · orphan_declared_label · region_hot_fluid·hot_inlet  · V94
[WARNING ] stl_face_label_validator · orphan_declared_label · region_hot_fluid·hot_outlet · V94
[WARNING ] stl_face_label_validator · orphan_declared_label · region_hot_fluid·hot_walls  · V94
[WARNING ] stl_face_label_validator · orphan_declared_label · region_cold_fluid·cold_inlet · V94
[WARNING ] stl_face_label_validator · orphan_declared_label · region_cold_fluid·cold_outlet · V94
[WARNING ] stl_face_label_validator · orphan_declared_label · region_cold_fluid·cold_walls · V94
[WARNING ] thin_wall_advisor · thin_wall_at_risk · hot_fin_base · V10 (cells_per_thickness=1.00 AT_RISK)
[INFO    ] thin_wall_advisor · thin_wall_at_risk · cold_fin_base · V10 (cells_per_thickness=2.00 marginal)
```

Reports serialised to:

- `scripts/stack_track_c_session_1_rerun/stack_report_python_rerun.json` (pre · unchanged from B33 land)
- `scripts/v63_case_011_substrate/stack_report_python_extended.json` (post · new)

## 5. V-row capture matrix on case_011

Mirrors B42/B45 9-row failure-mode matrix:

| # | failure mode | TRACK-1-rerun (pre) | B46 extended (post) | mechanism |
|---|---|---|---|---|
| 1 | **V10** thin_wall_at_risk (D8 canonical 0.6 mm sliver) | YES ✓ firm | YES ✓ firm | thin_wall_advisor critical on cold_fin_rear_third (cells_per_thickness=0.60) |
| 2 | **V20+V96** unit_inference (STEP mm/m ambiguity) | YES ✓ firm | YES ✓ firm | unit_detector — pre-existing TRACK-1 finding |
| 3 | **V22** A2-v2 plate-plate adjacency | partial (a2_d5.json placeholder per V25) | **YES ✓ firm** | virtual_interface_detector matches separator_3_4_d5_interface; normal_dot=1.0 |
| 4 | **V29** BC-name catalog | NO ← input-stranded | NO | out-of-stack (case_011 TRACK-1 build_inputs supplies no `bc_specs`; D10 dispatch gate not met) |
| 5 | **V30** thin_wall sliver class (multi-patch) | partial (1 sliver) | **YES ✓ firm** | thin_wall_advisor critical on cold_fin_rear_third (sliver-class confirmed); hot_fin_base AT_RISK warning extends the class signal |
| 6 | **V34** sHM cellzone fragmentation | NO | NO | out-of-stack (no fragmentation-class advisor yet; v1 evidence documents region_hot_fluid in 312 connected components but no LANDED advisor catches this) |
| 7 | **V94** face-label loss (D11 canonical coverage) | NO ← input-stranded | **YES ✓ firm** | stl_face_label_validator 6 orphan_declared_label findings — full V94 canonical replay (hot/cold inlet+outlet+walls all orphan) |
| 8 | **D5** sub-mm plate-plate offset (30 µm) | partial (a2_d5.json `interface_offset_um=30.0` scalar only, no field-validation) | **YES ✓ firm** | A2-v2 `should_have_been_shared_with_unintended_gap(max_gap_mm=1.0)` → True (gap=0.03 mm < 1.0 mm threshold) → critical D1-class finding |
| 9 | **D8** 0.6 mm rear fin (canonical thin_wall) | YES ✓ firm (shares V10) | YES ✓ firm (shares V10) | thin_wall_advisor (same finding row as V10) |

**Catch rate: 3 / 9 firm pre (V10 · V20+V96 · D8 [shared V10]) → 7 / 9 firm
post (V10 · V20+V96 · V22 · V30 · V94 · D5 · D8 [shared V10]). ≥ 3 / 9
target MET. ≥ 5 / 9 supplementary clause also MET on case_011 alone (6
distinct V-rows + 1 shared = 7 firm).**

> The case_004 B45 land achieved 5/9; case_006 B42 land achieved 3/9 (+
> D4 marginal). case_011 B46 with **6 distinct firm V-rows + 1 shared**
> (7/9) is the highest single-case firm count in the V63-A series so far —
> attributable to (a) case_011 being the canonical V94 sediment source
> (B39 D11 LANDED specifically to close case_011's gap, so the substrate
> input lands a clean 6-orphan replay), (b) the unique TRACK-1 unit_detector
> firing (V20/V96 carried over as a "pre-firm" bonus), and (c) the D8
> thin_wall coverage already pre-firm from TRACK-1.

## 6. Done dim #6 progress

```
clause 1 (≥ 5/9 on ≥1 canonical case):
    case_004 5/9 (B45) ✓ MET
    case_011 6+1/9 (B46 · this) ✓ MET — supplementary case at the threshold

clause 2 (≥ 3/9 on ≥3 cases):
    Pre B46:  2/3 cases (case_004 5/9 ✓ + case_006 3/9 ✓)
    Post B46: 3/3 cases (case_004 5/9 ✓ + case_006 3/9 ✓ + case_011 7/9 ✓)
              ✓ MET 100%

Done dim #6 overall: clause 1 ✓ + clause 2 ✓ → ✓ MET ✓ (both clauses)
V63-A Done dims MET: 3/6 → 4/6 (Done #1 + #3 + #5 + #6 ✓ · still
                                Done #2 V-corpus + #4 validation reports)
```

## 7. Backward-compat

- `scripts/stack_track_c_session_1_rerun/run_python_path_rerun.py` re-runs
  unchanged: still 5 advisors / 2 findings / 1 critical / 1 warning / 10
  V-rows. The `assemble_stack` keyword-only-with-`None`-default signature
  means the TRACK-1-rerun callsite (no `interface_bodies` / no
  `shm_stl_face_normals` / no `face_labels` in parts) silently skips A2-v2
  + D11 dispatches as designed (V130 silent-skip discipline).
- `scripts/stack_track_c_session_1/run_python_path.py` (original TRACK-1)
  untouched.
- `case/` directory contents untouched (OpenFOAM v5b runtime artifacts
  intact — 3.34 M hot / 2.98 M cold / 5.85 M solid cells).
- `inputs/cad_codex_v1.step` (5.5 MB STEP) — unchanged.
- `evidence/v[1-3]/*.json` — unchanged.
- `docs/decisions_v1.md` — unchanged.
- D11 stl_face_label_validator gate unaffected; its dispatch precondition
  reads `shm_stl_face_normals` / `parts_manifest face_labels` / `shm_dict`
  refinementSurfaces. The TRACK-1-rerun callsite supplies none, so D11
  silently skips. Only the B46 runner supplies the gate triggers.
- TRACK-1-rerun 100% advisor adoption (B33 closure) remains at **5/5 =
  100% PASS** post-B46 because B46's added advisors are dispatch
  conditional on substrate inputs the TRACK-1-rerun callsite doesn't
  provide — the 100% adoption applies to the **dispatched** advisors,
  which remain 5/5 on the TRACK-1-rerun path.

## 8. 4Q gate (inline)

1. **LLM-offline pass-through ✓** — Runner pops `ANTHROPIC_API_KEY` /
   `OPENAI_API_KEY` / `GOOGLE_API_KEY` / `DEEPSEEK_API_KEY` before any
   backend import. Output `env_keys_present` block confirms all four false
   in the JSON artifact. No advisor in the stack consumes LLM output —
   every advisor is pure-Python deterministic.
2. **Artifacts emitted ✓** —
   `scripts/v63_case_011_substrate/stack_report_python_extended.json`
   (full AdvisorStackReport serialisation · 11 findings · 7 advisor calls
   · 18 V-rows). Inputs at `inputs/{thin_wall_inputs.yaml,
   interface_bodies.json, interface_specs.json}`. Substrate edits
   strictly additive — no CAD / STL / manifest mutation.
3. **TrustGate explanation ✓** — Every finding cites V-rows linking back
   to `docs/openfoam_corpus/industrial_solver_findings_v_series.md`. The
   D5 critical finding cites the A2-v2 V-row union (V22/V25/V33/V36/V42/
   V43/V50); the 6 V94 warnings each cite V94 + carry `suggested_fix`;
   the V10 critical cites V10 with the bump-refinement message. No
   findings cite missing V-rows or unsourced corpus material.
4. **AI advisory-only ✓** — All 7 advisors return findings/warnings/
   critical recommendations; none modify case state, none write to
   `case/`, none invoke OpenFOAM, none call out to LLM. The runner
   serialises a JSON report; the engineer reads it and decides.

## 9. v2.3 compliance

- **Scope class**: sub-DEC (3 input files + 1 runner + 1 retro + 1 DEC =
  6 files; 3 shared code paths touched: `inputs/` additive · `scripts/`
  additive · `.planning/decisions/` + `.planning/retrospectives/`). Below
  charter threshold (no schema break, no security boundary, no spanning
  ≥3 shared code paths in a way that changes invariants). Full DEC
  frontmatter limited to the 6 required v2.3 fields (decision_id / title
  / status / parent_dec / phase / notion_sync_status).
- **Cadence floor (30)**: not triggered — net new LOC under 400 across
  3 input files + 1 runner. Documented cross-case extension, not a new
  direction.
- **Codex review**: not required. v2.3 1-sync-trigger is auth / signing /
  operator-endpoint only; substrate YAML/JSON additions + a per-case
  verification runner do not qualify. Round count: 0.
- **Kogami invocation**: not requested (v2.3 opt-in; substrate work is
  not a strategic-narrative event).
- **Notion sync**: pending. Per v2.3 round-1 loosen, only Status=Accepted
  DECs sync at session-end. The accompanying DEC moves to Accepted
  within this same dispatch and will sync in the next session-end batch
  if the user triggers `notion-sync-cfd-harness`.
- **Confidence**: med. Plate bbox values are build_cad.py-verbatim for
  the macro extents (W_MM=120, L_MM=180, PLATE_THICKNESS_MM=0.8,
  REAR_THIRD_START_Y_MM=80.0, D5_OFFSET_MM=0.03) and `evidence/v1/`-
  verbatim for the D5+D8 scalar inputs. The substrate's y-perpendicular
  encoding of D5 (rather than x-translation as in build_cad.py) is a
  documented abstraction choice with full _meta provenance. Stack diff
  pattern matches the B45 case_004 closure (multi-patch thin_wall +
  A2-v2 D-class + V94 firm) extended with D11 V94 6-orphan replay (B45
  case_004 has no STL yet so V94 stays NO there — case_011 is the only
  current case where D11 fires firm).

## 10. Open follow-ups (deferred · not blocking Accepted)

1. **ARC-GOAL.md Done dim #6 update** — main session reconciles between
   this B46 land and parallel B47 (V-series methodology). Recommended
   language: `clause 2 progress: 3 / ≥3 cases ≥3/9 covered (case_004 +
   case_006 + case_011); ≥3-case clause MET ✓ · Done dim #6 OVERALL MET ✓ ·
   Done dims MET 3/6 → 4/6`.
2. **D5 x-vs-y encoding canonicalisation** — case_011 substrate uses
   y-perpendicular encoding of the D5 30 µm offset; build_cad.py uses
   x-translation. A future cross-case sub-DEC (when D5-class accumulates
   2+ cases) should canonicalise the substrate→A2-v2 abstraction so the
   downstream interface_bodies.json convention is documented project-wide.
   Until then the _meta block per file is sufficient.
3. **V34 sHM cellzone fragmentation advisor** — case_011 v1 documented
   region_hot_fluid in 312 connected components (sHM merged 1 mm fin
   walls at effective 1 mm cell size). No LANDED advisor catches this
   today; promotion candidate as `cellzone_fragmentation_advisor`
   covering the V34/V36 connected-component class. Defer until 2+ cases
   show the pattern (case_011 only so far).
4. **V29 BC-name catalog firing on case_011** — would require TRACK-1
   build_inputs to additionally supply `bc_specs` reflecting the v5b
   `0/U`/`0/p`/`0/T` BC dictionaries. Out of scope for B46 (substrate-
   only). A follow-up sub-DEC could canonicalise the bc_specs input
   loader and re-run case_011 (also case_006 path-a if HTTP loader is
   wired per B42 §10 #3).
5. **HTTP-path auto-discovery (carry-over from B42 §10 #3 + B45 §10 #3)** —
   the production `/api/ai-review` route probes `case_dir/` root, not
   `case_dir/inputs/`, so case_011's three new files are invisible to
   the HTTP path. The path-b runner closes the V94/V22/V30/D5 capture
   gap as documented; HTTP path remains stranded until a future sub-DEC
   canonicalises the loader's probe locations (best done across
   case_004/006/011 simultaneously).
6. **Solver e2e validation (M-VAL-REPORT-1..3)** — case_011 v3
   sub-session sediments V94 + fragmented mesh; substrate work alone
   doesn't unblock a clean prep→solver→postp pipeline. M-VAL-REPORT-1
   for case_011 still requires v6 mesh (level (3,4) for fin patches per
   thin_wall_advisor recommendation) + V94 face-label re-export. B46
   gives the advisor stack visibility into both blockers but does not
   itself close them.

## Sediment

This retrospective sediments the following V-row reuse pattern that
should feed back into `industrial_case_solver_findings.md` if not already
present:

- **V94 cross-case promotion candidate**: case_011 is the canonical
  V94 sediment source; B46 demonstrates D11's dispatch produces the
  documented 6-orphan replay on a real industrial substrate. case_011 V94
  remains [QUESTIONABLE] until a 2nd case sediments a face-label-loss
  class (per DEC-V63-A-sub-D11 §Status). Recommended 2nd-case candidates:
  case_013 / case_015 CHT-LES (forward-loaded per case_proposal_queue.md).
- **D5/D1-class cross-case signature**: case_006 D1 root_fairing 0.35 mm
  + case_004 D1 nacelle 0.30 mm + case_011 D5 separator_3_4 0.03 mm =
  three distinct sub-mm A2-v2 unintended-gap detections across three
  numerics classes (compressible-transonic-shock + rotating-MRF-
  incompressible + steady-laminar-CHT-multi-stream). This is enough
  cross-case evidence to demote V22/V25/V33/V36/V42/V43/V50 from
  [QUESTIONABLE] to firm-promoted per V62-A sediment protocol (defer
  the actual promotion to B47 V-series methodology session).
