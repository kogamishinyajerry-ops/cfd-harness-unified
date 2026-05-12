# Codex Case-Design Request · case_020

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 4 #4 (FINAL CASE) per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: Anisotropic porous resistance — extends
> case_003 to Darcy-Forchheimer source term. Final case in
> 11-case industrial-extension batch.
> **Backend**: CRS gpt-5.4 high primary; 86gs fallback.
> **Soft blockers**: case_011 sediment helpful (multi-region
> patterns adjacent to porous-zone definition); D7 advisor
> decision (B4) may inform whether D9/D10 advisors land.

## Target

| field | value |
|---|---|
| case_id | `case_020_<short_name>` (Codex picks; suggested: `porous_media_filter_darcy_forchheimer`) |
| solver_class_target | Anisotropic porous resistance: `simpleFoam` + porous source term (Darcy-Forchheimer) (extends 003) |
| numerics_class | incompressible-RANS + Darcy-Forchheimer (extends 003) |
| coverage map row to fill | "Filter / porous media (HEPA / catalyst bed / EV cooling / fuel cell)" — currently uncovered |
| CAD source priority | Tier 1 ERCOFTAC porous-media benchmark → Tier 3 parametric fallback |
| defect injection count | 2 |
| defect injection hint | **D9 (porous-zone surface tessellation)** — UNCOVERED OR 2nd D9 if case_016/017 already injected + **D10 (open shell at filter edge)** — UNCOVERED in 003-019 roster |
| sandbox path suggestion | `~/Desktop/case_020_porous_media_filter/` |

## Why porous media filter as case_020 (Phase 4 #4 strategic role)

Final case in industrial-extension batch. Closes the harness's
ability to do filter / catalyst-bed / EV-cooling industrial CFD:

1. **Direct case_003 inheritance**: simpleFoam machinery already
   validated. Porous source term + anisotropic resistance tensor
   is the NEW element.
2. **Industry breadth**: HEPA filters / catalyst beds / EV
   battery cooling channels / fuel cell flow distributors all
   share Darcy-Forchheimer porous-zone modeling.
3. **D10 first injection**: open-shell-at-filter-edge defect is
   the LAST uncovered defect category in catalog. case_020
   completes the defect catalog coverage (assuming D6/D7/D9
   landed in earlier Phase 1-4 cases).
4. **D9 reinforcement**: 2nd or 3rd D9 injection (after case_016
   cavity walls + possibly case_017 faceted pins). Multi-case
   D9 evidence informs whether D9 advisor sub-DEC is worth
   landing.
5. **Phase 4 short case**: 8h effort. Lowest infrastructure
   climb in the batch — last-case dispatch lets the project
   close cleanly into harvest cycle 003.

## Hard constraints (Codex must honor)

1. **Solver class**: `simpleFoam` steady + porous source via
   `fvOptions` `explicitPorositySource` with
   `DarcyForchheimer` model. Document anisotropic resistance
   tensor (different d, f along streamwise vs cross-stream
   directions).
2. **CAD source**: Tier 1 ERCOFTAC porous-media benchmark
   (publicly documented) → Tier 3 parametric fallback (filter
   housing + porous zone + flow distributor — well-documented
   filter geometry).
3. **Geometry must be physically realistic**:
   - **Filter housing**: rectangular or cylindrical duct,
     200-500 mm length, 100-300 mm cross-section
   - **Porous zone**: filter element occupies 30-50% of housing
     cross-section, oriented perpendicular to bulk flow
   - **Inlet plenum**: ≥ 2× filter element thickness upstream
   - **Outlet plenum**: ≥ 2× filter element thickness downstream
   - **Filter element thickness**: 20-50 mm typical (HEPA /
     catalyst bed scale)
4. **Defect injection**: exactly 2 defects from catalog. Required
   set:
   - **D9**: faceted approximation of curved filter housing or
     filter element edge (12-24 facets per 90° instead of
     smooth curve). Advisor=NONE in v1 (or 2nd/3rd D9 if
     case_016/017 already landed).
   - **D10**: open shell at filter edge — non-watertight
     boundary between filter element and housing wall (small
     gap or open seam, e.g., 0.5-2 mm un-sealed slit at one
     corner). UNCOVERED in 003-019 roster — first D10
     injection. No LANDED advisor for non-watertight shell
     pattern.
