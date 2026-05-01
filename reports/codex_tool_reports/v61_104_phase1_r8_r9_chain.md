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

## Phase 1.5 empirical correction (2026-05-01) — original Phase 1 root-cause was wrong

Probe across mesh densities `lc ∈ {0.0085, 0.005, 0.003, 0.002, 0.001}` on actual `iter01/geometry.stl`:

| lc | single-loop total | inside blade bbox | multi-loop total | inside blade bbox |
|---|---|---|---|---|
| 0.0085 | 7,133 | **0** | 7,133 | **0** |
| 0.005 | 30,237 | **0** | 30,237 | **0** |
| 0.003 | 132,089 | **0** | 132,089 | **0** |
| 0.002 | 434,121 | **0** | 434,121 | **0** |
| 0.001 | 3,407,604 | **0** | 3,407,604 | **0** |

gmsh's single-loop `addVolume([all_surfaces])` ALREADY treats internal shells as obstacles — zero cells inside blade across 3 orders of magnitude of density. The Phase 1 multi-loop scaffolding produces byte-identical output. **The "no subtraction" claim was a probe artifact** (previous probe only counted total cells, not their location).

### What this means

- **Phase 1 multi-loop code is functionally redundant** but not harmful (same output as single-loop)
- **R8 TopologyPartitionError containment guard remains valuable**: protects against disconnected exterior shells (two separate cubes that would silently mesh wrong otherwise)
- **The original 3 Phase 1.5 approaches are RETIRED**: OCC cut / surface reversal / angle tuning all unnecessary
- **Phase 1.5 re-scoped**: investigate iter01's actual physics defect (BC mapping, solver, etc.) — the meshing layer is innocent

This honest correction prevented 1-3 days of engineering on a non-problem.
