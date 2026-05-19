# ARC-GOAL · V72 v3 Real-Data Wiring + Interaction Polish · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v72_charter_dec.md` (Accepted B177)
> **Predecessor**: DEC-V71-close (10-pillar 100/100 · B176)
> **NEW Pillar 11**: 交互体验 (Interaction Polish) per user 8th-invocation mandate
> **Target**: 11-pillar min ≥99 · 2-consecutive close gate

## North Star

Engineer navigates `/workbench/v3/case/lid_driven_cavity?step=1` and **everything is real**:
- Case list pulled from `/api/cases` (not hardcoded)
- Step 1 metadata pulled from `/api/cases/:id` (not stubbed)
- TruthChain verdict from `/api/cases/:id/completeness` (still real, verified)
- Full keyboard navigation works
- Motion transitions feel like Claude.ai (refined, not flashy)
- A playwright sub-agent runs Steps 1→5 + advisor consult end-to-end and reports PASS

## Done dim checklist (10 dims · all required)

- [x] **V72-DONE-1 · CaseBrowserV3 real-data wire** — `/api/cases` GET · skeleton state during fetch · error state if backend down
- [x] **V72-DONE-2 · Step1Inspector real metadata** — `/api/cases/:id` GET · falls back to mock when offline
- [x] **V72-DONE-3 · TruthChain real verdict** — `/api/cases/:id/completeness` (verify post-V71 hoist still working)
- [x] **V72-DONE-4 · Keyboard navigation spec PASS** — ≥4 tests · Tab cycle · ⌘K palette · Esc · ?-help
- [x] **V72-DONE-5 · Motion polish** — ≥12 transition-* usages in v3 · `prefers-reduced-motion` respected
- [x] **V72-DONE-6 · Focus management** — ≥20 ARIA/role/tabIndex usages · autoFocus on tab change
- [x] **V72-DONE-7 · Sub-agent journey test** — `user-journey-v3.spec.ts` PASSES Steps 1→5 + advisor
- [x] **V72-DONE-8 · 6 new visual baselines (31-36)** — keyboard-focus · motion-mid · advisor-expanded · etc.
- [x] **V72-DONE-9 · Pillar 11 (interaction_polish) ≥99**
- [x] **V72-DONE-10 · 11-pillar 2-consecutive close gate**

## Sub-DEC progress

- [x] **V72.1 · CaseBrowser + Step1Inspector real-data wire** — `useQuery` integration
- [x] **V72.2 · Keyboard navigation** — `useKeyboardShortcuts` hook + Tab/Esc/⌘K handlers
- [x] **V72.3 · Motion polish + reduced-motion** — Tailwind transitions + global CSS media query
- [x] **V72.4 · Focus management + ARIA** — autoFocus + comprehensive ARIA labels
- [x] **V72.5 · Sub-agent test harness** — `user-journey-v3.spec.ts` + .planning/methodology/autonomous-test-agent.md
- [x] **V72.6 · 6 visual baselines + close + retro** · LANDED B181 · DEC-V72-6

## Fleet criteria (11 pillars · V72 NEW Pillar 11)

| # | Agent | V71 close | V72 |
|---|---|---|---|
| 1 | Code Quality | 100 | unchanged |
| 2 | Physics | 100 | unchanged |
| 3 | UX | 100 | unchanged (still ≥17 specs) |
| 4 | Visualization | 100 (30 PNG) | **≥36 PNG** |
| 5 | Smoke | 100 | unchanged |
| 6 | Functional | 100 (6 sub + 9 Done) | **6 sub-DECs + 10 Done dims** |
| 7 | Stability | 100 | unchanged |
| 8 | CFD-Breadth | 100 | unchanged |
| 9 | Novice-Onboarding | 100 | unchanged |
| 10 | Industrial-UI | 100 | **+ real_data_wired + journey_test subscores** |
| 11 | **Interaction-Polish** | **N/A** | **≥99** (NEW · 4 subscores: keyboard / motion / focus / reduced-motion) |

## Iteration tracker

| Iter | Date | min(11) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V72 baseline) | 2026-05-16 | 27 | 101.89 | interaction_polish (27) | charter LANDED · NEW pillar 11 starts low (no kbd nav spec yet) · 10 of 11 pillars carry V71 close at 100 | `.planning/scores/V72_iter_0.md` |
| 1 (V72.1-6 LANDED) | 2026-05-16 | **100** | **107.00** | quality (100) | All 6 sub-DECs LANDED · all 10 Done dims MET · pillar 11 (interaction_polish) 27 → 100 | `.planning/scores/V72_iter_1.md` |
| 2 (CLOSE-CONFIRM) | 2026-05-16 | **100** | **107.00** | quality (100) | 2-consecutive close gate MET · V72 arc closes | `.planning/scores/V72_iter_2.md` |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button in any v3 surface (carries forward V71 rule)
- Pillar 6 regression below 99
- Any of 30 V71 baselines drift > 0.05 SSIM
- 5th persistent panel added
- Sub-agent journey claims false PASS (screenshots stale state)

## Counter telemetry

- V72 charter: B177
- V72.1: B178 estimated
- Subsequent: B179-B183 estimated

— V72 ARC-GOAL · 2026-05-16
