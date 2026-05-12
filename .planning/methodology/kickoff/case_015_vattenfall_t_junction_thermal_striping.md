# Case 015 · Vattenfall T-Junction Thermal Striping · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS,
> 160k tok single-round emit). Validated 2026-05-08 — see
> `case_015_validation.md`. PASS.
>
> **Phase 3 #1 of industrial-extension batch** — first compound
> numerics root (LES + CHT). Combines case_002b CHT + case_010
> LES into Vattenfall OECD/NEA T-junction benchmark.
>
> **A2 advisor LANDED 2026-05-08 BUT scope-narrow per V25**: D5
> (60 μm weld misalignment) verification is algorithm-runs-cleanly
> evidence; A2-v2 sub-DEC pending
> (`patches/draft_a2_v2_gap_detection_2026-05-08.md`).

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_015_vattenfall_t_junction_thermal_striping**.

**Phase 3 #1** — first compound numerics root (LES + CHT).

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
15 prior cases (002a/b + 003-014).

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
3. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
4. `.planning/case_proposal_queue.md`
5. **`.planning/methodology/kickoff/case_002b_codex_response.md`** — CHT inheritance
6. **`.planning/methodology/kickoff/case_010_codex_response.md`** — LES inheritance
7. **`.planning/methodology/kickoff/case_011_codex_response.md`** — multi-region cellZone
8. `.planning/case_profiles/case_002b_apu_bay_cht.md`
9. `.planning/methodology/industrial_case_solver_findings.md` (V14/V15 + LES findings if 010 sedimented)
10. `.planning/methodology/knowledge_status_convention.md`
11. `.planning/methodology/kickoff/case_015_codex_response.md`
12. `.planning/methodology/kickoff/case_015_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating
3. Use `virtual_interface_detector` for D5 (with [QUESTIONABLE] marker per V25)
4. Do NOT redesign — execute Codex brief; round-cap=3
5. **chtMultiRegionFoam LES variant** (NOT buoyantPimpleFoam single-region — wall thermal capacity required for fatigue prediction)
6. **Wall-modeled LES at y+ 30-100** (NOT wall-resolved DNS)
7. **No new defects outside D1-D10**
8. **No Ahmed/NACA/Sajben** (Lane B; not relevant)
9. Do NOT add `isSame()` fast-path (V2 lesson)

## Case identifier
`case_015_vattenfall_t_junction_thermal_striping` · solver-class
**chtMultiRegionFoam LES (WALE)** · numerics-class
**incompressible-LES-CHT** (NEW root — compound from 002b + 010)

## Codex brief summary
- Component: Vattenfall T-junction (OECD/NEA benchmark)
- Geometry: main pipe ID=140 mm, branch ID=100 mm, 90° T-junction,
  wall thickness 6 mm SS304, upstream ≥1000 mm, downstream
  ≥2000 mm (per spec for striping development zone)
- Operating point:
  - main_inlet (cold): T=19°C, ṁ=9.0 kg/s
  - branch_inlet (hot): T=36°C, ṁ=6.0 kg/s
  - SS304: ρ=7900, cp=500, k=15 W/m·K
- LES config:
  - chtMultiRegionFoam + WALE LES model
  - nutUSpaldingWallFunction (wall-modeled)
  - dt = 1e-4 s (CFL ≤ 1)
  - y+ target 30-100
  - statistics: ≥ 5 flow-throughs after settling, ≥ 10 for FFT
  - 10 thermocouple probes Tx10..Tx100 along downstream
- Defect: **D5** — 60 μm pipe-pipe weld interface misalignment
  at T-junction welded joint
- Effort: 12-15h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 130 LOC, deterministic. CadQuery
parametric, exports STEP with 3 fused regions + thermocouple
sampling probe metadata.

```bash
cd ~/Desktop/case_015_vattenfall_t_junction
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## LES + CHT setup (case_015 main work)

### `00_check_regions.py`
Verify STEP has 3 region bodies: region_main_fluid +
region_branch_fluid + region_wall_solid.

### `02_split_mesh_regions.py`
blockMesh + sHM + `splitMeshRegions -cellZones -overwrite`.

### `03_write_regionProperties.py`
```
regions
(
    fluid (region_main_fluid region_branch_fluid)
    solid (region_wall_solid)
);
```

### `04_write_thermophysical.py`
- region_main_fluid: water at 19°C
- region_branch_fluid: water at 36°C
- region_wall_solid: SS304 (hSolidThermo)

