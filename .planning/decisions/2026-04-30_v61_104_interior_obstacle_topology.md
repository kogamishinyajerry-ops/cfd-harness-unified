---
decision_id: DEC-V61-104
title: Interior-obstacle topology — gmsh runner builds outer surface loop + reversed-inner loops for cases with interior bodies
status: Phase 1 Implemented · Phase 1.5 Pending (2026-05-01 · Phase 1 ships scaffolding only — topology partitioner + multi-loop addVolume call site + TopologyPartitionError containment guard + 14/14 tests · Codex chain R8 APPROVE_WITH_COMMENTS → R9 APPROVE clean close · empirical finding: gmsh's geo-kernel addVolume hole subtraction does NOT actually subtract for STL-imported surfaces, iter01 still 7159 cells · Phase 1.5 follow-up to add OCC-kernel cut OR explicit surface-orientation reversal — see tools/adversarial/results/iter01_v61_104_phase1_partial_findings.md)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-30
authored_under: tools/adversarial/results/iter01_findings.md (defect 2b root cause + scope)
parent_decisions:
  - DEC-V61-103 (Imported-case BC mapper · this DEC builds on the named-patch foundation V61-103 establishes)
  - RETRO-V61-001 (risk-tier triggers · CFD geometry handling + mesh hot path = mandatory Codex review)
parent_artifacts:
  - tools/adversarial/results/iter01_findings.md (defect 2b · the 2 mm blade in the plenum was meshed as fluid, not as a hole)
  - ui/backend/services/meshing_gmsh/gmsh_runner.py:172-173 (current single-volume `addSurfaceLoop` + `addVolume` call)
  - ui/backend/services/geometry_ingest/health_check.py:104-105 (existing `body_count` reporting that already detects multi-body cases)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 50% (deeper architectural change — gmsh entity-to-body partitioning is non-trivial and the inner-vs-outer determination has multiple correct-looking heuristics that fail on degenerate cases · expect Codex round 2 minimum)
codex_tool_report_path: reports/codex_tool_reports/v61_104_phase1_r8_r9_chain.md (R8 APPROVE_WITH_COMMENTS 2 MED findings → R9 APPROVE clean close)
phase1_implementation_commits:
  - 30b659b (feat: topology partitioner + multi-body addVolume scaffolding · 9 tests)
  - bec98b2 (fix: close Codex R8 MED findings · TopologyPartitionError containment guard + real-gmsh addVolume coverage · 14/14 tests)
phase1_5_follow_up_scope:
  - approach_a: occ-kernel boolean cut (gmsh.model.occ.cut) — robust regardless of STL orientation; requires re-architecting from geo to occ kernel after classifySurfaces
  - approach_b: explicit surface-orientation reversal via gmsh.model.geo.reverse before addSurfaceLoop — lighter touch but fragile on degenerate normals
  - approach_c: classifySurfaces angle tuning (40° → 90°+) — may preserve topological gap that triggers clean addVolume separation
  - estimated_effort: 1-3 days investigation + tests per approach
notion_sync_status: synced 2026-04-30 (https://app.notion.com/p/353c68942bed81bb9a0bfcf29a07d09c) · re-sync pending for Phase 1 status update + R9 APPROVE

# Why now

Adversarial-loop iter01 generated a thin-blade-in-plenum geometry — a perfectly canonical engineering case (instrumented duct, valve seat, turbine blade, etc.). The current gmsh pipeline meshes the blade interior as fluid cells, which is physically wrong:

- Outer cavity surface → tetrahedralized as fluid ✓
- Blade interior surface → ALSO tetrahedralized as fluid ✗ (should be a hole)

The defect was masked in iter01 because gmsh's `classifySurfaces` at angle=40° collapsed the topology into a convex-hull-ish single volume. With the per-solid merge approach (which we explored and rejected for defect 2a), gmsh actually saw the topology and refused to mesh, returning a PLC error.

So defect 2b has TWO entangled problems:
1. The mesher doesn't recognize that some bodies are interior holes
2. The mesher silently produces wrong physics when (1) is unhandled

Without DEC-V61-104 fix, any imported CAD with an interior body (most realistic geometries: turbine + casing, valve + seat, instrument probe + duct) gets meshed wrong. The user wouldn't even know — the mesh count looks reasonable, the solver runs, the velocity field has plausible magnitudes, but the obstacle is missing.

# Scope

## Phase 1 · gmsh runner topology partitioning (1 week)

### 1.1 Body partitioning helper

`ui/backend/services/meshing_gmsh/topology.py` (NEW)

After `classifySurfaces+createGeometry`, the model has N parametric surfaces. Group them by topological body using bbox containment:

```python
def partition_surfaces_by_body(gmsh) -> list[list[int]]:
    """
    Returns [[outer_loop_tags], [inner_loop_1_tags], [inner_loop_2_tags], ...]
    where outer is identified by largest bbox + containing all others.
    """
    surfaces = gmsh.model.getEntities(dim=2)
    # Compute bbox per surface from mesh node coords (pre-generate(3))
    bboxes = {tag: surface_bbox(gmsh, tag) for _d, tag in surfaces}
    # Group by connectivity: surfaces sharing edges belong to same body
    bodies = connected_components_via_shared_edges(gmsh, surfaces)
    # Outer body: bbox contains all others
    outer = max(bodies, key=lambda b: bbox_volume(merged_bbox(b, bboxes)))
    inners = [b for b in bodies if b != outer]
    return [outer] + inners
```

### 1.2 Volume construction with holes

`ui/backend/services/meshing_gmsh/gmsh_runner.py` — replace `addSurfaceLoop+addVolume` block:

```python
# Replace the current single-loop path:
# surface_loop = gmsh.model.geo.addSurfaceLoop([s[1] for s in surfaces])
# gmsh.model.geo.addVolume([surface_loop])

bodies = partition_surfaces_by_body(gmsh)
outer_loop = gmsh.model.geo.addSurfaceLoop(bodies[0])
inner_loops = [gmsh.model.geo.addSurfaceLoop(body) for body in bodies[1:]]
# Negate the inner loops to mark them as holes
gmsh.model.geo.addVolume([outer_loop] + [-loop for loop in inner_loops])
```

### 1.3 Patch-name preservation across body boundary

The inner-body surfaces are still part of the boundary (no-slip walls on the obstacle). They get their own physical groups via the existing centroid-mapping path (DEC-V61-102's defect-2a fix). The new code only changes WHICH volume each surface bounds, not the surface→solid mapping.

### 1.4 `body_count` integration

`services/geometry_ingest/health_check.py` already reports `body_count`. When `body_count > 1`, the mesher SHOULD use the new path. Add a sanity check: if `body_count==1` but the new partitioner finds multiple bodies, log a warning (the two systems disagree → likely a topology classification edge case worth investigating).

## Phase 2 · Tests (4 days)

- 4 backend unit tests:
  - Single-body STL (existing `box_stl()`) → falls through to single-loop path, behavior unchanged
  - 2-body STL (cube with interior cube) → mesh has cells outside the inner cube but NOT inside it
  - 3-body STL (cube with 2 disjoint interior obstacles) → both holes correctly subtracted
  - Pathological: nested-deeply-nested obstacle (cube > inner cube > inner-inner cube) → outer fluid + middle solid + inner fluid? OR 2-level only? Document the choice.
- 1 cell-count regression: assert that 2-body case has fewer cells than 1-body case at same mesh density (validates obstacle volume actually subtracted).
- Adversarial iter05+: Codex generates "thin valve seat", "blockage in duct", "instrument probe in pipe" — realistic interior-obstacle topologies.

## Phase 3 · Adversarial validation (3 days)

Drive iter01 (Codex-generated thin-blade plenum) through the full pipeline. Expected:
- Import: ✅ (defect 1 fixed)
- Mesh: should succeed with ~6500 fluid cells (down from current 7159 if blade is correctly subtracted ≈ blade volume / cell volume ≈ 50-100 cells removed)
- Boundary: 4 named patches (inlet, outlet, walls, blade)
- Solve: icoFoam should produce flow that detours AROUND the blade (recirculation pocket downstream as Codex's intent.json predicted)

# Out of scope (deferred)

- Multi-region cases (porous + fluid + solid in same case) — needs separate `cellZones` + `regionProperties` handling. Document as DEC-V61-105+ scope.
- chtMultiRegionFoam-style conjugate heat transfer with body-fitted meshes — same.
- Self-intersecting geometries — gmsh has limited support; punt to user error.

# Risk areas (Codex review focus)

1. **Outer-body identification heuristic**: bbox containment can be wrong for non-convex outer bodies that don't fully bbox-contain interior bodies (e.g. C-shaped outer with interior obstacle near the opening). Need a connectivity-based fallback.

2. **Inner-loop orientation**: `-loop` negation in gmsh expects the loop's surface normals to be outward-facing on the inner body. If the STL has inconsistent windings on the obstacle, the negation produces wrong topology. Need an explicit normal-direction check.

3. **Backward compatibility**: `body_count==1` path MUST remain pixel-identical to current behavior. Existing 101 mesh tests + 11 geometry tests + LDC canary (26332 cells) MUST still pass byte-for-byte.

4. **Performance**: connected-component analysis on M=2-100 surfaces is O(M²) at worst; acceptable.

# Success criteria

1. iter01 thin-blade case meshes correctly: cell count slightly less than 7159, boundary file has 4 named patches.
2. icoFoam solve on iter01 produces qualitatively correct flow (slowing/recirculation behind blade, as intent.json predicted).
3. All existing tests pass (no regression on single-body LDC, channel, cylinder, naca0012 cases).
4. New 4 unit tests pass.
5. Codex review APPROVE or APPROVE_WITH_COMMENTS (≤2 rounds expected given complexity).

# Effort estimate

- Phase 1 (gmsh refactor): 1 week (150 LOC + topology helper module)
- Phase 2 (tests): 4 days
- Phase 3 (adversarial validation + iteration): 3 days

Total ≈ 2-3 weeks, depending on Codex round count for the topology partitioner.
