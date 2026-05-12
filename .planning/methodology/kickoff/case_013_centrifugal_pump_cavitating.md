# Case 013 · Centrifugal Pump Cavitating · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.5 xhigh, 86gs R0
> design 125k tok + gpt-5.4 high, CRS R1 emit 69k tok · network
> disconnect mid-emit fallback). Validated 2026-05-08 — see
> `case_013_validation.md`. PASS.
>
> **Phase 2 #1 of industrial-extension batch** — first true
> industrial confined rotating machinery + first phase-change
> physics for project. Combines case_004 MRF + NEW cavitatingFoam.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25**: D1 (tip-clearance gap 0.5→0.8 mm) verification produces
> algorithm-runs-cleanly evidence, NOT gap-detection field-validation.
> A2-v2 sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.
>
> **D7 NO LANDED ADVISOR** — case_012 surfaced this; case_013 is
> 2nd D7 evidence point. Manual FreeCAD `Face.normalAt()`
> verification. Post-Phase-2 retro evaluates A4 advisor candidate.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_013_centrifugal_pump_cavitating**.

This is **Phase 2 #1** — first true industrial confined rotating
machinery (replaces case_004 wind-rotor with confined volute pump).
First cavitation phase-change physics for the project.

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.

13 prior cases (original 10-case roster + Phase 1):
- case_002a/b: APU bay buoyant + CHT (active)
- case_003-010: original roster (5 with v1 sediment)
- case_011 (plate-fin compact HX): dispatched 2026-05-08
- case_012 (HVAC supply diffuser): dispatched 2026-05-08

Your case extends case_004 MRF infrastructure + NEW phase-change
solver pipeline.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
3. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
4. `.planning/case_proposal_queue.md`
5. **`.planning/case_profiles/case_004_nrel_phase_vi_mrf.md`** —
   your direct MRF inheritance source (open rotor; case_013 is
   confined volute extension)
6. `.planning/methodology/industrial_case_solver_findings.md`
   (V22-V24 from case_004 inherit; V25 [QUESTIONABLE] applies to
   D1; cavitation phase-change is NEW)
7. `.planning/methodology/solver_convergence_playbook.md`
8. `.planning/methodology/rag_corpus_format.md`
9. **`.planning/methodology/knowledge_status_convention.md`** —
   D1 [QUESTIONABLE] · D7 advisor-gap
10. `.planning/cross_cuts/v_series_2026-05-08.md`
11. `.planning/methodology/kickoff/case_013_codex_response.md`
12. `.planning/methodology/kickoff/case_013_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D1 — A2
     LANDED 2026-05-08, BUT see `[QUESTIONABLE]` marker below)
   - For D7: **no LANDED advisor**. Manual FreeCAD
     `Face.normalAt()` verification only.
   - DO NOT re-implement these case-locally
4. Do NOT redesign the case — execute Codex's brief; revision
   request only if fundamentally unworkable (round-cap=3)
5. **Single-region simpleFoam + MRF cellZone** in v1; **NOT
   chtMultiRegion** (case_011 territory)
6. **cavitatingFoam in v2 only** after v1 head curve validates;
   do NOT skip v1 baseline
7. **No new defects outside D1-D10**
8. **No Ahmed/NACA/Sajben** (Lane B; not relevant)
9. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
   (V2 lesson preserved)

## Case identifier
`case_013_centrifugal_pump_cavitating` · solver-class
**simpleFoam+MRF (v1) / cavitatingFoam+MRF+Schnerr-Sauer (v2)** ·
numerics-class **incompressible-MRF-cavitating** (NEW root —
combines case_004 MRF + first phase-change physics)

## Codex brief summary
- Component: industrial water-treatment centrifugal pump
  (Tier-3 reference-derived from Energies 2019 12(11) 2088 class;
  bank ID `D_PUMP_CENTRIFUGAL_01`)
- Geometry:
  - D2 (impeller outer dia) = 250 mm
  - D1_eye = 100 mm, b2 (blade outlet width) = 20 mm
  - 6 backward-curved blades, β1=22°, β2=28°
  - Archimedean spiral volute with cutwater at θ=0°
  - Suction pipe ID=100 mm, L=500 mm axial
  - Discharge nozzle 200 mm tangential
  - Tip clearance baseline 0.5 mm uniform
- Operating point:
  - N = 2900 rpm (= 303.69 rad/s)
  - Q_BEP = 0.080 m³/s (≈ 288 m³/h)
  - H_BEP = 35 m
  - η_BEP = 0.78 (78%)
  - NPSHr_BEP = 4.5 m, NPSHr_0.8Q = 3.5 m
  - U2 = 37.96 m/s tip speed
- Working fluid: water at 25°C (ρ=997, μ=8.9e-4, p_v=3170 Pa abs)
- Turbulence model: k-ω-SST
- Solver v1: simpleFoam + MRF — head curve at Q/Q_BEP =
  0.6/0.8/1.0/1.2 (4 operating points)
- Solver v2: cavitatingFoam + MRF + Schnerr-Sauer at 0.8 Q_BEP
  with NPSHr = 3.5 m (cavitation map at lowest documented NPSHr)
- Defects:
  - **D1**: tip-clearance gap on blade_5 enlarged to 0.8 mm
    (+0.3 mm over 0.5 mm nominal)
  - **D7**: wrong-normal LE on blade_3, 22° rotation around
    chord axis
- Effort: 12-15h, ~3 versions

## Codex CAD script (deliverable 2)

Save at `scripts/build_cad.py`. 412 LOC, deterministic. CadQuery
parametric, exports STEP with named bodies/patches:

- `region_fluid` (single fused fluid body)
- `mrf_zone_impeller` (cylindrical cellZone, axis=z, ω=303.69 rad/s)
- patches: suction_inlet, discharge_outlet, blade_1..6,
  blade_tip_1..6, hub_disk, volute_shroud, volute_cutwater,
  volute_outer_wall, suction_pipe_wall, discharge_nozzle_wall

```bash
cd ~/Desktop/case_013_centrifugal_pump_cavitating
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

