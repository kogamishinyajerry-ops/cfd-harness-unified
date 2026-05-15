# case_024 · Mesh Prep Log

**Date**: 2026-05-15
**Container**: opencfd/openfoam-default:2312 (fresh `--rm` invocation per case)
**Sandbox cases**: `~/Desktop/case_024_lid_driven_cavity/case_re{100,400,1000}/`
**Repo dicts**: `.planning/case_profiles/case_024_v64_val_full_4_cavity_dicts/`

## Mesh summary

| Metric | Value |
|---|---|
| Topology | 2D single-block hex (1m × 1m × 0.01m) |
| Cells | **16,641 hexahedra** (129 × 129 × 1) |
| Points | 33,800 |
| Faces | 66,822 (33,024 internal · 33,798 boundary) |
| Grading | `simpleGrading (1 1 1)` — uniform Cartesian |
| Cell size (Δx = Δy) | 7.7519e-3 m |
| Cell volume | 6.009254e-7 m³ (all cells, near-perfectly uniform) |
| Cell volume max/min ratio | 1.00000003 (machine-noise variation) |

## checkMesh — strict PASS on all 3 cases

All three sandbox case dirs use identical mesh (same blockMeshDict). checkMesh output is byte-identical across cases. Single representative summary:

| Check | Result |
|---|---|
| Boundary openness | (-3.26e-18, 3.26e-18, -2.40e-14) — OK |
| Max cell openness | 1.128e-16 — OK |
| **Max aspect ratio** | **1.000000013** — OK (perfect Cartesian) |
| **Mesh non-orthogonality** | **Max: 0, average: 0** — OK (axis-aligned) |
| Face pyramids | OK |
| **Max skewness** | **1.146e-13** — OK (machine zero) |
| Coupled point location match | average 0 — OK |
| **Final verdict** | **Mesh OK** (no flags) |

This is the cleanest possible checkMesh signature in OpenFOAM — perfect uniform Cartesian grid with zero non-orthogonality and machine-zero skewness. Any post-solve residual or Δ vs Ghia is attributable to discretization scheme + iteration count, NOT mesh quality.

## Patch layout

| Patch | Faces | BC type | OpenFOAM type |
|---|---|---|---|
| lid | 129 | moving wall (U=1,0,0) | `wall` |
| walls_fixed | 387 | no-slip (3 sides: bottom + left + right) | `wall` |
| frontAndBack | 33,282 | 2D constraint | `empty` |

walls_fixed combines 3 axis-aligned faces into one patch for simpler BC definition — 129 faces each × 3 sides = 387. This is a single OpenFOAM patch internally; the YAML manifest splits it logically.

## Re scaling delta

Per-case `constant/transportProperties` differs ONLY in `nu` value:

| Case | ν [m²/s] | Re_L = U_lid·L/ν |
|---|---:|---:|
| case_re100  | 0.01    |  100 |
| case_re400  | 0.0025  |  400 |
| case_re1000 | 0.001   | 1000 |

All other dicts (controlDict, fvSchemes, fvSolution, decomposeParDict, sampleDict, blockMeshDict, turbulenceProperties, 0/U, 0/p) are byte-identical across the 3 sandbox case dirs.

## Docker invocation pattern

```bash
SBOX=~/Desktop/case_024_lid_driven_cavity
for re in 100 400 1000; do
  docker run --rm -v $SBOX/case_re${re}:/case opencfd/openfoam-default:2312 \
    bash -c 'cd /case && blockMesh 2>&1 | tee log.blockMesh && \
             checkMesh 2>&1 | tee log.checkMesh'
done
```

Each run is fresh `--rm` (no container state shared) — Q1 LLM-offline reproducibility honored.

## Stderr note (transparency)

Initial Docker stderr emits `error while loading shared libraries: libblockMesh.so` once per invocation BEFORE the actual blockMesh runs successfully. This is an opencfd/openfoam-default:2312 image-init artifact — the entrypoint sources `/usr/lib/openfoam/openfoam2312/etc/bashrc` after the initial PATH probe, then the real blockMesh executes cleanly. Confirmed by: (a) 33,800 points emitted to `constant/polyMesh/`, (b) "Mesh OK" verdict from checkMesh, (c) byte-identical results across 3 independent container runs.

## Next action

Commit 3: run simpleFoam × 3 (Re=100/400/1000) · 10000 iter each (raised from 5000 to ensure laminar deep-convergence headroom) · postProcess sampleDict for u/v centerlines · extract 17-point Δ vs Ghia 1982 Tables I/II.