### `05_write_BCs.py`
**Fluid patches**:
- main_inlet: flowRateInlet ṁ=9.0, T=292.15 K
- branch_inlet: flowRateInlet ṁ=6.0, T=309.15 K
- main_outlet: pressureOutlet
**Conjugate interfaces**:
- both fluid↔solid: turbulentTemperatureCoupledBaffleMixed
**Outer wall** (region_wall_solid outer surface): adiabatic
zeroGradient T (or fixedHeatFlux 0).

### `06_write_LES_fvSchemes.py`
- ddt: backward (or CrankNicolson 0.5)
- divSchemes: linearUpwindV grad(U) (or LUST grad(U))
- gradSchemes: Gauss linear
- laplacianSchemes: Gauss linear corrected

### `07_write_LES_turbulenceProperties.py`
```
simulationType  LES;
LES
{
    LESModel    WALE;
    delta       cubeRootVol;
    cubeRootVolCoeffs { deltaCoeff 1; }
    turbulence  on;
    printCoeffs on;
}
```

### `08_write_field_average.py`
controlDict function objects:
- fieldAverage1 with timeStart = settling time
- T_probe sampling at Tx10..Tx100 every 0.001 s

### `09_run_solver.sh`
1. potentialFoam initialization
2. chtMultiRegionFoam transient at dt=1e-4 s
3. Run to settling time (5 flow-throughs)
4. Restart with fieldAverage active, run ≥ 10 flow-throughs

### `10_compute_wall_T_statistics.py`
- mean T at Tx10..Tx100
- RMS T' at Tx10..Tx100
- FFT spectrum at one downstream station

## Defect verification

### D5 (60 μm pipe-pipe weld misalignment) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: A2 v1 cannot field-validate
> 60 μm offset per V25 placeholder semantics. A2-v2 draft pending.

**Step 1**: FreeCAD measurement of wall-wall offset at weld toe.
**Step 2**: A2 advisor exercise (expected matched=True, 12th
cross-topology PASS).
**Step 3**: V-finding judgment per knowledge_status_convention.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_015_vattenfall_t_junction.md`
2. V-series append: LES+CHT joint statistics convergence,
   wall-modeled LES + CHT wall heat-flux interpretation,
   long-time statistic sample size for fatigue spectrum,
   multi-region time-step coordination. ALSO: **12th D1/D5
   cross-topology PASS** (with V25 caveat).
3. Playbook S15+ candidates:
   - "LES+CHT statistics not converged → extend averaging window
     to ≥10 flow-throughs"
   - "Wall T-residual oscillation → check wall-function vs
     CHT interface compatibility"
4. Stale-assumption fixes: case_002b/case_010 templates may need
   LES+CHT joint variants. Commit tag pattern.
5. Artifact extraction (3-4 likely):
   - `wall_temperature_striping_post_processor.py`
   - `T_spectrum_extractor.py`
   - `thermal_fatigue_advisor.py`
6. RAG corpus: 5 artifacts.

## Sandbox structure
```
~/Desktop/case_015_vattenfall_t_junction/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-014. Co-author Claude Opus 4.7.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (3-4 likely)
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  promote to wall-resolved LES (DNS scope), single-region
  promotion (CHT required for fatigue), exceed 15h

## Known issues
1. **A2 [QUESTIONABLE]** — D5 algorithm-runs-cleanly NOT
   field-validation
2. **First compound numerics root** — LES + CHT joint behavior
   may surface 2-3 NEW V-findings beyond inheritance
3. **Long-time statistics** — fatigue spectrum requires ≥10
   flow-throughs after 5 settling; budget compute carefully
4. **Wall-modeled LES** — y+ 30-100 means prism-layer mesh
   resolution at fluid-solid interface critical
5. **Multi-region time-step** — fluid LES dt~1e-4 vs solid
   implicit dt may need coordination

## Strategic role within batch

After case_015 lands, project demonstrates:
- LES + CHT compose into compound numerics root (validates
  numerics-class-combination methodology)
- T-spectrum + RMS T' post-processors for fatigue analysis
- 12th D1/D5 cross-topology A2 algorithm-PASS
- New industry KPI: thermal-fatigue stress estimate (nuclear /
  steam plant industry)

This is **first compound numerics root**; case_016 (compressible-
DES = 006 + 010) is **second compound root**. Phase 3 close
after both land.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_015 to Dispatched
- [ ] Update case_index.md
- [ ] Update INDEX.md
- [ ] When sub-session reports D5 A2 outcome: 12th cross-topology
      PASS (still [QUESTIONABLE])
- [ ] When sub-session extracts wall_T / FFT / fatigue post-
      processors: evaluate promotion
