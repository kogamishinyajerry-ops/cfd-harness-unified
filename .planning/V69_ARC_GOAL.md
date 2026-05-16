# ARC-GOAL · V69 Canonical Advisor Eval Regression Harness + Backend Hardening · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v69_charter_dec.md` (Accepted B151 · 2026-05-16)
> **Predecessor**: DEC-V68-C-close (B150 · iter-4 100/100 ratified · Pillar 6 98 · Pillar 7 85)
> **Target**: Pillar 6 98→99 + Pillar 7 85→88 · weighted +0.4 ceiling
> **User mandate** (5th invocation): "全都要" · C+F+E core, D continued spike

## North Star (charter §3 verbatim)

> "工程师 cd .planning/evals/canonical/; ls 看到 E01..E20 全部 20 个 case 文件（不再有 batched）。运行 `uv run pytest ui/backend/tests/test_canonical_advisor_eval.py -v` 在 5 秒内看到 20/20 PASS · 每个 case 报告它跑出的 advisor rule fire 列表 vs YAML frontmatter 里的 expected. CI 加 gate: 任何 advisor_stack 改动让 ≥1 个 canonical case regress · PR 必须解释 + 更新 expected_verdict_signature 或 revert. 同时 `pytest ui/backend/tests/ -q` 输出从 `14 failed, 2206 passed` 减少到 ≤7 failed (至少减半) · 每个剩余 failure 有对应的 tracking task 文件 in `.planning/followups/`."

## Done dim checklist (7 dims · all required for V69 close · FULL delivery only)

- [ ] **V69-DONE-1 · Canonical eval set 20/20** — 5 more case files authored · frontmatter schema validated
- [ ] **V69-DONE-2 · Eval regression harness** — `test_canonical_advisor_eval.py` runs all 20 cases · ≤5s total runtime
- [ ] **V69-DONE-3 · Backend pre-existing failure triage** — 14 → ≤7 · each remaining failure has tracking task
- [ ] **V69-DONE-4 · AI advisor SSOT regression-protected** — eval harness in default pytest run · advisor_stack regressions fail CI
- [ ] **V69-DONE-5 · StrictMode flakiness root-cause** — fix it OR document workaround
- [ ] **V69-DONE-6 · E2E against real backend (extended)** — 47+ e2e PASS (+4 V69 specs)
- [ ] **V69-DONE-7 · Pillar 6 ≥99 + Pillar 7 ≥88 dual re-anchor** — SCORING-FRAMEWORK.md updated

## Sub-DEC progress

- [ ] **V69.1 · Canonical eval set completion + frontmatter schema**
- [ ] **V69.2 · Eval regression harness**
- [ ] **V69.3 · Backend pre-existing failure triage**
- [ ] **V69.4 · E2E + StrictMode investigation + close**

## Fleet criteria (further tightened vs V68-C)

| # | Agent | V68-C criteria | V69 criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | (unchanged) |
| 2 | Physics | + whitelist count ≥11 | **+ canonical eval pass ≥20 cases** |
| 3 | UX/Playability | ≥9 specs PASS | **≥11 specs PASS** |
| 4 | Visualization | ≥16 PNG | **≥18 PNG** |
| 5 | Smoke | + 3 endpoint probes | **+ canonical eval harness pytest sub-probe** |
| 6 | Functional | 4/4 LANDED + 7/7 Done | (unchanged formula) |
| 7 | Stability | vitest flake | (unchanged) |

## Iteration tracker

| Iter | Date | min(7) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V69 baseline) | 2026-05-16 | TBD | TBD | TBD | charter LANDED · 0/4 sub-DECs · 0/7 Done · expected drops: physics (canonical 0<20) · viz (16<18 pro-rated) · smoke (eval probe pending) | `.planning/scores/V69_iter_0.md` |

## Reverse-stop log

- V132 `MUTATING_ROUTES` net diff > 0
- canonical eval harness exposes a real advisor_stack regression
- backend triage adds NEW failures
- StrictMode investigation balloons into 4-hour refactor
- pixel-diff 0.01 fails existing 16 baselines
- 14 pre-existing failures resist all triage

## Counter telemetry

- V69 charter: B151
- V69.1: B152 estimated
- Subsequent: B153-B158 estimated

— V69 ARC-GOAL · 2026-05-16
