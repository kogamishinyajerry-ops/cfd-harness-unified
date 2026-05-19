# V4 真 viewport 改造 · M1 数据源地图 (2026-05-19)

## 触发

用户在 KJ66 dogfood 末尾抓到的根本性 finding：

> "这里面全都是 SVG 图，完全不是真实的渲染出的，和蓝图严重不符"

R3-R8 八轮 Codex review 全程没抓到这个 — Codex 在审 test coverage / API contract / canonical legend
order，但**没有审 "Post / Solver / DoE / Physics 模式真的在渲染 case 的几何吗"**。我自己 8 轮里
没有打开过浏览器看实际效果，直接违反 `~/CLAUDE.md` 的硬规：

> "For UI or frontend changes, start the dev server and use the feature in a browser before
> reporting the task as complete. Type checking and test suites verify code correctness, not
> feature correctness."

R6-R8 "99/100 APPROVE" 分数对 **数据流和 API 契约**仍然有效（500 sample 真解析自 KJ66 log）。
但对 **viewport 真实性维度** 不成立 — 应被理解为 "得分仅覆盖审过的维度，没覆盖到的部分作废"。

## 现状 (audit 结果)

| Mode | 真 ViewportV4 | SVG fake | 评级 |
|---|---|---|---|
| Boundary | 5 处 | 2 处 | ✅ 真（参考实现） |
| Mesh | 2 处 | 3 处 | ⚠️ 混 |
| Geometry | 2 处 | 4 处 | ⚠️ 混 |
| **Post** | 0 | 6 处 | ❌ 纯卡通 |
| **Solver** | 0 | 5 处 | ❌ 纯卡通 |
| **DoE** | 0 | 5 处 | ❌ 纯卡通 |
| **Physics** | 0 | 2 处 | ❌ 纯卡通 |
| Import | 0 | 0 | (上传表单 · 正确) |

## 蓝图要求（8 张图重看后归纳）

每张蓝图都是 **真实 3D 渲染** with：

| 蓝图 | 模式 | viewport 主体 |
|---|---|---|
| 1 | overview | APU container 剖切 + 全场速度云图 + 流线 + 半透发动机 |
| 2 | Geometry | APU container 剖切 + 发动机零件按 body 分色 + BC label 引线 |
| 3 | Physics | 半透 APU 外壳 + 内部速度场 multi-color |
| 4 | Mesh | APU container + 蓝色 wireframe overlay |
| 5 | Boundary | APU container + 6 BC 面分别色块 (inlet=blue, outlet=violet, wall=orange) |
| 6 | Solver/Post 收口 | 大流速场 contour + 残差曲线 + 温度曲线 + GPU/CPU 仪表 |
| 7 | Solver mid-run | multi-color contour + 残差曲线 + 出口/入口流量曲线 |
| 8 | DoE | 12 个真实 contour 缩略图矩阵 + Pareto scatter |

**核心反差**：所有蓝图的 viewport 占 ~60% 屏幕面积，都是**真 3D**。我的 SVG 占位用了同样的位置和
比例，但里面是 hand-drawn streamlines + 紫色 box-frame icon — 视觉上能蒙混，**实质零信息密度**。

## 每个 fake 模式的替换需求 (data-source map)

### Post (`ModeRendererPost.tsx:606-609` · 4 fake 组件)

| Fake component | 蓝图意图 | 真实数据源 | Backend 状态 |
|---|---|---|---|
| `IndustrialBoxScene variant="post"` | APU 集装箱剖切外壳 | 复用 geometry.glb (case scope) | ✅ `/api/cases/{id}/geometry/render` 已存在 |
| `ContourBodyOverlay` (SVG path 假装是发动机) | 真发动机几何 with 表面 U 着色 | OpenFOAM U field → cell-colored glb 或 vtkPolyData | ❌ 需新做：`/api/cases/{id}/post/surface.glb?field=U&time=last` |
| `StreamlineField count=60` (hand-drawn SVG curves) | 真流线（积分 vtk streamline filter） | OpenFOAM U field → seed points → vtk integrator | ❌ 需新做：`/api/cases/{id}/post/streamlines.vtp?seeds=...` |
| `VelocityColorbar` (静态 SVG gradient) | 真速度 colormap 配合实际 [Umin, Umax] | OpenFOAM U field → min/max → 自动 colorbar | ❌ 需新做：post payload 里带 `umin/umax` |

**已有可复用资产**：
- `velocity-slice.png` 服务端 PNG 渲染器（z=0 中面 |U|）— 不能直接给 viewport 用但证明数据通路畅通
- `report-bundle` 已能输出 4 张 matplotlib PNG （velocity / pressure / vorticity / centreline）

### Solver (`ModeRendererSolver.tsx:100-107` · 4 fake 组件)

