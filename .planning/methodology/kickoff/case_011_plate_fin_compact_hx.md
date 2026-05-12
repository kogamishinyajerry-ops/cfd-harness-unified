# Case 011 · Plate-Fin Compact HX · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.5 xhigh, 86gs R0
> design + gpt-5.4 high, CRS R1 emit · 86gs hit 429 mid-emit).
> Validated 2026-05-08 — see `case_011_validation.md`. PASS.
>
> **First case in NEW STRATEGIC BATCH (Phase 1 #1)** per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> The new batch pivots from research-benchmark to
> industrial-service-market cases. case_011 inherits 002b CHT
> machinery, extends to multi-stream.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25** (open · sourced by case_005 v2 disambiguation, captured
> in harvest cycle 002): A2's `_run_shared` returns `matched=True`
> with hardcoded placeholder fields regardless of actual gap
> distance. D5 exercise on 30μm plate offset produces
> algorithm-runs-cleanly evidence, NOT gap-detection
> field-validation. A2-v2 sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_011_plate_fin_compact_hx**.

This is the **first case in Phase 1 of the industrial-extension
batch** (case_011-020). Original 10-case roster (002a/b + 003-010)
covered all numerics-class roots; this batch pivots from
research-benchmark cases toward industrial-service-market cases.

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience.

Ten prior cases (numerics-class root coverage complete):
- case_002a (APU bay buoyantSimpleFoam): active
- case_002b (APU bay CHT chtMultiRegionFoam): active · CHT
  machinery validated; case_011 inherits Pattern 6 directly
- case_003 (CRM-HLS, external high-Re): active · v1 paused on V20
  unit-scale block
- case_004 (NREL Phase VI rotor, MRF): active · v1 advisor done
- case_005 (RAE M2129 S-duct): active · v1+v2 ran; V16-V25 chain
  including V25 (A2 placeholder) OPEN
- case_006 (ONERA M6 transonic): dispatched-deferred
- case_007 (KCS ship VOF): dispatched-deferred
- case_008 (GLC305 Lagrangian): dispatched-deferred
- case_009 (Sandia Flame D): dispatched-deferred
- case_010 (DrivAer LES): dispatched-deferred · final original-roster case

Your case is **first in the NEW BATCH (Phase 1 #1)** per
`.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
You execute a **multi-stream CHT** workhorse — gas-turbine /
APU-style air-air compact recuperator.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
   — strategic SSOT for the new batch
3. `.planning/case_proposal_queue.md`
4. `.planning/case_profiles/case_002b_apu_bay_cht.md` — your direct
   inheritance source (chtMultiRegionFoam machinery, conjugate BC
   patterns, regionProperties scaffolding)
5. `.planning/methodology/industrial_case_solver_findings.md`
   (Pattern 6: case_011 inherits V14 + V15 from case_002b CHT but
   NOT V3-V13; multi-stream is a NEW numerics root extension)
6. `.planning/methodology/solver_convergence_playbook.md`
7. `.planning/methodology/rag_corpus_format.md`
8. **`.planning/methodology/knowledge_status_convention.md`**
   (NEW · 2026-05-08 harvest 002) — defines `[QUESTIONABLE]` /
   `[REFUTED]` / `[SUPERSEDED]` / `[VALIDATED]` markers
9. `.planning/cross_cuts/v_series_2026-05-08.md` (V-series snapshot)
10. `.planning/harvest_reports/2026-05-08_harvest_002.md` (cycle 002
    findings — A2 capability framing notes)
11. `.planning/methodology/kickoff/case_011_codex_response.md`
    (5 deliverables: engineering brief / CAD script / STEP path /
    parts manifest / defect manifest)
12. `.planning/methodology/kickoff/case_011_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (for D8 — LANDED;
     case_011 is **7th in cross-topology arc**, post-`[VALIDATED]`
     6-of-6 confirmation)
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D5 — A2
     LANDED 2026-05-08 a09ae0a, BUT see `[QUESTIONABLE]` marker
     in D5 verification section below; A2 v1 cannot detect 30μm
     offset)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier` (rarely needed since CAD is Tier-3
     parametric)
   - DO NOT re-implement these case-locally
4. Do NOT redesign the case — execute Codex's brief; revision
   request only if fundamentally unworkable (round-cap=2)
5. **Steady chtMultiRegionFoam** in v1; chtMultiRegionPimpleFoam
   only as v2 fallback if residual oscillation persists (V13 pattern)
6. **No new defects outside D1-D10**
7. **No Ahmed/NACA/Sajben** (Lane B exclusions; not relevant here
   anyway)
8. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
   (V2 lesson preserved)

## Case identifier
`case_011_plate_fin_compact_hx` · solver-class
**chtMultiRegionFoam_steady (multi-stream)** · numerics-class
**steady-laminar-CHT-multi-stream** (NEW root — partial inheritance
from 002b for multi-region machinery; multi-stream + laminar
regime is genuinely new)

## Codex brief summary
- Component: compact plate-fin air-air cross-flow recuperator
  (gas-turbine / APU thermal recovery flavor; bank ID promoted
  A1 → A1b_compact_heat_exchanger)
- Geometry envelope: L=180mm × W=120mm × H=55mm
- Plate thickness 0.8mm, fin gap 2.5mm
- Hot channels: 20 per layer × 2 layers; cold channels: 36 per
  layer × 1 layer (cross-flow, both fluids unmixed)
- Hot D_h = 4.14mm, Cold D_h = 4.32mm
- Operating point: T_h_in=420K, T_c_in=300K
  - ṁ_hot = 0.004 kg/s (Re_hot ≈ 1149, laminar)
  - ṁ_cold = 0.0045 kg/s (Re_cold ≈ 711, laminar)
- Predicted ε ≈ 0.466, Q ≈ 225 W (Kays-London ε-NTU)
  - T_h_out ≈ 364K, T_c_out ≈ 350K
  - Δp_hot ≈ 168 Pa, Δp_cold ≈ 26 Pa
  - ±20% tolerance: ε ∈ [0.37, 0.56], Q ∈ [180W, 270W]
- Solver v1: chtMultiRegionFoam steady, 2 fluid + 1 solid region
- v2 fallback: chtMultiRegionPimpleFoam if oscillation
- Defects: **D8** (0.6mm fin in rear-1/3 cold matrix) +
  **D5** (30μm offset on separator_plate_3_4 in rear-1/3)
- Effort: 10–12h, ~3 versions

## Codex CAD script (deliverable 2)

Save at `scripts/build_cad.py`. 492 LOC, deterministic. CadQuery
parametric, exports STEP labeled multi-body assembly with 3
named bodies:

- `region_hot_fluid` (single fused solid: hot channels + 2 hot
  manifolds)
- `region_cold_fluid` (single fused solid: cold channels + 2 cold
  manifolds)
- `region_solid` (single fused aluminum body: 4 plates + hot fins
  + cold fins, including D8 + D5)

```bash
cd ~/Desktop/case_011_plate_fin_compact_hx
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

Determinism check (must produce byte-identical STEP):
```bash
rm -f /tmp/case011_a.step /tmp/case011_b.step
python scripts/build_cad.py --out /tmp/case011_a.step
python scripts/build_cad.py --out /tmp/case011_b.step
shasum -a 256 /tmp/case011_a.step /tmp/case011_b.step
cmp -s /tmp/case011_a.step /tmp/case011_b.step
```

## Multi-region CHT setup (case_011 main work)

### `00_check_regions.py` (NEW — multi-stream specific)
Verify the STEP has exactly 3 named bodies matching the parts
manifest. Bail loudly if mismatch.

```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  print(sorted(x.Label for x in doc.Objects))"
# Expected: ['region_cold_fluid', 'region_hot_fluid', 'region_solid']
```

### `02_split_mesh_regions.py`
Use OpenFOAM's `splitMeshRegions` with cellZone-driven split:
1. blockMesh background + sHM with all 3 region cellZones
2. `splitMeshRegions -cellZones -overwrite` to produce
   `constant/region_hot_fluid/`, `constant/region_cold_fluid/`,
   `constant/region_solid/`

### `03_write_regionProperties.py`
```
regions
(
    fluid       (region_hot_fluid region_cold_fluid)
    solid       (region_solid)
);
```

### `04_write_thermophysical.py` per region
- `region_hot_fluid`: hPolynomial / pureMixture / air, ρ=0.80,
  μ=2.4e-5, cp=1007, k=0.036
- `region_cold_fluid`: hPolynomial / pureMixture / air, ρ=1.18,
  μ=1.9e-5, cp=1007, k=0.027
- `region_solid`: hSolidThermo / aluminum_6061, ρ=2700, cp=896,
  k=205

### `05_write_BCs.py` per region
**Fluid patches** (4 total across the 2 fluid regions):
- `hot_inlet`: `flowRateInletVelocity` ṁ=0.004, `T fixedValue 420`
- `hot_outlet`: `pressureOutlet` p=0
- `cold_inlet`: `flowRateInletVelocity` ṁ=0.0045, `T fixedValue 300`
- `cold_outlet`: `pressureOutlet` p=0

**Conjugate interfaces** (both fluid↔solid):
- type `compressible::turbulentTemperatureCoupledBaffleMixed`
- Tnbr T, value $internalField, kappaMethod fluidThermo (on fluid
  side) / solidThermo (on solid side)

### `06_write_fvSchemes.py`
Steady laminar settings:
- ddt: `steadyState`
- divSchemes: `Gauss linearUpwind grad(U)`, `Gauss limitedLinear 1`
  for energy/T
- gradSchemes: `Gauss linear`
- laplacianSchemes: `Gauss linear corrected`

### `07_write_fvSolution.py`
- p_rgh: GAMG (or PCG with DIC); rtol 1e-5
- U: smoothSolver / GaussSeidel; rtol 1e-6
- h / e (energy): PBiCGStab / DILU; rtol 1e-6
- relaxationFactors: U=0.7, p_rgh=0.3, h=0.95, T=0.95

### `08_run_solver.sh`
```bash
chtMultiRegionFoam 2>&1 | tee log.solver
```
- v1: steady; convergence target residuals < 1e-5; monitor
  `forceCoeffs` proxy via patch-integrated h/T
- v2 fallback: switch to `chtMultiRegionPimpleFoam`,
  `nOuterCorrectors 5`, `relaxationFactors` slightly tighter

### `09_compute_epsilon_ntu.py`
Tail-average outlet T over last 10% of converged steady steps:
```
ε = (T_h_in - T_h_out) / (T_h_in - T_c_in)   for C_h = C_min
Q = ṁ_h × cp × (T_h_in - T_h_out)
```
Compare to predicted ε=0.466 ± 20%, Q=225W ± 20%.

### `10_compute_pressure_drop.py`
Patch-integrated total pressure delta on each fluid:
```
Δp_hot = p_hot_inlet - p_hot_outlet
Δp_cold = p_cold_inlet - p_cold_outlet
```
Compare to 168Pa / 26Pa with K_manifold=2.5.

### `11_compute_h_and_eta_fin.py`
- Local h(x): partition hot stream at 5 cross-flow stations,
  compute h = q_wall / (T_wall - T_bulk)
- Fin efficiency η_fin: integrate (T_fin_tip - T_bulk) /
  (T_fin_root - T_bulk) on D8-free front-2/3 zone; expect ~0.9
- Manifold uniformity index: σ(ṁ_per_channel) / ṁ_per_channel_mean
  at hot inlet face; expect < 0.15

## Defect verification

### D8 (rear-1/3 cold-fin thickness 0.6mm) — thin_wall_advisor LANDED

```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['region_solid'].Shape.BoundBox; \
  print('region_solid bbox:', bb.XLength, bb.YLength, bb.ZLength)"
# Then run --check-d8:
python scripts/build_cad.py --check-d8
# Expected: 'D8 check: cold fin rear-third starts at y=80.000 mm; rear-third fin thickness=0.600 mm.'
```

Then exercise main-project advisor:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="cold_fin_rear_third",
                            bbox_dimensions=(0.0006, W_MM_REAR_THIRD_M, COLD_CH_HEIGHT_M))],
    refinement_levels={"cold_fin_rear_third": (1, 2)},
    background_cell_size=YOUR_BG_CELL_SIZE_METERS,
)
print(warnings)  # expect 'critical' (0.6mm thickness < min_cells_per_thickness threshold)
```

**7-case cross-topology validation arc**: case_002a (curved CATIA
Frame) + case_003 (planar CadQuery thin_access_plate) + case_004
(rotating-machinery yaw_sensor_shim 0.75mm) + case_007 (ship
transom plate 0.80mm) + case_008 (airfoil TE tab 0.80mm) +
case_010 (vehicle underbody cover sub-mm) + **case_011 (HX cold
fin 0.6mm)**. After case_010 lands, V10/V23 should be `[VALIDATED]`
6-of-6; case_011 confirms HX-topology robustness as 7th data
point. If divergent on case_011, flag context-sensitivity
V-finding for compact-HX fin geometry.

### D5 (separator_plate_3_4 30μm rear-1/3 offset) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: "exercise A2; expect detection of
> 30μm plate offset" framing assumes a capability A2 v1 does NOT
> have. A2 LANDED for V2 pattern (shared-interface confirmation
> on non-manifold STEP), NOT D5 pattern (sub-mm offset detection).
> Per V25 (open · `industrial_case_solver_findings.md#V25`),
> A2's `_run_shared` returns `matched=True` with hardcoded
> placeholder `bbox_overlap_fraction=1.0` /
> `area_diff_fraction=0.0` regardless of actual offset. A2-v2
> sub-DEC drafted (`.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`)
> adds `inter_face_gap_mm` field to `DetectedInterface`.
> Verification pending: A2-v2 lands AND case_011 sub-session
> re-runs D5 falsification on plate-3-4 separator. To resolve:
> A2-v2 sub-DEC merged. Until then, your A2 PASS confirms only
> that `_run_shared` runs cleanly on plate-plate adjacency —
> NOT that A2 detects the 30μm offset as a defect.

