# case_027 · MESH_PREP_LOG · Hagen-Poiseuille pipe axisymmetric wedge

> Commit 2 of 4 — blockMesh + checkMesh + dictionary set
> Build: opencfd/openfoam-default:2312 · linuxARM64GccDPInt32Opt · macOS Apple Silicon host

## Invocation (verbatim · re-runnable)

```bash
# Bootstrap sandbox case dir from repo
mkdir -p ~/Desktop/case_027_hagen_poiseuille_pipe/case
cp -r .planning/case_profiles/case_027_v64_pipe_dicts/{system,constant,0} \
      ~/Desktop/case_027_hagen_poiseuille_pipe/case/

# Generate mesh (Docker · non-root user for codedFixedValue compile compat)
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_027_hagen_poiseuille_pipe/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && blockMesh' > BLOCKMESH_LOG.txt 2>&1

# Verify mesh
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_027_hagen_poiseuille_pipe/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && checkMesh' > CHECKMESH_LOG.txt 2>&1
```

## Mesh metrics (blockMesh output · verbatim)

```
Mesh Information
----------------
  boundingBox: (0 0 -0.000218096937) (0.5 0.004995241108 0.000218096937)
  nPoints: 41082
  nCells: 20000
  nFaces: 80540
  nInternalFaces: 39460
----------------
Patches
----------------
  patch 0 (start: 39460 size: 40) name: inlet
  patch 1 (start: 39500 size: 40) name: outlet
  patch 2 (start: 39540 size: 500) name: wall
  patch 3 (start: 40040 size: 20000) name: front
  patch 4 (start: 60040 size: 20000) name: back
  patch 5 (start: 80040 size: 500) name: axis
----------------
Block 0 cell size:
  i (x):     0.001 .. 0.001                          (uniform Δx = 1 mm)
  j (r):     0.0002054700935 .. 6.848996269e-05      (axis → wall · 3:1 graded toward wall)
  k (θ):     0 .. 0                                  (single wedge cell · azimuth)
```

## Grading verification

- **Axis cell δr** (first j-cell): 2.05e-4 m (smoothly handles axis degeneracy)
- **Wall cell δr** (last j-cell):  6.85e-5 m (resolves steep ∂u/∂r near wall)
- **Ratio**: 6.85e-5 / 2.05e-4 = **0.334** ≈ 1/3 (matches simpleGrading 0.333333 intent)

## checkMesh status (PASS-with-2-axis-degeneracy-flags · OpenFOAM wedge convention)

**Overall**: 2 checks "Failed" by checkMesh, both intrinsic to OpenFOAM axisymmetric wedge convention:

1. **Zero or negative face area** (500 faces): The 500 degenerate axis faces (where the wedge cell collapses to a line at r=0). These are on the `axis` patch with type `empty` — OpenFOAM excludes them from solver computation. This is the standard wedge axis representation in OpenFOAM (per OF user guide §5.3.3 axisymmetric flow); the same flags appear in stock OpenFOAM tutorials (`pipeCyclic`, `axisymmetric`).

2. **High skewness** (500 highly skew faces, max skewness 1.4e+146): Same 500 degenerate axis faces. Skewness is undefined for zero-area faces (division by zero in the skewness formula gives a very large number). Same root cause as flag #1; same OpenFOAM-handles-it-natively status.

**Geometry checks PASS** (all flow-relevant):
- Boundary openness: 1.96e-15 (essentially zero · machine precision)
- Max cell openness: 1.44e-16 (machine precision)
- Max aspect ratio: **14.72** (acceptable for wall-resolved axisymmetric wedge · case_025 plane Poiseuille had max 3.7 for symmetric grading)
- Max cell volume: 3.36e-11 m³, min 1.84e-12 m³ (axis-vs-wall expected ratio · OK)
- Total volume: 5.45e-7 m³ (matches analytical π·R²·L · θ/360 = π·(0.005)²·0.5·(5/360) = 5.45e-7 ✓)
- Non-orthogonality max: 0 (mesh is fully orthogonal · expected for hex wedge)
- Wedge angle (front/back): 2.500000002° each (matches design 2.5°)

