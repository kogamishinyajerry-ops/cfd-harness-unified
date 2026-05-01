# Codex Review Chain · DEC-V61-104 Phase 1

**DEC**: DEC-V61-104 — Interior-obstacle topology
**Phase**: 1 (scaffolding only — partitioner + multi-loop addVolume call site + tests)
**Risk-tier triggers** (per RETRO-V61-001): CFD geometry handling + meshing hot path + multi-file backend logic = mandatory Codex review

## R8 — verdict: APPROVE_WITH_COMMENTS · 2 MED findings

**Reviewed commit**: `30b659b` (Phase 1 initial implementation)

**Finding #1 — Test coverage gap**
> "the new 'real-gmsh integration' test does not cover the new `gmsh_runner` branch or the `addVolume([outer, -inner...])` behavior it is meant to protect."

The existing real-gmsh test only exercised `partition_surfaces_by_body` against `classifySurfaces` output. The new gmsh_runner branch (the multi-loop `addSurfaceLoop` + `addVolume` call site that Phase 1 added) was uncovered.

**Finding #2 — Silent geometry corruption risk**
> "the multi-body branch assumes every non-largest component is an interior obstacle and negates it unconditionally. If partitioning or bbox ranking is wrong, or if the STL contains two disconnected exterior shells rather than 'outer + inner', this becomes a silent geometry corruption path instead of a loud rejection. There is no containment/sanity check before `addVolume([outer_loop] + [-loop ...])`."

Two disconnected exterior shells (e.g. two separate cubes that do not enclose one another) would be partitioned with the larger one selected as outer and the smaller silently treated as a hole — the resulting mesh would be physically wrong with no error surfaced.

## R9 — verdict: APPROVE · 0 findings (clean close)

**Reviewed commit**: `bec98b2` (R8 closure)

Direct quote from R9:

> APPROVE
>
> - No findings. The fix closes R8 #2 by rejecting non-contained secondary bodies in [topology.py](ui/backend/services/meshing_gmsh/topology.py:125) before they can be negated as holes, and [gmsh_runner.py](ui/backend/services/meshing_gmsh/gmsh_runner.py:186) maps that rejection into the existing geometry-failure path instead of silently meshing corrupted topology.
> - R8 #1 is also closed: [test_meshing_topology.py](ui/backend/tests/test_meshing_topology.py:198) adds the pure-logic containment/error-path coverage, and [test_meshing_topology.py](ui/backend/tests/test_meshing_topology.py:346) now exercises the real gmsh multi-loop `addSurfaceLoop` → `addVolume([outer, -inner])` → `synchronize()` → `generate(3)` branch with a non-zero tetrahedral-cell assertion.
> - I did not rerun the tests in this shell because the local env here is missing `trimesh` (`ModuleNotFoundError` from `ui/backend/tests/conftest.py`), so the verdict is based on code inspection plus your reported 14/14 local pass.

## Summary

- Codex chain: **R8 APPROVE_WITH_COMMENTS → R9 APPROVE** (1 round of CHANGES_REQUIRED-style closure)
- Self-estimated pass rate at DEC authoring: 50%
- Actual outcome: 1 round of MED-finding closure before clean APPROVE → estimate was reasonable (Codex did find issues, but they were tractable in one fix pass)
- 14/14 topology unit tests pass locally
- 769/773 backend tests pass (4 pre-existing unrelated failures in `case_export` / `convergence_attestor` / `g1_missing_target_quantity`)
- 4 PASS · 2 SKIP · 0 FAIL adversarial smoke baseline preserved

## Honest Phase 1 scope limitation

Phase 1 ships **scaffolding only**. Empirical finding documented in
`tools/adversarial/results/iter01_v61_104_phase1_partial_findings.md`:

> The cell count does not change between single-loop and multi-loop addVolume. gmsh's geo-kernel `addVolume([outer, -inner])` accepts the negated inner loop syntax but does not actually subtract the inner volume during tetrahedralization. Cells are still generated INSIDE the inner body.

iter01 status correctly reclassified as `physics_validation_required` until Phase 1.5 lands a working subtraction strategy.

## Phase 1.5 follow-up DEC scope

- **Approach A**: OCC-kernel boolean cut (`gmsh.model.occ.cut`) — proper boolean operation
- **Approach B**: explicit surface-orientation reversal via `gmsh.model.geo.reverse` before addSurfaceLoop
- **Approach C**: classifySurfaces angle tuning (40° → 90°+)

Each is 1-3 days of investigation + tests. Best handled in a fresh DEC-V61-104.1 follow-up with its own Codex chain.
