---
decision_id: DEC-V71-charter
title: V71 charter · v3 Blueprint Implementation · 10-pillar fleet · Pillar 6/10 tightened against visual contract
status: Accepted
parent_dec: DEC-V70-close
phase: V71
notion_sync_status: pending
predecessor: DEC-V70-close
batch: B169
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: none (charter)
substrate: V70 close · 8 v3 blueprint images ACCEPTED at .planning/blueprints/v3/ (B168) · 10-pillar fleet stable at 100/100
---

# DEC-V71-charter · V71 v3 Blueprint Implementation

## 1 · Decision

Launch V71 "v3 Blueprint Implementation" — the **7th V110 advisor-class single-day arc**. Mission: translate the 8 v3 blueprint images (committed B168 as visual SSOT) into a working `<WorkbenchShellV3>` React route at `/workbench/v3/case/:id`, parallel to existing routes, demonstrating all blueprint surfaces.

User mandate (7th "全都要" invocation):
> "瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……明确的完成度评分机制（绝对诚实客观，维度充足，包括CFD仿真全维度能力、新手用户使用难度、UI对标顶级工业软件）"

## 2 · Scope honesty (charter §6 anti-fraud frame)

V71 is **blueprint-driven proof-of-implementation**, not full migration. Specifically:

- **In scope**: build a NEW `<WorkbenchShellV3>` route + components that visually match the 8 blueprint images · lock baselines 23-30 · V132 contract test against new Advisor surface · Pillar 6 → 99.5+ and Pillar 10 → 95+
- **Out of scope**: migrating existing routes (WorkbenchIndexPage / EditCasePage / StepPanelShell) to v3 architecture · full SolveRunOrchestrator backend rewire · Electron multi-window wrapper (V72+)

This is the same scope-fitting honesty V70 used for Pillar 9 (artifact-presence not user-tested). V71 proves the blueprints are implementable; V72+ migrates production routes onto the implementation.

## 3 · North star (verifiable end-state)

> 工程师导航到 `/workbench/v3/case/lid_driven_cavity?step=1` 看到完整的 v3 四面板架构 (Activity Bar / Left Panel / Center / Right Panel + Bottom Panel · 5-Step Pipeline Strip + Viewport Mode Toolbar)。点击不同 step 切换 viewport mode 内容 · Inspector tab 切到 Advisor 看到 advisory-only findings · 没有 auto-execute buttons (V132 invariant test green) · 8 PNG visual baselines lock against blueprint images at ≤0.05 SSIM drift. Pillar 6 ≥99.5 · Pillar 10 ≥95 · 10-pillar min ≥99 (2-consecutive close gate).

## 4 · Done dim checklist (10 dims · all required for V71 close)

- [ ] **V71-DONE-1 · WorkbenchShellV3 4-panel grid** — Activity Bar + Left Panel + Center (Pipeline Strip + Viewport Mode Toolbar) + Right Panel + Bottom Panel · CSS Grid template-columns `48px 260px 1fr 340px` · all panels collapsible
- [ ] **V71.A · CaseBrowser tree** in Left Panel · 4 workspace sections + expandable Whitelist cases + recent runs + sand-coral left-indicator on active case
- [ ] **V71.B · 5-Step Pipeline Strip** with chevron separators + status dots · sand-coral underline on active step
- [ ] **V71.C · Viewport Mode Toolbar** with 6 modes · sand-coral underline on active mode
- [ ] **V71.D · Right Panel 3-tab strip** · Inspector / Advisor / TruthChain · tab switching
- [ ] **V71-DONE-2 · Step 1/2/3 surfaces** wired to shell · BC color-coded patches (dusty palette) · MaterialCard inline two-column
- [ ] **V71-DONE-3 · ResidualsChart primitive** · log-scale multi-line with sand-coral accent for watched curve + Bottom Panel with 4 tabs + Console streaming
- [ ] **V71-DONE-4 · AdvisorTab + V132 contract test** · paragraph + citations + preview-apply text links · ZERO auto-execute buttons (regression-protected)
- [ ] **V71-DONE-5 · ResultsCanvas + TrustGate verdict** · gold-vs-computed chart + HUGE PASS verdict + point-by-point table
- [ ] **V71-DONE-6 · Cross-step inspection** · viewport mode independent of pipeline step · Inspector contextual to both
- [ ] **V71-DONE-7 · 8 visual baselines (23-30)** locked against blueprint images at ≤0.05 SSIM drift
- [ ] **V71-DONE-8 · Pillar 6 99 → 99.5+ · Pillar 10 90 → 95+** with per-driver delta accounting
- [ ] **V71-DONE-9 · Fleet criteria tightened** · Pillar 6 includes "v3-shell-route-mounts" check · Pillar 10 includes "blueprint baseline diff" check

