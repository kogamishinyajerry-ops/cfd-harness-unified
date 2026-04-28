---
decision_id: DEC-V61-093
title: Pivot Charter Addendum 3 ratification — CAE-workbench interaction pivot (engineer-in-the-loop · ANSYS-Fluent-class · per-step AI co-pilot)
status: Accepted (2026-04-28 · Codex SKIPPED [CLASS-1 docs-only per V61-086/089 precedent · per-milestone Codex fires when M-VIZ etc. implement] · Kogami APPROVE_WITH_COMMENTS · recommended_next=merge · 4 findings (3 P2 + 1 P3) addressed inline · CFDJerry explicit ratification 2026-04-28)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-28
authored_under: post-M5.1 dogfood — CFDJerry product-narrative criticism "我要我的工作台能对标 ANSYS ... 不自动跳转下一步，而是要工程师点击'下一步'" + 三点框架确认 (3D 视口为中心 / 步骤独立 panel / Fluent 5 步模板) "全 yes"
parent_decisions:
  - Pivot Charter 2026-04-22 (Notion SSOT) — main charter unchanged by this Addendum
  - Pivot Charter Addendum 1 (2026-04-26 user-as-first-customer · Notion SSOT) — preserved
  - Pivot Charter Addendum 2 (reserved · Path-B retreat) — preserved (un-fired)
  - DEC-V61-087 (v6.2 three-layer governance · NOT modified — Kogami / Codex / Notion roles intact)
  - DEC-V61-089 (two-track invariant · Track A/B distinction · NOT modified — both tracks consume the new step-panel UI)
  - DEC-V61-091 (M5.1 verdict cap on imported user cases · NOT modified — cap fires automatically once M7-redefined wires it)
  - DEC-V61-092 (workbench nav-discoverability · just shipped 2026-04-28 — its fix is incremental; Addendum 3 supersedes the long-term UI architecture)
  - RETRO-V61-001 (risk-tier triggers · NOT modified)
  - .planning/strategic/path_a_first_customer_recruitment_2026-04-27.md (Path A recruitment binding gate · NOT modified — Addendum 3 raises demo credibility post-recruitment, does not lower the gate)
parent_artifacts:
  - docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md (the Addendum text itself · this DEC ratifies that document into Active state)
  - docs/governance/PIVOT_CHARTER_2026_04_22.md (repo-side §4.3a fragment of main charter · still in force)
prerequisite_status:
  m5_1_acceptance: confirmed (DEC-V61-091 Accepted 2026-04-28 · commit 7f6e3f2 + ce25e9e)
  m6_1_acceptance: confirmed (DEC-V61-090 Accepted 2026-04-28)
  v61_092_acceptance: confirmed (DEC-V61-092 Accepted 2026-04-28 · commit f7ff827 + d7411ac · nav-discoverability defect fixed; Addendum 3 builds on the now-reachable workbench)
notion_sync_status: |
  synced 2026-04-28
    DEC (Decisions DB row):                 https://www.notion.so/350c68942bed818dae03c0a9bf64b49c
    Addendum doc (sub-page · canonical):    https://www.notion.so/350c68942bed814aa314e9e2b39d7d67
    Addendum doc (standalone · searchable): https://www.notion.so/350c68942bed81a6a20cc935ed20a10b
autonomous_governance: true
codex_tool_report_path: null  # CLASS-1 docs-only per V61-086 / V61-089 precedent (no code change in this DEC; per-milestone Codex fires later when M-VIZ / M-RENDER-API / M-PANELS / M-AI-COPILOT implement)
codex_review_skipped: true
codex_skip_rationale: |
  CLASS-1 docs-only governance artifact. No code, no test, no API, no
  schema, no security path, no plane crossing. Per V61-086 + V61-089
  precedent (architectural anchors / charter fragments, both Codex-skipped).
  RETRO-V61-001 risk-tier triggers all evaluate to FALSE for this DEC:
    - 多文件前端改动: NO (no .tsx)
    - API 契约变更: NO
    - OpenFOAM solver: NO
    - foam_agent_adapter.py: NO
    - 新几何类型生成: NO
    - Phase E2E 批量测试失败: NO
    - 安全敏感 operator endpoint: NO
    - byte-reproducibility: NO
    - 跨 ≥3 文件 API rename: NO
    - GSD 产出物 / UI 交互模式变更: NO (proposes future change, no current change)
    - 用户 UX 批评后的首次实现: NO (Addendum is the framing, not the implementation)
  The implementation milestones (M-VIZ / M-RENDER-API / M-PANELS / M-AI-COPILOT)
  WILL each trigger Codex when they execute.
