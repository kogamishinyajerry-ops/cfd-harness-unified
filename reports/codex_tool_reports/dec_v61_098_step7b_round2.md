# Pre-merge Review — DEC-V61-098 Step 7b Round 2

Verdict: **RESOLVED**

Reviewed commit: `f7fd833 fix(ai-copilot): Codex Step 7b round-1 closure (HIGH 409 conflict re-fetch)`
Prior round: `00c343d` (`reports/codex_tool_reports/dec_v61_098_step7b_round1.md`)

## Result

Round 1's HIGH finding is closed.

`Step3SetupBC.handleSaveAnnotation()` now recovers correctly from `409 revision_conflict`: it re-fetches the latest `/face-annotations` document, updates local state, and surfaces a retry message instead of leaving the panel stuck on a stale revision. On the next save attempt, the PUT uses the bumped revision and still sends `annotated_by: "human"`.

## Verification

1. 409 re-fetch / local-state update / bumped-revision retry

In [ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:94), the save path now catches `ApiError` 409s, calls `api.getFaceAnnotations(caseId)`, and commits the fresh document via `setAnnotations(fresh)` before surfacing a retry error message ([Step3SetupBC.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:116)). Because `handleSaveAnnotation` depends on `annotations`, the callback is recreated after that state update, so the next PUT reads `fresh.revision` rather than the stale one.

The new regression test proves the end-to-end behavior: first PUT rejects with attempted revision `3`, the re-fetch returns revision `5`, and the retry sends `if_match_revision: 5` ([ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:131)).

2. Sticky invariant preserved

The manual save path still hard-codes `annotated_by: "human"` in the PUT body ([Step3SetupBC.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:100)). The happy-path test pins that on the initial save, and the 409 regression test pins it again on the retry body ([Step3SetupBC.test.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:82), [Step3SetupBC.test.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:203)).

3. Clear panel error on conflict

`AnnotationPanel` already renders thrown save errors inline through `annotation-panel-error` ([ui/frontend/src/pages/workbench/step_panel_shell/AnnotationPanel.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/AnnotationPanel.tsx:64)). The new conflict message is explicit: `Revision conflict (was X, latest Y). Refreshed — please retry.` ([Step3SetupBC.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx:127)). The new frontend test asserts that the conflict message reaches the panel error surface ([Step3SetupBC.test.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx:179)).

4. Stable publisher dependency

`useFacePickPublisher()` no longer depends on the whole context object. It extracts `ctx?.setPicked` and uses `[setPicked]` as the `useCallback` dependency ([ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx:79)). Since `setPicked` comes from `useState`, this satisfies the Round 1 note about callback identity stability across pick/clear cycles.

## Test Runs

- `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_face_annotations_route.py` → `10 passed`
- `(cd ui/frontend && npx vitest run)` → `16 passed`, `123 passed`

## Findings

No blocking findings in this round.
