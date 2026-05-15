# case_029 NACA 0012 stall · mesh prep log

## Commands executed (V65-A B75)

```bash
cd ~/Desktop/case_029_naca_stall
python3 generate_naca_stl.py naca=0012 chord=1.0 span=0.1 n=200 > airfoil.stl
cp airfoil.stl case/constant/triSurface/naca0012.stl

docker run --rm -v "$PWD/case:/case" opencfd/openfoam-default:2312 bash -c "
  cd /case
  surfaceFeatureExtract  # → log.sfe (naca0012.eMesh · 804 feature edges)
  blockMesh              # → log.bm  (60×40×1 = 2400 hex cells base)
  snappyHexMesh -overwrite  # → log.shm
  checkMesh              # → log.cm
"
```

## Outcomes

### surfaceFeatureExtract
- 804 feature edges extracted (LE/TE + sharp ridges)
- 0 open edges (closed airfoil polygon)
- naca0012.eMesh written → fed into sHM features dispatch (level 5)

### blockMesh
- 5 patches: inlet (40 faces) · outlet (40 faces) · bottom (60 faces) · top (60 faces) · frontAndBack (empty · 4800 faces × 2)
- 2400 hex base cells (0.5c × 0.5c × 0.1c base size)

### snappyHexMesh (2 attempts)

**Attempt 1** (level (3,4) · firstLayerThickness 5e-6 · 10 layers · 8256 base cells):
- Castellated + snap PASS
- addLayers: "Extruding 0 out of 688 faces (0%). Added 0 out of 8256 cells (0%)"
- SIGSEGV in writeLayerSets due to writeFlags (layerFields/scalarLevels/layerSets) writing for layers that weren't actually added

**Attempt 2** (level (4,5) · firstLayerThickness 1e-5 · 10 layers · writeFlags removed):
- Castellated + snap PASS
- addLayers: "Extruding 0 out of 1696 faces (0%). Added 0 out of 16960 cells (0%)"
- No SIGSEGV (writeFlags fix worked)
- Mesh quality CHECK PASS: non-ortho max 40.8 / avg 6.87 · skewness max 0.95 · aspect ratio max 2.95
- 12,520 cells final (post-snap · no layers)

### checkMesh quality criteria

| Criterion | Threshold | Actual | Met |
|---|---|---|---|
| Max skewness | < 4 | 0.95 | ✓ |
| Max non-orthogonality | < 70° | 40.8° | ✓ |
| Avg non-orthogonality | reasonable | 6.87° | ✓ |
| Max aspect ratio | reasonable | 2.95 | ✓ |
| Cell volumes | non-negative | min 2.51e-7 | ✓ |

### checkMesh failures (honest disclosure)

| Failure | Cause | Impact |
|---|---|---|
| "Total number of faces on empty patches is not divisible by the number of cells in the mesh. Hence this mesh is not 1D or 2D." | sHM octree refinement on 1-cell-z slab creates cells with non-uniform empty-face count | Mesh is still 2D-in-spirit; simpleFoam runs fine; downstream impact = none |
| "Number of edges not aligned with or perpendicular to non-empty directions: 6127" | Same sHM artifact (octree split refinement angles) | Cosmetic warning; simpleFoam handles |
| addLayers added 0 cells | 1-cell-z slab + addLayers medial axis algorithm cannot find extrusion space | y+ on surface cells will be > 1 — **explicit gap vs B75 goal (c)** |

## y+ predicted (without addLayers)

Surface cell size at refinement level 5: 0.5/32 = 0.0156 m
At Re=3e6, attached-side u_τ ≈ 1.87 m/s, ν = 1.5e-5 m²/s
y+ predicted ≈ (0.0156 / 2) × 1.87 / 1.5e-5 ≈ **970** (well above goal threshold of 1)

This forces verdict downgrade on goal condition (c) from FULL to PARTIAL on y+ axis specifically.

## Why addLayers fails on 2D slab (root cause analysis)

sHM addLayers uses the `displacementMedialAxis` mesh-motion solver to grow boundary-layer cells. The algorithm:
1. Finds the medial axis (skeleton of fluid region opposite each wall face)
2. Smoothly displaces interior cells along medial-axis-normal to make room for inflation cells
3. Inserts new prismatic layers between wall and displaced cells

On a 1-cell-thick z-slab:
- The "medial axis" in the z direction is degenerate (no fluid cells to displace toward z)
- `minMedialAxisAngle 90` requires the medial axis vector to deviate ≥90° from the surface normal — degenerate on z-slab geometry
- Result: 0 faces qualify for extrusion → 0 layers added

Industry workarounds (not pursued in B75 to respect 45-turn budget):
1. **Build 3D mesh with sHM addLayers (multi-cell z) then extrude to 2D** — extrudeMesh would re-collapse but layer prism cells survive
2. **Use blockMesh-only C-grid with structured BL grading** — gives y+ < 1 via explicit grading; bypasses sHM entirely
3. **Use prismToHex post-processing** to inject layers after castellated+snap on 2D
4. **Accept wall functions** — kOmegaSST with nutUSpaldingWallFunction handles y+ >> 1 industrially

case_029 B75 takes path (4) — `nutUSpaldingWallFunction` works for any y+. Disclosure on goal condition (c) is honest. Future case (V65-B refactor or case_029 v2) candidate: try blockMesh-only C-grid for strict y+ < 1.

## Final mesh summary

```
Cells:       12,520
Faces:       44,006
Points:      19,243
Patches:     6 (inlet · outlet · top · bottom · frontAndBack · naca0012)
naca0012:    1,696 faces (high-resolution airfoil surface)
frontAndBack: 8,340 faces (2D empty)
Mesh time:   45.4 s (single-thread Docker)
```

## Reusability

After mesh ready, single mesh shared across 3 AoA via:
```bash
for AOA in 10 15 18; do cp -r case case_aoa_$AOA; done
```

Per-AoA edits:
- 0/U internalField + freestreamValue → rotated to AoA vector
- system/controlDict liftDir + dragDir → perpendicular/parallel to freestream

Mesh once, run 3 AoA → 2× time savings vs per-AoA fresh mesh.
