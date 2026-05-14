# RETRO · case_006 ONERA M6 substrate extension · V63-A Tier 2 carry-over #3

> V63-A Tier 2 · M-CASE-006-SUBSTRATE (DEC-V63-A-sub-M-CASE-006-SUBSTRATE).
> Driver: TRACK-3-rerun retro
> `.planning/retrospectives/2026-05-14_stack_track_c_session_3_rerun_case_006.md`
> §"V-row truth-capture rate" — case_006 V-row catch was 1 / 9 (V29 via
> D10) with V30 + D1 + D4 sitting in the "input-manifest substrate-not-extended"
> bucket. This retro lands three substrate-side input files under
> `case_006/inputs/` so the now-LANDED `thin_wall_advisor` (V10) and
> A2-v2 `virtual_interface_detector` (V20/V22/V25/V33/V36/V42/V43/V50)
> dispatches can fire end-to-end, pushing the catch rate to **3 / 9
> firm + D4 marginal = 3-4 / 9**.

---

## §1 Goal

Close V63-A Tier 2 carry-over #3:

1. Synthesize three input files under `case_006/inputs/` derivable from
   existing `evidence/v1/face_geometry.json` + `inputs/parts_manifest.yaml`
   + `inputs/defect_manifest.yaml`:
   - `thin_wall_inputs.yaml` (V10 substrate for `thin_wall_advisor`)
   - `interface_bodies.json` (BodyGeometry list for A2-v2)
   - `interface_specs.json` (InterfaceSpec list for A2-v2)
2. Verify the route gap closes — `assemble_stack(...)` on case_006 must
   now dispatch `thin_wall_advisor` + `virtual_interface_detector`
   alongside the six TRACK-3-rerun-confirmed advisors.
3. Push V-row truth capture from 1 / 9 → ≥ 3 / 9 against the documented
   9 case_006 failure modes (V26 / V27 / V28 / V29 / V30 / V31 / V32 / D1 / D4).
4. Done dim #6 (V-row truth capture) advances from "1 / 9, silent-under-
   coverage active" → "3-4 / 9, silent-under-coverage further partially
   closed". Do **not** update ARC-GOAL.md (main session reconciles to
   avoid B43 parallel-arc rebase contention).

Constraints (dispatch + v2.3 governance):

- substrate edits limited to `inputs/` (3 new files; no case_dir / STEP /
  STL / manifest changes)
- no `assemble_stack` source edits
- no advisor / catalog source edits
- no Notion sync (sub-DEC stays local until Accepted; v2.3 round-1
  loosen only syncs Accepted DECs)
- no Codex review (substrate-side YAML/JSON additions are not a v2.2
  security-boundary sync trigger; not auth / signing / operator endpoint)
- no Kogami (v2.3 opt-in)
- 3 atomic commits each carrying `confidence: med`

---

## §2 face_geometry.json source survey

`evidence/v1/face_geometry.json` (9248 bytes) declares 3 bodies with
explicit per-face geometry under `unit: mm`:

| body | n_faces | bbox_xyz [mm] | role in case |
|---|---|---|---|
| `root_fairing_pad` | 6 | 22.0 × 16.0 × 7.0 | D1 candidate (gap +x face at x=91.61) |
| `root_fairing_cover` | 6 | 22.0 × 16.0 × 7.0 | D1 candidate (gap -x face at x=91.96) |
| `tip_cap_sliver` | 5 | 0.18 × 3.0 × 0.45 | V30 / D4 candidate (0.18 mm thinness) |

The 91.96 − 91.61 = 0.35 mm separation between the pad's +x face and the
cover's -x face matches `defect_manifest.yaml D1.measurement.claimed_gap_mm`
verbatim. The sliver's bbox-min direction (0.18 mm) matches
`defect_manifest.yaml D4.measurement.claimed_thickness_mm`. The two
defect-manifest claims are therefore externally re-verified by reading
`face_geometry.json` directly — no FreeCAD invocation needed for the
substrate-extension landing.

