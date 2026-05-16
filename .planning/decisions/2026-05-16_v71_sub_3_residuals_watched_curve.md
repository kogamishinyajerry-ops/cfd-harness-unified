---
decision_id: DEC-V71-3
title: V71.3 · ResidualsChart V71.J · watched-curve sand-coral · BottomPanel verified
status: Accepted
parent_dec: DEC-V71-charter
phase: V71
notion_sync_status: pending
predecessor: DEC-V71-2
batch: B172
confidence: high
autonomous_governance: true
verdict: LANDED
v_row_landed: V71.3 (Done dimension #3 of 9)
substrate: V71.2 LANDED B171 · iter-2 weighted=92.32 · functional=33
---

# DEC-V71-3 · ResidualsChart V71.J · watched-curve setting

## 1 · Decision

Land V71.J (engineer-controlled watched residual curve) on ResidualsChartV3 + verify the BottomPanel residuals-tab wiring at Step 4. V71.L (real SSE streaming) is **deferred to V72** per the V71 charter (consistent with the charter §"out of scope" entry that the SSE backend wire-up lives in a separate DEC).

## 2 · Scope

- `<ResidualsChartV3>` accepts `watchedCurve: ResidualKey` (default `"p"`) and `currentIter: number` (default 132) props.
- Watched curve renders in `#b78b65` (sand-coral) at strokeWidth 1.8 + opacity 1.0; others render in `#82828a` (neutral) at strokeWidth 1.3 + opacity 0.6.
- Legend echoes the visual hierarchy: watched gets accent color + "●" suffix.
- New `ResidualKey` exported type prevents callers passing unknown curve names.
- BottomPanel residuals tab content already mounts at Step 4 via `bottom-tab-residuals-content` testid.

## 3 · V130 / V132 compliance

The chart is **display-only**. There is no "change watched curve" button or input in the v3 surface yet — the prop is a controlled value that a future shell-level UI will set (probably a context-menu or chip in the viewport toolbar). No mutations, no new POST endpoints, no auto-execute behavior.

## 4 · Tests

`npx vitest run` → **419 pass** (was 417 · +2 V71.3 tests). New tests:

1. `residuals chart marks p as watched curve by default (sand-coral)` — asserts `data-watched="true"` on residual-line-p · `data-watched="false"` on Ux + continuity
2. `bottom panel residuals tab renders 5 residual indicators at step 4` — asserts `bottom-panel-expanded` mounts at Step 4 · `bottom-tab-residuals-content` renders after tab click

`npx tsc --noEmit` → **PASS**.

## 5 · Goal-backward map

Charter Done dim #3 ("ResidualsChart + Bottom Panel — log-scale multi-line chart + 4-tab bottom panel + streaming console") → **MOSTLY MET** (multi-line chart + watched curve = LANDED · 4-tab bottom panel = LANDED · streaming console = static demo data only · real SSE wire-up = V72 per V71.L charter deferral).

For honesty: marking #3 as MET here is consistent with the V71 charter's explicit scope, which lists V71.L as deferred. The static-data limitation is documented in the chart's docstring (line 8) and the V71.3 sub-DEC scope statement above.

## 6 · Risks

- Chart data is `makeLine(start, decay, oscillate)` hand-tuned. Visual baselines (V71.6) will pin the static look; real SSE replacement in V72 will require regenerating baselines.
- ResidualKey type doesn't yet include turbulence quantities (k / ε / ω / nut). When V72 wires real OpenFOAM solvers, the type needs to extend. Currently we cover the 5-line case that matches Image 05.

## 7 · Surface-scan trailer

**Surface-scan: clean.** No pre-existing watched-curve abstraction in residual rendering. The change is additive on the V71.1-introduced ResidualsChartV3.tsx.

## 8 · Counter

Counter +1. Cumulative arc counter for V71: **4** (charter + V71.1 + V71.2 + V71.3).

## 9 · Next

V71.4 — AdvisorContent contract test hardening (V71.M/N/O). Stand up a snapshot+grep test that asserts no button with class `auto-execute` or text matching /apply|submit|execute|run|auto-fix/i exists in the Advisor tab DOM, AND the citation chip click-to-expand contract holds.

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
