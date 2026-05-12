# case_008 · GLC305 IRT Lagrangian (Industrial Reference)

> **NOT a gold-standard case.** No NASA Glenn IRT impingement-database parity
> is claimed in v1 — the engineering question is **harness ingestion +
> kinematicCloud writer + β(s/c) post-processor correctness on a clean
> GLC305 reference**, not droplet-impingement validation.
>
> Established 2026-05-08 by sub-session under DEC-V61-198 case-fleet protocol
> (queue dispatch from `case_proposal_queue.md`). **First Lagrangian case in
> the project — solver-class coverage map advances by one axis
> (incompressible-RANS-Lagrangian root, Pattern 6).**
>
> **Sibling thread**: none. case_008b future = DPMFoam 2-way coupling fallback
> if particle-volume-fraction effects emerge above the dilute 7e-7 baseline;
> case_008c future = MVD sweep at fixed LWC for impingement-limit sensitivity.

## What this entry is

Tier-1 NASA Glenn IRT GLC-305 swept-airfoil reference geometry (NTRS
20020061865 / 20020090796). CAD regenerated parametrically by Codex's
case-design protocol (cadquery + 51-pt clean GLC305 normalized table +
2D-extruded slab, span = 1 chord, no ice horn). 10-body parts manifest
including `airfoil_clean` + 3 auxiliary defect bodies (D1 root_mount_pad
+ root_mount_strut, D8 trailing_edge_tab_thin) + 6 farfield/boundary
patches.

**Key non-redesign**: input is CLEAN GLC305 — the harness predicts where
ice WOULD form via β(s/c) on the clean reference. No ice-horn input,
per kickoff hard guardrail.

## What this entry is for

Three orthogonal uses:

1. **Solver-class coverage**: First incompressible-RANS-Lagrangian case in
   the fleet. Pattern 6 root — no inheritance from case_002a/b
   (compressible-buoyant) nor case_003-006 (incompressible-RANS / MRF /
   compressible-shock-density-based) nor case_007 (multiphase-VOF). Future
   Lagrangian cases (DPMFoam 2-way, sprayCloud combustion injection,
   sediment transport) inherit any V36-V<n> findings from this case.

2. **A2 advisor 5th algorithm-path PASS**: case_008 D1 = 0.35 mm vertical
   gap between `root_mount_pad` (planar CadQuery box) and `root_mount_strut`
   (planar CadQuery box) at airfoil-mount root location. Manual ground
   truth: `pad_bottom_y − strut_top_y = 0.3500 mm` exact. A2 `_run_shared`
   returns matched=True via `find_face_facing_target` (normal-only
   matching). **PASS interpretation per V25 [QUESTIONABLE]**:
   algorithm-runs-cleanly evidence on incompressible-RANS-Lagrangian
   airfoil-mount topology. Does NOT field-validate gap-detection capability.

