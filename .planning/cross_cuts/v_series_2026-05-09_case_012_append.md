# V-series append · case_012 HVAC supply diffuser · 2026-05-09

> Append-only update to `v_series_2026-05-08.md` and
> `v_series_case_011_append_2026-05-09.md`.
> case_012 is the **second case in Phase 1 of the industrial-extension
> batch** (case_011-020). First buoyantSimpleFoam re-deployment outside
> APU bay topology; closes Phase 1 alongside case_011.
> Pattern 6 inheritance: case_002a (compressible-buoyant-RANS root) →
> case_012 (commercial-office HVAC topology). NO new numerics root.

---

## V49 · A2 advisor `_run_shared` 9th cross-topology PASS — HVAC ceiling-diffuser room (case_012)

**Status**: open (PASS evidence; per V25 caveat, NOT field-validated for gap distance)
**Numerics class**: compressible-buoyant-RANS (case_002a inheritance, NOT new root)
**Pattern 6 ancestry**: case_002a (APU confined-bay) → case_012 (commercial-office room)

**Observation**: Exercising A2 (`virtual_interface_detector._run_shared`)
on the diffuser_face_plate ↔ ceiling pair (the 0.35 mm D1 gap) returns
`matched=True` with `bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`,
`normal_dot=1.0` — these are V25 placeholder fields, NOT measured.

```
A2_RESULT: patch=diffuser__ceiling_interface matched=True body_owner=ceiling
           bbox_overlap=1.0000 area_diff=0.0000 normal_dot=1.0000
           diagnostic="shared face on 'ceiling' (area=2.7e+07)"
```

This is the **9th cross-topology PASS** in the V22 / V33 / V36 / V42 / V43
chain. Topology classes covered:
1. APU confined-bay (case_002a/b)
2. CRM-HLS aerodynamic (case_003)
3. NREL Phase VI rotating-frame (case_004)
4. RAE M2129 internal duct (case_005)
5. ONERA M6 transonic external (case_006)
6. KCS ship hydro free-surface (case_007)
7. GLC305 IRT airfoil-mount (case_008)
8. Sandia Flame D combustion-burner (case_009)
9. DrivAer fastback vehicle-aero (case_010)
10. **HVAC ceiling-diffuser room (case_012)** ← NEW

(case_011 plate-fin HX has its own multi-stream conjugate-coupling A2
exercise; tracked separately in V47.)

**Status discriminator**: 9 algorithm-runs-cleanly PASSes do NOT
substitute for field-validation. Per V25, A2 v1 returns hardcoded
placeholder fields. A2-v2 sub-DEC pending (`inter_face_gap_mm`
addition).

**Verification pending**: A2-v2 sub-DEC implementation.
**To resolve**: A2-v2 lands AND case_012 v2 re-runs D1 falsification
with field-validated gap-distance API.

**Anti-pattern**: Do NOT propose `isSame()` fast-path (V2 lesson — re-
introduces the BREP topological-symmetry assumption that sHM-output
STLs do not satisfy).

---

## V50 · D7 (face-orientation defect) advisor gap — first project D7 injection (case_012)

**Status**: open (advisor gap surfaced; manual FreeCAD verification path established)
**Numerics class**: compressible-buoyant-RANS (case_002a inheritance)
**Defect class**: D7 (face-normal misalignment)

**Observation**: Codex case_012 brief injected D7 (louver_vane_2 rotated
38° from intended normal). This is the **first D7 in the project**;
no LANDED advisor exists for face-orientation defects.

Manual verification via FreeCAD `Face.normalAt()` + dot-product against
intended normal succeeds:

```
RESULT PASS: body=louver_vane_2 measured_normal=(0.6157,-0.7880,0.0000)
             intended_normal=(0.0000,-1.0000,0.0000) angle_deg=38.000
             expected_offset_deg=38.000 tol_deg=2.000 delta_deg=0.000
```

Control case `louver_vane_0` (un-defected, base 0°): measures 0.000°
offset → confirms intended-normal table is correct.

**Why it matters**: D7 is a class of defect that production CAD-export
pipelines reliably produce (see CATIA Z-axis flip cases in industry).
A4 advisor candidate (face-normal vs intended-normal dot-product check)
is a tractable extension to the geometry_ingest advisor stack.

**Status discriminator**: advisor-gap V-finding. Manual verification
path established but does not generalize to advisor coverage. Recommend
post-case_012 retro evaluate A4 advisor as Phase 2 / Phase 3 candidate.

**Verification pending**: 2+ Phase 1-4 cases inject D7 (012 + e.g.
016 cavity walls + 020 filter shell). If frequency holds, advisor sub-
DEC becomes high-priority.

**To resolve**: A4 advisor sub-DEC lands; case_012 v2 re-runs D7
falsification via the landed advisor instead of manual FreeCAD path.

---

## V51 · STEP wall-clock timestamp embedded in `FILE_NAME` line breaks byte-determinism — canonicalization workaround (case_012)

**Status**: confirmed (case_012 + case_002a + case_005 + case_011 all observed; same Codex CadQuery + cq.Assembly.save STEP path)
**Numerics class**: tooling (NOT solver-numerics)

