# M3.2 retrospective visual audit · cross-track findings backlog · 2026-05-25

> Surfaced during M3.3 cycle 1 visual spot-check (first real screenshot of live workbench after M3.2 close).
> Source screenshots: /tmp/m33_idle.png, /tmp/m33_toast.png, /tmp/m33_body_toast.png, /tmp/m33_full.png
> SSOT entry: this file is THE backlog tracker for these 5 findings until each one is closed via DEC/PR/dispatch.
>
> **CRITICAL UPDATE 2026-05-25 M3.3 cycle 3** — cross-step spot-check at `--step mesh / physics / boundary` confirms ALL 5 findings are **uniquely localized to step=geometry** when the case has no actual CAD upload. At mesh / physics / boundary the workbench renders correctly: 3D viewport works (where applicable), no number collision, no dual-display banner, rich right-side rails, no sidebar dead-space. **Reframe**: B1-B5 are NOT workbench-wide defects; they are **graceful-degradation failures at step=geometry when geometry artifacts are absent**. Likely root: multiple widgets at step 1 assume CAD is imported and bail out / mis-position when it isn't, instead of falling back to an empty-state placeholder. Investigations should focus on "what does the geometry step render when the case has no CAD?" — a common state at the START of a workflow.
> Cross-step proof screenshots: `/tmp/cfd_workbench_screenshots/step_mesh/*` · `/step_physics/*` · `/step_boundary/*`.

## Disposition guide
| Status | Meaning |
|---|---|
| Open | not yet investigated, not assigned |
| Investigating | someone is looking into root cause |
| Assigned-track | dispatched to a specific track owner |
| In-flight | active work, links to commit/PR |
| Closed | resolved with link to closing commit |

## Findings

### B1 · MainCanvas viewport renders 0% of the right ~70% of workbench

**Severity**: P1 (workbench is unusable for visual CFD work — the actual 3D model is the core artifact)
**Track**: M-VIZ / VtkCanvasV3 / WebGL pipeline (M3.4 charter scope)
**Status**: **CLOSED 2026-05-25 M3.4 cycle 2** — 1-LOC fix landed at `ModeRendererGeometry.tsx:107` (gate `useAssemblyGlb` on `authoredCadParts`). Verified: post-fix screenshot shows no error popup; empty area routes to existing `<GeometryEmptyState/>` branch (line 287). Cycle 3+ will polish the empty-state visual (currently low-contrast small text — needs CTA + Upload affordance).
**Root cause (per M3.4 cycle 1 subagent S4)**: `ModeRendererGeometry` unconditionally falls back to `/blueprints/v4/apu-cad-assembly.glb` (15 MB static APU blueprint) when case has no CAD. `assemblyProbe.available` always returns true → ViewportV4 mounts → `vtkGenericRenderWindow.newInstance()` allocates a WebGL context → context allocation fails (browser context limit) → `vtk.js Rendering/OpenGL/RenderWindow.js:243` unconditionally wraps null context in `new Proxy(null, ...)` → V8 throws "Cannot create proxy with a non-object as target". The V4 ErrorBoundary catches and shows the popup.
**Cross-step proof**: Mesh / Physics / Boundary modes have `probe.available === true` gates on per-case artifacts (no static fallback). They never hit the proxy creation path.
**Fix applied**: `useAssemblyGlb = !useCaseGlb && !waitForCaseGlb && assemblyProbe.available === true && authoredCadParts` (added `&& authoredCadParts` clause). Cases without CAD parts now route to GeometryEmptyState.

### B2 · Number collision at bottom-center: "17 2 2.0 18 76" overlap

**Severity**: P2
**Track**: V4 shell layout (was misclassified as DOE / dashboard layer)
**Status**: **CLOSED · CASCADE-CLEARED by M3.4 cycle 5 (B6 fix) · 2026-05-25**. The numbers were not absolute-positioned widgets — they were the legitimate bottom KpiStrip stats (零件总数 / 待修补 / 包裹尺寸 / 流体域体积) being squished onto the same 148px column when `<main>` collapsed due to B6's content-overflow leak. With the W4 ShellV4 wrapper gaining `w-[300px] shrink-0` (cycle 5), main returns to ~860px and the KpiStrip lays out cleanly as 4 columns.
**Verification**: post-cycle-5 screenshot `/tmp/cfd_workbench_screenshots/m33_ux_demo_seed_idle.png` shows bottom row clean: "17 零件总数 · 2 待修补 · 2.0 包裹尺寸 · 18.76 流体域体积".

### B3 · Bottom horizontal banner duplicates the rail's gap content

