# Case 010 · DrivAer Fastback LES · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.5 xhigh, 86gs).
> Validated 2026-05-08 — see `case_010_validation.md`. PASS WITH
> NOTES. **Final case in 10-case roster.**
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25** (open · sourced by case_005 v2 disambiguation, captured
> in harvest cycle 002): A2's `_run_shared` returns matched=True
> with hardcoded placeholder fields regardless of actual gap
> distance. D1 exercise produces algorithm-runs-cleanly evidence,
> NOT gap-detection field-validation. A2-v2 sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_010_drivaer_fastback_les**.

This is the LAST case in the 10-case roster (all numerics
classes covered after you complete).

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience.

Nine prior cases:
- case_002a, 002b: active
- case_003 (CRM-HLS, external high-Re): active · v1 paused on V20
  unit-scale block
- case_004 (NREL Phase VI rotor, MRF): active · v1 advisor-validation
  done; CFD pending v2
- case_005 (RAE M2129 S-duct): active · v1+v2 ran; sourced
  V16-V25 chain (incl. V25: A2 placeholder semantic OPEN; V17:
  A3 redundancy gap OPEN)
- case_006 (ONERA M6 transonic): dispatched-deferred
- case_007 (KCS ship VOF): dispatched-deferred
- case_008 (GLC305 Lagrangian): dispatched-deferred
- case_009 (Sandia Flame D): dispatched-deferred

Your case fills **incompressible-LES** external transient (vehicle
aerodynamics) — first LES for project. You also EXTEND the
thin_wall_advisor cross-topology validation arc to **6-case**:
case_002a (curved CATIA) + case_003 (planar aero) + case_004
(rotating-machinery shim) + case_007 (ship transom) + case_008
(airfoil TE tab) + case_010 (vehicle underbody cover) — final
case in roster makes the cross-topology arc complete.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md`, `case_002b_*.md`
4. `.planning/methodology/industrial_case_solver_findings.md`
   (Pattern 6: case_010 inherits NONE of V3-V25; incompressible-LES
   is a new numerics root)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. **`.planning/methodology/knowledge_status_convention.md`**
   (NEW · 2026-05-08 harvest 002) — defines `[QUESTIONABLE]` /
   `[REFUTED]` / `[SUPERSEDED]` / `[VALIDATED]` markers
8. `.planning/cross_cuts/v_series_2026-05-08.md` (V-series snapshot)
9. `.planning/harvest_reports/2026-05-08_harvest_002.md` (cycle 002
   findings — A2 capability framing notes)
10. `~/Desktop/apu-bay-ventilation/`
11. `.planning/methodology/kickoff/case_010_codex_response.md`
12. `.planning/methodology/kickoff/case_010_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (for D8 — LANDED,
     case_010 is 6th in cross-topology arc)
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D1 — A2
     LANDED 2026-05-08 a09ae0a, BUT see `[QUESTIONABLE]` marker
     in D1 verification section below)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier` (for vehicle CAD decimation if forced)
   - DO NOT re-implement these case-locally
4. Do NOT redesign the case — execute Codex's brief; revision
   request only if fundamentally unworkable (round-cap=2)
5. **Wall-modeled LES** (y+=30-100); do NOT escalate to
   wall-resolved DNS-quality (out of scope, multi-month effort)
6. **Stationary wheels and ground in v1** (moving floor / rotating
   tires is sub-session v3 decision, not case design)
7. **No Ahmed body** — Lane B excluded; you're using DrivAer
8. **No external redistribution of generated STEP** without
   TUM registration verification (license caveat per case_007 pattern)
9. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
   (V2 lesson preserved)

## Case identifier
`case_010_drivaer_fastback_les` · solver-class
**incompressible-LES** · numerics-class **incompressible-LES** (root)

## Codex brief summary
- TUM DrivAer fastback, smooth underbody, mirrors, stationary wheels
- L=4.61 m, W=1.76 m, H=1.42 m, wheelbase=2.79 m
- U_inf=16 m/s, Re_L=4.87e6
- Solver v1: pimpleFoam + WALE LES + nutUSpaldingWallFunction
- v2 fallback: dynamicKEqn LES OR pisoFoam if pimple under-converges
- y+ target 30-100 wall-modeled
- dt target ~ 1e-4 s (CFL ≤ 1)
- Averaging window: start at t = 2 L/U_inf flow-throughs, accumulate over ≥ 5 flow-throughs
- Target: time-averaged Cd≈0.281, Cl, Cm, surface Cp at TUM taps,
  base-pressure recovery, Q/λ2 wake topology
- Defects: D1 (0.35 mm side-mirror trim gap) + D8 (sub-mm
  underbody plate between axles)
- Effort: 10-14h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 250 LOC, deterministic. 12 named
bodies (vehicle_body, side_mirror_outboard, wheel_front_outboard,
wheel_rear_outboard, mirror_edge_trim_strip, underbody_sensor_cover_thin,
inlet, outlet, top, side_outboard, ground, symmetry_plane_centerline).

```bash
cd ~/Desktop/case_010_drivaer_fastback_les
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## LES-specific work (case_010 unique)

