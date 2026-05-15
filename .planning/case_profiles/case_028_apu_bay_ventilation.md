# case_028 · APU Bay Ventilation (V65-A net-new industrial)

**Status**: substrate prep landed (V65-A B74 dispatch · 2026-05-16)
**Parent DEC**: DEC-V65-A-charter
**Sub-DEC**: DEC-V65-A-sub-M-V65A-CASE-APU-BAY (in flight)
**Tier**: Tier 2 · M-V65A-CASE-APU-BAY · primary V65-A Done #3 contribution

## North Star (one line)

> 把 V64-A 1D analytical strict-FULL 方法论真正落到 industrial-grade — APU bay 17 机械部件 + ×2 实例几何 + per_solid 29 STL face-name preservation + simpleFoam kOmegaSST RAS ventilation flow + mass conservation Δṁ < 1% + advisor stack ≥5/9 V-row clause-2 attribution + experimental/literature comparison to APU bay typical ventilation Re.

## Case classification

- **Class**: external-flow-in-bounded-domain (bay enclosure with internal obstacles)
- **Solver**: `simpleFoam` (NOT chtMultiRegionFoam · CHT 推迟到 V65-B / V66)
- **Turbulence**: `kOmegaSST` RAS
- **Compressibility**: incompressible (Mach ≪ 0.1 at typical APU bay ventilation Re)
- **Geometry source**: external project `~/Desktop/apu-bay-ventilation-cht/work/stl_repair/per_solid/` (29 component STLs · 560 MB total · NOT in git per case_021..027 substrate convention)

## Geometry inventory (29 per_solid STLs · external sandbox)

### Bay enclosure (defines fluid region boundary)
- `Outer_Surf.stl` (50 MB) — bay outer shell
- `Inner_Surf.stl` (50 MB) — bay inner walls
- `Plane_Outer_Surf.stl` (57 MB) — outer plane segment

### Ventilation pathway components (inlet/outlet surface candidates)
- `intake_duct.stl` — intake (air entry path)
- `vent_door.stl` — vent (potential outlet)
- `door.stl` — operable door (closed in baseline)
- `plenum.stl` — distribution plenum
- `exhaust_pipe_1.stl` — exhaust pipe section
- `exhaust_section.stl` — exhaust manifold section
- `bleed_air_pipe.stl` — bleed air piping
- `ejector.stl` — ejector pump assembly

### APU core components (interior obstacles · walls)
- `gearbox_1.stl` · `gearbox_2.stl` (×2 instance per memory project_apu_bay_step_reexport)
- `compressor.stl` (70 MB) · `load_compressor.stl`
- `load_volute.stl` (138 MB · largest single component)
- `combustion_chamber.stl`
- `fuel_valve.stl` (×2 instance · single STL)

### Structural members (walls)
- `firewall_front.stl` · `firewall_behind.stl`
- `Frame_1.stl` · `Frame_2.stl` · `Frame_3.stl` · `Frame_4.stl` · `Frame_5.stl` · `Frame_6.stl`
- `beam_1.stl` · `beam_2.stl` · `beam_3.stl`

## Domain + BC plan

### Bounding box (inherited from source CHT baseline · validated sHM at 89,745 cells)

```
(63.5  -1.0  -1.5) to (67.5  2.5  1.5)  // 4 × 3.5 × 3 m bay enclosure
```

### Block boundary split (modification vs source CHT)

Source CHT had single `bg_walls` patch. For ventilation simpleFoam we split:

| Block face | Patch name | BC type | Physical meaning |
|---|---|---|---|
| +x face (67.5) | `outlet` | pressureInletOutletVelocity / fixedValue p=0 | Ventilation exhaust |
| -x face (63.5) | `inlet` | fixedValue U=(5 0 0) | Ventilation intake (5 m/s typical APU bay flow) |
| +y face (2.5) | `bay_top` | slip / symmetry | Top of bay (above APU clearance) |
| -y face (-1.0) | `bay_bottom` | slip / symmetry | Bottom of bay |
| +z face (1.5) | `bay_side_p` | slip / symmetry | Lateral bay walls |
| -z face (-1.5) | `bay_side_n` | slip / symmetry | Lateral bay walls |

Rationale: inflow/outflow along +x (longitudinal · aligned with engine compartment airflow direction); slip on 4 lateral faces models extended bay envelope without forcing artificial wall friction; STL components inside = noSlip walls.

### Refinement strategy

- Base mesh: 40 × 35 × 30 = 42,000 hex cells (same as source CHT)
- Refinement: per_solid surfaces at level (0 1) — single level near components
- Expected nCells post-sHM: ~80,000 - 120,000 (depends on per_solid face count + nCellsBetweenLevels)
- nCellsBetweenLevels: 2
- locationInMesh: `(63.8 0.5 0.0)` (inherited from source CHT · point in fluid region between Outer_Surf and APU components)

