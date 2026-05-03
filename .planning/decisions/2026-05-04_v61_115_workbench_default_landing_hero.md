---
decision_id: DEC-V61-115
title: Workbench-first default landing + hero CTA (flip / → /workbench, demote /learn)
status: Proposed (2026-05-04 · authored under user 2026-05-04 autonomous-mode mandate "全都按你的建议来"; awaiting Codex pre-merge approval per RETRO-V61-001 risk-tier)
codex_tool_report_path: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User feedback 2026-05-04 — "目前的UI仍然看起来过于压抑，10个gold case的展示固然是不错的，但是作为一个工作台，主角应该是CFD的仿真工作台，一个工程师一眼就知道自己该怎么新建case的入口". Five-DEC arc plan A→C→B→D→E confirmed by user "全都按你的建议来"; this is item A (smallest, immediately-visible value).
parent_decisions:
  - DEC-V61-046 (buyer-facing hero on /learn · 2026-04-22 convergence round established /learn as default landing — this DEC inverts that decision based on user-as-engineer feedback)
  - DEC-V61-092 (workbench nav-discoverability fix · added /workbench to sidebar — this DEC continues that direction by making /workbench the default landing)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan-found trailer per §)
  - RETRO-V61-001 (risk-tier · multi-file frontend change = mandatory Codex pre-merge)
parent_artifacts:
  - .planning/ROADMAP.md L9 ("North star: 你能每天打开 /workbench …") — this DEC realigns landing to the documented north star
  - ui/frontend/src/App.tsx:39 + :103 (current default + catch-all both redirect to /learn)
  - ui/frontend/src/pages/workbench/WorkbenchIndexPage.tsx (current landing has small header + 10-card grid, no clear "新建案例" CTA)
  - ui/frontend/src/components/Layout.tsx (sidebar already exposes /workbench; /learn already linked as "← Learn")
counter_impact: +1 (autonomous_governance: true · UX flip with no external gate; Kogami skip-clause: docs-only? — NO, UI change. Skip-clause "single-file ≤50 LOC routine"? — NO, multi-file. Kogami-trigger check: not a phase-close, not a RETRO draft, not a high-risk operator-endpoint PR · Kogami SKIP per DEC-V61-087 §4.2 — UI default-landing flip with no governance-rule change is below high-risk-PR threshold. Codex pre-merge MANDATORY per RETRO-V61-001 multi-file-frontend trigger.)
self_estimated_pass_rate: 70% (HIGH baseline · small scope, 3 files, ~100 LOC. Risk surface: (a) Codex may flag a11y on new hero CTAs, (b) Codex may want focus management on default-landing flip, (c) Codex may suggest preserving /learn as canonical link in hero for buyers/reviewers, (d) Codex may catch that the catch-all-redirect flip needs to also update the workbench-relative deep-link fallback. Expect 1-2 rounds; possible P3 nits.)
notion_sync_status: pending (will sync after Codex APPROVE + commit lands)

---

# DEC-V61-115 · Workbench-first default landing + hero CTA

## Why now

User feedback 2026-05-04 (verbatim): "目前的UI仍然看起来过于压抑，10个gold case的展示固然是不错的，但是作为一个工作台，主角应该是CFD的仿真工作台，一个工程师一眼就知道自己该怎么新建case的入口".

The 2026-04-22 convergence round (DEC-V61-046 R1-M1/M4) made `/learn` the default landing on the rationale that buyer-facing positioning was the priority (10 canonical cases + literature comparator + signed audit package strip). That priority was correct for that moment but the **product's primary user is the CFD engineer creating a new case**, and the engineer's entry point is currently buried under buyer copy:

- `/` → `/learn` (catalog of 10 gold cases · governance jargon strip · "Pilot inquiry" mailto)
- Engineer must scroll past hero → CTA strip → BatchMatrix → ExportPanel → catalog grid header → click "新手向导 · 从模板建第一个案例" link buried IN the CTA strip
- Even on `/workbench`, the WorkbenchIndexPage opens with `Pick a case to edit parameters and run...` and lists the 10 whitelist cases — no big "新建案例" or "导入 STL" hero

The ROADMAP's documented north star (`L9: "你能每天打开 /workbench, 改 LDC 参数, 跑真实 Docker+OpenFOAM..."`) already declares /workbench as the front door. This DEC realigns the running UI to that north star.

## Decision

Three-part flip, all in the frontend (no backend changes):

### Part 1: Flip `/` default redirect

`ui/frontend/src/App.tsx:39` — change `<Route index element={<Navigate to="/learn" replace />} />` to `<Route index element={<Navigate to="/workbench" replace />} />`.

`ui/frontend/src/App.tsx:103` — change catch-all `<Route path="*" element={<Navigate to="/learn" replace />} />` to `<Route path="*" element={<Navigate to="/workbench" replace />} />`.

