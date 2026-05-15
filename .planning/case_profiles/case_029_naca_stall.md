# case_029 · NACA 0012 High-AoA Stall (V65-A net-new industrial · 2nd Tier 2)

**Status**: substrate prep landed (V65-A B75 dispatch · 2026-05-16)
**Parent DEC**: DEC-V65-A-charter
**Sub-DEC**: DEC-V65-A-sub-M-V65A-CASE-NACA-STALL (in flight)
**Tier**: Tier 2 · M-V65A-CASE-NACA-STALL · 2nd V65-A Done #3 contribution + V104 promotion path

## North Star (one line)

> NACA 0012 high-AoA stall canonical airfoil e2e — analytic 4-digit STL (200 chordwise pts cosine-clustered) + rectangular blockMesh + sHM + addLayers (y+ target < 1) + simpleFoam kOmegaSST RAS × 3 AoA (10° / 15° / 18°) + forceCoeffs Cl/Cd/Cm vs NASA TM 4074 (Ladson 1996) Re=3e6 → stall-onset capture quality + V104 promotion judgment (F-NEW-15 inlet BL separation 2nd witness via NACA stall · 1st = case_022 BFS V64-A).

## Case classification

- **Class**: external-flow-around-airfoil (canonical aerodynamic body)
- **Solver**: `simpleFoam` (steady-state RANS)
- **Turbulence**: `kOmegaSST` RAS (industry-standard for airfoil aerodynamics · low-Re wall treatment with all-y+ wall functions)
- **Compressibility**: incompressible (Mach ≈ 0.13 at Re=3e6 · M < 0.3 OK)
- **Geometry source**: programmatic NACA 4-digit analytic formula → `generate_naca_stl.py` → `airfoil.stl` (200 chordwise pts · cosine-clustered · 1604 ASCII STL facets · sharp TE)
- **Re classification**: Re_c = 3 × 10⁶ — matches NASA TM 4074 (Ladson 1996) Re=2-12M experimental data range

## Geometry

- NACA 0012 symmetric airfoil (canonical stall benchmark · zero camber)
- Chord c = 1.0 m
- Span = 0.1 m (pseudo-2D slab · symmetryPlane on spanwise faces · empties also acceptable)
- Sharp trailing edge (closure at last cosine point)
- STL: 1604 facets, 401 polygon points (upper 200 + LE shared + lower 200)

## Domain + BC plan

### Bounding box (30 chord × 20 chord rectangular farfield · pseudo-2D slab)

```
x: -10c to +20c  (30 chord streamwise · -10c upstream · +20c wake)
y: -10c to +10c  (20 chord vertical)
z: -0.05c to +0.05c  (spanwise slab matching STL)
```

### Block boundary patches

| Block face | Patch name | BC type | Physical meaning |
|---|---|---|---|
| -x face (-10c) | `inlet` | freestreamVelocity / zeroGradient p | Inflow farfield |
| +x face (+20c) | `outlet` | freestreamVelocity / freestreamPressure | Outflow farfield |
| +y face (+10c) | `top` | freestreamVelocity / zeroGradient p | Top farfield |
| -y face (-10c) | `bottom` | freestreamVelocity / zeroGradient p | Bottom farfield |
| +z face (+0.05c) | `frontAndBack` (combined) | empty | 2D constraint |
| -z face (-0.05c) | `frontAndBack` | empty | 2D constraint |
| airfoil STL (sHM) | `naca0012` | noSlip | Wing surface |

`freestreamVelocity` (+ `freestreamPressure` on outlet) auto-switches between fixedValue (inflow) and zeroGradient (outflow) based on local flux direction — robust for AoA sweep where flow direction is rotated.

### AoA sweep velocity vectors

Free-stream rotated, airfoil fixed (chord aligned with +x):

| AoA | U vector | |U| |
|---|---|---|
| 10° | (44.32, 7.81, 0) | 45 m/s |
| 15° | (43.47, 11.65, 0) | 45 m/s |
| 18° | (42.80, 13.91, 0) | 45 m/s |

Re_c = ρ * U * c / μ = 1.225 * 45 * 1 / 1.84e-5 ≈ 3.0 × 10⁶ ✓ (NASA TM 4074 range)

Using ν = 1.5e-5 m²/s (kinematic, air at 15°C standard conditions). Mach = 45/340 = 0.132 < 0.3 → incompressible.

