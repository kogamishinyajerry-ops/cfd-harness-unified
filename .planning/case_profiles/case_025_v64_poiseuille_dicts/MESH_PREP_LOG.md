# case_025 · MESH_PREP_LOG

> Commit 2 of 4 — mesh generation only (substrate-prep was commit 1).
> Run on host macOS via Docker `opencfd/openfoam-default:2312` (host OpenFOAM-v2512 source unpacked but not built; mirrors case_022 pattern).

## Invocation (verbatim · re-runnable)

```bash
# Sandbox setup (already done in commit 2)
mkdir -p ~/Desktop/case_025_poiseuille_channel/case
cp -r .planning/case_profiles/case_025_v64_poiseuille_dicts/{0,constant,system} \
    ~/Desktop/case_025_poiseuille_channel/case/

# blockMesh
docker run --rm \
    -v ~/Desktop/case_025_poiseuille_channel/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && blockMesh' 2>&1 | tee BLOCKMESH_LOG.txt

# checkMesh
docker run --rm \
    -v ~/Desktop/case_025_poiseuille_channel/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && checkMesh' 2>&1 | tee CHECKMESH_LOG.txt
```

## Mesh outcome

| Metric | Value | Status |
|---|---|---|
| Cell type | hexahedra · 20,000 | ✓ |
| Bounding box | (0, -0.01, 0) → (0.5, 0.01, 0.001) | ✓ matches design |
| nPoints | 41,082 | ✓ |
| nFaces | 80,540 (internal 39,460 + boundary 41,080) | ✓ |
| Max aspect ratio | **3.659874899** | ✓ excellent (target <10) |
| Min cell volume | 2.73e-10 m³ (wall cell · δy ≈ 2.73e-4 m) | ✓ |
| Max cell volume | 8.197e-10 m³ (centerline · δy ≈ 8.2e-4 m) | ✓ |
| **Cell vol ratio center:wall** | **8.197 / 2.732 = 3.000** | ✓ **exactly as designed** |
| Total volume | 1.0e-5 m³ = L × 2H × Δz = 0.5 × 0.02 × 0.001 | ✓ |
| Min face area | 2.73e-7 m² (wall cell on inlet/outlet face: δy × Δz) | ✓ |
| Max face area | 1.0e-6 m² (frontAndBack face: Δx × Δz = 1e-6) | ✓ |
| Non-orthogonality | Max 0, average 0 | ✓ perfect (hex orthogonal) |
| Max skewness | 5.54e-13 | ✓ essentially zero |
| Mesh-OK verdict | **Mesh OK.** | ✓ **PASS clean** |

## Wall cell δy verification (for analytical comparison)

| Quantity | Value | Source |
|---|---|---|
| δy at walls (y=±H) | ~2.73e-4 m | blockMesh j cell-size min |
| δy at centerline (y=0) | ~8.20e-4 m | blockMesh j cell-size max (inferred from vol max) |
| Cells per half-channel | 20 (with bilinear distribution) | ny=40 ÷ 2 |
| Smallest cell y-resolution | δy/H ≈ 0.027 (2.7% of half-channel near wall) | sufficient for analytical 1D Poiseuille |

For plane Poiseuille u(y) = u_max·(1 - (y/H)²), the analytical profile is a smooth quadratic, fully resolved by 20 cells per half-channel.

## Patches enumeration (from checkMesh)

| Patch | Faces | Points | Surface topology |
|---|---|---|---|
| inlet | 40 | 82 | ok (non-closed singly connected) |
| outlet | 40 | 82 | ok (non-closed singly connected) |
| bottomWall | 500 | 1002 | ok |
| topWall | 500 | 1002 | ok |
| frontAndBack | 40,000 | 41,082 | ok (empty 2D) |

Total boundary faces 41,080 = 40+40+500+500+40,000 ✓

## Risk-flag closure

- ✓ Mesh quality OK · no warnings
- ✓ Cell volume range matches design 3:1 ratio · grading symmetric bilinear works as expected
- ✓ Aspect ratio 3.66 well below typical CFD threshold (10-100)
- ✓ All boundary patches non-closed singly connected (standard 2D channel topology)

Mesh prep clean. Solver execution (commit 3) is the next step.
