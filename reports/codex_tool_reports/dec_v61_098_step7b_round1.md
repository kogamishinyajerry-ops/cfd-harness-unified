# Pre-merge Review — DEC-V61-098 Step 7b Round 1

Verdict: **CHANGES_REQUIRED**

Reviewed commit: `00c343d feat(ai-copilot): Step 7b — FacePickContext + Step3SetupBC integration`

## Findings

### HIGH — stale annotation revision becomes unrecoverable after any concurrent write
File: [ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:93)

`handleSaveAnnotation()` always sends `if_match_revision: annotations.revision` from the one-time GET state loaded at mount, and only updates local state on the success path. If a concurrent writer bumps the document revision after that GET — the exact race this review asked about, including another `[AI 处理]` path or a second client — the PUT correctly returns `409 revision_conflict`, but this component never re-fetches or updates `annotations` on that failure path.

Result: the panel is stuck on the stale revision forever. Clicking `Save` again repeats the same stale `if_match_revision`, so the engineer cannot recover without a full remount / page refresh. That is a correctness bug, not just missing UX polish, because Step 7b is explicitly wiring human edits onto a revisioned document with concurrent AI writes in scope.

Expected fix: on `409`, refresh `/face-annotations` (or fold the latest revision from the error/retry flow into local state) before allowing retry. The retry path should preserve the sticky invariant by continuing to send `annotated_by: "human"`.

## Notes

- `annotated_by="human"` is wired correctly on the manual save path ([Step3SetupBC.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:98)); that preserves the backend sticky rule for `user_authoritative` faces.
- `StepPanelShell` gates `pickMode` correctly to Step 3 only, and only after `stepStates[3] === "completed"` ([StepPanelShell.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/StepPanelShell.tsx:402)). Non-pick steps still render through the transparent wrapper, and the existing shell tests stayed green.
- Navigation away from Step 3 does not leak pick handling into other steps: `Viewport` clears the kernel pick handler whenever `pickMode` becomes false ([Viewport.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/Viewport.tsx:217)). The selected face remains provider-scoped state, so returning to Step 3 restores the pending pick rather than publishing into Steps 1/2/4/5.
- Minor follow-up, not a blocker for this round: `useFacePickPublisher()` is wrapped in `useCallback`, but its dependency is the whole context object ([FacePickContext.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx:73)), and that object is recreated whenever `picked` changes ([FacePickContext.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx:36)). So the callback is not actually identity-stable across picks/clears. This does not currently resubscribe the VTK handler because `Viewport` reads `onFacePick` through a ref and its effect does not depend on handler identity, but it does not satisfy the stated “stable callback” goal literally.

## Verification

- `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_face_annotations_route.py ui/backend/tests/test_face_index.py ui/backend/tests/test_case_annotations.py` → `47 passed`
- `(cd ui/frontend && npx vitest run)` → `15 passed`, `121 passed`