### `08b_write_les_fvschemes.py`
Emit `system/fvSchemes` with LES-friendly settings:
- ddtSchemes: `default backward;` (or `CrankNicolson 0.5;`)
- divSchemes: `div(phi,U) Gauss linearUpwindV grad(U);` (or `LUST grad(U);` for DES-like)
- gradSchemes: `Gauss linear;`
- laplacianSchemes: `Gauss linear corrected;`

### `08c_write_les_turbulenceProperties.py`
Emit `constant/turbulenceProperties`:
```
simulationType  LES;
LES
{
    LESModel    WALE;          // or dynamicKEqn for v2
    delta       cubeRootVol;
    cubeRootVolCoeffs { deltaCoeff 1; }
    turbulence  on;
    printCoeffs on;
    WALECoeffs  { Ck 0.094; Ce 1.048; Cw 0.325; }
}
```

### `08d_write_wall_functions.py`
For wall-modeled LES at y+=30-100:
- `nut: nutUSpaldingWallFunction`
- `nuTilda` not needed (LES doesn't use Spalart-Allmaras)
- `k`, `omega` not needed (WALE has built-in subgrid)

### `08e_write_field_average_function_object.py`
Add `system/controlDict` function objects:
```
functions
{
    forceCoeffs1
    {
        type            forceCoeffs;
        libs            (forces);
        patches         (vehicle_body wheel_front_outboard wheel_rear_outboard side_mirror_outboard);
        rho             rhoInf;
        rhoInf          1.225;
        liftDir         (0 0 1);
        dragDir         (1 0 0);
        CofR            (2.305 0 0.71);   // half-wheelbase
        pitchAxis       (0 1 0);
        magUInf         16;
        lRef            4.61;
        Aref            <fastback frontal area>;
    }
    fieldAverage1
    {
        type            fieldAverage;
        libs            (fieldFunctionObjects);
        timeStart       <2*L/U_inf>;
        cleanRestart    true;
        fields
        (
            U { mean on; prime2Mean off; base time; }
            p { mean on; prime2Mean off; base time; }
        );
    }
}
```

### `09_run_solver.sh`
1. blockMesh + sHM with refinement near vehicle body
2. potentialFoam initialization (recommended for LES start)
3. pimpleFoam in transient mode, dt = 1e-4 s, run to t = 2 L/U_inf
   (transient settling)
4. Restart with fieldAverage active, run ≥ 5 L/U_inf
5. Tail-average forces + time-averaged U/p fields

### `10b_compute_q_criterion.py`
Use ParaView (or pyvista):
1. Compute Q-criterion = 0.5*(Ω_ij Ω_ij - S_ij S_ij) on cell centers
2. Threshold isosurface at Q = 1000 (or λ2 = -100)
3. Visualize wake structures (A-pillar vortex, side-mirror
   vortex, base-pressure recirculation)
4. Emit `evidence/<v>/wake_topology_report.md`

### `10c_compute_cd_decomposition.py`
1. Tail-average forces from forceCoeffs.dat (last 5 flow-throughs)
2. Cd_total = Cd_pressure + Cd_friction
3. Compare Cd_total to TUM target ≈ 0.281
4. Surface Cp at published TUM tap locations
5. Base pressure recovery vs published

## Defect verification

### D1 (mirror_edge_trim_strip 0.35 mm gap) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: "exercise A2; expect detection of
> 0.35 mm gap" framing assumes a capability A2 v1 does NOT have.
> A2 LANDED for V2 pattern (shared-interface confirmation on
> non-manifold STEP), NOT D1 pattern (gap-as-defect detection).
> Per V25 (open · `industrial_case_solver_findings.md#V25`),
> A2's `_run_shared` returns `matched=True` with hardcoded
> placeholder `bbox_overlap_fraction=1.0` /
> `area_diff_fraction=0.0` regardless of actual gap distance.
> Verification pending: A2-v2 sub-DEC adds `inter_face_gap_mm`
> field to `DetectedInterface` (drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> To resolve: A2-v2 lands AND case_010 sub-session re-runs D1
> falsification on side-mirror trim geometry. Until then, your
> A2 PASS confirms only that `_run_shared` runs cleanly on
> mirror-trim faces — NOT that A2 detects the 0.35 mm gap as
> a defect.

**Step 1 — manual ground truth via FreeCAD**:

```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_010_drivaer_fastback_les/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['side_mirror_outboard'].Shape.distToShape(o['mirror_edge_trim_strip'].Shape)[0])"
```

Expected ≈ 0.35 mm. Report actual measured value.

**Step 2 — exercise landed A2 advisor**:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec, FaceGeometry, BodyGeometry,
)
spec = InterfaceSpec(
    name="side_mirror__mirror_trim_interface",
    mode="shared",
    bodies=("side_mirror_outboard", "mirror_edge_trim_strip"),
)
result = detect_virtual_interfaces(bodies=[mirror_body, trim_body],
                                   specs=[spec])
# Expect: matched=True (per V21/V22 pattern) BUT this PASS is
# NOT field-validation of gap-detection capability per V25.
```

**Step 3 — V-finding judgments**:

- If `matched=True`: document as "case_010 cross-topology PASS for
  `_run_shared` on vehicle-aero side-mirror trim geometry"
  (algorithm-runs-cleanly, NOT gap-detection per V25).
  **FINAL case in roster** — this completes A2 `_run_shared`
  cross-topology evidence (axis-aligned-planar / flange-ring
  axial-end / rotating-machinery / ship-hydro / Lagrangian-
  airfoil-mount / combustion-burner if D1 / vehicle-aero).
- If `matched=False`: NEW V-finding documenting which geometric
  property of side-mirror trim fails `find_face_facing_target`.
- Do NOT propose `isSame()` fast-path (V2 lesson).

### D8 (underbody_sensor_cover_thin) — thin_wall_advisor LANDED
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['underbody_sensor_cover_thin'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```
Expected sub-mm. Then exercise:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="underbody_sensor_cover_thin",
                            bbox_dimensions=(cover_dx_m, cover_dy_m, cover_dz_m))],
    refinement_levels={"underbody_sensor_cover_thin": (1, 2)},
    background_cell_size=YOUR_BG_CELL_SIZE_METERS,
)
print(warnings)  # expect 'critical'
```

**6-case cross-topology validation arc (FINAL — completes
roster)**: case_002a (curved CATIA Frame) + case_003 (planar
CadQuery thin_access_plate) + case_004 (rotating-machinery
`yaw_sensor_shim` 0.75mm) + case_007 (ship transom plate 0.80mm)
+ case_008 (airfoil TE tab 0.80mm) + case_010 (vehicle underbody
cover sub-mm). If all 6 produce critical warning consistent,
**upgrade V10 / V23 status to "6-of-6 — robust across (curved-
shell, planar-aero, rotating-aux, ship-hydro, airfoil-TE, vehicle-
underbody) topologies — cleanest piece of A1-A5 sediment in
project"** per `knowledge_status_convention.md` `[VALIDATED]`
marker. If divergent on case_010 specifically, flag as advisor-
context-sensitivity V-finding for vehicle aerodynamics.

## Six per-case standard moves
1. Reference profile at `case_profiles/case_010_drivaer_fastback_les.md`
2. V-series append: LES timestep stability vs CFL, time-averaging
   window sufficiency, A-pillar / mirror / wake transient coherent
   structures, sHM refinement near vehicle body, ground-vehicle
   gap mesh resolution. ALSO: **A2 `_run_shared` behavior on
   vehicle-aero topology** (above); **thin_wall 6-case cross-
   topology FINAL check** (above)
3. Playbook S13+: "LES Cd unstable when averaged < 5 flow-throughs
   → extend averaging window" / "y+ overshoot at A-pillar → refine
   prism layer near sharp edge" / "fastback base separation
   over-predicts → check WALE Ck constant or switch dynamicKEqn"
4. Stale-assumption fixes: 0.orig template needs LES variants;
   turbulenceProperties needs LES section. Commit tag:
   `corrects-assumption: <X>, surfaced-by: case_010-V<n>`
5. Artifact extraction (4 likely):
   - `les_fvschemes_writer.py`
   - `les_turbulence_properties_writer.py`
   - `field_average_function_object_writer.py`
   - `q_criterion_post_processor.py`
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_010_drivaer_fastback_les/
├── README.md, Makefile, .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── templates/{turbulenceProperties_LES.j2 (NEW), fvSchemes_LES.j2 (NEW),
│              0.orig.j2 LES extension, controlDict.j2 with field averaging,
│              ...}
├── scripts/{01..11 + 08b/c/d/e + 10b/c}
├── case/    (gitignored)
└── evidence/<v>/{REPORT.md, wake_topology_report.md, cd_decomposition.md}
```

