# V-series append · case_011 plate-fin compact HX · 2026-05-09

> Append-only update to `v_series_2026-05-08.md`.
> case_011 is the **first case in Phase 1 of the industrial-extension batch**
> (case_011-020). Multi-stream CHT root extension to the Pattern 6 inheritance
> graph. New V-findings + S-playbook candidates surfaced during v1 setup.

---

## V47 — `chtMultiRegionFoam` multi-stream first-time-startup BC bookkeeping

**Status**: open
**Numerics class**: steady-laminar-CHT-multi-stream (NEW root)
**Pattern 6 ancestry**: case_002b (single-stream CHT) → case_011 (2-fluid + 1-solid)

**Observation**: Setting up `chtMultiRegionFoam` for **two fluid regions
+ one solid region** (vs. case_002b's 1 fluid + 6 solid extrusions)
requires deliberate per-region 0/<region>/ field authoring with
**different conjugate BC names per pair**. The auto-generated
`region_<fluid>_to_region_<solid>` patches from `splitMeshRegions
-cellZones -overwrite` produce conjugate BCs in **both directions**:

- `0/region_hot_fluid/T`  needs BC `region_hot_fluid_to_region_solid`
- `0/region_cold_fluid/T` needs BC `region_cold_fluid_to_region_solid`
- `0/region_solid/T`      needs BCs **both** `region_solid_to_region_hot_fluid`
                          AND `region_solid_to_region_cold_fluid`
                          (two distinct patches, NOT one combined)

**Why it matters**: case_002b's BC bookkeeping pattern (one fluid ↔
many solids) does NOT translate trivially. The solid region in case_011
must distinguish hot-side vs cold-side conjugate patches in its T field;
naively using a wildcard `region_solid_to_.*` works for some kappaMethod
choices but breaks if hot/cold sides need different `Tnbr` semantics.

**Status discriminator**: writes-OF-BC-files-cleanly evidence. Field-validation
of the dual-conjugate setup pending v1 solver run.

**Anti-pattern**: Do NOT collapse the two `region_solid_to_*` patches
into a single regex-matched BC if individual coupling parameters need
to differ between hot- and cold-side mating fluids in v2.

---

## V48 — sHM `multiRegionFeatureSnap=true` on compact-fin geometry: snap-quality cliff

**Status**: open (case_011 v1 only data point)
**Numerics class**: sHM-thin-wall (V10 family extension)

**Observation**: `snappyHexMesh -overwrite` on the case_011 STEP-derived
3-region STL (region_hot_fluid + region_cold_fluid + region_solid)
with `multiRegionFeatureSnap true` and refinement (1, 2) produces
**non-converging snap** within default `nSolveIter=30`. Log emits:
> `Did not successfully snap mesh. Continuing to snap to resolve easy
> surfaces but the resulting mesh will not satisfy your quality
> constraints`

**Iteration trace**: morph iteration 7-8+, decreasing displacement
scaling (0.42 → 0.32), face quality counters stuck at hundreds of
non-orthogonal/twisted faces.

**Root cause hypothesis**: BASE_FIN_THICKNESS_MM = 1.0 mm with
background_cell_size = 4 mm at level (1, 2) → effective cell ~1 mm
→ exactly at the edge of "1 cell per fin thickness". sHM tries to
snap two opposing fin walls into the same cell layer.

**Cross-validation**: `thin_wall_advisor` (V10/V23/V30) PRE-MESH
flagged this exact failure mode for the 0.6mm rear-third cold fin
(severity=critical, recommended_level=4, see
`evidence/v1/thin_wall_d8.json`). The 1.0mm front-2/3 nominal fins
should also be at level 3-4, not (1, 2). **The advisor's PASS on
v1 mesh selection was correctly predictive.**

**v2 path**: Bump cold + hot fin patches to level (3, 4); rerun;
expect snap convergence within `nSolveIter=30`.

**S-playbook anchor candidate**: S22 (sHM compact-HX fin meshing)
— "if fin thickness < 2× background cell size, level must be
chosen to make effective cell size ≤ thickness / min_cells_per_thickness".

---

