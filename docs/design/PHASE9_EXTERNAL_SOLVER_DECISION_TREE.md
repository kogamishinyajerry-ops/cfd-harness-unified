# Phase 9 External Solver Decision Tree

## Status

- Phase: `9`
- Task anchor: `Phase 9a - External solver touchpoint inventory + SU2/CFX decision tree`
- Prepared on: `2026-04-17`
- Updated on: `2026-04-17` (post-D4-gate trigger)
- Scope of this artifact: `planning only`
- Runtime changes in this artifact: `none`
- D4 gate status: `TRIGGERED` — SY-1 baseline captured, Opus review required before routing policy drafting

## Executive Summary

Phase 9 must not start from the assumption that `multi-solver runtime` is now allowed.
The current repo and Notion truth disagree only at the `tooling surface`, not at the
`execution plane`:

1. Notion still declares `OpenFOAM is the only execution engine` and explicitly rejects
   `SU2Executor`.
2. The repo exposes a `SU2 CLI Harness Skill` in `knowledge/skill_index.yaml` (installed
   in `cfd-openfoam` Docker container at `/opt/su2/bin/`).
3. The live execution adapter in `src/foam_agent_adapter.py` still targets the
   `cfd-openfoam` container and OpenFOAM-oriented execution only.
4. No first-class `CFX` surface is visible in the current repo or Phase metadata.
5. D4 gate has been triggered by SY-1 first baseline measurement. Phase 9 is frozen in
   `planning_only` until Opus reviews the baseline capture.

The recommended activation posture is therefore:

- keep `single-engine OpenFOAM runtime` as the default branch
- allow `SU2` to be evaluated as a `reference/tooling surface`
- keep `CFX` in `hold` until there is concrete evidence that it deserves a bounded slice
- require a new Opus review before any `executor` work is opened

## Repo Truth Inventory

| Surface | Evidence | Current meaning | Activation implication |
| --- | --- | --- | --- |
| Execution plane | `src/foam_agent_adapter.py` uses `cfd-openfoam` and OpenFOAM solver flows | Runtime remains OpenFOAM-centered | Preserve as default |
| Skill inventory | `knowledge/skill_index.yaml` includes `su2_harness` (SU2 v8.4.0 at `/opt/su2/bin/`) | SU2 exists as CLI/tooling surface in cfd-openfoam | May be evaluated as reference without opening runtime |
| Test coverage | `tests/test_skill_index/test_skill_loader.py` fixture includes `su2_harness` entry | SU2 harness is covered by skill_loader unit tests | Surface is under test coverage |
| Skill generator | `scripts/gen_skill_index.py` line 63 includes `su2` in harness detection | SU2 is recognized by the automated skill index generator | Integration is script-maintained |
| Whitelist policy | Notion canonical doc `AI-CFD Single-Engine OpenFOAM Whitelist v2` says `no SU2Executor` | Governance still fences execution to OpenFOAM | Must not be silently overridden |
| CFX surface | No repo hit in current scan | No live integration surface exists | Keep in hold branch |

## Plane Separation

### Execution Plane

Changes in this plane would include:

- new `CFDExecutor` implementations
- runtime routing that selects non-OpenFOAM solvers for case execution
- new container/runtime orchestration for external solvers
- changes to `task_runner`, `foam_agent_adapter`, or execution-side schemas

### Reference / Evaluation Plane

Changes in this plane may remain in-bounds for Phase 9 if Opus approves:

- CLI harness discovery and documentation
- benchmark-definition reuse
- geometry or observable mapping notes
- baseline planning and replay design
- report-side or governance-side comparison of solver capabilities

## SU2/CFX Touchpoint Inventory

### SU2 — Full Inventory

| Location | Evidence type | What it says |
| --- | --- | --- |
| `knowledge/skill_index.yaml` | skill entry `su2_harness` | SU2 v8.4.0 CLI harness, installed in `cfd-openfoam` at `/opt/su2/bin/` |
| `tests/test_skill_index/test_skill_loader.py` | unit test fixture | `su2_harness` appears in synthetic test index at lines 56-61 |
| `scripts/gen_skill_index.py` | harness detection | Line 63: `su2` included in harness-type file detection list |
| `reports/baselines/SY-1_deterministic_replay_capture.md` | baseline capture | D3 SU2/CFX redline compliance: CLEAR |
| `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md` | gate doc | SU2 classified as Branch B reference-only; SU2Executor out of scope |
| `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md` | gate doc | SU2 classified as Branch B; SU2Executor out of scope |
| `docs/design/this_file` | decision tree | Branch B assigned to SU2 |