kogami_review:
  required: true
  rationale: |
    Charter-level pivot — classified under DEC-V61-087 §4 "high-risk PR"
    Must-trigger row by **analogy on blast radius**, NOT under
    "autonomous_governance rule change" (which kogami_triggers.md P-4
    defines narrowly as DECs modifying RETRO-V61-001 / DEC-V61-087 /
    kogami_*.md — none of which this DEC touches). The blast radius of
    a Pivot Charter Addendum binding future implementation across 4
    new milestones + 2 redefined milestones meets or exceeds the
    high-risk-PR criteria spirit (trust-core boundary / security
    operator endpoint / byte-reproducibility / API-schema-rename ≥3
    files / verdict-graph) on the dimensions of cross-system reach
    and irreversibility. Kogami strategic review catches narrative
    drift, scope honesty, and roadmap coherence — exactly the failure
    modes a 4-milestone re-roadmap can introduce.

    Forward note (Kogami P2 #1 finding): if Pivot Charter Addenda
    recur, a successor DEC should add "charter-level pivot / Pivot
    Charter Addendum" as an explicit sixth Must-trigger row in
    kogami_triggers.md so future framings are unambiguous.
  triggers:
    - Pivot Charter Addendum (high-risk PR by blast-radius analogy · charter scope ≥ §4.1 criteria spirit)
    - 4 new milestones introduced (M-VIZ · M-RENDER-API · M-PANELS · M-AI-COPILOT) re-routing M7/M8 dependency chains
    - HARD YES constraints in Addendum §3 will bind future implementation DECs (irreversibility risk if mis-framed)
    - §11.1 workbench-freeze interaction (M-PANELS will need BREAK_FREEZE escape, Addendum 3 §5 mandates the rationale chain)
  status: APPROVE_WITH_COMMENTS · recommended_next=merge
  invocation_date: 2026-04-28
  artifacts: .planning/reviews/kogami/addendum_3_cae_workbench_pivot_2026-04-28/
  findings_addressed_in_dec:
    - P2 #1 (trigger framing stretch — re-classified as high-risk PR by blast-radius analogy + forward note for sixth Must-trigger row)
    - P2 #2 (Path A stranger engagement during 6-10 week wait) → Failure modes table gained recruitment-succeeds-pre-M-PANELS row + §Impact Path A subsection updated with engagement-policy options
    - P2 #3 (line-A/line-B path declaration for viewport infra) → §Scope item 2 (M-VIZ) gained prerequisite clause: M-VIZ kickoff DEC must extend ROADMAP isolation contract
    - P3 #4 (60-day extension routes reframing mechanism) → §Impact Architectural impact paragraph 3 expanded with concrete reframing mechanism
---

# DEC-V61-093 · Pivot Charter Addendum 3 ratification

## Why

CFDJerry, on 2026-04-28 (post-M5.1 ship · post-DEC-V61-092 nav fix), gave
critical product-narrative feedback that the current "agentic-wizard"
interaction model does not match what he or any recruited Path A
stranger expects from a CAE workbench. He explicitly asked for ANSYS-
Fluent-class engineer-in-the-loop control with per-step AI co-pilot —
"AI 处理" buttons that opt-in automate each step, but never auto-
advance.

After Claude Code mapped current vs target architecturally and proposed
a three-point framework, CFDJerry confirmed "全 yes" on:

1. 3D viewport is the product center (not JSON / YAML cards)
2. Each step is an independent panel; user controls AI invocation + advance
3. ANSYS Fluent's 5-step framework (Geometry / Mesh / Setup / Solve / Results) as template

This DEC ratifies those three confirmations into a load-bearing charter
Addendum (`docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md`) and
records the resulting roadmap impact (4 new milestones · M7/M8 re-
defined).

## Scope

### What this DEC ratifies (in scope)

1. **Pivot Charter Addendum 3 doc** at
   `docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md` becomes
   Status=Active upon this DEC's acceptance. Three HARD YES constraints
   (§3.a 3D viewport center · §3.b engineer-driven · §3.c Fluent 5-step
   template) become binding on future implementation DECs.

2. **4 new milestones** introduced:
   - **M-VIZ** — 3D viewport infrastructure (vtk.js / three.js selection · STL/glTF rendering · trackball/orbit/pan/zoom camera)
   - **M-RENDER-API** — backend rendering endpoints (geometry / mesh / results field)
   - **M-PANELS** — Step-Tree + Task-Panel + Viewport three-pane layout · `[AI 处理]` / `[下一步]` / `[上一步]` button contract
   - **M-AI-COPILOT** — wrap existing automation as per-step opt-in invocation

   **Prerequisite for M-VIZ implementation** (Kogami P2 #3 finding): the M-VIZ kickoff DEC MUST extend the ROADMAP §Line-A/Line-B isolation contract to declare the new viewport-infrastructure paths as line-A-only BEFORE the first M-VIZ commit lands. Likely paths needing explicit line-A claim:
   - `ui/frontend/src/visualization/**` (new — viewport components)
   - `ui/backend/services/render/**` (new — rendering endpoint services)
   - any new `ui/frontend/src/components/viewport/**` if the layout split warrants it
   Without this prior declaration, M-VIZ commits could spawn ad-hoc paths colliding with line-B writes (e.g., if `src/visualization/` is later claimed by case-physics extractors). The boundary lock-in is a prerequisite, not a deliverable.

3. **Hard implementation ordering** (per Addendum §4.c):
   M-VIZ → M-RENDER-API → M-PANELS → M-AI-COPILOT → M7-redefined → M8-redefined

4. **Re-definition of M7 + M8**:
   - M7 was: "production wire-up · imported-case run path"
   - M7 becomes: "Setup + Solve panel接通 imported case 到 FoamAgentExecutor · V61-091 cap 自动激活"
   - M8 was: "stranger dogfood"
   - M8 becomes: "stranger dogfood **on the new step-panel UI** (not on SSE wizard)"

5. **§11.1 workbench-freeze interaction** acknowledged: M-PANELS will require explicit `BREAK_FREEZE` escape clause referencing Addendum 3 §3, since freeze paths (`ui/frontend/src/pages/workbench/*`) overlap with the planned UI redesign. Each affected PR must cite Addendum 3 in its commit message.

### What this DEC explicitly does NOT do (out of scope)

- Does NOT modify Pivot Charter main body (2026-04-22) — §4.3a freeze
  semantics, 10-case Whitelist ceiling, etc. all unchanged.
- Does NOT modify Pivot Charter Addendum 1 (user-as-first-customer ·
  V61-091 cap derivation) — Addendum 1 stays in force.
- Does NOT modify ADR-001 four-plane import direction.
- Does NOT modify DEC-V61-087 v6.2 three-layer governance.
- Does NOT modify DEC-V61-089 two-track (Track A/B) invariant.
- Does NOT modify Path A recruitment binding gate (still requires named stranger before M7/M8 implementation begins).
- Does NOT plan or implement any of the 4 new milestones — each gets its own kickoff DEC + Codex + Kogami when started.
- Does NOT pick the 3D viewport library (vtk.js vs three.js vs paraview-glance) — that's M-VIZ kickoff scope.
- Does NOT change current backend services — gmsh / FoamAgent / TrustGate / KnowledgeDB all preserved and consumed by new milestones.

## Impact

### Architectural impact

- Frontend grows a new shell (Step-Tree + Viewport + Task-Panel) alongside / replacing the current discrete-route wizard.
- Backend gains 3 rendering endpoints; existing services unchanged.
- The 60-day extension routes (WorkbenchTodayPage / WorkbenchRunPage / RunComparePage / etc.) get reframed as "power-user advanced views" rather than the main flow. Specifically (Kogami P3 #4 finding): they REMAIN at their current URLs (`/workbench/today`, `/workbench/run/{id}`, `/workbench/case/{id}/runs`, `/workbench/case/{id}/compare`) and continue to function — M-PANELS implementation MUST NOT break or remove them. They will no longer be linked from the primary step-panel shell; users reach them only via direct URL or a future power-user nav drawer. M-PANELS kickoff DEC will codify this non-negotiable as an acceptance criterion.

### Roadmap impact

- M7 / M8 effectively delayed by ~6-10 weeks (the time M-VIZ + M-RENDER-API + M-PANELS + M-AI-COPILOT take). Path A recruitment can run in parallel during this window — finding the stranger is independent.
- Each new milestone is a Codex-triggering implementation arc (multi-file frontend + UX implementation), so governance overhead is real but bounded.

### Path A recruitment impact

- **Strictly raises** demo credibility post-recruitment: ANSYS-Fluent-class UI is a well-known interaction pattern that engineers recognize and trust. Stranger walkthrough at M8 becomes "look, it's a Fluent-shaped workbench but every step has an AI accelerator" — a clean narrative.
- **Does NOT change** recruitment criteria or binding gate.
- **Engagement policy during the 6-10 week M-VIZ → M-AI-COPILOT wait** (Kogami P2 #2 finding): if recruitment succeeds before M-PANELS lands, the recruited stranger MUST be given an interim handhold so the relationship doesn't decay silently. Three handholds available (in order of cost):
  1. **Async mockup feedback** — share Figma / static screenshots of the planned step-panel UI for early reactions on the interaction model itself. Lowest cost, immediate.
  2. **Early M-VIZ-only demo** — once M-VIZ ships (~3 weeks in), invite the stranger to interact with just the 3D viewport on their own STL. Demonstrates the viewport pivot is real even before the step-panel framework lands.
  3. **Explicit re-engagement policy** — written commitment ("we will re-engage you when M-PANELS lands, expected ~week N") with periodic status updates so the stranger experiences the wait as honest progression rather than abandonment.
  Default ordering: (1) immediately on recruitment, (2) at M-VIZ ship, (3) at M-PANELS / M-AI-COPILOT ship for full Fluent-class walkthrough. The Path A recruitment doc gains a corresponding "post-recruitment engagement timeline" section in M-VIZ kickoff DEC.

### Counter impact (per V61-087 §5 Interpretation B · STATE.md SSOT)

- **Pre-advance**: 57 (post-V61-092 Accepted)
- **Post-advance**: 58
- Kogami review is gate not counter; doesn't affect math.

## Alternatives considered

(a) **Defer Addendum 3 → ship M7/M8 as currently defined → fix UX in M9** —
rejected: M7/M8 with current SSE-wizard UI cannot be demoed to a Path A
stranger credibly. Demoing then re-doing wastes dogfood goodwill and is
not honest under Addendum 1 user-as-first-customer principle.

(b) **Skip Addendum 3, just refactor frontend in a single big M-FRONTEND
milestone** — rejected: a 4-6-week monolithic refactor without a
governance anchor (Addendum) loses scope discipline. Splitting into 4
small milestones with each gated lets each Codex-review and CFDJerry-
ratify, preserving v6.2.

(c) **Take a 3rd-party CAE-workbench OSS (paraview-glance, OpenFOAM-
GUI, ParaView Web) and embed it** — partially rejected: paraview-glance
will likely be the M-VIZ choice (mature CAE-grade). But "embed it
wholesale" loses the AI-co-pilot-per-step value-add, which is our
differentiation. M-VIZ kickoff DEC will choose embed-vs-build.

(d) **Drop the user's request, keep agentic-wizard direction** —
rejected: violates Addendum 1 (user is first customer, his UX
criticism is canonical product input).

## Failure modes considered

| Failure mode | Mitigation |
|---|---|
| Scope creep — "while we're rebuilding frontend, also redo Track A teaching surfaces" | HARD ORDERING in Addendum §4.c. Each new milestone has explicit out-of-scope listing every kickoff. Track A `/learn` surface stays unchanged. |
| 3D viewport library mis-pick (e.g. three.js for raw CAD when vtk.js fits CAE) | M-VIZ kickoff DEC must include library trade-off section + Codex review of the choice. Switching libraries mid-project is a P0 event. |
| §11.1 freeze blocks M-PANELS without escape | Each M-PANELS PR cites `BREAK_FREEZE: Addendum 3 §3 binding · DEC-V61-093` in commit message. The freeze script supports this escape path. |
| Path A recruitment stalls 6-10 weeks → no stranger by the time M-PANELS / M7-redefined ready | Recruitment is independent and runs in parallel. If still no stranger after M-AI-COPILOT lands, Pivot Charter Addendum 2 (Path-B retreat) re-evaluates. |
| Path A recruitment **succeeds early** (e.g., week 2) but M-PANELS doesn't land until week 8-10 → stranger has no demo-ready UI to engage with → relationship decays silently (Kogami P2 #2) | §Impact Path A subsection added 3-tier engagement policy: async mockup feedback immediately, early M-VIZ-only viewport demo at ~week 3, explicit re-engagement commitment with status updates. M-VIZ kickoff DEC must include a "post-recruitment engagement timeline" section operationalizing this. |
| Addendum 3 §3 hard constraints conflict with later technical reality (e.g. real-time viewport too slow on commodity laptops) | §3 hard constraints can be re-evaluated only via new Addendum 4 + Kogami + CFDJerry ratify. Premature constraint relaxation forbidden. Performance escape valves (LOD / sample-then-render / async stream) belong in M-VIZ implementation choices, not in §3 relaxation. |
| AI 处理 buttons mis-implemented as auto-advance (regression to agentic-wizard) | §3.b explicit + §3.d 严禁列出 "AI 一键自动化整流" as the first banned pattern. M-AI-COPILOT kickoff DEC must include test asserting "下一步" is user-only. |
| Workbench freeze (§11.1) auto-flips to strict mode 2026-05-19 mid-M-PANELS implementation | Each M-PANELS PR uses BREAK_FREEZE escape regardless of advisory/strict mode. The escape clause works in both modes per workbench_freeze.sh. |

## Verification plan

### Self-test (none for docs-only DEC)
- This DEC introduces no code; the Addendum doc itself is reviewed by Kogami.

### Codex review
- **SKIPPED** per CLASS-1 docs-only precedent (V61-086, V61-089).
- Per-milestone Codex will fire when M-VIZ / M-RENDER-API / M-PANELS / M-AI-COPILOT implement.

### Kogami strategic review
- **Required** per frontmatter `kogami_review.required: true` rationale.
- Strategic package: `.planning/reviews/kogami/addendum_3_cae_workbench_pivot_2026-04-28/`
  - `intent_summary.md` — roadmap_milestone, business_goal, affected_subsystems
  - `merge_risk_summary.md` — risk_class (high · charter-level pivot · re-routes 4+ milestones), reversibility (medium · Addendum can be amended via Addendum 4 but cumulative tech debt builds), blast_radius (cross-system · frontend + new endpoints + governance metadata)

### CFDJerry explicit ratification
- Required per DEC-V61-087 — pre-merge gate; STOP point.
- Visual: this DEC has no UI to verify; ratification is on the Addendum text + roadmap re-routing.

## Sync

Notion sync runs only after Status flips to Accepted. Both the
Addendum doc and this DEC sync paired (Notion needs both: Addendum 3
as a Charter sub-page, this DEC as a Decisions DB row referencing it).
Pre-merge state stays Proposed in the repo.
