# Codex Case-Design Request · case_009

> **Status**: drafted 2026-05-08; queued behind case_007 + case_008
> in single-fire sequence. **Long-pole**: 12-16h sub-session
> effort, highest infrastructure climb in roster.

## Target

| field | value |
|---|---|
| case_id | `case_009_<short_name>` (working name `case_009_sandia_flame_d`) |
| solver_class_target | reacting low-Mach piloted jet flame |
| numerics_class | **reacting-low-Mach** (new — pure Pattern 6 root) |
| coverage map row to fill | "Combustion / reacting flow" — currently 📝 proposed |
| CAD source priority | Tier-1 Sandia Flame D (TNF Workshop CH4/air piloted jet) |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_009_<short_name>/` |

## Why Sandia Flame D as case_009

Fills the reacting-low-Mach row. **Highest infrastructure climb
in the entire roster** — brand new infrastructure:
- `reactingFoam` (or `reactingPimpleFoam`) solver path
- Species transport equations (CH4, O2, N2, CO2, H2O at minimum;
  more for reduced mechanism)
- Tabulated chemistry (PaSR / EDC) OR finite-rate kinetics
- Reduced mechanism: **DRM-19 or 2-step** (NOT GRI-Mech 3.0 —
  too expensive)
- Buoyancy in low-Mach formulation
- Temperature scalar transport with combustion source term
- Mixture fraction Z post-processing for non-premixed validation

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified project. Design ONE industrial CFD case end-to-end.

## Project context
cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198, accumulates industrial CFD experience. Eight cases dispatched (case_002a, 002b, 003-008). case_009 fills the **reacting-low-Mach combustion** row — first reacting case for project. Highest infrastructure climb in the 10-case roster (12-16h estimated effort).

## Required reading (in repo)
1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (Lane B exclusions)
3. .planning/methodology/public_cad_sources.md (Sandia Flame D / TNF Workshop)
4. .planning/methodology/kickoff/case_007_codex_response.md AND case_008_codex_response.md (your prior; same pattern)
5. .planning/methodology/industrial_case_solver_findings.md (Pattern 6: case_009 inherits NONE)

## Hard constraints

1. **Solver class**: reacting low-Mach piloted jet flame. v1: reactingFoam (or rhoReactingFoam if compressibility matters above flame). v2 fallback: reactingPimpleFoam for transient. KEEP scope tight: this is a CANONICAL Sandia Flame D, NOT a full industrial combustor (NASA Combustor C3 / DLR-A flame are out of case_009 scope — they go in case_011+ if ever)
2. **CAD source priority**:
   - PRIMARY: **Sandia Flame D** (TNF Workshop CH4/air piloted jet, Barlow & Frank 1998). Geometry: main fuel jet (D=7.2 mm CH4/air mix at 25/75 vol%), pilot annulus (D_inner=7.7 mm, D_outer=18.2 mm; pilot flame), coflow air (D_outer=240 mm)
   - Source: Sandia TNF workshop public archive https://tnfworkshop.org/
3. **Reduced chemistry mechanism — MANDATORY**:
   - PRIMARY: **DRM-19** (19-species, 84-step reduced mechanism, well-validated for CH4/air diffusion flames)
   - FALLBACK: **2-step Westbrook-Dryer** (CH4 + 1.5 O2 → CO + 2 H2O; CO + 0.5 O2 → CO2) — minimum viable
   - **HARD EXCLUSION**: do NOT specify GRI-Mech 3.0 (53 species, ~325 reactions — too expensive for v1; sub-session can upgrade to GRI-Mech in v3 if needed)
4. **Defect injection**: exactly 2 defects from D1-D10. Defects must NOT corrupt the published mixture-fraction Z(r,z) or temperature T(r,z) profiles at z/D = 7.5, 15, 30, 45, 60 (radial Raman/Rayleigh measurement stations from Barlow & Frank). Safe locations: pilot housing exterior, coflow plenum mounting bracket
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$
6. **Combustion control explicit**: parts manifest must include `combustion:` block with chemistry mechanism file path (Codex specifies expected filename like `chem.inp` + `tran.dat`), thermo type (janaf), turbulence-chemistry interaction model (PaSR or EDC, default PaSR Cmix=1.0), Schmidt number 0.7
7. **Inflow specification explicit**: parts manifest declares 3 inlet patches with species mass fractions:
   - `fuel_jet`: CH4 mass fraction 0.156, air 0.844 (corresponding to 25/75 vol% CH4/air mix), U=49.6 m/s, T=294 K
   - `pilot_annulus`: products of stoichiometric burn (CO2, H2O, N2, partially OH/CH for flame stability), T=1880 K, U=11.4 m/s (per Barlow & Frank)
   - `coflow_air`: air (O2 0.232, N2 0.768), U=0.9 m/s, T=291 K
8. **Buoyancy**: Sandia Flame D is buoyancy-modulated low-Mach (jet-induced buoyancy at z/D > 30); g vector explicit in manifest
9. **Reference data preservation**: Z(r,z) and T(r,z) measurement stations at z/D = 7.5, 15, 30, 45, 60 must remain mesh-clean
10. **Determinism**: byte-identical STEP given identical inputs
11. **Industrial flavor**: Sandia Flame D is canonical TNF benchmark — academic but heavily used by industrial-combustion CFD shops as validation reference
12. **Pure non-premixed diffusion flame**: do NOT design as premixed (case_009 scope is non-premixed; premixed flames are case_011+ if ever)
13. **Symmetry**: 2D axisymmetric wedge (5° wedge, single layer) for v1; full 3D LES is out-of-scope (case_010 LES territory)

## Your 5 deliverables (same format as case_008)

### 1. Engineering brief (Markdown)
Component + bank ID / Engineering question (Z(r,z), T(r,z), CH4 / CO2 / H2O / O2 / OH species profiles vs Barlow & Frank Raman/Rayleigh) / Physics signature (Re_jet=22400 at jet, Da=Damköhler, equivalence ratio at z/D, expected flame length L_st) / Parts inventory (fuel_jet, pilot_annulus, coflow_air, axisymmetric wedge front/back, far_outlet, ground if relevant) / BC plan / Expected metrics (Z(r,z), T(r,z), species(r,z) at 5 published stations; flame length L_st; lift-off height if any) / Hypothesized failure modes (reacting-specific) / Defect summary / Effort estimate (12-16h)

### 2. CAD generation script (Python, executable)
- 2D axisymmetric wedge geometry (5° wedge, 1 cell thick)
- Wedge front/back faces with bc.U: wedge
- 3 concentric inlet patches at z=0
- Far outlet at z = 80 D (D=7.2 mm; far enough for flame length)
- Outer side wall at r = 250 mm (slip or freestream)
- Optional defect bodies on pilot exterior or coflow plenum bracket

### 3. STEP file path
`/Users/Zhuanz/Desktop/case_009_<name>/inputs/cad_codex_v1.step`

### 4. Parts manifest YAML
Plus:
- `combustion:` block (chemistry mech path, thermo type, turbulence-chem model, Sc)
- `species_inflow:` block (per inlet: mass fractions, T, U)
- `reference_data:` block (Barlow & Frank Z/T/species at 5 z/D stations + URL)
- `dimensionless_groups:` block (Re_jet, Da, equivalence ratio profile)

### 5. Defect manifest YAML
Two defects, D1-D10. Z/T/species measurement stations defect-free.

## Format response (same as case_008)

## Round budget
Round 1 of 2.

## What you should NOT do
- Do NOT specify GRI-Mech 3.0 (HARD — too expensive for v1)
- Do NOT design premixed flame (case_009 is non-premixed)
- Do NOT include moving parts / pilot ignition transient — assume steady piloted flame
- Do NOT design as full 3D — 2D axisymmetric wedge is correct
- Do NOT pick Lane B references (Ahmed / NACA 0012 / Sajben / BFS / Ercoftac)
- Do NOT pick a different combustion benchmark (DLR-A, BERL, NASA Combustor C3 are case_011+ scope)
- Do NOT include rotating / compressible-shock / VOF / Lagrangian elements
- Do NOT design defects in measurement stations

## Begin
```

## Validation checklist
- [ ] CAD: Sandia Flame D
- [ ] Script syntax-clean
- [ ] **DRM-19 or 2-step Westbrook-Dryer specified** (not GRI-Mech)
- [ ] **3 inlet patches** with species mass fractions / T / U
- [ ] **combustion block** complete
- [ ] **2D axisymmetric wedge** geometry
- [ ] All patch names valid
- [ ] Defects NOT on z/D = 7.5/15/30/45/60 measurement stations
- [ ] Both defects measurable
- [ ] Reference data URL declared (TNF workshop)
- [ ] expected_advisor_to_catch references real or pending advisor
