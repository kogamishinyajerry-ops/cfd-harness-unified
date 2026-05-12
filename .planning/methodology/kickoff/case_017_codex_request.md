# Codex Case-Design Request · case_017

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 4 #1 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: Microscale CHT extension — applies case_002b
> chtMultiRegion + case_011 multi-stream patterns to chip-scale
> electronic cooling. Booming data center / EV battery / IGBT
> industry.
> **Backend**: CRS gpt-5.4 high primary (Phase 4 single-case;
> well-trodden territory); 86gs gpt-5.5 fallback if CRS struggles.
> **Soft blockers**: case_011 sediment helpful (multi-stream
> patterns indexed) · component_bank A1 entry refinement post-
> case_011 useful.

## Target

| field | value |
|---|---|
| case_id | `case_017_<short_name>` (Codex picks; suggested: `pin_fin_electronic_heatsink`) |
| solver_class_target | Microscale CHT: `chtMultiRegionFoam` steady, low-Re air over pin-fin array + chip + heatsink solid (extends 002b to chip scale) |
| numerics_class | chtMultiRegionFoam at chip scale (extends 002b — partial inheritance, scale shift to mm/μm) |
| coverage map row to fill | "Electronic cooling / microchannel" — currently uncovered |
| CAD source priority | Tier 2 (TIMA Lab benchmarks if license-permissive) → Tier 3 parametric fallback. Document choice |
| defect injection count | 2 |
| defect injection hint | D8 (thin pin walls 0.3-0.6 mm — `[VALIDATED]` 6-of-6 cross-topology arc, this is 8th-or-9th data point for arc consistency) + D9 (faceted fin curvature — UNCOVERED if case_016 not yet landed; otherwise 2nd D9 injection) |
| sandbox path suggestion | `~/Desktop/case_017_pin_fin_electronic_heatsink/` |

## Why pin-fin electronic heatsink as case_017 (Phase 4 #1 strategic role)

After Phase 1-3 establishes single + compound numerics roots,
Phase 4 packs 4 specialized industrial verticals at lower
sub-session cost (8-12h each). case_017 is the highest-priority
Phase 4 case:

1. **Booming industry**: data center cooling, EV battery thermal,
   IGBT (power electronics) all scaling rapidly. Service market
   value high.
2. **Direct case_011 + 002b inheritance**: chtMultiRegion +
   multi-stream patterns directly apply at chip scale. Pattern 6
   numerics-class inheritance with scale shift (200×120×55 mm
   case_011 → 50×50×20 mm typical chip-scale heatsink).
3. **Component_bank A1 entry**: A1 was promoted from "plate-fin
   heatsink" to "compact heat exchanger" by case_011. case_017
   re-anchors A1's original meaning (pin-fin heatsink) at the
   correct scale.
4. **D8 cross-topology arc consistency**: 8th-or-9th data point
   for `[VALIDATED]` 6-of-6 arc. Adds chip-scale thin-fin
   topology to the validation evidence; if consistent, upgrades
   V10/V23 status to robust across 7 topology classes.
5. **Microscale Re check**: typical pin-fin Re_pin = 100-1000
   (laminar / transitional). Sub-session must explicitly check
   regime — k-ε would be wrong (similar to case_011 laminar
   issue). New playbook entry candidate.

## Hard constraints (Codex must honor)

1. **Solver class**: `chtMultiRegionFoam` steady. v1: 1 fluid
   (air) + 2 solids (chip die + heatsink base + fins as one
   solid; OR chip die + thermal interface material TIM +
   heatsink as 3 solids). Document choice.
2. **CAD source**: Tier 2 TIMA Lab benchmarks OR Tier 3 parametric.
   TIMA Lab thermal CAD must have license verified; Tier 3
   parametric is the safer default for case_017.
3. **Geometry must be physically realistic**:
   - **Heatsink base**: 50 × 50 × 5 mm (typical chip-scale)
   - **Chip die**: 10 × 10 × 0.7 mm (representative die size)
   - **Pin-fin array**: 8×8 or 10×10 grid; pin diameter 1-2 mm;
     pin height 10-15 mm; pin pitch 2.5-4 mm
   - **TIM layer** (optional): 0.05-0.10 mm between chip and
     heatsink base (thermal interface material)
   - **Air channel**: forced convection over pin-fin top; air
     inlet upstream of array, outlet downstream
   - **Power dissipation**: 50 W from chip die (CPU-class) or
     100 W (GPU-class — Codex picks based on operating point)
4. **Defect injection**: exactly 2 defects from catalog. Required
   set:
   - **D8**: 0.3-0.6 mm thin pin walls on a subset of pins
     (e.g., 4 pins in one corner of the array). Expected
     advisor: `thin_wall_advisor` ([VALIDATED 6-of-6]; this is
     8th-or-9th data point).
   - **D9**: faceted pin cross-section (replace circular pins
     with 8-12-faceted polygonal approximation on a subset of
     pins, e.g., 4 pins in another corner). UNCOVERED in
     003-015 if case_016 not yet landed; 2nd D9 if 016 landed.