Determinism check (same pattern as case_011/012).

## Single-region MRF setup (case_013 main work — v1)

### `00_check_region.py`
Verify the STEP has 1 fluid region body matching parts manifest.

### `02_blockmesh_shm.py`
blockMesh background + sHM with refinement near impeller blades
(especially blade_tip_5 with 0.8 mm gap → ≥ 4 cells across) and
near volute cutwater.

### `03_write_MRFProperties.py`
Inherit case_004 pattern + `08b_write_mrf.py` from case_004 (if
extracted). MRF cellZone definition:
```
mrf_zone_impeller
{
    cellZone mrf_zone_impeller;
    active true;
    nonRotatingPatches (volute_shroud volute_cutwater volute_outer_wall
                       suction_pipe_wall discharge_nozzle_wall);
    origin (0 0 0);
    axis (0 0 1);
    omega 303.69;  // 2900 rpm
}
```

### `04_write_thermophysical.py` (v1)
water at 25°C single phase:
- thermoType: heRhoThermo / pureMixture / sensibleEnthalpy /
  hConst / specie / Sutherland-OFF (use constant μ for water)
- ρ = 997, μ = 8.9e-4, cp = 4182, k = 0.598

### `05_write_BCs.py`
**v1 (simpleFoam + MRF)**:
- `suction_inlet`: `totalPressure` with total head derived from
  NPSH spec (typically NPSHa ≈ 6.0 m for above-NPSHr operation;
  set p_total - ρ g h = required suction static head)
- `discharge_outlet`: `pressureOutlet` with stepped p_outlet to
  recover Q/Q_BEP = 0.6/0.8/1.0/1.2 (4 operating points)
- blade_*, blade_tip_*, hub_disk: rotating wall in MRF zone
- volute_shroud, volute_cutwater, volute_outer_wall: stationary
  noSlip
- suction_pipe_wall, discharge_nozzle_wall: stationary noSlip

### `06_write_fvSchemes.py` (v1)
Steady incompressible turbulent settings:
- ddt: `steadyState`
- divSchemes: `Gauss linearUpwind grad(U)`,
  `Gauss limitedLinear 1` for k, ω
- gradSchemes: `Gauss linear`
- laplacianSchemes: `Gauss linear corrected`

### `07_write_fvSolution.py` (v1)
- p: GAMG; rtol 1e-5
- U / k / ω: smoothSolver / GaussSeidel; rtol 1e-6
- relaxationFactors: U=0.7, p=0.3, k=0.7, ω=0.7

### `08_run_solver_v1.sh`
4-point head curve sweep:
```bash
for Q_factor in 0.6 0.8 1.0 1.2; do
    # update p_outlet for target Q
    simpleFoam 2>&1 | tee log.solver_Q${Q_factor}
done
```

### `09_compute_HQ_curve.py`
H = (p_total_outlet - p_total_inlet) / (ρ g)
η = (ρ g Q H) / (M_shaft × ω) where M_shaft is impeller torque
NPSHr_3% = head at which 3% drop from non-cavitating H occurs

## Cavitation v2 (case_013 NEW physics)

### `10_write_thermophysical_v2.py`
water + water_vapor mixture for cavitatingFoam:
- liquid: water (ρ=997, μ=8.9e-4)
- vapor: water_vapor (ρ_v=0.0173 at 25°C, μ_v=9.86e-6)
- saturation pressure: 3170 Pa absolute at 25°C