`face_geometry.json` does **not** list `wing_surface_reference` or
`tip_cap` (the geometry-validation pass only emitted defect-class bodies).
For the thin-wall advisor those two had to be derived from
`parts_manifest.yaml::geometry_reference` (span_mm 1196.3, mac_mm 646.07,
taper_ratio 0.562) using
`chord_root = 2 * MAC / (1 + λ) = 826.9 mm` and an ONERA M6 nominal
`t/c = 0.10` for root thickness (~82.7 mm). These are *informed
estimates*, not verbatim measurements; they exist so the advisor returns
"no risk" for the wing surfaces rather than skipping them silently.

---

## §3 Synthesis — what landed under `case_006/inputs/`

### 3.1 `thin_wall_inputs.yaml` (62 LOC incl. provenance comment)

```yaml
patches:                              # 5 entries — 3 from face_geometry, 2 derived
  - {name: wing_surface_reference, bbox_dimensions: [826.9, 1196.3, 82.7]}
  - {name: tip_cap,                bbox_dimensions: [50.0, 50.0, 8.0]}
  - {name: root_fairing_pad,       bbox_dimensions: [22.0, 16.0, 7.0]}
  - {name: root_fairing_cover,     bbox_dimensions: [22.0, 16.0, 7.0]}
  - {name: tip_cap_sliver,         bbox_dimensions: [0.18, 3.0, 0.45]}

refinement_levels:                    # mirrors build_inputs.py shm_dict
  wing_surface_reference: [4, 5]
  tip_cap:                [4, 5]
  root_fairing_pad:       [3, 4]
  root_fairing_cover:     [3, 4]
  tip_cap_sliver:         [1, 2]

background_cell_size: 20.0            # mm; effective cell at level 5 = 0.625 mm
min_cells_per_thickness: 2            # advisor default
```

