# Codex Case-Design Request · case_018

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 4 #2 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: 3D swirl-dominant + Lagrangian particle —
> extends case_008 from airfoil icing to cyclone separation.
> Validates that Lagrangian patterns work in swirl-dominant flow.
> **Backend**: CRS gpt-5.4 high primary (Phase 4); 86gs fallback.
> **Soft blockers**: case_008 v2 sediment helpful (Lagrangian
> CFD pipeline complete); case_008 only ran v1 advisor-validation.

## Target

| field | value |
|---|---|
| case_id | `case_018_<short_name>` (Codex picks; suggested: `stairmand_cyclone_separator`) |
| solver_class_target | 3D swirl + Lagrangian: `pimpleFoam` + RSM turbulence + kinematicCloud (extends 008) |
| numerics_class | incompressible-RANS-Lagrangian-swirl (extends 008 to swirl-dominant topology) |
| coverage map row to fill | "Cyclone / vortex separator (chemical / mining / dust collection)" — currently uncovered |
| CAD source priority | Tier 1 Stairmand high-efficiency cyclone (industry-standard geometry, public dimensions) OR Lapple cyclone alternate |
| defect injection count | 1 |
| defect injection hint | **D6 (debris in collection chamber)** — 2nd D6 injection if case_016 already landed; otherwise first |
| sandbox path suggestion | `~/Desktop/case_018_stairmand_cyclone_separator/` |

## Why Stairmand cyclone as case_018 (Phase 4 #2 strategic role)

Cyclone separators are widely used in chemical / mining / power /
dust-collection industries. case_008 established Lagrangian
infrastructure on airfoil icing; case_018 extends to **swirl-
dominant 3D flow**:

1. **Direct case_008 inheritance**: simpleFoam → pimpleFoam +
   kinematicCloud one-way coupling already validated. Swirl-
   dominant geometry (vs case_008 airfoil) is the NEW element.
2. **RSM turbulence requirement**: high-swirl flows have strong
   anisotropy; k-ε / k-ω-SST under-predict vortex core. Cyclone
   industry standard is RSM (Reynolds Stress Model). First RSM
   case for project — playbook entry candidate.
3. **Engineering KPIs**: d50 cut-off diameter + collection
   efficiency η(d_p) — clean industry-recognizable metrics tied
   to Stairmand published curves.
4. **Defect catalog**: D6 (debris) extends to collection-chamber
   topology. If case_016 already landed with D6, case_018 is
   the 2nd D6 — advisor-gap evidence accumulation.
5. **Phase 4 short case**: 10-12h effort. Direct inheritance
   keeps it tight despite RSM novelty.

## Hard constraints (Codex must honor)

1. **Solver class**: `pimpleFoam` transient + RSM turbulence
   (LRR or LaunderGibsonRSTM) + `kinematicCloud` one-way
   coupled (particle motion does not feed back to fluid; same
   pattern as case_008). Document RSM model choice + rationale
   over k-ε.
2. **CAD source**: Tier 1 Stairmand high-efficiency cyclone
   (1980s-era industry-standard dimensions; ratios documented
   per Stairmand spec). Alternate: Lapple cyclone if Stairmand
   URL blocks. License: industry-public; bake-into-script.
3. **Geometry must be physically realistic** — Stairmand spec:
   - Cyclone body diameter D = 200-300 mm (industrial scale)
   - Inlet height = 0.5 D (rectangular inlet)
   - Inlet width = 0.2 D
   - Cylindrical body height = 1.5 D
   - Conical section height = 2.5 D
   - Vortex finder (overflow tube) diameter = 0.5 D, length =
     0.5 D
   - Underflow (dust collection chamber) diameter ≥ 0.4 D
   - Document chosen D + scale-derived dimensions
4. **Defect injection**: exactly 1 defect (Phase 4 short case;
   complexity comes from RSM + Lagrangian, not defect count):
   - **D6**: debris cube/block (10-30 mm) inside collection
     chamber at documented position. Advisor=NONE (no LANDED
     advisor for extra-body-in-fluid pattern; if case_016
     landed first, applies same advisor-gap V-finding;
     otherwise first D6 injection).
