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

**Severity**: P2 (visual chaos · suggests multiple absolute-positioned stat widgets bleeding into the same area)
**Track**: DOE / design exploration dashboard layer OR layout governance
**Status**: Open
**Evidence**: Around bottom-center of the workbench (between the rail panel and the step-rail), there are 5+ numeric labels (17, 2, 2.0, 18, 76, "76" very large) overlapping each other from different components. Some are partially obscured.
**Hypothesis**: Multiple components use position:absolute with overlapping z-index. Possibly a particle estimator + cell count + DOE confidence label all rendering on the same coordinates.
**Repro**: same URL as B1.
**Action**: identify the components (grep for the numeric values in src/pages/workbench/), then propose a layout consolidation.

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

**Severity**: P1 (severely limits empty-state UX visibility · main viewport area is occupied by other-component dark void)
**Track**: V4 shell layout / step-geometry workbench composition
**Status**: Open · surfaced 2026-05-25 M3.4 cycle 3 (DOM inspection during empty-state polish)
**Evidence**: At /workbench/case/m33_ux_demo_seed?step=geometry, DOM check shows `[data-testid="v4-mode-geometry-empty-scene"]` bbox = x=242, y=144, width=148, height=489. ModeRendererGeometry's root has `flex h-full w-full flex-col` (line 124) but ITS parent only allocates 148px width. Mesh/Physics/Boundary mode renderers visibly fill ~860px of the right viewport area (per cross-step screenshots at /tmp/cfd_workbench_screenshots/step_*) — so the V4 shell layout differs by step.
**Hypothesis**: V4 shell uses a different layout for step=geometry (likely splits the right area into multiple columns reflecting the "辅助几何准备 / 自动识别零件 / 缝隙检查 / 包裹建议 / 包裹尺寸 / 流体域提取" cards visible in screenshots) — and ModeRendererGeometry is bound to ONE of those columns, not the full-width viewport area. The right ~70% (where mesh/physics/boundary show their viewport) is occupied by something other than ModeRendererGeometry at step=geometry.
**Repro**: same URL · check with playwright DOM query for testid bboxes.
**Action**: investigate what component owns the right ~70% at step=geometry · is it intentional multi-column layout or layout bug · if intentional, the empty-state CTA (cycle 3 work) should be hoisted to that primary column · if bug, V4 shell should give ModeRendererGeometry the same full-viewport allocation as other modes.

### B5 · Step rail (01-07 indicators) overlaps the B3 bottom banner

**Severity**: P2 (visual overlap · the step rail and the bottom-cards banner sit on the same y-range, fighting for space)
**Track**: V4 shell layout
**Status**: Open
**Evidence**: At bottom of screenshot, the step indicators "01 导入 完成 / 02 几何 进行中 / 03 网格 待处理 / 04 物理 待处理 / 05 边界 待处理 / 06 求解 待处理 / 07 后处理 待处理" are partially obscured by the B3 banner.
**Hypothesis**: Step rail and BottomCards both render absolutely at bottom of viewport without z-index coordination.
**Repro**: same URL as B1.
**Action**: tied to B3 — once B3 disposition is decided, B5 likely resolves by repositioning or removing the duplicate banner.

## Process change request

These 5 findings were ALL surfaced by a single 30-second screenshot. None of them were caught by unit tests or Playwright E2E because tests assert testid presence + click + role=status, not visual layout.

**Recommendation**: every M-track cycle MUST include a screenshot spot-check as part of the cycle's close. This is being implemented separately as `scripts/dogfood/m33_ux_screenshot.mjs` + process doc.
