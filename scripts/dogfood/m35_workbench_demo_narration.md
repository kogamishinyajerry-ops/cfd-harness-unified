# M3.5+M3.6 · CFD 工作台 0→1 全流程演示 · 文字版

> 视频文件 (M3.6 cycle 1 · 真实 CAD): `~/Desktop/cfd_workbench_demo_realcad_2026-05-25.webm` (~5 MB · 72s)
> 视频文件 (M3.5 · 无 CAD seed): `~/Desktop/cfd_workbench_demo_2026-05-25.webm` (4.7 MB · 73s) — 保留对比基线
> 抽样帧 (M3.6 cycle 1):
>   - `~/Desktop/cfd_workbench_demo_realcad_geometry.png` (步 1 · 真实 3D cylinder)
>   - `~/Desktop/cfd_workbench_demo_realcad_boundary.png` (步 4 · BC patches)
>   - `~/Desktop/cfd_workbench_demo_realcad_post.png` (步 6 · 后处理 + 残差曲线)
> 录制脚本: `scripts/dogfood/m35_workbench_demo.mjs`
> 案例 (M3.6): `circular_cylinder_wake` (圆柱绕流经典 CFD 算例 · 7 patches · 真实 cylinder.stl 渲染)
> 录制日期: 2026-05-25
> 视频时长: 72 秒
> 视口: 1440×900 headless chromium + `--use-gl=swiftshader` (软件 WebGL)
>
> 演化路径:
> - M3.5 cycle 1: 初版录制 · overlay 不可见 (IIFE 在 body 不存在时执行)
> - M3.5 cycle 2: `DOMContentLoaded` guard 修复 overlay 注入 · z-index → 2147483647
> - M3.6 cycle 1: 切换 case `m33_ux_demo_seed` → `circular_cylinder_wake`
>   + 加 `--use-gl=swiftshader` 启用软件 WebGL → vtk.js 拿到真 GL context
>   → 中心 viewport 渲染真实 3D cylinder 模型 (case geometry.glb · solver STL transcode)
>
> 本文档与视频配对使用: 视频内已嵌入中文 caption + 红色 cursor; 本文档给出每步的更深解释 + UI/功能/操作三重视角。

## 录制目标

证明 M3.2-M3.4 闭环成果在真实浏览器里全部生效:
- M3.2 cycles 4-7: 📝 copy body_text 按钮 · aria-live toast · Playwright E2E 6+7 dogfood
- M3.3 cycles 1-3: 真人 UX 验证 · A1-A4 视觉 polish · 永久 spot-check 工具 · 跨 step 重定性
- M3.4 cycles 1-5: B1 MainCanvas proxy 修复 · 极致 empty-state polish · B6 wrapper layout cascade-clear

## 演示流程

### 引导 (~3.5s)
- caption 显示: "CFD 工作台 0→1 全流程演示 · M3.2-M3.4 改进总验"
- 鼠标移动到中心 (720,450 · 40 steps 平滑曲线)
- UI 显示: 步骤 1 几何 · case_family 缺字段 rail · 上传 CAD CTA

### 第 1 步 · 几何 (Geometry) · 7s
**操作**: 鼠标先 hover 中心 viewport 区, 再精确移到 `data-testid="v4-mode-geometry-upload-cta"` 按钮上 (commit `bf3d41d` 引入), 然后 hover `dynamic-frame-copy-field-path` 触发点击。**UI 展示**: 中央 viewport 空状态 (无 CAD), 上方醒目「↑ 上传 CAD」CTA, 右栏 case_family 缺字段 rail 显示「待补充」amber 标签, 📋/📝 复制按钮可见。**功能验证**: M3.4 cycle 3 empty-state polish 把"找不到几何"从死状态变成行动入口; M3.2 cycle 5 的 inline aria-live toast「✓ 已复制」在 1.5s 内弹出消失 (role=status, 浏览器原生)。

### 第 2 步 · 网格 (Mesh) · 6s
**操作**: 鼠标先停 viewport 中心, 然后扫过底部 4 列 stats (280→540→800 px), 每列停 700ms。**UI 展示**: 中心 3D viewport 渲染 mesh.glb (vtk.js + WebGL backbone), 底部 4 列质量指标 histogram (偏度/表面质量/单元质量/正交性/长宽比), 右栏「Step 2 · 网格就绪」+ AI 助理 ADVISORY ONLY 标签 · 80% 准备度 · 18.86 万单元。**功能验证**: M3.4 cycle 5 B6 wrapper cascade-clear 修复让 4 列 grid 不再撞栏 — 这是 layout 闭环的关键证据。