## Sediment + commit convention
Same as case_002a/b. `confidence: <high|med|low>` trailer.
Co-author Claude Opus 4.7. `case/` runtime gitignored.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated" if you only confirmed `_run_shared` runs cleanly.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (4 likely), advisor-bias fixes, add LES
  fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  upgrade to wall-resolved DNS-quality, redistribute DrivAer STEP
  externally without TUM registration verification, add `isSame()`
  fast-path to `virtual_interface_detector` (V2 lesson)

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D1 exercise
   produces algorithm-runs-cleanly evidence, NOT gap-detection
   field-validation. See `[QUESTIONABLE]` marker in D1 verification
   section above. A2-v2 sub-DEC drafted
   (`patches/draft_a2_v2_gap_detection_2026-05-08.md`); after it
   lands, case_010 v3 re-runs D1 falsification.
2. **D8 thin_wall_advisor 6-case cross-topology FINAL check** —
   case_002a + 003 + 004 + 007 + 008 + 010 should all produce
   critical warning; this completes the roster's cross-topology
   validation arc. Upgrade V10/V23 to `[VALIDATED]` (6-of-6) on
   consistency, or flag context-sensitivity V-finding on divergence.
3. **First transient LES for project** — pimpleFoam + WALE
   infrastructure all-new