**Observation**: cadquery 2.7.0 + OCP STEP exporter writes a
`FILE_NAME('Open CASCADE Shape Model','<wall-clock-timestamp>',...)` line.
Repeat invocations of the same `build_cad.py` produce different
wall-clock timestamps → different SHA-256 → byte-determinism check
fails despite geometrically-identical output.

**Workaround** (case_012 `scripts/build_cad.py:canonicalize_step()`):
post-write replacement of the timestamp line with a fixed sentinel
(`'1970-01-01T00:00:00'`). After canonicalization, two consecutive
runs produce byte-identical STEP files (sha256 verified).

**Why it matters**: byte-determinism is a Codex-protocol requirement
for the case-design contract (per
`.planning/methodology/codex_case_design_protocol.md`). Without
canonicalization, the determinism check fails despite the case being
correctly deterministic.

**Productizable artifact candidate**: `step_canonicalizer.py` —
extends to FILE_DESCRIPTION + AUTHOR fields + any other timestamp-
embedded metadata. Promote to `ui.backend.services.geometry_ingest`
as a pre-ingest pass on Codex-generated STEPs.

**Cross-link**: V14 (CATIA STEP `Import.insert()` name preservation)
addressed name preservation; V51 addresses byte-determinism — both
are cadquery/OCP STEP-export sediment.

---

## V52 · snappyHexMeshDict key `minMedialAxisAngle` (NOT `minMedianAxisAngle`) in OpenFOAM 2312 (case_012)

**Status**: **[VALIDATED] 2026-05-14** — A8 `shm_dict_validator` landed (DEC-V61-198-sub-A8). `ui/backend/services/geometry_ingest/shm_dict_validator.py` ships with 9-test suite; `test_v52_typo_regression_case_012` pins the case_012 v1 typo (parsed dict `addLayersControls.minMedianAxisAngle 90` → `typo_suspicion` warning, suggestion `minMedialAxisAngle`, edit-distance ≤ 2). Pre-flight check now catches the typo class before sHM consumes wall-clock minutes. Promotion gate met by V52 (typo) + V86 (orphan) cross-topology pair (V25→A2-v2 convention). Previously: confirmed (case_012 v1 sHM crash on first run; recovered after key rename).
**Numerics class**: tooling (NOT solver-numerics)

**Observation**: Writing `addLayersControls.minMedianAxisAngle 90;`
(typo: "Median" instead of "Medial") in snappyHexMeshDict produces:

```
--> FOAM FATAL IO ERROR: (openfoam-2312)
Entry 'minMedialAxisAngle' not found in dictionary
"/case/system/snappyHexMeshDict/addLayersControls"
```

OpenFOAM ESI 2312 expects `minMedialAxisAngle` (canonical name from the
`displacementMedialAxis` mesh-mover algorithm). The typo "MedianAxis"
appears in some legacy templates and StackExchange responses but does
NOT match the OF source.

**Why it matters**: catches a class of "looks-right but isn't" config-
key drift between OpenFOAM versions. Productizable as a pre-flight
config-key validator.

**Productizable artifact candidate**: `snappy_hex_mesh_dict_validator.py`
— catches typo-class drift + version-mismatch keys before solver
invocation, fails fast with named-key suggestions.

---

## V53 · Codex CAD pattern emits 3D-solid supply/return bodies → sHM treats as walls → inlet/outlet patches not realized (case_012)

**Status**: confirmed (case_012 v1; first observation; Codex case-design protocol class)
**Numerics class**: tooling + CAD-protocol (NOT solver-numerics)
**Defect class**: methodology — Codex CAD generator semantics

**Observation**: case_012 Codex `build_cad.py` registered `supply_inlet`
and `return_outlet` as **3D solid boxes** (180×180×35 mm and 520×20×320 mm
respectively) in the cq.Assembly. After `01_extract_stl.py` exports them
as triangulated STLs and `02_setup_case.py` registers them in
snappyHexMeshDict's `geometry { triSurfaceMesh; name X; }` block with
`patchInfo { type patch; }`, snappyHexMesh **treats both as closed
surfaces inside the fluid region** → walls. Resulting mesh has 16 patches
(no supply_inlet, no return_outlet). The room is effectively **sealed**.

```
--> FOAM FATAL ERROR: surfaceFieldValue massBalance: patch(supply_inlet):
    No matching patches: (supply_inlet)
    Known patch names: 16 (ceiling, floor, wall_*, diffuser_face_plate,
    louver_vane_*, occupant_*, equipment_patch)
```

