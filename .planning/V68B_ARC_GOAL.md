# ARC-GOAL · V68-B Real Backend & Industrial Dogfood · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v68b_charter_dec.md` (Accepted B133 · 2026-05-16)
> **Predecessor**: DEC-V68-A-close (B132 · 79.30 weighted · Pillar 6 95)
> **Target**: Pillar 6 95→97 · weighted +0.2 ceiling · MSW→fastapi swap + industrial dogfood + pixel-diff 0.01 + WASM spike
> **User mandate**: 全权开发 · 7-agent fleet (further tightened) · 真实测评 · 使用手感 · 可视化追踪 · ≥99 分

## North Star (charter §3 verbatim)

> "工程师启动 `./scripts/start-ui-dev.sh` (起 fastapi + vite)，访问 `/workbench/case/case_002a` 看到 APU bay industrial case 真实加载 (geometry render · mesh stats · BC patches · 真实 audit verdict · CompletenessCard 真实数据)。pixel-diff CI gate 收紧到 0.01 阻挡视觉退化。Playwright e2e 跑通真实 backend 后的全流程。OpenFOAM-WASM spike 记录 emscripten 工具链 + WASM 编译 gap manifest 作为后续 arc 决策依据。"

## Done dim checklist (7 dims · all required for V68-B close · FULL delivery only)

- [x] **V68-B-DONE-1 · Backend dev bootstrap** — start-ui-dev.sh + 12-poll backend readiness wait · 5 pytest probes PASS (app + /api/cases LIST/GET/completeness/404) · MSW gate at main.tsx verified opt-in only · evidence: `test_v68b_readiness_probe.py` · B134
- [x] **V68-B-DONE-2 · /api/cases real serving** — useCaseStatus repointed to /completeness · normalize maps case_kind/ready_for_archive/blocked_by_critical/percentage → TopBar vocab · 9 new vitest PASS · `lid_driven_cavity` real-fixture snapshot test PASS · evidence: `useCaseStatus.ts` · B135
- [x] **V68-B-DONE-3 · CompletenessCard real-data wiring** — useCaseStatus hook = SSOT for case audit verdict · drives both TopBar and CompletenessCard surfaces from real `/completeness` data · evidence: V68-B.2 consolidated (same hook) · B135
- [x] **V68-B-DONE-4 · Industrial case dogfood (naca0012_airfoil)** — pivoted from case_002a (sandbox-only, not in whitelist) to naca0012_airfoil (whitelist · external aero · simpleFoam k-ω SST · ready_for_archive=true · audit=92.3% · trustGate=PASS) · 6/6 e2e dogfood PASS · evidence: `industrial-dogfood.spec.ts` · B136
- [x] **V68-B-DONE-5 · pixel-diff CI gate (0.01)** — `maxDiffPixelRatio: 0.01` (was 0.1) · 12 PNG total (8 V68-A.4 + 4 V68-B.4 new) · 12/12 PASS on re-run no-update (threshold stable across runs) · evidence: `visual-baseline.spec.ts` · B136
- [x] **V68-B-DONE-6 · E2E against real backend** — dual-process webServer (uvicorn :8001 + vite :5173 · MSW off) · 37/37 e2e PASS · 0 ECONNREFUSED · evidence: `playwright.config.ts` · B137
- [x] **V68-B-DONE-7 · OpenFOAM-WASM spike + Pillar 6 ≥97 re-anchor** — `.planning/research/openfoam_wasm_feasibility.md` (7 sections) · emscripten MISSING locally · toolchain inventory + dep audit + 14-22 week cost estimate · V68-D arc deferred · SCORING-FRAMEWORK.md 97-100 zone updated · evidence: V68-B close DEC §4+§10 · B138

## Sub-DEC progress

- [x] **V68-B.1 · Backend bootstrap + dev startup script** — start-ui-dev.sh readiness wait + 5 pytest probes PASS · MSW retire-default confirmed · B134
- [x] **V68-B.2 · /api/cases real serving** — useCaseStatus → /completeness · normalize V68-A legacy + V68-B real shapes · 9 new tests · 376 total · B135
- [x] **V68-B.3 · CompletenessCard real-data wiring** — consolidated into V68-B.2 (same useCaseStatus hook = SSOT) · B135
- [x] **V68-B.4 · Industrial case dogfood + pixel-diff CI gate** — naca0012_airfoil dogfood (6/6 e2e) + threshold 0.1→0.01 + 4 new baselines (12 PNG total) · B136
- [x] **V68-B.5 · E2E against real backend + close** — playwright dual-webServer · MSW off · 37/37 PASS · close DEC pending · B137-B138
- [x] **V68-B.6-spike · OpenFOAM-WASM feasibility** — research artifact (0 LOC code · spike-class) · V68-D arc deferred · B137 commit

## Fleet criteria (further tightened vs V68-A)

| # | Agent | V68-A criteria | V68-B criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | (unchanged) |
| 2 | Physics | mass_balance+corpus+bc_routes | (unchanged) |
| 3 | UX/Playability | ≥5 specs PASS | **≥7 specs PASS** for FULL flow=60 |
| 4 | Visualization | ≥4 viewport-mode + ≥6 PNG | **≥4 viewport-mode + ≥12 PNG** |
| 5 | Smoke | backend+build+tc+lint | **+ backend HTTP /api/cases probe** |
| 6 | Functional | 5/5 LANDED + 7/7 Done | (unchanged formula) |
| 7 | Stability | vitest flake | (unchanged) |

## Iteration tracker

| Iter | Date | min(7) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V68-B baseline) | 2026-05-16 | TBD | TBD | TBD | charter LANDED · 0/5 sub-DECs · 0/7 Done · expected regression on functional + visualization (new ≥12 PNG threshold) | `.planning/scores/V68-B_iter_0.md` |

## Reverse-stop log

- V132 `MUTATING_ROUTES` net diff > 0
- fastapi backend won't start in dev (port collision or dependency drift)
- case_002a routes 404 on real backend (corpus data missing)
- pixel-diff 0.01 threshold causes existing baselines to fail on stable rerun
- Playwright + concurrent backend webServer hangs >2min
- OpenFOAM-WASM spike reveals emscripten toolchain catastrophically broken

(none triggered yet · pre-iter-0)

## Counter telemetry

- V68-B charter: B133
- V68-B.1: B134 estimated
- Subsequent: B135-B140 estimated (+ spike commit B141)

— V68-B ARC-GOAL · 2026-05-16