**Step 1 — manual ground truth via FreeCAD**:

```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print('region_solid bbox includes 30um offset on rear-third of separator_plate_3_4')"

python scripts/build_cad.py --check-d5
# Expected: 'D5 check: separator_plate_3_4 rear-third x-offset=30.0 um for y>=80.000 mm.'
```

**Step 2 — exercise landed A2 advisor**:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec, FaceGeometry, BodyGeometry,
)
spec = InterfaceSpec(
    name="separator_3_4__plate_offset_interface",
    mode="shared",
    bodies=("separator_plate_3_4_front", "separator_plate_3_4_rear_offset"),
)
result = detect_virtual_interfaces(bodies=[plate_front_body, plate_rear_offset_body],
                                   specs=[spec])
# Expect: matched=True (per V21/V22 pattern) BUT this PASS is
# NOT field-validation of 30μm offset detection per V25.
```

**Step 3 — V-finding judgments**:

- If `matched=True`: document as "case_011 cross-topology PASS for
  `_run_shared` on HX plate-plate adjacency"
  (algorithm-runs-cleanly, NOT offset-detection per V25). Flag for
  A2-v2 falsification once sub-DEC lands.
- If `matched=False`: NEW V-finding documenting which geometric
  property of plate-plate offset fails `find_face_facing_target`.
- Do NOT propose `isSame()` fast-path (V2 lesson).
- Apply `[QUESTIONABLE 2026-05-08]` marker in your evidence —
  do NOT write "A2 field-validated 30μm offset detection".

## Six per-case standard moves

1. Reference profile at `case_profiles/case_011_plate_fin_compact_hx.md`
2. V-series append: chtMultiRegionFoam multi-stream startup,
   3-region splitMeshRegions correctness, conjugate interface
   T-residual oscillation, manifold uneven flow distribution,
   ε-NTU CFD-vs-prediction within ±20% band, fin efficiency
   measurement reproducibility. ALSO: **A2 `_run_shared` behavior
   on HX plate-plate topology** (above); **thin_wall 7th-case
   cross-topology check** (above)
3. Playbook S14+ candidates:
   - "ε deviates >20% from Kays-London → check manifold uniformity"
   - "Conjugate residual oscillation → switch to PimpleFoam +
      under-relax T 0.95 → 0.85"
   - "Δp_hot off prediction → check K_manifold loss model in
      brief vs CFD-resolved manifold geometry"
   - "T_solid spatial discontinuity at conjugate interface → check
      sampling owner side per V14 pattern"
4. Stale-assumption fixes: `0.orig` template needs multi-region
   variants (per-region 0/U, 0/T, 0/p, 0/p_rgh); regionProperties
   needs documented multi-stream pattern. Commit tag:
   `corrects-assumption: <X>, surfaced-by: case_011-V<n>`
5. Artifact extraction (3-4 likely):
   - `multi_stream_region_property_writer.py`
   - `epsilon_ntu_post_processor.py`
   - `manifold_uniformity_post_processor.py`
   - `fin_efficiency_post_processor.py`
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_011_plate_fin_compact_hx/
├── README.md, Makefile, .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── templates/{regionProperties_multi_stream.j2 (NEW),
│              thermophysicalProperties_air_hot.j2 (NEW),
│              thermophysicalProperties_air_cold.j2 (NEW),
│              thermophysicalProperties_aluminum.j2 (NEW),
│              0.orig.j2 multi-region extension,
│              fvSchemes_steady_laminar_cht.j2,
│              fvSolution_steady_laminar_cht.j2,
│              ...}
├── scripts/{00..11 + build_cad.py}
├── case/    (gitignored)
└── evidence/<v>/{REPORT.md, epsilon_ntu_comparison.md,
                  manifold_uniformity.md, fin_efficiency.md}
```

