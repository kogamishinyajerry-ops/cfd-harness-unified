---
decision_id: DEC-V67-C-charter
title: V67-C "Product Workbench UI Build-out" arc charter · Pillar 6 Engineer UX 55→90+ · 7-agent fleet · ≥99 score iteration mandate
status: Accepted
parent_dec: DEC-V67-D-extension
phase: V67-C
notion_sync_status: pending
predecessor: DEC-V67-D-extension
batch: B117
confidence: high
autonomous_governance: true
verdict: ARC_CHARTER_ACCEPTED
v_row_landed: none (charter)
substrate: blueprint v3 §4 + ~/Downloads/cfd_harness_workbench_ui_concept.svg + ui/frontend/src/pages/workbench/ (StepPanelShell + 5 steps + step_panel_shell/*)
---

# DEC-V67-C-charter · V67-C "Product Workbench UI Build-out"

## 1 · Decision

Launch successor arc **V67-C "Product Workbench UI Build-out"** targeting **Pillar 6 (Engineer UX 55→90+)** with explicit user mandate from 2026-05-16 evening session: *"全权开发 · 专门测试子 agent · 真实测评功能/使用手感/可视化追踪 · 明确完成度评分机制（绝对诚实客观）· 一直迭代直至 99 分以上"*.

V67-C is the **first arc explicitly user-mandated to chase ≥99 score** (project-internal scoring framework target is 95; user target is stricter at 99 in V67-C scope).

## 2 · Rationale · why Pillar 6 now

Post V67-D extension, project weighted score = **75.30 / 95** with these Pillar gaps:

| Pillar | Weight | Current | Headroom raw | Headroom weighted | V67-C target? |
|---|---|---|---|---|---|
| 1 Validation maturity | 30% | 56 | 44 | +13.2 | ❌ needs sandbox compute · multi-session |
| 2 Corpus depth | 20% | 90 | 10 | +2.0 | ❌ saturated |
| 3 Advisor stack | 15% | 86 | 14 | +2.1 | ❌ V66-B saturated |
| 4 Reproducibility | 10% | 91 | 9 | +0.9 | ❌ V67-D saturated |
| 5 Governance | 10% | 89 | 11 | +1.1 | ❌ saturated |
| **6 Engineer UX** | **10%** | **55** | **45** | **+4.5 ⭐** | ✅ **V67-C primary lever** |
| 7 AI-advisor SSOT | 5% | 82 | 18 | +0.9 | ❌ V66-B saturated |

**Pillar 6 = highest autonomous-feasible weighted headroom + perfect alignment with user-mandate emphasis on "使用手感 + 可视化追踪"**. Pillar 1's 13.2 ceiling is technically larger but requires sandbox compute (V67-A demonstrated unreliable in single autonomous session).

Substrate readiness: Frontend skeleton **already exists** (StepPanelShell + 5 Step bodies + Viewport lazy-load + AIAdvisorPanel + AICoachPanel + CompletenessCard + step_panel_shell/__tests__ 224+ green) — V67-C is **打磨 + 整合 + visibility** work, not greenfield build.

## 3 · North Star (1 sentence)

> "工程师打开 `/workbench/case/{id}`，5-step spine 视觉清晰可点，TopBar 6 字段（case · OF truth · TrustGate · LLM offline · Audit % · AI=advisor）全可见，Engineer Control Rail（Beginner/Power + CompletenessCard）整合到位，Viewport mode（geometry / mesh wireframe / BC faces / field slice / residuals / report grid）流畅切换，AI panel 严格 advisory-only（无 mutating button），30 分钟从 Import 走到 Results 不卡顿不困惑。"

## 4 · Done Definition (8 dims · all required for V67-C close · matched to 7-agent fleet)

| # | Done dim | Threshold | Verification source |
|---|---|---|---|
| 1 | TopBar 6-field information density | Blueprint v3 §4 (case · OF truth · TrustGate · LLM offline · Audit % · AI=advisor) all visible + tested | `TopBar.test.tsx` + Playwright `topbar.spec.ts` + visual snapshot |
| 2 | StatusStrip live indicators | progress · current step status · trust state · last action — 4 live fields | `StatusStrip.test.tsx` + Playwright |
| 3 | Engineer Control Rail integrated | Beginner/Power toggle on every step · CompletenessCard top-fixed · advanced disclosure | `__tests__/EngineerControlRail.test.tsx` + Playwright + visual snapshot |
| 4 | 5-step spine visual polish | step status indicators (✓/●/○) · transition animations · Apple-tier visual consistency | `StepPanelShell.test.tsx` + Playwright + visual diff baseline |
| 5 | Viewport mode switching | geometry/mesh/BC/field/residuals/report-grid · ≤200ms transition · no z-fighting | `Viewport.test.tsx` + Playwright `viewport-mode.spec.ts` |
| 6 | AI panel strict advisory-only | no `Apply` button · copy-paste UX · V132 MUTATING_ROUTES registry net diff = 0 | static grep + Code Quality agent + Playwright button-presence test |
| 7 | Truth Chain visibility across 5 steps | TopBar field "OF truth" updates per step · audit % rolls forward · TrustGate state surfaces consistently | Playwright `truth-chain.spec.ts` full-flow test |
| 8 | Pillar 6 ≥90 (re-anchor) | scoring framework v1.0 Pillar 6 anchor language matches `90-100` zone | this DEC §10 + retro |

**Close gate**: 8/8 Done dims MET via honest accounting per scoring framework v1.0 + fleet score min(7 dims) ≥99.

## 5 · Sub-DEC seeds (6 sub-DECs · serial sequencing)

### V67-C.1 · TopBar 6-field upgrade (Done dim #1 + #7)
- Scope: extend `TopBar.tsx` 2 fields → 6 fields per blueprint v3 §4
- LOC est: ~120 prod (TopBar 50→170) + 80 test
- Confidence: med
- Scope class: sub-DEC (cross 2 modules · TopBar.tsx + Viewport state contract)

### V67-C.2 · StatusStrip live indicators (Done dim #2)
- Scope: 4 live indicator fields + SSE subscription for current step status
- LOC est: ~80 prod + 60 test
- Confidence: med
- Scope class: sub-DEC

### V67-C.3 · Engineer Control Rail integration (Done dim #3)
- Scope: Beginner/Power toggle Context + CompletenessCard top-fixed in TaskPanel + advanced-disclosure pattern on all 5 step bodies
- LOC est: ~200 prod (new BeginnerPowerToggleContext + 5 step body wraps) + 150 test
- Confidence: med
- Scope class: sub-DEC (cross 6 modules · context + 5 steps · charter-class candidate but stays sub-DEC because no schema break)

### V67-C.4 · 5-step spine visual polish (Done dim #4)
- Scope: StepTree step indicators (status icons + transition states) + StepPanelShell layout consistency pass + Apple-tier visual review
- LOC est: ~150 prod (StepTree polish + StepPanelShell CSS) + 100 test + visual snapshot baseline
- Confidence: med
- Scope class: sub-DEC

### V67-C.5 · Viewport mode switching (Done dim #5)
- Scope: 6-mode dispatcher in StepPanelShell · per-step Viewport `format` prop wiring · ≤200ms transition guarantee · z-buffer / camera reset discipline
- LOC est: ~180 prod + 140 test
- Confidence: med
- Scope class: sub-DEC (cross 3 modules · Viewport.tsx + StepPanelShell + step bodies)

### V67-C.6 · AI panel advisory-only audit + visualization tracking (Done dim #6 + #7)
- Scope: grep + Playwright audit of AIAdvisorPanel + AICoachPanel · ensure no Apply/Mutate buttons · copy-paste UX polish · MUTATING_ROUTES registry diff guard · Truth Chain end-to-end Playwright test
- LOC est: ~100 prod (panel audit + copy-paste UX) + 200 test (Playwright suite)
- Confidence: med
- Scope class: sub-DEC

**Total estimate**: ~830 prod LOC + ~730 test LOC + Playwright suite addition · 8-15 commits · single-session feasible if iter cap ≤10 holds.

## 6 · 7-agent fleet · the test apparatus

Per user mandate ("专门测试子 agent · 真实测评 · 绝对诚实客观"), V67-C deploys 7 independent testing agents (no shared transcript · scoring is script-output, not agent-sentiment):

| # | Agent | Backing implementation | Dimension | Score formula (0-100) |
|---|---|---|---|---|
| 1 | **Code Quality** | `codex-review-relay --base origin/main` (86gs gpt-5.4 xhigh) | 代码质量 / 产物质量 | `pytest_pass_rate × 100 − P1×20 − P2×5` (clip [0,100]) |
| 2 | **Physics Validator** | Sonnet subagent + pytest `tests/test_checkmesh_runner.py` + `test_bc_writer_mass_balance.py` regression | 物理/数值稳定 | `(checkMesh_pass + mass_balance_pass + V_row_regression_pass_rate) / 3 × 100` |
| 3 | **UX/Playability** ⭐ | Playwright headless + flow-step latency + jank detector | 使用手感 | `(flow_completion_rate × 60) + (latency_p95_under_200ms × 25) + (no_blocker_clicks × 15)` |
| 4 | **Visualization** ⭐ | Playwright screenshot diff + Viewport mode-switch success rate + image-diff baseline | 可视化追踪 | `(render_success_rate × 50) + (mode_switch_correctness × 30) + (visual_diff_within_baseline × 20)` |
| 5 | **E2E Smoke** | Bash + `scripts/smoke/dogfood_loop.py` + 1 industrial case rerun + frontend `npm run build` + typecheck + lint | 端到端 pipeline | `(smoke_pass × 40) + (frontend_build_pass × 30) + (typecheck_pass × 20) + (lint_pass × 10)` |
| 6 | **Functional Checklist** | Main session inspect git log + DEC frontmatter Status + Done dim verification | 功能完整度 | `(LANDED_sub_DEC_count / 6) × 70 + (Done_dim_MET_count / 8) × 30` |
| 7 | **Stability** | Bash long-run (N=20 Playwright iter no flake) + edge-case suite + memory leak detector | 稳定性 | `100 − crash_count×30 − flaky_count×10 − memory_growth_pct×5` (clip [0,100]) |

### Total score formula

```
fleet_score = min(score_1, score_2, score_3, score_4, score_5, score_6, score_7)
```

**一票否决**. 任一维度 < 99 = 触发下一轮迭代修复**该维度**.

### Honesty enforcement (5 hard rules · embedded in fleet scripts)

1. **失败原文必须粘** — stderr 关键段 verbatim 入 `.planning/scores/V67-C_iter_N.md`
2. **每分必有 evidence** — test name / commit SHA / log line / Playwright trace path
3. **0 不是 default** — 分数必须计算，不许"未跑就 0"
4. **下降允许** — 本轮 < 上轮诚实记录，不允许 score 膨胀
5. **min() 一票否决** — 不允许"3 维高 + 1 维低"被平均掩盖

### 反 22-轮陷阱机制 (3-tier protection)

1. **Sub-DEC level Codex round cap = 3** (inherited from v2.3 V133)
2. **Iter-level cap = 10** — ≥10 轮未达 99 → 主 session 必须 explicit 报告"why no convergence" + user 抉择 continue/accept/redesign
3. **Plateau detector** — every 5 iter check "scoring max-min < 5" → 标记"原地踏步" + 强制方向重审

### 反 persona dogfood 回流

- E2E Smoke agent (#5) 必须 ≥1 真实 industrial case (不允许 LDC/backward_step 作主测)
- UX/Playability (#3) 测试场景必须包含 ≥1 完整 Import→Mesh→BC→Solve→Results pipeline

### 反 AI 越权回流

- Code Quality agent (#1) hard-check: V132 `MUTATING_ROUTES` registry diff = 0
- 净增任何 mutating route 触发 automatic P1 (∝ blast radius)

## 7 · Iteration loop (mandatory protocol)

```
[起点] V67-C charter LANDED · baseline iter 0 score
   ↓
[Iter N] (触发式 · 无日历)
   ↓
A. Dev sub-DEC (Opus 主导 · Codex 仅 1-sync-trigger 触发即审)
   ↓
B. Trigger fleet (7 agent 并行 · 单条消息多 tool call)
   ↓
C. Score & log .planning/scores/V67-C_iter_N.md (8 节: 7 维 + summary)
   ↓
D. fleet_score = min(7) ?
   ├─ < 99 → identify lowest dim → its failing case → 回 A
   └─ ≥ 99 (持续 2 iter) → §8 Close
```

## 8 · V67-C close protocol

V67-C closes when:
- 8/8 Done dims MET per honest accounting
- fleet_score ≥ 99 持续 2 consecutive iter on stable code (no source change between iter)
- Codex APPROVE on any 1-sync-trigger PR (auth / signing / security boundary)
- Pillar 6 re-anchor ≥ 90 verified

Close DEC writes to `.planning/decisions/2026-05-XX_v67c_close_dec.md` + retro to `.planning/retrospectives/2026-05-XX_v67c_close_retro.md` + Notion batch sync (Accepted DECs only per v2.3).

## 9 · 4Q gate baseline answers (V67-C scope-wide · MUST be reaffirmed per sub-DEC PR)

| Q | A | Justification |
|---|---|---|
| LLM 离线工程师能完成 5-step pipeline ? | ✓ YES | UI work doesn't introduce LLM dependency; AI panel is advisor-overlay, base pipeline (Import/Mesh/BC/Solve/Results) is LLM-offline |
| 这一步有 artifacts 输出 ? | ✓ YES | OpenFOAM artifacts unchanged by UI work; UI surfaces artifacts via existing routes (case_visualize / field_artifacts / geometry_render) |
| TrustGate / completeness / audit trail 解释可信度 ? | ✓ YES | V67-C dim #7 (Truth Chain visibility) explicitly delivers this; TopBar Audit % field surfaces audit roll-up |
| AI 仅 advisory · 不调 mutating route ? | ✓ YES | V67-C dim #6 (AI panel advisory-only audit) explicitly hardens this; Code Quality agent enforces MUTATING_ROUTES diff = 0 |

## 10 · Scoring framework v1.0 Pillar 6 anchor language

Per `.planning/SCORING-FRAMEWORK.md`:

- **55-69 zone (current)**: "Workbench skeleton exists · 5-step spine renders · Viewport lazy-loads · individual step bodies functional · BUT visual cohesion uneven · Truth Chain not visible · Beginner/Power toggle absent · AI panel may have unguarded surfaces"
- **70-84 zone**: "Visual cohesion uniform · TopBar carries 4+ fields · StepTree status indicators · Engineer Control Rail concept present in ≥1 step"
- **85-100 zone**: "TopBar 6 fields · Engineer Control Rail uniform across 5 steps · Truth Chain visible in TopBar + StatusStrip · Viewport mode switching ≤200ms · AI panel strict advisory-only · visual snapshot baseline + diff < 5% across 8 canonical UI states"

**V67-C target**: re-anchor to **90** (within 85-100 zone) with documented Playwright + visual diff evidence.

## 11 · Reverse-stop triggers (must immediately surface to user, do NOT autonomously resolve)

- V132 `MUTATING_ROUTES` registry net diff > 0 (any new mutating route added by AI panel)
- Beginner mode 失效 (Beginner toggle breaks step body rendering)
- Persona dogfood drift (E2E Smoke agent reverts to LDC-only testing)
- Plateau over 5 iter with max-min < 5 (forced redesign signal)
- Codex round cap=3 hit on 1-sync-trigger PR (security boundary blocker)

## 12 · v2.3 governance compliance

- **DEC scope**: charter-class (cross 6+ frontend modules · governance-mandate change "≥99 score iteration") → full DEC schema ✓
- **Codex 1-sync-trigger**: NOT applicable in baseline V67-C scope (no security boundary changes in pure UI work); sub-DECs evaluated individually
- **Kogami opt-in**: invoked once at charter level for independent strategic review (user mandate "全权" implies trust but charter-class warrants 2nd opinion)
- **Confidence**: high (charter) · per sub-DEC: med (UI work has subjectivity)
- **Counter**: autonomous_governance=true · +1 (consolidating future B118-B125+ batches)
- **Notion**: session-end batch sync · Accepted-only per V133

## 13 · Substrate dependencies

V67-C depends on (verified present 2026-05-16):
- `ui/frontend/src/pages/workbench/StepPanelShell.tsx` ✓
- `ui/frontend/src/pages/workbench/step_panel_shell/{TopBar,StatusStrip,CompletenessCard,StepTree,TaskPanel,AIAdvisorPanel,AICoachPanel}.tsx` ✓
- `ui/frontend/src/visualization/Viewport.tsx` (lazy-loaded) ✓
- `ui/frontend/package.json` (vite + vitest + typecheck + lint scripts) ✓
- 224+ green frontend tests baseline ✓
- `scripts/smoke/dogfood_loop.py` ✓
- `codex-review-relay` (`~/.codex-relay`) ✓
- v2.3 governance scripts (`scripts/governance/`) ✓

V67-C will ADD:
- `scripts/governance/v67c_fleet/` with 7 score scripts + `score_all.sh` aggregator
- `ui/frontend/playwright.config.ts` + `ui/frontend/e2e/*.spec.ts` (Playwright bootstrap)
- `ui/frontend/__visual_baselines__/` (visual diff baseline)
- `.planning/scores/V67-C_iter_N.md` per iteration

## 14 · Counter telemetry

- V65-A: 28 sub-DECs (B72-B99) autonomous_governance=true
- V66-B: 7 sub-DECs (B100-B106) autonomous_governance=true
- V67-A: 8 sub-DECs (B107-B114) autonomous_governance=true
- V67-D: 2 sub-DECs (B115-B116) autonomous_governance=true (charter+close in 1 DEC + extension)
- V67-C charter: B117 autonomous_governance=true (this DEC)
- V67-C est: B118-B130 (6 sub-DEC × ~2 batch each = ~12 batches)

## 15 · Out of scope (explicit non-goals)

- **NOT** rebuilding StepPanelShell from scratch (existing skeleton is sound)
- **NOT** adding 6th step to spine (blueprint §7 forbids)
- **NOT** adding sibling "AI Workbench" page (blueprint §7 forbids)
- **NOT** introducing LLM dependency to base pipeline (V130 violation)
- **NOT** touching trust-core surfaces (`src/audit_package/`, `src/auto_verifier/`, `src/convergence_attestor.py`) — V67-C is frontend + governance scripts only
- **NOT** Pillar 1 industrial FULL push (V67-E territory if revived)

— Claude Code (Opus 4.7 1M) · B117 · V67-C charter · 2026-05-16