4. **Time-averaging window sensitivity** — Cd convergence may
   require ≥ 5 L/U_inf accumulation; v1 may show drift
5. **Wall-modeled y+** — sHM prism layer must produce y+=30-100
   on body surfaces; use `checkMesh -allTopology` to verify
6. **License caveat** — bake-into-script keeps STEP regeneration
   deterministic from public TUM offsets; do NOT publish the
   generated binary externally without TUM permission

## Coverage matrix complete after this case

After your sub-session sediment lands, the project's 10-case
roster covers all 10 numerics-class roots:
1. compressible-buoyant-RANS (case_002a)
2. + CHT extension (case_002b)
3. incompressible-RANS external (case_003)
4. incompressible-RANS-MRF (case_004)
5. compressible-RANS internal (case_005)
6. compressible-shock-density-based (case_006)
7. multiphase-VOF (case_007)
8. incompressible-RANS-Lagrangian (case_008)
9. reacting-low-Mach (case_009)
10. **incompressible-LES (case_010 — YOU)**

Workhorse OpenFOAM solver matrix complete. Future cases extend
combinations (LES+CHT, reacting-LES, compressible-Lagrangian) but
each numerics root has at least one anchor case.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_010 row from "Active queue" to "In-flight"
- [ ] Update `case_index.md` with case_010 status=active
- [ ] Update `INDEX.md` kickoff list status reconciled
- [ ] **10-case roster fully dispatched** — all numerics-class
      roots have anchor cases; future work extends combinations
- [ ] When sub-session reports A2 `_run_shared` outcome on
      vehicle-aero side-mirror trim topology (PASS = algorithm-
      runs-cleanly, NOT gap-detection per V25), update V22 / V25
      evidence rows — case_010 is FINAL piece of A2 cross-topology
      evidence
- [ ] When sub-session reports thin_wall 6-case cross-topology
      outcome, upgrade V10/V23 to `[VALIDATED]` (6-of-6) or open
      context-sensitivity V-finding on divergence — completes the
      roster's cross-topology validation arc
- [ ] When sub-session extracts LES infrastructure (fvSchemes
      writer, turbulence writer, field-averaging, Q-criterion
      post-processor), evaluate for promotion to main-project
      shared services
