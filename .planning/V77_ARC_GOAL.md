# ARC-GOAL · V77 v3 Real-time Solver Observability · SSE residual stream + state badge + inflight ticker · **ACTIVE 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v77_charter_dec.md` (Accepted B214)
> **Predecessor**: DEC-V76-close (15-pillar 100/100 · B213)
> **NEW Pillar 16**: 实时求解器可观察性 (Real-time Solver Observability) · 4 subscores
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate

## North Star

Engineer at `/workbench/v3/case/foo?step=4&view=residuals` sees live residual values streaming via SSE: `p: 3.2e-4 · U_x: 1.1e-5 · U_y: 8.7e-6 · ω: 2.3e-3` updating per iteration. State badge flips running→converged when threshold met. Last-10-iteration ticker shows console-style stream. If backend SSE offline, UI shows honest "stream unavailable" without crashing.

## Why this arc

SSE residuals has been bookmarked since V71.L (~8 arcs ago). V76 retro Open Question #1: "now 7 arcs aged. CRITICAL to track or formally rescope". V77 closes it. Same work-forcing pattern V76 used for vtk.js — score-axis pressure converts dormant bookmarks into landed substrate.

## Done dim checklist

- [x] **V76-DONE-1..15 carry** — 15/15 carry V76 100/100 (verified iter-4/5)
- [x] **V77-DONE-16 · Composite** — Pillar 16 = **100** · all 4 subscores at FULL

## Sub-DEC progress

- [x] **V77.1 · SSE event stream wire + types** — useSseResidualStream hook · 6/6 unit tests
- [x] **V77.2 · Residual live update component** — ResidualLiveStreamV3 · 6 per-var literal testids
- [x] **V77.3 · Solver state stream + badge** — SolverStateBadge · running/converged/diverged/idle
- [x] **V77.4 · Inflight residual ticker** — SolverInflightTicker · console-style last-10 log
- [x] **V77.5 · Pillar 16 scorer wired + 7 contract tests**
- [x] **V77.6 · 8 visual baselines (69-76) captured + V76 carry resolved (11 PNGs) + SwiftShader fix + close DEC + retro**

## Fleet criteria (16 pillars · V77 NEW Pillar 16)

| # | Agent | V76 close | V77 |
|---|---|---|---|
| 1-9 | (carry) | 100 | unchanged |
| 4 | Visualization | 100 (68 PNG scaffolded) | **≥76 PNG** scaffolded |
| 10-11 | Industrial-UI / Interaction-Polish | 100 | unchanged |
| 12 | Backend-Integration | 100 (useQuery≥30) | **useQuery_count ≥35** |
| 13 | Data-Fidelity-Auditability | 100 | unchanged |
| 14 | Resumability-Observability | 100 | unchanged |
| 15 | 3D-Visualization-Fidelity | 100 | unchanged |
| 16 | **Real-time-Solver-Observability** | **N/A** | **≥99** (NEW · 4 subscores) |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V77 baseline) | 2026-05-17 | 12 | 110 | rt_solver_obs | charter LANDED · only hook landed (12/100 partial) · UX 87 V76 carry · stability 70 flake | V77_iter_0.md |
| 1 | 2026-05-17 | 54 | mid | smoke | All 3 components LANDED · pillar 16 → 100 · iter-1 lint err + tsc err from unused vi import broke 3 pillars | V77_iter_1.md |
| 2 | 2026-05-17 | 50 | mid | quality | tsc err persisted on test file · regression from un-fixed import | V77_iter_2.md |
| 3 | 2026-05-17 | 87 | mid | ux | lint + tsc clean · only UX 87 stuck (V76.6 baseline-pending carry) | V77_iter_3.md |
| 4 | 2026-05-17 | **100** | 121.04 | (all 100) | playwright --update-snapshots: all 76 PNGs captured · UX recovered · CLOSE_ELIGIBLE | V77_iter_4.md |
| 5 | 2026-05-17 | **100** | 121.04 | (all 100) | stability re-confirm · CLOSE_CONFIRMED (2-consec) | V77_iter_5.md |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0 (locked at 9)
- Any auto-execute button in any v3 surface
- Any of 68 baselines drifts > 0.01 pixel ratio
- SSE reconnect storms (must use exp backoff, never tight loop)
- EventSource memory leak (must close on unmount)
- Pillar 15 regression below 99 (V76 substrate)
- axe-core finds WCAG violations on any of Steps 1-5

## Counter telemetry

- V77 charter: B214
- V77.1-V77.6 + close: B215-B221 estimated

— V77 ARC-GOAL · 2026-05-17
