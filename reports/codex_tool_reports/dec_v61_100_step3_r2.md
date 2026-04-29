Verdict: CHANGES_REQUIRED

Finding 1
Status: NOT RESOLVED
Severity: MED
File: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:333-350`

What I verified:
- `aiModeGenRef` is present and bumps on `aiMode` changes (`Step3SetupBC.tsx:115-123`).
- `runEnvelope()` captures the generation token and guards the first post-`await` `setEnvelope(result)`, the post-refresh `setAnnotations(fresh)`, and the catch-path error writes (`Step3SetupBC.tsx:317-318`, `324-325`, `334-335`, `352-372`).
- Legitimate sequential runs within the same `ai_mode` are still allowed because the generation only changes on `aiMode` flips, not per request. The resume path still re-runs envelope mode successfully in the current tests (`ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:403-504`).

Remaining gap:
- `runEnvelope()` has a second async boundary at `const fresh = await api.getFaceAnnotations(caseId)` (`Step3SetupBC.tsx:334`).
- After that nested `await`, the code only guards `setAnnotations(fresh)` (`Step3SetupBC.tsx:335`), but it does not re-check `isStale()` before the confident completion block at `Step3SetupBC.tsx:341-350`.
- If `ai_mode` flips while that refresh is in flight, the stale request can still execute `setPickedFaceIdForQuestion({})` and `onStepComplete()` from the old mode. That means the round-1 MED finding is only partially closed.

Suggested fix:
- Re-check `isStale()` immediately after the annotation-refresh block and before the confident completion block, or wrap the completion block itself in an `if (!isStale())`.
- Add a regression test that returns a confident envelope with `annotations_revision_after !== annotations.revision`, holds `getFaceAnnotations()` pending, flips `ai_mode`, then verifies the stale request cannot complete the step or mutate dialog state.

Finding 2
Status: RESOLVED
File: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:186-210`, `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:595-610`

What I verified:
- Bare picks are now swallowed when the envelope still has unresolved face-selection questions but no active slot is selected (`Step3SetupBC.tsx:205-208`).
- The updated multi-question test now explicitly asserts `queryByTestId("annotation-panel")` is `null` after the no-active bare-pick path (`Step3SetupBC.test.tsx:595-610`).
- `AnnotationPanel` still surfaces outside the envelope-awaiting-face-selection state because the swallow branch is gated by `envelopeAwaitsFaceSelection`; otherwise the existing render path on `facePick?.picked` remains intact (`Step3SetupBC.tsx:186-210`, `566-574`). The existing annotation save-path tests still pass (`ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:93-219`).

Verification

```bash
cd ui/frontend
npx vitest run src/pages/workbench/step_panel_shell/__tests__/DialogPanel.test.tsx src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx
```

Result: `2` test files passed, `17` tests passed.

Overall M9 Step 3 status

`faa2e08` + `a54f4b7` are not ready to merge yet because Finding 1 remains open.
