---
decision_id: DEC-V61-099
title: M-PANELS Phase-1A · post-R3 live-run defect closure — solver_streamer staging order regression (V61-097 R1 HIGH-2 interaction)
status: Active (2026-04-29 · post-R3 live-run defect per RETRO-V61-053 addendum methodology · Codex pre-merge mandatory per RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · CFDJerry caught on first LDC dogfood after V61-097 R4 RESOLVED commit `c49fd11`)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-29
authored_under: V61-097 closure arc · post-R3 defect class per RETRO-V61-053 addendum
parent_decisions:
  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · this DEC closes a DEFECT INTRODUCED IN ROUND 1 of that arc)
  - RETRO-V61-001 (risk-tier triggers · OpenFOAM solver bug fix mandates Codex pre-merge)
  - RETRO-V61-053 addendum (post-R3 live-run defect methodology · executable_smoke_test risk-flag class)
parent_artifacts:
  - reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md (round 1 verdict where the buggy fix originated)
  - reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md (round 4 RESOLVED · static review missed the runtime defect)
implementation_paths:
  - ui/backend/services/case_solve/solver_streamer.py (MODIFIED · staging order at lines 284-321 · pre-create BASE only · unconditional mv with rm -rf guard)
  - ui/backend/tests/test_solver_streamer.py (MODIFIED · NEW test_staging_renames_extracted_dir_into_run_id_suffix regression test · tracks bash command sequence)
notion_sync_status: pending
autonomous_governance: true
codex_review_required: true
codex_review_phase: pre-merge (RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · post-R3 defect raises stakes)
codex_triggers:
  - OpenFOAM solver 报错修复 (FOAM Fatal Error: cannot find file system/controlDict)
  - Phase E2E 批量测试中超过 3 个 case 连续失败 — N/A (single-case dogfood failure but post-R3 elevates priority)
  - solver_streamer.py modification > 5 LOC
kogami_review:
  required: false
  rationale: |
    Post-R3 closure of a defect within an already-Codex-blessed arc.
    Per V61-094 P2 #1 bounding clause (Accepted 2026-04-28): no
    charter modification, no line-A extension, counter <20 since
    RETRO-V61-005, no risk-tier change. Self-check 4 conditions all NO.
break_freeze_required: true
break_freeze_rationale: |
  Bug fix to V61-097 BREAK_FREEZE'd code (slot 2/3 already consumed
  by V61-096 + V61-097 arc). This fix RIDES UNDER V61-097's existing
  BREAK_FREEZE — does NOT consume new quota. Per Pivot Charter
  Addendum 3 §5: bug fixes within an Accepted arc do not consume
  fresh slots. Quota count: still 2/3 → 3/3 after M-AI-COPILOT
  arc closes (this DEC does not change the projection).
self_estimated_pass_rate: 80
self_estimated_pass_rate_calibration: |
  Higher than typical (V61-097 was 55%) because:
  - Fix is structurally simple: mkdir BASE only + unconditional mv +
    defensive rm -rf. ≤15 LOC.
  - Regression test pins the exact failure mode by tracking bash
    command sequence — Codex can verify the test catches the bug
    by examining the assertions.
  - No new public API. No new dependency. No cross-track contract.
  - The 5-condition verbatim-exception path FAILS (this is a NEW
    finding not derived from a Codex round, condition 1 fails;
    PR body cannot reference a Codex round closure, condition 5
    fails) → full Codex pre-merge review required, not verbatim.
  Calibration risk: Codex may flag (a) the rm -rf as overly broad
  (suggest narrower removal); (b) chmod 777 as too permissive;
  (c) the regression test's string-matching assertions as fragile
  to future refactor. All three are reasonable findings — would
  cost a round 2.
counter_v61: 64
counter_v61_delta_since_retro: 13  # since RETRO-V61-005
---

## Decision

Apply a 15-LOC fix to `ui/backend/services/case_solve/solver_streamer.py`
that corrects the staging order introduced in V61-097 round 1 HIGH-2
(run_id-suffixed `container_work_dir`). Add a regression test
(`test_staging_renames_extracted_dir_into_run_id_suffix`) that pins
the exact failure mode by tracking the bash command sequence sent to
the container.

## Root cause

V61-097 round 1 HIGH-2 fix made `container_work_dir` run_id-suffixed
to prevent abandoned-run collisions. The staging sequence was:

```python
# BUGGY:
container.exec_run(cmd=["bash", "-c",
    f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}"])  # ❶
ok = container.put_archive(path=CONTAINER_WORK_BASE, data=...)             # ❷
container.exec_run(cmd=["bash", "-c",
    f"if [ -d {CONTAINER_WORK_BASE}/{case_id} ] && "
    f"[ ! -d {container_work_dir} ]; then "
    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir}; fi"])       # ❸
```

