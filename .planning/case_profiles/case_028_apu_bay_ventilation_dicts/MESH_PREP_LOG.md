# case_028 · Mesh Prep Log

**Date**: 2026-05-16 (V65-A B74 dispatch)
**Container**: opencfd/openfoam-default:2312 (fresh `--rm` invocations)
**Sandbox**: `/Users/Zhuanz/Desktop/case_028_apu_bay_ventilation/case`
**Source geometry**: `~/Desktop/apu-bay-ventilation-cht/work/stl_repair/per_solid/` (29 STLs · 560 MB · READ-ONLY)

## blockMesh result

- **nCells**: 42,000 hexahedra ✓ (matches spec 40 × 35 × 30)
- **nPoints**: 45,756
- **nFaces**: 129,650 (122,350 internal + 7,300 named patches)
- **Bounding box**: (63.5, -1.0, -1.5) to (67.5, 2.5, 1.5) m ✓
- **Cell size**: i=j=k=0.1 m (uniform · simpleGrading 1 1 1)
- **Patch split**: 6 patches as designed
  - inlet (1050 faces · -x face)
  - outlet (1050 faces · +x face)
  - bay_top (1200 faces · +y face)
  - bay_bottom (1200 faces · -y face)
  - bay_side_p (1400 faces · +z face)
  - bay_side_n (1400 faces · -z face)

**Verdict**: blockMesh PASS

## snappyHexMesh result

**Runtime**: 41.52 s (M-class Mac · single-thread sHM)

**Mesh state at end-of-snap**:
- nCells: **89,784** (vs source CHT baseline 89,745 · within 0.04% rounding)
- nFaces: 290,339
- nPoints: 113,237
- Cells per refinement level:
  - level 0: 33,362
  - level 1: 56,422

**Quality at end-of-snap** (9 checks):
- non-orthogonality > 65° : 0 faces
- face pyramid volume < 1e-13: 0
- face-decomposition tet quality < 1e-30: 0 (4 transient → restored)
- concavity > 80°: 0
- skewness > 4 (internal) / > 20 (boundary): 0
- interpolation weights < 0.05: 0
- volume ratio neighbours < 0.01: 0
- face twist < 0.02: 0
- determinant < 0.001: 0

**Mesh log**: "Finished meshing without any errors"

**Verdict**: sHM PASS (no errors · no quality flags · 1-pass castellation + snap)

## checkMesh result

| Check | Status |
|---|---|
| Boundary definition | OK |
| Cell to face addressing | OK |
| Point usage | OK |
| Upper triangular ordering | OK |
| Face vertices | OK |
| Number of regions | 1 (OK) |
| Patch topology (35 patches) | all OK (non-closed singly connected · 29 STL + 6 block) |
| Geometric directions | 3 (3D mesh OK) |
| Boundary openness | OK (5e-18 numerical noise) |
| Max aspect ratio | **9.15** ✓ (< 100 · excellent) |
| Min face area | 1.16e-4 m² · OK |
| Max face area | 1.53e-2 m² · OK |
| Min cell volume | 9.83e-6 m³ · OK |
| Max cell volume | 1.54e-3 m³ · OK |
| **Total domain volume** | **40.45 m³** (vs bbox 42 m³ → fluid:obstacle = 96.3%:3.7%) |
| Mesh non-orthogonality | **Max 61.24 / Avg 10.53** ✓ (< 65) |
| Max skewness | **3.58** ✓ (< 4) |
| Coupled point location match | OK |

**Verdict**: checkMesh **Mesh OK** (no flags · no errors)

## Patch face counts (post-sHM)

### Block patches (inherited from blockMesh, unchanged by sHM)
- inlet: 1050 · outlet: 1050 · bay_top: 1200 · bay_bottom: 1200 · bay_side_p: 1400 · bay_side_n: 1400

### STL-derived patches (sHM-generated · per-component preserved ✓)

| Patch | Faces | Note |
|---|---|---|
| Outer_Surf | 3825 | bay outer shell (significant intersection) |
| Inner_Surf | 3861 | bay inner walls (significant intersection) |
| Plane_Outer_Surf | 2959 | outer plane segment |
| intake_duct | 1568 | intake air duct |
| door | 1967 | operable door (closed) |
| firewall_front | 1336 | front firewall |
| firewall_behind | 3633 | rear firewall (largest STL-derived patch) |
| ejector | 663 | ejector pump |
| plenum | 412 | distribution plenum |
| exhaust_pipe_1 | 428 | exhaust pipe section |
| bleed_air_pipe | 274 | bleed air piping |
| load_volute | 227 | load volute (large STL · most outside bay bbox) |
| combustion_chamber | 165 | combustion chamber |
| Frame_5 | 142 | most prominent frame |
| beam_2 | 141 | beam_2 |
| gearbox_2 | 141 | APU accessory gearbox #2 |
| compressor | 132 | APU compressor |
| beam_1 / beam_3 | 146 / 141 | beams |
| gearbox_1 | 114 | APU accessory gearbox #1 |
| vent_door | 167 | vent door |
| exhaust_section | 110 | exhaust manifold |
| fuel_valve | 79 | fuel valve (×2 instance merged) |
| load_compressor | 51 | load compressor |
| Frame_1..Frame_6 | 3/2/1/2/142/1 | structural frames (most outside fluid region) |

**29 STL components recognized as distinct patches** ✓ — face-name semantics preserved through CAD→STL→sHM. V94-family gap avoided (no face-zone loss).

**Note on small-face Frames (Frame_1/2/3/4/6)**: 1-3 faces each. These STLs are mostly outside the bay bbox or got refined to small intersection bands. Not a defect — these frames have minimal flow-region presence. sHM correctly limited refinement to the intersected sub-region.

## Comparison vs source CHT baseline

| Metric | source CHT (test_step_stl_cadgrade) | case_028 B74 | Δ |
|---|---|---|---|
| nCells (post-sHM) | 89,745 | 89,784 | +39 (+0.04%) |
| Mesh quality | sHM PASS-no-errors | sHM PASS-no-errors | identical class |
| Number of patches | 1 (apu merged) + 1 (bg_walls) = 2 | 29 (per_solid) + 6 (block split) = 35 | +33 ✓ semantics preserved |
| Geometry input | 1 × 503 MB merged STL | 29 × per_solid STLs (560 MB total) | per-component |
| sHM runtime | (unknown, source baseline) | 41.52 s | fast |
| checkMesh | PASS | PASS Mesh OK | identical |

case_028 matches source baseline cell count + quality while gaining 33 additional named patches that preserve component semantics — directly addresses V94 face-zone-loss family lesson.

## Next action

Run simpleFoam (kOmegaSST RAS, 3000 iter cap, residual convergence target 1e-4 on U/p/k/omega). Monitor mass flow at inlet vs outlet (Δṁ < 1% target) + 3 velocity probes inside bay.