OpenFOAM's `0/U.boundaryField.supply_inlet` is silently ignored at
`buoyantSimpleFoam` startup (the patch doesn't exist). Solver runs as
**natural-convection-only** (heat sources drive ρ gradient → buoyant
recirculation; no through-flow). v1 ADPI / throw-distance / dumping
metrics are meaningless against the original HVAC engineering question
because no supply jet ever entered.

**Root cause**: Codex case-design protocol does not currently
distinguish between:
- **3D solid bodies** (occupants, equipment, walls — should become walls)
- **Thin face geometries** (supply inlets, returns — should become
  bounded patches OR carved face-zones)

The existing protocol treats both as `cq.Workplane().box(...)` →
`Assembly.add()` → STEP solid → STL → sHM closed-surface. For
inlet/outlet, this is wrong.

**Fix family**:

| Fix # | Approach | Effort | When |
|-------|----------|--------|------|
| #1 (cheap) | createPatch after sHM: select faces inside supply_inlet bbox currently belonging to a wall patch; move into a new `supply_inlet` patch | ~50 LOC additional script | v1.5 — same-mesh re-run |
| #2 | Codex CAD generator emits supply/return as **thin 2D rectangles** (e.g., `cq.Workplane("XY").rect(L,W).extrude(0.001)` — 1 mm thick); sHM treats as openings | Update Codex case-design protocol + regenerate STEP | v2 — re-run from CAD step |
| #3 | Codex CAD generator emits supply/return as **named faceZones** via `cq.Assembly.add(face, name=...)` | Untested cadquery API path; risky | v3 — research |

**Why it matters**: this is a high-frequency Codex CAD pattern. case_011
(plate-fin compact HX) likely has the same issue with hot/cold inlets;
needs cross-check. **All Phase 1 cases should audit their patch list
post-sHM** to confirm inlet/outlet patches exist.

**Productizable artifact candidate**: `codex_cad_inlet_outlet_audit.py`
(~80 LOC) — post-mesh check that compares parts_manifest.yaml roles
(supply / return) against `constant/polyMesh/boundary` and emits
warnings + suggested createPatch dict if gaps found.

**Cross-link**:
- V14 (CATIA STEP `Import.insert()` name preservation) — different cadquery/OCP issue
- V51 (STEP timestamp determinism) — sibling Codex/cadquery sediment
- DEC-V61-198 — APU bay strategic pivot Pillar 5 — case-fleet protocol
- `codex_case_design_protocol.md` — needs amendment to specify
  inlet/outlet emission convention

**Honest evidence statement**: case_012 v1 evidence is for
**natural-convection-only sealed-room** physics, NOT HVAC-with-supply-jet.
ADPI / throw / dumping metrics CANNOT be compared to ASHRAE 55 design
table for the original brief; they are reported in REPORT.md v1 to
characterize the natural-convection signal, not to verdict-pass the
HVAC question.

**v1.5 / v2 plan**: apply Fix #1 or Fix #2; re-run; produce real HVAC
evidence. v1 closes with this V-finding documented; Phase 1 close
includes V53 in the harvest cycle 003.

---

## V-series summary table (case_012 contributions)

| V-row | Status | Class | Mechanism |
|-------|--------|-------|-----------|
| V49 | open (PASS) | A2 advisor | 9th cross-topology PASS for `_run_shared`; field-validation pending V25 |
| V50 | open (advisor gap) | D7 face-orientation | first D7 injection; no LANDED advisor; A4 candidate flagged |
| V51 | confirmed | tooling | STEP timestamp canonicalization for byte-determinism |
| V52 | **[VALIDATED] 2026-05-14** (A8 landed) | tooling | sHM `minMedialAxisAngle` (NOT MedianAxis) in OF 2312 |
| V53 | **confirmed** | **CAD-protocol** | **Codex 3D-solid supply/return → sHM walls; inlet/outlet patches not realized; sealed-room v1** |

## S-series candidates (post-case_012)

S22 (HVAC stratified-room steady oscillation): same root as S10
(pseudo-steady not fully steady), but specific to room-scale Ra ~
1e9-1e10 mixed convection. Promote if v1 baseline shows residual
oscillation pattern matching S10 mechanism.

S23 (occupied-zone field-averaging via cellZone topoSet): canonical
pattern for ASHRAE 55 ADPI / IEA Annex 20 design-table comparison.
Bundle controlDict function-object setup + topoSetDict + sampleDict
into a Phase 1 deliverable.

## Artifact extraction candidates

A6 — `adpi_post_processor.py` (~150 LOC): consume `postProcessing/sample/`
output; compute ADPI / throw distance T_50 / dumping criterion.
Generalizes case_012 v1's `05_postprocess.py`.

A7 — `step_canonicalizer.py` (~80 LOC): pre-ingest pass on Codex-
generated STEPs to eliminate wall-clock timestamps. Resolves V51.

A8 — `snappy_hex_mesh_dict_validator.py` (~120 LOC): pre-flight key
validation against OpenFOAM-version-pinned canonical key set. Resolves
V52 class.

(Optional) A4 — `face_orientation_advisor.py` (~200 LOC): manual D7
verification path generalized as advisor. Conditional on 2+ Phase 1-4
D7 injections (V50 dependency).

## Cross-references

- `case_012_hvac_supply_diffuser.md` — case profile
- `industrial_case_solver_findings.md` — V-series master index
- `solver_convergence_playbook.md` — S-series (S1-S21 + candidates)
- `knowledge_status_convention.md` — [QUESTIONABLE] grammar
- `case_011_020_industrial_extension_roadmap_2026-05-08.md` — Phase 1 batch plan
