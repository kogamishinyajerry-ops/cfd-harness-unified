# Case 012 · HVAC Supply Diffuser · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS, single
> round emit · 118k tokens). Validated 2026-05-08 — see
> `case_012_validation.md`. PASS.
>
> **Phase 1 #2 of industrial-extension batch** per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> Direct case_002a buoyantSimpleFoam inheritance, room-scale topology.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25**: D1 (0.35 mm slot gap) verification produces algorithm-
> runs-cleanly evidence, NOT gap-detection field-validation. A2-v2
> sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.
>
> **D7 first injection in project** — no LANDED advisor for face-
> orientation defects. Sub-session manually verifies via FreeCAD
> `Face.normalAt()`. Post-case_012 retro evaluates A4 advisor
> candidate.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_012_hvac_supply_diffuser**.

This is **Phase 1 #2** of the industrial-extension batch. Direct
case_002a buoyantSimpleFoam inheritance applied to commercial
office HVAC topology.

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience.

12 prior cases (original roster + Phase 1 #1):
- case_002a (APU bay buoyantSimpleFoam): active · v14 — your
  direct inheritance source
- case_002b (APU bay CHT): active · v2
- case_003-010: dispatched (5 with v1 sediment)
- case_011 (plate-fin compact HX): dispatched 2026-05-08

Your case is **first BuoyantSimpleFoam re-deployment outside APU
bay** — same numerics root, different industrial topology.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
3. `.planning/case_proposal_queue.md`
4. **`.planning/case_profiles/case_002a_apu_bay_buoyant.md`** —
   your direct inheritance source (buoyantSimpleFoam machinery,
   Boussinesq BC patterns, V3-V13 + S1-S13)
5. `.planning/methodology/industrial_case_solver_findings.md`
   (Pattern 6: case_012 inherits V3-V13 + S1-S13 directly; no
   NEW numerics root)
6. `.planning/methodology/solver_convergence_playbook.md`
7. `.planning/methodology/rag_corpus_format.md`
8. **`.planning/methodology/knowledge_status_convention.md`** —
   `[QUESTIONABLE]` marker on D1; D7 advisor-gap flag
9. `.planning/cross_cuts/v_series_2026-05-08.md`
10. `.planning/harvest_reports/2026-05-08_harvest_002.md`
11. `.planning/methodology/kickoff/case_012_codex_response.md`
12. `.planning/methodology/kickoff/case_012_validation.md`

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
5. **Steady buoyantSimpleFoam** in v1; chtMultiRegion fallback is
   v2 user-driven decision, NOT case design (do NOT promote to
   multi-region without user request)
6. **No new defects outside D1-D10**
7. **No Ahmed/NACA/Sajben** (Lane B; not relevant)
8. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
   (V2 lesson preserved)

## Case identifier
`case_012_hvac_supply_diffuser` · solver-class
**buoyantSimpleFoam (single-region)** · numerics-class
**compressible-buoyant-RANS** (already covered by 002a; this is
the **industrial-deployment** form, NOT a NEW root)

## Codex brief summary
- Component: 4-way ceiling diffuser commercial office
  (bank ID `B_HVAC_DIFFUSER_01`)
- Room: 6.0 m × 4.5 m × 3.0 m
- Supply: T=289.15 K (16 °C), U=2.6 m/s, slot width 10 mm
- Return: low-side-wall (pressureOutlet)
- Heat sources: 4 occupants × 75 W + equipment 200 W = 500 W total
- Predicted ADPI ≈ 85% (ASHRAE 55 / IEA Annex 20 design table)
  - target ADPI ≥ 80%
  - throw distance to T_50 ≈ 2.7 m
  - occupied-zone U_max < 0.25 m/s
  - vertical dT/dz near floor < 2 K/m
  - ΔT_ceiling-floor ≈ 3 K
  - CFD ADPI ± 10 percentage points expected
- Solver v1: buoyantSimpleFoam steady
- Defects: **D1** (0.35 mm gap diffuser_face_plate ↔ ceiling) +
  **D7** (louver_vane_2 rotated 38° from intended)
- Effort: 8-10h, ~3 versions

## Codex CAD script (deliverable 2)

Save at `scripts/build_cad.py`. 248 LOC, deterministic. CadQuery
parametric, exports STEP with named bodies/patches:

- `region_air` (single fused fluid region representing room interior)
- patches: ceiling, floor, wall_north/south/east/west,
  supply_inlet, return_outlet, diffuser_face_plate,
  louver_vane_0..3, occupant_0..3, equipment_patch

```bash
cd ~/Desktop/case_012_hvac_supply_diffuser
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

Determinism check:
```bash
rm -f /tmp/case012_a.step /tmp/case012_b.step
python scripts/build_cad.py --out /tmp/case012_a.step
python scripts/build_cad.py --out /tmp/case012_b.step
shasum -a 256 /tmp/case012_a.step /tmp/case012_b.step
cmp -s /tmp/case012_a.step /tmp/case012_b.step
```

## Single-region buoyant setup (case_012 main work)

### `00_check_region.py`
Verify the STEP has 1 fluid region body matching parts manifest.

```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  print(sorted(x.Label for x in doc.Objects))"
# Expected: includes 'region_air' + all named patches
```

### `02_blockmesh_shm.py`
Use blockMesh background (room envelope) + sHM with refinement
near diffuser geometry (slot scale ~10 mm) and near heat-source
patches.

### `03_write_thermophysical.py`
Air with Boussinesq buoyancy:
- thermoType: heRhoThermo / pureMixture / Boussinesq /
  hConst / specie / sensibleEnthalpy
- T_ref = 293.15 K, ρ_ref = 1.204, β = 0.00341 1/K, Pr = 0.71

### `04_write_BCs.py`
**Patches**:
- `supply_inlet`: flowRateInletVelocity (ṁ derived from U=2.6 m/s
  × A_slot, or U fixedValue), `T fixedValue 289.15`, `p_rgh
  zeroGradient`
- `return_outlet`: `pressureOutlet p_rgh fixedValue 0`,
  `T zeroGradient`, `U pressureInletOutletVelocity`
- ceiling/floor/walls: `noSlip`, `T zeroGradient`,
  `p_rgh fixedFluxPressure`
- diffuser_face_plate / louver_vane_*: `noSlip`,
  `T zeroGradient`, `p_rgh fixedFluxPressure`
- occupant_0..3: `noSlip`, `T externalWallHeatFluxTemperature`
  with q = 75 W / patch_area
- equipment_patch: `noSlip`, `T externalWallHeatFluxTemperature`
  with q = 200 W / patch_area

### `05_write_fvSchemes.py`
Steady mixed-convection settings (inherits 002a):
- ddt: `steadyState`
- divSchemes: `Gauss linearUpwind grad(U)`,
  `Gauss limitedLinear 1` for T
- gradSchemes: `Gauss linear`
- laplacianSchemes: `Gauss linear corrected`

### `06_write_fvSolution.py`
Inherits 002a; relaxationFactors U=0.7, p_rgh=0.3, T=0.95.

### `07_run_solver.sh`
```bash
buoyantSimpleFoam 2>&1 | tee log.solver
```
Convergence target residuals < 1e-5; monitor mass balance per
S12; monitor occupied-zone T statistics.

### `08_compute_adpi.py`
ADPI per ASHRAE 55:
1. Sample U + T on 27-point occupied-zone grid (1.1 m height,
   0.6 m from walls)
2. Effective Draft Temperature θ_ED = (T_local - T_ref) -
   8 × (U_local - 0.15)
3. ADPI = % of points where -1.7 ≤ θ_ED ≤ +1.1
4. Compare to predicted 85% ± 10 pp

### `09_compute_throw_distance.py`
Sample T along jet centerline downstream of supply_inlet;
locate T_50 (50% of (T_supply - T_return)) downstream distance.

### `10_compute_dumping_criterion.py`
Sample dT/dz near floor (z = 0 to z = 1.1 m); peak vertical
gradient < 2 K/m within occupied zone.

## Defect verification

### D1 (0.35 mm slot gap diffuser_face_plate ↔ ceiling) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: A2 v1 cannot field-validate 0.35 mm
> gap distance per V25 placeholder semantics. A2-v2 sub-DEC
> drafted (`patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> Until A2-v2 lands, A2 PASS = `_run_shared` runs cleanly on
> diffuser-ceiling adjacency, NOT field-validation of 0.35 mm.

**Step 1 — manual ground truth via FreeCAD**:
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['diffuser_face_plate'].Shape.distToShape(o['ceiling'].Shape)[0])"
```
Expected ≈ 0.35 mm.

**Step 2 — exercise landed A2 advisor**:
```python
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec,
)
spec = InterfaceSpec(
    name="diffuser__ceiling_interface",
    mode="shared",
    bodies=("diffuser_face_plate", "ceiling"),
)
result = detect_virtual_interfaces(bodies=[diffuser_body, ceiling_body],
                                   specs=[spec])
