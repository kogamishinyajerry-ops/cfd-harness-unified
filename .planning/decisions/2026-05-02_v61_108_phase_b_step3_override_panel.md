---
decision_id: DEC-V61-108-B
title: Step 3 per-patch BC classification override panel (Phase B · frontend wiring)
status: Accepted (2026-05-02 · Codex APPROVE on R3 commit f6d40e1 after 3 rounds R1-R3)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-02
authored_under: |
  user direction "全权授予你开发，全都按你的建议来" + standing strategic target
  "实现 CFD 仿真操作工作台, 能处理任意的 CAD 几何 (人工可以自由选中编辑,
  AI 可以进行辅助操作)". Phase B is the frontend half of DEC-V61-108 — the
  Step 3 panel that lets the engineer actually use the per-patch override
  store DEC-V61-108-A built.
parent_decisions:
  - DEC-V61-108-A (Per-patch BC override store · this DEC consumes the GET/PUT/DELETE routes)
  - DEC-V61-098 (M-AI-COPILOT collab · provides the FacePickContext substrate that drives picked-patch highlighting)
  - DEC-V61-096 (M-PANELS shell kickoff · provides the Step 3 mount point)
  - RETRO-V61-001 (risk-tier triggers · multi-file frontend change + new API contract surface = mandatory Codex review)
parent_artifacts:
  - ui/frontend/src/api/client.ts (3 new fetch wrappers)
  - ui/frontend/src/pages/workbench/step_panel_shell/types.ts (3 new types matching backend schema)
  - ui/frontend/src/pages/workbench/step_panel_shell/PatchClassificationPanel.tsx (NEW · the panel itself)
  - ui/frontend/src/pages/workbench/step_panel_shell/__tests__/PatchClassificationPanel.test.tsx (NEW · 11 vitest cases)
  - ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx (mount site)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 55% (anticipated React state-sync rough edges; expected ~2 rounds to APPROVE)
actual_pass_rate: ~33% (Codex required 3 rounds — under-calibrated by ~0.20; root cause: my R1 closure introduced a single-token model that conflated case-invalidation with mutation-ordering, requiring R2 → R3 to split into dual-token model)
codex_tool_report_path: reports/codex_tool_reports/v61_108_phase_b_r1_r3_chain.md (R1-R3 full chain)
implementation_commits:
  - 4f1dd6c (feat: Step 3 override panel · initial)
  - c7cb785 (R1 P1+P2+P3 closure · single stateGenRef + key={caseId} + ApiError.detail formatting)
  - f6d40e1 (R2 P1+P3 closure · dual-token split caseGenRef vs saveSeqRef/committedSeqRef)
  - 2b34191 (R1-R3 chain report)
notion_sync_status: synced 2026-05-02 (https://www.notion.so/354c68942bed81a4b547c4b80e459e9a)

# Why now

DEC-V61-108-A shipped the backend store but it only ever populates
from out-of-band scripts until a frontend surface exists. The
"human can freely select+edit" half of the workbench charter is
materially blocked without this DEC. Phase B is the smallest
shippable unit that turns the override store into a usable feature.

# Decision

New `PatchClassificationPanel` component renders below Step 3's
setup-bc surface. Lists every patch in `polyMesh/boundary` with
two columns:
- "Auto" — what the heuristic emits WITHOUT the override layer
- "Override" — what the engineer has saved

Each row has a dropdown to set/clear the override. When the engineer
picks a face in the Viewport AND the picked face's patch can be
resolved via `FaceIndexDocument`, that row highlights so the user
sees "this is the patch you just clicked".

Concurrency model (final, post-R2 closure):
- `caseGenRef`: bumped on caseId change. Used by initial-GET load +
  getFaceIndex (case-scoped fetches; saves must NOT invalidate them).
- `saveSeqRef`: monotonic counter; bumped on every save dispatch
  to mint mySeq.
- `committedSeqRef`: highest save-seq actually applied to state.
  Save commits iff (caseGen unchanged) AND (mySeq > committedSeq).
  Failed saves leave committedSeq untouched, so an older save
  that succeeds later can still land.

Mounted as `<PatchClassificationPanel key={caseId} ... />` in
Step3SetupBC so a React Router caseId swap forces full remount.

# Codex narrative

R1: 4 valid findings — race on parallel edits; caseId-stale state
without key prop; missing concurrency tests; load-error path
collapses ApiError.detail.

R1 closure: single-token stateGenRef model + key={caseId} +
formatApiErrorDetail helper + 2 concurrency regression tests.

R2: my R1 closure introduced 2 follow-on bugs. The single token
conflated two concerns:
- Case/unmount invalidation (when caseId changes, drop everything
  from old case)
- Mutation ordering (when newer save issued, drop older save's
  response)

The bug: if A is in flight, B issued (bumps gen), B FAILS but A
SUCCEEDS — A's success is dropped because gen has moved past A.
The backend has A's update persisted but UI doesn't reflect it.
Same conflation strands an in-flight face-index GET if a save
happens before it resolves.

R2 closure: dual-token split (caseGenRef vs saveSeqRef +
committedSeqRef) + 2 new regression tests ("commits an older
save's response after a newer save fails", "preserves faceIndex
when a save lands before it resolves").

R3 APPROVE: zero findings. Codex confirmed the dual-token model
fully closes both R2 P1 and R2 P3 without regressing R1's
protections.

# Verification

- 11 PatchClassificationPanel vitest cases (4 happy + 4 corner +
  3 concurrency regressions)
- 165/165 frontend vitest passing on initial commit
- 109/109 shell tests passing on R2 closure
- tsc --noEmit clean on every commit
- 0 post-R3 defects

# Future work

The patch_classification panel is now production-quality from a
concurrency standpoint. Open opportunities (not blocked by this DEC):
- Bulk operations (one-click "set all unannotated to no_slip_wall")
- if_match_revision conflict surfacing for multi-browser editing
- Reverse highlight: clicking a row in the panel highlights the
  corresponding patch in the viewport (requires plumbing through
  FacePickContext + viewport selection state)
