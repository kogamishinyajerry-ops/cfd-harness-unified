# Case 007 · KRISO Container Ship KCS · multiphase-VOF / interFoam (Industrial Reference)

> **NOT a gold-standard case.** Reference-derived hull offsets baked into
> a deterministic CadQuery generator (no STEP redistribution); ITTC/NMRI
> Tokyo workshop benchmarks exist but this v1 sub-session targets
> infrastructure shake-down + advisor exercise, not strict KCS Ct/Cw
> verdict-pass.
>
> Established by sub-session under DEC-V61-198 (APU bay strategic pivot,
> 2026-05-07): industrial CFD experience accumulator. This is the **first
> multiphase-VOF case** for the project; numerics-class root, inherits
> NONE of V3-V25 numerics findings (per industrial_case_solver_findings
> Pattern 6).
>
> Sub-session executed 2026-05-08; v1 paused at advisor-exercise +
> mesh-chain shake-down; full interFoam tail-averaged Ct/Cw run deferred
> to v2 (compute budget).

## What this entry is

10th industrial reference profile (002a/002b/003/004/005/006-deferred
/007/008/009/010-deferred sequence). Sub-session entry-point case for
**multiphase-VOF** axis on the harness coverage map; first time the
harness is exercised on an `alpha.water` field with `setFields`,
`p_rgh` totalPressure atmosphere, `variableHeightFlowRate` water
inlet, and a free-surface refinement band.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_007_kcs_ship_vof/` |
| Top-level overview | `~/Desktop/case_007_kcs_ship_vof/README.md` |
| v1 evidence | `~/Desktop/case_007_kcs_ship_vof/evidence/v1/REPORT.md` |
| SSOT YAML | `~/Desktop/case_007_kcs_ship_vof/config/case.yaml` |
| Codex CAD generator | `scripts/build_cad.py` (312 LOC, baked NMRI-style hull offsets) |
| 9-script pipeline | `scripts/03_validate_step.py … 10b_compute_wave_metrics.py` |
| Templates | `templates/{0.orig,constant,system}/` |
| Defect manifest | inline in `inputs/cad_codex_v1.step` (D1 0.35mm rudder hub gap, D8 0.80mm transom) |

## Engineering question

Can the harness ingest a realistic ship-hydrodynamics STEP, configure
`interFoam` for a long unsteady quasi-steady tow, preserve a sharp
`alpha.water` free surface, and report KCS-style resistance + wave
metrics without corrupting hull pressure or wave-cut reference zones?

**Reference physics** (KCS model scale):
- Lpp = 7.2786 m, Bwl = 1.019 m, draft = 0.3418 m
- Fr = 0.26, U_inf = 2.1962 m/s, Re = 1.4e7, M ≈ 0.006
- Half-domain with centerline symmetry (`y/L = 0.0`)
- Wave-cut reference at `y/L = 0.1509`
- Wetted surface (no rudder) S = 9.4379 m²

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (sediment candidates):
- Codex's `scripts/build_cad.py` baked-offset CadQuery hull (no STEP redistribution)
- `scripts/03_validate_step.py` OCAF-recursing STEP loader + `BRepExtrema_DistShapeShape` defect ground-truth (FreeCAD-free path)
- `scripts/03b_exercise_advisors.py` advisor invocation for D1/D8 (with V25-aware framing)
- `scripts/04_step_to_stl.py` multi-region ASCII STL emitter (mm→m scale baked)
- `scripts/08b_write_multiphase_bc.py` BC contract checker (`alpha.water + p_rgh + variableHeightFlowRate + totalPressure + fixedFluxPressure`)
- `templates/0.orig/{alpha.water,p_rgh,U,k,omega,nut}` — first multiphase 0/ family in project
- `templates/constant/{transportProperties,turbulenceProperties,g}` — first multiphase transport
- `templates/system/{setFieldsDict,snappyHexMeshDict (free-surface band + multi-region STL),controlDict (interFoam + isoSurface FO),fvSchemes (vanLeer alpha + linearUpwindV U),fvSolution (MULES),decomposeParDict}`
- `scripts/09_run_solver.sh` Docker `interFoam` runner (smoke / full / meshonly modes)
- `scripts/10b_compute_wave_metrics.py` ITTC-1957 Cf + tail-averaged Ct + Cw extractor

**Reused from main project** via `PYTHONPATH`:
- `ui.backend.services.geometry_ingest.virtual_interface_detector`
  (A2 advisor) — invoked via public `detect_virtual_interfaces` API on
  `(rudder_hub_fairing, rudder_reference)` pair, both spec orderings;
  PASS interpretation per V25 placeholder-semantic guard
- `ui.backend.services.geometry_ingest.thin_wall_advisor` (thin_wall)
  — invoked on `stern_transom_plate_thin` at the kickoff-prescribed
  refinement (1, 2)

**Pending reuse / extraction candidates** (post-v1):
- multiphase BC writer → main-project `case_bc/multiphase_bc_writer.py` (V11 multiphase extension)
- setFields water-level writer → `case_solve/setFields_water_level_writer.py`
- wave-cut post-processor → `postprocess/wave_cut_post_processor.py`
- multi-region ASCII STL emitter (currently apu-bay-pattern-divergent: this case bakes mm→m at write time, apu-bay does not)

## v1 sub-session per-step wall-time (reference)

Measured 2026-05-08 on macOS Apple Silicon (Docker
`opencfd/openfoam-default:2312`, ARM64).

| Step | Script | Wall time | Output |
|---|---|---|---|
| build_cad | `scripts/build_cad.py` | ~5 s | 376 KB STEP, 10 named bodies |
| 03_validate_step | `scripts/03_validate_step.py` | ~3 s | `evidence/v1/defect_ground_truth.json` (D1=0.350, D8=0.800) |
| 03b_exercise_advisors | `scripts/03b_exercise_advisors.py` | ~5 s | `evidence/v1/advisor_exercise.json` |
| 04_step_to_stl | `scripts/04_step_to_stl.py` | ~10 s | 1.5 MB ASCII STL (5873+32+12+12 tris) |
| 05_scaffold_case | `scripts/05_scaffold_case.sh` | <1 s | `case/` tree |
| blockMesh | (Docker) | ~3 s | 720k bg cells (200×60×60) |
| surfaceFeatureExtract + sHM | (Docker) | (see v1 REPORT) | (see v1 REPORT) |
| interFoam smoke | (Docker, 1 s sim) | (deferred per evidence) | (deferred per evidence) |

## Defect ground truth + advisor results

| Defect | Claimed | Measured | Method | Status |
|---|---|---|---|---|
| D1 (rudder hub axial gap) | 0.35 mm | 0.3500 mm | OCC `BRepExtrema_DistShapeShape` between `rudder_hub_fairing` and `rudder_reference` | exact ✓ |
| D8 (transom plate thickness) | 0.80 mm | 0.800 mm | `min(BoundBox.{xlen,ylen,zlen})` on `stern_transom_plate_thin` | exact ✓ |

**A2 (`virtual_interface_detector`)**: matched=True both spec orderings;
`owner=rudder_reference`, area ≈ 5.93×10³ mm², `normal_dot=0.514`;
`bbox_overlap_fraction` and `area_diff_fraction` are HARDCODED PLACEHOLDERS
per V25, NOT measurements. PASS = `_run_shared` runs cleanly on
ship-hydro topology; this is NOT field-validation as gap-defect detector.
A2-v2 sub-DEC must land before D1 can be field-validated.

**thin_wall_advisor**: severity=`critical`, thickness=0.0008 m,
effective_cell_size=0.018 m, cells_per_thickness=0.044, recommended
level_max=8 vs assigned (1, 2). **Consistent with cases 002a / 003 /
004**; case_007 closes the **4-of-4 cross-topology arc** (curved CATIA
shell · planar CadQuery aero plate · rotating-machinery aux shim ·
ship-hydro above-WL transom plate).

## V-series sourced

| ID | Status | Topic |
|---|---|---|
| V10 (upgrade) | `[VALIDATED 2026-05-08 4-of-4]` | thin_wall_advisor robust across (curved-shell, planar-aero, rotating-aux, ship-hydro) topologies |
| V23 (upgrade) | `[VALIDATED 2026-05-08 4-of-4]` | same arc; case_007 transom plate closes |
| V33 (NEW) | `[QUESTIONABLE 2026-05-08]` per V25 | A2 `_run_shared` cross-topology consistency on ship-hydro: matched=True both orderings; algorithm-runs-cleanly only — does NOT field-validate gap detection (V25 placeholder semantic still in force). Closes 4th `_run_shared` cross-topology PASS (003 + 004 + 005-v2-disambiguation + 007) on the algorithm-path side; gap-detection capability still pending A2-v2 sub-DEC. |
| V34 (NEW) | partial | snappyHexMesh `free_surface_band` slab volume × 8^level can saturate maxGlobalCells before refinementSurfaces phase begins; 6M cell budget consumed by 0% surface refinement on first attempt. Pre-meshing volumetric `free_surface_refinement_advisor` candidate (multiphase analog of thin_wall_advisor). Awaits 2nd multiphase case to confirm pattern recurs |
| V35 (NEW) | partial | interFoam + kOmegaSST requires `wallDist { method meshWave; }` in fvSchemes; apu-bay-inherited fvSchemes template omits it. Surfaces at turbulence-model selection step. Per-numerics-class fvSchemes default registry overdue (compounds V11) |
| V36+ (candidate) | open · pattern-6 root | multiphase-VOF root patterns from full interFoam tail-averaged run (alpha smearing under MULES vanLeer; p_rgh hydrostatic init pitfalls; Kelvin wake decay rate vs free-surface refinement) — populated after v2 ≥ 30 L/U_inf run |

## Playbook entries sourced

(v1 too short to seed S-rows; v2/v3 sub-session expected to add S15+:
free-surface convergence, MULES Courant limits, alpha.water BC family
pitfalls.)

## License context

NMRI / Tokyo Workshop public pages (see Codex deliverable 2 source
URLs) expose hull dimensions and validation variables but do not
visibly grant explicit redistribution permission. Codex baked
hull-offset constants into the CadQuery script — that script is
canonical IP-clean. The script's STEP output is **local-use only**;
external publication requires explicit ITTC permission verification.

## Hard guardrails honored

1. V130 advisory-only: no AI writes case files; all sandbox edits via
   tooling
2. V132 no AI-mutating routes: read-only advisor exercise
3. No date / calendar gating
4. No persona dogfood
5. OpenFOAM is truth source: interFoam is the only solver of record
6. Main-project advisors used unchanged (no case-local re-implementation)
7. Did not redesign the case (executed Codex's 5 deliverables)
8. Mach ceiling: 0.0064 << 0.3 (incompressible regime preserved)
9. Hull surface untouched; wave-cut at y/L=0.1509 untouched
10. STEP output kept local (license safe path)
11. NO `isSame()` fast-path added to `virtual_interface_detector`
    (V2 lesson preserved)

## What this case does NOT yet have

- **Full interFoam tail-averaged run**: v1 ran a smoke-grade chain
  (≤ 1 s sim time); reliable Ct / Cw / wave cut requires ≥ 30 L/U_inf
  flow-throughs. Deferred to v2.
- **interIsoFoam fallback**: v2 trigger if v1 alpha smearing destroys
  Kelvin wake.
- **Free-to-heave-and-pitch**: v1 fixed-attitude only.
- **Verdict-pass parity vs ITTC/Tokyo workshop Ct**: not the v1 goal
  per kickoff (compute budget); v3 candidate.
- **A2 D1 field-validation as gap detector**: blocked by V25
  placeholder semantic; pending A2-v2 sub-DEC landing.