# Expect: matched=True (V25 placeholder pattern); 9th D1 cross-topology PASS
```

**Step 3 — V-finding judgments**:
- If `matched=True`: 9th D1 cross-topology PASS for A2
  `_run_shared`. Apply `[QUESTIONABLE 2026-05-08]` marker; do NOT
  claim gap-distance field-validated.
- If `matched=False`: NEW V-finding on what fails (ceiling
  patch geometry quirk?).
- Do NOT propose `isSame()` fast-path (V2 lesson).

### D7 (louver_vane_2 rotated 38° from intended) — NO LANDED ADVISOR

> **First D7 injection in project**. No advisor exists for
> face-orientation defects. Manual verification only.

**Step 1 — manual ground truth via FreeCAD**:
```python
import FreeCAD as App
import Import
doc = App.newDocument()
Import.insert('inputs/cad_codex_v1.step', doc.Name)
louver = next(x for x in doc.Objects if x.Label == 'louver_vane_2')
# Sample face normal
face = louver.Shape.Faces[0]  # primary face
normal = face.normalAt(0.5, 0.5)
# Compute angle vs intended (Codex documented intended_rotation_deg=180,
# actual=218, so 38° offset)
import math
intended_normal = ...  # per Codex defect manifest
dot_product = normal.dot(intended_normal)
angle_deg = math.degrees(math.acos(dot_product))
print(f"D7 louver_vane_2 actual angle: {angle_deg:.1f} deg")
```
Expected ≈ 38° offset from intended.

**Step 2 — V-finding**:
- Document as **NEW V-finding: D7 advisor gap (face-orientation
  defects have no automated detection path)**.
- Recommend post-case_012 retro evaluate A4 advisor candidate
  (face-normal vs intended-normal dot-product check).
- If 2+ Phase 1-4 cases inject D7 (012, possibly 016 cavity walls,
  020 filter shell), advisor sub-DEC becomes high-priority.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_012_hvac_supply_diffuser.md`
