# case_028 v3 · Mesh Prep Log

**Date**: 2026-05-16 · B78 (V65-A autonomous mode)
**OpenFOAM image**: opencfd/openfoam-default:2312

## Steps

| # | Step | Result |
|---|---|---|
| 1 | `blockMesh` | PASS · 42,000 hex base cells · 6 walls (end_minus_x / end_plus_x / 4 lateral) |
| 2 | `snappyHexMesh -overwrite` | PASS · `Finished meshing without any errors` · 37.6 s · 110,748 final cells (vs 89,784 v1/v2 baseline) |
| 3 | `checkMesh` | **Mesh OK** · max non-orthogonality 64.3 (avg 11.2) · max skewness 3.74 · max aspect ratio 8.80 |

## Cell count breakdown (sHM final)

| Refinement level | Cells |
|---|---|
| 0 (bg-block) | 33,114 |
| 1 (intake_duct/vent_door · was 0-1 in v1/v2) | 55,905 |
| 2 (intake/vent fine refinement · NEW in v3 for patch-quality) | 21,729 |
| **Total** | **110,748** |

Cell count up 24% vs v1/v2 (89.8k) because intake_duct + vent_door bumped from `level (0 1)` to `level (1 2)` to ensure patch-quality on now-active inflow/outflow surfaces.

## Patches in final mesh

| Patch | Type | nFaces |
|---|---|---|
| end_minus_x | wall | 1050 |
| end_plus_x | wall | 1050 |
| bay_top | wall | 1200 |
| bay_bottom | wall | 1200 |
| bay_side_p | wall | 1400 |
| bay_side_n | wall | 1400 |
| **intake_duct** | **patch** | **7104** (effective surface area 4.6975 m² — confirmed via solver `Area` field) |
| **vent_door** | **patch** | **660** |
| (+ 27 STL walls: Outer_Surf, Inner_Surf, ..., beam_3) | wall | varies |

## Empirical finding (during B78 execution)

**intake_duct STL is a 3D ducted surface, not a 2D aperture face.** Effective surface area = 4.6975 m² (per surfaceFieldValue Area output), vs initial bbox-projection estimate of ~1 m². Mass flow target recalibration: U_in 1.5 m/s → 0.3 m/s to land in SAE AIR1168/4 0.5-2 kg/s range.

This is a B78 empirical engineering payoff: **for 3D STL ducted geometries, surface area should be measured from sHM patch output, not estimated from bbox face projection**. Candidate V107 promotion if pattern surfaces on 2nd 3D-ducted STL case.

## Reproducibility

```bash
cd ~/Desktop/case_028_apu_bay_ventilation/case_v3
docker run --rm -v $(pwd):/case opencfd/openfoam-default:2312 bash -c "cd /case && blockMesh && snappyHexMesh -overwrite && checkMesh"
```

Expected: blockMesh 42k hex · sHM 110,748 cells · checkMesh `Mesh OK`.