5. **Patch naming**: `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Single fluid region** + porous zone declared via cellZone:
   - region: `region_fluid` (single)
   - cellZone: `porous_zone_filter_element` (where Darcy-
     Forchheimer source applies)
   - patches: `inlet`, `outlet`, `housing_wall`,
     `filter_element_face_upstream`,
     `filter_element_face_downstream`, `filter_edge_seal`,
     `filter_edge_open_d10` (the D10 defect patch)
7. **Operating point**: filter-industry typical
   - Air at standard conditions (HEPA / dust filtration) OR
     water (catalyst / fuel cell flow distributor) — Codex picks
   - Face velocity U_face = 0.5-2.5 m/s (typical filter face
     velocity per ASHRAE filter spec)
   - Re_housing based on hydraulic diameter, expect 1e3-1e5
     (laminar to fully turbulent depending on application)
8. **Darcy-Forchheimer parameters**: documented per ERCOFTAC
   reference OR derived from pressure-drop curve
   - Streamwise: high resistance (d_streamwise large)
   - Cross-stream: very high resistance (d_cross >> d_streamwise)
     forcing flow through filter
   - Forchheimer term f for inertia at higher U_face
9. **Determinism**: CadQuery script byte-identical regeneration.
10. **Industrial flavor**: HEPA filter / catalyst bed / EV
    battery cooling / fuel cell distributor.
11. **Reference data**:
    - Pressure drop Δp_filter at design face velocity (per
      ERCOFTAC or filter manufacturer spec)
    - Flow uniformity downstream of filter (σ_U / U_mean)
    - Anisotropic flow split into streamwise vs cross-stream
      validates Darcy-Forchheimer tensor implementation
    - CFD vs reference Δp ± 10%; uniformity index ± 0.05

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified
project. You design ONE industrial CFD case end-to-end.

This is the **FINAL case** in the industrial-extension batch
(case_011-020). 19 prior cases dispatched; this closes the
batch into harvest cycle 003.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/.
19 prior cases (002a/b + 003-019). You designed 004-019.
**case_020 is Phase 4 #4 (FINAL)** — porous media filter with
Darcy-Forchheimer. Extends case_003 incompressible-RANS to
anisotropic porous source term.

## Required reading

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (E-class filter)
3. .planning/methodology/public_cad_sources.md (Tier 1 ERCOFTAC)
4. .planning/methodology/kickoff/case_003_codex_response.md
5. .planning/case_profiles/case_003_crm_hls_boundary_layer.md
6. .planning/methodology/industrial_case_solver_findings.md
7. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
8. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
   (B4 blocker: D9 advisor decision; D10 first injection)
9. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: simpleFoam steady + fvOptions
   explicitPorositySource with DarcyForchheimer model.
   Anisotropic resistance tensor.
2. **CAD source**: Tier 1 ERCOFTAC porous-media → Tier 3
   parametric fallback. Document choice.
3. **Geometry physical realism**:
   - Filter housing 200-500mm × 100-300mm
   - Porous zone 30-50% cross-section, perpendicular to flow
   - Inlet/outlet plenum ≥ 2× element thickness each
   - Filter element thickness 20-50 mm
4. **Defect injection (REQUIRED 2 defects)**:
   - D9: faceted curved surface (12-24 facets per 90°). Advisor=NONE
     (or 2nd/3rd D9 cross-case evidence).
   - D10: open shell at filter edge (0.5-2 mm un-sealed slit).
     UNCOVERED in 003-019. Advisor=NONE; flag advisor-gap
     V-finding.
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Single fluid region** + cellZone for porous zone.
7. **Operating point**: U_face=0.5-2.5 m/s, Re_housing 1e3-1e5.
   Air or water (Codex picks based on application).
8. **Darcy-Forchheimer**: d streamwise + d cross + f Forchheimer
   anisotropic per ERCOFTAC reference.
9. **Industrial flavor**: HEPA / catalyst / EV cooling / fuel
   cell distributor.
10. **Reference data**: Δp ± 10%, uniformity ± 0.05.
11. **NO Ahmed/NACA/Sajben** (Lane B).
12. **NO new defect categories** outside D1-D10.
13. **NO scalar transport** (case_019 covers; 020 is porous source
    only).

## Your 5 deliverables

(same format as prior)

### 1. Engineering brief
- Component picked + bank ID + reasoning
- Engineering question (typical: "what is filter Δp +
  downstream uniformity at design face velocity, with
  as-installed faceted-housing + open-edge-seal defects?")
- Physics signature (simpleFoam + DarcyForchheimer porous,
  Re 1e3-1e5, anisotropic resistance)
- Parts inventory (single fluid + cellZone + named patches)
- BC plan (inlet: flowRateInlet U_face; outlet: pressureOutlet;
  housing_wall: noSlip; filter_element_face_*: derived from
  cellZone porous source; filter_edge_open_d10: noSlip ON the
  defect side, free-flow opportunity creates leak path)
- Expected metrics:
  - Pressure drop Δp_filter
  - Flow uniformity index σ_U / U_mean at outlet plane
  - Bypass flow through D10 open-edge gap (fraction of total
    flow)
  - Anisotropic flow split (streamwise vs cross-stream within
    porous zone — validates Darcy-Forchheimer tensor)
- Hypothesized failure modes:
  - case_003 inheritance (incompressible-RANS patterns)
  - NEW: porous source term sign convention (drag opposes flow
    direction; cellZone orientation matters)
  - NEW: anisotropic resistance tensor coordinate frame
    (DarcyForchheimer requires coordinate basis declaration)
  - NEW: bypass flow through D10 distorts Δp prediction
    significantly
  - NEW: faceted housing D9 introduces local separation at
    sharp facet edges
  - NEW: D10 advisor-gap (non-watertight shell detection)
- Defect injection summary (D9 + D10 with verification
  commands)
- Sub-session estimated effort: 8h

### 2. CAD generation script (Python, executable)

CadQuery preferred:
- Deterministic
- --out CLI with default
- Parametric constants (housing_L, housing_W, housing_H,
  filter_element_thickness, filter_aspect_ratio,
  inlet_outlet_plenum_factor, d9_facet_count_per_90deg,
  d9_target_surface, d10_gap_size_mm, d10_corner_index, ...)
- Single fluid region body + cellZone for porous zone
  + named patches
- Defect injection: D9 replaces curved housing or filter edge
  with faceted approximation; D10 introduces 0.5-2 mm gap at
  one corner of filter-housing seal
- STEP export with named patches preserved (cq.Solid.fuse() per
  V16/V24)

### 3. STEP file path

/Users/Zhuanz/Desktop/case_020_porous_media_filter/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- region: region_fluid (single)
- cellZones: porous_zone_filter_element with DarcyForchheimer
  parameters (d_streamwise, d_cross, f_Forchheimer, coordinate
  frame)
- patches: full list with bc_type plan
- thermophysics: air (HEPA / dust) or water (catalyst / fuel
  cell flow distributor) — document choice
- filter operating point: U_face, Re_housing, application
- Darcy-Forchheimer parameters: source (ERCOFTAC reference or
  derived from Δp curve)
- reference: ERCOFTAC porous-media citation OR filter-spec
  reference

### 5. Defect manifest YAML

- D9 faceted curve:
  - target surface (housing curved transition or filter edge)
  - facet count
  - expected_advisor_to_catch: NONE in v1 (or 2nd/3rd D9 case
    if case_016/017 landed); flag advisor-gap consistency or
    promote D9 advisor candidate
  - manual verification: chord-length comparison vs smooth
    reference
- D10 open shell:
  - target corner / seal location
  - gap size 0.5-2 mm
  - expected_advisor_to_catch: NONE; FIRST D10 injection;
    advisor-gap V-finding flagged for harvest 003 retro
  - manual verification: FreeCAD watertight check OR explicit
    gap measurement

## Format your response

(same as prior)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT use scalar transport (case_019 territory; case_020 is
  porous source only)
- Do NOT use chtMultiRegion (single-region + cellZone)
- Do NOT skip Darcy-Forchheimer anisotropic tensor
- Do NOT use D1/D2/D5/D6/D7/D8 (D9 + D10 are the under-utilized
  choices for case_020)
- Do NOT exceed 8h sub-session effort

## Begin
```

