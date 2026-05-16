# ARC-GOAL · V68-A Workbench Depth & Real-Usability · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v68a_charter_dec.md` (Accepted B126 · 2026-05-16)
> **Predecessor**: DEC-V67-C-close (B124 · 78.80 weighted · 8/8 Done dims MET, 4 SCAFFOLDING + 4 FULL)
> **Target**: Pillar 6 90→95 · weighted +0.5 ceiling · upgrade 4 SCAFFOLDING dims → FULL via real backend-driven flow
> **User mandate**: 全权开发 · 7-agent fleet (tightened criteria) · 真实测评 · 使用手感 · 可视化追踪 · ≥99 分

## North Star (charter §3 verbatim)

> "工程师打开 `/workbench/case/<demo>`，5-step pipeline 全程可达（MSW mock backend）· TopBar 4 字段实时更新（truthSource/trustGate/auditPct/llmOffline）· Viewport mode 6 状态切换（geometry/mesh/BC/field/residuals/report-grid）· Beginner/Power toggle 实际控制 5 step body 高级区显隐 · 8 个 canonical UI 状态有 pixel-diff baseline · 全流程 Playwright e2e PASS"

## Done dim checklist (7 dims · all required for V68-A close · FULL delivery only)

- [x] **V68-A-DONE-1 · MSW backend mocking** — 7 `http.get` handlers cover case + status + geometry/render + geometry/stl + mesh/render + bc/render + import/stl · gated by `VITE_MSW=1` · 3 vitest shape tests PASS · 342/342 full vitest PASS · evidence: `src/mocks/handlers.ts` · B127
- [ ] **V68-A-DONE-2 · TopBar real data wiring** — 4 dynamic fields (truthSource/trustGate/auditPct/llmOffline) feed from `useCaseStatus` React Query hook · evidence: `useCaseStatus.test.ts` + visual snapshot diff < 0.1%
- [ ] **V68-A-DONE-3 · Step body Power-mode adoption** — 5 step bodies (Import/Mesh/SetupBC/SolveRun/ResultsView) gate advanced section behind `isPower` · Beginner shows preset · Power reveals advanced · evidence: 5 step body tests + 1 e2e toggle test
- [ ] **V68-A-DONE-4 · Viewport mode dispatcher** — 6 modes (geometry/mesh-wireframe/BC-faces/field-slice/residuals/report-grid) · mode-state surfaces in viewport · ≤200ms switch · evidence: viewport dispatcher test + e2e test
- [ ] **V68-A-DONE-5 · Visual snapshot baseline** — 8 canonical UI states · `toHaveScreenshot()` baseline files committed · diff < 0.1% on stable runs · evidence: `__visual_baselines__/chromium/*-snapshots/` ≥8 PNG files
- [ ] **V68-A-DONE-6 · End-to-end 5-step flow** — Import→Mesh→BC→Solve→Results · all 5 steps reachable · CompletenessCard updates · TopBar `trustGate` progresses · evidence: `e2e/full-flow.spec.ts` ≥5 step navigations
- [ ] **V68-A-DONE-7 · Pillar 6 ≥95 re-anchor** — scoring framework v1.0 Pillar 6 anchor language matches `95-100` zone · evidence: V68-A close DEC §10

## Sub-DEC progress (5 sub-DECs · serial)

- [x] **V68-A.1 · MSW bootstrap** — msw@2.14.6 + 7 handlers + service worker + main.tsx opt-in + 3 vitest shape tests · B127 · commit pending
- [ ] **V68-A.2 · TopBar real data wiring** — useCaseStatus hook + StepPanelShell call-site update
- [ ] **V68-A.3 · Step body Power-mode disclosure** — 5 step bodies gate advanced section
- [ ] **V68-A.4 · Viewport mode dispatcher + visual baseline** — 6-mode dispatcher + 8 PNG snapshots
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