❶ pre-creates the suffixed dir as an empty real directory.
❷ extracts the tarball, which lands as `{BASE}/{case_id}` (un-suffixed,
   since the tarball's top-level dir is named after the host case dir).
❸ guards the rename with `[ ! -d {container_work_dir} ]` — but ❶ just
   created it, so the guard is FALSE → `mv` is silently SKIPPED.

End state:
- `{BASE}/{case_id}/` (un-suffixed): contains the actual case files
- `{BASE}/{case_id}-{run_id}/` (suffixed): empty
- icoFoam `cd`'s into the empty suffixed dir → **FOAM Fatal: cannot
  find file system/controlDict**

## Why Codex's static review missed this

The V61-097 round-1 verdict file (`reports/codex_tool_reports/
dec_v61_097_phase_1a_round1.md`) flagged "abort/restart race — no
run-generation guard, shared `container_work_dir`" as HIGH-2.

The fix Claude applied for HIGH-2 was correct in concept (run_id
suffix + per-case lock + run_id surfaced via SSE `start` event), but
the BASH sequence interaction (mkdir + put_archive + conditional mv)
was a runtime-emergent failure mode that the test suite did not
exercise:

- `test_run_id_suffixes_container_work_dir` (line 220-249) only
  checked that `prepared.container_work_dir.endswith(...)` — string
  assertion, not file-system behavior.
- The `_FakeContainer.put_archive` mock returned `True` without
  simulating the actual extract behavior. The mock had no notion of
  WHERE the tarball would land, so it couldn't surface the
  ❶-❷-❸ interaction.
- Codex rounds 2/3/4 never re-examined the staging sequence because
  rounds 2/3 closed the GeneratorExit + cache-hit symlink + start
  yield findings — orthogonal to staging.

This is the **`executable_smoke_test` blind-spot class** documented
in RETRO-V61-053 addendum: defects that require a real execution
environment (Docker container actually running put_archive +
icoFoam) to surface, regardless of how thorough static review is.

## The fix

```python
# FIXED:
container.exec_run(cmd=["bash", "-c",
    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}"])  # ❶'
ok = container.put_archive(path=CONTAINER_WORK_BASE, data=...)              # ❷
container.exec_run(cmd=["bash", "-c",
    f"rm -rf {container_work_dir} && "
    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
    f"chmod 777 {container_work_dir}"])                                      # ❸'
```

Changes:
- ❶' pre-creates ONLY the BASE (idempotent), not the suffixed dir.
- ❸' is unconditional: `rm -rf {container_work_dir}` defensively
  clears any orphan from a prior abandoned run (process kill, container
  restart) whose `finally` cleanup didn't run; then `mv` always
  succeeds because the destination doesn't exist.
- `chmod 777` moves into ❸' (it was applied to the wrong path in ❶
  anyway — the suffixed dir didn't actually receive the case files).

## Why this fix is safe

- run_id is unique per `_claim_run` (hex token from secrets module),
  so no in-flight peer can hold the same suffixed path → no race
  between concurrent runs that the `rm -rf` could harm.
- The `_finally` cleanup path at solver_streamer.py:528 already does
  `rm -rf {container_work_dir}` — the fix's defensive rm just
  duplicates that cleanup at a known safe time (start of new run,
  after the run_id is uniquely claimed).
- Container-internal scope only — `{CONTAINER_WORK_BASE}` is
  `/tmp/cfd-harness-cases-mesh` inside the cfd-openfoam Docker, not
  a host path.

## The regression test

Added `test_staging_renames_extracted_dir_into_run_id_suffix` in
`ui/backend/tests/test_solver_streamer.py`. Tracks every `bash -c`
command sent to `exec_run` and asserts:

1. **No mkdir pre-creates the run_id-suffixed dir.** This catches
   the V61-099 bug because the buggy version's mkdir included the
   suffix.
2. **The mv is unconditional** (no `[ ! -d {suffix_dir} ]` guard).
   This catches any future regression that re-introduces the guard.

Test passes against the fixed code; would fail against the buggy
code (verified by inspection of the assertion logic).

## Governance

- **Codex pre-merge review**: MANDATORY. Triggers per RETRO-V61-001:
  - "OpenFOAM solver 报错修复" (FOAM Fatal Error: cannot find file)
  - "solver_streamer.py modification > 5 LOC" (this fix is ~15 LOC)
- **Verbatim exception**: NOT applicable. Conditions 1 and 5 fail
  (this is a NEW finding from live run, not a Codex round closure).
- **§11.1 BREAK_FREEZE**: rides under V61-097's existing slot 2/3.
  Bug fixes within Accepted arcs do NOT consume fresh quota per
  Pivot Charter Addendum 3 §5.
- **Counter**: +1 (63 → 64). `autonomous_governance: true`.
- **Kogami**: NOT triggered (V61-094 P2 #1 bounding clause · 4-condition
  self-check passes).
- **RETRO addendum**: required per RETRO-V61-053 methodology. Will
  add to next RETRO entry as a `hidden_defects_caught_post_R3` row,
  with `executable_smoke_test` risk-flag tagged.

## Lessons for future arcs

1. **Mock fidelity**: `_FakeContainer.put_archive` returning True
   without simulating extract was the single point that allowed this
   to slip. Future Docker-mock test suites should track destination
   paths AND simulate extract semantics, OR fail loudly when called
   without that fidelity.
2. **Bash command sequence audit**: when staging logic spans 3+
   exec_run calls with shared filesystem state, add a regression
   test that asserts the SEQUENCE not just individual commands.
3. **Live-run smoke before R4 RESOLVED**: per RETRO-V61-053
   addendum, every Codex APPROVE arc should ideally have at least
   one live-run smoke test before the arc is declared closed. V61-097
   was declared RESOLVED based on static analysis only (Codex round 4
   confirmed no findings) — first live run surfaced this defect ~1
   hour after the push to origin/main.

## Linked artifacts

- DEC-V61-097 (predecessor · closed `c49fd11`) — this DEC closes a
  defect originating in V61-097 round 1
- RETRO-V61-053 addendum (post-R3 defect methodology) — captures
  the `executable_smoke_test` risk-flag class this defect belongs to
- M-AI-COPILOT (DEC-V61-098 · Active) — implementation arc currently
  in flight; this fix lands BEFORE M-AI-COPILOT Step 2 backend
  skeleton to avoid mixing concerns
- Workbench long-horizon roadmap (proposal at
  `.planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md`) —
  M9 (Tier-B AI) and beyond depend on Phase-1A staging being
  trustworthy on arbitrary STL geometries
