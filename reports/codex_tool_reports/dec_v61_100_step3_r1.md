Verdict: CHANGES_REQUIRED

Finding 1
Severity: MED
File: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:109-113`, `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:282-317`
Root cause: the new `useEffect([aiMode])` cleanup only clears local state; it does not invalidate an older `runEnvelope()` request that was started under the previous `ai_mode`. If the engineer flips `?ai_mode=` while `setupBCWithEnvelope()` is still in flight, the stale promise still reaches `setEnvelope(result)` and can still call `onStepComplete()`. That recreates exactly the stale-mode surface this commit is trying to remove: an old envelope or old success state can reappear after the mode was changed.
Suggested fix: give each envelope run a request-generation token (or abort/cancel signal) tied to the current `aiMode`, and ignore late results/errors/completions once the mode changes. The same guard should cover `setEnvelope`, `setRejection`, `setNetworkError`, and `onStepComplete`.

Finding 2
Severity: LOW
File: `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:166-182`, `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:526-533`, `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:595-620`
Root cause: in the new multi-question flow, a viewport pick with no active slot is no longer auto-routed to a dialog question, but it is still left in `FacePickContext` and therefore still renders `AnnotationPanel`. The new integration test proves only that neither dialog hint gets a `picked:` value; it would still pass while this extra write surface appears. That makes “multi-q always requires explicit click” only half true in practice, because a stray pick still opens a different mutation path.
Suggested fix: while an unresolved face-question envelope is open and `activeFaceQuestion` is `null`, swallow or clear bare picks instead of surfacing `AnnotationPanel`, and extend the test to assert that `annotation-panel` stays absent on the no-active path.

Checklist notes

- [A] Pass for the current dialog round. `activeFaceQuestion` only auto-falls back when the current envelope contains exactly one face-selection question and that slot is still unpicked (`Step3SetupBC.tsx:157-162`). Because answered slots stay inside `envelope.unresolved_questions` until resume, the “two questions become one after the first pick” fallback does not reappear inside the same round.
- [B] Not fully closed because of Finding 1. Within a stable `aiMode`, legitimate envelope updates are fine; the remaining race is specifically “mode changed while request was in flight.”
- [C] Pass. `DialogPanel` renders `Active` first, then `Re-pick`, then `Select this face`, and active rows are disabled even when the slot already has a picked face (`DialogPanel.tsx:177-225`).
- [D] Treated as a leak, not intended product behavior, for the reasons in Finding 2.
- [E] Partial pass. The test does exercise the no-auto-route branch, but it does not prove the branch is side-effect free because it never checks whether `AnnotationPanel` appeared.
- [F] Pass. The new `data-testid`s use the `dialog-panel-*` prefix (`DialogPanel.tsx:187-216`).

Verification

```bash
cd ui/frontend && npx vitest run src/pages/workbench/step_panel_shell/__tests__/DialogPanel.test.tsx src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx
```

Result: `2` test files passed, `17` tests passed.
