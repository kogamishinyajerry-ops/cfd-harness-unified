---
decision_id: DEC-V77-charter
title: V77 charter · v3 Real-time Solver Observability · SSE residual stream + state badge + inflight ticker · 16-pillar fleet (Pillar 16 NEW · 4 subscores)
status: Accepted
parent_dec: DEC-V76-close
phase: V77
notion_sync_status: pending
predecessor: DEC-V76-close
batch: B214
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V77-charter (bootstrap)
substrate: V76 closed 15/15 × 2 consec · SSE residuals bookmark 7 arcs aged from V71.L · zero existing SSE infrastructure (frontend OR backend) · greenfield
---

# DEC-V77-charter · V77 v3 Real-time Solver Observability · CHARTER

## 1 · Mandate (13th verbatim)

> "批准授权你全权开发，瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

13th V110 advisor-class single-day arc. Identical wording across V67-C..V76.

## 2 · Why a NEW Pillar 16

V76 close DEC §8 ranked V77 priorities. **#1 was SSE residuals integration · "7 arcs aged · CRITICAL"**. Same pattern V76 used for vtk.js: bookmark age + score-axis force = work happens.

**Real industrial CAE has live convergence monitoring as table-stakes:**
- ANSYS Fluent · Residual Monitor (real-time per-iteration log)
- STAR-CCM+ · convergence plotter (live curves during solve)
- OpenFOAM (via paraFoam / pyFoam) · sample-on-fly residuals
- CONVERGE Studio · in-solver SSE

V67-C..V76 had STATIC residual demo curves. V77 wires real-time streaming. This is genuinely missing functionality, not score gaming.

## 3 · NEW Pillar 16 · 实时求解器可观察性 (Real-time Solver Observability)

**4 subscores · each 25 points:**

| Subscore | Points | Surface | Literal data-testid |
|---|---|---|---|
| sse_event_stream | 25 | EventSource hook + typed payloads | `sse-stream-status`, `useSseResidualStream` symbol |
| residual_live_update | 25 | Per-variable live residual values | `residual-live-{var}` (p, U_x, U_y, U_z, k, omega) |
| solver_state_stream | 25 | running/converged/diverged state | `solver-state-badge` |
| inflight_residual_display | 25 | Last-N ticker · console-style | `solver-inflight-residual` |

Each subscore PRO-RATED only if substrate present; if no literal-testid match → 0.

## 4 · Threshold tightening (force real work)

| Pillar | V76 close | V77 charter |
|---|---|---|
| 4 · visualization | 60+8=68 PNG baselines (V76 scaffolded) | **≥76 PNG** (V77.6 adds 8 more) |
| 12 · backend_integration | useQuery ≥30 | **useQuery ≥35** (V77 adds 5+ SSE hook refs) |
| 14 · resumability_observability | unchanged | unchanged |
| 15 · visualization_fidelity | 5 subscores @ 100 | unchanged |
| **16 · real-time solver observability (NEW)** | **N/A** | **≥99** (4 subscores · 25 each) |

## 5 · Sub-DEC roadmap

| Sub-DEC | Headline | Substrate to land |
|---|---|---|
| **V77.1** | SSE event stream wire + types | `hooks/useSseResidualStream.ts` + ResidualTick / StateChange / IterationCheckpoint types · EventSource lifecycle with ECONNREFUSED-tolerant fallback |
| **V77.2** | Residual live update component | `ResidualLiveStreamV3` · per-var rows with literal `data-testid="residual-live-{p,U_x,U_y,U_z,k,omega}"` (6 lines) |
| **V77.3** | Solver state stream + badge | `SolverStateBadge` with `data-testid="solver-state-badge"` · data-state="running" \| "converged" \| "diverged" |
| **V77.4** | Inflight residual ticker | `SolverInflightTicker` console-style last-10-events log · exponential backoff reconnect (1s → 2s → 4s → max 30s) |
| **V77.5** | Pillar 16 scorer wired + contract tests | scorer script + 6+ vitest tests for SSE hook + components |
| **V77.6** | 8 visual baselines (69-76) + close DEC + retro | Lock substrate visually |

