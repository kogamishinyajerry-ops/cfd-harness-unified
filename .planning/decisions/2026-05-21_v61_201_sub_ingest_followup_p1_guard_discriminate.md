---
decision_id: DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE
title: Tighten ingest BLOCKED-skip guard to discriminate precondition vs post-residual outcomes
status: Accepted
accepted_date: 2026-05-22
parent_dec: DEC-V61-201-SUB-INGEST
phase: post-merge follow-up
notion_sync_status: pending_session_end_batch
---

## Why

Codex R7 (86gs, effort=xhigh) on `feature/audit-ingest-mode` raised
this finding as P1 alongside another P2. Per user discipline-rule on
2026-05-21 ("strict stop-and-queue at 7 rounds" — see retrospective
`2026-05-21_v61_201_sub_ingest_codex_5round_arc.md`), both R7
findings were deferred rather than iterated. The R6 P1 fix in
commit `bd03954` introduced this over-suppression as a side-effect
of correctly protecting precondition refusals.

## What

`audit/solver.py::ingest()` currently guards against state-clobbering
with `if gate.get("status") == "BLOCKED": return gate` (no
`_write_gate` call). This is too coarse:

- **Correct case (precondition refusal)**: backend returned BLOCKED
  with `details.execution == "skipped"` for env failures (Docker
  unavailable, no log, decomposed-only, image not pulled, etc.).
  Skipping persistence is right — prevents clobbering existing
  good gates.

- **Incorrect case (post-residual BLOCKED)**: backend completed env
  checks, ran checkMesh, transcribed log, parsed residuals, and then
  `_compute_gate_from_residuals` returned BLOCKED because the parsed
  log has no iterations (`no_iterations_in_log`) or none of the
  manifest target fields appear (`fields_missing_in_log`). These ARE
  real ingested-solver evidence outcomes — `details.execution ==
  "ingested"` is already set on the gate. Skipping persistence here
  drops the real BLOCKED reason; subsequent `cfdtrust report` falls
  back to the banner-fallback path in `read_artifacts()` and surfaces
  the generic ingested-WARN message instead of the actual diagnostic.

## How

Replace the status-only check with a discriminator on the gate's
`details.execution`:

```python
details = gate.get("details", {}) or {}
if gate.get("status") == "BLOCKED" and details.get("execution") == "skipped":
    # Precondition refusal: do not clobber existing solver_gate.json
    return gate
return _write_gate(case_dir, gate)
```

`details.execution` is already set to `"skipped"` by every backend
precondition BLOCKED return and to `"ingested"` by the post-residual
gate. The discriminator is already in the data.

## Scope class

Spike-class:
- 1 file edit (`audit/solver.py`), 2-3 LOC
- 2 tests (post-residual BLOCKED persists; precondition refusal still
  doesn't)
- No schema change, no governance change

## Why deferred and not merged into parent DEC

User hard-stop discipline at 7 rounds (2026-05-21) to avoid the N1.1
22-round anti-pattern V133 was designed to prevent. The R7 P1 is a
real regression in the R6 P1 fix, but the worst-case behaviour is
"masked diagnostic at report time" (the gate falls through to the
WARN banner-fallback rather than surfacing the actual `no_iterations`
reason) — does NOT break honesty fences, does NOT silently produce
false PASS/validated.

## Acceptance criteria

- [ ] `solver.ingest()` guard discriminates by `details.execution`
- [ ] Test: post-residual BLOCKED (e.g., empty log → no iterations)
      persists to `solver_gate.json` with the real reason
- [ ] Test: precondition BLOCKED (no_solver_log_found) still does
      NOT persist (existing R6 protection preserved)
- [ ] All 405 existing tests still pass

## Risks

Very low. The change is a tighter discriminator, not a behaviour
flip — the precondition-protection path is preserved verbatim.

## Implementation note

- **Commit**: `e86c011` (e86c0112fc46b473dde4551137ba7d02b04746a5).
- **Branch**: `worktree-agent-a99d74ec81d8094d9`.
- **Functional LOC delta** (`ui/backend/audit/cfdtrust/audit/solver.py`):
  net +2 LOC of behaviour change — extract `details = gate.get("details", {}) or {}`
  and tighten the guard predicate to
  `gate.get("status") == "BLOCKED" and details.get("execution") == "skipped"`.
  Total file diff is +22/-11 because the surrounding R6-P1 commentary
  was rewritten to explain both the skipped/ingested discriminator and
  cross-reference this DEC; pure code change is 3 lines as specified
  in §How.
- **Tests added** (`ui/backend/audit/cfdtrust_tests/test_ingest_mode.py`):
  - `test_solver_ingest_post_residual_blocked_persists_real_diagnostic` —
    asserts that a log with zero parseable iterations triggers
    `_compute_gate_from_residuals` → BLOCKED with
    `details.execution == "ingested"` and `reason == "no_iterations_in_log"`,
    and that this gate IS persisted to `artifacts/solver_gate.json`
    (the R7-P1 regression case).
  - `test_solver_ingest_precondition_blocked_still_protected_by_discriminator` —
    asserts that `no_solver_log_found` (precondition refusal,
    `details.execution == "skipped"`) still does NOT clobber a
    pre-existing `solver_gate.json` from an earlier successful
    `cfdtrust run` (R6-P1 protection preserved verbatim).
- **Test suite**: 407 → 409 passing in
  `ui/backend/audit/cfdtrust_tests/` (1 skipped unchanged). No
  regressions in any other test.
- **Spike-class compliance**: 1 file edit (≤3 functional LOC) +
  2 tests + 0 schema change + 0 governance change. No DEC body
  beyond this note; no Codex relay round (R7-P1 finding was already
  reviewed in the parent DEC's R7); no Kogami invocation; no
  charter-trigger surface crossed.