## 5 · Sub-DEC seeds (6 expected)

| Sub-DEC | Title | Blueprint anchors | Pillar drivers |
|---|---|---|---|
| V71.1 | WorkbenchShell v3 4-panel + Activity Bar + Pipeline Strip | Image 01 | Pillar 6, 10 |
| V71.2 | Step views + Inspector contextual + BC color + MaterialCard | Images 02-04 | Pillar 6 |
| V71.3 | ResidualsChart + Bottom Panel + SolveRun streaming | Image 05 | Pillar 4, 6 |
| V71.4 | AdvisorTab right-panel peer + V132 contract test | Image 06 | Pillar 7, 10 |
| V71.5 | ResultsCanvas + TrustGate verdict surface | Image 07 | Pillar 6, 7 |
| V71.6 | Visual baselines 23-30 + cross-step + close | Image 08 + all | Pillar 4, 10 |

## 6 · Fleet criteria (10-pillar · tightened vs V70)

| # | Agent | V70 criteria | V71 criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | unchanged |
| 2 | Physics | + canonical eval ≥30 | unchanged |
| 3 | UX | ≥13 specs PASS | **≥17 specs PASS** (+4 V71 e2e) |
| 4 | Visualization | ≥22 PNG | **≥30 PNG** (+8 V71 baselines) |
| 5 | Smoke | + canonical harness | unchanged |
| 6 | Functional | 6 sub-DECs · 9 Done | **6 sub-DECs · 9 Done** (unchanged formula) |
| 7 | Stability | vitest 3-run flake | unchanged |
| 8 | CFD-Breadth | unchanged | unchanged |
| 9 | Novice-Onboarding | unchanged | unchanged |
| 10 | Industrial-UI | benchmark doc + 3 improvements | **+ v3 blueprint compliance · ≥6 V71.UI tags LANDED · ≥3 v3-route components mounted** |

Plus: NEW Pillar-10 sub-score **`v3_route_mounts`** — count of `WorkbenchShellV3`-tagged top-level routes resolved · ≥1 required.

## 7 · Reverse-stop log

- V132 `MUTATING_ROUTES` net diff > 0 (new shell must NOT add MUTATING routes · only display routes)
- Any `auto-execute` / `AI-runs` / `Auto-fix` button created in Advisor surface (V132 invariant violation)
- v3 shell uses any accent color other than sand-coral `#b78b65` (palette violation)
- New shell adds a 5th persistent panel beyond the 4 documented (architecture violation)
- Visual baseline diff > 0.05 SSIM from blueprint image on first generation (UI drift from contract)
- Pillar 6 regression below 99 (existing surfaces broke)
- V71 work breaks any existing 22 baselines (cross-arc regression)

## 8 · Counter telemetry projection

| Counter | Projection |
|---|---|
| autonomous_governance_counter_v61 tick | +7 (charter + 6 sub-DECs + close) |
| Total counter (cumulative through V71) | 28 (V70 21 + V71 7) |
| V110 advisor-class arc applications | 7 (V67-C through V71) |
| MUTATING_ROUTES at close | 9 (V132 invariant locked · v3 routes are display-only) |
| Charter Q4 violations | 0 (4Q gate 4/4) |

## 9 · Confidence: high

- 8 blueprint images provide concrete visual SSOT (V70 didn't have this · V71 does)
- 21 implementation tasks already enumerated in `.planning/blueprints/v3/INDEX.md` · just need to be packed into 6 sub-DECs
- Existing workbench substrate (StepPanelShell · MaterialCard · AIAdvisorPanel · etc.) provides patterns to copy
- 10-pillar fleet already stable from V70 · just needs Pillar 10 tightening + 8 new baselines
- v3 routes are DISPLAY-only · zero MUTATING_ROUTES growth · zero V132 invariant risk if AdvisorTab follows the no-auto-execute pattern

— V71 charter · 2026-05-16 · B169
