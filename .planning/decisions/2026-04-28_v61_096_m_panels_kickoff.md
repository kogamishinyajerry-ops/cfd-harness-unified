---
decision_id: DEC-V61-096
title: M-PANELS kickoff — three-pane workbench shell + 5-step tree + AI 处理 / 下一步 / 上一步 button contract (third milestone under Pivot Charter Addendum 3)
status: Accepted (2026-04-28 · CLASS-1 docs-only governance kickoff per V61-086/089/093/094/095 precedent · Codex SKIPPED at kickoff [will fire pre-merge per RETRO-V61-001 ≤70% self-pass-rate gate during implementation arc Step 8 of spec_v2 §Sequence] · Kogami NOT triggered per V61-094 P2 #1 bounding clause [4-condition self-check passes: no charter mod · workbench/** + visualization/** already line-A · counter <20 since RETRO-V61-005 · no risk-tier change] · CFDJerry explicit ratification 2026-04-28)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-28
authored_under: Pivot Charter Addendum 3 §3 (product-interaction hard constraint) + §4.a (M-PANELS surface) + §4.c HARD ORDERING (DEC-V61-093 Accepted 2026-04-28)
parent_decisions:
  - DEC-V61-093 (Pivot Charter Addendum 3 ratification · binding parent — §3 + §4.a + §4.c)
  - DEC-V61-095 (M-RENDER-API kickoff · ratifying parent precedent — closed 2026-04-28 commit 3acdf14 · Codex APPROVE at round 5 · framing inherited per V61-094 P2 #1 bounding clause)
  - DEC-V61-094 (M-VIZ kickoff · framing precedent · closed 2026-04-28 commit 36c4a78)
  - DEC-V61-087 (v6.2 three-layer governance · NOT modified)
  - DEC-V61-088 (pre-implementation surface scan · routine startup discipline)
  - DEC-V61-089 (two-track invariant · workbench frontend serves both tracks)
  - DEC-V61-091 (M5.1 verdict cap · cap remains dormant; Step 4 Solve placeholder references it)
  - DEC-V61-092 (workbench nav-discoverability · superseded by M-PANELS step-tree)
  - RETRO-V61-001 (risk-tier triggers · multi-file frontend + UX-critique-driven impl + ≤70% self-pass triggers PRE-MERGE Codex)
parent_artifacts:
  - docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md (charter binding · §3 + §4.a + §4.c)
  - .planning/strategic/m_panels_kickoff/brief_2026-04-28.md (one-pager)
  - .planning/strategic/m_panels_kickoff/spec_v2_2026-04-28.md (tier-split spec)
  - .planning/strategic/m_panels_interactive_face_naming_2026-04-28.md (deferred Tier-B candidate per CFDJerry M-VIZ Step-7 ask)
implementation_paths:
  - ui/frontend/src/pages/workbench/StepPanelShell.tsx (NEW · top-level shell)
  - ui/frontend/src/pages/workbench/step_panel_shell/** (NEW · 5 step files + 5 shell components)
  - ui/frontend/src/pages/workbench/ImportPage.tsx (MODIFIED · extract Step1Import primitives + switch to format='glb')
  - ui/frontend/src/router.tsx (MODIFIED · /workbench/<id> route + legacy redirects)
  - ui/frontend/src/api/client.ts (MODIFIED if surface scan finds inlined endpoints)
  - ui/frontend/src/visualization/Viewport.tsx (UNMODIFIED · Tier-A consumes existing format='stl'|'glb' API)
read_paths:
  - reports/codex_tool_reports/m_render_api_arc/README.md (Codex precedent reference)
  - .planning/dogfood/M_RENDER_API_v0.md (closure pattern reference)
  - .planning/dogfood/M_VIZ_v0.md (closure pattern + visual-smoke step reference)
prerequisite_status:
  v61_095_acceptance: confirmed (M-RENDER-API closed 2026-04-28 · commit 3acdf14 · Codex APPROVE at round 5 · 7 findings closed)
  v61_094_acceptance: confirmed (M-VIZ closed 2026-04-28 · commit 36c4a78 · Step-7 visual smoke PASSED)
  v61_093_acceptance: confirmed (Pivot Charter Addendum 3 §3 + §4.a + §4.c binding)
  line_a_contract: confirmed (workbench/** declared line-A in ROADMAP §"Line-A / Line-B isolation contract" predates V61-094; visualization/** declared in commit 8fdb0a3 PRE-M-VIZ. NO further ROADMAP extension needed for M-PANELS Tier-A.)
  m_render_api_endpoints: confirmed (geometry/render + mesh/render + results/{run}/field/{name} all live · Codex APPROVE)
  break_freeze_quota: confirmed (current count 1/3 from M-VIZ Step 6 e453ba0 · M-PANELS Tier-A consumes 1 slot taking total to 2/3 · M-AI-COPILOT projected to consume the last slot taking total to 3/3 · accounted in spec_v2 §F)
notion_sync_status: pending (DEC + brief + spec_v2 sub-pages will sync after this DEC's ratify trailer commit per V61-094/V61-095 §Sync precedent · Kogami P3 #5 placement)
autonomous_governance: true
library_choice: React + React Router + Tailwind (all existing) · @kitware/vtk.js Viewport from M-VIZ · @tanstack/react-query for endpoint state (verify usage in surface scan; add if absent · single PR scope) · NO new UI component library / state-management library
codex_tool_report_path: pending (per-implementation-arc Codex fires PRE-MERGE on Step 8 of spec_v2 §Sequence per RETRO-V61-001 ≤70% self-pass gate)
codex_review_required: true
codex_review_phase: pre-merge (RETRO-V61-001 ≤70% self-pass gate · NOT post-merge)
codex_triggers:
  - 多文件前端改动 (>10 new files: shell + 5 steps + 4 shell components + tests)
  - 用户 UX 批评后的首次实现 (Pivot Charter Addendum 3 §3 product-interaction hard constraint this milestone delivers)
  - UI 交互模式变更 (agentic-wizard → engineer-driven step-panel)
  - ≤70% self-pass-rate (60% per spec_v2 §self-pass-rate · triggers pre-merge per RETRO-V61-001)
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
       verbatim. M-PANELS executes the §3 product-interaction hard
       constraint as already-ratified.
    2. Line-A contract extension beyond M-VIZ? NO.
       `ui/frontend/src/pages/workbench/**` is line-A per ROADMAP
       §"Line-A / Line-B isolation contract" table row that PREDATES
       V61-094 (workbench frontend has been line-A since the
       isolation table existed). `ui/frontend/src/visualization/**`
       was extended PRE-M-VIZ in commit 8fdb0a3. Both paths cover
       M-PANELS Tier-A surface. NO new line-A claim.
    3. Counter ≥20 since RETRO-V61-005? NO. Counter currently 60
       after V61-095 close-out. M-PANELS kickoff brings it to 61.
       Δ since RETRO-V61-005 = 10. Well below 20-trigger threshold.
    4. Explicit risk-tier change? NO. Same risk class as M-VIZ /
       M-RENDER-API (multi-file frontend + UX-critique-driven impl).
       60% self-pass-rate triggers PRE-MERGE Codex per
       RETRO-V61-001, NOT a Kogami strategic review tier change.

    All 4 NO → Kogami NOT TRIGGERED. CFDJerry ratification of THIS
    DEC is the strategic gate.

    Important note: M-PANELS is the LARGEST UX surface in the
    Addendum 3 arc. If CFDJerry wants Kogami strategic review on
    this kickoff specifically (overriding the bounding clause), he
    can request it pre-merge — it would not change Kogami's "not
    automatically triggered" status but would land as an
    ad-hoc-strategic-clearance run with its own audit trail at
    `.planning/reviews/kogami/m_panels_kickoff_<date>/`.
break_freeze_required: true
break_freeze_rationale: |
  Per Pivot Charter Addendum 3 §5 选项一: workbench/** edits in
  M-PANELS Tier-A consume 1 of the remaining 2 §11.1 BREAK_FREEZE
  quota slots. Each implementation commit touching
  ui/frontend/src/pages/workbench/** carries the
  `BREAK_FREEZE: rationale=Addendum 3 §3 binding (M-PANELS · DEC-V61-096)`
  trailer. Quota ledger maintained in spec_v2 §F. Counter:
  1/3 used (M-VIZ Step 6 e453ba0) → 2/3 after M-PANELS arc closes.
self_estimated_pass_rate: 60
self_estimated_pass_rate_calibration: |
  -15% vs M-RENDER-API (75%) and -10% vs M-VIZ (70%) because:
  - largest UX surface yet (three-pane shell + step-tree + button
    contract is structurally novel)
  - §11.1 BREAK_FREEZE consumed (per-PR escape clause adds
    governance overhead)
  - routing redirect contract is tricky (legacy deep links must
    keep working for one milestone, then deprecate cleanly)
  - vtk.js + react-query + form-state interaction has multi-axis
    failure modes (state sync, abort signals, stale glb chunks
    across step navigation)
  Per RETRO-V61-001: ≤70% triggers PRE-MERGE Codex review (not
  post-merge). M-PANELS pre-merge Codex is mandatory.
counter_v61: 61
counter_v61_delta_since_retro: 10  # since RETRO-V61-005
---

## Decision

**Ratify M-PANELS kickoff** as a CLASS-1 docs-only governance kickoff:
- Tier-A scope = three-pane workbench shell (top bar + left step-tree
  + center 3D viewport + right task-panel + bottom status strip) +
  5-step tree (Import / Mesh / Setup / Solve / Results) + the
  `[AI 处理] / [上一步] / [下一步]` button contract + Steps 1 (Import)
  and 2 (Mesh) wired end-to-end + Steps 3-5 placeholder task-panels
- No new dependencies (React + React Router + Tailwind + vtk.js +
  react-query · all already in stack)
- No new ROADMAP line-A extension (workbench/** + visualization/**
  already declared line-A)
- No new backend endpoints in Tier-A (consumes M-RENDER-API)
- §11.1 BREAK_FREEZE: 1 slot consumed (1/3 → 2/3) per Addendum 3 §5
  选项一
- Codex PRE-MERGE review per RETRO-V61-001 ≤70% self-pass-rate gate
- Kogami NOT triggered per V61-094 P2 #1 bounding clause (4-condition
  self-check passes)
- Path A engagement Gate-3 unlocks at M-PANELS Tier-A merge

## Why this kickoff DEC is needed

This DEC ratifies the implementation plan + Tier-A scope + library
choice + line-A path coverage + the §11.1 BREAK_FREEZE quota usage +
the Codex pre-merge gate trigger condition. Without this DEC ratified,
no M-PANELS implementation commit lands. CFDJerry's signoff on the
spec_v2 + the ratification of the bounding-clause Kogami self-check is
the strategic gate.

The three Tier-A scope decisions that materially constrain
implementation:

1. **Tier-A bounded to Steps 1-2 wired + Steps 3-5 placeholder**.
   Adding face-pick / face-naming (CFDJerry's M-VIZ Step-7 ask) to
   Tier-A would balloon scope across 3 milestones (per the captured
   feature-request doc). Tier-A keeps face-naming as a deferred
   Tier-B candidate landing in M-PANELS.advanced or as a fast-track
   if Path A signal demands.

2. **No new component library / state-management library**. Tailwind
   primitives + a thin `<Pane>` / `<Button>` / `<FormRow>` wrapper
   layer is enough for Tier-A. Material UI / shadcn / Chakra would
   be over-budget. URL-driven step state + react-query for server
   state replaces Redux / Zustand / Jotai.

3. **Legacy routes redirect for one milestone, deprecate in M7**.
   Deep links into `/workbench/<id>/{import,edit,mesh,run}` keep
   working via React-Router redirects with `?step=N` query param.
   M7-redefined removes the legacy paths once Setup + Solve land.

## Pre-implementation surface scan (per DEC-V61-088)

Spec_v2 §E Step 1 will execute this in detail. Top-level checks
already verified for the kickoff:

1. **ROADMAP line-A coverage**:
   - `ui/frontend/src/pages/workbench/**` line-A row exists (predates
     V61-094) ✓
   - `ui/frontend/src/visualization/**` declared line-A in commit
     8fdb0a3 (PRE-M-VIZ) ✓
   - **No new ROADMAP extension needed** for M-PANELS Tier-A.

2. **Existing-implementation grep targets (verify in spec_v2 §E
   Step 1)**:
   - `useQuery` / `useMutation` / `QueryClient` — confirm react-query
     is already wired; if not, add it as part of Step 2 skeleton
     commit (single PR · line-A bounded)
   - `<ImportPage>` upload primitives — extract into `<Step1Import>`
   - existing mesh-wizard form components — extract into `<Step2Mesh>`

3. **§11.1 BREAK_FREEZE quota check**:
   - Current count: 1/3 (M-VIZ Step 6 commit e453ba0 ImportPage
     edit on 2026-04-28)
   - M-PANELS Tier-A: will consume 1 slot for the entire arc (all
     workbench/** edits bundled per spec_v2 §E sequence)
   - Projected post-arc: 2/3
   - Forward note for M-AI-COPILOT: 1 slot remaining; M-AI-COPILOT
     must bundle all workbench/** touches into a single arc.

4. **Forward note for M7-redefined / M8-redefined**:
   - M7-redefined: removes the legacy ImportPage / EditCasePage /
     MeshWizardPage / WizardRunPage route shells (their content is
     now in StepPanelShell)
   - M8-redefined: invites stranger dogfood ON THE STEP-PANEL UI;
     M-PANELS Tier-A is the surface they evaluate

## Linked artifacts (Notion sync targets)

Three artifacts pair-sync per V61-094 / V61-095 §Sync precedent
(Kogami P3 #5 finding):

1. **DEC** — Decisions DB row (this page · standard pattern)
2. **brief_2026-04-28.md** — Notion sub-page under this DEC's row
3. **spec_v2_2026-04-28.md** — Notion sub-page under this DEC's row

Counter +1 (60 → 61). Kogami review N/A (not triggered).

## Implementation arc (per spec_v2 §E)

11 steps total (mirrors V61-094 / V61-095 patterns):

1. Pre-implementation surface scan (CLASS-1 docs · this DEC § ↑)
2. Skeleton commit · StepPanelShell + 5 step files + types + routing
3. Shell components · StepTree + StepNavigation + StatusStrip + TopBar + tests
4. Step 1 Import wired (format='glb' · extract from ImportPage)
5. Step 2 Mesh wired ([AI 处理] + wireframe glbUrl)
6. Steps 3-5 placeholders + legacy redirects + bundle-budget check
7. Build + typecheck + test smoke
8. **Pre-merge Codex review** (mandatory per RETRO-V61-001 ≤70% gate)
9. NO Kogami (V61-094 P2 #1 bounding clause)
10. CFDJerry visual smoke + ratify
11. Dogfood log + DEC Status flip + Notion sync

## Path A engagement implications

- M-PANELS Tier-A delivers the workbench shell that LOOKS LIKE ANSYS
  Workbench on Steps 1-2.
- Path A Gate-3 unlocks at M-PANELS Tier-A merge per
  `.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md`.
- If a Path A stranger recruit hits the binary-STL / single-solid
  face-naming gap during Step 1 demo, **elevate the M-PANELS.advanced
  face-pick fast-track** per the feature-request doc's signal-driven
  recommendation.
