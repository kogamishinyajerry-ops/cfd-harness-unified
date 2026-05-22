# Dogfood · case_007 KCS VOF · M3.0 cycle 2 closed-loop

> **Cycle**: DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR
> **Date**: 2026-05-22
> **Surface under test**: GET frame → PATCH /api/cases/{id}/manifest → re-GET frame loop
> **Method**: programmatic via FastAPI TestClient in `scripts/dogfood/case_007_cycle2_closed_loop.py`
> **Verdict**: **PASS** · 8/8 checks

## Context

Cycle 1 landed the display layer; cycle 2 closes the **observation → action → state-change** loop. This dogfood proves:

1. Engineer can SEE what's blocking (cycle 1 surface)
2. Engineer can CLICK a CTA to apply a fix (cycle 2 mutation path)
3. The next frame REFLECTS the change (cycle 2 invalidation path)
4. Unrelated downstream problems PERSIST (no false "completed" claims)

## Test design

Synthetic case_007 state:
- `manifest`: interFoam + kOmegaSST, **no `vof_contract.phases` declared**
- `artifacts.bc_quality.json`: `gate_status: FAIL` with `Missing field p_rgh` finding
- Uses **real** `analyze_case_completeness()` (not a fake) — verifies post-PATCH frame correctly reflects the new manifest state from disk

## Trace

```
[Step 3 pre-PATCH]   rail.kind = info_gap, field_path = physics.solver
                     topbar.kind = step_default, topbar.enabled = False
                     manifest_sha[:8] = 2f4a2246

[PATCH vof_contract.phases = ["water", "air"]]
                     applied_path = vof_contract.phases
                     new_sha[:8] = b6fef8c3
                     case_kind = imported_user

[Step 3 post-PATCH]  manifest_sha[:8] = b6fef8c3  (matches PATCH response)

[Step 4 post-PATCH]  rail.kind = problem_fix
                     rail.title = bc_quality.json FAIL
                     bottom_cards include "Missing field p_rgh"
```

## Closure criteria (cycle 2)

| # | Check | Result |
|---|---|---|
| 1 | Step 3 pre-PATCH rail surfaces actionable item (info_gap or problem_fix) | PASS |
| 2 | Step 3 pre-PATCH topbar disabled when rail is info_gap | PASS |
| 3 | Step 3 pre-PATCH topbar reason is set when disabled | PASS |
| 4 | PATCH endpoint returns 200 + success=true | PASS |
| 5 | PATCH applied_path matches request field_path | PASS |
| 6 | New state_sha differs from old (write actually happened) | PASS |
| 7 | Post-PATCH frame's manifest_state_sha matches PATCH response | PASS |
| 8 | Step 4 still surfaces p_rgh problem (partial-progress preserved) | PASS |

## Observations / cycle 3 candidate

The real `analyze_case_completeness()` for `imported_user` cases prioritizes `physics.solver` / `bc.patches` over `vof_contract.phases` in the missing-fields list — so the rail at Step 3 surfaces `physics.solver` first (not phases). This is correct from completeness's perspective but means a beginner constructing a VOF case sees solver+turbulence requests before phase declarations.

**Cycle 3 candidate**: re-prioritize completeness's missing list per-step. Step 3 (Physics) should put `vof_contract.phases` / `compressible_contract.*` / `les_contract.*` BEFORE generic `physics.solver` when the manifest already declares a multiphase / compressible / LES regime. Captured in cycle 3 sub-DEC's "out of scope" list as a queue item.

## V130 four-question gate

| Q | Answer |
|---|---|
| LLM offline runnable? | Yes — PATCH service is pure Python; no LLM call |
| Artifacts as truth? | Yes — frame re-reads manifest from disk on next GET |
| TrustGate explainable? | Yes — frame still carries `rail_primary.provenance` |
| AI advisory-only? | Yes — PATCH is engineer-initiated (rail CTA click), not AI-initiated |
| 5th (DEC-V61-202): serves guided UX? | Yes — closes the loop a beginner needs to make progress |

## Provenance

- Sub-DEC: `.planning/decisions/2026-05-22_v61_202_sub_m30_cycle2_mutation_topbar.md`
- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (Accepted 2026-05-22)
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Dogfood script: `scripts/dogfood/case_007_cycle2_closed_loop.py`
- Backend commits: `524d40b` (schema + service + route + 20 tests)
- Frontend commit: (this session HEAD)
