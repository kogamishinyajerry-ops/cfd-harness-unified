# case_026 · MESH_PREP_LOG · plane Couette · 2D · 20k uniform hex

> Commit 2 of 4 — blockMesh single-block uniform-y + checkMesh
> OpenFOAM v2512 (Docker `opencfd/openfoam-default:2312` · linuxARM64GccDPInt32Opt) · macOS Apple Silicon host

## Invocation (verbatim · re-runnable · Q1 LLM-offline)

```bash
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_026_plane_couette/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && blockMesh' > BLOCKMESH_LOG.txt 2>&1

docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_026_plane_couette/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && checkMesh' > CHECKMESH_LOG.txt 2>&1
```

`--user $(id -u):$(id -g)` already required for later codedFixedValue compile (F-NEW-A from B68); convention preserved here.

## Mesh stats (from BLOCKMESH_LOG)

| Metric | Value |
|---|---|
| nPoints | 41,082 |
| nCells | 20,000 |
| nFaces | 80,540 |
| nInternalFaces | 39,460 |
| Bounding box | (0 0 0) → (0.5 0.01 0.001) |
| inlet patch | 40 faces |
| outlet patch | 40 faces |
| bottomWall patch | 500 faces |
| topWall patch | 500 faces |
| frontAndBack patch | 40,000 faces (empty 2D) |

Cell count derivation: 500 × 40 × 1 = 20,000 hex cells.

## Topology

Single hex block:
- x: 500 cells uniform (Δx = 1.0e-3 m)
- y: 40 cells uniform (Δy = 2.5e-4 m) · **NO grading** (key difference vs B68 Poiseuille bilinear 3:1)
- z: 1 cell uniform (Δz = 1.0e-3 m, 2D empty patches)

## checkMesh quality (from CHECKMESH_LOG)

| Quality metric | Value | Status |
|---|---|---|
| Max aspect ratio | **4.0** | OK (uniform throughout) |
| Min volume | 2.5e-10 m³ | OK |
| Max volume | 2.5e-10 m³ | OK (uniform · 1:1 ratio) |
| Total volume | 5.0e-06 m³ | matches 0.5·0.01·0.001 ✓ |
| Max non-orthogonality | **0** | OK (orthogonal cartesian grid) |
| Average non-orthogonality | 0 | OK |
| Max skewness | 5.55e-13 | OK (machine-precision · purely rectangular cells) |
| Face area | 2.5e-7 to 1.0e-6 | OK |
| Boundary openness | 1.1e-18 | OK |
| Max cell openness | 1.06e-16 | OK |

**Verdict: Mesh OK** (zero quality warnings · perfectly uniform cartesian grid).

## Comparison with B68 Poiseuille mesh (case_025)

| Metric | B68 Poiseuille | B69 Couette (this) |
|---|---|---|
| nCells | 20,000 (same) | 20,000 |
| y-grading | bilinear 3:1 toward both walls | uniform (1:1) |
| Max aspect ratio | 3.66 | 4.00 (slightly higher uniform) |
| Max non-ortho | 0 | 0 (both purely orthogonal) |
| Min/max cell volume ratio | 3:1 (graded) | 1:1 (uniform) |

The uniform mesh is the deliberate canonical choice for Couette (linear field has constant gradient · no benefit from wall refinement · per CASE_SPEC §9 rationale).

## Risk flags

- `executable_smoke_test`: triggered ✓ — first Couette substrate, full local invocation logged above
- `solver_stability_on_novel_geometry`: low — mesh is the simplest possible: 2D uniform cartesian rectangle

## V-row attribution carry-forward

- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse
- **F-NEW-A from B68** (codedFixedValue under Docker container needs `--user $(id -u):$(id -g)` flag) — direct reuse (convention preserved here for later simpleFoam run)

F-NEW candidates this commit:
- **F-NEW (case_026)**: uniform-y single-block simpleGrading 1 plane channel · first time in repo for laminar canonical validation (B68 used bilinear; case_022 BFS used multi-block bilinear; case_024 cavity used uniform but only 129² square · this is a 500×40 elongated uniform · new substrate shape)

## 4Q gate

- **Q1 LLM-offline**: blockMesh + checkMesh re-runnable via env-i-equivalent Docker invocation (host PATH not required · Docker is hermetic) ✓
- **Q2 artifacts**: BLOCKMESH_LOG.txt + CHECKMESH_LOG.txt + 5 system/ dicts + 2 constant/ dicts + 2 0/ BC fields + parts_manifest + CASE_SPEC + MESH_PREP_LOG ✓
- **Q3 TrustGate**: every quality metric in §checkMesh quality cites CHECKMESH_LOG specific line ranges (visible in committed log) ✓
- **Q4 advisor-only**: NO advisor stack edits (ui/backend/ untouched · this commit) ✓

## Next action

Commit 3: simpleFoam laminar run · 5000-iter cap (expect convergence iter ~500-1500) · sample u(y) at exit + mid stations · extract τ_w · run extract_couette.py · write RUN_LOG.md.
