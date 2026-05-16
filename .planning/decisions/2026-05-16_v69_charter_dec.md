---
decision_id: DEC-V69-charter
title: V69 charter · Canonical Advisor Eval Regression Harness + Backend Hardening + Pillar 6/7 Lift
status: Accepted
parent_dec: DEC-V68-C-close
phase: V69
notion_sync_status: pending
predecessor: DEC-V68-C-close
batch: B151
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: none (charter)
substrate: V68-C close · V66-B eval set 15/20 partial · 14 pre-existing backend test failures inherited
---

# DEC-V69-charter · V69 arc launch

## 1 · Decision

Launch V69 "Canonical Advisor Eval Regression Harness + Backend Hardening + Pillar 6/7 Lift" — the 5th V110 advisor-class arc application.

Charter scope (C+F+E core · D continued spike):
- **C (core)**: Finish canonical eval set 15→20 + author regression harness (`test_canonical_advisor_eval.py`) that runs each catalogued case through `assemble_stack` and asserts expected V-row attribution + rule firings · this is the **AI advisor SSOT** Pillar 7 lift driver
- **F (followup)**: Triage 14 pre-existing backend test failures inherited from V68-A/B/C (g1 / geometry_ingest / meshing_gmsh / n6_2_ai_review / n6_3_ai_diagnose) — split into fix vs document-with-tracking-task
- **E (extension)**: 4 e2e specs against real backend exercising the eval-harness + advisor regression smoke + post-V68-C UI surface stability
- **D (deferred)**: V68-D WASM still parked (iter-2 conclusion: 5-question gate still no answer)

Pillar 6 target: 98 → 99 · Pillar 7 target: 85 → 88 · weighted +0.4 ceiling.

## 2 · User mandate (verbatim)

> "全都要。继续构建下一个阶段的蓝图，然后批准授权你全权开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观），一直迭代开发下去，直至达到你（主开发会话）眼里的优秀水准（99分以上）"

5th invocation of the standing mandate. Same fleet pattern (7 agents) with tightened V69 criteria.

## 3 · North Star

> "工程师 cd .planning/evals/canonical/; ls 看到 E01..E20 全部 20 个 case 文件（不再有 batched）。运行 `uv run pytest ui/backend/tests/test_canonical_advisor_eval.py -v` 在 5 秒内看到 20/20 PASS · 每个 case 报告它跑出的 advisor rule fire 列表 vs YAML frontmatter 里的 expected. CI 加 gate: 任何 advisor_stack 改动让 ≥1 个 canonical case regress · PR 必须解释 + 更新 expected_verdict_signature 或 revert. 同时 `pytest ui/backend/tests/ -q` 输出从 `14 failed, 2206 passed` 减少到 ≤7 failed (至少减半) · 每个剩余 failure 有对应的 tracking task 文件 in `.planning/followups/`."

## 4 · Done dim checklist (7 dims · FULL delivery)

- [ ] **V69-DONE-1 · Canonical eval set 20/20** — 5 more case files authored (E03-E15 batched split into individual files OR 5 new V108+ cases) + frontmatter schema validated
- [ ] **V69-DONE-2 · Eval regression harness** — `test_canonical_advisor_eval.py` runs all 20 cases through `assemble_stack`, asserts V-row attribution + rule firings · ≤5s total runtime
- [ ] **V69-DONE-3 · Backend pre-existing failure triage** — 14 failures → ≤7 (at least halved) · each remaining failure has tracking task file
- [ ] **V69-DONE-4 · AI advisor SSOT regression-protected** — eval harness is part of `pytest ui/backend/tests/` default run · changes to advisor_stack that regress any canonical case fail CI
- [ ] **V69-DONE-5 · StrictMode flakiness root-cause** — either fix it (re-enable /workbench/case/:id playwright) OR document the root-cause + workaround in `.planning/followups/`
- [ ] **V69-DONE-6 · E2E against real backend (extended)** — 47+ e2e PASS (+4 V69 specs: eval-harness wire / advisor regression smoke / V69 surface stability / V68-C inheritance verification)
- [ ] **V69-DONE-7 · Pillar 6 ≥99 + Pillar 7 ≥88 dual re-anchor** — SCORING-FRAMEWORK.md updated with per-driver delta accounting

## 5 · Sub-DEC progress

- [ ] **V69.1 · Canonical eval set completion + frontmatter schema** — 5 new files + schema validator
- [ ] **V69.2 · Eval regression harness** — test_canonical_advisor_eval.py + advisor_stack pinning
- [ ] **V69.3 · Backend pre-existing failure triage** — fix-or-track 14 failures
- [ ] **V69.4 · E2E + StrictMode investigation + close** — 4 new playwright + close DEC

## 6 · Fleet criteria (further tightened vs V68-C)

| # | Agent | V68-C criteria | V69 criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | (unchanged) |
| 2 | Physics | mass_balance+corpus+bc+whitelist≥11 | **+ canonical eval pass ≥20 cases** (new sub-score) |
| 3 | UX/Playability | ≥9 specs PASS | **≥11 specs PASS** for FULL flow=60 |
| 4 | Visualization | ≥4 viewport + ≥16 PNG | **≥18 PNG** (+2 V69 surfaces) |
| 5 | Smoke | + 3 endpoint probes | **+ canonical eval harness pytest sub-probe** |
| 6 | Functional | 4/4 LANDED + 7/7 Done | (unchanged formula) |
| 7 | Stability | vitest flake | (unchanged) |

## 7 · Iteration tracker

| Iter | Date | min(7) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V69 baseline) | 2026-05-16 | TBD | TBD | TBD | charter LANDED · 0/4 sub-DECs · 0/7 Done · expected drops: physics (canonical 0<20) · viz (16<18 pro-rated) · smoke (eval probe pending) | `.planning/scores/V69_iter_0.md` |

## 8 · Reverse-stop log

- V132 `MUTATING_ROUTES` net diff > 0
- canonical eval harness exposes a real advisor_stack regression (PR for V69 itself causes a canonical case to fire wrong rules)
- backend triage adds NEW failures while attempting to fix existing ones
- StrictMode "investigation" turns into a 4-hour deep refactor that blocks other arc work
- pixel-diff 0.01 threshold causes existing 16 baselines to fail
- pre-existing 14 failures resist all reasonable triage (every fix attempt fails)

## 9 · Counter telemetry

- V69 charter: B151
- V69.1: B152 estimated
- Subsequent: B153-B158 estimated

— V69 charter · 2026-05-16
