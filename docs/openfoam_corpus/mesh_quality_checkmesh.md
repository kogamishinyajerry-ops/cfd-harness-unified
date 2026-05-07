# Mesh quality and checkMesh interpretation

`checkMesh` reports geometric mesh quality. Engineers should run it
after every mesh build (gmsh, snappyHexMesh, blockMesh) and before
solving.

## Critical thresholds

A mesh is broadly considered solver-ready when:

- **Max non-orthogonality** ≤ 70° (warning at 65°). Above this, the
  diffusion term needs explicit non-orthogonal correctors (`nNonOrthogonalCorrectors`
  in `fvSolution`).
- **Max skewness** ≤ 4.0 (warning at 2.0). High skewness causes
  pressure-velocity decoupling and stability issues.
- **Min cell volume** > 0. Negative volumes mean the mesh is invalid
  and must be rebuilt.
- **Max aspect ratio** ≤ 100 for general flows; up to 1000 acceptable
  in boundary-layer prism stacks.

## Common failure patterns

### Negative volumes

Cause: snappyHexMesh failed to snap cleanly to the surface, leaving
inverted cells. Mitigation: increase `nFeatureSnapIter`, decrease
`relaxationFactor` in snapControls, or improve surface mesh quality
upstream.

### High skewness near boundaries

Cause: surface refinement level too aggressive, mesh transition too
abrupt. Mitigation: add intermediate refinement levels, or use
`refinementSurfaces` with a region transition.

### Non-orthogonal cells in prism layers

Cause: addLayers stage shrunk too aggressively against curved
surfaces. Mitigation: reduce `expansionRatio` (try 1.1-1.2),
increase `nLayerIter`, or accept fewer `finalLayerThickness`.

## Audit policy

Failed checkMesh is a `warning`-severity issue per N5.2 enumerator
(`mesh_checkmesh_failed`). The case will run but results may be
unreliable; engineer should review the report before trusting
solver output.
