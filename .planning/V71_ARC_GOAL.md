# ARC-GOAL · V71 v3 Blueprint Implementation · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v71_charter_dec.md` (Accepted B169 · 2026-05-16)
> **Predecessor**: DEC-V70-close (B166 · 10-pillar fleet · Pillar 6 99.5 · Pillar 7 90)
> **Visual SSOT**: `.planning/blueprints/v3/INDEX.md` + 8 PNG images (B168)
> **Target**: Pillar 6 99.5 → ≥99.7 · Pillar 10 90 → ≥95 · 10-pillar min ≥99 · 2-consecutive close gate

## North Star

工程师导航到 `/workbench/v3/case/lid_driven_cavity?step=1` → 完整 v3 四面板架构 (Activity Bar · Left Panel · Center · Right Panel + Bottom Panel · 5-Step Pipeline Strip + Viewport Mode Toolbar) · 切换 step / viewport mode / right-panel tab 全部 working · Advisor tab V132 invariant test 绿 · 8 PNG visual baselines (23-30) 锁定 against blueprint images.

## Done dim checklist (9 dims · all required)

- [x] **V71-DONE-1 · WorkbenchShellV3 4-panel grid** — Activity Bar 48px + Left Panel 260px + Center workspace (Pipeline Strip 44px + Viewport Mode Toolbar 36px + Main Canvas + Bottom Panel toggle) + Right Panel 340px · CSS Grid layout · all panels rendered · **LANDED B170** commit `9df67ab` · `data-v71-ui-shell="true"` tag present · 414 tests pass
- [x] **V71-DONE-2 · Step 1/2/3 surfaces** wired to shell — Step 1 geometry viewport + Inspector metadata · Step 2 mesh wireframe + Inspector quality table + bottom Console (on-demand) · Step 3 BC color-coded patches + MaterialCard inline two-column · **LANDED B171** · V71.G `QualityRow` + V71.H `BC_PALETTE` + V71.I `MaterialCard`
- [ ] **V71-DONE-3 · ResidualsChart + Bottom Panel** — log-scale multi-line chart + 4-tab bottom panel + streaming console
- [ ] **V71-DONE-4 · AdvisorTab + V132 contract test** — right-panel peer tab · paragraph + citations + preview-apply text links · ZERO auto-execute buttons regression-protected via e2e
- [ ] **V71-DONE-5 · ResultsCanvas + TrustGate verdict** — gold-vs-computed chart + HUGE PASS + point-by-point table
- [x] **V71-DONE-6 · Cross-step inspection** — viewport mode independent of pipeline step · Inspector adapts to both · **LANDED B170** · V71.S in `WorkbenchShellV3.tsx` (handleSetStep preserves engineer override) · V71.T in `InspectorContent.tsx` (Step4ActiveSolveInspector when stepId=4 + viewportMode='mesh')
- [ ] **V71-DONE-7 · 8 visual baselines (23-30)** locked against blueprint images
- [ ] **V71-DONE-8 · Pillar 6 99.5 → 99.7 + Pillar 10 90 → 95** with per-driver delta accounting
- [ ] **V71-DONE-9 · Fleet criteria tightened** — Pillar 6 `v3_route_mounts` sub-score · Pillar 10 `v3_blueprint_compliance` sub-score · all 10 pillars at ≥99

## Sub-DEC progress

- [x] **V71.1 · WorkbenchShell v3 4-panel grid** — Image 01 · V71.A/B/C/D · **LANDED B170** · DEC-V71-1
- [x] **V71.2 · Step views + Inspector contextual + MaterialCard** — Images 02/03/04 · V71.G/H/I/T · **LANDED B171** · DEC-V71-2
- [ ] **V71.3 · ResidualsChart + Bottom Panel + SolveRun streaming** — Image 05 · V71.E/F/J/L
- [ ] **V71.4 · AdvisorTab right-panel peer + V132 contract test** — Image 06 · V71.K/M/N/O
- [ ] **V71.5 · ResultsCanvas + TrustGate verdict surface** — Image 07 · V71.P/Q
- [ ] **V71.6 · 8 visual baselines + cross-step + close** — Image 08 · V71.S/U

## Fleet criteria (10 pillars · V71 tightened)

| # | Agent | V70 | V71 |
|---|---|---|---|
| 1 | Code Quality | binary 100 | unchanged |
| 2 | Physics | canonical eval ≥30 | unchanged |
| 3 | UX | ≥13 specs PASS | **≥17 specs PASS** |
| 4 | Visualization | ≥22 PNG | **≥30 PNG** |
| 5 | Smoke | unchanged | unchanged |
| 6 | Functional | 6 sub-DECs · 9 Done | 6 sub-DECs · 9 Done |
| 7 | Stability | unchanged | unchanged |
| 8 | CFD-Breadth | unchanged | unchanged |
| 9 | Novice-Onboarding | unchanged | unchanged |
| 10 | Industrial-UI | 3 improvements · benchmark doc | **+ v3_route_mounts ≥1 · ≥6 V71-UI tags · blueprint compliance** |

## Iteration tracker

| Iter | Date | min(10) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V71 baseline) | 2026-05-16 | 0 | 79.84 | functional (0) | charter LANDED · expected lows confirmed | `.planning/scores/V71_iter_0.md` |
| 1 (V71.1 LANDED) | 2026-05-16 | 17 | 91.04 | functional (17) | shell route mounts · 7/10 pillars at 100 · industrial_ui 48 → 84 (+36) · functional 0 → 17 (+17) · ux/cfd_breadth/novice flipped from intermediate to 100 · viz still 92 (need V71.6 baselines 23-30) | `.planning/scores/V71_iter_1.md` |
| 2 (V71.2 LANDED) | 2026-05-16 | 33 | 92.32 | functional (33) | V71.G/H/I polish · functional 17 → 33 (+16, 2 sub-DECs of 6 + 2 Done dims of 9) · industrial_ui unchanged 84 · viz unchanged 92 | `.planning/scores/V71_iter_2.md` |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button in Advisor surface
- Non-sand-coral accent color
- 5th persistent panel added
- Visual baseline > 0.05 SSIM drift from blueprint
- Pillar 6 regression below 99
- V71 breaks any existing 22 baselines

## Counter telemetry

- V71 charter: B169
- V71.1: B170 estimated
- Subsequent: B171-B176 estimated

— V71 ARC-GOAL · 2026-05-16