## Sediment + commit convention
Same as case_002a/b. `confidence: <high|med|low>` trailer.
Co-author Claude Opus 4.7. `case/` runtime gitignored.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated 30μm offset" if you only confirmed
`_run_shared` runs cleanly. Mark D5 with `[QUESTIONABLE 2026-05-08]`
until A2-v2 lands.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (3-4 likely), advisor-bias fixes, add
  multi-region fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  redistribute generated STEP externally (CAD is parametric,
  no license issue, but main-session policy is sandbox-internal),
  add `isSame()` fast-path to `virtual_interface_detector` (V2),
  exceed 12h estimated effort

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D5 exercise
   produces algorithm-runs-cleanly evidence, NOT offset-detection
   field-validation. See `[QUESTIONABLE]` marker in D5 verification
   section. A2-v2 sub-DEC drafted; after it lands, case_011 v2
   re-runs D5 falsification.
2. **D8 thin_wall_advisor 7th-case** — case_011 extends
   cross-topology arc to HX-fin geometry (post-`[VALIDATED]`
   6-of-6 confirmation pending case_010 sediment). If consistent
   critical warning, case_011 confirms HX-topology robustness; if
   divergent, flag context-sensitivity V-finding.
3. **First multi-stream CHT for project** — 002b CHT machinery
   re-used (V14, V15 inheritance) but multi-stream BC bookkeeping
   + multi-fluid thermophysical setup is NEW. Expect 1-2 V-findings
   in this territory.
