# DEC-V61-105 Phase 2.4 · Codex R1-R2 chain

**DEC**: `.planning/decisions/2026-05-01_v61_105_adversarial_smoke_as_hot_path_regression_gate.md`
**Phase**: 2.4 (forward-looking · Codex deferred findings — defensive hardening on gmsh runner named-solid voting)
**Trigger**: RETRO-V61-001 risk-tier · shared-infra geometry primitive change + multi-file backend logic (1 src + 1 test)
**Backend**: 86gamestore (`~/.codex-relay`, gpt-5.4, xhigh effort)
**Result**: 2 rounds → APPROVE (clean · 0 findings on R2)
**Self-estimated pass-rate vs actual**: 75% (R0 estimate) → 50% actual (1 CHANGES_REQUIRED + 1 APPROVE)

## Round 1 (commit 147ba92 · CHANGES_REQUIRED)

**Initial Phase 2.4 R0 scope**: close the two Codex deferred findings
explicitly listed in DEC-V61-105 §6.2.4:
1. `gmsh assumes 3-node tris; defensive check for mixed element types`
2. `malformed face-points raise IndexError before the fallback path`

Implementation landed at the named-solid per-triangle voting site
(`ui/backend/services/meshing_gmsh/gmsh_runner.py:262-322`):

- **#1 element-type guard**: validate `elem_types` from
  `getElements(dim=2, tag=tag)` contains only Triangle3 (gmsh element
  type 2); raise `GmshMeshGenerationError` listing the unsupported
  types and pointing the operator at `Mesh.ElementOrder=1` +
  `Mesh.SecondOrderIncomplete=0` as the re-mesh remediation.
- **#2 malformed-array guard**: assert `len(flat_nodes) % 3 == 0`
  before computing `n_tri`; raise `GmshMeshGenerationError` with the
  offending length so the operator either re-runs meshing or reports
  the gmsh-binding bug.

Tests (3): mixed `[Triangle3, Triangle6]` injection; `length=4` malformed
array injection; clean `[Triangle3]` regression guard.

### Codex finding (1 P2)

**[P2] Reclassify malformed Triangle3 payloads as backend errors**
— `ui/backend/services/meshing_gmsh/gmsh_runner.py:316-324`

> The new defensive checks are reasonable, but the malformed-node-array
> path introduces a fault-classification regression: gmsh/backend
> corruption is surfaced as a user-facing geometry rejection (422)
> instead of a backend error (5xx).
>
> When `gmsh.model.mesh.getElements()` returns a truncated Triangle3
> node array (for example from a gmsh binding/version mismatch or other
> internal payload corruption), this new branch raises
> `GmshMeshGenerationError`. That exception is mapped by
> `mesh_imported_case()` to `failing_check="gmsh_diverged"`/HTTP 422,
> so a backend fault is now reported as if the user's STL were bad.
> This codebase has been careful to keep backend/setup failures on a
> 5xx path, so this guard should use a non-geometry exception class
> instead.

**Codex did NOT flag #1.** A Triangle6/Quad4 surface element under
`Mesh.Algorithm3D=1` over STL input would imply the operator
misconfigured the mesher (e.g. flipped `Mesh.ElementOrder=2`); that IS
user-mesh-config fault, so 422 `gmsh_diverged` is the correct
classification for #1.

For #2, the operator has no agency — gmsh's binding returned bad data.
Project convention (`gmsh_runner.py:432` catch-all + `GmshSubprocessError`
docstring + `_subprocess_target` queue protocol): backend / binding /
host faults must bubble as 5xx. Codex is correct.

## Round 2 (commit 980e026 · APPROVE TBD)

**R1 closure scope** (this DEC's final Phase 2.4 decision):

- `gmsh_runner.py:316-340` — change defensive #2 from `raise
  GmshMeshGenerationError` to `raise OSError`. The existing
  `except OSError: raise` boundary at the catch-all + the `os_error`
  queue kind in `_subprocess_target` already propagate OSError as 5xx;
  no additional plumbing needed. Inline 11-line comment cites Codex R1
  P2 + explains the classification choice + names the path through
  `_subprocess_target`'s `os_error` branch.
- `test_meshing_gmsh.py::test_v61_105_phase2_4_rejects_malformed_triangle3_node_array`
  expectation flipped from `pytest.raises(GmshMeshGenerationError)` to
  `pytest.raises(OSError)`. Added two extra asserts:
  - `type(exc) is OSError` (bare class, not `FileNotFoundError` /
    `PermissionError` subclass — those carry different operational
    semantics)
  - `not isinstance(exc, GmshMeshGenerationError)` (locks the Codex R1
    P2 finding so any future regression that re-routes #2 through the
    422 path fails this test loudly)

Defensive #1 unchanged.

### Codex verdict (R2)

> The change consistently reroutes the malformed Triangle3 payload
> path onto the existing backend-fault/OSError path, which matches
> the surrounding subprocess and pipeline error-handling design. I
> did not find a discrete regression in the touched production code
> or its updated tests.

**APPROVE.** Zero findings on R2.

## Verification (R2 final state)

- 49/49 meshing_gmsh + topology unit tests green (37 pre-existing +
  3 new V61-105 P2.4 + 9 topology); zero regressions
- 839/843 full backend pass; the 4 failures are the documented V108
  pre-existing baseline
  (`test_case_export::test_export_renders_physics_contract_with_three_state_markers`,
  `test_convergence_attestor::test_attestor_bfs_real_log_is_hazard_plus_gate_fail`,
  `test_g1_missing_target_quantity` × 2 [bfs / cylinder]) — none
  touched by this change

## Methodology takeaway (for next RETRO)

**Defensive checks that gate user input vs backend faults must
choose the exception class deliberately.** R0 reflexively used
`GmshMeshGenerationError` for both defensive checks because both
fire in the gmsh path. But the two fault classes have different
agency:

- #1 mixed element types — operator misconfigured the mesher → 4xx
  geometry-rejection class is right
- #2 malformed node array — gmsh binding corruption / version
  mismatch → 5xx backend-fault class is right

The project already encodes this distinction in 3 places (catch-all
boundary, GmshSubprocessError docstring, `_subprocess_target` queue
protocol). R0 missed it because the two new guards looked alike at
the call site. Codex R1 caught it in static review.

The new test's `not isinstance(exc, GmshMeshGenerationError)` assert
locks the contract so any future "let's unify the defensive errors"
refactor fails loudly in CI.

## Counter

`autonomous_governance_counter_v61` advances by **+1** on V61-105
Phase 2.4 closure (autonomous_governance: true · 2 commits ·
1 CHANGES_REQUIRED → APPROVE Codex round arc · DEC-V61-105 itself
also flips Proposed → Accepted on this same closure since Phase 2.4
was the last open scope item per V61-105 §6.2 in-scope/out-of-scope).
