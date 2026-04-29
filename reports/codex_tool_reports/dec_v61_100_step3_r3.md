Verdict: APPROVE

Finding count: 0

Scope

- Repo: `/Users/Zhuanz/Desktop/cfd-harness-unified`
- Branch: `main`
- Verified commits: `faa2e08` + `a54f4b7` + `6ae9a3b`
- Target file: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx`

Checks

1. Confident-path guard

- Verified at `Step3SetupBC.tsx:341-345`.
- The completion branch is now gated by all three conditions:
  - `!isStale()`
  - `result.confidence === "confident"`
  - `result.unresolved_questions.length === 0`

2. Post-await stale guards inside `runEnvelope`

- After `await api.setupBCWithEnvelope(...)`, the code immediately executes `if (isStale()) return;` before `setEnvelope(result)` (`Step3SetupBC.tsx:320-325`).
- After the nested `await api.getFaceAnnotations(caseId)`, the only state write is `if (!isStale()) setAnnotations(fresh)` (`Step3SetupBC.tsx:334-335`).
- The confident completion block now re-checks staleness before `setPickedFaceIdForQuestion({})` and `onStepComplete()` (`Step3SetupBC.tsx:341-354`).
- The catch path begins with `if (isStale()) return;` before any error-state write or `onStepError(...)` call (`Step3SetupBC.tsx:356-376`).

Conclusion: I did not find any remaining success-path or catch-path state write inside `runEnvelope` that can run after an `await` without an `isStale()` guard.

3. Sequential same-mode resume path

- `aiModeGenRef` only increments inside the `[aiMode]` effect (`Step3SetupBC.tsx:115-123`).
- `runEnvelope` captures `const generation = aiModeGenRef.current` at request start and compares against that same token on resolve (`Step3SetupBC.tsx:317-318`).
- When `aiMode` does not flip, the captured generation still matches at resolve, so the normal resume flow remains live.
- Existing test coverage already exercises the same-mode sequence `handleDialogResume -> runEnvelope({ useForceFlags: false }) -> onStepComplete` (`ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:403-504`).

Verification

```bash
cd /Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend
npm test -- --run src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx
```

Result

- `1` test file passed
- `7` tests passed
- `0` failures

Approval

`6ae9a3b` closes the Round 2 open finding. M9 Step 3 (`faa2e08` + `a54f4b7` + `6ae9a3b`) is ready to merge.