5. **Patch naming**: `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Multi-region cellZone**: parts manifest MUST declare:
   - `region_air` (fluid)
   - `region_chip_die` (solid: silicon, k=130 W/m·K)
   - `region_heatsink` (solid: aluminum 6063, k=200 W/m·K) —
     fused as one body via cq.Solid.fuse() per V16/V24
   - Optional `region_tim` (solid: thermal grease, k=4 W/m·K) if
     Codex chooses 4-region setup
   - Conjugate interfaces at all fluid-solid + solid-solid
     boundaries
7. **Operating point**:
   - Air inlet: T = 25 °C (298.15 K), U = 2-5 m/s (forced
     convection typical chip cooling fan velocity)
   - Power: 50-100 W chip dissipation (Codex picks)
   - Re_pin: based on selected U and pin diameter; expect
     100-1000 → **document laminar/transitional regime
     explicitly** (do NOT use k-ε without rationale)
   - Target T_chip < 85 °C (typical CPU thermal spec)
8. **Determinism**: CadQuery script byte-identical regeneration.
9. **Industrial flavor**: recognizable CPU / GPU / IGBT / EV
   battery cooler topology. Pin-fin is the standard form.
10. **Reference data**: predicted thermal resistance
    R_θ_junction-to-ambient = (T_chip - T_air_in) / Q_chip
    based on TIMA / IBM thermal correlation for selected pin-
    fin geometry. CFD R_θ within ±15% expected.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified
project. You design ONE industrial CFD case end-to-end.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/.
16 prior cases (002a/b + 003-016). You designed 004-016.
**case_017 is Phase 4 #1** — pin-fin electronic heatsink.
Microscale chtMultiRegion extension (extends case_002b to chip
scale; reuses case_011 multi-region patterns).

## Required reading

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (A1 entry — ORIGINAL
   pin-fin heatsink meaning, NOT promoted compact HX from case_011)
3. .planning/methodology/public_cad_sources.md
4. .planning/methodology/kickoff/case_002b_codex_response.md (CHT)
5. .planning/methodology/kickoff/case_011_codex_response.md
   (multi-region cellZone bookkeeping, scale 200 mm)
6. .planning/case_profiles/case_002b_apu_bay_cht.md
7. .planning/methodology/industrial_case_solver_findings.md
   (V14/V15 CHT inheritance; multi-region findings from case_011
   if sedimented)
8. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
9. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
10. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: chtMultiRegionFoam steady. v1: 1 fluid (air)
   + 2 or 3 solids (chip die + heatsink ± TIM). Document region
   count choice.
2. **CAD source**: Tier 2 TIMA / IBM (license check) OR Tier 3
   parametric (default). Document choice.
3. **Geometry physical realism**:
   - Heatsink base 50×50×5 mm
   - Chip die 10×10×0.7 mm
   - Pin-fin 8×8 or 10×10; D=1-2 mm; H=10-15 mm; pitch 2.5-4 mm
   - Optional TIM 0.05-0.10 mm
   - Air channel inlet/outlet
   - Power 50-100 W
4. **Defect injection (REQUIRED 2 defects)**:
   - D8: 0.3-0.6 mm thin pin walls on subset of pins (4 corner
     pins). Advisor=thin_wall_advisor [VALIDATED 6-of-6];
     case_017 = 8th-or-9th cross-topology arc data point.
   - D9: faceted pin cross-section (8-12 facets) on subset of
     pins (different 4 corner pins). Advisor=NONE (or 2nd D9
     after case_016 if 016 already landed).
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Multi-region**: region_air + region_chip_die + region_heatsink
   (+ optional region_tim). All solids fused via cq.Solid.fuse().
7. **Operating point**: T_air_in=298.15 K, U=2-5 m/s, P_chip=50-100 W.
8. **Re check**: laminar/transitional regime documented; do NOT
   default to k-ε without rationale. Likely simulationType
   laminar OR k-ω-SST with low-Re corrections.
9. **Industrial flavor**: CPU/GPU/IGBT/EV-battery cooler;
   pin-fin standard form.
10. **Reference data**: R_θ_junction-to-ambient ± 15% per TIMA/IBM
    correlation.
11. **NO Ahmed/NACA/Sajben** (Lane B).
12. **NO new defect categories** outside D1-D10.

## Your 5 deliverables

(same format as prior cases)

### 1. Engineering brief
- Component picked + bank ID + reasoning (A1 ORIGINAL pin-fin
  heatsink meaning)
- Engineering question (typical: "does this pin-fin heatsink
  keep T_chip < 85°C at P_chip W with as-installed thin-pin +
  faceted-pin defects?")
- Physics signature (chtMultiRegionFoam, Re_pin 100-1000
  laminar/transitional, Pr=0.71, conjugate Si-Al-air thermal
  coupling)
- Parts inventory (3 or 4 regions: air + chip die + heatsink ±
  TIM)
- BC plan (air_inlet: flowRateInlet T=298.15K; air_outlet:
  pressureOutlet; chip_bottom: fixedHeatFlux from P_chip /
  area; conjugate interfaces:
  turbulentTemperatureCoupledBaffleMixed; outer faces:
  zeroGradient T)
- Expected metrics:
  - T_chip junction temperature (target < 85°C)
  - R_θ junction-to-ambient (predicted from TIMA correlation)
  - Pin-array Δp (forced convection pressure drop)
  - Pin h(local) for 4 representative pins (corner thin-D8
    pins, corner faceted-D9 pins, center pin, edge pin)
  - Heat flux distribution on heatsink base
- Hypothesized failure modes:
  - V14/V15 inheritance from 002b CHT
  - V-findings from case_011 multi-region (if sedimented)
  - NEW: low-Re pin-array forced convection turbulence model
    selection (laminar vs transitional)
  - NEW: chip-die ↔ TIM ↔ heatsink solid-solid conjugate BC
    (if 4-region) — different from 002b 1-fluid-1-solid
  - NEW: faceted-pin h_local deviation vs smooth pin (validates
    D9 detection rationale)
  - NEW: thin-pin h_local + thermal short circuit (D8 effect on
    R_θ)
  - NEW: chip-scale length-scale (mm) vs APU bay (m) — meshing
    sensitivity at thermal boundary layer
- Defect injection summary
- Sub-session estimated effort: 8-10h

### 2. CAD generation script (Python, executable)

CadQuery preferred:
- Deterministic
- --out CLI with default
- Parametric constants (heatsink_base_mm, chip_die_mm, pin_grid,
  pin_diameter_mm, pin_height_mm, pin_pitch_mm, tim_thickness_mm,
  air_channel_height_mm, d8_thin_pin_diameter_mm,
  d8_thin_pin_indices, d9_faceted_pin_facets,
  d9_faceted_pin_indices, ...)
- 3 or 4 regions fused via cq.Solid.fuse() per V16/V24
- Defect injection: D8 reduces pin diameter on chosen indices;
  D9 replaces circular cross-section with N-faceted polygon on
  chosen indices
- STEP export with named bodies preserved

### 3. STEP file path

/Users/Zhuanz/Desktop/case_017_pin_fin_electronic_heatsink/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- regions: 3 or 4 (air + chip + heatsink ± TIM)
- conjugate_interfaces: explicit pairing (air↔heatsink_pin_top,
  air↔heatsink_base, heatsink_base↔TIM, TIM↔chip_die OR
  heatsink_base↔chip_die directly)
- thermophysics: air, silicon (chip), aluminum 6063, optional
  TIM (thermal grease k=4 W/m·K)
- chip operating point: P_chip W, T_air_in K, U_air m/s,
  T_chip_target < 85°C
- TIMA correlation reference for predicted R_θ

### 5. Defect manifest YAML

- D8 thin pin: advisor=thin_wall_advisor [VALIDATED 6-of-6];
  case_017 = 8th-or-9th cross-topology arc data point. Expected
  critical warning at 0.3-0.6 mm.
- D9 faceted pin: advisor=NONE (or 2nd D9 if case_016 landed
  with D9 advisor candidate). Manual verification: chord-length
  comparison vs smooth circle.

## Format your response

(same as prior)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT use k-ε without rationale (low-Re regime; likely
  laminar)
- Do NOT use single-region (chtMultiRegion is the case identity)
- Do NOT skip pin-fin array (defines the case; not bare-plate
  heatsink)
- Do NOT use D1/D5/D6/D7 (D8 + D9 are the under-utilized choices
  for case_017)
- Do NOT exceed 10h sub-session effort

## Begin
```

## Validation checklist

- [ ] CAD source picked (Tier 2 / Tier 3 with rationale)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All names ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **3 or 4 regions** declared (air + chip + heatsink ± TIM)
- [ ] **Conjugate interfaces** at all junctions
- [ ] Geometry: heatsink 50×50×5, chip 10×10×0.7, 8×8 or 10×10
      pin grid, D=1-2 mm, H=10-15 mm
- [ ] Power 50-100 W chip dissipation
- [ ] D8 thin pins: 0.3-0.6 mm, advisor=thin_wall_advisor
- [ ] D9 faceted pins: 8-12 facets, advisor=NONE (or 2nd D9)
- [ ] **Re_pin regime documented** (laminar/transitional)
- [ ] **Turbulence model rationale** explicit (NOT k-ε default)
- [ ] T_chip target < 85°C declared
- [ ] R_θ TIMA correlation reference cited

## After validation passes

(same as prior)

## Risk mitigations

- If Codex defaults to k-ε without rationale → revision request
- If Codex picks single-region → revision request (chtMultiRegion
  required)
- If Codex skips faceted-pin D9 → revision request
- If 86gs gpt-5.5 503/429 (or CRS overload) → fall back to other
