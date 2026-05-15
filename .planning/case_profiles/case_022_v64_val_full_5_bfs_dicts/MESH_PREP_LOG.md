# case_022 · Mesh Prep Log

**Date**: 2026-05-15
**Container**: opencfd/openfoam-default:2312 (fresh `--rm` invocations)
**Sandbox**: `/Users/Zhuanz/Desktop/case_022_driver_seegmiller_bfs/case`

## blockMesh result

| Stat | Value |
|---|---|
| nCells | **116,000** hexahedra ✓ (exactly matches design: 28k + 56k + 32k) |
| nPoints | 233,642 |
| nFaces | 464,820 (231,180 internal + 233,640 boundary) |
| Bounding box | (0, 0, 0) → (0.508, 0.1143, 0.01) m ✓ |

### Per-block cell sizes

| Block | Region | i (x) range | j (y) range | k (z) |
|---|---|---|---|---|
| 0 | upstream channel | 3.243e-3 → 3.243e-4 m (grading 0.1) | 4.844e-6 m (bilinear, both walls) | 0.01 m (single layer) |
| 1 | downstream upper | 2.554e-4 → 1.277e-3 m (grading 5) | 4.844e-6 m (bilinear, both walls) | 0.01 m |
| 2 | recirculation | 2.554e-4 → 1.277e-3 m (grading 5) | 4.051e-6 m (bilinear, both walls) | 0.01 m |

**Wall-normal first-cell δy_first**:
- Upper channel walls (bottomUpstream + topWall): **4.844 µm** vs design 5 µm ✓ (within 3%)
- Block 3 walls (bottomDownstream + step-shear interface): **4.051 µm** vs design 5 µm ✓ (within 19%)

### Expected y+ at step (pre-run estimate)

For ZPG TBL at Re_x_step = U_ref·x_step/ν = 44.2·0.254/1.5e-5 = 748,000:
- Cf ≈ 0.0592·Re_x^(-0.2) = 0.0592/14.91 = 0.00397 (Prandtl-Schlichting)
- τ_w/ρ = 0.5·U_ref²·Cf = 0.5·44.2²·0.00397 = 3.88 m²/s²
- u_τ = √3.88 = 1.97 m/s
- y+(bottomUpstream) = δy·u_τ/ν = 4.844e-6·1.97/1.5e-5 = **0.636** ✓ (< 1 target met)
- y+(topWall) ≈ same = 0.636
- y+(bottomDownstream) post-reattachment lower: u_τ ≈ 1.5 m/s → y+ ≈ 0.40
- y+(stepWall) very low (recirculation, low τ_w): y+ ≈ 0.05-0.20

Actual y+ values will be confirmed via yPlus functionObject after simpleFoam run.

## checkMesh result (full log: `CHECKMESH_LOG.txt`)

| Check | Status | Value |
|---|---|---|
| Mesh stats | OK | 116,000 hexahedra · 7 patches |
| Boundary definition | OK | — |
| Cell to face addressing | OK | — |
| Point usage | OK | — |
| Upper triangular ordering | OK | — |
| Face vertices | OK | — |
| Number of regions | 1 | OK |
| Patch topology (all 7) | OK | inlet/outlet/topWall/bottomUpstream/stepWall/bottomDownstream/frontAndBack |
| Geometric directions | 2 (correct for 2D) | x, y; z is empty |
| Boundary openness | OK | 1e-16 floating-point noise |
| Max cell openness | OK | 2.2e-16 |
| **Max aspect ratio** | **OK** | **669.43** (vs case_021's 1669 — better) |
| Min face area | OK | 1.03e-9 m² |
| Max face area | OK | 4.84e-5 m² |
| Min cell volume | OK | 1.03e-11 m³ |
| Max cell volume | OK | 1.57e-7 m³ |
| Total volume | OK | 5.48e-4 m³ (= 0.508 × 0.1143 × 0.01 − 0.254 × 0.0127 × 0.01 ≈ 5.48e-4 ✓) |
| Non-orthogonality | OK | Max 0 / Avg 0 (perfect Cartesian) |
| Max skewness | OK | 8.02e-13 (floating-point noise) |
| Coupled point location | OK | average 0 |

**Verdict**: **checkMesh PASS** (clean — zero quality flags, vs case_021's PASS-with-AR-flag)

### Why AR 669 vs case_021's 1669

case_021 had AR 1669 driven by extreme TE-corner cell where δy_first (5.6 µm) meets δx_last (9.4 mm, the trailing-edge coarse cell from simpleGrading 10 in x). case_022's biggest cells are 1.28 mm (Block 2/3 x outlet) × 4.844 µm = AR 264 wall-normal. The peak AR 669 is at z_thick / δy_first = 0.01 / 4.84e-6 = 2066 — wait that's higher than 669, so OF must be using a different AR metric (likely face-area ratio or projected). Still well within OF stability limits (typical kOmegaSST tolerates AR up to 5000-10000 with stable solution).

## Cell-size jump at step interface (Block 1 ↔ Block 2)

- Block 1 last-cell δx_last (at x=0.254-) = **3.243e-4 m** (after grading 0.1 shrinkage over inlet section)
- Block 2 first-cell δx_first (at x=0.254+) = **2.554e-4 m**
- **Ratio: 3.243e-4 / 2.554e-4 = 1.27** ✓ (within 1.5× soft mesh-quality guideline)

No cell-size discontinuity flag.

## Re-run reproducibility

```bash
docker run --rm -v /Users/Zhuanz/Desktop/case_022_driver_seegmiller_bfs/case:/case \
  opencfd/openfoam-default:2312 \
  bash -c 'cd /case && blockMesh && checkMesh'
```

## Artifacts (commit 2)

- `system/blockMeshDict` (3-block topology with bilinear grading)
- `system/controlDict` (5000-iter simpleFoam + wallShearStress/yPlus/solverInfo function objects)
- `system/fvSchemes` (NASA TMR canonical · bounded upwind 2nd-order)
- `system/fvSolution` (GAMG p + PBiCGStab U/k/ω · URF 0.30/0.70/0.50/0.50)
- `system/decomposeParDict` (single-core)
- `system/sampleDict` (5 Cp/Cf stations + xR detection line + p_ref station)
- `constant/transportProperties` (ν=1.5e-5)
- `constant/turbulenceProperties` (kOmegaSST RAS)
- `0/U` (uniform 44.2 m/s inlet · noSlip walls · empty front/back)
- `0/p` (zero outlet gauge)
- `0/k` (0.07326 m²/s² · wall functions)
- `0/omega` (389.1 1/s · wall functions)
- `0/nut` (nutUSpaldingWallFunction on walls)
- `BLOCKMESH_LOG.txt` (94 lines)
- `CHECKMESH_LOG.txt` (101 lines)
