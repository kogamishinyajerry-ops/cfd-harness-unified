# Codex Case-Design Request · case_015

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 3 #1 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: First **compound numerics root** (LES + CHT)
> for project — combines case_002b CHT + case_010 LES on
> Vattenfall T-junction OECD/NEA benchmark. Validates that
> compound roots inherit cleanly from single roots.
> **Backend**: 86gs gpt-5.5 xhigh primary; CRS gpt-5.4 high fallback.
> **Soft blockers**: case_011 multi-stream sediment helpful
> (multi-region cellZone bookkeeping) · case_010 LES sediment
> helpful (LES infrastructure indexed) · A2-v2 ideally landed for
> D5 weld-misalignment verification.

## Target

| field | value |
|---|---|
| case_id | `case_015_<short_name>` (Codex picks; suggested: `vattenfall_t_junction_thermal_striping`) |
| solver_class_target | LES + CHT compound: `chtMultiRegionFoam` LES variant OR `buoyantPimpleFoam` LES + walls-as-CHT-region. Document choice |
| numerics_class | incompressible-LES-CHT (NEW root — compound from 002b + 010) |
| coverage map row to fill | "Compound LES+CHT (thermal striping / nuclear primary loop / steam pipe / chemical reactor inlet)" |
| CAD source priority | Tier 1 Vattenfall T-junction OECD/NEA benchmark (publicly documented; check OECD/NEA URL) |
| defect injection count | 1 |
| defect injection hint | D5 (pipe-pipe weld interface mis-alignment, 30-100 μm — real welding tolerance) |
| sandbox path suggestion | `~/Desktop/case_015_vattenfall_t_junction/` |

## Why Vattenfall T-junction as case_015 (Phase 3 #1 strategic role)

After Phase 1-2 (single numerics roots covered), Phase 3 validates
that **compound numerics roots** (LES + CHT) work in the harness.
Vattenfall T-junction is the canonical OECD/NEA benchmark for
thermal striping:

1. **Compound root verification**: case_002b validated CHT alone;
   case_010 will validate LES alone; case_015 confirms they
   compose. Compound-root validation is the prerequisite for
   case_016 (compressible-DES = compressible + DES compound).
2. **Industrial relevance**: thermal fatigue from striping is
   real $$$ in nuclear primary loops (PWR cold/hot leg
   junction), steam pipe networks, chemical reactor inlets.
   Industry uses Vattenfall as the pre-test simulation
   reference.
3. **Cleanest D5 case**: case_011 already injects D5 (30 μm plate
   offset) but the comparison zone in HX is well-separated;
   Vattenfall D5 (pipe-weld misalignment) is on the actual flow
   path, exercising A2-v2 detection in the most real-world
   industrial defect pattern.
