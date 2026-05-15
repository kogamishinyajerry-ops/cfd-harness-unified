# case_028 v2 · Mesh Prep Log

**Date**: 2026-05-16 (V65-A B77 dispatch · no-slip lateral refactor)
**Container**: opencfd/openfoam-default:2312 (fresh `--rm` invocations)
**Sandbox**: `/Users/Zhuanz/Desktop/case_028_apu_bay_ventilation_v2/case`
**Source geometry**: `~/Desktop/apu-bay-ventilation-cht/work/stl_repair/per_solid/` (29 STLs · 560 MB · READ-ONLY · identical to v1)

## v1 → v2 diff (mesh-side)

- blockMeshDict: 4 lateral patches (`bay_top` / `bay_bottom` / `bay_side_p` / `bay_side_n`) `type patch;` → `type wall;` (required for nutkWallFunction / kqRWallFunction / omegaWallFunction high-Re wall treatment)
- inlet / outlet remain `type patch;`
- snappyHexMeshDict, transportProperties, turbulenceProperties: unchanged from v1
- 29 STL components: identical (copied from v1 sandbox `constant/triSurface/`)

## blockMesh result

- **nCells**: 42,000 hexahedra ✓ (identical to v1)
- **nPoints**: 45,756 (identical to v1)
- **nFaces**: 129,650 (identical to v1)
- **Bounding box**: (63.5, -1.0, -1.5) to (67.5, 2.5, 1.5) m ✓
- **Patch split** (post v2 type changes):
  - inlet (1050 faces · -x face · `patch`)
  - outlet (1050 faces · +x face · `patch`)
  - bay_top (1200 faces · +y face · **`wall`**)
  - bay_bottom (1200 faces · -y face · **`wall`**)
  - bay_side_p (1400 faces · +z face · **`wall`**)
  - bay_side_n (1400 faces · -z face · **`wall`**)

**Verdict**: blockMesh PASS · identical cell layout · 4 lateral patches re-typed as `wall`

## snappyHexMesh result

**Runtime**: **31.07 s** (M-class Mac · single-thread sHM) — vs v1 41.52 s (slightly faster due to local machine load · semantically identical mesh)

**Mesh state at end-of-snap**:
- nCells: **89,784** (identical to v1 · patch type does not affect castellation logic)
- nFaces: 290,339 (identical to v1)
- nPoints: 113,237 (identical to v1)
- Cells per refinement level:
  - level 0: 33,362 (identical to v1)
  - level 1: 56,422 (identical to v1)

**Quality at end-of-snap** (9 checks · all PASS · identical to v1):
- non-orthogonality > 65° : 0 faces
- face pyramid volume < 1e-13: 0
- face-decomposition tet quality < 1e-30: 0
- concavity > 80°: 0
- skewness > 4 (internal) / > 20 (boundary): 0
- interpolation weights < 0.05: 0
- volume ratio neighbours < 0.01: 0
- face twist < 0.02: 0
- determinant < 0.001: 0

**Mesh log**: "Finished meshing without any errors"

**Verdict**: sHM PASS (no errors · no quality flags · 1-pass castellation + snap)

## checkMesh result

| Check | Status (identical to v1) |
|---|---|
| Boundary definition | OK |
| Patch topology (35 patches: 29 STL + 6 block; 4 lateral now `wall`) | all OK |
| Max aspect ratio | **9.15** ✓ |
| Max non-orthogonality | **61.24** (avg 10.53) ✓ |
| Max skewness | **3.58** ✓ |
| Max cell openness | 3.9e-16 (≈0) ✓ |
| Total domain volume | 40.45 m³ (96.3% of bbox · 3.7% obstacle volume) |
| Coupled point location match | OK |

**Verdict**: checkMesh **Mesh OK** (identical class to v1 · no defects)

## Comparison vs v1 baseline

| Metric | v1 (B74) | v2 (B77) | Δ |
|---|---|---|---|
| nCells (post-sHM) | 89,784 | 89,784 | **identical** ✓ |
| Mesh quality | Mesh OK | Mesh OK | identical |
| Number of patches | 35 (29 STL + 6 block) | 35 (29 STL + 6 block · 4 of which now `wall`) | type changes only |
| sHM runtime | 41.52 s | 31.07 s | -25% (machine load variance) |
| checkMesh max non-ortho | 61.24 | 61.24 | bit-identical |
| Geometry input | 29 per_solid STLs (560 MB) | identical (READ-ONLY reuse) | unchanged |

case_028 v2 mesh is **bit-identical** to v1 mesh in cell layout · only patch type metadata differs (4 lateral `patch` → `wall`). This confirms patch type is a runtime concept consumed by the solver (BC dictionary type-checking), not a mesh-generation concept.

## Next action

Run simpleFoam v2 (kOmegaSST RAS, 3000 iter cap, residual convergence target 1e-4 on U/p/k/omega). Expected: ~2–3× more iterations vs v1 due to noSlip wall friction adding boundary-layer development on 4 lateral walls. Monitor mass flow at inlet vs outlet (Δṁ < 1% target · same volumetric rate expected since inlet topology unchanged) + 3 velocity probes inside bay (expect probe 0 + 2 marginally different from v1; bay interior likely still stagnant pending STL-driven inlet/outlet refactor).
