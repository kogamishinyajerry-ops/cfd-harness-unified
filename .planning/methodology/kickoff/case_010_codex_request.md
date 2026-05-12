# Codex Case-Design Request · case_010

> **Status**: drafted 2026-05-08; queued behind case_007/008/009
> in single-fire sequence.

## Target

| field | value |
|---|---|
| case_id | `case_010_<short_name>` (working name `case_010_drivaer_les`) |
| solver_class_target | external transient LES (vehicle aerodynamics) |
| numerics_class | **incompressible-LES** (new — pure Pattern 6 root) |
| coverage map row to fill | "Transient LES / DES" — currently 📝 proposed |
| CAD source priority | Tier-1 DrivAer fastback (TUM / BMW-AUDI public benchmark) |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_010_<short_name>/` |

## Why DrivAer LES as case_010

Fills the transient LES row. New infrastructure:
- `pimpleFoam` (or `pisoFoam`) transient solver path
- LES turbulence model (Smagorinsky / WALE / dynamic-k Lilly)
- Temporal averaging via `fieldAverage` function object
- Wall-modeling: wall functions vs resolved viscous sublayer
  (DrivAer typical: wall-modeled LES with `nutUSpaldingWallFunction`)
- Vortex / wake-coherent-structure post-processing
  (Q-criterion, λ2, FW-H if acoustic)

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified project. Design ONE industrial CFD case end-to-end.

## Project context
cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198, accumulates industrial CFD experience. Nine cases dispatched (case_002a, 002b, 003-009). case_010 fills the **transient LES external (vehicle aerodynamics)** row — first transient LES case for project. Final case in the 10-case roster.

## Required reading (in repo)
1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (Lane B exclusions: **Ahmed body** explicitly EXCLUDED)
3. .planning/methodology/public_cad_sources.md
4. .planning/methodology/kickoff/case_008_codex_response.md AND case_009_codex_response.md (your prior; same pattern)
5. .planning/methodology/industrial_case_solver_findings.md (Pattern 6: case_010 inherits NONE)

## Hard constraints

1. **Solver class**: external transient LES. v1: pimpleFoam + LES (WALE or dynamic-k Lilly subgrid model). v2 fallback: pisoFoam if pimple's pressure-velocity coupling under-converges per timestep
2. **CAD source priority**:
   - PRIMARY: **DrivAer fastback** (TUM / Heft-Indinger-Adams 2012 public benchmark; geometry available via TUM website). DrivAer has 3 standard configurations: notchback, fastback, estate-back. Pick **FASTBACK** (most common LES validation target)
   - **HARD EXCLUSION**: do NOT pick Ahmed body (Lane B excluded)
   - FALLBACK: any TUM-derived simplified vehicle (e.g., DrivAer-derived simplified box-with-A-pillars) ONLY if DrivAer license blocks
3. **Wall-modeled LES regime**: target Reynolds Re_L ≈ 4.87e6 (DrivAer model-scale at 16 m/s). Wall y+ ≈ 30-100 (wall-modeled, NOT resolved sublayer — full DNS-quality LES is multi-month effort, out-of-scope). Use `nutUSpaldingWallFunction` for U-tangential modeling
4. **Defect injection**: exactly 2 defects from D1-D10. Defects must NOT be on:
   - Front wheel housings (drag contribution measurement zone)
   - Rear-wake measurement plane (Cd / Cl / Cm validation)
   - Vehicle centerline (symmetry plane)
   Safe locations: side-mirror housing edge, side underbody area outside wake plane
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$
6. **Symmetry plane at vehicle centerline** (half-vehicle); standard practice for DrivAer LES
7. **Domain sizing explicit**: parts manifest declares blockMesh dimensions:
   - Upstream: 4 L (vehicle length L ≈ 4.6 m)
   - Downstream: 8 L (capture wake)
   - Top: 5 L
   - Side: 3 L (half-domain due to symmetry)
   - Ground: y=0 fixed wall (or moving floor at U_inf for ground-effect studies — pick fixed for v1 simplicity)
8. **LES setup explicit**: parts manifest must include `les:` block with:
   - subgrid model (WALE or dynamicKEqn)
   - filter type (cubeRootVol)
   - wall treatment (nutUSpaldingWallFunction)
   - timestep target (CFL ≤ 1, expect dt ≈ 1e-4 s for Re_L = 4.87e6 with L=4.6m)
   - averaging window (start at t = 2 L/U_inf flow-throughs after init transient, accumulate over ≥ 5 flow-throughs)
9. **Reference data preservation**: front-wheel + rear-wake regions defect-free. DrivAer published Cd, Cl, surface pressure at A-pillar / mirror / rear / underbody must remain measurable
10. **Vortex post-processing explicit**: parts manifest declares `vortex_metrics:` block (Q-criterion threshold, λ2 threshold, isosurface generation strategy)
11. **Determinism**: byte-identical STEP given identical inputs
12. **Industrial flavor**: DrivAer IS — actual BMW/AUDI body shape published as research benchmark; canonical for vehicle-aero LES
13. **Mach regime**: incompressible (M ≈ 0.05); pure incompressible-LES, no compressible thermo
14. **No moving boundary in v1**: wheels stationary, ground stationary. Moving-floor / rotating-wheel is v3+ extension if needed (and is sub-session decision, not Codex's design call)

## Your 5 deliverables (same format as case_009)

### 1. Engineering brief (Markdown)
Component + bank ID / Engineering question (Cd target ≈ 0.281 fastback per TUM; instantaneous wake structures + time-averaged surface Cp + base pressure recovery) / Physics signature (Re_L, U_inf, expected wake topology: A-pillar vortex, side mirror vortex, rear separation, ground-vehicle gap flow) / Parts inventory (vehicle_body, side_mirror_left/right merged or skipped per DrivAer config, wheels_front_left/right, wheels_rear_left/right, ground, symmetry_plane_centerline, inlet, outlet, top, side_outboard, optional auxiliary defect bodies) / BC plan / Expected metrics (Cd / Cl / Cm time-averaged, surface Cp at TUM published taps, wake topology Q/λ2, instantaneous + time-averaged velocity fields) / Hypothesized failure modes (LES-specific) / Defect summary / Effort estimate (10-14h)

### 2. CAD generation script (Python, executable)
- DrivAer fastback CAD reconstruction from published TUM offsets (or load STEP if available)
- 4 wheels (stationary in v1), 2 side mirrors, optional rear spoiler if fastback configuration includes one
- Symmetry plane at centerline
- BlockMesh-ready domain box
- Optional auxiliary defect bodies on safe zones (side-mirror housing edge, side-underbody)
- Export STEP

### 3. STEP file path
`/Users/Zhuanz/Desktop/case_010_<name>/inputs/cad_codex_v1.step`

### 4. Parts manifest YAML
Plus:
- `freestream:` block (U_inf=16 m/s typical or higher, T, p, Re_L)
- `les:` block (subgrid model, filter, wall treatment, dt target, averaging strategy)
- `vortex_metrics:` block (Q / λ2 thresholds)
- `reference_data:` block (TUM Cd reference, surface pressure tap locations)

### 5. Defect manifest YAML
Two defects, D1-D10. Front-wheel + rear-wake + centerline defect-free.

## Format response (same as case_009)

## Round budget
Round 1 of 2.

## What you should NOT do
- Do NOT pick Ahmed body (HARD Lane B exclusion)
- Do NOT pick NACA 0012 / Sajben / BFS / Ercoftac (Lane B)
- Do NOT design DNS-quality wall-resolved LES — wall-modeled is correct for case_010 scope
- Do NOT include moving wheels / rotating tires for v1
- Do NOT include compressible thermo / multiphase / Lagrangian / reacting / MRF
- Do NOT design defects on Cd-measurement zones
- Do NOT pick estate-back or notchback DrivAer variants — fastback is canonical LES validation target

## Begin
```

## Validation checklist
- [ ] CAD: DrivAer fastback (NOT Ahmed body)
- [ ] Script syntax-clean
- [ ] All patch names valid
- [ ] Symmetry plane at vehicle centerline declared
- [ ] **les block** with subgrid model + wall treatment + dt + averaging strategy
- [ ] **freestream block** with Re_L ≈ 4.87e6
- [ ] **vortex_metrics block** with Q / λ2
- [ ] Defects NOT on front-wheel / rear-wake / centerline
- [ ] Both defects measurable
- [ ] Domain sizing per blockMesh (4L upstream, 8L downstream, etc.)
- [ ] expected_advisor_to_catch references real or pending advisor
