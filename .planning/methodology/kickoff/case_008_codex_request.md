# Codex Case-Design Request · case_008

> **Status**: drafted 2026-05-08; queued behind case_007 in
> single-fire sequence.

## Target

| field | value |
|---|---|
| case_id | `case_008_<short_name>` (working name `case_008_irt_icing_lagrangian`) |
| solver_class_target | external + Lagrangian particle (icing droplet impingement) |
| numerics_class | **incompressible-RANS-Lagrangian** (new — pure Pattern 6 root) |
| coverage map row to fill | "Particle-laden / Lagrangian (icing)" — currently 📝 proposed |
| CAD source priority | Tier-1 NASA Glenn IRT reference airfoil — GLC305 OR NACA 23012; NEVER NACA 0012 (Lane B) |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_008_<short_name>/` |

## Why NASA IRT icing as case_008

Fills the Lagrangian particle-laden row. New infrastructure:
- Lagrangian cloud (kinematicCloud / DPMFoam / sprayFoam — Codex picks)
- Particle injection model (point-injection upstream, MVD distribution)
- Particle-wall interaction model (impact, stick, splash)
- Collection efficiency β post-processing
- Coupling: 1-way (particles tracked through Eulerian flow; flow not affected)

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified project. Design ONE industrial CFD case end-to-end.

## Project context
cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198, accumulates industrial CFD experience. Seven cases dispatched (case_002a, 002b, 003-007). case_008 fills the **incompressible-RANS-Lagrangian (icing droplet impingement)** row — first Lagrangian case for project.

## Required reading (in repo)
1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (Lane B exclusions: Ahmed / **NACA 0012** / Sajben / BFS / Ercoftac mixing tank)
3. .planning/methodology/public_cad_sources.md (NASA Glenn IRT references)
4. .planning/methodology/kickoff/case_006_codex_response.md AND case_007_codex_response.md (your prior outputs; same pattern)
5. .planning/methodology/industrial_case_solver_findings.md (Pattern 6: case_008 inherits NONE of prior numerics classes)

## Hard constraints

1. **Solver class**: external + Lagrangian particle (icing droplet impingement). v1: simpleFoam + kinematicCloud (1-way coupling, particles tracked through converged Eulerian flow). v2 fallback: DPMFoam (full 2-way coupling) ONLY if particle volume fraction is non-negligible (typical IRT LWC ≪ 1, so 1-way is sufficient)
2. **CAD source priority**:
   - PRIMARY: **GLC305** (Glaze ICE airfoil at 305 mm chord, NASA Glenn IRT standard) — clean baseline geometry, NO ice horn (the horn is what the harness would PREDICT, not part of the input geometry)
   - FALLBACK 1: **NACA 23012** (NACA 5-digit airfoil, used in NASA TM-2007-214921 IRT validation)
   - FALLBACK 2: any other NASA Glenn IRT reference airfoil from public_cad_sources.md
   - **HARD EXCLUSION**: do NOT pick NACA 0012 (Lane B excluded)
3. **Defect injection**: exactly 2 defects from D1-D10. Defects must NOT be at the leading-edge stagnation region (where droplet impingement and collection efficiency β are measured). Safe locations: trailing-edge (D8 thin shell), wing-root mounting bracket / strut (D1 gap, D5 degenerate tri, D6 sharp corner)
4. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$
5. **Lagrangian cloud setup explicit**: parts manifest must include `lagrangian_cloud:` block with cloud name, injection model (`patchInjection` or `manualInjection`), particle properties (LWC = 0.5-1.0 g/m³ typical IRT, MVD = 15-40 µm typical, density 1000 kg/m³ liquid water), drag model, particle-force model, particle-wall interaction (`stick` for icing collection), max parcels per second
6. **Engineering metric**: collection efficiency β = (particle mass flux at surface) / (freestream particle mass flux × cosθ). Parts manifest must declare `collection_efficiency:` block with measurement strategy (band of patches at LE, or surface-integral on each spanwise station)
7. **Reference conditions**: freestream U_inf = 67 m/s (typical IRT), T_inf = 268 K (icing T below freezing), p_atm = 101325, ν_air = 1.4e-5, Re ≈ 1.8e6 at chord 305 mm
8. **Reference-data preservation**: leading-edge β(s/c) curves and 2D ice shapes from NASA Glenn IRT must remain measurable (defects NOT on LE between -10° and +30° angle around stagnation)
9. **Determinism**: byte-identical STEP given identical inputs
10. **Industrial flavor**: GLC305 IS — it's the canonical FAR Part 25 Appendix C icing certification reference geometry
11. **Symmetry plane** at one wing end (2D-extruded slab simulation is acceptable for v1; full 3D is over-scope for case_008)
12. **Steady-state Eulerian**: simpleFoam converges first, THEN kinematicCloud is added for particle tracking (1-way coupling means particles follow steady flow field)
13. **Mach regime**: incompressible (M ≈ 0.2 at 67 m/s)
14. **No ice horn in input geometry**: the airfoil is CLEAN; the harness's role is to predict where ice would accrete via β(s/c) — the actual horn shape is an ICE3D output, NOT a CAD input

## Your 5 deliverables (same format as case_007)

### 1. Engineering brief (Markdown)
Component + bank ID / Engineering question (collection efficiency β at LE; impingement limits at upper/lower s/c) / Physics signature (Re, U_inf, MVD, LWC, dimensionless K = ρ_p·D²·U / (18·μ_air·c) inertia parameter) / Parts inventory (airfoil_clean, optional auxiliary defect bodies, inlet, outlet, sym_plane_left/right, farfield_top/bottom) / BC plan / Expected metrics (β(s/c) curve at multiple spans, impingement limit s_upper / s_lower, total catch rate) / Hypothesized failure modes (Lagrangian-specific) / Defect summary / Effort estimate

### 2. CAD generation script (Python, executable)
- GLC305 (or chosen) coordinate table baked in
- 2D-extruded slab geometry (2 spanwise units = 1 chord), with sym_plane_left + sym_plane_right
- Outer farfield box
- Optional auxiliary defect bodies (NOT on LE stagnation region)
- Export STEP

### 3. STEP file path
`/Users/Zhuanz/Desktop/case_008_<name>/inputs/cad_codex_v1.step`

### 4. Parts manifest YAML
Plus:
- `lagrangian_cloud:` block (kinematicCloud config)
- `freestream:` block (U_inf, T_inf, p_atm, MVD, LWC, particle_density)
- `collection_efficiency:` block (measurement strategy)
- `dimensionless_groups:` block (Re, K inertia, Stokes, We if relevant)

### 5. Defect manifest YAML
Two defects, D1-D10. LE β-measurement zone defect-free.

## Format response (same as case_007)

## Round budget
Round 1 of 2.

## What you should NOT do
- Do NOT pick NACA 0012 (Lane B excluded — HARD)
- Do NOT pick Ahmed / Sajben / BFS / Ercoftac (Lane B)
- Do NOT include ice horn shape — input is CLEAN airfoil
- Do NOT include heat transfer / icing thermodynamics — case_008 is collision-only β(s/c); ICE3D thermal coupling is out-of-scope
- Do NOT use 2-way DPM coupling for v1 — typical IRT LWC is dilute, 1-way kinematicCloud is correct
- Do NOT include rotating elements / compressible thermo / multiphase VOF
- Do NOT design defects on LE stagnation — that's the measurement zone

## Begin
```

## Validation checklist
- [ ] CAD source: GLC305 / NACA 23012 / other IRT (NOT NACA 0012)
- [ ] Script syntax-clean
- [ ] All patch names valid
- [ ] **lagrangian_cloud block** with kinematicCloud config
- [ ] **freestream block** with MVD / LWC / particle_density
- [ ] **collection_efficiency block** with β measurement strategy
- [ ] Both defects NOT on LE stagnation region
- [ ] Both defects measurable
- [ ] Symmetry planes for 2D-extruded slab
- [ ] expected_advisor_to_catch references real or pending advisor
