---
followup_id: V71B-FOLLOWUP-2
title: Draft-editor vs frozen-benchmark identity — a workbench draft of a benchmark anchor that edits benchmark-defining params is mis-graded against the frozen gold
opened: 2026-06-09
opened_by: Codex DEC-V61-236 R4 P1 (final confirmatory review of 8606b3b) — user-ratified as a known limitation (accept + scoped follow-up)
priority: medium
severity: wrong-verdict-on-self-created-variant (NOT a silent unverified pass)
status: open
parent_dec: V61-236
---

# V71B-FOLLOWUP-2 · draft-editor ↔ frozen-benchmark identity

## The problem (the DEC-V61-236 R2→R3→R4 whack-a-mole, named)

`is_bfs_lowre_dispatch` (and any future specialized benchmark dispatch) must answer
"is THIS spec the canonical frozen benchmark anchor?" so the dedicated runner + the
frozen-gold gate fire for it and ONLY it. The workbench editor
(`PUT /api/cases/{id}/yaml` → `ui/backend/user_drafts/{case_id}.yaml`) makes that
question fundamentally ambiguous: a draft can override ANY field of a benchmark case
while keeping its `case_id`. Point-fixes keyed on a single attribute each revealed the
next edge:

- **R2 P2** — keying on `boundary_conditions.wall_treatment=='resolved'` was too BROAD
  (any resolved BFS draft got benchmarked). Fixed → name-only.
- **R3 P1** — keying on the editable `name` was too FRAGILE (a renamed anchor draft
  escaped the gate → silent unverified pass). Fixed → stable `case_id` (landed in
  DEC-V61-236 8606b3b: `TaskSpec.case_id` + `case_id`-keyed predicate).
- **R4 P1** (this follow-up) — keying on `case_id` is too BROAD for the editor path: a
  draft that KEEPS `case_id='backward_facing_step_lowre'` but EDITS a benchmark-defining
  param (`parameters.Re`, and by extension `expansion_ratio`/mesh) is still routed to the
  dedicated runner and graded by `_verify_bfs_lowre` against the FROZEN Re=5000 gold
  (Xr/H=6.26) — a WRONG verdict on a user-created variant.

The root cause is structural: a mutable draft of a frozen benchmark has no clean
single-key identity. Each param the predicate doesn't check is an escape hatch.

## Severity / blast radius (why it was ratified as a known limitation, not a blocker)

- **Trigger is narrow + deliberate**: a user must open the canonical benchmark anchor in
  the workbench editor, change a benchmark-defining param (e.g. Re), save it as a draft,
  and run it.
- **Failure mode is a WRONG VERDICT, not a silent unverified pass** (the cardinal sin R3
  closed): the gate DOES run and emits PASS/FAIL — it just compares a variant against the
  wrong gold (almost certainly a FAIL, since Xr/H at a different Re ≠ 6.26).
- **The PRIMARY path is unaffected and correct**: the benchmark anchor run+verified
  through the whitelist / `run_batch` path (the actual DEC-V61-236 deliverable) is
  unambiguous and green — `case_id` there comes from the frozen whitelist `id`, params
  from the frozen whitelist gold.

## Candidate holistic fixes (decide deliberately, NOT under round-cap pressure)

1. **Source-gating (preferred direction)**: bind the frozen-benchmark gate to the
   FROZEN source only. Only whitelist/batch-sourced specs are "the benchmark"; ANY
   draft-sourced spec is a user variant and is NEVER routed to the frozen-gold gate
   (it stays unverified-by-this-gate, which is HONEST for a variant — the UI must show
   "user variant · not benchmark-verified", not a bare success). Mildly reopens R3's
   "renamed unedited draft" (it would show unverified) — acceptable IF the UI is honest.
   Needs a `source` signal on TaskSpec (the `_task_spec_from_case_id` `source_origin`
   already distinguishes draft vs whitelist — thread it onto the spec).
2. **Canonical-param fingerprint**: route to the benchmark only when case_id==anchor AND
   the benchmark-defining params match the frozen whitelist values (Re, expansion_ratio,
   …). Closes R4 but is a maintenance burden (every benchmark-defining field must be
   enumerated; a missed field is the next escape hatch).
3. **Forbid editor drafts of whitelist anchors**: the editor refuses to save a draft over
   a frozen whitelist `id` (anchors are read-only in the workbench). Simplest, but a
   product-UX decision.

## Done-when

A workbench-editor draft that edits ANY benchmark-defining field of a whitelist anchor is
either (a) not routed to the frozen-benchmark gate at all (source-gated) or (b) correctly
recognised as a non-canonical variant — with an honest UI verdict in both cases, and a
regression test for the param-edited-draft path. Decided + implemented deliberately, not
as a round-cap point-fix.
