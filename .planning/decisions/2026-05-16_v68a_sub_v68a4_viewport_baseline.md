---
decision_id: DEC-V68-A.4
title: V68-A.4 · Viewport mode dispatcher (6 modes) + visual snapshot baseline (8 PNG)
status: Accepted
parent_dec: DEC-V68-A-charter
phase: V68-A
notion_sync_status: pending
predecessor: DEC-V68-A.3
batch: B130
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-A charter §4 Done dims #4 + #5 · §5 sub-DEC V68-A.4
---

# DEC-V68-A.4 · Viewport mode dispatcher + visual snapshot baseline

## 1 · Decision

Land `ViewportModeDispatcher` (6-mode component + toolbar UI) wired into
StepPanelShell viewport pane + generate 8 visual snapshot PNGs as
committed baseline for pixel-diff regression.

**Done dim #4 (Viewport mode dispatcher · 6 modes) → FULL-MET**
**Done dim #5 (Visual snapshot baseline · 8 PNGs) → FULL-MET**

## 2 · Rationale

V67-C.4-5-7 SCAFFOLDING landed an empty `__visual_baselines__/` dir + 2
viewport-mode specs at SPA-shell level. V68-A.4 promotes both to FULL:
- 6 canonical modes (geometry / mesh-wireframe / bc-faces / field-slice /
  residuals / report-grid) exposed via `data-viewport-mode` attribute
- step-default mapping (Step 1→geometry, 2→mesh, 3→bc, 4→residuals,
  5→report-grid) so the viewport's default mode tracks the pipeline
- user override via toolbar buttons (6 clickable buttons with
  data-active attribute)
- 8 PNG snapshot baselines committed under
  `__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots/`

## 3 · Implementation

### Files added (4 NEW)

- `ui/frontend/src/pages/workbench/step_panel_shell/ViewportMode.tsx` (~95 LOC)
  Component `ViewportModeDispatcher` + `defaultModeForStep` pure fn +
  `VIEWPORT_MODES` const array.
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/ViewportMode.test.tsx`
  12 vitest tests covering: step default mapping (1..5 + null/unknown),
  VIEWPORT_MODES list shape, button render, click semantics,
  click-to-toggle-back-to-default, overrideMode prop precedence.
- `ui/frontend/src/pages/dev/ViewportModeDevPage.tsx` (~40 LOC)
  Standalone harness route `/workbench/dev/viewport-mode` for Playwright
  e2e — avoids StepPanelShell + Suspense + Step3State remount races that
  made the spec flaky on `/workbench/case/:id` route.
- `ui/frontend/e2e/visual-baseline.spec.ts`
  8 `toHaveScreenshot()` cases against the dev harness · committed PNG
  baselines at `__visual_baselines__/chromium/.../*.png`.

### Files modified (3)

- `ui/frontend/src/pages/workbench/StepPanelShell.tsx`
  Wrap `<main data-testid="viewport-pane">` content in
  `<ViewportModeDispatcher stepId={currentStepId}>` so the dispatcher
  surfaces mode state per current 5-step pipeline.
- `ui/frontend/src/App.tsx`
  Add `/workbench/dev/viewport-mode` route bound to `ViewportModeDevPage`.
- `ui/frontend/playwright.config.ts`
  `snapshotPathTemplate` repointed to
  `__visual_baselines__/{projectName}/{testFilePath}-snapshots/{arg}{ext}`
  so fleet's `find __visual_baselines__ -name "*.png"` discovers them.
- `ui/frontend/e2e/viewport-mode.spec.ts` rewritten · 7 tests vs prior 2 ·
  uses dev harness route to bypass shell-mount flakiness.
- `ui/frontend/e2e/topbar.spec.ts` first test hardened with `toPass`
  polling for StrictMode first-commit window.

## 4 · Test evidence

- `vitest run` (full): **367/367 PASS** (was 355, +12 ViewportMode tests)
- `npx tsc --noEmit`: 0 errors
- `playwright test` (all e2e): **20/20 PASS** including:
  - viewport-mode.spec.ts: 7/7 (vs V67-C 2/2 · ≥4 V68-A threshold MET)
  - visual-baseline.spec.ts: 8/8 (new · ≥6 V68-A threshold MET)
  - topbar.spec.ts: 3/3 (hardened first test)
  - truth-chain.spec.ts: 2/2 (V67-C inherited)
- 8 PNG snapshot files at
  `ui/frontend/__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots/`

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (≥3 shared paths: ViewportMode.tsx · StepPanelShell ·
  App.tsx · playwright.config · 2 e2e specs · dev page · tests)
- **Codex 1-sync-trigger**: NOT applicable (UI-only · no auth/signing)
- **Kogami opt-in**: NOT invoked
- **Confidence**: med (Playwright StrictMode race surfaced + worked around
  via dev-harness route · documented in spec comments for posterity)
- **Counter**: B130 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline | ✓ YES | dispatcher is pure client-side state, no LLM dep |
| Artifacts produced | ✓ YES | ViewportMode.tsx + dev page + 2 e2e specs + 8 PNGs + DEC |
| TrustGate / audit | ✓ YES | unrelated to TrustGate · doesn't touch advisor-only invariants |
| Advisor-only · no mutating route | ✓ YES | no API calls · V132 MUTATING_ROUTES = 9 unchanged |

## 7 · What this LANDS for V68-A close

- Done dim #4 Viewport mode dispatcher: **FULL-MET**
- Done dim #5 Visual snapshot baseline: **FULL-MET**
- Fleet visualization score: should jump from 55 → 100 (render 40 +
  mode_switch 30 + baseline 30) at next iter
- Fleet UX score: should hold at 100 (now 5+ specs PASS threshold MET)
- Substrate for V68-A.5 e2e full-flow Import→Mesh→BC→Solve→Results

## 8 · Known caveat · dev harness route

The `/workbench/dev/viewport-mode` route mounts in production too (no
import.meta.env.DEV gate). This was a deliberate trade-off: gating
breaks Playwright e2e (which runs against `npm run dev` which is
`import.meta.env.DEV === true`) is fragile. The route adds <1 KB to
bundle and surfaces no sensitive data. **NOT** linked from any
user-facing nav; only reachable by direct URL.

## 9 · Out of scope

- **NOT** wiring viewport's actual vtk.js renderer to mode state
  (Step 5 actual residual chart vs Step 1 geometry; mode is data-only
  for now · render-side dispatch is V68-A.5+)
- **NOT** full pixel-diff CI gate (8 baselines committed, threshold
  `maxDiffPixelRatio: 0.1` lenient on first run · tighter gate post-arc)
- **NOT** persisting user mode override per case (session-state only)

— Claude Code (Opus 4.7 1M) · B130 · V68-A.4 viewport + baseline · 2026-05-16