**SU2 conclusion:** Surface exists in repo as tooling/reference only. No runtime executor exists.
Branch B (reference-only) is the correct and currently enforced posture.

### CFX — Full Inventory

| Location | Evidence type | What it says |
| --- | --- | --- |
| `docs/design/this_file` | decision tree | Branch A (hold) assigned to CFX |
| `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md` | gate doc | CFX hold posture; no repo touchpoint found |
| `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md` | gate doc | CFX hold posture confirmed |
| `reports/baselines/SY-1_deterministic_replay_capture.md` | baseline capture | D3 SU2/CFX redline compliance: CLEAR |

**CFX conclusion:** Zero repo surface. No skill entry, no harness, no test fixture, no
Docker integration. Branch A (hold) is the only defensible posture.

## Decision Tree

### Branch A — Hold Single-Engine Runtime

**Assigned to:** `CFX` (default, holds until evidence appears)

Entry criteria:

- existing OpenFOAM path can still cover the next meaningful benchmark set
- no named capability gap proves that OpenFOAM reconstruction is insufficient
- solver diversity would only add operational complexity without new learning value

Evidence required:

- current whitelist still maps retained validation targets into OpenFOAM reconstruction
- no pending blocker is attributable solely to the lack of an external solver runtime

Stop conditions:

- a named case or physics family cannot be bounded inside OpenFOAM with reasonable effort
- Phase 7/8 evidence shows systemic loss from single-engine reconstruction

Recommended use:

- default branch at Phase 9 activation
- also the current assignment for CFX

---

### Branch B — Allow Reference-Only External Surface

**Assigned to:** `SU2` (confirmed 2026-04-17)

Entry criteria:

- external solver value is limited to `definition`, `inspection`, `benchmark`, or
  `tooling assistance`
- no runtime path change is required

Evidence required:

- concrete list of files, skills, or artifacts that remain outside execution
- explicit confirmation that no `executor` abstraction or runtime route is opened

Stop conditions:

- proposed work starts to require execution scheduling, solver selection, or runtime I/O
- external tooling becomes coupled to case execution rather than evidence gathering

Recommended use:

- `SU2` may enter here immediately because a CLI harness surface already exists in cfd-openfoam
- SU2 v8.4.0 at `/opt/su2/bin/` is available as a reference inspection tool

---

### Branch C — Open Bounded Proof Slice

Entry criteria:

- a named capability gap exists
- the gap is tied to one bounded case family or one bounded benchmark obligation
- the slice can be fenced with explicit non-goals and no broad runtime rewrite

Evidence required:

- one named case or case family
- one measurable success criterion
- one additive integration boundary
- one rollback rule if the slice starts mutating the current execution plane

Stop conditions:

- the slice grows into general `multi-solver support`
- the slice needs a new executor family without a fresh gate
- the slice touches Phase 7 in-flight runtime files

Recommended use:

- do not open by default
- require a fresh Opus scope review even after Phase 9 activation

---

### Branch D — Reject Broad Multi-Solver Rollout

Entry criteria:

- proposal is framed as `support SU2/CFX generally`
- ROI is unclear or hand-wavy
- the change requires silent policy reversal

Evidence required:

- none; this is the safety branch

Stop conditions:

- reopen only when a bounded proof slice is named and scoped

Recommended use:

- default response to any attempt to convert Phase 9 into a general runtime expansion

## Current D4 Gate State

D4 has been triggered by SY-1 first baseline measurement (2026-04-17T07:10:00Z).
Per D4: "After first actual baseline measurement, STOP and submit lightweight Opus review
before drafting any Model Routing v3.2 policy text."

Current state: Phase 9 is frozen in `planning_only`. No routing policy drafting may proceed
until Opus reviews the SY-1 capture.

## Activation Recommendation

If Phase 9 is activated after Opus D4 review clears, the safest opening scope is:

1. `SU2 reference-only evaluation` (Branch B)
2. `CFX hold` (Branch A)
3. `Model routing baseline capture` (EX-1, PL-1, SY-1 replay tracks)
4. `No executor implementation`

This keeps the phase aligned with current repo truth and defers any execution-plane
expansion to a later bounded proof slice review.

## Non-Goals

- define or implement `SU2Executor`
- define or implement `CFXExecutor`
- rewrite whitelist runtime policy
- broaden execution coverage beyond the current OpenFOAM-centered model
- routing policy drafting before D4 gate is cleared by Opus

---

*Decision tree: 2026-04-17 | SU2=Branch B (reference-only) | CFX=Branch A (hold) | D4=TRIGGERED*
