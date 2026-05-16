---
decision_id: DEC-V72-charter
title: V72 charter · v3 Real-Data Wiring + Interaction Polish · 11-pillar fleet · NEW Pillar 11 (交互体验)
status: Accepted
parent_dec: DEC-V71-close
phase: V72
notion_sync_status: pending
predecessor: DEC-V71-close
batch: B177
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: none (charter)
substrate: V71 closed at 100/100 across 10 pillars (B176) · 30 PNG baselines locked · v3 shell mounted at /workbench/v3/case/:id
---

# DEC-V72-charter · V72 v3 Real-Data Wiring + Interaction Polish

## 1 · Decision

Launch V72 — the **8th V110 advisor-class single-day arc**. Mission: pay down V71's honestly-disclosed static-demo-data debt, and add the 11th pillar the user specifically named in their 8th "全都要" mandate ("交互模式" — interaction polish).

User mandate (8th invocation · 2026-05-16):
> "批准授权你全权开发，瞄准蓝图进行开发，要有一套专门的测试子agent...明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、**交互模式**，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你（主开发会话）眼里的优秀水准（99分以上）"

Three explicit user emphases vs V71:
- **测试子agent** (test sub-agent) — formalize as autonomous playwright `user-journey-v3.spec.ts`
- **交互模式** (interaction patterns) — new 11th fleet pillar
- **Claude UI审美** — extend the restrained-aesthetic principles to motion + focus

## 2 · Scope (honest)

V72 is **wiring + polish**, not new functional surfaces. Specifically:

**In scope** (single-day arc · 6 sub-DECs):
- Real-data wiring for surfaces where backends already exist (no backend work)
- Keyboard navigation across panels (Tab/Shift+Tab/Esc/⌘K)
- Motion design via Tailwind transitions + `prefers-reduced-motion` respect
- Focus management (ARIA, role, tabIndex, autoFocus when tabs change)
- Sub-agent test harness: new `user-journey-v3.spec.ts` exercising the full happy path
- 6 new visual baselines (31-36) locking interaction states
- 11th pillar scorer: `score_interaction_polish.sh` (4 sub-criteria)

**Out of scope** (deferred to V73):
- Real `/api/runs/:id/residuals` SSE (V71.L · requires backend addition · still deferred)
- Real `/api/cases/:id/trust-gate` derivation (still mocked PASS)
- Canvas field-render mode (vtk.js / WebGL · large dependency)
- Multi-case dashboard composition
- VerdictPill unification across TruthChain + TrustGate (cosmetic)

## 3 · 11-pillar fleet (V71 10 + V72 NEW)

| # | Agent | Dim | Weight | V71 close | V72 target |
|---|---|---|---|---|---|
| 1 | quality | 代码质量 | 0.12 | 100 | ≥99 |
| 2 | physics | 物理/数值 | 0.12 | 100 | ≥99 |
| 3 | ux | 使用手感 | 0.15 | 100 | ≥99 |
| 4 | visualization | 可视化追踪 | 0.15 | 100 | ≥99 (≥36 PNG · was ≥30) |
| 5 | smoke | 端到端 | 0.08 | 100 | ≥99 |
| 6 | functional | 功能完整度 | 0.08 | 100 | ≥99 (6 sub-DECs · **10 Done dims** · was 9) |
| 7 | stability | 稳定性 | 0.08 | 100 | ≥99 |
| 8 | cfd_breadth | CFD全维度 | 0.08 | 100 | ≥99 |
| 9 | novice | 新手难度 | 0.07 | 100 | ≥99 |
| 10 | industrial_ui | 工业UI对标 | 0.07 | 100 | ≥99 (+real_data_wired subscore · +journey_test subscore) |
| 11 | **interaction_polish** | **交互体验** | **0.07** | **N/A** | **≥99** (NEW pillar · 4 subscores) |

Sum of weights: 0.12+0.12+0.15+0.15+0.08+0.08+0.08+0.08+0.07+0.07+0.07 = **1.07** (informational; min one-vote-veto is the gate).

## 4 · 10 Done dims (was 9 · V72 adds DONE-10)

- DONE-1 · `CaseBrowserV3` wires to `/api/cases` real list (replaces hardcoded 11 cases)
- DONE-2 · `Step1Inspector` wires to `/api/cases/:id` real metadata
- DONE-3 · `TruthChainContent` already wires to `/api/cases/:id/completeness` — verify still working post-route hoist
- DONE-4 · Keyboard navigation spec PASS: Tab cycles activity-bar → left → pipeline → viewport → canvas → right · Esc closes overlays · ⌘K opens palette
- DONE-5 · Motion polish: ≥12 transition-* usages in v3 components · `prefers-reduced-motion` respected
- DONE-6 · Focus management: ≥20 ARIA/role/tabIndex usages · autoFocus on tab change
- DONE-7 · `user-journey-v3.spec.ts` exercises Steps 1→2→3→4→5 + tab switches + advisor consult · PASS
- DONE-8 · 6 new visual baselines (31-36) locking keyboard-focus + motion-mid + advisor-expanded + cross-tab states
- DONE-9 · NEW Pillar 11 (interaction_polish) at ≥99
- DONE-10 · 11-pillar fleet 2-consecutive close

## 5 · 6 sub-DECs

- **V72.1 · CaseBrowser + Step1Inspector real-data wire** — backend already exposes /api/cases
- **V72.2 · Keyboard navigation** — `useKeyboardShortcuts` hook + Tab cycle + Esc handler
- **V72.3 · Motion polish + reduced-motion respect** — Tailwind transition utilities + global CSS
- **V72.4 · Focus management + ARIA** — autoFocus on tab change + comprehensive ARIA
- **V72.5 · Sub-agent test harness** — `user-journey-v3.spec.ts` + autonomous-test-agent.md doc
- **V72.6 · 6 visual baselines (31-36) + V72 close DEC + retro**

## 6 · Anti-fraud frame (carried from V71)

- Displayed numbers must match displayed verdicts
- Static-demo-data must be explicitly disclosed in DECs (no silent claims of "real")
- Real-data wiring must use actual backend endpoints (no fake fetches that return hardcoded JSON)
- New pillar 11 must compute its score from actual file evidence (not preset)

## 7 · Reverse-stops

- MUTATING_ROUTES net diff > 0 (locked at 9 since V70)
- Any new auto-execute button in any v3 surface (V130/V132 contract)
- Pillar 6 (functional) regresses below 99 (V71 close was 100)
- Any pre-existing 30 visual baselines drift > 0.05 SSIM
- V72 introduces a new persistent panel (4-panel + collapsible bottom is locked)
- Sub-agent test harness asserts false success (e.g., screenshot a stale state and claim journey complete)

## 8 · Counter

V72 charter = autonomous_governance: true → counter +1. V72 expected delta: charter + 6 sub-DECs + close = +8 (matches V71's arc size).

## 9 · Substrate inventory

Already on disk:
- 21 files in `ui/frontend/src/pages/workbench/v3/`
- 30 PNG baselines locked (V71.6)
- 427 vitest tests + 30 playwright baselines
- Tailwind v3.* tokens
- 7 DECs (V71 charter + 6 sub + close)
- 6 score iters (V71_iter_0..6)

V72 builds on top — no greenfield architecture.

## 10 · Acceptance criteria

V72 closes when:
- All 6 sub-DECs LANDED
- All 10 Done dims MET
- 11-pillar fleet at min ≥99 on 2 consecutive iters
- Sub-agent journey test PASSES (proves human-equivalent user journey works end-to-end)
- 36 PNG baselines (30 existing + 6 new) stable

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
