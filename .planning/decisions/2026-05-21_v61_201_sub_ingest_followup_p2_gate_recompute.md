---
decision_id: DEC-V61-201-SUB-INGEST-P2-FOLLOWUP
title: Recompute ingest gate from residuals.csv when solver_gate.json is missing
status: Proposed
parent_dec: DEC-V61-201-SUB-INGEST
phase: post-merge follow-up
notion_sync_status: not_applicable_proposed
---

## Why

Codex R6 (CRS, effort=high) on `feature/audit-ingest-mode` raised this
finding as P2 alongside a P1 (state-clobbering) that landed in commit
`<R6-fix-SHA>` (round 7 of the V133 round-cap=3 + user-ratified
continuation arc). The P1 was a regression-risk; this P2 is a signal-
precision degradation. Per user ratification on 2026-05-21, the P2
was explicitly deferred to a follow-up sub-DEC rather than extending
the parent sub-DEC's review chain further. See
`.planning/retrospectives/2026-05-21_v61_201_sub_ingest_codex_5round_arc.md`
for the multi-round arc analysis.

## What

`audit/solver.py::read_artifacts()` currently collapses every
INGEST_BANNER-detected fallback to `status="WARN"`. This loses two
distinctions:

1. **Non-converged ingested case demoted upward**. A real-world
   external run that didn't meet its residual targets carries
   `status="FAIL"` in the persisted `solver_gate.json`. If that file
   is lost, the banner fallback re-classifies the case as WARN —
   silently upgrading a FAIL evidence-state to a WARN one. The user
   sees softer trust signal than the residuals actually justify.

2. **Fully-passing ingested case loses partial-validation path**.
   `report.py::assemble()` already caps an ingested case at
   `overall_status=WARN`, `validation_status=partial` when EVERY gate
   PASSes individually. The banner fallback's hard-coded WARN status
   means the solver gate is never PASS, so this branch in
   assemble() can never fire after gate-JSON loss.
   `validation_status` falls to `not_validated` instead of `partial`.

## How

`read_artifacts()` already has the manifest + `solver.log` +
`residuals.csv` in scope. The clean fix re-parses the log via
`backends/openfoam._parse_simplefoam_log` + recomputes the gate via
`_compute_gate_from_residuals(parsed, manifest)`, then overrides
`details.execution = "ingested"` + `details.real_solver_invoked =
False`. The resulting gate carries the correct PASS/WARN/FAIL status
AND the ingest provenance — exactly what the original successful
ingest produced, recovered from the disk artifacts.

## Scope class

Spike-class:
- Single file edit (`audit/solver.py`)
- ≤30 LOC change (one fallback branch rewrite)
- 2-3 tests adapting the existing R5-P1 tests to assert per-status
  recovery instead of hard-coded WARN
- No schema change, no governance change, no charter trigger

## Why deferred and not merged into parent DEC

Per V133, P2/P3 after R3 → retro queue. The parent DEC's review chain
hit 6 rounds (3 + 3 user-ratified) over R1→R6. Continuing for this P2
would replicate the N1.1 anti-pattern V133 was designed to prevent.

The deferral is honest because:
- The P1 from R6 (state clobbering) IS being landed in the parent DEC
  (it was a regression risk on user state, severity higher than
  precision-loss).
- This P2 is real but does not break honesty fences: an ingested case
  with a lost gate JSON still gets WARN-flavoured trust signal, NEVER
  a false PASS / validated.
- The follow-up is small + well-scoped enough to land as its own
  spike-class sub-DEC when someone has cycles for it.

## Acceptance criteria

- [ ] `read_artifacts()` banner-fallback branch recomputes the gate
      via `_compute_gate_from_residuals` + manifest residual_targets.
- [ ] `details.execution = "ingested"` + `real_solver_invoked = False`
      preserved.
- [ ] Existing R5-P1 tests updated:
      - non-converged ingested case + missing gate JSON → recovered
        gate status = FAIL (was WARN).
      - converged ingested case + missing gate JSON → recovered gate
        status = PASS; `report.py::assemble()` then writes
        `validation_status = "partial"` (was "not_validated").
- [ ] Existing 405 tests in the audit subsystem still pass.

## Risks

Low. The recomputation uses already-shipped pure functions
(`_parse_simplefoam_log` + `_compute_gate_from_residuals`); the gate
status will be exactly what the original successful ingest produced.
The only edge case is if residuals.csv has been corrupted while
solver.log is intact — the gate would report no-iterations-parsed
BLOCKED, which is the correct honest signal.
