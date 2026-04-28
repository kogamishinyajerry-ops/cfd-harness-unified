# M-PANELS arc · Codex review · Round 1 (DEC-V61-096)

**Date**: 2026-04-28
**Session**: `019dd36b-bfda-78a3-8f2c-a0abd7899e4e`
**Source rollout**: `~/.codex/sessions/2026/04/28/rollout-2026-04-28T17-29-07-019dd36b-bfda-78a3-8f2c-a0abd7899e4e.jsonl`
**Reviewer**: Codex GPT-5.4 (xhigh) — pre-merge per RETRO-V61-001 (DEC-V61-096 self-rated 60% ≤ 70% gate)
**Commit range**: `08b0d16..d25e365` (Steps 2–6 of M-PANELS Tier-A implementation arc)

## Verdict

`CHANGES_REQUIRED` — 2 P2 findings, 0 P1, 0 P3.

## Findings

### Finding 1 [P2]: Step-tree navigation stays live while the non-abortable mesh run is in flight

**File**: `ui/frontend/src/pages/workbench/StepPanelShell.tsx:244`

**Issue**: The left `StepTree` stays clickable even when `aiInFlight` is true, so a user can leave Step 2 while `api.meshImported(...)` is still running. That request is not abortable and `Step2Mesh` still updates local component state after the awaited call returns (`ui/frontend/src/pages/workbench/step_panel_shell/steps/Step2Mesh.tsx:45-75`). The result is a muddled state model: the shell keeps running the old action, the Step 2 body is gone, and the success/rejection panel is discarded if the user returns later.

**Suggested fix**: Either lock step-tree navigation while `aiInFlight` is true, or make the mesh trigger cancellation-safe and persist its result outside the component-local state. The minimal patch is to pass `aiInFlight` into `StepTree` and disable its buttons during mesh execution.

### Finding 2 [P2]: Step 2 AI button is enabled before its action is actually registered

**File**: `ui/frontend/src/pages/workbench/StepPanelShell.tsx:293`

**Issue**: The shell enables `[AI 处理]` purely from `activeStep.aiActionWiredInTierA`, but the real Step 2 action is only installed later via `registerAiAction(triggerMesh)` in a passive effect (`ui/frontend/src/pages/workbench/step_panel_shell/steps/Step2Mesh.tsx:72-75`). In that gap, `onAiProcess` exists but `activeAiActionRef.current` is still `null`, so the first click becomes a silent no-op (`StepPanelShell.tsx:295-296`). The current shell test only checks that the button is enabled; it never clicks through the full shell path, so this race is untested (`ui/frontend/src/pages/workbench/step_panel_shell/__tests__/StepPanelShell.test.tsx:154-164`).

**Suggested fix**: Gate the enabled state on actual action registration, not just on step metadata. For example, track a shell-level `hasRegisteredAiAction` boolean alongside the ref, or have Step 2 register in a layout effect. Add a full-shell integration test that navigates to Step 2 and clicks `[AI 处理]` through `StepPanelShell`, not just the isolated `Step2Mesh` body.

## Round-2 fix lineage

Both findings addressed in commit `060d25b` (`fix(panels): M-PANELS Round-2 Codex fixes (DEC-V61-096)`):

- F1 → `StepTree` gains `disabled?: boolean` prop; shell threads `aiInFlight` in. Per-row `disabled` + `data-disabled` attribute. New `StepTree.test.tsx` unit + `StepPanelShell.test.tsx` integration cover the lock + unwind.
- F2 → `hasRegisteredAiAction` state flag in shell, set by `registerAiAction`. `onAiProcess` gated on both `aiActionWiredInTierA && hasRegisteredAiAction`. New `StepPanelShell.test.tsx` integration clicks `[AI 处理]` through the shell and asserts `api.meshImported` fires.

Tests: 96 → 100 passing. Bundle unchanged (353.88 KB gz main + 191.59 KB gz Viewport chunk).