## Validation checklist

- [ ] CAD source: Tier 1 / Tier 3 with rationale
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All names ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single fluid region** + **cellZone for porous zone**
- [ ] Filter housing + element + plenums per spec
- [ ] D9 faceted: 12-24 facets, advisor=NONE
- [ ] D10 open shell: 0.5-2 mm gap, advisor=NONE (FIRST D10)
- [ ] Operating point: U_face 0.5-2.5 m/s, fluid documented
- [ ] **Darcy-Forchheimer anisotropic** (d streamwise / d cross /
      f Forchheimer + coordinate frame)
- [ ] Reference (ERCOFTAC or filter spec) cited
- [ ] D10 advisor-gap V-finding flagged for harvest 003 retro

## After validation passes

(same as prior)

## Risk mitigations

- If Codex skips Darcy-Forchheimer (uses only Darcy linear) →
  revision request (Forchheimer term required for higher U_face)
- If Codex picks isotropic resistance → revision request
  (anisotropic is the case identity; flow must be forced through
  filter)
- If Codex picks D1/D8 → revision request (D9/D10 are the
  under-utilized choices for catalog completion)
- If 86gs / CRS overload → fall back to other

## Closing note

case_020 closes the industrial-extension batch (cases 011-020).
After case_020 sediment lands, **harvest cycle 003** is triggered:
- All 11 industrial-extension cases sedimented
- Defect catalog coverage analysis (D1-D10 utilization)
- Advisor-gap consolidation (D6 / D7 / D9 / D10 all surfaced
  during Phase 1-4; harvest 003 proposes A4-A8 advisor sub-DECs
  as warranted)
- Component_bank refinement post-batch
- Strategic doc successor: `case_021_030_*.md` (next batch)
