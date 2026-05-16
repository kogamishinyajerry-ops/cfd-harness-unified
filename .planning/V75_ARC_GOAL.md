# ARC-GOAL · V75 v3 Resumability & Observability + error boundaries + URL state + loading skeletons · **ACTIVE 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v75_charter_dec.md` (Accepted B198)
> **Predecessor**: DEC-V74-close (13-pillar 100/100 · B197)
> **NEW Pillar 14**: 可恢复性与可观察性 (Resumability & Observability) · 4 subscores
> **Target**: 14-pillar min ≥99 · 2-consecutive close gate

## North Star

Engineer refreshes `/workbench/v3/case/foo?step=3&tab=advisor&btab=residuals&view=mesh` → identical state restored. TopBar always shows backend health. Async failures surface as calm error-boundary cards, not white-screen crashes. Skeletons hold layout shape during fetch.

## Done dim checklist

- [x] **V74-DONE-1..12 carry** — verify no regression on V74 close
- [x] **V75-DONE-13 · Composite** — Pillar 14 = **100** AND 4 error boundaries AND 4 skeletons AND URL state on 3 aspects (view/tab/btab) AND TopBar observability indicator live

## Sub-DEC progress

- [x] **V75.1 · Error boundaries** — 3 boundaries with data-testid="error-boundary-*"
- [x] **V75.2 · Loading skeletons** — 4 surfaces with Skeleton primitive
- [x] **V75.3 · URL state resumability** — ?tab=&btab=&view= deep-link safe
- [x] **V75.4 · Observability indicator** — TopBar shows TTFB + inflight count
- [x] **V75.5 · Pillar 14 scorer wired** — 4 subscores · all ≥25 floor
- [x] **V75.6 · 8 visual baselines (53-60) + close + retro**

## Fleet criteria (14 pillars · V75 NEW Pillar 14)

| # | Agent | V74 close | V75 |
|---|---|---|---|
| 1-9 | (carry) | 100 | unchanged |
| 4 | Visualization | 100 (52 PNG) | **≥60 PNG** |
| 10-11 | Industrial-UI / Interaction-Polish | 100 | unchanged |
| 12 | Backend-Integration | 100 | **useQuery_count ≥24** |
| 13 | Data-Fidelity-Auditability | 100 | unchanged |
| 14 | **Resumability-Observability** | **N/A** | **≥99** (NEW · 4 subscores) |

## Iteration tracker

| Iter | Date | min(14) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V75 baseline) | 2026-05-17 | 16 | 99.04 | resumability_observability (NEW pillar) | charter LANDED · pillar 14 NEW · 13 of 14 carry V74 100 | V75_iter_0.md |
| 1 | 2026-05-17 | **100** | 121.04 | (all 100) | V75.1+2+3+4 LANDED · CLOSE_ELIGIBLE | V75_iter_1.md |
| 2 | 2026-05-17 | **100** | 121.04 | (all 100) | stability re-confirm · CLOSE_CONFIRMED (2-consec) | V75_iter_2.md |
| 3 | 2026-05-17 | **100** | 121.04 | (all 100) | + 8 baselines (53-60) · 60/60 PASS · 3-consec margin | V75_iter_3.md |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button in any v3 surface
- Pillar 6 regression below 99
- Any of 52 V74 baselines drifts > 0.01 pixel ratio
- axe-core finds WCAG violations on any of Steps 1-5
- Error boundary swallows real bugs (must log + surface)
- URL state changes mutate case state (must be read-only)

## Counter telemetry

- V75 charter: B198
- V75.1-V75.6 + close: B199-B205 estimated

— V75 ARC-GOAL · 2026-05-17