2. V-series append: HVAC supply jet detachment (Coanda breakdown),
   cold-jet dumping, ADPI sensitivity to D1 leakage, D7 jet
   deflection, occupied-zone stratification residual convergence,
   buoyant-RANS mass balance at multi-patch heat-source room.
   ALSO: **D7 advisor-gap V-finding** (above)
3. Playbook S15+ candidates:
   - "ADPI < target → check D1 leakage / D7 deflection / mesh
      near jet"
   - "Cold-jet dumping → increase supply U or modify diffuser
      pattern"
   - "Steady residual oscillation in stratified room → relax T
      0.95 → 0.85 OR fall back to buoyantPimpleFoam"
4. Stale-assumption fixes: 002a templates may need slot-jet BC
   variants; controlDict needs ADPI sampling function objects.
   Commit tag: `corrects-assumption: <X>, surfaced-by: case_012-V<n>`
5. Artifact extraction (3-4 likely):
   - `adpi_post_processor.py` (occupied-zone 27-point grid +
     θ_ED computation)
   - `diffuser_throw_calculator.py` (T_50 distance along jet
     centerline)
   - `room_uniformity_advisor.py` (dT/dz dumping criterion)
   - (optional) `face_orientation_advisor.py` (A4 candidate IF
      retro decides to land it)
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_012_hvac_supply_diffuser/
├── README.md, Makefile, .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── templates/{thermophysicalProperties_Boussinesq.j2,
│              fvSchemes_steady_buoyant.j2,
│              fvSolution_steady_buoyant.j2,
│              0.orig.j2 with adpi sampling probes,
│              controlDict.j2 with ADPI function object,
│              ...}
├── scripts/{00..10 + build_cad.py + check_gap.py +
│            check_face_normal.py}
├── case/    (gitignored)
└── evidence/<v>/{REPORT.md, adpi_report.md,
                  throw_distance.md, dumping_criterion.md}
