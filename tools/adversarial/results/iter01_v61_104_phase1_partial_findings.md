# Adversarial Loop · iter01 revisited — DEC-V61-104 Phase 1 partial closure

**Date:** 2026-05-01
**Context:** DEC-V61-104 (interior obstacle topology) Phase 1 implemented. iter01 (thin-blade plenum) re-tested.

## Phase 1 implementation

Shipped:
- `ui/backend/services/meshing_gmsh/topology.py` (NEW) — `partition_surfaces_by_body` groups parametric surfaces by topological body via shared-edge connectivity, then sorts by bbox volume (outer = largest).
- `ui/backend/services/meshing_gmsh/gmsh_runner.py` — replaces single-loop `addVolume` with multi-loop `addVolume([outer_loop, -inner_loop, ...])` when partitioner finds >1 body.
- `ui/backend/tests/test_meshing_topology.py` — 9 tests (8 pure-logic with fake gmsh stub + 1 real-gmsh integration on cube-in-cube fixture).
- `ui/backend/tests/conftest.py` — new `cube_with_interior_obstacle_stl` fixture.

Single-body backward compat verified: 59/59 mesh + topology + geometry tests pass; LDC + naca0012 + cylinder cell counts unchanged.

## iter01 retest result

| metric | before V61-104 | after V61-104 Phase 1 |
|---|---|---|
| import (watertight, body_count) | 2 bodies | 2 bodies |
| gmsh classifySurfaces | 16 parametric surfaces | 16 (unchanged) |
| topology.partition_surfaces_by_body | (n/a, didn't exist) | **2 bodies** (6-surface outer + 10-surface inner blade) |
| gmsh.model.geo.addVolume | `[single_loop]` | `[outer_loop, -inner_loop]` ✓ |
| polyMesh patches | 4 (inlet, outlet, walls, blade) | 4 (unchanged) |
| **cell count** | **7159** | **7159 (no reduction)** |

## What worked

- Topology partitioner correctly identifies the 2 bodies (outer cavity + inner blade) for iter01 and cube-in-cube cases.
- Outer body is correctly identified as the larger-bbox component.
- `addVolume([outer_loop, -inner_loop])` runs without errors; gmsh accepts the call.
- The boundary file correctly emits the blade as a separate `patch` entry (294 faces).

## What didn't work — gmsh's geo-kernel hole subtraction

Empirical test (standalone gmsh, both cube-in-cube and iter01):

```
cube_in_cube  multi_body=False pgs=False: 5212 cells
cube_in_cube  multi_body=True  pgs=False: 5212 cells
cube_in_cube  multi_body=True  pgs=True : 5212 cells
```

**The cell count does not change between single-loop and multi-loop addVolume.** gmsh's geo-kernel `addVolume([outer, -inner])` accepts the negated inner loop syntax but does not actually subtract the inner volume during tetrahedralization. Cells are still generated INSIDE the inner body.

The `-loop` negation is documented as marking subsequent loops as holes (cf. the 2D `addPlaneSurface([outer_loop, inner_loop])` where the second loop is automatically a hole). For 3D `addVolume`, the behavior is not consistently triggered for arbitrary STL-imported surfaces.

Hypothesized root cause: the inner body's surface normals are outward-facing (standard STL convention), but gmsh's geo kernel needs them to be inward-facing for hole semantics. The `-loop` negation is supposed to flip orientation but doesn't reach into the per-surface normals.

## Phase 1 closure status

Phase 1 ships the **scaffolding** (topology partitioner + multi-loop addVolume call site + tests + cube-in-cube fixture). The actual hole subtraction does NOT work yet on iter01-class geometries.

**iter01 status reclassified**: stays at `physics_validation_required` in `tools/adversarial/cases/iter01/intent.json` until Phase 1.5 lands a working subtraction strategy. The smoke runner correctly skips it; the V61-104 work is genuinely partial, not silently broken.

## Recommended Phase 1.5 (separate PR)

Three approaches to investigate:

1. **OCC kernel boolean cut**: `gmsh.model.occ.cut(outer_volume, inner_volume)` — proper boolean operation, robust regardless of STL orientation. Requires re-architecting from geo to occ kernel after classifySurfaces (mixing the two kernels is fragile).

2. **Explicit surface-orientation reversal**: before `addSurfaceLoop` for the inner body, call `gmsh.model.geo.reverse([(2, t) for t in inner_body])` to flip the normals. Then the outer loop addVolume call's `-inner_loop` negation actually has the right semantics.

3. **classifySurfaces angle tuning**: the current 40° angle may collapse the blade's surfaces. A larger angle (90°+) might preserve the topological gap that allows clean addVolume separation.

Each approach is 1-3 days of investigation + tests. Best done in a fresh DEC-V61-104.1 follow-up commit.

## Test status (after Phase 1)

- 9/9 topology unit tests pass (8 pure-logic + 1 cube-in-cube real-gmsh)
- 59/59 mesh + topology + geometry tests pass (single-body backward compat preserved)
- 38/38 BC + solver tests pass
- 4 PASS · 2 SKIP · 0 FAIL adversarial smoke baseline (unchanged)

Phase 1 ships the right abstractions; Phase 1.5 makes them actually subtract.