4. **Long-time statistics infrastructure**: case_010 will need
   long-time field averaging; case_015 needs LES + CHT joint
   long-time statistics (wall-T spectrum, RMS T'). New post-
   processor: `wall_T_spectrum_extractor.py` —
   reusable for case_016 acoustic analysis.

## Hard constraints (Codex must honor)

1. **Solver class**: `chtMultiRegionFoam` with LES variant (each
   fluid region uses LES; solid region uses standard heat
   conduction) OR `buoyantPimpleFoam` LES single-region + walls
   patch (faster but no solid heat capacity). Document
   trade-off; default: `chtMultiRegionFoam` with LES if pipe
   wall thermal capacity matters (Vattenfall benchmark requires
   it for fatigue prediction).
2. **CAD source**: Tier 1 Vattenfall T-junction. Geometry per
   OECD/NEA spec: main pipe ID 140 mm, branch pipe ID 100 mm,
   90° T-junction (perpendicular). Pipe wall thickness 6 mm
   (typical SS304 piping). Length 1000 mm upstream + 2000 mm
   downstream. License: OECD/NEA public benchmark — citation
   required; bake-into-script if URL transient.
3. **Geometry must be physically realistic**:
   - Main pipe (cold inlet): ID 140 mm
   - Branch pipe (hot inlet): ID 100 mm at 90° T-junction
   - Pipe wall: 6 mm thickness, SS304 material
   - Upstream length: ≥ 1000 mm (allow flow development)
   - Downstream length: ≥ 2000 mm (allow striping development
     + statistics window)
   - Wall thermal coupling (CHT path)
4. **Defect injection**: exactly 1 defect (this case is more
   physics-heavy than other cases; defect count reduced):
   - **D5**: pipe-pipe weld interface mis-alignment, 30-100 μm
     offset between main pipe wall and branch pipe wall at
     T-junction welded joint. Apply [QUESTIONABLE 2026-05-08]
     marker per V25 (A2 v1 cannot field-validate offset
     distance; A2-v2 draft pending).
5. **Patch naming**: `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Multi-region cellZone**: parts manifest MUST declare:
   - `region_main_fluid` (cold water in main pipe)
   - `region_branch_fluid` (hot water in branch pipe)
   - `region_wall_solid` (SS304 pipe wall, fused as ONE body
     per cq.Solid.fuse() per V16/V24)
   - Conjugate interfaces at all fluid-solid junctions
7. **Operating point**: Vattenfall benchmark conditions
   - Main (cold): T = 19 °C, ṁ = 9.0 kg/s (ID 140 mm)
   - Branch (hot): T = 36 °C, ṁ = 6.0 kg/s (ID 100 mm)
   - Re_main ≈ 79,200; Re_branch ≈ 76,400 (both turbulent;
     LES wall-modeled at y+ 30-100)
   - SS304 thermal: ρ=7900, cp=500, k=15 W/m·K
8. **LES configuration**:
   - LES model: WALE or dynamicKEqn (document choice)
   - Wall model: nutUSpaldingWallFunction (wall-modeled, NOT
     wall-resolved DNS)
   - Time step: dt ~ 1e-4 s (CFL ≤ 1)
   - Statistics window: ≥ 5 flow-throughs after settling (≥ 10
     for fatigue spectrum if computed)
9. **Determinism**: CadQuery script byte-identical regeneration.
10. **Industrial flavor**: Vattenfall is recognizable industrial
    benchmark (nuclear pre-test); do NOT genericize.
11. **Reference data**: wall-T striping amplitude at 10 stations
    along downstream (Vattenfall Tx10/Tx20/.../Tx100 thermocouple
    positions); RMS T' at each station; CFD vs experiment within
    ±2 K mean, ±0.5 K RMS (typical LES tolerance).

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified
project. You design ONE industrial CFD case end-to-end.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/.
14 prior cases (002a/b + 003-014). You designed 004-014.
**case_015 is Phase 3 #1** — first compound numerics root (LES +
CHT) on Vattenfall T-junction OECD/NEA benchmark.

## Required reading

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (E-class pipework)
3. .planning/methodology/public_cad_sources.md (Tier 1 OECD/NEA)
4. .planning/methodology/kickoff/case_002b_codex_response.md (CHT)
5. .planning/methodology/kickoff/case_010_codex_response.md (LES)
6. .planning/methodology/kickoff/case_011_codex_response.md
   (multi-region cellZone bookkeeping)
7. .planning/case_profiles/case_002b_apu_bay_cht.md
8. .planning/methodology/industrial_case_solver_findings.md
   (V14/V15 CHT inheritance; V-findings from case_010 LES if
   sedimented)
9. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
10. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
11. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: chtMultiRegionFoam with LES variant
   (preferred — wall thermal capacity matters for fatigue) OR
   buoyantPimpleFoam LES + walls-as-patch fallback. Document
   choice.
2. **CAD source**: Tier 1 Vattenfall T-junction. Main pipe ID
   140mm, branch ID 100mm, 90° T, wall 6mm SS304. Lengths
   1000mm upstream + 2000mm downstream.
3. **Geometry**:
   - Realistic pipework with welded T-junction joint
   - Wall thermal coupling (CHT)
   - Sufficient upstream/downstream length
4. **Defect injection (REQUIRED 1 defect)**:
   - D5: pipe-pipe weld misalignment, 30-100 μm offset between
     main and branch pipe walls at welded joint. Apply
     [QUESTIONABLE 2026-05-08] per V25.
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Multi-region**: region_main_fluid + region_branch_fluid +
   region_wall_solid (fused via cq.Solid.fuse()).
7. **Operating point**: Vattenfall (T_cold=19°C, ṁ_cold=9.0;
   T_hot=36°C, ṁ_hot=6.0; SS304 walls).
8. **LES**: WALE or dynamicKEqn; wall-modeled at y+30-100;
   nutUSpaldingWallFunction; dt ~ 1e-4 s; ≥ 5 flow-through
   statistics.
9. **Industrial flavor**: nuclear primary loop / steam pipe
   recognizable.
10. **Reference data**: wall-T amplitude + RMS T' at Tx10..Tx100
    stations; CFD ± 2K mean, ± 0.5K RMS.
11. **NO Ahmed/NACA/Sajben** (Lane B).
12. **NO new defect categories** outside D1-D10.
13. **NO wall-resolved LES** (wall-modeled only; DNS out of
    scope).

## Your 5 deliverables

(same format as prior cases)

### 1. Engineering brief
- Component picked + bank ID + reasoning
- Engineering question (typical: "what is wall-T striping amplitude
  + frequency spectrum at downstream stations? Does as-installed
  weld misalignment alter striping pattern?")
- Physics signature (chtMultiRegionFoam + LES, Re 76k-79k both
  pipes, wall-modeled y+ 30-100, CHT to SS304 walls)
- Parts inventory (3 regions: main fluid + branch fluid +
  wall solid; conjugate interfaces; thermocouple sampling
  patches Tx10..Tx100)
- BC plan (main_inlet: flowRateInlet T_cold; branch_inlet:
  flowRateInlet T_hot; outlet: pressureOutlet; conjugate
  interfaces: turbulentTemperatureCoupledBaffleMixed; outer wall:
  zeroGradient T or fixedHeatFlux 0)
- Expected metrics: wall-T at Tx10..Tx100 (mean + RMS T'),
  spectrum at one downstream station (FFT of wall-T time series),
  fatigue stress estimate (optional Phase 3 stretch)
- Hypothesized failure modes:
  - V14/V15 inheritance from 002b CHT
  - V-findings from case_010 LES (long-time averaging,
    wall-modeled y+ resolution)
  - V-findings from case_011 (multi-region cellZone bookkeeping)
  - NEW: LES + CHT joint statistics convergence (longer than
    pure LES)
  - NEW: wall-modeled LES + CHT wall heat-flux interface
    interpretation
  - NEW: long-time statistic sample size for fatigue spectrum
    (need ≥ 10 flow-through for FFT)
  - NEW: multi-region time-step coordination (fluid LES dt vs
    solid implicit dt)
- Defect injection summary (D5 with measurable verification)
- Sub-session estimated effort: 12-15h

### 2. CAD generation script (Python, executable)

CadQuery preferred:
- Deterministic
- --out CLI with default
- Parametric constants (D_main_id, D_branch_id, wall_thickness,
  L_upstream, L_downstream, weld_misalignment_um, thermocouple_positions, ...)
- 3 fused regions per cq.Solid.fuse() per V16/V24
- Defect: D5 30-100 μm offset on main/branch wall interface at
  weld
- STEP export with 3 named bodies + sampling patches

### 3. STEP file path

/Users/Zhuanz/Desktop/case_015_vattenfall_t_junction/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- regions: 3 (main fluid / branch fluid / wall solid)
- conjugate_interfaces: explicit pairing
- thermophysics: water (cold + hot), SS304
- vattenfall operating point + Tx10..Tx100 sampling patches
- LES config (model, wall function, time step, statistics window)

### 5. Defect manifest YAML

D5 [QUESTIONABLE 2026-05-08]: A2 v1 cannot field-validate
30-100 μm offset; A2-v2 draft pending. Verification command
+ FreeCAD measurement protocol.

## Format your response

(same as prior)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT propose wall-resolved LES (wall-modeled only)
- Do NOT skip CHT to wall (defeats fatigue purpose)
- Do NOT use simpleFoam / steady (LES is transient)
- Do NOT propose 2 defects (1 is enough; complexity comes from
  LES + CHT, not defect count)
- Do NOT use D1/D8 (D5 is the under-utilized choice; D5 + V25
  arc is the case identity)
- Do NOT exceed 15h sub-session effort

## Begin
```

## Validation checklist

- [ ] CAD source picked (Tier 1 Vattenfall, OECD/NEA citation)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All names ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **3 regions** declared (main fluid + branch fluid + wall solid)
- [ ] **Conjugate interfaces** at all fluid-solid junctions
- [ ] Pipe geometry per Vattenfall (140 mm + 100 mm + 6 mm wall)
- [ ] Upstream ≥ 1000mm, downstream ≥ 2000mm
- [ ] D5 weld misalignment: 30-100 μm, [QUESTIONABLE]
- [ ] Operating point matches Vattenfall (cold/hot ṁ + T)
- [ ] LES config documented (WALE/dynamicKEqn + wall-modeled +
      time step + statistics window)
- [ ] **Tx10..Tx100 sampling stations** declared
- [ ] CHT interface BC type explicit
  (turbulentTemperatureCoupledBaffleMixed)
- [ ] Reference data (mean + RMS) ± tolerance documented

## After validation passes

(same as prior)

## Risk mitigations

- If Codex picks buoyantPimpleFoam single-region (skips CHT) →
  challenge in revision; CHT is required for fatigue prediction
- If Codex skips long-time statistics window → revision request
- If Codex picks wall-resolved → revision request (wall-modeled
  only)
- If 86gs 503/429 → fall back to CRS gpt-5.4 high