```

## Sediment + commit convention
Same as case_002a/b. `confidence: <high|med|low>` trailer.
Co-author Claude Opus 4.7. `case/` runtime gitignored.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated 0.35 mm gap" if you only confirmed
`_run_shared` runs cleanly. Mark D1 with
`[QUESTIONABLE 2026-05-08]` until A2-v2 lands.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (3-4 likely), advisor-bias fixes, add HVAC
  fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  promote to chtMultiRegion without user request, add `isSame()`
  fast-path to `virtual_interface_detector` (V2),
  exceed 10h estimated effort

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D1 exercise
   produces algorithm-runs-cleanly, NOT field-validation. Apply
   `[QUESTIONABLE]` marker. A2-v2 sub-DEC drafted; after lands,
   case_012 v2 re-runs D1 falsification.
2. **D7 first injection — no advisor** — surface advisor-gap
   V-finding; manual FreeCAD verification only. Post-case retro
   evaluates A4 candidate.
3. **Steady stratified-room residual oscillation** — possible
   pseudo-steady per V13 pattern; v2 fallback to
   buoyantPimpleFoam if persistent.
4. **9th D1 cross-topology PASS** — confirms A2 `_run_shared`
   robustness across topologies (APU bay → CRM-HLS → NREL Phase
   VI → ONERA M6 → Sandia Flame D → ... → HVAC room). Strong
   evidence for V22 status upgrade (subject to V25 caveat).

## Strategic role within batch

After case_012 lands, the project demonstrates:
- buoyantSimpleFoam works on industrial-deployment HVAC topology
  (not just APU bay)
- Pattern 6 (numerics-class inheritance) extends from APU
  confined-bay buoyant to commercial-office room buoyant
- D7 (wrong-normal) becomes the project's **advisor-gap surfacer**
  → triggers post-case retro on A4 advisor candidate
- ADPI / throw-distance / dumping-criterion post-processors are
  HVAC-industry-recognizable engineering KPIs

This closes Phase 1 (cases 011 + 012). Phase 1 close triggers
harvest cycle 003. After harvest 003 + A2-v2 implementation,
Phase 2 begins (cases 013/014 turbomachinery).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_012 row from "Active queue (Proposed Phase 1)"
      to "Dispatched"
- [ ] Update `case_index.md` with case_012 status=active
- [ ] Update `INDEX.md` kickoff list with case_012 entry
- [ ] When sub-session reports D1 A2 outcome, count as 9th
      cross-topology PASS for A2 `_run_shared` (still
      `[QUESTIONABLE]` until A2-v2)
- [ ] When sub-session reports D7 outcome, **flag for harvest 003
      retro**: D7 advisor candidate (A4)
- [ ] When sub-session extracts ADPI / throw / dumping post-
      processors, evaluate for promotion to main-project shared
      services
- [ ] After case_012 sediment + case_011 sediment land: trigger
      Phase 1 close + harvest cycle 003
