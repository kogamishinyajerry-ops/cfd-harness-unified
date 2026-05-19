---
decision_id: DEC-V70-charter
title: V70 charter · CFD Capability Breadth × Novice Onboarding × Industrial-UI Benchmark · 10-pillar fleet
status: Accepted
parent_dec: DEC-V69-close
phase: V70
notion_sync_status: pending
predecessor: DEC-V69-close
batch: B159
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: none (charter)
substrate: V69 close · 7-pillar fleet stable at 100/100 · user mandate (6th invocation) expands scoring to 10 pillars
---

# DEC-V70-charter · V70 arc launch · expanded 10-pillar scoring

## 1 · Decision

Launch V70 "CFD Capability Breadth × Novice Onboarding × Industrial-UI Benchmark" — the **6th V110 advisor-class** application + the FIRST arc to extend the fleet from 7 → **10 pillars** per user mandate (6th "全都要" invocation, 2026-05-16):

> "要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且**维度充足**，包括**CFD仿真全维度能力**，包括**新手人类用户的使用难度、交互模式**，包括**UI设计是否能对标顶级工业软件**）"

The 3 new pillars are explicitly user-named and orthogonal to the existing 7:

| New Pillar | Name | Weight | Driver |
|---|---|---|---|
| **8** | CFD-Capability-Breadth | 0.08 | Workbench's CFD regime coverage (turbulence × compressibility × steadiness × meshing × BCs) |
| **9** | Novice-Onboarding | 0.07 | First-time engineer's time-to-first-success · error recovery · tutorial coverage |
| **10** | Industrial-UI-Benchmark | 0.07 | Comparison against top-3 commercial CFD GUIs (ANSYS Fluent · STAR-CCM+ · SimScale) |

Existing 7 pillars retain weights (rebalanced to make room): quality 0.12 · physics 0.12 · ux 0.16 · viz 0.16 · smoke 0.08 · functional 0.08 · stability 0.08. Total weight = 1.00.

## 2 · North star (verifiable end-state)

> 工程师在没有教程的情况下，10 分钟内完成第一次 lid_driven_cavity 全流程仿真。
> 同时一个 CFD 老手在 5 分钟内能从 workbench 跑出 NACA 0012 翼型在 Re=3M 的 RANS k-omega-SST 收敛解。
> 同时把 workbench 截图甩给 ANSYS Fluent / STAR-CCM+ 重度用户看，**至少 1 个用户在 6 个 UI 评估维度上的 3 个维度给出 "comparable or better than commercial" 评分**。
> 同时 V69 已建立的 advisor SSOT 规模扩展到 ≥30 canonical eval cases · 覆盖 ≥4 turbulence models × ≥3 compressibility regimes × ≥2 steadiness regimes.

## 3 · Done dim checklist (9 dims · all required for V70 close · FULL delivery only)

- [ ] **V70-DONE-1 · CFD capability matrix** — `.planning/cfd_capability_matrix.md` enumerates supported regimes (turbulence × compressibility × steadiness × meshing) with PR/non-PR cell status; ≥80% cells PR or explicit gap-tracked
- [ ] **V70-DONE-2 · Canonical eval set 20→30** — 10 new individual case files covering ≥4 turbulence models × ≥3 compressibility regimes
- [ ] **V70-DONE-3 · Novice onboarding artifacts** — `/workbench/tutorial` route + ≥6 tooltips on Engineer Control Rail + first-time-user banner pointing to lid_driven_cavity as starter
- [ ] **V70-DONE-4 · Industrial-UI benchmark report** — `.planning/benchmarks/industrial_ui_benchmark.md` evaluates workbench on 6 axes against ANSYS Fluent + STAR-CCM+ + SimScale + lands top-3 improvements
- [ ] **V70-DONE-5 · 3 new fleet agents wired** — `score_cfd_breadth.sh` + `score_novice_onboarding.sh` + `score_industrial_ui.sh` produce structured JSON; merged into `score_all.sh`
- [ ] **V70-DONE-6 · SCORING-FRAMEWORK Pillar 8/9/10 anchor zones** — each new pillar gets 0-100 anchor table + initial position evidence-backed
- [ ] **V70-DONE-7 · E2E coverage for new artifacts** — ≥3 V70 e2e specs (tutorial route mount + tooltip presence + first-time banner)
- [ ] **V70-DONE-8 · 4 new visual baselines** — 18 → 22 PNG (tutorial · tooltip · first-time banner · dark-mode toggle OR equivalent V70-introduced surface)
- [ ] **V70-DONE-9 · Pillar 6 99 → 99.5 + Pillar 7 88 → 90 + Pillar 8/9/10 floor** — close DEC documents per-driver delta; weighted score ≥ 95

