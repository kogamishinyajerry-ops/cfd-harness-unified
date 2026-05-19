# ARC-GOAL · V78 v3 Tooling-Debt Arc · NO NEW PILLAR · backend SSE + SSIM + audit-package E2E + UX 100% specs · **ACTIVE 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v78_charter_dec.md` (Accepted B222)
> **Predecessor**: DEC-V77-close (16-pillar 100/100 · B221)
> **Pillar count**: stays at 16 (V77 retro Open Q #6 honored)
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate **under TIGHTENED scoring**

## North Star

The arc closes with same nominal score (16-pillar 100/100) but substantially harder substrate underneath:
- Backend SSE endpoint live · solver-state-badge shows actual server events not offline fallback
- 76 visual baselines compared by SSIM ≥0.99 (structural similarity) not pixel-ratio (shallow pixel-count)
- Audit-package buildAuditPackage call verified end-to-end · downloaded zip parsed · manifest schema + signature_hex validated
- Playwright UX scorer requires 100% specs PASS not "≥17 of 122 PASS"

## Why this arc

V67-C → V77 added 9 pillars (7→16). **V77 retro #6 declared "V78 should NOT add Pillar 17 reflexively"**. The honest reading of "迭代开发下去 till 99+" demands that breadth-vs-depth tradeoff flip. V78 chooses depth.

## Done dim checklist

- [x] **V77-DONE-1..16 carry** — 16/16 pillars at 100 under TIGHTENED scoring (verified iter-1/iter-2)
- [x] **V78-DONE-COMPOSITE** — All 16 pillars at 100 UNDER TIGHTENED SCORING · NO new pillar added

## Sub-DEC progress

- [x] **V78.1 · Backend SSE endpoint impl** — FastAPI StreamingResponse · synthetic generator · 5/5 pytest
- [x] **V78.2 · SSIM visual baseline tool** — `scripts/visual/ssim_compare.py` · 11×11 windowed Wang 2004 · numpy+PIL · 5-retro carry CLOSED
- [x] **V78.3 · Audit-package E2E smoke** — 5/5 pytest · POST build → GET manifest → GET zip roundtrip · 4-arc carry CLOSED
- [x] **V78.4 · UX 100% specs threshold** — flow_completion now requires 100% specs PASS · 3-arc carry CLOSED
- [x] **V78.5 · 16-pillar scorer refresh (v78_fleet)** — 5 scorers · 0 new pillar · subscores rebalanced 25→20
- [x] **V78.6 · Close DEC + retro + a11y fix (SolverInflightTicker tabIndex + role=log) + 3 baseline re-snaps**

## Fleet criteria (16 pillars · V78 tightens existing)

| # | Agent | V77 close | V78 (tightened) |
|---|---|---|---|
| 1-2 | (carry) | 100 | unchanged |
| 3 | UX (使用手感) | 100 (≥17 of 122 specs) | **100% playwright specs PASS** |
| 4 | Visualization | 100 (76 PNG · maxDiffPixelRatio) | **76 PNG · SSIM ≥0.99** |
| 5-12 | (mostly carry) | 100 | unchanged |
| 13 | data_fidelity | 100 | + `audit_package_e2e` subscore |
| 14-15 | (carry) | 100 | unchanged |
| 16 | rt_solver_observability | 100 (offline graceful) | + `backend_sse_e2e` subscore (live) |
| ~~17~~ | ~~(declined)~~ | — | **EXPLICITLY NOT ADDED** |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V78 baseline) | 2026-05-17 | 70 | mid | stability | stability vitest flake (1/3) · ux 85 (V73.1-style 100% threshold not met · 4 specs failing: 1 a11y + 3 baselines drifted from V78.1 backend live) | V78_iter_0.md |
| 1 | 2026-05-17 | **100** | 121.04 | (all 100) | a11y fix · 3 baselines re-snapped · CLOSE_ELIGIBLE | V78_iter_1.md |
| 2 | 2026-05-17 | **100** | 121.04 | (all 100) | stability re-confirm · CLOSE_CONFIRMED (2-consec) | V78_iter_2.md |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0 (locked at 9)
- Adding Pillar 17 (charter-level reverse-stop)
- Backend SSE leaks goroutines/async tasks
- audit-package E2E smoke false-passes
- UX 100% specs hides regressions instead of surfacing
- Any of 76 baselines drifts > 0.01 pixel OR SSIM < 0.99

## Counter telemetry

- V78 charter: B222
- V78.1-V78.6 + close: B223-B229 estimated

— V78 ARC-GOAL · 2026-05-17