Key derivation decision: `background_cell_size = 20.0 mm` so that level-5
cells (the wing's max refinement) are 0.625 mm — consistent with the
chord/1000 resolution target for transonic Cp at AGARD stations on a MAC
~646 mm wing. The tip_cap_sliver patch at level [1, 2] thus sees
effective cell 5.0 mm against estimated thickness 0.18 mm, yielding
cells_per_thickness = 0.036 (well below `_SEVERITY_CRITICAL_RATIO = 1.0`).

### 3.2 `interface_bodies.json` (~120 LOC incl. provenance)

Pads + covers (12 faces total) copied verbatim from
`face_geometry.json::bodies['root_fairing_pad' | 'root_fairing_cover']`.
Schema mirrors `virtual_interface_detector.BodyGeometry` dataclass; the
runner under `scripts/v63_case_006_substrate/run_extended.py` reconstructs
the dataclass instances at dispatch time. `tip_cap_sliver` is omitted —
D1 is a 2-body gap defect, only pad + cover relevant.

### 3.3 `interface_specs.json` (one spec)

Single `InterfaceSpec(patch_name='root_fairing_d1_interface', mode='shared',
body_a='root_fairing_pad', body_b='root_fairing_cover')`. The detector
finds the pad's +x face vs cover's -x face, normal_dot = -1, area match,
bbox overlap ~zero → matched=True, inter_face_gap_mm = 0.35. Classifier
`should_have_been_shared_with_unintended_gap(threshold=1.0)` flags D1.

`_meta` block kept under a leading-underscore key so iterating bodies /
specs skips it; this is the same pattern used in `interface_bodies.json`
and is consumed by the runner's `if key.startswith("_")` guard.

---

## §4 Verification — assemble_stack pre vs post

### 4.1 Pre (TRACK-3-rerun baseline · re-ran 2026-05-15)

`scripts/stack_track_c_session_3_rerun/run_python_path.py`, unchanged
substrate:

```
advisor_count:        6
finding_count:        10
critical_count:       10
warning_count:        0
failed_advisor_count: 0
advisors_dispatched:  ['bc_type_name_validity_advisor',
                      'face_orientation_advisor',
                      'inlet_outlet_validator',
                      'shm_dict_validator',
                      'thermo_polynomial_range_advisor',
                      'unit_detector']
evidence_refs:        12 V-rows (V20 V29 V41 V52 V79 V81 V86 V87 V93 V96
                      V99 V100)
env_keys_present:     all four false (V130 4Q-Q1 ✓)
```

### 4.2 Post (substrate-extended)

`scripts/v63_case_006_substrate/run_extended.py`, loads the 3 new input
files alongside the TRACK-3-rerun parts_manifest / shm_dict / thermo_dict
/ step_path:

```
advisor_count:        8                     (+2: thin_wall_advisor, virtual_interface_detector)
finding_count:        12                    (+2)
critical_count:       12                    (+2)
warning_count:        0
failed_advisor_count: 0
advisors_dispatched:  ['bc_type_name_validity_advisor',
                      'face_orientation_advisor',
                      'inlet_outlet_validator',
                      'shm_dict_validator',
                      'thermo_polynomial_range_advisor',
                      'thin_wall_advisor',          ← NEW
                      'unit_detector',
                      'virtual_interface_detector'] ← NEW
evidence_refs:        20 V-rows (was 12; added V10 V22 V25 V33 V36 V42 V43 V50)
env_keys_present:     all four false (V130 4Q-Q1 ✓)
```

### 4.3 New findings (delta = 2)

| # | source_advisor | severity | code | location | V-rows |
|---|---|---|---|---|---|
| 11 | `virtual_interface_detector` | critical | `d1_unintended_gap` | `root_fairing_d1_interface` | V22 V25 V33 V36 V42 V43 V50 |
| 12 | `thin_wall_advisor` | critical | `thin_wall_at_risk` | `tip_cap_sliver` | V10 |

Finding #11's V-row union (V22+V25+V33+V36+V42+V43+V50) is the cross-case
A2-v2 evidence list — confirms the same D1 detector that fires on
case_003 / 004 / 005-v2 / 007-011 sub-mm gaps now also fires on case_006
once the substrate carries an `InterfaceSpec`.

Finding #12 reports `estimated_thickness=0.18 mm`, `effective_cell_size=5.0 mm`
(level_max=2 → 20 / 2^2 = 5), `cells_per_thickness=0.036`,
`severity=critical`. Matches V30 documented failure mode exactly.

### 4.4 Diff diagonal

| metric | pre (TRACK-3-rerun) | post (this retro) | delta |
|---|---|---|---|
| advisor_count | 6 | 8 | +2 |
| finding_count | 10 | 12 | +2 |
| critical_count | 10 | 12 | +2 |
| evidence_refs (V-rows in union) | 12 | 20 | +8 |
| documented-failure capture | 1 / 9 (V29) | 3 / 9 firm + D4 marginal | +2 firm |
| silent-under-coverage status | partial (V30 + D1 input-stranded) | further-partial (V30 + D1 closed; V26/V27/V28/V31/V32 still out-of-stack) | step-improvement |

---

## §5 V-row capture matrix vs 9 documented case_006 failure modes

(Same enumeration as TRACK-3-rerun §5 — 7 V-rows + 2 D-class defect IDs.)

| failure mode | TRACK-3 | TRACK-3-rerun | this retro (post-substrate) | reason for current state |
|---|---|---|---|---|
| V26 Codex CAD off-by-half-width | NO | NO | **NO** | Codex-protocol issue; out-of-stack scope; no `codex_output_validator` advisor exists nor planned |
| V27 rhoCentralFoam adjustTimeStep | NO | NO | **NO** | No fvSchemes / fvSolution advisor in stack; S15 candidate is V-row level only |
| V28 rhoCentralFoam DILU preconditioner | NO | NO | **NO** | Same — no matrix-solver-class advisor |
| V29 BC-name validity | NO | YES ✓ | **YES ✓** | D10 LANDED B33; TRACK-3-rerun confirmed end-to-end; unchanged |
| **V30 thin_wall 0.18 mm sliver** | NO | NO ← input-stranded | **YES ✓** | `thin_wall_inputs.yaml` lands; `thin_wall_advisor` dispatches on tip_cap_sliver (0.18 mm, level [1,2], BG 20 mm) → critical |
| V31 Codex defect→advisor mapping | NO | NO | **NO** | Protocol-revision-level issue; out-of-stack scope |
| V32 Tier-1 NASA Glenn HTTP 500 | NO | NO | **NO** | Infra-level finding; out-of-stack scope |
| **D1 root_fairing sub-mm gap** | partial | partial ← input-stranded | **YES ✓** | `interface_bodies.json` + `interface_specs.json` land; A2-v2 detector returns inter_face_gap_mm=0.35; classifier flags D1 critical |
| D4 tip_cap_sliver 0.18 mm | partial | partial ← input-stranded | **YES ✓ (marginal)** | `thin_wall_advisor` fires on tip_cap_sliver at 0.18 mm. Note: the canonical "expected advisor" per defect_manifest is `geometry_surgery.decimate_to_tier` (different remediation path); `thin_wall_advisor` catches the same substrate-level failure via the thinness-vs-cell-size route. Counted as marginal because the canonical advisor is a different surgery class |

**Capture rate: 1 / 9 (V29 firm) → 3 / 9 (V29 + V30 + D1 firm) + D4
marginal. Hard target ≥ 3 / 9: MET.** The 5 remaining no-catch rows
(V26 / V27 / V28 / V31 / V32) are all classified out-of-stack scope per
TRACK-3-rerun §5; closing them requires new advisor land or upstream
protocol revision, not substrate work.

### Silent-under-coverage failure mode status

- **Closed for V29** (D10 catalog · permanent).
- **Closed for V30** (thin_wall_inputs.yaml substrate-extended · permanent for case_006).
- **Closed for D1** (interface_bodies.json + interface_specs.json substrate-extended · permanent for case_006).
- **Marginal-close for D4** (thin_wall_advisor fires on substrate; canonical
  geometry_surgery advisor not yet LANDED — close-on-LAND tracked under
  separate sub-DEC if scoped in V63-A).
- **Still open for V26 / V27 / V28 / V31 / V32** — out-of-stack scope per
  TRACK-3-rerun retro §5; not driven by substrate work.

---

## §6 4Q gate offline confirmation

Q1 (LLM-offline): the runner pops `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
/ `GOOGLE_API_KEY` / `DEEPSEEK_API_KEY` from `os.environ` **before** any
backend import. Report's `env_keys_present` block confirms all four false
in both pre and post runs. No advisor or finding produced under this
retro depends on an LLM call.

Q2 (artifacts emitted): post-run `stack_report_python_extended.json`
serialized to `scripts/v63_case_006_substrate/`. Pre-run
`stack_report_python.json` already at `scripts/stack_track_c_session_3_rerun/`.
Both are byte-stable on re-run (no timestamp / random-ID fields in the
output schema).

Q3 (TrustGate explanation): the 2 new findings carry a non-empty
`message` field rendered by the dispatch normalizer
(`_normalize_thin_wall` and `_normalize_interfaces`). They surface as
critical so the eventual UI / report renderer treats them as
adoption-track findings rather than silent noise.

Q4 (AI advisory-only): the 2 new advisors are pure-Python rule-based
detectors (`thin_wall_advisor` uses bbox-min as thickness estimator +
cell-size arithmetic; `virtual_interface_detector` uses face-geometric
overlap + normal dot product). Neither calls an LLM nor an external
inference service. Both produce structured findings the user adjudicates;
no auto-remediation.

All four pillars confirmed ✓.

---

## §7 Done-dim #6 advance (V-row truth capture)

V63-A ARC-GOAL.md Done-dim #6 (V-row truth-capture rate on case_006) was
recorded as 1 / 9 firm after TRACK-3-rerun. This retro advances the
counter to **3 / 9 firm + D4 marginal** at substrate-land. ARC-GOAL.md
itself is **not** edited under this dispatch — per task instructions,
the main session reconciles between this carry-over-#3 land and the
parallel M-CASE-EXT-1 (B43) land to avoid `git pull --rebase` contention.

Recommend the next ARC-GOAL edit (main-session-side) reflect:

```
Done dim #6: V-row truth-capture rate (case_006)
  TRACK-3:            0 / 9
  TRACK-3-rerun:      1 / 9 (V29)
  M-CASE-006-SUBSTRATE (this): 3 / 9 firm + D4 marginal (V29, V30, D1, D4-marginal)
  Status:             ≥3/9 target MET; remaining 5 are out-of-stack scope
                      (V26/V27/V28/V31/V32 require new-advisor land or upstream
                      protocol revision, not substrate work)
```

---

## §8 Counter telemetry (v2.3 nature)

- `autonomous_governance_counter_v61` increment: +1 (this sub-DEC ratifies
  autonomous_governance=true, no external gate).
- `autonomous_governance: true`. No external gate dependency; substrate-
  side files synthesized from already-present case artifacts.
- Codex round: 0 (no review triggered — substrate YAML/JSON additions
  are not a v2.2 security-boundary 1-sync-trigger).
- Kogami invocation: 0 (v2.3 opt-in; not requested).

---

## §9 Hidden-defects-caught-post-R3 (TRACK-3-rerun §addendum honored)

None. This retro is a substrate-extension validation, not a code-path land;
there is no R0..R3 review chain associated. Any post-merge defect surfacing
later (e.g., a downstream consumer of `interface_bodies.json` schema-
breaking) would be classified post-R3 blind-spot and folded into a
follow-up retro per RETRO-V61-053 addendum.

---

## §10 Surface-scan trailer

Pre-implementation surface scan ran on three target files:

```
$ ls ~/Desktop/case_006_onera_m6_transonic/inputs/ | grep -E "thin_wall_inputs|interface_bodies|interface_specs"
(empty — confirmed none exist)
```

No prior implementation found. Commits carry `Surface-scan: clean`.

---

## §11 Backward-compat

- `scripts/stack_track_c_session_3_rerun/run_python_path.py` continues to
  pass `assemble_stack` without the 3 new arg blocks (kwargs are keyword-
  only with `None` defaults). Re-confirmed at the top of §4.1 — same
  6-advisor / 10-finding output as TRACK-3-rerun retro §3.
- `case/` directory untouched; existing `01_blockMesh.log` /
  `02_snappyHexMesh.log` / `03_checkMesh.log` / `rhoCentralFoam.log` /
  `REPORT.md` unchanged.
- `parts_manifest.yaml`, `defect_manifest.yaml`, `cad_codex_v1.step` —
  unchanged.

---

## §12 Open questions for V63-A reconcile (main session)

1. Should D4 marginal capture be promoted to firm by adding the
   `geometry_surgery.decimate_to_tier` advisor under V63-A Tier 2? Currently
   `thin_wall_advisor` covers the same substrate-level failure via a
   different remediation route — sufficient for production triage, but the
   canonical defect_manifest map still points to a not-yet-LANDED advisor.
2. Should the `_meta` block convention (leading-underscore key in JSON
   maps) be hoisted to a project-wide schema doc, given two new JSON inputs
   now use it? Recommend deferred to M-CASE-EXT-N where additional cases
   add similar substrate files; premature to codify with N=1 use.
3. Should `thin_wall_inputs.yaml` add a `_meta` section like the JSON
   files? Currently the YAML uses a comment block instead. Either form
   serializes losslessly; recommend keeping the existing comment form (no
   schema mutation needed; YAML readers ignore comments cleanly).
