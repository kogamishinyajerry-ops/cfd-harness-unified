# Codex Case-Design Request · case_007

> **Status**: drafted 2026-05-08; about to be sent via
> `codex-relay-with gpt-5.5` (xhigh, 86gs primary; CRS gpt-5.4
> fallback if 503).

## Target

| field | value |
|---|---|
| case_id | `case_007_<short_name>` (working name `case_007_kcs_ship_vof`) |
| solver_class_target | free-surface ship hydrodynamics, steady or quasi-steady multiphase VOF |
| numerics_class | **multiphase-VOF** (new — pure Pattern 6 root) |
| coverage map row to fill | "Multiphase / VOF" — currently 📝 proposed |
| CAD source priority | Tier-1/Tier-1-adjacent: KRISO KCS (ITTC G2010); Wigley hull (Tier 3 analytic) fallback if KCS license blocks redistribution |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_007_<short_name>/` |

## Why KCS ship VOF as case_007

case_007 fills the multiphase-VOF row. KCS is the canonical
ITTC G2010 multiphase-CFD benchmark; brand new infrastructure
forced:
- `interFoam` (or `interIsoFoam`) solver path
- `alpha.water` field + MULES bounding
- Free-surface BC: `inletOutlet`/`zeroGradient` for alpha at
  inlet/outlet/atmosphere, `slip` at sides
- Symmetry plane at ship centerline (half-hull)
- Wave-elevation post-processing + resistance coefficient
  decomposition (Cw / Cf / Ct)

Pure new numerics root — inherits NONE of the prior 6 cases.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified project. Design ONE industrial CFD case end-to-end.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198, the project accumulates industrial CFD experience via dogfood cases. Six cases already in fleet:
- case_002a (APU bay buoyantSimpleFoam) — active
- case_002b (APU bay CHT) — active
- case_003 (CRM-HLS, incompressible-RANS) — dispatched, deferred
- case_004 (NREL Phase VI rotor, MRF) — dispatched, deferred
- case_005 (RAE M2129 S-duct, compressible-RANS / rhoSimpleFoam) — dispatched, deferred
- case_006 (ONERA M6, compressible-shock-density-based / rhoCentralFoam) — dispatched, deferred

case_007 fills the multiphase-VOF row. This is the FIRST multiphase case for the project. New infrastructure: interFoam, alpha.water field, MULES, free-surface BC family, wave-elevation post-processing.

## Required reading (in repo)
1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (Lane B exclusions: Ahmed / NACA 0012 / Sajben / BFS / Ercoftac mixing tank)
3. .planning/methodology/public_cad_sources.md (canonical multiphase ship: ITTC G2010 KCS / KVLCC2 / DTMB 5415; if license blocks, Wigley hull is Tier-3 analytic fallback)
4. .planning/methodology/kickoff/case_005_codex_response.md AND case_006_codex_response.md (your prior outputs; same pattern)
5. .planning/methodology/industrial_case_solver_findings.md (Pattern 6: case_007 inherits NONE of prior numerics classes)

## Hard constraints

1. **Solver class**: free-surface ship hydrodynamics, multiphase-VOF. v1: interFoam (or interIsoFoam) steady-like via long unsteady simulation with averaged tail. v2 fallback: interIsoFoam if alpha smearing degrades wave pattern, OR finer mesh near free surface
2. **CAD source priority**:
   - PRIMARY: **KRISO KCS** (ITTC G2010 benchmark hull, Lpp ≈ 230 m model-scale or full-scale; published wave pattern + resistance data). Verify ITTC license allows derivative STEP redistribution; if blocked → fallback
   - FALLBACK: **Wigley hull** (analytic parabolic hull, Tier-3 from-scratch, no license issue; widely-validated for VOF benchmark). Use only if KCS license blocks
   - DO NOT pick KVLCC2 (proprietary MOERI license issues) or DTMB 5415 (US Navy classification ambiguity)
3. **Half-hull with symmetry plane**: standard practice; Codex must declare `symmetry_plane_centerline` patch with bc.U: symmetry, bc.alpha.water: symmetry
4. **Free-surface BC family explicit**: parts manifest declares atmosphere patch (alpha.water: inletOutlet, U: pressureInletOutletVelocity, p_rgh: totalPressure with p0=0), water inlet (alpha.water: variableHeightFlowRate or fixed alpha=1, U: fixedValue), water outlet (alpha.water: zeroGradient or inletOutlet), slip side walls
5. **Free-surface initialization**: parts manifest must specify `initial_water_level_z` for setFields. Reference: KCS at design speed Fr=0.26
6. **Reference conditions**: Fr=0.26 (KCS design point, U_inf at model scale), Re=1.4e7 (typical), p_atm=101325, ρ_water=998.8, ρ_air=1.225, ν_water=1.05e-6, ν_air=1.5e-5, σ=0.072 N/m surface tension
7. **Defect injection**: exactly 2 defects from D1-D10. NOT on hull-published-pressure-tap regions or wave-cut measurement lines
8. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$
9. **Determinism**: byte-identical STEP given identical inputs
10. **Reference-data preservation**: hull surface and stern wave region untouched
11. **Mach regime**: incompressible (M ≈ 0.01); do NOT introduce compressible thermo
12. **No buoyancy / heat transfer**: case_002a/b cover those; case_007 is pure isothermal multiphase
13. **Not the case_002a/b CRM-HLS / NREL / RAE territory**: pure free-surface ship

## Your 5 deliverables (same format as case_006)

### 1. Engineering brief (Markdown)
Component + bank ID / Engineering question / Physics signature (Fr, Re, free-surface waves, hull form factor) / Parts inventory (hull, rudder if KCS, atmosphere, water_inlet, water_outlet, side_walls, symmetry_plane_centerline) / BC plan / Expected metrics (Cw / Cf / Ct, wave pattern at z=0, sinkage/trim if free-to-trim, hull pressure distribution) / Hypothesized failure modes (multiphase-VOF specific) / Defect summary / Effort estimate

### 2. CAD generation script (Python, executable)
CadQuery preferred. Must:
- If KCS: generate hull from offsets table (use parametric ITTC G2010 station offsets; bake coordinates into script)
- If Wigley fallback: y(x,z) = (B/2)·(1 - (2x/L)²)·(1 - (z/T)²) parabolic
- Define rudder if KCS (rudder hub gap = D1 candidate location)
- Define stern transom plate (thin transom = D8 candidate)
- Define symmetry plane at y=0
- Define atmosphere/inlet/outlet/sides domain box
- Export STEP with named bodies preserved

### 3. STEP file path
`/Users/Zhuanz/Desktop/case_007_<name>/inputs/cad_codex_v1.step`

### 4. Parts manifest YAML
Plus:
- `multiphase:` block (rho_water, rho_air, nu_water, nu_air, sigma, g vector)
- `reference_conditions:` block (Fr, Re, U_inf, Lpp, design_water_level_z)
- `wave_metrics:` block (Cw decomposition method, wave-cut x-stations for comparison)
- Per-patch role explicit including alpha.water BC

### 5. Defect manifest YAML
Two defects, D1-D10. Hull pressure-tap and wave-cut zones must remain defect-free.

## Format response (same as case_006)
## Deliverable 1 — Engineering brief
<markdown>
## Deliverable 2 — CAD generation script
```python
<full script>
```
## Deliverable 3 — STEP file path
<path>
## Deliverable 4 — Parts manifest
```yaml
<yaml>
```
## Deliverable 5 — Defect manifest
```yaml
<yaml>
```

## Round budget
Round 1 of 2.

## What you should NOT do
- Do NOT design easy
- Do NOT skip defect injection
- Do NOT pick Lane B references (Ahmed / NACA 0012 / Sajben / BFS / Ercoftac mixing tank)
- Do NOT pick KVLCC2 (license) or DTMB 5415 (classification)
- Do NOT include rotating elements (case_004), heat transfer (case_002a/b), or compressible thermo (case_005/006)
- Do NOT pick a deeply-submerged body — case_007 IS free-surface; alpha.water gradient at z=0 is the engineering point
- Do NOT use interMixingFoam or compressibleInterFoam — pure interFoam (or interIsoFoam fallback)

## Begin
```

## Validation checklist (after Codex responds)

- [ ] CAD source: KCS or Wigley declared
- [ ] If KCS: ITTC license context noted in license field
- [ ] Script syntax-clean
- [ ] All patch names valid regex
- [ ] **Symmetry plane at centerline declared** (half-hull)
- [ ] **atmosphere patch with alpha.water=inletOutlet** declared
- [ ] **water_inlet + water_outlet patches** with alpha.water BCs declared
- [ ] **multiphase block** with rho_water / rho_air / nu_water / nu_air / sigma / g
- [ ] **reference_conditions block** with Fr / Re / U_inf / Lpp / design_water_level_z
- [ ] **wave_metrics block** with Cw decomposition method
- [ ] Both defects measurable
- [ ] Hull pressure-tap and wave-cut zones defect-free
- [ ] expected_advisor_to_catch references real or pending advisor

## After validation passes

1. Save Codex response at `kickoff/case_007_codex_response.md`
2. Format kickoff at `kickoff/case_007_<name>.md`
3. Update queue + indexes
4. Tell user: "case_007 dispatched. Continuing with case_008 NASA IRT icing Lagrangian."