## Verdict scale (per B74 dispatch reverse condition)

- **FULL**: solver converges (residuals < 1e-4 on U / p / k / omega) AND mass balance Δṁ < 1% AND advisor ≥5/9 V-row clause-2 AND experimental/literature comparison present (even qualitative)
- **strong-PARTIAL**: convergence + mass balance OK BUT experimental comparison weak OR advisor < 5/9
- **PARTIAL**: mesh/solver any stage blocked (checkMesh FAIL or residual stuck or mass balance > 5%)

## Done dim advancement target (V65-A charter)

- **Done #3** (net-new industrial e2e): 0/2 → **1/2** ✓ (primary B74 contribution)
- **Done #4** (industrial-grade FULL reports): 0/3 → **0 or 1/3** (verdict-dependent)
- **Done #1** (carry-over absorption): 0/5 (unchanged · APU bay is not a V64-A carry-over)
- **Done #6** (V-row truth-capture): clause-2 contribution depends on advisor coverage

## V-row attribution targets (≥5/9 clause-2)

Expected advisor coverage on APU bay ventilation case:

| Advisor | V-row potential |
|---|---|
| `face_orientation_advisor` (V79/V87) | likely surface — 29 named STLs |
| `shm_dict_validator` (V52/V86/V99/V100) | refinementSurfaces dict audit |
| `stl_face_label_validator` (V94) | per-component face-zone preservation |
| `inlet_outlet_validator` (V81) | new inlet/outlet patches on blockMesh side |
| `solver_block_advisor` (V64-A B55) | simpleFoam steady-state block coverage |
| `extra_body_advisor` (V55) | 29 named bodies vs case profile manifest |
| `unit_detector` (V96/V97) | bbox-range plausibility on 4 × 3.5 × 3 m bay |
| `thermo_polynomial_range_advisor` (V93) | N/A (incompressible · no thermo) |
| `face_normal_uniqueness` (V99 widening) | per-component STL normal uniqueness |

Target ≥5/9 attribution; clause-2 distinct-case witness via case_028 (new) vs case_002a (V63-A simplified APU bay) + case_003 (CRM-HLS) cross-coverage.

## Canonical reference (for Done #4 experimental/literature comparison)

- **Primary**: SAE AIR1168/4 *APU Installation* — typical APU bay ventilation Re ≈ 10^5 - 10^6, ventilation flow 0.5-2 kg/s per APU, bay temperature rise 30-60 K above ambient
- **Secondary**: ISO 7967-9 *Gas turbines · Vocabulary · Auxiliary power units* — APU bay airflow definitions
- **Tertiary**: Howe (2003) *Acoustics of Fluid-Structure Interactions* ch.4 — confined cavity ventilation Re scaling

Qualitative-only comparison expected at B74 (verdict gates "experimental comparison even qualitative" suffices for strong-PARTIAL / FULL distinction).

## Sandbox path

- **Repo dicts**: `.planning/case_profiles/case_028_apu_bay_ventilation_dicts/` (committed)
- **Sandbox**: `~/Desktop/case_028_apu_bay_ventilation/case/` (NOT in git · Docker mount source)
- **External geometry source** (READ-ONLY): `~/Desktop/apu-bay-ventilation-cht/work/stl_repair/per_solid/`

## Docker container

- Image: `opencfd/openfoam-default:2312`
- Invocation pattern: `docker run --rm -v ~/Desktop/case_028_apu_bay_ventilation/case:/case opencfd/openfoam-default:2312 bash -c "cd /case && <cmd>"`
- One-shot per command (no persistent container)

## Out of scope (explicit · per B74 brief)

- ❌ CHT (chtMultiRegionFoam) path · CHT deferred to V65-B / V66
- ❌ Modification to source `~/Desktop/apu-bay-ventilation-cht/` (read-only)
- ❌ V102+ promotions (V101 already LANDED at B73)
- ❌ Advisor stack extension (B74 uses 12 LANDED advisors as-is)
- ❌ STAR-CCM+ delivery path (V65-A is OpenFOAM-based · STAR-CCM+ is independent project)
- ❌ Modification to case_001..027 substrates
- ❌ Kogami invocation (opt-in only · user did not invoke)
- ❌ Notion sync (session-end batch)

## Next action

Commit 1: write substrate spec + RESUME + parts_manifest + initial dicts skeleton, populate sandbox geometry from external source, prepare blockMeshDict + snappyHexMeshDict for ventilation BC split.