| Fake | 蓝图意图 | 真实数据源 |
|---|---|---|
| `IndustrialBoxScene` | 同 Post · 复用 geometry.glb | ✅ 现成 |
| `StreamlineField count=72 animated` | 求解过程的 live 流线 (每 N 迭代刷新) | ❌ 需新做：定期 sample + 增量推送（SSE 或轮询） |
| `VelocityColorbar` | 实时 U range | ❌ 同上 |

**简化路径**：mid-run 不需要流线动画 — 用最近一帧的 streamlines.vtp 静态展示即可。"live" 来自残差
曲线/KPI 已经实时，主 viewport 静态 OK。

### Physics (`ModeRendererPhysics.tsx:35` · 1 fake)

| Fake | 蓝图意图 | 真实数据源 |
|---|---|---|
| `IndustrialBoxScene variant="physics"` | 半透 APU 外壳 + 内部速度多色 volume | geometry.glb + post/surface.glb (复用 Post 资产) |

**最简模式**：基本是 Post 的子集（不要 streamlines · 主体几何半透 · BC 平面用 outline）。

### DoE (`ModeRendererDoe.tsx:60-62` · 缩略图矩阵)

| Fake | 蓝图意图 | 真实数据源 |
|---|---|---|
| `IndustrialBoxScene variant="solver"` × N | 每个 DoE 样点的真 contour 缩略图 | per-case `/api/cases/{id}/post/thumbnail.png?size=160` |

**关键决定**：DoE thumbnail 用 **server-side PNG 缩略图缓存**（每个 case 一张 160px PNG）远比
mount 12 个 vtk kernel 高效。复用现有 `report-bundle` 的 matplotlib 渲染器即可，缩小输出尺寸。

## 工程路径（按 ROI 排序）

| 优先级 | Task | 工程量 | 数据通路 |
|---|---|---|---|
| **A1** | DoE thumbnail PNG endpoint + UI 接 img src | 0.3 session | 改 report_bundle 加 thumbnail mode |
| **A2** | Physics: geometry.glb + 半透 shader | 0.3 session | 现成 endpoint · 改 ViewportV4 加 opacity |
| **B1** | Solver: geometry.glb + 静态 last-frame streamlines.vtp | 0.7 session | 需新做 streamlines exporter |
| **B2** | Post: surface.glb (U-colored) + streamlines.vtp + colorbar | 1.0 session | 双 endpoint · vtk.js mapper 切换 |
| **C1** | M6 visual smoke in browser on real KJ66 case | 0.2 session | 已下载 KJ66 case · 跑 foamToVTK 拿数据 |

**总估**: ~2.5 session（与之前承诺的 2-3 session 一致）

## B2.5 收尾状态（Codex R0 · 2026-05-19）

- Status: done: this commit
- Browser evidence: `http://localhost:5181/workbench/case/imported_2026-05-19T01-15-19Z_69bed2d0?step=post`
- Fixed: VTP surface actor now renders from the mutated polyData with active `magU`; streamlines render as vtk.js TubeFilter tubes; VTP actor bounds drive the post-load camera fit; the colorbar range ignores degenerate no-slip wall ranges and uses the non-degenerate streamline U range.
- Evidence screenshots: `/tmp/cfd_b25_after_patch2.png` (post viewport) and `/tmp/cfd_b25_after_rotate.png` (camera-drag rotation).
- Source-data caveat: current `engine.vtp` has `U` magnitude `0..0` because it is a no-slip wall patch, so the hull renders blue rather than a blue-to-red hull gradient. Current `streamlines.vtp` contains 7 line cells, not 8; changing either requires backend/case data work, which was outside this B2.5 R0 boundary.

## 工程做法决策点（先和用户对齐再动手）

### D1 · vtk.js 流线渲染 vs. 服务器端 PNG over geometry

| 路径 | 优点 | 缺点 |
|---|---|---|
| 全 vtk.js（客户端 streamline tube actor） | 真互动、可旋转、可改 seeds | 需要新 attachVtp() 路径 · vtk.js bundle 已经 35MB |
| 服务器 PNG 叠 geometry glb | 复用 report_bundle 已工作的 matplotlib | 失去 3D 互动 · 蓝图明显是 3D 风格 |
| **混合**：glb 表面用 U 着色 (静态3D) · streamlines 作为 vtkPolyData 加载 | 真 3D 互动 + 实数据 + 复用现成 OpenFOAM 字段 | 最大工程量 |

**默认建议**：混合方案（B2 路径），蓝图视觉风格强烈倾向真 3D。

### D2 · 一次性全做 vs. 增量 ship

- **一次性**：所有 4 个 fake 替换好再让用户看。风险=2.5 session 没东西看。
- **增量**：A1+A2 先 ship（0.6 session），让用户先看到部分蓝图达标。然后 B1，最后 B2。每次都过 M6 browser smoke。

**建议**：增量。理由：(a) M1 audit 已经证明我闭门看代码不可靠，需要尽早把可视成果给用户看 (b)
KJ66 dogfood 已经有真实 OpenFOAM 输出，可作每步 browser smoke 的素材。
