# M-PANELS · Pre-implementation Surface Scan

**Date**: 2026-04-28
**Scope**: Spec_v2 §E Step 1 (DEC-V61-096)
**Verdict**: 3 deviations from spec_v2 noted (corrected before Step 2 skeleton commit); no blockers found.

---

## Q1 · Routing setup

- **Router**: `BrowserRouter` (`ui/frontend/src/main.tsx:4`) + `Routes` / `Route` (`App.tsx`).
- **All routes wrapped in `<Layout />`** (`App.tsx:51-97` · `Layout.tsx:40-108`):
  - 56px-wide left `<aside>` sidebar with NavLinks (/pro, /workbench, /cases, /decisions, /runs, /audit-package, /learn)
  - `<main>` flex-1 with `<Outlet />` for the child route
- **Current workbench routes** (using `case/:caseId/...` prefix, NOT `/<caseId>/...`):
  - `/workbench/case/:caseId/edit` → `<EditCasePage />` (`App.tsx:81`)
  - `/workbench/case/:caseId/mesh` → `<MeshWizardPage />` (`App.tsx:86`)
  - `/workbench/case/:caseId/runs` → `<RunHistoryPage />` (`App.tsx:90`)
  - `/workbench/case/:caseId/run/:runId` → `<RunDetailPage />` (`App.tsx:91`)
  - Plus `/workbench/today`, `/workbench/index`, etc.
  - Plus the import flow at `/workbench/import` (separate from a case_id)

**Deviation from spec_v2 §A.4**: spec_v2 declared the route shape as `/workbench/<case_id>` and legacy redirects as `/workbench/<case_id>/{import,edit,mesh,run}`. Actual existing routes use `/workbench/case/:caseId/{edit,mesh,runs,run}`. The new shell + redirects must use `/workbench/case/:caseId` (with `case/` segment).

## Q2 · React Query

**Already wired ✓** — no setup needed.

- `QueryClient` + `QueryClientProvider` instantiated at `main.tsx:9-22`
- Defaults: `staleTime: 30_000`, `refetchOnWindowFocus: false`, `retry: 1`
- 15+ existing pages use `useQuery` / `useMutation` (DashboardPage, DecisionsQueuePage, AuditPackagePage, CaseEditorPage, CaseListPage, WorkbenchIndexPage, ExportPanel, BatchMatrix, ValidationReportPage, etc.)

**Implication**: M-PANELS Step components can use `useQuery` / `useMutation` directly. The skeleton commit does NOT need a react-query install / wireup pass.

## Q3 · ImportPage upload primitives

**File**: `ui/frontend/src/pages/workbench/ImportPage.tsx`

Extractable blocks for `<Step1Import>`:
- `:79-80` — constants (`ACCEPT`, `MAX_DISPLAY_MB`)
- `:82-99` — state setup (`file`, `uploading`, `response`, `rejection`, `networkError`, `featureState`) + feature-probe effect
- `:101-106` — `reset()`
- `:108-128` — `onUpload()` calling `api.importStl(file)` + typed `ApiError.detail` rejection handling
- `:130-225` — upload input UI + rejection display
- `:227-255` — success response card with geometry preview
- `:271` — Viewport call site (currently `<Viewport stlUrl={...} />` · no `format` prop · uses default `'stl'`)