**Severity**: P2 (visual redundancy · "缺字段 / Missing: case_family" + same body_text + small action icon appear AGAIN at the bottom while already displayed in DynamicFramePanel)
**Track**: M3.0 (DynamicBottomCards) layered display
**Status**: **CLOSED · BY DESIGN 2026-05-25 M3.4 cycle 1 subagent S3**.
**Investigation result** (per M3.4 cycle 1 subagent S3): rail vs bottom-cards is intentional dual-driver UX per M3.0 charter. `_pick_rail_primary` (workbench_decide.py:228) applies a strict priority cascade (FAIL → critical gap → WARN → soft gap → default) and picks ONE winning item. `_pick_bottom_cards` (workbench_decide.py:591-596) surfaces ALL step-relevant problems + gaps (8-card cap, severity-sorted). With the m33 demo seed having only ONE info_gap (`case_family`), both layers necessarily show the same single content → looks duplicated. Multi-gap cases would show 1 in rail + N in cards.
**File evidence**: `.planning/decisions/2026-05-22_v61_202_workbench_dynamic_guided.md:34-35` · `ui/backend/services/workbench_decide.py:228, 591-596` · `DynamicFramePanel.tsx:1-6` + `DynamicBottomCards.tsx:1-6`.
**No action needed**. Kept open in this backlog for archive only.

### B4 · Left sidebar (~265px wide) has dead vertical space below tree

**Severity**: P3 (real estate waste · not breaking · low priority)
**Track**: V4 shell layout / overall workbench information architecture
**Status**: Open
**Evidence**: Left sidebar shows case tree (案例树 LIVE · 搜索 · R-042 · 几何 · 零件 17 · 修复 2 · 包裹 1 · 区域 5 · 网格 · 物理模型 · 工况与求解 · 结果) but the bottom ~60% of the sidebar is empty.
**Hypothesis**: Sidebar height = full viewport but content collapses. Could host a minimap, recent activities, or thumbnails.
**Repro**: same URL as B1.
**Action**: defer until M3.4+ unless V4 shell owner picks it up. Not blocking.

### B6 · ModeRendererGeometry rendered in narrow 148px column at step=geometry

**Severity**: P1
**Track**: V4 shell layout
**Status**: **CLOSED 2026-05-25 M3.4 cycle 5** — 2-LOC fix at `WorkbenchShellV4.tsx:255`. Was a CSS content-overflow leak (NOT a per-step layout switch as initially hypothesized).
**Root cause (per M3.4 cycle 4 subagent investigation)**: `<V4ErrorBoundary zone="RightPanel">`'s wrapper `<div className="flex flex-col">` (no width, no shrink-0) hosted `DynamicFramePanel` whose `<p>` body_text had no `max-w-*`. At step=geometry the seed case's long `case_family` info_gap body_text gave the wrapper huge intrinsic width. Flex resolution: LeftRail held 242px, `<main>` (`min-w-0 flex-1`) collapsed to ~148px, wrapper took ~1050px. Mesh/Physics/Boundary worked silently because their `rail_primary.body_text` was short and stayed under `RightPanelV4`'s internal `w-[300px]`. The "different layout per step" hypothesis was wrong — the shell is identical at every step; only body_text length differed.
**Fix applied**: `<div className="flex w-[300px] shrink-0 flex-col">` — makes the implicit contract (the wrapper should be 300px) explicit and content-pressure-proof.
**Cascade effect**: closing B6 also closed B2 + B5 (both were downstream of the layout collapse, not independent defects).
**Verification**: post-fix DOM check would show empty-scene bbox width ≈ 860 (vs. 148 pre-fix). Screenshot at /tmp/cfd_workbench_screenshots/m33_ux_demo_seed_idle.png shows polished GeometryEmptyState + Upload CAD CTA centered in main viewport area.

### B5 · Step rail (01-07 indicators) overlaps the B3 bottom banner

**Severity**: P2
**Track**: V4 shell layout
**Status**: **CLOSED · CASCADE-CLEARED by M3.4 cycle 5 (B6 fix) · 2026-05-25**. Same root cause as B2 — the visual overlap was a downstream of `<main>` getting squished to 148px (which collapsed vertical layout and pushed step-rail rendering on top of bottom-card banner). With cycle 5's wrapper width fix, both elements have proper vertical space and lay out cleanly.
**Verification**: post-cycle-5 screenshot shows step rail (01-07 indicators) cleanly below the bottom-card banner, no overlap.

## Process change request

These 5 findings were ALL surfaced by a single 30-second screenshot. None of them were caught by unit tests or Playwright E2E because tests assert testid presence + click + role=status, not visual layout.

**Recommendation**: every M-track cycle MUST include a screenshot spot-check as part of the cycle's close. This is being implemented separately as `scripts/dogfood/m33_ux_screenshot.mjs` + process doc.
