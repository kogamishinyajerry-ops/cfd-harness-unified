# case_021 · Mesh Prep Log

**Date**: 2026-05-15
**Container**: opencfd/openfoam-default:2312 (fresh `--rm` invocations)
**Sandbox**: `/Users/Zhuanz/Desktop/case_021_nasa_tmr_flat_plate/case`

## blockMesh result

- **nCells**: 209,825 hexahedra ✓ (matches NASA TMR fine grid 545×385 = 209,825)
- **nPoints**: 421,512
- **nFaces**: 840,230 (418,720 internal + 419,650 frontAndBack empty + 1860 named patches)
- **Bounding box**: (0, 0, 0) to (2, 0.3, 0.01) m ✓
- **Cell size**:
  - i (x): 0.938 mm (LE finest) → 9.38 mm (TE coarsest) · simpleGrading 10
  - j (y): **5.62e-6 m** (wall · y+ ≈ 1 target) → 5.31e-3 m (top) · simpleGrading 944
  - k (z): 0.01 m (single wedge layer)

**Wall-normal first-cell δy_first = 5.62e-6 m** vs design target 5.0e-6 m — within 12% (acceptable; computed expansion ratio 944 vs spec 945 also matches within rounding).

## checkMesh result

| Check | Status |
|---|---|
| Boundary definition | OK |
| Cell to face addressing | OK |
| Point usage | OK |
| Upper triangular ordering | OK |
| Face vertices | OK |
| Number of regions | 1 (OK) |
| Patch topology (inlet/outlet/plate/top/frontAndBack) | all OK (non-closed singly connected) |
| Geometric directions | 2 (correct for 2D wedge) |
| Boundary openness | OK (1e-14 residual · floating point noise) |
| Min face area | 5.27e-9 m² (TE wall) · OK |
| Max face area | 9.38e-5 m² · OK |
| Min cell volume | 5.27e-11 m³ · OK |
| Max cell volume | 4.98e-7 m³ · OK |
| Mesh non-orthogonality | Max 0 / Avg 0 ✓ (perfect Cartesian) |
| Max skewness | 3.0e-13 ✓ (floating point noise) |
| Coupled point location match | OK |
| **Max aspect ratio** | **1669.45 on 1815 cells** |

**Verdict**: checkMesh PASS-with-1-flag

### Aspect ratio flag analysis

- Max AR 1669 occurs at trailing-edge near-wall first-cell: AR ≈ δx_last/δy_first = 9.38e-3 / 5.62e-6 = 1669 ✓ (matches computed value exactly)
- 1815 cells = ~1 plate length of TE near-wall cells (consistent with expected near-wall TE band)
- **This is the canonical NASA TMR grid signature** for y+≈1 high-Re ZPG TBL. NASA's own reference grids exhibit AR > 5000 at TE first-cell. Long-axis of stretched cells is aligned with primary flow direction (streamwise), so the AR does NOT degrade scheme accuracy because there is no significant transverse gradient sampled by stretched cells.
- This pattern is **not a quality issue** but a physically-correct y+-1 resolution decision. Same pattern present in B54 case_004 mesh gen v2 (checkMesh PASS-with-1-flag per ARC-GOAL Tier 1 entry).

## Re-run reproducibility

```bash
docker run --rm -v /Users/Zhuanz/Desktop/case_021_nasa_tmr_flat_plate/case:/case \
  opencfd/openfoam-default:2312 \
  bash -c 'cd /case && blockMesh && checkMesh'
```

## Artifacts

- `system/blockMeshDict` (geometry + grading spec)
- `BLOCKMESH_LOG.txt` (full blockMesh stdout · 83 lines)
- `CHECKMESH_LOG.txt` (full checkMesh stdout · 99 lines)