5. **Patch naming**: `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Single fluid region** + named patches:
   - patches: `inlet_tangential`, `overflow_outlet` (vortex
     finder), `underflow_outlet` (collection chamber bottom),
     `body_cylindrical_wall`, `body_conical_wall`,
     `vortex_finder_wall`, `collection_chamber_wall`,
     `debris_block` (D6)
7. **Operating point**: Stairmand reference
   - Air at standard conditions (ρ=1.225, μ=1.8e-5)
   - U_inlet ≈ 15-25 m/s (typical industrial cyclone inlet
     velocity)
   - Re_D ≈ 2e5-4e5
   - Particle phase: density ρ_p ≈ 2650 kg/m³ (silica dust
     reference), particle size distribution log-normal or
     uniform spanning 1-50 μm
   - Particle injection: at inlet, mass loading 10-50 g/m³
     (typical industrial dust loading)
8. **Lagrangian config**:
   - kinematicCloud one-way coupled (particle motion follows
     air; no momentum feedback)
   - Drag model: SchillerNaumann or sphere
   - Wall interaction: rebound (or escape on collection
     chamber bottom)
   - 1000-10000 parcels (representative statistics)
   - Time step: pimpleFoam transient dt ~ 1e-3 to 1e-4 s
9. **Determinism**: CadQuery script byte-identical regeneration.
10. **Industrial flavor**: Stairmand cyclone is industry standard
    for dust collection.
11. **Reference data**: predicted d50 cut-off diameter (per
    Stairmand correlation); η(d_p) curve at 5-7 particle sizes.
    CFD vs Stairmand published within ±10% η at d50; ±20% at
    fine dust.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified
project. You design ONE industrial CFD case end-to-end.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/.
17 prior cases (002a/b + 003-017). You designed 004-017.
**case_018 is Phase 4 #2** — Stairmand cyclone separator.
Extends case_008 Lagrangian to swirl-dominant flow.

## Required reading

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (E-class separator)
3. .planning/methodology/public_cad_sources.md (Tier 1 Stairmand
   industry-public dimensions)
4. .planning/methodology/kickoff/case_008_codex_response.md
   (Lagrangian + kinematicCloud)
5. .planning/case_profiles/case_008_glc305_irt_lagrangian.md
6. .planning/methodology/industrial_case_solver_findings.md
   (V36-V37 from case_008 if sedimented)
7. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
8. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
9. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: pimpleFoam transient + RSM (LRR or
   LaunderGibsonRSTM) + kinematicCloud one-way coupled.
   Document RSM choice over k-ε / k-ω-SST.
2. **CAD source**: Tier 1 Stairmand cyclone (1980s industry
   standard). Lapple alternate if Stairmand blocks. Bake-into-
   script.
3. **Geometry physical realism** — Stairmand spec:
   - D = 200-300 mm
   - Inlet 0.5D × 0.2D rectangular
   - Cylindrical body 1.5D
   - Conical 2.5D
   - Vortex finder 0.5D dia × 0.5D length
   - Underflow ≥ 0.4D
4. **Defect injection (REQUIRED 1 defect)**:
   - D6: debris cube 10-30 mm inside collection chamber.
     Advisor=NONE (no LANDED advisor; flag advisor-gap or
     consistency with case_016 if landed).
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Operating point**: Stairmand-typical
   (U_inlet=15-25 m/s, ρ_p=2650 kg/m³, particle 1-50 μm log-
   normal, mass loading 10-50 g/m³).
7. **Lagrangian**: kinematicCloud one-way; SchillerNaumann drag;
   rebound or escape wall interaction; 1000-10000 parcels;
   dt ~ 1e-3 to 1e-4 s.
8. **Industrial flavor**: Stairmand cyclone (dust collection).
9. **Reference data**: d50 ± 10%, η(d_p) ± 10% at d50 / ± 20%
   at fine dust per Stairmand correlation.
10. **NO Ahmed/NACA/Sajben** (Lane B).
11. **NO new defect categories** outside D1-D10.
12. **NO 2D simplification** (cyclone is 3D swirl).
13. **NO k-ε / k-ω-SST** without explicit rationale (RSM
    industry standard for high-swirl).

## Your 5 deliverables

(same format as prior)

### 1. Engineering brief
- Component picked + bank ID + reasoning
- Engineering question (typical: "what is d50 cut-off + η(d_p)
  curve for this Stairmand cyclone with as-installed debris
  defect; does swirl number degrade with debris obstruction?")
- Physics signature (pimpleFoam + RSM + kinematicCloud,
  Re_D=2e5-4e5, swirl number ~ 1-3, particle Stokes 0.01-1.0
  spanning collection regimes)
- Parts inventory (single fluid + named patches + debris body)
- BC plan (inlet_tangential: flowRateInletVelocity / fixedValue
  U; overflow_outlet: pressureOutlet; underflow_outlet:
  pressureOutlet OR closed-bottom with particle escape;
  walls: noSlip)
- Expected metrics:
  - Swirl number S = ∫ U_θ U_z r dA / (R ∫ U_z² dA)
  - d50 cut-off diameter
  - η(d_p) collection efficiency curve at 5-7 particle sizes
  - Pressure drop Δp_inlet-overflow
  - Vortex core trajectory (precessing-vortex-core if RSM
    captures)
- Hypothesized failure modes:
  - V36/V37 inheritance from case_008 (Lagrangian patterns)
  - NEW: RSM convergence sensitivity (slower than k-ε)
  - NEW: vortex core precession capture (PVC unstable below
    convergence threshold)
  - NEW: particle injection plane sensitivity
  - NEW: rebound vs escape wall BC effect on η at fine dust
  - NEW: D6 debris obstruction effect on swirl number
- Defect injection summary
- Sub-session estimated effort: 10-12h

### 2. CAD generation script (Python, executable)

CadQuery preferred:
- Deterministic
- --out CLI with default
- Parametric constants (D_cyclone, inlet_h_factor, inlet_w_factor,
  body_h_factor, cone_h_factor, vortex_finder_d_factor,
  vortex_finder_l_factor, underflow_d_factor, debris_size_mm,
  debris_position_xyz_mm, ...)
- Single fluid region body + named patches
- Defect: D6 debris cube inside collection chamber
- STEP export with named patches preserved (cq.Solid.fuse() per
  V16/V24)

### 3. STEP file path

/Users/Zhuanz/Desktop/case_018_stairmand_cyclone_separator/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- region: region_air (single fluid)
- patches: full list with bc_type plan
- thermophysics: air standard
- particle: ρ_p=2650, size distribution, mass loading,
  parcel count
- cyclone operating point: D, U_inlet, Re_D, swirl number target
- RSM config: model + relaxation factors
- reference: Stairmand correlation citation

### 5. Defect manifest YAML

- D6 [QUESTIONABLE 2026-05-08] (no LANDED advisor for
  extra-body-in-fluid; consistency with case_016 if landed;
  manual FreeCAD body-count + bbox check; flag advisor-gap
  V-finding if first; reinforce if second).

## Format your response

(same as prior)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT use 2D simplification
- Do NOT use k-ε / k-ω-SST without rationale (RSM required)
- Do NOT use steady solver (transient pimpleFoam for vortex
  precession capture)
- Do NOT skip particle injection
- Do NOT use D1/D7/D8/D9 (D6 is the under-utilized choice for
  case_018)
- Do NOT exceed 12h sub-session effort

## Begin
```

## Validation checklist

- [ ] CAD source: Tier 1 Stairmand (or Lapple alternate)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All names ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single fluid region** declared
- [ ] **Stairmand dimensions** per spec (factor ratios documented)
- [ ] D6 debris: 10-30 mm in collection chamber, advisor=NONE
- [ ] Operating point: U_inlet 15-25 m/s, Re_D 2e5-4e5
- [ ] **RSM turbulence model** documented (NOT k-ε / k-ω-SST)
- [ ] **kinematicCloud one-way** documented
- [ ] Particle: ρ_p, size distribution, mass loading, parcel count
- [ ] dt ≤ 1e-3 s for vortex precession capture
- [ ] Reference data (d50 ± 10%, η ± 10-20%) documented
- [ ] D6 advisor-gap V-finding flagged

## After validation passes

(same as prior)

## Risk mitigations

- If Codex picks 2D → revision request
- If Codex picks k-ε / k-ω-SST → revision request (RSM required)
- If Codex skips particle injection → revision request
- If Codex picks steady solver → revision request (transient
  required)
- If 86gs / CRS overload → fall back to other