### Refinement strategy (sHM)

- Base mesh: blockMesh 60 × 40 × 1 = 2,400 hex cells (0.5c × 0.5c × 0.1c base size)
- Refinement levels around airfoil: (3, 4) → near-surface cells ~0.015c
- Surface refinement: refinementSurfaces `naca0012` level (3, 4)
- Volume refinement region: rectangular box around airfoil x∈[-2c, +4c], y∈[-2c, +2c] at level 2
- nCellsBetweenLevels: 3
- addLayers: 10 layers, expansion ratio 1.2, finalLayerThickness ratio adjusted for y+ < 1 target (first cell ~8 μm at Re=3e6 per Schlichting Cf correlation)
- Expected nCells post-sHM: ~80-150k cells (pseudo-2D)
- locationInMesh: (-5.0, 0.0, 0.0) (point in fluid region upstream of airfoil)

## Verdict scale (per B75 dispatch reverse condition)

- **FULL**: solver converges (residuals < 1e-4 on U / p / k / omega) AND y+ < 1 AND advisor ≥7/9 fired AND experimental delta table |Δ Cl| < 10% × 3 AoA AND stall-onset Δα < 2° AND ≥6/9 V-row clause-2
- **strong-PARTIAL**: convergence + delta table OK BUT y+ in 1-5 range OR advisor 6/9 OR stall-onset Δα 2-4°
- **PARTIAL**: mesh/solver stuck OR any AoA fails to converge OR y+ > 5 OR advisor < 6/9 OR comparison absent

## Done dim advancement target (V65-A charter)

- **Done #3** (net-new industrial e2e): 1/2 → **2/2 ✓ MET** (primary B75 contribution · must-met by /goal condition (i))
- **Done #4** (industrial-grade FULL reports): 0/3 → **0 or 1/3** (verdict-dependent · only FULL advances)
- **Done #1** (carry-over absorption): 0/5 → **1/5** (V64-A carry-over #2 F-NEW-15 inlet BL separation 2nd witness via NACA stall)
- **Done #2** (V101+ promotion): 1/6 → **2/6** if V104 LANDED (F-NEW-15 2nd witness LANDS), else stays 1/6 + V104 QUESTIONABLE
- **Done #6** clause-1 (≥7/9 V-row): per advisor stack run
- **Done #6** clause-2 (≥5/9 on ≥2 cases): per advisor stack run (case_028 was clause-1 over-met at 8/9 single case)

## V-row attribution targets (≥6/9 clause-2)

Expected advisor coverage for canonical airfoil case:

| Advisor | V-row potential | case_028 status |
|---|---|---|
| `face_orientation_advisor` (V29/V79/V87) | likely fire on airfoil STL | ✓ fired (3 V-rows) |
| `inlet_outlet_validator` (V81) | inlet/outlet block patches | ✓ fired (1 V-row) |
| `bc_type_name_validity_advisor` (V29) | freestreamVelocity / noSlip / empty types | ✓ fired |
| `shm_dict_validator` (V52/V86/V99/V100) | refinementSurfaces audit | ✓ fired (4 V-rows) |
| `solver_block_advisor` (V64-A B55) | simpleFoam steady-state block | ✗ input gap (case_028) → **plumb stl_bbox_set + solver_block_snapshot for case_029** |
| `extra_body_advisor` (V55) | single airfoil body vs manifest | ✗ input gap (case_028) → plumb |
| `unit_detector` (V96/V97) | domain extent plausibility | ✓ fires from step_body_extents_raw |
| `thin_wall_advisor` | sharp TE = thin-wall candidate | ✗ input gap (case_028) → plumb thin_wall_inputs |
| `stl_face_label_validator` (V94) | per-component STL preservation | ✗ input gap (case_028) → optional plumb via shm_stl_face_normals |
| `thermo_polynomial_range_advisor` (V93) | N/A (incompressible) | N/A |
| `virtual_interface_detector` | N/A (single region) | N/A |

**case_029 plumbing goal**: build runner script with stl_bbox_set + solver_block_snapshot + thin_wall_inputs + shm_stl_face_normals → close 4 of 5 case_028 input gaps → achieve **≥7/9 fired** (input gap closing is V102+ candidate · pattern continuity if also surfaces on case_030+).

## Canonical reference (for Done #4 experimental/literature comparison)

