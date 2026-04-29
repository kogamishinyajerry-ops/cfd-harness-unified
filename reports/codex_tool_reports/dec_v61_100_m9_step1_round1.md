Verdict: APPROVE_WITH_COMMENTS

No blocking findings for commit `24ba77d` in the current M9 Tier-B Step 1 dogfood scope (`?ai_mode=force_uncertain|force_blocked`, frontend-only). I reviewed the Step 3 wiring and tests, and ran:

```bash
(cd ui/frontend && npx vitest run src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx src/pages/workbench/step_panel_shell/__tests__/AnnotationPanel.test.tsx src/pages/workbench/step_panel_shell/__tests__/DialogPanel.test.tsx)
```

Result: `3` test files passed, `20` tests passed.

Comments

1. Face-pick routing is correct for the current single-active-question dogfood path, but it is intentionally lossy under rapid double-picks.
   Reference: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:121-140`, `ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx:36-41`
   `activeFaceQuestion` always targets the first unresolved face-selection question, and the shared `FacePickContext` holds only one `picked` value. If two viewport picks land before the effect consumes the first one, the later pick wins and the earlier one is silently overwritten. That does not break the current `force_uncertain` substrate because there is only one face-selection question per round, but it is a real assumption that should be preserved explicitly when this flow grows beyond single-question LDC dogfood.

2. Stale dialog state is mostly harmless today, but it depends on current backend behavior.
   Reference: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:81-88`, `:249-275`, `:297-349`, `:377-419`
   `pickedFaceIdForQuestion` is cleared only on the confident terminal path, and `envelope` is cleared only when legacy setup succeeds. For the present backend this is fine because the resumed envelope run drops the force flags and returns a confident payload, so stale question ids do not survive into another uncertain round. The same is true for your noted mid-session `ai_mode` toggle: the old envelope can stay rendered until the next legacy success, which is more of a UX oddity than a correctness problem. I would not block this commit on that, but once the real arbitrary-STL classifier can emit repeated or same-id follow-up questions, this state should be cleared more aggressively.

Focus checks

- Race conditions:
  The current pick-consumption logic is coherent for one active face question. It is not queue-backed, so rapid multi-pick input is last-write-wins rather than ordered delivery.
- `handleDialogResume` stale picked map:
  No current blocker. The code does not clear `pickedFaceIdForQuestion` on resume, but the present backend path returns a different terminal shape (`confident`, no questions), so stale entries do not interfere in this slice.
- Sticky invariant:
  Preserved. Both write paths send `annotated_by: "human"` and `confidence: "user_authoritative"` (`Step3SetupBC.tsx:155-159`, `:311-323`). I did not see an AI write path in this commit that can bypass that during resume.
- Error recovery:
  If `putFaceAnnotations` succeeds and the subsequent envelope rerun fails, the panel keeps the old uncertain envelope on screen, `annotations` stays updated to the new revision, and the user sees the retryable error surfaced through the dialog/global error path. That is not ideal UX, but it is recoverable and does not lose the committed annotation.
- Test coverage:
  The important happy path is covered, and the “resume without a face pick” negative is already pinned indirectly by `DialogPanel.test.tsx:82-121`, which keeps `[继续 AI 处理]` disabled until a face is selected. The only notable missing case is the post-PUT / pre-rerun failure path described above; I would treat that as follow-up hardening, not a merge gate.
