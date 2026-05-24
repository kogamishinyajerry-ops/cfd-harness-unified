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
**Track**: M-VIZ / VtkCanvasV3 / WebGL pipeline
**Status**: Open
**Evidence**: At /workbench/case/m33_ux_demo_seed?step=geometry on a 1440×900 viewport, the right 70% of the main canvas area is solid black with a visible error popup: "MainCanvas 区域渲染失败 / Cannot create proxy with a non-object as target". Error appears at top-left of the would-be canvas area.
**Hypothesis**: Proxy creation in VtkCanvas state setup is called with undefined/null target — may be a regression after a recent vtk.js or React refactor.
**Repro**: bash scripts/dogfood/stage_m33_ux_demo.py · http://localhost:5173/workbench/case/m33_ux_demo_seed?step=geometry
**Action**: hand to M-VIZ / VtkCanvas owner; do NOT close without root-cause + fix.

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
**Track**: M3.0 (DynamicBottomCards) OR a deliberate layered display that needs visual differentiation
**Status**: Open
**Evidence**: A horizontal banner at y≈760-790 in the screenshot shows "缺字段 / Missing: case_family" with the same body_text "This simpleFoam case could match..." that's already in the DynamicFramePanel at top. The bottom banner has a small icon at far right edge (similar to the cycle-4 📝 copy button but possibly pre-existing in BottomCards).
**Hypothesis**: DynamicBottomCards (M3.0 era) and DynamicFramePanel (M3.0 era too) both render the same rail's content. This may have been intentional (different visual layers for different scenarios), but for the "single info_gap" case it shows visual duplication.
**Repro**: same URL as B1.
**Action**: read .planning/decisions/2026-05-22_v61_202_workbench_dynamic_guided.md + .planning/decisions/2026-05-22_v61_202_sub_m30_cycle1_decide_state.md to confirm whether dual-display is by design. If yes → propose differentiation rule (e.g., bottom cards only render secondary/non-primary problems). If no → file as bug.

### B4 · Left sidebar (~265px wide) has dead vertical space below tree

**Severity**: P3 (real estate waste · not breaking · low priority)
**Track**: V4 shell layout / overall workbench information architecture
**Status**: Open
**Evidence**: Left sidebar shows case tree (案例树 LIVE · 搜索 · R-042 · 几何 · 零件 17 · 修复 2 · 包裹 1 · 区域 5 · 网格 · 物理模型 · 工况与求解 · 结果) but the bottom ~60% of the sidebar is empty.
**Hypothesis**: Sidebar height = full viewport but content collapses. Could host a minimap, recent activities, or thumbnails.
**Repro**: same URL as B1.
**Action**: defer until M3.4+ unless V4 shell owner picks it up. Not blocking.

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
