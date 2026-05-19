---
decision_id: DEC-V76-charter
title: V76 charter · v3 3D Visualization Fidelity · vtk.js mount + camera + legend + FPS + WebGL fallback · 15-pillar fleet (Pillar 15 NEW · 5 subscores)
status: Accepted
parent_dec: DEC-V75-close
phase: V76
notion_sync_status: pending
predecessor: DEC-V75-close
batch: B206
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V76-charter (bootstrap)
substrate: V75 closed 14/14 × 3 consec · vtk.js bookmark 6 arcs aged · viewport_kernel infrastructure already exists, just unwired in MainCanvasV3
---

# DEC-V76-charter · V76 v3 3D Visualization Fidelity · CHARTER

## 1 · Mandate (12th verbatim)

> "批准授权你全权开发，瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

12th V110 advisor-class single-day arc. Identical wording to V67-C..V75.

## 2 · Why a NEW Pillar 15

V67-C → V75 has piled 14 pillars. V75 close DEC §8 explicitly bookmarked **vtk.js MainCanvasV3 integration** as "6 arcs aged · time-bombed". Same Pillar-N pattern V67-C used to force novice_onboarding work — make the lacuna a first-class score axis.

V75 retro Open Question #6: "What's the ceiling on Pillar count?" — V76 answer: **add Pillar 15 BECAUSE it forces real 3D viz work**; if the pillar didn't exist, "MainCanvasV3 has placeholders" would never block any score and the bookmark would continue rotting. The pillar's existence IS the work-forcing function.

## 3 · NEW Pillar 15 · 三维可视化保真度 (3D Visualization Fidelity)

**5 subscores · each weighted to total 100:**

| Subscore | Points | Surface | Literal data-testid |
|---|---|---|---|
| vtk_canvas_mounts | 30 | MainCanvasV3 geometry/mesh modes mount vtk.js Viewport (not placeholder) | `vtk-canvas-mounted` |
| camera_controls | 20 | Reset camera + axes widget visible | `vtk-camera-reset`, `vtk-axes-widget` |
| field_legend | 20 | Color legend on residuals/field surfaces | `vtk-color-legend` |
| performance_signal | 15 | FPS / frame-time indicator | `vtk-fps-indicator` |
| load_fallback | 15 | WebGL-unavailable graceful fallback | `vtk-webgl-fallback` |

**Honest 0-floor**: each subscore PRO-RATED only if substrate present; if no literal-testid match → 0 (no partial credit).

## 4 · Threshold tightening (force real work · not score-game)

| Pillar | V75 close | V76 charter |
|---|---|---|
| 4 · visualization | 60 PNG baselines | **≥68 PNG** (V76.6 adds 8) |
| 12 · backend_integration | useQuery ≥24 | **≥30** (V76.1+V76.2 add viz queries) |
| 14 · resumability_observability | 4 subscores @ 25 | unchanged |
| **15 · 3D viz fidelity (NEW)** | **N/A** | **≥99** (5 subscores) |

## 5 · Sub-DEC roadmap

| Sub-DEC | Headline | Substrate to land |
|---|---|---|
| **V76.1** | vtk.js mounts in MainCanvasV3 (geometry/mesh) | Replace GeometryPlaceholder + MeshPlaceholder with `<Viewport>` wired to `/api/cases/{id}/geometry/stl` or `/mesh/render` |
| **V76.2** | Real STL/GLB load + per-mode wiring | Use `api.getCaseGeometryStl` / new query hook; data-source="live" \| "fallback" |
| **V76.3** | Camera controls + axes widget | Reset button + axes overlay component |
| **V76.4** | FPS indicator + color legend | rAF-based fps counter + legend for residuals/field |
| **V76.5** | Pillar 15 scorer wired + WebGL fallback | scorer script + `<vtk-webgl-fallback>` non-WebGL branch |
| **V76.6** | 8 visual baselines (61-68) + close DEC + retro | Lock substrate visually |

## 6 · Literal-testid scorer patch (4-arc carry · BUNDLED INTO BOOTSTRAP)

V75.6 retro §"What I'd do differently" promised a fix. Bundle into V76 bootstrap (not a separate sub-DEC) — scorer regexes upgraded from literal-only to template-friendly:

**Before (V73.4/V74.3/V74.5/V75.1 bitten):**
```bash
grep -rE "data-testid=\"observability-" ...
```

**After (V76 bootstrap):**
```bash
grep -rE "data-testid=([\"\\`{][^\"\\`}]*)?observability-" ...
```

Pattern accepts BOTH literal `"observability-foo"` AND template `{`observability-${kind}`}`. Convention-encouraged-but-not-required.

This is a **scorer hardening**, not score gaming — code that previously emitted the same testid via template now scores correctly. V73.4 hash chips would have scored correctly without the 4-subclass workaround.

## 7 · Reverse-stops (V76)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface
3. Any of 60 V75 visual baselines drifts > 0.01 pixel ratio
4. WebGL fallback path swallows real vtk errors (must log + surface)
5. axe-core finds WCAG violations on any of Steps 1-5
6. vtk.js memory leak across remounts (kernel.dispose contract)
7. Pillar 14 regression below 99 (resumability/observability already solid)

## 8 · Honest disclosures (V76 explicitly NOT doing)

Per V75 close §8 + V75 retro open questions:
- ❌ **SSE residuals integration** — V71.L bookmark · 6+ arcs aged · still deferred
- ❌ **Pixel-ratio → SSIM tooling switch** — 3 retros mentioned · 4th if not done; **DEFERRED to V77**
- ❌ **Backend audit-package E2E round-trip smoke** — V74.5 wire still unverified
- ❌ **UX scorer threshold tightening to 100% specs PASS** — would have caught V73.1 fragility earlier
- ✅ **Literal-testid scorer trap** — FIXED in this charter §6 (bundled bootstrap)

## 9 · Counter telemetry (estimated)

- V76-charter: B206
- V76.1-V76.6 + close: B207-B213 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 10 · 4Q gate (every sub-DEC must answer)

1. **LLM offline runnable?** vtk.js path is offline-pure (no LLM call) ✓
2. **Artifacts emitted?** STL/GLB fetched from existing backend routes; no new artifact types
3. **TrustGate intact?** No new MUTATING_ROUTES; viewport is read-only
4. **AI advisory only?** No AI affordances added to viewport surface

## 11 · Single sand-coral accent invariant

vtk.js scenes use neutral colormap (white/grey wireframe + sand-coral #b78b65 ONLY for selected face highlight); legend uses viridis (not coral). No competing accents.

## 12 · Iteration target

| Iter | Goal | Expected min(15) |
|---|---|---|
| 0 | Baseline scoring · all 14 carry V75 100 + Pillar 15 = 0 (placeholders) | 0 |
| 1 | V76.1+V76.2 LANDED · vtk canvas + STL load | 50-70 |
| 2 | V76.3+V76.4 LANDED · camera + legend + FPS | 80-99 |
| 3 | V76.5 LANDED · WebGL fallback + scorer wired | 100 (CLOSE_ELIGIBLE) |
| 4 | Stability re-confirm | 100 (CLOSE_CONFIRMED 2-consec) |
| 5 | V76.6 baselines (61-68) | 100 (3-consec margin) |

**Close gate**: 15-pillar min ≥99 × 2-consecutive iters.

— DEC-V76-charter · 2026-05-17 · LANDED
