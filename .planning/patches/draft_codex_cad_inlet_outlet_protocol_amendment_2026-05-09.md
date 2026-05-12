# DRAFT patch · Codex case-design protocol amendment · inlet/outlet emission

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: harvest cycle 003 · 2026-05-09
> **Target**: main session for landing as governance-rule-change
> **Scope**: amendment to `methodology/codex_case_design_protocol.md` +
> retroactive audit of dispatched cases 013-020 + post-mesh audit
> script (A8-class)
> **Triggers**: V53 (case_012) — Codex emitted supply_inlet + return_outlet
> as **3D solid bodies**; sHM treated them as walls; resulting mesh has
> no inlet/outlet patches; v1 ran as natural-convection-only sealed-room

## Why this patch

case_012 v1 honest-evidence statement (per V53 in append file):

> case_012 v1 evidence is for **natural-convection-only sealed-room**
> physics, NOT HVAC-with-supply-jet. ADPI / throw / dumping metrics
> CANNOT be compared to ASHRAE 55 design table for the original brief;
> they are reported in REPORT.md v1 to characterize the natural-
> convection signal, not to verdict-pass the HVAC question.

**Root cause**: Codex case-design protocol does not currently
distinguish between:
- **3D solid bodies** (occupants, equipment, walls — should become
  walls when STL'd into sHM)
- **Thin face geometries** (supply inlets, returns — should become
  bounded patches OR carved face-zones)

Both currently emit as `cq.Workplane().box(...)` →
`Assembly.add()` → STEP solid → STL → sHM closed-surface. For
inlet/outlet, this collapses the patch entirely.

**Risk surface**: every Codex CAD generator with through-flow
boundaries (case_013 pump, case_015 T-junction, case_017 pin-fin,
case_018 cyclone, case_019 mixer, case_020 filter) is at risk of
the same failure mode. Phase 2-4 sediment may have to be redone.

## Surface scan

Already documented in case_012 V53 append. Existing main-project
modules touched:
- `ui/backend/services/geometry_ingest/patch_detector.py` — could be
  extended to flag missing-inlet/outlet patches post-mesh
- `ui/backend/services/geometry_ingest/health_check.py` — currently
  watertight-only; could add patch-presence check

## Recommended amendment to `codex_case_design_protocol.md`

### New section: § "Inlet/outlet boundary geometry emission"

> When Codex's engineering brief specifies fluid through-flow
> boundaries (supply, return, inlet, outlet), the CAD generator MUST
> emit those boundaries as **carved face-zones** OR **thin extrusions**,
> NOT as 3D solid bodies that snappyHexMesh will treat as walls.
>
> **Approved emission patterns**:
>
> 1. **Thin-extrusion (cheapest, most-portable)**: emit the boundary
>    as `cq.Workplane(<plane>).rect(L, W).extrude(0.001)` — 1 mm
>    thick. sHM treats this as an opening to the fluid region;
>    `01_extract_stl.py` exports the two faces; `snappyHexMeshDict`
>    `geometry { triSurfaceMesh; }` block + `patchInfo { type patch; }`
>    correctly registers as a bounded patch.
>
> 2. **createPatch carve (post-mesh)**: emit the boundary location as
>    metadata in `parts_manifest.yaml`:
>    ```yaml
>    boundary_zones:
>      - name: supply_inlet
>        type: patch
>        bbox: [x_min, y_min, z_min, x_max, y_max, z_max]
>        carve_from_patch: ceiling
>    ```
>    Pipeline scripts then run `createPatchDict` post-sHM to carve
>    faces from the parent wall patch.
>
> 3. **Named faceZones (cadquery API)**: experimental; do not use
>    until verified.

### New mandatory deliverable check

Add to validation checklist in protocol § "Main session validation
step":

> 7. **Boundary-zone audit**: for every entry in
>    `parts_manifest.yaml` with `role: supply` or `role: return` or
>    `role: inlet` or `role: outlet`, verify the CAD generator emits
>    EITHER:
>    - A thin-extrusion body (≤ 5 mm in the boundary-normal direction
>      AND with a `boundary_emission: thin_extrusion` annotation),
>      OR
>    - A `boundary_zones` entry in the parts manifest specifying the
>      bbox + parent patch for createPatch carve
>    If neither: validation FAIL; Codex must respin with the
>    inlet/outlet emission pattern fixed.

### Pre-flight validator script (A-class candidate)

`ui/backend/services/geometry_ingest/codex_cad_inlet_outlet_audit.py`
(~80 LOC). Reads parts_manifest.yaml + parts_manifest's bbox tags +
post-sHM `constant/polyMesh/boundary` and emits warnings + suggested
createPatch dict if gaps found.

This is the workaround for already-shipped Codex CAD that has the
problem; the protocol amendment is the prevention going forward.

## Retroactive audit recommended (Phase 1 cases)

Before Phase 2 (case_013/014) sediment lands:

1. **case_011 v1 sandbox audit**: verify hot/cold inlet patches exist
   in `case/constant/polyMesh/boundary` after sHM. case_011 used
   3-region splitMeshRegions which may have side-stepped this — but
   verify, don't assume. (The case_011 V47-V50 append doesn't mention
   inlet/outlet protocol; that's a gap to close.)
2. **case_012 v1 sandbox**: already known to have failed (V53
   surfaces this); v1.5 fix path documented in append. Apply Fix #1
   (createPatch carve) to land v1.5 evidence.
3. **case_013-020 dispatched kickoffs**: scan each Codex deliverable
   2 (CadQuery script) for `boundary_emission: thin_extrusion`
   annotation OR `boundary_zones` parts_manifest section. Cases
   missing both are at risk.

## Cross-references

- V53 — case_012 V-finding (root V-row for this patch)
- `methodology/codex_case_design_protocol.md` — target file for amendment
- `methodology/case_kickoff_prompt_template.md` — companion update
  to mention "verify inlet/outlet patch presence before declaring v1
  complete"
- DEC-V61-198 — APU bay strategic pivot (Pillar 5, case-fleet protocol)
- `patches/draft_a8_shm_dict_validator_2026-05-09.md` — sibling A-class
  pre-flight validator pattern (validation done in main project, not
  case-locally)

## Open questions

- Is the existing `parts_manifest.yaml` schema rich enough to carry
  `boundary_zones`, or does it need a schema bump?
- Should the audit script be wired into `make all` for every case
  sandbox, or kept as a manual main-session check?
- For dispatched-but-not-sediment cases (013-020): do we redispatch
  Codex for a rev-with-correct-emission-pattern, or wait for
  sub-sessions to surface the issue case-by-case?