## V49 — A2 `_run_shared` on HX plate-plate adjacency: algorithm-runs-cleanly + V25 placeholder reproduces

**Status**: closed-as-algorithm-runs-cleanly · `[QUESTIONABLE 2026-05-08]` field-validation pending A2-v2
**Numerics class**: virtual-interface-detection (V2/V25 family)

**Observation**: case_011 D5 separator_plate_3_4 split into
front-2/3 nominal half + rear-1/3 30 µm-offset half exercises
A2 via:

```python
spec = InterfaceSpec(
    patch_name="separator_3_4__plate_offset_interface",
    mode="shared",
    body_a="separator_plate_3_4_front",
    body_b="separator_plate_3_4_rear_offset",
)
```

**Result**: `matched=True`, `body_owner='separator_plate_3_4_front'`,
`bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`,
`normal_dot=0.99999`, `diagnostic="shared face on
'separator_plate_3_4_front' (area=144)"`.

**V25 placeholder reproduces verbatim**: `bbox_overlap_fraction=1.0`
and `area_diff_fraction=0.0` are LITERALS, not measurements. A2
matched the y=80mm face-pair (the abutment plane) but did NOT
measure the 30µm x-offset between the two plate halves.

**Cross-topology evidence stack (D1 / D5 family)**:

| Case | Defect | Topology | Public-API outcome |
|---|---|---|---|
| case_003 | D1 0.35mm | planar CadQuery boxes | matched=True (placeholder) |
| case_004 | D1 0.30mm | rotating-machinery planar | matched=True (placeholder) |
| case_005 v2 | D1 0.35mm | flange annular planar | matched=True (placeholder) |
| **case_011** | **D5 30µm** | **HX plate-plate adjacency (NEW topology)** | **matched=True (placeholder)** |

**Verdict per `knowledge_status_convention.md`**: case_011 is the
**4th data point** confirming the V25 silent-placeholder semantic
across **a fourth distinct topology** (HX plate-plate). Sub-DEC
overdetermination strengthened. Did NOT propose `isSame()` fast-path
(V2 lesson preserved).

**To resolve**: A2-v2 sub-DEC merge + injection re-test on case_011
30µm offset. Until then, D5 verification status = `[QUESTIONABLE
2026-05-08]`.

---

## V50 — `thin_wall_advisor` 7th cross-topology data point: HX cold fin 0.6mm

**Status**: closed (advisor landed + field-validated cross-topology, 7-of-7 if case_010 also PASSes)
**Numerics class**: sHM-thin-wall (V10/V23/V30 family extension)

**Observation**: case_011 D8 (cold-fin rear-1/3 thickness=0.6mm at
level (1,2), background=4mm) exercises `detect_thin_wall_patches_at_risk`:

```python
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="cold_fin_rear_third",
                            bbox_dimensions=(0.0006, 0.016, 0.180))],
    refinement_levels={"cold_fin_rear_third": (1, 2)},
    background_cell_size=0.004,
)
```

**Result**: severity=critical, `cells_per_thickness=0.6`,
`recommended_level_max=4`, `effective_cell_size=0.001 m` (1 mm at
level 2) > thickness=0.0006 m → `WILL be merged by sHM`.

**Cross-topology arc state (post-case_011)**:

| Case | D8 dim | Geometry class | Outcome |
|---|---|---|---|
| case_002a/b | (origin) | curved CATIA Frame | LANDED |
| case_003 | 0.80mm | planar CadQuery box | PASS (V10 → closed cross-topology) |
| case_004 | 0.75mm | rotating-machinery shim | PASS (V23) |
| case_006 | 0.18mm | extreme-thinness compound | PASS (V30; 5-case) |
| case_007 | 0.80mm | ship transom plate | sediment landed (V33-V35) |
| case_008 | 0.80mm | airfoil TE tab | sediment landed (V36-V37) |
| case_009 | n/a | reacting-low-Mach root | n/a (D8 not in defect set) |
| case_010 | sub-mm | vehicle underbody cover | sediment landed (V43-V46) |
| **case_011** | **0.60mm** | **HX cold fin (NEW topology: compact-HX)** | **PASS (this finding)** |