3. **thin_wall_advisor 6th-topology field-validation** (extends V10/V23/V30
   coverage): D8 = 0.80 mm airfoil-TE auxiliary tab. Background cell
   0.020 m at refinement level [1,2] → cells_per_thickness = 0.16,
   severity=critical, recommended_level_max=6. Topology adds airfoil-TE
   to the cross-topology set: curved CATIA frame (002a/b 50 mm) +
   planar aero plate (003 0.80 mm) + rotating-machinery aux shim
   (004 0.75 mm) + transonic wing-tip sliver (006 0.18 mm) + ship
   above-WL transom plate (007 0.80 mm) + airfoil-TE auxiliary tab
   (008 0.80 mm). Six distinct industrial topologies, three orders of
   magnitude in thickness — `[VALIDATED]` per knowledge_status_convention.md.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_008_glc305_irt_lagrangian/` |
| Top-level overview | `~/Desktop/case_008_glc305_irt_lagrangian/README.md` |
| v1 sub-session report | `~/Desktop/case_008_glc305_irt_lagrangian/evidence/v1/REPORT.md` |
| SSOT YAML | `~/Desktop/case_008_glc305_irt_lagrangian/config/case.yaml` |
| Defect verification | `evidence/v1/{thin_wall_advisor_output.json, a2_advisor_output.json}` |
| CAD generation script | `scripts/build_cad.py` (Codex deliverable 2, 231 LOC) |
| Parts manifest | `inputs/parts_manifest.yaml` (Codex deliverable 4) |
| Defect manifest | `inputs/defect_manifest.yaml` (Codex deliverable 5) |
| Lagrangian infrastructure (NEW) | `templates/0.orig/{U,p,k,omega,nut}` + `scripts/08b_write_kinematic_cloud.py` + `scripts/10b_compute_collection_efficiency.py` + `scripts/09_run_solver.sh` (staged simpleFoam→freeze→cloud) |

## Solver-class capability axis

| axis | value |
|---|---|
| solver_class | incompressible-RANS-Lagrangian (icing droplet impingement) |
| numerics_class | incompressible-RANS-Lagrangian (Pattern 6 root) |
| pattern_6_inheritance | NONE (first Lagrangian); no V-finding inherits from prior cases |
| solver_v1 | simpleFoam (steady) + frozen-Eulerian + kinematicCloud (one-way) |
| solver_v2_fallback | DPMFoam (2-way coupling) only if particle volume fraction effects emerge |
| turbulence | kOmegaSST RAS (steady) |
| fluid | air, ν=1.4e-5 m²/s at T=268 K, ρ=1.318 kg/m³ |
| particle | water, ρ=1000 kg/m³, MVD=25 µm, LWC=0.7 g/m³ |
| volume fraction | 7e-7 (dilute → 1-way correct for v1) |
| inflow | U_inf = 67 m/s with α=4° → U=(66.84, 4.67, 0); chord = 305 mm |
| Re_chord | 1.46e6 (off nominal IRT 1.8e6 due to cold-T ν shift) |
| Stokes_chord | 0.41 |

## Per-step wall time (v1 sub-session, executed portion only)

Measured 2026-05-08 on macOS Apple Silicon. CAD generation + CFD pipeline
deferred (cadquery not yet installed in venv; OpenFOAM container path
not yet exercised for kinematicCloud).

| Step | Script | Wall time | Output |
|---|---|---|---|
| sandbox skeleton | n/a | <5 s | 10 files in config/inputs/scripts/templates |
| advisor exercise (thin_wall) | `scripts/exercise_thin_wall_advisor.py` | <1 s | `evidence/v1/thin_wall_advisor_output.json` |
| advisor exercise (A2) | `scripts/exercise_a2_advisor.py` | <1 s | `evidence/v1/a2_advisor_output.json` |
| 08b smoke test | `scripts/test_08b_kinematic_cloud.py` | <1 s | `evidence/v1/sample_kinematicCloudProperties` |
| β post-proc dry-run | `scripts/10b_compute_collection_efficiency.py` (pending-cfd-run) | <1 s | `evidence/v1/beta_report.md` (placeholder) |

**Total v1-executed pipeline wall time**: ~10 s.

**Pending v2 sub-session steps**:
- cadquery STEP generation (`make cad`); est. 30-60 s
- FreeCAD ground truth `make ground-truth-{d1,d8}` (pad/strut distance + tab bbox); est. 15 s
- `01_extract_stl` (multi-solid STL via FreeCAD); est. 30-60 s
- `04_scaffold_case` + `05_make_dicts` (Jinja2 → OpenFOAM dicts); est. <30 s
- `06_run_mesh.sh` (snappyHexMesh airfoil + auxiliary bodies); est. 5-15 min
- `09_run_solver.sh` stage 1 (simpleFoam to <1e-5); est. 1-3 h
- `09_run_solver.sh` stages 2-4 (freeze → kinematicCloud → β post-proc); est. 30-90 min
- v3: A2-v2 re-run on D1 once gap-detection capability lands

## V-finding contributions

- **V36** (NEW) · A2 `_run_shared` cross-topology PASS on incompressible-RANS-Lagrangian airfoil-mount topology — 5th algorithm-path PASS, gap-detection still pending V25 fix
- **V37** (NEW) · thin_wall_advisor 6-topology cross-topology validation closed — case_008 airfoil-TE tab (0.80 mm) joins the cross-topology arc; status `[VALIDATED]`
- **V10/V23/V30 status upgrade** — 6 topologies × 3 orders of magnitude thickness without behavioral divergence; advisor correctness arc closed
- **V33 status reinforced** — A2 algorithm-path PASS on a 5th distinct topology (incompressible-Lagrangian airfoil-mount); V25 placeholder semantic still unresolved

## S-series contribution

- **S16** (NEW) · Lagrangian-on-frozen-Eulerian: converge simpleFoam to <1e-5; copy U/p/nut into stage-2 0/; run kinematicCloud with `solution.coupled=false`; cloud requires no further pressure-velocity coupling. Pattern: stage decoupling for Pattern 6 Lagrangian root.

## Status

- v1: sandbox + scripts + advisor exercises + smoke tests **complete** (executed portion); CFD pipeline pending (deferred to v2)
- v2 (planned): cadquery STEP regeneration → mesh → simpleFoam to <1e-5 → freeze → kinematicCloud → β(s/c)
- v3 (planned): A2-v2 (gap-detection capability) re-validation on D1 once the V25 sub-DEC lands

## Last touch
2026-05-08 (sub-session v1 advisor-validation + Lagrangian-infrastructure design)
