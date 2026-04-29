---
decision_id: DEC-V61-098
title: M-AI-COPILOT (collab-first) kickoff — human-AI collaboration layer for arbitrary-STL workflows (4 interaction primitives + face-pick + face_annotations.yaml + AI uncertainty envelope; merges deferred M-PANELS.advanced face-pick) [fourth milestone under Pivot Charter Addendum 3]
status: Active (2026-04-29 · CLASS-1 docs-only governance kickoff per V61-094/095/096 precedent · Codex SKIPPED at kickoff [will fire pre-merge per RETRO-V61-001 ≤70% self-pass-rate gate during implementation arc Step 8 of spec_v2 §E] · Kogami NOT triggered per V61-094 P2 #1 bounding clause [4-condition self-check passes: no charter mod · workbench/** + visualization/** already line-A · counter <20 since RETRO-V61-005 · no risk-tier change] · CFDJerry explicit ratification 2026-04-29 "很好，按照你的理解和建议，执行")
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-29
authored_under: Pivot Charter Addendum 3 §3 (product-interaction hard constraint) + §4.a (M-AI-COPILOT surface) + §4.c HARD ORDERING (DEC-V61-093 Accepted 2026-04-28 · M-VIZ → M-RENDER-API → M-PANELS → **M-AI-COPILOT** → M7-redefined → M8-redefined)
parent_decisions:
  - DEC-V61-093 (Pivot Charter Addendum 3 ratification · binding parent — §3 + §4.a + §4.c)
  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · the demo that exposed the collab-first gap motivating this milestone)
  - DEC-V61-096 (M-PANELS Tier-A · binding parent — kickoff precedent + framing inheritance + Step 4 task-panel surface this milestone extends)
  - DEC-V61-095 (M-RENDER-API kickoff · framing precedent · closed 2026-04-28 commit 3acdf14)
  - DEC-V61-094 (M-VIZ kickoff · framing precedent + P2 #1 bounding clause this milestone inherits · closed 2026-04-28 commit 36c4a78)
  - DEC-V61-087 (v6.2 three-layer governance · NOT modified)
  - DEC-V61-088 (pre-implementation surface scan · routine startup discipline)
  - DEC-V61-089 (two-track invariant · workbench frontend serves both tracks)
  - RETRO-V61-001 (risk-tier triggers · multi-file frontend + new API contract + UX-driven impl + ≤70% self-pass triggers PRE-MERGE Codex)
parent_artifacts:
  - docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md (charter binding · §3 + §4.a + §4.c)
  - .planning/strategic/m_ai_copilot_kickoff/brief_2026-04-29.md (one-pager · 4 interaction primitives + 3 user stories + Tier scope)
  - .planning/strategic/m_ai_copilot_kickoff/spec_v2_2026-04-29.md (Tier-A scope table A1-A12 + face_annotations.yaml schema + AIActionEnvelope + face_id hash + 11-step sequence)
  - .planning/strategic/m_panels_interactive_face_naming_2026-04-28.md (the deferred Tier-B candidate now absorbed into M-AI-COPILOT Tier-A · CFDJerry M-VIZ Step-7 ask)
implementation_paths:
  - ui/backend/services/case_setup/face_annotations.py (NEW · YAML reader/writer + face_id hash + revision counter)
  - ui/backend/services/case_setup/ai_envelope.py (NEW · AIActionEnvelope + UnresolvedQuestion Pydantic schemas)
  - ui/backend/services/case_setup/setup_bc_runner.py (MODIFIED · returns AIActionEnvelope; reads face_annotations.yaml; emits blocked when ambiguous)
  - ui/backend/routes/case_setup.py (MODIFIED · /setup-bc returns envelope; new /face-annotations GET/PUT routes)
  - ui/backend/tests/test_face_annotations.py (NEW · face_id stability under polyMesh regen + round-trip + revision)
  - ui/backend/tests/test_ai_envelope.py (NEW · envelope schema validation + blocked/uncertain/confident transitions)
  - ui/frontend/src/visualization/Viewport.tsx (MODIFIED · pickMode prop + vtkCellPicker integration + hover/click/shift-click handlers)
  - ui/frontend/src/visualization/FacePickOverlay.tsx (NEW · floating annotation panel anchored to click position)
  - ui/frontend/src/pages/workbench/step_panel_shell/Step3Setup.tsx (MODIFIED · dialog panel split + UnresolvedQuestion checklist + [继续 AI 处理] re-run)
  - ui/frontend/src/pages/workbench/step_panel_shell/types.ts (MODIFIED · awaiting_user step state + AIEnvelope + UnresolvedQuestion frontend types)
  - ui/frontend/src/api/client.ts (MODIFIED · faceAnnotations endpoints + setupBc envelope return type)
  - ui/frontend/src/pages/workbench/step_panel_shell/StepPanelShell.tsx (MODIFIED · awaiting_user state + status-strip "AI is waiting for: N questions" hint)
read_paths:
  - reports/codex_tool_reports/dec_v61_097_phase_1a_round{1,2,3,4}.md (Codex precedent reference for arc-size discipline + verbatim-exception path)
  - .planning/dogfood/M_PANELS_v0.md (closure pattern reference if exists)
  - .planning/strategic/m_panels_kickoff/spec_v2_2026-04-28.md (Step 4 task-panel surface this milestone extends)
prerequisite_status:
  v61_097_acceptance: confirmed (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · Step 3 interactive 3D BC viewport + rAF residual chart batching landed)
  v61_096_acceptance: confirmed (M-PANELS Tier-A · closed 2026-04-28 commit 5b21df5 · 4-round Codex APPROVE · three-pane shell + 5-step tree + button contract live)
  v61_094_acceptance: confirmed (M-VIZ closed · Step-7 visual smoke PASSED · Viewport supplies pickMode extension surface)
  v61_093_acceptance: confirmed (Pivot Charter Addendum 3 §3 + §4.a + §4.c binding)
  line_a_contract: confirmed (workbench/** + visualization/** + ui/backend/services/case_setup/** all line-A · NO new ROADMAP extension needed for M-AI-COPILOT Tier-A)
  m_render_api_endpoints: confirmed (geometry/render + mesh/render + results/{run}/field/{name} all live · face_id surfaces from polyMesh data already exposed via mesh/render)
  break_freeze_quota: confirmed (current count 2/3 from M-VIZ Step 6 e453ba0 + M-PANELS arc · M-AI-COPILOT Tier-A consumes the FINAL slot taking total to 3/3 · accounted in spec_v2 §F · post-arc the dogfood window's quota is exhausted; subsequent workbench/** changes route through normal feature freeze)
notion_sync_status: synced 2026-04-29 (DEC https://app.notion.com/p/351c68942bed81719f85d72415d1252d · brief sub-page https://app.notion.com/p/351c68942bed8171a159debd91518db3 · spec_v2 sub-page https://app.notion.com/p/351c68942bed81378b26e509120f2583 · placement inherits V61-094/V61-095/V61-096 P3 #5 precedent)
autonomous_governance: true
library_choice: React + React Router + Tailwind (existing) · @kitware/vtk.js Viewport from M-VIZ (extends with vtkCellPicker · already a sibling import in vtk.js core) · @tanstack/react-query for envelope state · pyyaml for face_annotations.yaml read/write (existing dep · used elsewhere in case_setup) · NO new UI component library / state-management library / 3D library
codex_tool_report_path:
  round_1: pending (will land at reports/codex_tool_reports/2026-04-XX_m_ai_copilot_arc_codex_review_round1.md after spec_v2 §E Step 8)
codex_review_required: true
codex_review_phase: pre-merge (RETRO-V61-001 ≤70% self-pass gate · NOT post-merge)
codex_triggers:
  - 多文件前端改动 (>5 new/modified files: Viewport pickMode + FacePickOverlay + Step3Setup dialog + types + StepPanelShell + client)
  - 多文件后端改动 + 新 API 契约 (face_annotations.yaml schema + AIActionEnvelope · 2 new persistent contracts)
  - UI 交互模式变更 (autonomous AI button → bidirectional dialog with awaiting_user step state · structurally novel)
  - 用户 UX 批评后的首次实现 (CFDJerry 2026-04-29 collab-first insight + Pivot Charter Addendum 3 §3 product-interaction hard constraint)
  - ≤70% self-pass-rate (50% per spec_v2 §self-pass-rate · triggers pre-merge per RETRO-V61-001)
  - 跨 ≥3 文件的 API schema (新 envelope + face_annotations 跨 setup_bc_runner / case_setup 路由 / frontend client / types)
kogami_review:
  required: false
  rationale: |
    Per V61-094 Kogami review P2 #1 bounding clause (Accepted
    2026-04-28): "M-RENDER-API / M-PANELS / M-AI-COPILOT inherit
    M-VIZ's framing precedent and do NOT re-fire Kogami unless they
    independently meet a Must-trigger condition (charter modification ·
    line-A contract extension beyond M-VIZ's claim · counter ≥20 ·
    explicit risk-tier change)."

    Self-check (4 conditions, all NO):
    1. Charter modification? NO. Inherits Addendum 3 §3 + §4.a + §4.c
       verbatim. M-AI-COPILOT executes the §3 product-interaction
       hard constraint as already-ratified — specifically the
       "human-in-the-loop when AI is uncertain" sub-promise that
       M-PANELS Tier-A and Phase-1A LDC demo exposed as the gating
       requirement for arbitrary-STL workflows.
    2. Line-A contract extension beyond M-VIZ? NO.
       `ui/frontend/src/pages/workbench/**` line-A predates V61-094.
       `ui/frontend/src/visualization/**` line-A in commit 8fdb0a3
       PRE-M-VIZ. `ui/backend/services/case_setup/**` already line-A
       in ROADMAP §"Line-A / Line-B isolation contract" since
       pre-V61-094. All 3 paths covered. NO new line-A claim.
    3. Counter ≥20 since RETRO-V61-005? NO. Counter currently 62
       after V61-097 close-out. M-AI-COPILOT kickoff brings it to
       63. Δ since RETRO-V61-005 = 12. Below 20-trigger threshold.
    4. Explicit risk-tier change? NO. Same risk class as M-PANELS
       (multi-file frontend + UX-critique-driven impl + new API
       contract). 50% self-pass-rate triggers PRE-MERGE Codex per
       RETRO-V61-001, NOT a Kogami strategic review tier change.
       The 50% (vs M-PANELS 60%) reflects DOGFOOD difficulty
       within the same risk tier, not a tier escalation.

    All 4 NO → Kogami NOT TRIGGERED. CFDJerry ratification of THIS
    DEC ("很好，按照你的理解和建议，执行" 2026-04-29) is the
    strategic gate.

    Important note: M-AI-COPILOT is the LAST milestone in the
    Addendum 3 §4.c hard ordering before M7/M8 redefinition. It is
    also the milestone that defines the human-AI dialog contract
    that all future milestones inherit. If CFDJerry wants Kogami
    strategic review on this kickoff specifically (overriding the
    bounding clause), he can request it pre-merge — it would not
    change Kogami's "not automatically triggered" status but would
    land as an ad-hoc-strategic-clearance run with its own audit
    trail at `.planning/reviews/kogami/m_ai_copilot_kickoff_2026-04-29/`.
break_freeze_required: true
break_freeze_rationale: |
  Per Pivot Charter Addendum 3 §5 选项一: workbench/** +
  visualization/** + case_setup/** edits in M-AI-COPILOT Tier-A
  consume the FINAL §11.1 BREAK_FREEZE quota slot (2/3 → 3/3).
  Each implementation commit touching these paths carries the
  `BREAK_FREEZE: rationale=Addendum 3 §3 binding (M-AI-COPILOT · DEC-V61-098)`
  trailer. Quota ledger maintained in spec_v2 §F. Counter:
  2/3 used (M-VIZ Step 6 e453ba0 + M-PANELS arc) →
  3/3 after M-AI-COPILOT arc closes. POST-ARC: dogfood window's
  quota EXHAUSTED; M7-redefined / M8-redefined and any subsequent
  workbench/** changes route through normal feature freeze (no
  per-PR escape clause).
self_estimated_pass_rate: 50
self_estimated_pass_rate_calibration: |
  -10% vs M-PANELS Tier-A (60%) and -5% calibrated against V61-097
  actual (4 rounds against 55% predicted, drift -55%) because:
  - human-AI dialog state machine has more failure modes than
    rAF-batched residual chart (multi-step user-AI ping-pong,
    annotation_revision race against in-flight AI runs, blocked
    state recovery semantics)
  - face_id stability across mesh regen is novel — vertex-set hash
    relies on `gmshToFoam` determinism; one corner case (vertex
    re-ordering, rounding drift) ripples into wrong-face annotation
    on the user's screen
  - TWO new persistent contracts (`face_annotations.yaml` schema
    + AIActionEnvelope) doubled compared to V61-097 (which had
    one: SSE preflight envelope). Each contract is a Codex
    surface area.
  - vtk.js cell-picker introduces a new failure axis (picker
    latency at 25k LDC cells should be sub-frame; arbitrary STL
    not in Tier-A scope but Codex will probe perf assumptions)
  - Tier-B arbitrary-STL is gated by Tier-A correctness —
    a single missed corner case in the dialog state machine
    (e.g., user navigates away mid-blocked-state) blocks the
    whole next milestone
  - the 4-interaction-primitive integration surface is structurally
    novel: signal + pick + persist + dialog must compose
    coherently, and Codex will probe the seams
  Per RETRO-V61-001: ≤70% triggers PRE-MERGE Codex review (not
  post-merge). M-AI-COPILOT pre-merge Codex is mandatory.
  Calibration log: V61-097 self-estimated 55%, actual 4 rounds
  (drift -55%); V61-098 calibrates -5% to 50% reflecting (a)
  larger contract surface area than V61-097 and (b) novel state
  machine vs V61-097's mostly-mechanical preflight extraction.
counter_v61: 63
counter_v61_delta_since_retro: 12  # since RETRO-V61-005
---

## Decision

**Ratify M-AI-COPILOT (collab-first) kickoff** as a CLASS-1 docs-only
governance kickoff:
- Tier-A scope = the 4 interaction primitives wired end-to-end on the
  LDC + simple-cube fixture (single-PR scope):
  1. AI uncertainty signal (`confidence` enum + `unresolved_questions[]`)
  2. 3D viewport face-pick (vtk.js cell-picker + face_id stable hash)
  3. Annotation persistence (`face_annotations.yaml` per case-dir)
  4. Bidirectional dialog panel (Step 4 task-panel split into action
     zone + question checklist + `[继续 AI 处理]` re-run)
- M-PANELS.advanced face-pick (deferred from V61-096) is **MERGED**
  into M-AI-COPILOT Tier-A per the brief §"Why now" architectural
  insight: face-pick is the channel for the human to answer the AI's
  questions; doing the milestones sequentially would mean shipping
  AI escalation hooks against a UI surface that doesn't exist yet
- One AI demonstration: Step 3 (Setup BC) on the LDC fixture **forced**
  into a `blocked` state via a flag, so we can dogfood the dialog flow
  without arbitrary STL (Tier-B candidate)
- Tier-B (arbitrary STL with rule-based AI) deferred to next milestone
  candidate; Tier-C polish (multi-select drag, undo/redo, annotation
  diff viz) deferred to M-PANELS.advanced.polish or M7+
- No new dependencies (React + React Router + Tailwind + vtk.js
  + react-query + pyyaml · all already in stack)
- No new ROADMAP line-A extension (workbench/** + visualization/**
  + case_setup/** already declared line-A)
- New backend endpoints: `/face-annotations` GET/PUT (under
  `/cases/{case_id}/`); existing `/setup-bc` return type extended to
  `AIActionEnvelope` (additive — old `confident`-only callers continue
  to work as a degenerate envelope)
- §11.1 BREAK_FREEZE: 1 slot consumed (2/3 → 3/3 · FINAL slot per
  Addendum 3 §5 选项一); post-arc the dogfood window's quota is
  exhausted
- Codex PRE-MERGE review per RETRO-V61-001 ≤70% self-pass-rate gate
  (50% reflects 2 new contracts + dialog state machine novelty)
- Kogami NOT triggered per V61-094 P2 #1 bounding clause (4-condition
  self-check passes)
- Path A engagement Gate-4 unlocks at M-AI-COPILOT Tier-A merge
  (arbitrary-STL recruit demos can now route to face-pick when AI
  blocks)

## Why this kickoff DEC is needed

This DEC ratifies (a) the implementation plan; (b) the merging of
M-PANELS.advanced face-pick into M-AI-COPILOT Tier-A; (c) the
2-new-persistent-contracts decision (`face_annotations.yaml` +
`AIActionEnvelope`); (d) the Codex pre-merge gate trigger condition;
(e) the FINAL §11.1 BREAK_FREEZE quota slot consumption; and (f) the
Kogami bounding-clause self-check pass.

CFDJerry's 2026-04-29 architectural insight is the binding rationale:

> 任意STL的AI处理非常困难，必须有一套优秀的人机交互机制，确保AI在
> 完全不知道怎么办的情况下，可以及时获取人类工程师的指导，人类工程
> 师也可以自己对渲染出来的CAD模型进行点击、编辑、命名……

This refutes two simpler framings prior milestones implicitly assumed:
1. **"AI alone can drive the workflow"** — M-PANELS Tier-A's
   `[AI 处理]` button suggests an autonomous step. The LDC fixture
   works because lid/walls/front-back patches are knowable by
   axis-aligned face geometry. For an arbitrary STL with N
   inlet/outlet/wall surfaces, no purely-geometric heuristic
   disambiguates them — the AI must ask.
2. **"Face picking is a polish item"** — V61-096 deferred face-pick
   to M-PANELS.advanced. But without face-pick, there is no channel
   for the human to answer the AI's questions. M-PANELS.advanced
   was the missing primitive, not a nice-to-have.

So M-AI-COPILOT and the deferred M-PANELS.advanced face-pick **must
merge**. Doing them sequentially would mean shipping AI escalation
hooks against a UI surface that doesn't exist yet, then doing the
surface, then re-wiring.

## The four Tier-A scope decisions that materially constrain implementation

1. **`face_annotations.yaml` is the user-authoritative SSOT**.
   Subsequent AI steps MUST read this file before deciding;
   `user_authoritative` entries override AI guesses. The file lives in
   `<case_dir>/face_annotations.yaml` and travels with import / export
   / audit packages. This eliminates ambiguity about precedence — the
   user always wins on a per-face basis.

2. **`face_id` is a vertex-set hash, not a face index**.
   Face indices change under mesh regen. `face_id = "fid_" +
   sha1(repr(sorted(round(coords, 9 decimals))))[:16]` survives regen
   as long as topology doesn't change. Codex will probe `gmshToFoam`
   determinism in round 1; if deterministic, this contract holds.

3. **`annotation_revision` is the AI staleness guard**.
   If user is editing annotation while AI is mid-run, the AI's answer
   arrives stale. Every AI envelope includes the revision it ran
   against; frontend rejects envelopes with stale revisions. Mirrors
   V61-097's `genRef` pattern in SolveStreamContext.

4. **`awaiting_user` is a first-class step state**, not a flag**.
   Step state machine: `idle → ai_running → confident | uncertain |
   awaiting_user(blocked) → ai_running (after [继续 AI 处理]) → ...`.
   Status strip surfaces "AI is waiting for: N face labels" hint.
   This is not a modal — user can navigate to other steps and come
   back; the awaiting_user state persists as case metadata.

## Pre-implementation surface scan (per DEC-V61-088)

Spec_v2 §E Step 1 will execute this in detail. Top-level checks
already verified for the kickoff:

1. **ROADMAP line-A coverage**:
   - `ui/frontend/src/pages/workbench/**` line-A row exists ✓
   - `ui/frontend/src/visualization/**` declared line-A in commit
     8fdb0a3 (PRE-M-VIZ) ✓
   - `ui/backend/services/case_setup/**` declared line-A
     pre-V61-094 ✓
   - **No new ROADMAP extension needed** for M-AI-COPILOT Tier-A.

2. **Existing-implementation grep targets (verify in spec_v2 §E
   Step 1)**:
   - `vtk.js` cell-picker import path — confirm `@kitware/vtk.js/Rendering/Core/CellPicker`
     resolves; if not, add to package.json (single-PR · line-A)
   - existing `face_id` references — confirm none collide with the
     new hash naming (greenfield contract)
   - `pyyaml` already imported in case_setup — confirm via `grep -r
     "import yaml" ui/backend/services/case_setup/`
   - `awaiting_user` step state — confirm not already used by
     M-PANELS Step state machine

3. **§11.1 BREAK_FREEZE quota check**:
   - Current count: 2/3 (M-VIZ Step 6 commit e453ba0 +
     M-PANELS arc 5b21df5 + Phase-1A c49fd11 ROLLED INTO
     M-PANELS arc per V61-097)
   - M-AI-COPILOT Tier-A: will consume 1 slot for the entire arc
     (all workbench/** + visualization/** + case_setup/** edits
     bundled per spec_v2 §E sequence)
   - Projected post-arc: **3/3 · QUOTA EXHAUSTED**
   - Forward note: NO milestone after M-AI-COPILOT may invoke
     §11.1 BREAK_FREEZE; M7-redefined / M8-redefined and beyond
     route through normal feature freeze. Quota EOL is a hard
     governance boundary.

4. **Forward note for M7-redefined / M8-redefined**:
   - M7-redefined: rule-based AI for arbitrary STL (Tier-B); reads
     `face_annotations.yaml` to seed its priors
   - M8-redefined: invites stranger dogfood ON THE COLLAB FLOW;
     M-AI-COPILOT Tier-A's blocked → answered → re-run dialog is
     the surface they evaluate

## Open questions (pre-impl scan will close)

1. **face_id stability**: vertex-set hash works as long as
   `gmshToFoam` is deterministic. Probable yes; verify with a regen
   test in spec_v2 §E Step 3 (test_face_id_stability).
2. **vtk.js picker latency**: at ~25k LDC cells the picker should be
   sub-frame; arbitrary STL with 1M cells may need vtkPropPicker →
   vtkCellPicker fallback or progressive picking. Tier-A focuses on
   LDC; Tier-B adds the perf knob. Codex round 1 will likely flag
   this as a forward note.
3. **Race between user annotation and AI action**: solved by
   `annotation_revision` in envelope (mirrors V61-097 `genRef`).
4. **Reset semantics**: re-running setup-bc with new annotations —
   Tier-A: full re-run (simplest); Tier-B may want incremental.

## Linked artifacts (Notion sync targets)

Three artifacts pair-sync per V61-094 / V61-095 / V61-096 §Sync
precedent (Kogami P3 #5 finding):

1. **DEC** — Decisions DB row (this page · standard pattern)
2. **brief_2026-04-29.md** — Notion sub-page under this DEC's row
3. **spec_v2_2026-04-29.md** — Notion sub-page under this DEC's row

Counter +1 (62 → 63). Kogami review N/A (not triggered).

## Implementation arc (per spec_v2 §E)

11 steps total (mirrors V61-094 / V61-095 / V61-096 patterns):

1. Pre-implementation surface scan (CLASS-1 docs · this DEC § ↑)
2. Backend skeleton commit · `face_annotations.py` + `ai_envelope.py`
   + tests for face_id stability + envelope round-trip
3. Backend integration · `setup_bc_runner.py` returns
   `AIActionEnvelope` + reads `face_annotations.yaml` + LDC
   forced-blocked flag
4. Backend route surface · `/face-annotations` GET/PUT under
   `/cases/{case_id}/` + envelope return on `/setup-bc`
5. Frontend types + client · `AIEnvelope` + `UnresolvedQuestion`
   + `awaiting_user` state + faceAnnotations endpoints
6. Frontend Viewport pickMode · `vtkCellPicker` + hover/click/
   shift-click handlers + face highlight overlay
7. Frontend Step3Setup dialog panel · question checklist +
   FacePickOverlay + `[继续 AI 处理]` button armed by completion
8. **Pre-merge Codex review** (mandatory per RETRO-V61-001 ≤70%
   gate · 50% self-pass-rate)
9. NO Kogami (V61-094 P2 #1 bounding clause)
10. CFDJerry visual smoke + ratify (LDC forced-blocked dialog flow
    end-to-end)
11. Dogfood log + DEC Status flip to Accepted + Notion sync

## Path A engagement implications

- M-AI-COPILOT Tier-A delivers the human-AI collab layer that makes
  arbitrary-STL recruitment viable. Without it, Path A demos hit a
  wall whenever the AI can't disambiguate inlet/outlet/walls.
- Path A Gate-4 unlocks at M-AI-COPILOT Tier-A merge per the natural
  extension of `.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md`
  (Gate-3 unlocked at M-PANELS Tier-A).
- If a Path A stranger recruit imports an arbitrary STL during a
  Tier-A demo, the LDC forced-blocked flag can be dropped and the
  recruit can drive the dialog manually — the UI is fixture-agnostic
  by design (face_id hash + face_annotations.yaml are STL-agnostic).
- Tier-B (rule-based AI for arbitrary STL) is the next milestone
  candidate; M-AI-COPILOT Tier-A is the prerequisite gate.