- **Primary**: NASA TM 4074 (Ladson 1996) *Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section* — NACA 0012 Re=2-12M Cl-α + Cd-α + Cm-α + stall-onset α_max,Cl tabulated
- **Secondary**: NACA TR-460 (Jacobs 1933) *The Characteristics of 78 Related Airfoil Sections from Tests in the Variable-Density Wind Tunnel* — historical NACA 0012 benchmark
- **Tertiary**: Sheldahl & Klimas (1981) SAND80-2114 — NACA 0012 wider AoA range incl. post-stall

Expected canonical data points at Re=3e6 (interpolated from NASA TM 4074 Re=2.88M table):
- α=10°: Cl ≈ 1.08, Cd ≈ 0.012
- α=15°: Cl ≈ 1.52 (near stall), Cd ≈ 0.025
- α=18°: Cl ≈ 1.20 (post-stall · separated), Cd ≈ 0.08+
- α_max,Cl (stall onset): ≈ 16° experimental

**Known kOmegaSST RANS limit**: typically under-predicts stall onset by 1-2° α AND/OR over-predicts max Cl on attached side — industry-known separation-class limitation, **honest disclosure required** per V64-A B66 F-NEW-15 precedent (case_022 BFS inlet BL thickness mismatch shows same kOmegaSST RANS class-limit).

## Sandbox path

- **Repo dicts**: `.planning/case_profiles/case_029_naca_stall_dicts/` (committed)
- **Sandbox**: `~/Desktop/case_029_naca_stall/case/` (NOT in git · Docker mount source)
- **NACA STL generator**: `~/Desktop/case_029_naca_stall/generate_naca_stl.py` (NOT in git · regeneration script)
- **STL artifact**: `~/Desktop/case_029_naca_stall/airfoil.stl` (1604 facets · regenerable from Python)

## Docker container

- Image: `opencfd/openfoam-default:2312` (same as case_028)
- Invocation pattern: `docker run --rm -v ~/Desktop/case_029_naca_stall/case:/case opencfd/openfoam-default:2312 bash -c "cd /case && <cmd>"`
- One-shot per command (no persistent container)

## Per-AoA case dir convention

After single mesh build in `case/`:
```
cp -r case case_aoa_10
cp -r case case_aoa_15
cp -r case case_aoa_18
# Edit 0/U.freestreamValue per AoA in each subdir
# Run simpleFoam in each
```

This saves ~2× meshing time vs per-AoA fresh mesh.

## V104 promotion criterion (per V65-A charter §"V101+ promotion queue")

V104 candidate: F-NEW-15 inlet BL thickness mismatch · separation 2nd witness via NACA stall.

**LANDED criterion**: NACA stall reproduces consistent kOmegaSST RANS pattern at high AoA — under-predicted stall-onset Δα ≥ 1° OR over-predicted attached-side Cl ≥ 5% at α=10° AND distinct-signature attributed via "kOmegaSST RANS high-AoA stall under-prediction" + canonical reference attribution NASA TM 4074.

**QUESTIONABLE criterion**: stall onset matches NASA TM 4074 within 1° AND Cl error < 5% at all 3 AoA — RANS captures separation accurately, V104 does not LAND, pending 3rd witness.

**no-promote criterion**: NACA case PARTIAL (any AoA blocked) — insufficient evidence either way, V104 stays as V64-A B66 single-witness candidate.

## Out of scope (explicit · per B75 brief)

- ❌ LES / DES variant (V65-A RANS scope · DES deferred V66+)
- ❌ Transonic / compressible (M < 0.3 in scope · M > 0.3 deferred)
- ❌ NACA 4412 cambered alternate (mentioned as fallback but not pursued · NACA 0012 is canonical stall benchmark)
- ❌ Modification to case_001..028 substrates
- ❌ Advisor stack extension (no new advisor file added · only kwargs plumbed in runner)
- ❌ Codex review (v2.3 1-sync-trigger N/A · no auth/signing/security surface)
- ❌ Kogami invocation (opt-in only · user did not invoke)
- ❌ Notion sync (session-end batch · only Accepted DECs)

## Next action

Commit 1: substrate (spec + RESUME + dicts + STL generator).
Commit 2: mesh (blockMesh + sHM + addLayers + checkMesh PASS + y+ verification).
Commit 3: solver × 3 AoA + advisor stack + report.
Commit 4: sub-DEC + ARC-GOAL.
