---
decision_id: DEC-V75-charter
title: V75 charter · v3 Resumability & Observability + error boundaries + URL state + loading skeletons · 14-pillar fleet
status: Accepted
parent_dec: DEC-V74-close
phase: V75
notion_sync_status: pending
batch: B198
confidence: high
autonomous_governance: true
---

# DEC-V75-charter · v3 Resumability & Observability · 14-pillar fleet

## 1 · North Star

Engineer is mid-investigation at `/workbench/v3/case/foo?step=3&tab=advisor&btab=residuals&view=mesh`. They refresh the page — the **exact same view** comes back without re-clicking anywhere. The TopBar always shows live backend health (active-query count + last-TTFB). When the advisor backend hiccups, a calm **error boundary** card surfaces inside the right panel instead of a white-screen crash. While `/api/cases` is in flight, a real **skeleton** holds the shape of the layout instead of a "loading…" text shimmy.

These four properties (error boundaries · loading skeletons · URL state resumability · observability indicator) are what every top-tier industrial CAE — CATIA, STAR-CCM+, Solidworks, Bloomberg Terminal — has baked in. V74 buried them; V75 makes them first-class.

## 2 · NEW Pillar 14 · 可恢复性与可观察性 (Resumability & Observability)

| Subscore | Weight | Floor for FULL |
|---|---|---|
| `error_boundary_coverage` | 25 | ≥3 React error boundaries with data-testid="error-boundary-*" |
| `loading_skeleton_coverage` | 25 | ≥4 surfaces using <Skeleton> primitive (not "loading…" text) |
| `url_state_resumability` | 25 | ≥3 UI state aspects (tab/btab/view) survive ?param refresh |
| `observability_indicator` | 25 | TTFB + active-query count visible in TopBar (data-testid="observability-*") |

Weight = **0.06** (same as Pillars 12 + 13).

## 3 · Pillar extensions (V75 increment)

| Pillar | V74 close | V75 |
|---|---|---|
| 12 backend_integration | useQuery_count ≥18 · endpoints ≥6 | useQuery_count ≥24 (no endpoint count change) |
| 4 visualization | 52 PNG baselines | ≥60 PNG baselines |

## 4 · Sub-DEC plan (6)

| Sub-DEC | Headline | Pillar fed |
|---|---|---|
| V75.1 | React error boundaries · 3 surfaces | 14 error_boundary_coverage |
| V75.2 | Loading skeletons · 4 surfaces | 14 loading_skeleton_coverage |
| V75.3 | URL state resumability · tab/btab/view | 14 url_state_resumability |
| V75.4 | Observability indicator · TTFB + inflight queries | 14 observability_indicator |
| V75.5 | Pillar 14 scorer wired | 14 (validates) |
| V75.6 | 8 visual baselines (53-60) + close + retro | 4 + close |

## 5 · Reverse-stops

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button (V130 invariant)
- Any pillar regression below 99
- Any of 52 V74 baselines drifts > 0.01 pixel ratio
- axe-core finds WCAG violations on any of Steps 1-5
- Error boundary catches a real bug but hides it (must log + surface)
- URL state changes mutate case (must be read-only)

## 6 · Counter telemetry

- V75-charter: B198
- V75.1-V75.6 + close: B199-B205 (estimated)

## 7 · Close gate

13-pillar carry + Pillar 14 ≥99 × 2 consecutive iters.

## 8 · Acknowledged V74 carry items (NOT in V75 scope)

- vtk.js MainCanvasV3 integration (V71.L · 5 arcs aged)
- SSE residuals integration (V71.L · 5 arcs aged)
- Backend `audit-package/build` E2E round-trip smoke
- Pixel-ratio vs SSIM tooling switch (3 retros mentioned · still unaddressed)
- Literal-testid scorer trap (4 arcs · still convention not lint)

These are honest carries to V76+, not silent omissions.