## 4 · Sub-DEC seeds (≥5 expected; charter §5 enforces ≥5 not "exactly 5")

| Sub-DEC | Title | Driver pillar |
|---|---|---|
| V70.1 | CFD capability matrix audit + 1 missing regime closure | Pillar 8 |
| V70.2 | Canonical eval set 20→30 (10 new individual files · ≥4 turb × ≥3 compressibility) | Pillars 2, 7, 8 |
| V70.3 | Novice onboarding: tutorial route + tooltips + first-time banner | Pillar 9 |
| V70.4 | Industrial-UI benchmark report + top-3 improvements landed | Pillar 10 |
| V70.5 | Fleet agents 3 new + framework anchor zones | Pillars 8, 9, 10 + meta |
| V70.6 | E2E + 4 visual baselines + arc close | Pillars 3, 4 + close |

## 5 · Fleet criteria (further tightened vs V69)

| # | Agent | V69 criteria | V70 criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | (unchanged) |
| 2 | Physics | + canonical eval ≥20 | **+ canonical eval ≥30** |
| 3 | UX/Playability | ≥11 specs PASS | **≥13 specs PASS** (+2 tutorial e2e) |
| 4 | Visualization | ≥18 PNG | **≥22 PNG** (+4 V70 surfaces) |
| 5 | Smoke | + canonical harness pytest | (unchanged) |
| 6 | Functional | 4/4 sub-DECs · 7/7 Done | **6/6 sub-DECs · 9/9 Done** |
| 7 | Stability | vitest 3-run flake check | (unchanged) |
| **8 NEW** | CFD-Breadth | n/a | turbulence ≥4 · compressibility ≥3 · steadiness ≥2 · BC types ≥10 · meshing ≥2 |
| **9 NEW** | Novice-Onboarding | n/a | tutorial route · 6 tooltips · first-time banner · novice e2e ≥1 · onboarding doc ≥1000 words |
| **10 NEW** | Industrial-UI-Benchmark | n/a | benchmark doc · 6 axes evaluated · 3 GUIs compared · ≥3 improvements LANDED · 2 new visual baselines |

## 6 · Reverse-stop log

- V132 `MUTATING_ROUTES` net diff > 0
- Capability matrix audit reveals workbench **cannot run** a regime the V-series claims it can (structural fraud signal)
- Onboarding tutorial unable to complete in <10 minutes by a fresh Claude Code session (= acts as novice proxy)
- Industrial UI benchmark report drifts into pure marketing (no honest "ANSYS still better at X" findings)
- New fleet agents introduce flakiness that destabilizes existing 7-pillar stable score
- ≥3 of 10 new canonical eval cases fail to PARSE (vs FIRE) the canonical harness on first run

## 7 · Counter telemetry projection

| Counter | Projection |
|---|---|
| autonomous_governance_counter_v61 tick | +7 (charter + 6 sub-DECs + close) |
| V110 advisor-class arc applications | 6 (V67-C + V68-A + V68-B + V68-C + V69 + V70) |
| MUTATING_ROUTES at close | 9 (V132 invariant locked · onboarding adds GET routes only) |
| Charter Q4 violations | 0 (4Q gate must hold) |

## 8 · Confidence: high

- 10-pillar fleet is the user's explicit expansion mandate — not Claude-invented scope
- All 3 new pillars have computable subscores (no subjective fleet judgment)
- Industrial-UI benchmark involves authored doc (human-readable) but scoring is artifact-presence-based (objective)
- V69 100/100 substrate gives runway to absorb 3 new pillars while keeping ≥99 min(10) target

— V70 charter · 2026-05-16 · B159
