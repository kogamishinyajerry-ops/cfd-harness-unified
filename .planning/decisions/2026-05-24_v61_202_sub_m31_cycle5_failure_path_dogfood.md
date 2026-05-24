---
decision_id: DEC-V61-202-SUB-M31-CYCLE5-FAILURE-PATH-DOGFOOD
title: M3.1 cycle 5 — failure-path ergonomics dogfood (wrong-fix → revert → proceed)
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (1 P2 + 1 P3) → R1 (1 P3) → R2 (1 P3) → R3 (1 P2, user-ratified small fix)
final_commit: 46880cc
user_ratification: 2026-05-24 AskUserQuestion — "Apply small msg-only scan fix, close cycle 5 (Recommended)"
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 5 (engineer mistake-recovery validation)
notion_sync_status: synced 2026-05-24 (https://www.notion.so/36ac68942bed8187ba36f2b3134dd547)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE7-BEGINNER-TEST  # happy-path surrogate
  - DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF
---

## Why

M3.0 retro Open Question #3:
> "The litmus surrogate took the happy path; we have no evidence the
> workbench handles 'engineer applies wrong fix → re-audit surfaces new
> FAIL → engineer reverts' cycles gracefully. M3.1 should write a
> failure-path dogfood."

Cycle 5 writes that dogfood. The goal is **document, not fix** — surface
whatever the system actually does when an engineer makes a recoverable
mistake. If bugs are found, file them as cycle-6+ work rather than
expanding cycle 5 scope.

## What

### In scope

1. **New dogfood script** `scripts/dogfood/case_007_cycle5_failure_path.py`
   walking this 7-step journey on an imported interFoam case:

   a. **Initial**: stage manifest with no case_family, no bc.patches
   b. **Correct progress**: PATCH case_family=ship_vof → rail surfaces
      skeleton at step 4
   c. **Apply skeleton**: PATCH bc.patches=skeleton → bc.patches lands
   d. **Wrong move (silent)**: PATCH bc.patches.inlet.patch_type to a
      structurally-valid but semantically-wrong value (e.g.
      `"fixedValue_typo"`) — tests whether the backend silently
      accepts the bad value or rejects it
   e. **Wrong move (structural)**: PATCH bc.patches.inlet to a
      type-wrong value (e.g. a string instead of a dict) — tests
      whether the backend rejects on type validation
   f. **Revert correct value**: PATCH back to the canonical
      `"fixedValue"` — tests whether the rail clears and case
      becomes ready again
   g. **Final fetch**: confirm step 4 rail returned to step_default
      and case is ready

2. **Verification checks** (≥5 PASS items):
   - case_family PATCH succeeds
   - skeleton PATCH succeeds
   - typo PATCH either rejects (200 success=false + validation_errors)
     OR succeeds-but-manifest-shows-typo (document either way)
   - struct-wrong PATCH must reject (type mismatch is a hard
     contract violation)
   - revert PATCH succeeds and manifest restores
   - final rail kind is step_default

3. **DOGFOOD report** `.planning/dogfood/DOGFOOD_M31_CYCLE5_FAILURE_PATH.md`
   capturing what the system actually does at each step. If bugs are
   surfaced, document them and create cycle-6+ followup entries (this
   DEC does NOT fix bugs found — just inventories them).

### Out of scope (later cycles)

- **Fixing any bugs the dogfood surfaces** — cycle 6+ scope. Each bug
  gets its own sub-DEC.
- **UI revert affordance** ("undo last PATCH" button) — frontend
  feature, cycle 7+.
- **Audit-pipeline state tracking across mutations** — needs separate
  design DEC if this turns out to be inconsistent.
- **Multi-step undo / history rewind** — orthogonal feature.
- **Concurrent-edit conflict resolution** — covered by
  `manifest_state_sha` already.

## Closure criteria

- [ ] Dogfood script `case_007_cycle5_failure_path.py` exists and
      runs to completion (PASS or document FAIL per step)
- [ ] DOGFOOD report enumerates what happened at each of 7 steps
- [ ] Any bugs found are filed as a numbered backlog in DOGFOOD doc
      (cycle-6+ candidates)
- [ ] Codex review ≤ 3 rounds
- [ ] DEC Proposed → Accepted (whether or not all 7 checks PASS —
      the goal is documentation, not happy-path)
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Dogfood surfaces a critical backend bug (e.g. PATCH silently corrupts manifest) | Document + file cycle-6 fix DEC. Don't expand cycle 5 to "fix the bug we just discovered" |
| `manifest_patch` validation is stricter than the dogfood expects (rejects typo at step d) | Document the rejection as the system's actual behavior — that's a positive finding, not a bug |
| Revert PATCH triggers a new state_sha that invalidates downstream artifacts unexpectedly | Likely the correct behavior; document the cascade |
| The PATCH endpoint's response shape varies between success-with-validation-errors and 4xx | Dogfood inspects both `status_code` + JSON body; document the actual envelope |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- M3.0 retro Open Question #3 (failure-path ergonomics)
- M3.0 retro Recommendation: "Bundle domain-aware form helpers +
  failure-path dogfood + log rotation as the engine-side workstream"
- User mandate 2026-05-24: 持续开发，自动执行下一步建议

Surface-scan-found: existing dogfood pattern
`scripts/dogfood/case_007_cycle1_form_helper.py` ·
disposition: extend-pattern (new dogfood script following same
TestClient + isolated tmpdir shape); no parallel-new framework, no
rename of existing scripts.
