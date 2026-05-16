# ARC-GOAL · V68-A Workbench Depth & Real-Usability · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v68a_charter_dec.md` (Accepted B126 · 2026-05-16)
> **Predecessor**: DEC-V67-C-close (B124 · 78.80 weighted · 8/8 Done dims MET, 4 SCAFFOLDING + 4 FULL)
> **Target**: Pillar 6 90→95 · weighted +0.5 ceiling · upgrade 4 SCAFFOLDING dims → FULL via real backend-driven flow
> **User mandate**: 全权开发 · 7-agent fleet (tightened criteria) · 真实测评 · 使用手感 · 可视化追踪 · ≥99 分

## North Star (charter §3 verbatim)

> "工程师打开 `/workbench/case/<demo>`，5-step pipeline 全程可达（MSW mock backend）· TopBar 4 字段实时更新（truthSource/trustGate/auditPct/llmOffline）· Viewport mode 6 状态切换（geometry/mesh/BC/field/residuals/report-grid）· Beginner/Power toggle 实际控制 5 step body 高级区显隐 · 8 个 canonical UI 状态有 pixel-diff baseline · 全流程 Playwright e2e PASS"

## Done dim checklist (7 dims · all required for V68-A close · FULL delivery only)

- [x] **V68-A-DONE-1 · MSW backend mocking** — 7 `http.get` handlers cover case + status + geometry/render + geometry/stl + mesh/render + bc/render + import/stl · gated by `VITE_MSW=1` · 3 vitest shape tests PASS · 342/342 full vitest PASS · evidence: `src/mocks/handlers.ts` · B127
- [x] **V68-A-DONE-2 · TopBar real data wiring** — 4 dynamic fields feed from `useCaseStatus` React Query hook against `/api/cases/:id/status` · normalised + clamped · V130 default-true invariant preserved · 9 vitest PASS · 351/351 full suite · evidence: `useCaseStatus.ts` · B128
- [x] **V68-A-DONE-3 · Step body Power-mode adoption** — PowerDisclosure wrapper (~65 LOC) + 5 step bodies (Step1Import/2Mesh/3SetupBC/4SolveRun/5ResultsView) each gate one engineer-tier advanced section behind `isPower` · graceful no-Provider fallback · 4 vitest PASS · 355/355 full suite · evidence: `PowerDisclosure.tsx` · B129
- [x] **V68-A-DONE-4 · Viewport mode dispatcher** — ViewportModeDispatcher (~95 LOC) · 6 modes via data-viewport-mode attr · step default mapping (1→geometry, 2→mesh, 3→bc, 4→residuals, 5→report) · 12 vitest PASS · 7/7 e2e PASS · evidence: `ViewportMode.tsx` · B130
- [x] **V68-A-DONE-5 · Visual snapshot baseline** — 8 PNG files committed at `__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots/` · 8/8 e2e PASS first-run (lenient `maxDiffPixelRatio: 0.1`) · evidence: `visual-baseline.spec.ts` · B130
- [ ] **V68-A-DONE-6 · End-to-end 5-step flow** — Import→Mesh→BC→Solve→Results · all 5 steps reachable · CompletenessCard updates · TopBar `trustGate` progresses · evidence: `e2e/full-flow.spec.ts` ≥5 step navigations
- [ ] **V68-A-DONE-7 · Pillar 6 ≥95 re-anchor** — scoring framework v1.0 Pillar 6 anchor language matches `95-100` zone · evidence: V68-A close DEC §10

## Sub-DEC progress (5 sub-DECs · serial)

- [x] **V68-A.1 · MSW bootstrap** — msw@2.14.6 + 7 handlers + service worker + main.tsx opt-in + 3 vitest shape tests · B127 · commit pending
- [x] **V68-A.2 · TopBar real data wiring** — useCaseStatus hook (~105 LOC) + StepPanelShell call-site updated · 9 vitest PASS · B128
- [x] **V68-A.3 · Step body Power-mode disclosure** — PowerDisclosure wrapper + 5 step bodies adopted · 4 vitest PASS · B129
- [x] **V68-A.4 · Viewport mode dispatcher + visual baseline** — ViewportModeDispatcher + ViewportModeDevPage harness + 7+8 e2e specs + 8 PNG baselines · B130
- [ ] **V68-A.5 · End-to-end 5-step flow + close** — full Playwright e2e Import→Mesh→BC→Solve→Results

## Fleet criteria (tightened vs V67-C)

| # | Agent | V67-C criteria | V68-A criteria |
|---|---|---|---|
| 1 | Code Quality | typecheck+lint+vitest | (unchanged) |
| 2 | Physics | mass_balance+corpus+bc_routes | (unchanged) |
| 3 | UX/Playability | spec pass ratio pro-rated | **≥5 specs PASS** for FULL flow=60 |
| 4 | Visualization | viewport+truth specs · baseline dir exists | **≥4 viewport-mode specs PASS** + **≥6 PNG snapshot files** |
| 5 | Smoke | backend+build+tc+lint | (unchanged) |
| 6 | Functional | LANDED + Done dim count | thresholds: 5/5 LANDED + 7/7 Done |
| 7 | Stability | vitest flake | (unchanged) |

## Iteration tracker

| Iter | Date | min(7) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V68-A baseline) | 2026-05-16 | TBD | TBD | functional | V68-A charter LANDED · 0/5 sub-DECs · 0/7 Done dims · expected functional drop | `.planning/scores/V68-A_iter_0.md` |

## Predicted trajectory (per charter §11)

- iter 0: min(7) low (functional → 0 because V68-A criteria tighten · 0/5 LANDED, 0/7 Done)
- iter 1 (V68-A.1 MSW): functional partial · MSW handlers + e2e against mocked backend unlock real flow
- iter 2-5: sub-DECs land incrementally · Done dims progress
- iter 6+: min(7) ≥99 for 2 consecutive · CLOSE_ELIGIBLE

V68-A may temporarily REGRESS overall score vs V67-C close 100/100 because criteria tighten. This is **honest** — V67-C's 100/100 was against V67-C charter criteria, not V68-A's.

## Reverse-stop log (must surface to user if any below trigger)

- V132 `MUTATING_ROUTES` net diff > 0
- MSW handler breaks SPA rendering
- Beginner mode breaks step body rendering
- Pixel-diff baseline diff > 0.1% on stable run (3 consecutive)
- Plateau over 5 iter with max-min < 5
- Codex round cap=3 on any 1-sync-trigger PR

(none triggered yet · pre-iter-0)

## Counter telemetry

- V68-A charter: B126
- V68-A.1 bootstrap: B127 estimated
- Subsequent batches: B128-B135 estimated

— V68-A ARC-GOAL · 2026-05-16
