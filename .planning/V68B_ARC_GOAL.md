# ARC-GOAL · V68-B Real Backend & Industrial Dogfood · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v68b_charter_dec.md` (Accepted B133 · 2026-05-16)
> **Predecessor**: DEC-V68-A-close (B132 · 79.30 weighted · Pillar 6 95)
> **Target**: Pillar 6 95→97 · weighted +0.2 ceiling · MSW→fastapi swap + industrial dogfood + pixel-diff 0.01 + WASM spike
> **User mandate**: 全权开发 · 7-agent fleet (further tightened) · 真实测评 · 使用手感 · 可视化追踪 · ≥99 分

## North Star (charter §3 verbatim)

> "工程师启动 `./scripts/start-ui-dev.sh` (起 fastapi + vite)，访问 `/workbench/case/case_002a` 看到 APU bay industrial case 真实加载 (geometry render · mesh stats · BC patches · 真实 audit verdict · CompletenessCard 真实数据)。pixel-diff CI gate 收紧到 0.01 阻挡视觉退化。Playwright e2e 跑通真实 backend 后的全流程。OpenFOAM-WASM spike 记录 emscripten 工具链 + WASM 编译 gap manifest 作为后续 arc 决策依据。"

## Done dim checklist (7 dims · all required for V68-B close · FULL delivery only)

- [x] **V68-B-DONE-1 · Backend dev bootstrap** — start-ui-dev.sh + 12-poll backend readiness wait · 5 pytest probes PASS (app + /api/cases LIST/GET/completeness/404) · MSW gate at main.tsx verified opt-in only · evidence: `test_v68b_readiness_probe.py` · B134
- [ ] **V68-B-DONE-2 · /api/cases real serving** — LIST + GET + status from corpus (not mock) · 10 whitelist + case_002a APU bay reachable
- [ ] **V68-B-DONE-3 · CompletenessCard real-data wiring** — /api/cases/:id/completeness real route · MeshQualityCard polyMesh · ProposalCard ai_advisor
- [ ] **V68-B-DONE-4 · Industrial case dogfood (case_002a APU bay)** — /workbench/case/case_002a renders · 5-step navigable · geometry serves · audit verdict displayed · MSW bypassed
- [ ] **V68-B-DONE-5 · pixel-diff CI gate (0.01)** — `maxDiffPixelRatio: 0.01` (was 0.1) · all baselines re-validated · ≥4 new case_002a baselines · ≥12 PNG total
- [ ] **V68-B-DONE-6 · E2E against real backend** — Playwright runs against real fastapi (MSW disabled) · case_002a flow PASS · no ECONNREFUSED
- [ ] **V68-B-DONE-7 · OpenFOAM-WASM spike + Pillar 6 ≥97 re-anchor** — spike-class probe `.planning/research/openfoam_wasm_feasibility.md` · emscripten check + gap manifest · Pillar 6 anchor 97 zone language updated · evidence: V68-B close DEC §10

## Sub-DEC progress

- [x] **V68-B.1 · Backend bootstrap + dev startup script** — start-ui-dev.sh readiness wait + 5 pytest probes PASS · MSW retire-default confirmed · B134
- [ ] **V68-B.2 · /api/cases real serving** — WorkbenchIndexPage + useCaseStatus verified against real fastapi
- [ ] **V68-B.3 · CompletenessCard real-data wiring** — real-route tested
- [ ] **V68-B.4 · Industrial case dogfood + pixel-diff CI gate** — case_002a e2e + threshold 0.1→0.01 + 4 new baselines
- [ ] **V68-B.5 · E2E against real backend + close** — webServer co-process · MSW off · close DEC + retro
- [ ] **V68-B.6-spike · OpenFOAM-WASM feasibility** (spike-class · ≤30 LOC + 1 manifest · NOT a sub-DEC)

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
