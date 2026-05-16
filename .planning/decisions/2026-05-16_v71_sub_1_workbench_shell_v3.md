---
decision_id: DEC-V71-1
title: V71.1 · WorkbenchShellV3 · 4-panel blueprint-aligned mount at /workbench/v3
status: Accepted
parent_dec: DEC-V71-charter
phase: V71
notion_sync_status: pending
predecessor: DEC-V71-charter
batch: B170
confidence: high
autonomous_governance: true
verdict: LANDED
v_row_landed: V71.1 (Done dimension #1 of 9)
substrate: V71 charter LANDED B169 · 8 v3 blueprints at .planning/blueprints/v3/ · iter-0 baseline weighted=79.84 · functional pillar=0 (untouched until shell exists)
---

# DEC-V71-1 · WorkbenchShellV3 · 4-panel blueprint-aligned route mount

## 1 · Decision

Land the parallel route `/workbench/v3/case/:caseId` (alias `/workbench/v3`) hosting `<WorkbenchShellV3>` — the blueprint-aligned 4-panel persistent workspace. Existing legacy routes remain untouched (no migration this iteration). The v3 surface is **display-only** · zero new MUTATING_ROUTES (locked at 9 · V110 invariant preserved).

## 2 · Architecture (per .planning/blueprints/v3/INDEX.md Image 01)

```
Row 1 (40px):   TopBarV3 (breadcrumb · run state · SHA · ⌘K · avatar · gear)
Row 2:
  Col 1 (48px):    ActivityBarV3 (Workbench / Catalog / Runs / Benchmarks / Tutorial / Settings)
  Col 2 (260px):   CaseBrowserV3 (WORKSPACE + RECENT · 11 whitelist cases)
  Col 3 (1fr):     PipelineStripV3 (44px · 5 steps) +
                   ViewportToolbarV3 (36px · 6 modes) +
                   MainCanvasV3 (1fr) +
                   BottomPanelV3 (32px collapsed / 180px expanded)
  Col 4 (340px):   RightPanelV3 (3 tabs · Inspector / Advisor / TruthChain)
```

CSS grid: `template-columns: 48px 260px 1fr 340px · template-rows: 40px 1fr`.

## 3 · Cross-step rules (V71.S/V71.T)

- **V71.S**: Viewport mode is INDEPENDENT of pipeline step · engineer can override at any time · default per step but override persists.
- **V71.T**: Inspector content adapts to (stepId, viewportMode). Step 4 + viewport=mesh → ACTIVE SOLVE + MESH SUMMARY (Image 08 cross-step variant).
- Step 4+ entry auto-expands bottom panel.

## 4 · Components landed (15 + 1 test)

| File | LOC | Purpose | Image |
|------|----:|---------|-------|
| `WorkbenchShellV3.tsx` | ~180 | Main shell + grid + state hub | Image 01 |
| `TopBarV3.tsx` | ~40 | 40px topbar | Image 01 |
| `ActivityBarV3.tsx` | ~65 | 48px left strip | Image 01 |
| `CaseBrowserV3.tsx` | ~130 | Left panel · cases | Image 01 |
| `PipelineStripV3.tsx` | ~80 | 5-step strip | Image 02-07 |
| `ViewportToolbarV3.tsx` | ~95 | 6-mode toolbar | Image 02-07 |
| `MainCanvasV3.tsx` | ~50 | Canvas router | Image 02-07 |
| `BottomPanelV3.tsx` | ~225 | Collapsible 4-tab bottom | Image 03/05/08 |
| `RightPanelV3.tsx` | ~90 | 3-tab right panel | Image 02-07 |
| `right-panel/InspectorContent.tsx` | ~340 | Step-aware Inspector | Image 02-04/07/08 |
| `right-panel/AdvisorContent.tsx` | ~340 | V130/V132 advisor surface | Image 06 |
| `right-panel/TruthChainContent.tsx` | ~215 | Provenance chain | Image 05/07 |
| `canvas/GeometryPlaceholder.tsx` | ~75 | SVG geometry wireframes | Image 02 |
| `canvas/MeshPlaceholder.tsx` | ~85 | SVG mesh grid | Image 03 |
| `canvas/BCPlaceholder.tsx` | ~50 | BC color patches | Image 04 |
| `canvas/ResidualsChartV3.tsx` | ~180 | 5-line log chart | Image 05 |
| `canvas/ReportComparisonV3.tsx` | ~155 | Ghia 1982 gold vs computed | Image 07 |
| `canvas/EmptyCanvasV3.tsx` | ~25 | Empty state | Image 01 |
| `__tests__/WorkbenchShellV3.test.tsx` | ~195 | Smoke + V130/V132 contract | — |

Total: ~2770 LOC across 21 files (1 staged App.tsx + 1 tailwind.config.ts + 19 new).

## 5 · V130/V132 contract preservation

The Advisor surface inherits the existing AIAdvisorPanel hard contract:

- GET-only API calls (no POST/PUT/DELETE)
- Citation chips render `path · sha · anchor` and expand inline to corpus text
- `llm_available=false` → calm "advisor offline" banner (not red error)
- ZERO "apply / submit / execute / auto-fix / 应用 / 提交 / 执行" buttons
- `data-testid="advisor-advisory-badge"` always present

V71.4 will add a dedicated contract test that snapshots the Advisor tab DOM and asserts no mutating button surface exists. V71.1 includes a precursor assertion in `WorkbenchShellV3.test.tsx`.

## 6 · Tailwind tokens added

Added `v3.*` namespace to `ui/frontend/tailwind.config.ts`:
- `bg / surface1 / surface2 / border / borderActive`
- `textPrimary / textSecondary / textTertiary`
- `accent` (sand-coral #b78b65)
- `inlet / wall / symmetry / custom` (dusty CFD palette)

## 7 · Tests

`npx vitest run` → **414 pass** (was 405 · +9 v3 tests · 0 regressions).
`npx tsc --noEmit` → **PASS** (0 errors).

The 9 new tests assert:
1. Shell mounts all 4 panels + topbar + bottom collapsed bar
2. `data-v71-ui-shell="true"` tag present for visual baseline contract
3. 5 pipeline steps exposed (`pipeline-step-1..5`)
4. 6 viewport modes exposed (`viewport-mode-{geometry|mesh|bc|field|residuals|report}`)
5. Pipeline step 4 click auto-expands bottom panel
6. 3 right-panel tabs (Inspector / Advisor / TruthChain)
7. Advisor tab → advisory-only badge + ZERO mutating buttons (V130/V132)
8. Bottom panel collapse↔expand toggles
9. 6 activity-bar entries

## 8 · Risk + reverse-stop

**Risks**:
- SVG canvas mocks are static · V71.3 wires real residual SSE → V71.6 baselines may shift then.
- ResidualsChartV3 hand-tuned data points · V72 should swap for live `/api/runs/:id/residuals` SSE.
- ReportComparisonV3 currently uses Ghia 1982 as both reference AND computed (with sine perturbation) · V72 replaces "computed" with real solver output.

**Reverse-stop conditions** (per V71 charter):
- Visual baseline > 0.05 SSIM drift from blueprint image (V71.6 will lock baselines 23-30)
- Any MUTATING_ROUTE added → automatic V132 violation → revert
- TSC fails or vitest <414 → revert

## 9 · Goal-backward map

Charter Done dim #1 ("v3 route mounts at /workbench/v3/case/:id with all four panels visible") → **LANDED**.

Fleet pillar impact (predicted, will verify on next score iter):
- **functional** (0 → expected ≥80): 4-panel shell now mounts at expected route
- **industrial_ui** (48 → expected ~70): v3 tokens + sand-coral accent landed but blueprint baselines 23-30 not yet locked
- **viz** (92 → no change): canvas placeholders are SVG · same as before
- **novice / ux / cfd_breadth / smoke / stability / quality / physics**: no expected regression (parallel route)

## 10 · Surface-scan trailer

**Surface-scan: clean.** No pre-existing `ui/frontend/src/pages/workbench/v3/` directory existed before this batch. This is greenfield per V71 charter §3. The legacy `StepPanelShell` route (`/workbench/case/:caseId`) is untouched.

## 11 · Counter

Counter +1 (V71 = autonomous_governance: true). Cumulative arc counter for V71: **2** (charter + this sub-DEC).

## 12 · Next

V71.2 starts immediately — wire viewport BC color palette into actual canvas (currently the inspector colors BCs but BCPlaceholder uses its own palette) + add MaterialCard interactive expansion + run a fresh fleet score iteration to capture the functional pillar rise.

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