### 第 3 步 · 物理 (Physics) · 6s
**操作**: 鼠标依次扫过湍流模型卡片栈 (500,100→500,220→500,340), 每张停 800ms。**UI 展示**: 5 个湍流模型卡片 (SST k-ω 已选 · Spalart-Allmaras · k-ε · Laminar · Energy off), 5 种材料 (空气/钛合金/钢/inconel/隔热层), 底部 stats 5 物理模型 · 5 材料 · 稳态 · 28.6 万估算单元, 右栏 Step 3 物理已设。**功能验证**: 卡片化选择器 + AI advisory rail 协同, AI 不写入, 只 advise (cfd 战略转向 SSOT 兑现)。

### 第 4 步 · 边界 (Boundary) · 6s
**操作**: 鼠标在 3D 模型上扫过 patch label 区 (600,280→800,280→900,380)。**UI 展示**: 中心 3D 模型带 label (入口/出口/壁面/转子域/未识别), BC 表 28 入口 + 27 出口 + 1 热壁面 + 4 转子域 + 9 壁面 + 1 未识别, 右栏 Step 4 边界已设 · 边界数 61 · 覆盖度 98.4% · 应用 AI 建议按钮。**功能验证**: AI advisor 在 BC 识别给出建议但人工点应用才落, 体现 advisory-not-driver 四问门控。

### 第 5 步 · 求解 (Solver) · 5.5s
**操作**: 鼠标横扫从 viewport (700,400) 到右栏配置区 (1000,400), 各停 900ms。**UI 展示**: solver 类型选项 (simpleFoam / pimpleFoam / interFoam) · 时间步 · 迭代次数 · 收敛准则, 监控面板预备槽位 (残差曲线 · 字段采样 · 实时探针 · log tail), 右栏 Step 5 rail 显示启动状态或缺字段提示。**功能验证**: m33_ux_demo_seed 无 solver_results artifact, 所以仅展示配置 UI, 不实际启动。

### 第 6 步 · 后处理 (Post) · 5.5s
**操作**: 鼠标从 viewport (750,450) 扫到工具栏 (1100,450), 各停 900ms。**UI 展示**: ParaView/Trame 远程 viewport 槽位 · 字段切换器 (压力/速度/涡量/温度/湍流量) · 工具按钮 (slice/clip/streamline/contour/探针线/截面绘图) · 报告导出 (图片/VTP/FOAM/Notion 同步)。**功能验证**: Post 步骤的 empty viewport 走 M3.4 cycle 2 PostEmptyViewport pattern, 复用同一 polish 范式。

### 收尾 (~4.5s)
- caption 显示: "演示完成 · M3.2 / M3.3 / M3.4 全部生效"
- 鼠标定格中心 (720,450 · 60 steps 长尾曲线)
- 录制结束 · video promise resolve · `/tmp/cfd_demo_recording/*.webm` 落盘

## 视觉元素说明

| 元素 | 出处 | 说明 |
|---|---|---|
| 底部黑色 caption 框 | M3.5 cycle 1 inject | DOM-level 注入 · z-index 999999 |
| 红色光圆 cursor | 同上 | mousemove listener · 24px radial gradient |
| 顶栏 / 左栏 / 右栏 / 步骤栏 | M3.2-M3.4 V4 shell | 不属于 demo · 都是真实工作台 UI |
| ✓ 已复制 toast | M3.2 cycle 5 inline aria-live | role=status · 1.5s · 浏览器原生 |
| 「上传 CAD」CTA | M3.4 cycle 3 polish | route to /workbench/import · 复用 PostEmptyViewport pattern |
| 主 viewport 完整宽度 | M3.4 cycle 5 fix | w-[300px] 右栏明确宽 · main 恢复 ~860px |

## 怎么看视频

1. 用 macOS QuickLook (空格) 或 VLC 打开 .webm
2. 按 → / ← 快进 / 后退
3. 重点观察:
   - 第 1 步: 上传 CAD 按钮被高亮鼠标 hover
   - 第 1 步末尾: 📋 copy 按钮被点击 → 旁边出现 "✓ 已复制" inline toast
   - 第 2 步: 4 列网格 stats 整齐不撞 (M3.4 cycle 5 cascade-clear B2)
   - 第 4 步: 3D 模型上的 patch label (入口 / 出口 / 壁面 / 转子域)
   - 第 6 步收尾: caption 完整列出 session 成就

## 已知限制

- m33_ux_demo_seed 没有真实 CAD → Geometry 步骤 viewport 是 empty state · 不是真实 3D 模型
- Solver / Post 步骤可能只展示 rail · 无实际 solver 启动 (案例无 solver_results artifact)
- headless 模式录制 · 浏览器 cursor 由 DOM 注入元素模拟 · 不是真实 OS cursor
- 视频包含 chrome devtools-style 元素 (caption + cursor overlay) · 真实工作台无这些