**Switch to glb (per spec_v2 §A.6 + §G AC#5)**: change `:271` from
```tsx
<Viewport stlUrl={...} />
```
to
```tsx
<Viewport format="glb" glbUrl={`/api/cases/${response.case_id}/geometry/render`} />
```
The Viewport already supports `format='glb'` (M-RENDER-API · `Viewport.tsx:28`).

## Q4 · MeshWizardPage form primitives

**File**: `ui/frontend/src/pages/workbench/MeshWizardPage.tsx`

Extractable blocks for `<Step2Mesh>`:
- `:24-29` — state (`meshMode`, `running`, `response`, `rejection`, `networkError`)
- `:37-55` — `onGenerate()` calling `api.meshImported(caseId, meshMode)` + typed rejection handling
- `:89-109` — radio group for `meshMode: "beginner" | "power"`
- `:112-119` — "Generate mesh" button (disabled while `running`)
- `:131-161` — success response card with mesh summary

**API endpoint** (`client.ts:223-253`): `api.meshImported(caseId, meshMode)` → POST `/api/import/{caseId}/mesh` with `{ mesh_mode }`.

**Wire to `<Viewport format='glb' glbUrl="/api/cases/<id>/mesh/render">`** after successful mesh generation (M-RENDER-API endpoint).

## Q5 · Tailwind tokens

**File**: `ui/frontend/tailwind.config.ts`

- `surface-100` through `surface-950` — full grayscale ladder (in use across pages)
- `contract-{pass, hazard, fail, unknown}` — for state colors
- **No `accent-*` scale**; pages use `emerald-{300, 400, 500}` for "go / success" actions (e.g. file input button at `ImportPage.tsx:183`)

**Deviation from spec_v2 §A.7**: spec_v2 §A.7 referenced `bg-accent-500/15 border-accent-500` for active step. Use `bg-emerald-500/15 border-emerald-500` (or `bg-emerald-500/10 text-emerald-300` to match existing button conventions).

Updated step-state mapping for the StepTree:
- Active: `bg-emerald-500/10 border-emerald-500/40 text-emerald-200`
- Completed: `text-emerald-400` + check icon
- Error: `border-rose-500 text-rose-200` (already in spec_v2 · matches `Viewport.tsx` error banner)
- Pending: `text-surface-500`

## Q6 · API client

**File**: `ui/frontend/src/api/client.ts`

26 endpoint methods including the M-RENDER-API ones we'll consume (`importStl`, `meshImported`, `getCase`, `getCaseYaml`, etc.). Typed `ApiError` class with `status: number` + `detail?: unknown`.

**No new client methods needed for M-PANELS Tier-A.** The shell consumes the existing `getCase` + `importStl` + `meshImported` + `wizardRunStreamUrl` endpoints, plus M-RENDER-API endpoints reached directly by URL via the Viewport's `glbUrl` prop (no client method needed since the URL is constructed inline).

## Q7 · Existing tests

| Path | Lines |
|---|---|
| `pages/workbench/__tests__/NewCaseWizardPage.test.tsx` | 231 |
| `pages/workbench/__tests__/WorkbenchRunPage.test.tsx` | 169 |
| `visualization/__tests__/glb_loader.test.ts` | 125 |
| `visualization/__tests__/stl_loader.test.ts` | 130 |
| `visualization/__tests__/Viewport.test.tsx` | 252 |
| **Total** | **907** |

**Important**: `ImportPage.tsx` and `MeshWizardPage.tsx` have NO test coverage today. M-PANELS Tier-A will:
- Test the new Step1Import / Step2Mesh components (mocked api.importStl / api.meshImported)
- NOT add retroactive tests for the legacy ImportPage / MeshWizardPage shells (they're slated for removal in M7-redefined)

## Q8 · App.tsx layout decision

**Layout wraps all routes** including workbench. The three-pane M-PANELS shell has two design choices:

**Option A · Keep Layout, replace Outlet content** (chosen):
- New route `<Route path="/workbench/case/:caseId" element={<StepPanelShell />} />` renders inside the existing Layout
- The Layout's left sidebar (56px wide) stays visible alongside the StepPanelShell's own left step-tree
- StepPanelShell has its own top bar / left step-tree / center / right / bottom

**Option B · Replace Layout for workbench routes**:
- Add `<Route path="/workbench/case/:caseId" element={<WorkbenchShellLayout />}>` outside the existing Layout wrapper
- StepPanelShell IS the layout
- Hides the global sidebar inside the workbench

**Decision (provisional · revisit at Step 2)**: Option A. Reasons:
- Smaller diff in App.tsx (one new Route, no restructure)
- Global navigation stays visible (engineers can flip back to /pro / /cases)
- Aligns with ANSYS Workbench convention (global navigation persists; case-internal navigation is the inner shell)
- Trivially reversible to Option B if visual smoke shows the dual-sidebar feels cluttered

**Deviation from spec_v2 §A.4**: spec_v2 didn't make this decision explicit. The implementation chooses Option A; if Option B turns out to be needed (clutter complaint at Step 10 visual smoke), the change is one-line in App.tsx (replace `<Layout>` wrap with the workbench shell) — track as a Tier-B candidate.

---

## Deviations from spec_v2 (apply during Step 2 skeleton commit)

| # | Spec_v2 reference | Spec said | Actual / corrected | Rationale |
|---|---|---|---|---|
| D1 | §A.4 routing contract | `/workbench/<case_id>` + legacy `/workbench/<case_id>/{import,edit,mesh,run}` | `/workbench/case/:caseId` + legacy `/workbench/case/:caseId/{edit,mesh,run}` (no separate `/import` — import is at `/workbench/import` standalone today; map to `?step=1` only when arriving from a case context) | existing routes use `case/` segment; my spec_v2 used the wrong path |
| D2 | §A.7 design tokens | `bg-accent-500/15 border-accent-500` | `bg-emerald-500/10 border-emerald-500/40 text-emerald-200` | no `accent-*` scale exists; emerald is the existing convention |
| D3 | §A.4 layout decision | not specified | Option A: keep Layout wrapper; StepPanelShell renders inside `<Outlet />` | smaller diff + global nav persists; trivially reversible |
| D4 | §A.4 + brief §Tier-A 7 — legacy redirects | `/workbench/case/:caseId/{edit,mesh,run}` redirect to `/workbench/case/:caseId?step=N` in M-PANELS Tier-A | **Deferred to M7-redefined** (added 2026-04-28 during Step 6 implementation): legacy routes stay alive as direct routes in M-PANELS Tier-A. Step 3-5 placeholder bodies link to legacy as an explicit fallback. M7-redefined lands the redirect when Step 3 has functional parity with the YAML editor. | Redirecting today would orphan engineers using `/edit` for live BC editing while Step 3 is just a placeholder. Placeholder copy + per-step link to legacy gives an explicit fallback path with zero deprecation surface. |

**No blockers.** Four deviations documented, all minor.

---

## §11.1 BREAK_FREEZE forecast

The skeleton commit will touch `ui/frontend/src/App.tsx` (new route) but NOT yet edit `ui/frontend/src/pages/workbench/**` (it adds new files under `pages/workbench/step_panel_shell/**`). The first commit that EDITS `pages/workbench/ImportPage.tsx` (Step 4 per spec_v2 §E) will be the one carrying the `BREAK_FREEZE: rationale=Addendum 3 §3 binding (M-PANELS · DEC-V61-096)` trailer. Skeleton commit is freeze-quota-neutral (only adds new files).

## Skeleton-commit file plan (Step 2)

New files (all freeze-neutral):
- `ui/frontend/src/pages/workbench/StepPanelShell.tsx` (top-level shell)
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts`
- `ui/frontend/src/pages/workbench/step_panel_shell/StepTree.tsx` (placeholder body)
- `ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx` (placeholder body)
- `ui/frontend/src/pages/workbench/step_panel_shell/StatusStrip.tsx` (placeholder body)
- `ui/frontend/src/pages/workbench/step_panel_shell/TopBar.tsx` (placeholder body)
- `ui/frontend/src/pages/workbench/step_panel_shell/StepNavigation.tsx` (placeholder body)
- `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step{1Import,2Mesh,3SetupPlaceholder,4SolvePlaceholder,5ResultsPlaceholder}.tsx` (placeholder bodies)
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/StepPanelShell.test.tsx` (smoke test asserting shell mounts + 5 step IDs render)

Modified files:
- `ui/frontend/src/App.tsx` — add `<Route path="/workbench/case/:caseId" element={<StepPanelShell />} />` BEFORE the existing case-prefixed routes so the new shell wins on direct visits; legacy routes (`/edit`, `/mesh`, `/run`) keep their existing `<EditCasePage>` / `<MeshWizardPage>` / `<WizardRunPage>` for now (redirects land in Step 6, NOT skeleton)

The skeleton commit ships:
- Shell mounts at `/workbench/case/:caseId` with 5-pane layout markup but ALL bodies are placeholder
- Type contract (StepDef, StepId, etc.) finalized
- Smoke test confirms shell mounts cleanly with no runtime errors
- Tier-A wiring continues in Steps 3-6