### `11_write_cavitatingFoam_BCs.py`
Adjust for two-phase mixture:
- alpha.water field (1.0 = liquid, 0 = vapor)
- inlet: alpha.water = 1.0 (pure liquid)
- outlet: zeroGradient
- Schnerr-Sauer model: n_nuclei=1e13, d_nucleus=1e-5

### `12_run_solver_v2.sh`
At 0.8 Q_BEP operating point, lower p_outlet to drive NPSHa down
to 3.5 m (NPSHr point). Run cavitatingFoam transient with
small dt to capture cavitation pocket development.

### `13_compute_cavitation_map.py`
- Vapor volume fraction iso-surface (α_water = 0.5 envelope)
- Suction-side cavitation inception location per blade
- Tip-clearance vapor localization at blade_5 (defect blade)
- Compare to NPSHr 3% head-drop criterion

## Defect verification

### D1 (tip-clearance 0.5→0.8 mm on blade_5) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: A2 v1 cannot field-validate
> 0.3 mm gap-difference per V25 placeholder semantics. A2-v2
> sub-DEC drafted (`patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> Until A2-v2 lands, A2 PASS = `_run_shared` runs cleanly on
> blade_tip_5 ↔ volute_shroud adjacency, NOT field-validation
> of the 0.3 mm gap differential.

**Step 1 — manual ground truth via FreeCAD**:
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  # blade_tip_5 ↔ volute_shroud at 4 angular positions
  print(o['blade_tip_5'].Shape.distToShape(o['volute_shroud'].Shape)[0])"
```
Expected ≈ 0.8 mm at blade_tip_5; ≈ 0.5 mm at blade_tip_1..4,6.

**Step 2 — exercise landed A2 advisor**:
```python
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec,
)
spec = InterfaceSpec(
    name="blade_tip_5__volute_shroud_interface",
    mode="shared",
    bodies=("blade_tip_5", "volute_shroud"),
)
result = detect_virtual_interfaces(bodies=[blade_tip_5_body, volute_shroud_body],
                                   specs=[spec])
# Expect: matched=True (V25 placeholder pattern); 10th D1 cross-topology PASS
```

**Step 3 — V-finding judgments**:
- If `matched=True`: 10th D1 cross-topology PASS for A2
  `_run_shared`. Apply `[QUESTIONABLE 2026-05-08]` marker.
- If `matched=False`: NEW V-finding.
- Do NOT propose `isSame()` fast-path (V2 lesson).

### D7 (blade_3 LE rotated 22° from intended) — NO LANDED ADVISOR

> **2nd D7 injection in project** (case_012 was 1st). Advisor-
> gap evidence accumulating. Post-Phase-2 retro should evaluate
> A4 face-orientation advisor candidate.

**Step 1 — manual ground truth via FreeCAD**:
```python
import FreeCAD as App
import Import
doc = App.newDocument()
Import.insert('inputs/cad_codex_v1.step', doc.Name)
blade = next(x for x in doc.Objects if x.Label == 'blade_3')
le_face = blade.Shape.Faces[0]  # leading-edge face (verify which)
normal = le_face.normalAt(0.5, 0.5)
intended_normal = ...  # per Codex defect manifest reference
import math
dot_product = normal.dot(intended_normal)
angle_deg = math.degrees(math.acos(abs(dot_product)))
print(f"D7 blade_3 LE actual angle: {angle_deg:.1f} deg")
```
Expected ≈ 22° offset from intended.

**Step 2 — V-finding**:
- Document as **2nd D7 evidence** for advisor-gap pattern.
- Confirm A4 face-orientation advisor candidate viability across
  HVAC (case_012) + turbomachinery (case_013) topologies.
- Post-Phase-2 retro: evaluate A4 sub-DEC priority based on
  case_013 + 014 + 016 + 020 D7/D9 cumulative evidence.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_013_centrifugal_pump_cavitating.md`
2. V-series append: confined-volute MRF cutwater interaction,
   tip-leakage capture grid sensitivity, NPSH inlet specification,
   cavitation phase-change BC pathology, Schnerr-Sauer numerical
   stability, frozen-rotor vs sliding-mesh accuracy. ALSO:
   **2nd D7 advisor-gap evidence**, **10th A2 cross-topology
   PASS**.
3. Playbook S15+ candidates:
   - "H(Q) curve deviates >10% → check volute hydraulic resistance"
   - "Tip-leakage smeared → refine blade_tip cells to ≥ 4 across gap"
   - "Cavitation onset wrong → verify gauge/absolute pressure
      bookkeeping in NPSH inlet spec"
   - "cavitatingFoam diverges → relax Schnerr-Sauer source terms
      OR reduce dt"
4. Stale-assumption fixes: case_004 MRFProperties writer may
   need cavitation-fluid mixture variant. Commit tag:
   `corrects-assumption: <X>, surfaced-by: case_013-V<n>`
5. Artifact extraction (4-5 likely):
   - `pump_curve_generator.py` (H-Q-η characteristic)
   - `cavitation_advisor.py` (vapor map post-processor)
   - `npsh_post_processor.py` (NPSHr 3% extraction)
   - `cellzone_volute_audit.py` (MRF zone boundary check)
   - (optional) `face_orientation_advisor.py` (A4 candidate IF
      Phase-2 retro lands it after multi-case D7 evidence)
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_013_centrifugal_pump_cavitating/
├── README.md, Makefile, .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── templates/{MRFProperties_v1.j2,
│              thermophysicalProperties_water_25C.j2,
│              thermophysicalProperties_cavitating_mixture.j2 (NEW),
│              fvSchemes_steady_simpleFoam_MRF.j2,
│              fvSchemes_transient_cavitatingFoam.j2 (NEW),
│              fvSolution_steady_pump.j2,
│              fvSolution_transient_cavitating.j2 (NEW),
│              0.orig.j2 with cavitation alpha.water field,
│              ...}
├── scripts/{00..13 + build_cad.py + check_d1_gap.py +
│            check_d7_normal.py}
├── case/    (gitignored)
└── evidence/<v>/{REPORT.md, hq_curve.md, npsh_curve.md,
                  cavitation_map.md}
```

## Sediment + commit convention
Same as case_002a/b/011/012. `confidence: <high|med|low>` trailer.
Co-author Claude Opus 4.7. `case/` runtime gitignored.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated 0.3 mm tip-gap" if you only confirmed
`_run_shared` runs cleanly. Mark D1 with
`[QUESTIONABLE 2026-05-08]` until A2-v2 lands.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (4-5 likely), advisor-bias fixes, add
  cavitation fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  promote to chtMultiRegion (single-region + MRF cellZone),
  add `isSame()` fast-path to `virtual_interface_detector` (V2),
  redistribute industrial pump CAD reference (Tier-3 derived
  from open paper; bake-into-script keeps reproducibility),
  exceed 15h estimated effort

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D1 exercise
   produces algorithm-runs-cleanly, NOT field-validation. Apply
   `[QUESTIONABLE]` marker. A2-v2 sub-DEC drafted; after lands,
   case_013 v3 re-runs D1 falsification.
2. **D7 2nd injection — no advisor** — accumulating advisor-gap
   evidence. Post-Phase-2 retro evaluates A4 candidate.
3. **First cavitation phase-change for project** — Schnerr-Sauer
   pipeline + alpha.water mixture infrastructure all-new. Expect
   1-2 V-findings on cavitatingFoam BC pathology.
4. **Tip-leakage capture sensitivity** — 0.5/0.8 mm gap requires
   ≥ 4 cells across gap (≥ 0.1 mm cell size at gap). May force
   v3 mesh refinement.
5. **Frozen-rotor MRF limitation** — cutwater-blade interaction
   phase missed vs sliding-mesh. Acceptable for v1/v2 harness
   validation; document limitation.
6. **NPSH inlet bookkeeping** — gauge vs absolute pressure
   mix-up easy to miss. Document p_total at suction with
   explicit absolute-pressure reference.

## Strategic role within batch

After case_013 lands, the project demonstrates:
- simpleFoam+MRF works on confined-volute industrial topology
  (not just open-rotor case_004)
- cavitatingFoam works on industrial pump cavitation (first
  phase-change for project)
- Pattern 6 (numerics-class inheritance) extends from case_004
  open rotor to case_013 confined volute
- D1 + D7 sub-mm verification accumulates more advisor evidence
  (A2 10th cross-topology, D7 2nd advisor-gap)
- New industry-recognizable post-processors: H(Q) curve,
  η(Q) curve, NPSHr 3%, cavitation map

This unblocks Phase 2 #2 (case_014 NASA CC3 compressor stage).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_013 row from "Active queue (Proposed Phase 2)"
      to "Dispatched"
- [ ] Update `case_index.md` with case_013 status=active
- [ ] Update `INDEX.md` kickoff list with case_013 entry
- [ ] When sub-session reports D1 A2 outcome, count as 10th
      cross-topology PASS for A2 `_run_shared` (still
      `[QUESTIONABLE]` until A2-v2)
- [ ] When sub-session reports D7 outcome, **2nd D7 evidence
      point** for advisor-gap; post-Phase-2 retro evaluates
      A4 advisor candidate
- [ ] When sub-session extracts pump_curve / cavitation /
      NPSH post-processors, evaluate for promotion to main-
      project shared services
- [ ] After case_013 sediment + case_014 sediment land: trigger
      Phase 2 close + harvest cycle pattern (or join into
      harvest cycle 003 at end of Phase 4)