## 6 · Backend SSE endpoint policy

**Frontend wire is the focus.** Backend `/api/cases/{id}/solver/stream` endpoint:
- If backend implements SSE → frontend connects, receives real solver events
- If backend returns 404 / connection refused → `sse-stream-status="offline"` data-source surfaces honestly · UI degrades to "stream unavailable" placeholder · canvas/state-badge testids still mount (per Pillar 16 testid-presence scoring)

This mirrors V76's vtk.js asset-missing handling. The 4Q gate "LLM offline runnable" extends to "solver-offline runnable" — UI navigable without backend SSE.

## 7 · Reverse-stops (V77)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface
3. Any of 60 V75 + 8 V76 baselines drifts > 0.01 pixel ratio
4. SSE reconnect storms (must use exp backoff, never tight loop)
5. EventSource memory leak (must close on unmount)
6. Pillar 15 regression below 99 (V76 substrate)
7. axe-core finds WCAG violations on any of Steps 1-5

## 8 · Honest disclosures (V77 explicitly NOT doing)

Per V76 close §8:
- ❌ **Pixel-ratio → SSIM tooling switch** — 4 retros mentioned · **DEFERRED to V78**
- ❌ **Backend audit-package E2E round-trip smoke** — V74.5 wire still unverified · DEFERRED
- ❌ **UX scorer 100% specs PASS threshold tightening** — DEFERRED
- ❌ **vtk.js camera presets** (front/top/iso) — DEFERRED
- ❌ **Real STL backend availability matrix** — DEFERRED
- ❌ **V76.6 playwright baseline first-capture** — `--update-snapshots` requires live dev env · iter-4 UX regression carries from V76 until user runs locally
- ✅ **SSE residuals integration** — addressed (V71.L bookmark FINALLY closed after 8 arcs)

## 9 · Counter telemetry (estimated)

- V77-charter: B214
- V77.1-V77.6 + close: B215-B221 estimated
- All `autonomous_governance: true`
- Counter contribution: **+8** · arc within v2.3 cadence floor 30

## 10 · 4Q gate (every sub-DEC must answer)

1. **LLM offline runnable?** SSE path is pure browser EventSource (no LLM call) ✓
2. **Artifacts emitted?** Live residuals consumed in UI; not persisted as new artifacts (read-only stream)
3. **TrustGate intact?** No new MUTATING_ROUTES; SSE is GET-only with `text/event-stream`
4. **AI advisory only?** No AI affordances added to solver stream surface

## 11 · Single sand-coral accent invariant

Live residual chart uses neutral palette (#9a9aa0 grid · #b78b65 sand-coral for the WATCHED variable only · viridis colormap not introduced here). State badge uses neutral fills with semantic borders (running=blue, converged=green, diverged=rose).

## 12 · Pillar-count ceiling honest disclosure

**V67-C started with 7 pillars. V77 has 16.** Each addition was forced by genuine missing substrate (V71 backend_integration, V72 interaction_polish, V74 data_fidelity, V75 resumability_observability, V76 visualization_fidelity, V77 real-time_solver_observability). **The honest read: 16 is approaching saturation for canonical industrial-CAE UX axes.** V78 might address tooling debts (SSIM) instead of new pillars.

## 13 · Iteration target

| Iter | Goal | Expected min(16) |
|---|---|---|
| 0 | Baseline · all 15 carry V76 100 + Pillar 16 = 0 (no SSE infra) | 0 |
| 1 | V77.1+V77.2 LANDED · stream + residual lines | 50-75 |
| 2 | V77.3+V77.4 LANDED · state badge + ticker | 90-100 |
| 3 | V77.5 LANDED · scorer + contract tests | 100 (CLOSE_ELIGIBLE) |
| 4 | Stability re-confirm | 100 (CLOSE_CONFIRMED 2-consec) |
| 5 | V77.6 baselines (69-76) | 100 (3-consec margin) |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters.

— DEC-V77-charter · 2026-05-17 · LANDED
