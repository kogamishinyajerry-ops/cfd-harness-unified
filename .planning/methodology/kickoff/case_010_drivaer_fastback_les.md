# Case 010 · DrivAer Fastback LES · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.5 xhigh, 86gs).
> Validated 2026-05-08 — see `case_010_validation.md`. PASS WITH
> NOTES. **Final case in 10-case roster.**

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_010_drivaer_fastback_les**.

This is the LAST case in the 10-case roster (all numerics
classes covered after you complete).

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience. Nine
prior cases dispatched. Your case fills **incompressible-LES**
external transient (vehicle aerodynamics) — first LES for project.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md`, `case_002b_*.md`
4. `.planning/methodology/industrial_case_solver_findings.md` (Pattern 6: case_010 inherits NONE)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. `~/Desktop/apu-bay-ventilation/`
8. `.planning/methodology/kickoff/case_010_codex_response.md`
9. `.planning/methodology/kickoff/case_010_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `thin_wall_advisor` for D8 (4-case consistency: cases 004 + 007 + 008 + 010)
   - `geometry_surgery` for vehicle CAD decimation if forced
4. Do NOT redesign the case
5. **Wall-modeled LES** (y+=30-100); do NOT escalate to
   wall-resolved DNS-quality (out of scope, multi-month effort)
6. **Stationary wheels and ground in v1** (moving floor / rotating
   tires is sub-session v3 decision, not case design)
7. **No Ahmed body** — Lane B excluded; you're using DrivAer
8. **No external redistribution of generated STEP** without
   TUM registration verification (license caveat per case_007 pattern)

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

### D1 (mirror_edge_trim_strip 0.35 mm gap)
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['side_mirror_outboard'].Shape.distToShape(o['mirror_edge_trim_strip'].Shape)[0])"
```
Expected ≈ 0.35 mm. **A2 advisor pending — 8th consecutive case
(if pattern holds)**.

### D8 (underbody_sensor_cover_thin)
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['underbody_sensor_cover_thin'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```
Expected sub-mm. Run thin_wall_advisor (LANDED). **4-case
consistency check** (cases 004 + 007 + 008 + 010). Strong
falsification context.

## Six per-case standard moves
1. Reference profile at `case_profiles/case_010_drivaer_fastback_les.md`
2. V-series: LES timestep stability vs CFL, time-averaging window
   sufficiency, A-pillar / mirror / wake transient coherent
   structures, sHM refinement near vehicle body, ground-vehicle
   gap mesh resolution
3. Playbook S13+: "LES Cd unstable when averaged < 5 flow-throughs
   → extend averaging window" / "y+ overshoot at A-pillar → refine
   prism layer near sharp edge" / "fastback base separation
   over-predicts → check WALE Ck constant or switch dynamicKEqn"
4. Stale-assumption fixes: 0.orig template needs LES variants;
   turbulenceProperties needs LES section
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

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment, <250 LOC
  artifact extraction (4 likely), advisor-bias fixes, add LES
  fields to 0.orig
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  upgrade to wall-resolved DNS-quality, redistribute DrivAer STEP
  externally without TUM registration verification

## Known issues
1. **A2 pending — 8-of-8 evidence likely after this case**
2. **D8 thin_wall_advisor 4-case consistency** — strong context
3. **First transient LES for project** — pimpleFoam + WALE
   infrastructure all-new
4. **Time-averaging window sensitivity** — Cd convergence may
   require ≥ 5 L/U_inf accumulation; v1 may show drift
5. **Wall-modeled y+** — sHM prism layer must produce y+=30-100
   on body surfaces; use `checkMesh -allTopology` to verify

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_010 row from "Active queue" to "Dispatched"
- [ ] Update `case_index.md` with case_010 status=dispatched
- [ ] Update `INDEX.md` kickoff list
- [ ] **10-case roster complete** — 5 deferred kickoffs in queue
      (003, 004, 005, 006, 007, 008, 009, 010 = 8 cases minus
      002a/b active = 8 deferred)
- [ ] When sub-session extracts LES infrastructure (fvSchemes
      writer, turbulence writer, field-averaging, Q-criterion
      post-processor), evaluate for promotion