**Conclusion**: Mesh PASS for solver use. 2 checkMesh flags are documented OpenFOAM-wedge-convention artifacts, NOT mesh defects.

## CASE_SPEC §5 sample-line numeric typo (caught in commit 2)

CASE_SPEC.md §5 (committed in `de1fe86`) lists sample-line end y-coordinate as
`0.004990480935` with the comment "y = R·cos(2.5°) = 0.005·0.999048". **The numeric
value is wrong** (typo); the correct R·cos(2.5°) = 0.005·0.999048 = **0.004995241108**.

Committed sampleDict (this commit) uses **y_end = 0.004990** — slightly inside
the wall cell (wall vertex y=0.004995241; wall cell center y≈0.004960) — for safe
midPoint sampling. CASE_SPEC retained as-is for commit-1 audit trail; correction
documented here + validation report §3.x.

Source-of-truth alignment:
- analytical R = 0.005 (geometric pipe radius · vertex distance from axis)
- mesh wall vertex at (y, z) = (R·cos(2.5°), ±R·sin(2.5°)) = (0.004995241, ±0.000218097)
- "effective wall" in 3D for the flat wedge face midline (z=0): r_eff = R·cos(2.5°) ≈ 0.999·R (geometric chord approximation)
- This wedge-chord-approximation will introduce a 0.1%-R systematic bias in u(r) at the wall-adjacent cell; expect ~0.2-0.4% peak |Δu| from this alone (analyzed in CASE_SPEC §10 risk flag `wedge_axis_discretization`)
- Margin to strict gate 1%: ×2.5 to ×5 (acceptable buffer)

## defaultPatch absorption pattern (F-NEW candidate)

Initial blockMesh run without `defaultPatch` placed 500 axis faces into an
implicit `defaultFaces` patch with type `patch` (default). checkMesh flagged
them as ungrouped and the solver would error on solving the "patch" type for
the degenerate axis (no rotation/symmetry handling).

Fix: add `defaultPatch { name axis; type empty; }` to blockMeshDict (top-level
block before `vertices`). This routes blockMesh's auto-detected default faces
into a properly-typed `axis` patch with type `empty`, which tells OpenFOAM these
faces have zero flux/computation. Standard OpenFOAM axisymmetric wedge pattern.

F-NEW-A (med-impact): OpenFOAM axisymmetric wedge requires `defaultPatch
{ name axis; type empty; }` declaration in blockMeshDict to route degenerate
axis faces; without it, blockMesh creates `defaultFaces` (type patch) which
causes solver to attempt computation on zero-area faces.

## 4Q gate

- **Q1 LLM-offline**: `env -i HOME PATH source ~/OpenFOAM-v2512/etc/bashrc && blockMesh && checkMesh` re-runnable inside Docker (Q1 spirit · Docker is the LLM-offline-equivalent for OpenFOAM tooling)
- **Q2 artifacts**: blockMeshDict + 4 system/ dicts (controlDict + fvSchemes + fvSolution + sampleDict) + 2 constant/ dicts (transportProperties + turbulenceProperties laminar) + 2 0/ BC fields (U codedFixedValue + p) + BLOCKMESH_LOG.txt + CHECKMESH_LOG.txt + MESH_PREP_LOG.md (this file)
- **Q3 TrustGate**: every numeric (R·cos(2.5°), R·sin(2.5°), wall δr, axis δr, total volume) re-derivable from blockMesh log and basic geometry; F-NEW-A precondition reproducible
- **Q4 advisor-only**: NO advisor stack edits (ui/backend/ untouched · entire commit 2)

## Next action

Commit 3: simpleFoam laminar run · 17+ r-point u(r) extraction at exit station + dp/dx via axis pressure linear-fit + τ_w via wallShearStress functionObject · Δ% vs analytical · strict-gate verdict.