4. **Laminar regime** — Re_hot=1149, Re_cold=711 are below 2300.
   Do NOT use k-ε / k-ω-SST in v1 (will give wrong h_fluid).
   Use `simulationType laminar;`.
5. **Manifold geometry resolution** — CAD has tapered manifolds;
   sHM refinement near manifold tapers should resolve flow split.
   K_manifold=2.5 is a reference assumption; CFD-resolved Δp may
   show ±15% deviation.
6. **Industrial flavor** — recognizable as gas-turbine / APU
   air-air recuperator (Kays-London classical example).
   Do not be tempted to convert to water-glycol radiator
   (different scope; case_017 territory).

## Strategic role within new batch

After case_011 lands, the project demonstrates:
- chtMultiRegionFoam works on multi-stream cross-flow geometry
- Pattern 6 (numerics-class inheritance) extends from single-stream
  CHT to multi-stream CHT
- D5 (mis-aligned plate interface) becomes the third defect
  category exercised in the project (D1 + D8 + D5)
- ε-NTU comparison provides a clean engineering KPI tied to
  classical literature, demonstrating the harness can produce
  industrial-grade results

This unblocks Phase 1 #2 (case_012 HVAC diffuser) and Phase 2
(cases 013/014 centrifugal pump/compressor) per the strategic
roadmap.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_011 row from "Active queue (Proposed Phase 1)" to
      "Dispatched"
- [ ] Update `case_index.md` with case_011 status=active
- [ ] Update `INDEX.md` kickoff list with case_011 entry
- [ ] When sub-session reports D5 A2 outcome on plate-plate
      adjacency, flag for A2-v2 re-falsification once sub-DEC
      lands — do NOT mark V25 closed based on case_011 alone
- [ ] When sub-session reports D8 thin_wall outcome, evaluate
      against post-case_010 V10/V23 status (`[VALIDATED]` 6-of-6
      → 7-of-7 if consistent, or context-sensitivity V-finding if
      divergent)
- [ ] When sub-session extracts multi-stream CHT infrastructure
      (regionProperties writer, ε-NTU post-processor, manifold
      uniformity post-processor, fin efficiency post-processor),
      evaluate for promotion to main-project shared services