**Cross-validation with V48**: V50's advisor warning was correctly
predictive of V48's empirical sHM snap-failure on the same fin
geometry. Pre-mesh advisor PASS predicts post-mesh sHM struggle —
the advisor's intended use case validates.

**To verify**: cross-walk case_007 / case_008 / case_010 sediment to
confirm thin_wall_advisor PASSes are consistent. If yes, V10 → 8-case
cross-topology robustness across {curved CATIA, planar CadQuery,
rotating shim, extreme-thinness, ship transom, airfoil TE, vehicle
underbody, compact-HX fin}. If any FAIL, case_011 becomes the boundary
of HX-vs-other-topology context-sensitivity.

---

## S22 (candidate) — sHM compact-HX fin meshing: refinement level vs fin thickness

**Status**: candidate (one data point: case_011 v1)
**Anchored V-findings**: V48 (snap struggle), V50 (advisor pre-prediction)

**Heuristic statement**:
> For compact heat-exchanger geometry with fin thickness `t_fin` and
> background cell size `bg`, choose refinement level `n` such that
> the effective cell size `bg / 2^n` ≤ `t_fin / min_cells_per_thickness`
> (default `min_cells_per_thickness = 2`).
> If `t_fin < 2 × bg`, level (1, 2) is insufficient; use (3, 4) or
> bump background.

**case_011 worked example** (rear-third cold fin 0.6mm, bg=4mm):
- thin_wall_advisor `recommended_level_max = 4` → effective cell = 4/16 = 0.25 mm
- `cells_per_thickness = 0.6 / 0.25 = 2.4` → safe

**v2 action item**: bump `case.yaml.mesh.refinement.cold_fin_rear_third`
to `(3, 4)` and re-run; record sHM snap convergence delta as S22
empirical confirmation.

---

## S23 (candidate) — chtMultiRegionFoam multi-stream BC bookkeeping checklist

**Status**: candidate (case_011 v1 setup-time discovery)
**Anchored V-findings**: V47

**Heuristic statement**:
> When extending single-stream CHT (case_002b pattern) to N-fluid
> CHT (case_011 N=2 pattern), each solid region's `0/T` field must
> declare a distinct conjugate BC for **each fluid region it
> couples to**, with patch names matching `splitMeshRegions
> -cellZones`'s auto-generated `region_<solid>_to_region_<fluid>_<i>`
> convention. Wildcards (`region_solid_to_.*`) are convenient but
> hide kappaMethod / Tnbr asymmetry; explicit per-pair BCs are safer.

---

## Stale-assumption fixes (applied in v1)

### Fix 1 — `cq.exporters.export(assembly, ...)` → `assembly.save(..., 'STEP')`

**Surfaced by**: case_011 v1 build_cad.py first run
**Stale assumption**: cadquery 1.x style `cq.exporters.export(assembly, path)`
**Reality**: cadquery 2.7+ deprecates this; use `assembly.save(path, 'STEP')`
or `assembly.export(path, 'STEP')`.
**Fix-in-place**: `scripts/build_cad.py:export_step` patched 2026-05-09;
deterministic STEP output preserved (byte-identical regen verified).
**Commit tag**: `corrects-assumption: cq_exporters_export_assembly,
surfaced-by: case_011-v1-build`

### Fix 2 — STEP `FILE_NAME` timestamp non-determinism

**Surfaced by**: case_011 v1 byte-identical regen check
**Stale assumption**: cadquery STEP export is byte-deterministic out of the box
**Reality**: OpenCASCADE STEP writer stamps a wall-clock timestamp
into `FILE_NAME(...,'YYYY-MM-DDTHH:MM:SS',...)`; geometry is otherwise
deterministic.
**Fix-in-place**: post-export normalization to fixed timestamp
`2026-05-08T00:00:00`; `scripts/build_cad.py:_normalize_step_header`.
**Commit tag**: `corrects-assumption: step_file_name_timestamp,
surfaced-by: case_011-v1-determinism`

---

## Counter

case_011 sub-session V-finding contribution: **+4 V (V47-V50) + 2 S
(S22, S23 candidates) + 2 stale-assumption fixes**. autonomous_governance
counter += 1 (case_011 dispatch DEC pending main-session ratification).