### Part 2: WorkbenchIndexPage hero

Add a hero section at the top of `WorkbenchIndexPage.tsx` (above the existing CaseCard grid):

```
┌───────────────────────────────────────────────────────────────┐
│  CFD 仿真工作台 · CFD Simulation Workbench                       │
│  从空白模板新建案例 / 上传几何 / 编辑已有案例 — 全在 GUI 中完成。     │
│                                                                │
│  [ ▶ 新建案例（从模板）]  [ 📥 导入 STL 几何 ]                      │
│   New case from template     Import STL geometry                │
│                                                                │
│  AI 助手随时召唤 → 每个步骤的 [AI 处理] 按钮 = AI 跑当前阶段          │
│  (网格 / 边界条件 / 求解 / 报告生成)                                │
└───────────────────────────────────────────────────────────────┘
```

Two large primary CTAs: 新建案例 (→ `/workbench/new`) + 导入 STL (→ `/workbench/import`). Visual weight should beat the existing CaseCard grid below.

### Part 3: Demote 10-card grid to "参考案例"

Below the hero, retitle the grid section: `参考案例 · Reference cases` with subtitle `10 个金标准案例 — 复现历史文献，可直接编辑参数二次仿真，是验证 workbench 可信度的基线`. Visual treatment unchanged (CaseCard component preserved), only the section heading + intro copy change.

Add a footer link in the hero block to `/learn` for buyers/reviewers who want the 10-case demo gallery: "想看 10 个金标准案例的演示模式 → /learn".

## Acceptance criteria

§1 `/` redirects to `/workbench` (was `/learn`). Both index Route + catch-all updated.

§2 WorkbenchIndexPage renders hero block above existing CaseCard grid. Hero contains:
- Title: 「CFD 仿真工作台 · CFD Simulation Workbench」
- Two primary CTAs (`新建案例` → `/workbench/new`, `导入 STL` → `/workbench/import`) with visual weight (border + background + larger font) exceeding the CaseCard grid items below
- One AI-assistant explainer line ("每个步骤右侧 [AI 处理] 按钮 = 召唤 AI 跑当前步")
- One footer link "想看 10 个金标准案例的演示模式 → /learn"

§3 CaseCard grid section retitled to `参考案例 · Reference cases` with subtitle clarifying their role as baseline reference, not the primary engineer-flow entry.

§4 `/learn` route remains accessible (Layout sidebar "← Learn" link unchanged + new hero footer link). No deletion of LearnHomePage / LearnLayout.

§5 Existing tests still pass (WorkbenchRunPage.test.tsx asserts `/workbench/new` link from /workbench/run/* — not affected).

§6 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001 (multi-file frontend trigger).

§7 Surface scan applied per V61-088: see `Surface-scan-found:` trailer.

## Out of scope

- StepTree refactor to Fluent-style expandable tree — separate DEC (V61-117 · arc item B)
- Completeness analyzer + sticky right-rail card — separate DEC (V61-116 · arc item C)
- LLM provider integration — separate DEC arc (V61-118 · item D)
- Removing /learn or LearnHomePage — explicitly preserved (still has demo value for buyers/reviewers)
- Any new backend endpoint — frontend-only DEC

## Process note

This is item A of the user-confirmed 5-DEC arc (A → C → B → D → E):
- A · V61-115 — workbench default landing flip (this DEC, smallest)
- C · V61-116 — completeness analyzer (rule-based, no LLM)
- B · V61-117 — StepTree expandable Fluent-style tree
- ARC RETRO V61-088 → V61-114 — deferred to between C+B and D (per user mandate; counter ≥20 trigger noted)
- D · V61-118 — DeepSeek V4 Pro primary + MiniMax-M2.7-highspeed fallback (LLM)
- E · V61-119 — LLM-wrapped completeness coaching

`Surface-scan-found: ui/frontend/src/App.tsx:39 + :103 (default + catch-all redirect to /learn) + ui/frontend/src/pages/workbench/WorkbenchIndexPage.tsx:41-67 (current header lacks new-case hero CTA) + ui/frontend/src/components/Layout.tsx (sidebar already exposes both /workbench + ← Learn — no change needed) · disposition: extend existing (add hero block, flip redirect, retitle grid section; no deletions, no new routes, no new backend)`

## Counter impact

This DEC's acceptance advances `autonomous_governance_counter_v61` 73 → 74. RETRO-V61-001 cadence rule #2 (counter ≥20 since prior retro · last anchor RETRO-V61-V107-V108 at counter 53 → arc retro at counter 73) is **already triggered** but explicitly deferred per user 2026-05-04 mandate to between C and B+D in the 5-DEC arc plan. Tracked as task #23.
