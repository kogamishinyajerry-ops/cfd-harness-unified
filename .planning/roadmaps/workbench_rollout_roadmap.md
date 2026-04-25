---
type: roadmap
id: ROADMAP-workbench-rollout
title: Industrial CFD Workbench · 6-Stage Signal-Driven Rollout
status: ACTIVE
created: 2026-04-25
authority: |
  Codex GPT-5.4 (xhigh) industrial-workbench 5-persona meeting
  2026-04-25 (transcript: reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md).
  User authoritative direction 2026-04-25:
    "如何把这个项目打造成一款工业级的 CFD workbench？让一名刚接触
     系统的新手 CFD 工程师，也能像使用 ANSYS 或 STAR-CCM+ 一样：
     每个步骤有清晰的指引、交互、对应部件与产物的渲染显示。文字
     不能过重，可视化、几何渲染、模型渲染、数据标注一定要专业且显眼。"
related:
  - reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md
  - .planning/roadmaps/post_w5_roadmap.md  # line A companion (different scope)
no_calendar_in_triggers: true  # Per Phase 6 governance lock-in: every trigger here is event/signal-based.
---

# Industrial CFD Workbench · 6-Stage Rollout

> **Calendar dates appear ONLY in `created` field, never in stage triggers.** Triggers fire when conditions naturally arise — fast if push rate is fast, slow if not. Trigger never firing = correct behavior, not a failure.

## Posture (David verdict, locked-in)

> 工业级目标可达 **68%**。底子强在 10 case + gold-overlay + PDF 链路；短板是几何/网格/BC schema 缺位。`LearnCaseDetailPage` 3294 LOC 不重写，**先拆**。`/learn` 与 `/pro` 双轨**保留**：前者前门，后者批量与证据。**最糟反模式**："把报告页伪装成工作台"。

## 工业级 ≠ ANSYS-style 3D viewport (key insight)

Kai 的 bundle-size 数字（vtk.js 30.3 MB · three.js 37.0 MB · @react-three/fiber 2.17 MB + bundles three · trame-vtk 1.64 MB + WebSocket 长连接冷启动）证明：**当前 workbench 用手写 SVG + 后端 PNG 在用户体验维度实际胜出**（每个 primitive 6-12 KB · 无冷启动 · 无重型依赖）。

工业级的标志不是 3D viewport — 而是：
- **每步有清晰的视觉/数据完成信号**（不是文字"完成了"）
- **每个 primitive 是 dashboard 级专业 dataviz**（color-semantic + data-ink ratio 最大）
- **progressive disclosure**（新手浅、专家深，不是 modal hell / tab hell）
- **guided 但 skippable**（引导默认 3 步，可跳过且记住）

## Sarah 12-step user journey (target experience)

| Step | viz primitive | 完成信号 | ANSYS Fluent 类比 |
|---|---|---|---|
| 1. 选案 | case matrix | 10 case 状态一眼分层 | Launcher |
| 2. 看几何 | topology SVG | 区域 / 入口 / 出口 / 壁面全点亮 | Display |
| 3. 设物性 | property strip | rho/mu/T 全绿 | Materials |
| 4. 设边界 | BC pin-map | 每个 patch 有 type/value/unit | Boundary Conditions |
| 5. 选模型 | model ladder | solver / 湍流 / 稳态 锁定 | Models |
| 6. 看网格 | mesh ladder | 4 档密度可切 | Mesh Display |
| 7. 查质量 | QC band | skew / non-orth / y+ 红黄绿 | Mesh Metrics |
| 8. 跑基线 | checkpoint rail | preflight 5/5 pass | Initialize + Run |
| 9. 盯收敛 | residual SVG | 下降 / 平台 / 异常点可见 | Residual Monitor |
| 10. 对 gold | overlay SVG | 容差带 + 偏差点可见 | XY Plot |
| 11. 批量扫 | batch matrix | ≥4 runs 热图完成 | Parametric Study |
| 12. 出报告 | export panel | PDF + xlsx 双绿 | Reports |

## 5 核心可视化 primitive (技术方案)

| Primitive | 库选型 | 关键能力 | 当前 stack 距离 | bundle | 依赖 |
|---|---|---|---|---|---|
| **CaseFrame** | 手写 SVG + Tailwind | 几何 / patch / BC 一屏 | 远 | 6-10 KB | 新 basics endpoint |
| **MeshQC** | SVG bars | skew / non-orth / y+ / GCI | 中 | 4-8 KB | 新 mesh-metrics endpoint |
| **ContractOverlay** | SVG + 后端 PNG | gold vs run + tol band | 近 | 8-12 KB | 现有 context / renders |
| **RunRail** | SVG + react-query | checkpoint / residual / live 状态 | 中 | 5-9 KB | 现有 stream / checkpoints |
| **BatchMatrix** | SVG heatmap | 多 run 对比 / export | 中偏远 | 6-12 KB | 新 aggregate + xlsx endpoint |

**总 bundle delta: ~30-50 KB**（vs vtk.js 30 MB）。

## Stages

### Stage 1 · 壳层拆分 ✅ LANDED (commit 7537049)

- **Trigger**: `LOC>2500 && tabs=5` (满足: 3294 LOC × 5 tabs)
- **Scope**: 拆 `LearnCaseDetailPage.tsx` 3294 → 197 LOC + 8 模块 (`./case_detail/{StoryTab, CompareTab, MeshTab, RunTab, AdvancedTab, ScientificComparisonReport, constants, shared}`)
- **Predecessor**: 无
- **Risk**: 路由碎裂 / 跨文件 type 引用断链 (验证: tsc 0 错 + vite build 通过 + live HTTP 200)
- **Maturity impact**: +0.02 (壳层准备就绪 · 后续每个 viz primitive 改动只摸单文件)

### Stage 2 · CaseFrame 首屏 ✅ CLOSED (commits e34f4b4 + 7921fa0 + c884aad, 2026-04-25)

- **Trigger (start)**: ✅ MET — Stage 1 落地 + LDC 通过 endpoint (commit e34f4b4)
- **MVP scope** (delivered): `/api/cases/{id}/workbench-basics` FastAPI route + Pydantic schema + 5 SVG renderers in `<CaseFrame>` (rectangle / step / airfoil / cylinder + UnsupportedShapeStub fallback)
- **Trigger (close)**: ✅ EXCEEDED — 10/10 cases authored as of commit 8b3ad33 (LDC, plane_channel, flat_plate, DHC, RBC, BFS, NACA0012, cylinder, duct_flow, impinging_jet). 5 shape renderers cover the full whitelist (rectangle / step / airfoil / cylinder / jet_impingement); UnsupportedShapeStub retained for future case admissions.
- **主交付 viz** (delivered): topology SVG (4 shape renderers, role-coded patch edges, driver arrows, vortex/recirc hints) + 物理锚点 panel (Re prominent + derived) + BC pin-map table + materials/solver strip + terse hints row
- **Predecessor**: Stage 1
- **Risk** (resolved): schema drift surfaces as soft amber banner via `validate_patch_consistency()`, never 500s. Aspect ratio clamped to [0.25, 5] for legibility on long/thin geometries.
- **Anti-pattern guard observed**: hints intentionally terse (3 captions × 1 line); long-form prose stays in StoryTab. Honesty hints surface known gaps (e.g., plane_channel laminar-vs-DNS contract incompatibility, RBC-vs-classical-textbook side-vs-bottom heating divergence).

### Stage 3 · MeshTrust QC band

- **Trigger (start)**: Stage 2 close 满足 (≥8 case basics) **AND** `mesh-metrics` endpoint 返回 skew / non-orthogonality / y+ / GCI 至少 1 case
- **MVP scope**: `/api/cases/{id}/mesh-metrics` 后端 endpoint + `<MeshQC>` 前端 SVG bars (4 档 mesh 密度切换 · 每个 metric 独立条 · 红/黄/绿三态)
- **Trigger (close)**: `4 档 mesh 数据 ≥8 case` (8 case 有完整 mesh sweep + QC metrics)
- **主交付 viz**: QC band (3-tier color-semantic) + mesh ladder selector + 单 metric 详情 popover
- **Predecessor**: Stage 2
- **Risk**: "假安全感" — metrics 全绿但物理仍错 (Codex/Lin disagreement: 必须配合 contract_status panel 解释 "metric pass ≠ physics pass")
- **Anti-pattern**: 把网格 metrics 搞成"网格质量证书"伪装

### Stage 4 · GuardedRun · checkpoint rail + first-visit tour

- **Trigger (start)**: Stage 3 close 满足 **AND** preflight 事件分类清单 ≥5 类 (e.g., fluid_props_unset, BC_unmatched, schema_invalid, mesh_zero_cells, solver_unsupported)
- **MVP scope**: `<RunRail>` checkpoint visualization (5+ preflight 检查项 · 每项 pass/fail/skip 三态 · 失败展开 evidence) + first-visit guided tour (默认 3 步 · 可跳过 + 记住 · checkpoint fail 再唤起)
- **Trigger (close)**: `preflight 事件 ≥5 类` (实际累计 5 种以上不同 preflight 失败被捕捉到 + 解决方案 documented)
- **主交付 viz**: run rail (vertical timeline of checkpoints) + tour overlay + residual SVG live update
- **Predecessor**: Stage 3
- **Risk**: 打扰感 (Lin/Sarah disagreement resolution: 默认 3 步可跳 · 仅在 fail 时再唤起)
- **Anti-pattern**: tour 步数多到把 surface 占满 / tour 不能 dismiss

### Stage 5 · GoldOps · overlay + batch matrix

- **Trigger (start)**: Stage 4 close 满足 **AND** 现有 3 个 anchor case (LDC + BFS + cylinder_wake) 的 ContractOverlay 完整率 = 100% (即每个 anchor case 都能在一屏内同时看到 gold 曲线 + run 曲线 + tol band + per-point deviation marker)
- **MVP scope**: ContractOverlay 升级 (现有 8-section iframe 报告 → 集成进 CompareTab 主屏 + 新增 BatchMatrix heatmap (多 run × 多 case 一屏对比))
- **Trigger (close)**: `3 anchor case compare 完整率=100%` (LDC + BFS + cylinder 全维 dimension overlay 渲染就绪)
- **主交付 viz**: ContractOverlay (3-band gradient + per-point markers) + BatchMatrix (heatmap) + per-cell drill-in popover
- **Predecessor**: Stage 4
- **Risk**: 信息过载 (Maya/David disagreement resolution: Story-tab 常显仅 3 张风险卡 · 详情进 expand)
- **Anti-pattern**: 把 BatchMatrix 搞成 spreadsheet (失去 viz 优势)

### Stage 6 · ExportPack · PDF + xlsx 双绿

- **Trigger (start)**: Stage 5 close 满足 **AND** xlsx 序列化 schema 定稿 (字段映射 ≥30 行 · 含 metric / dimension / verdict / commit_sha / gold ref)
- **MVP scope**: `/api/cases/{id}/runs/{label}/export.xlsx` 后端 endpoint + `<ExportPanel>` 前端组件 (PDF (现有) + xlsx (新) 双绿状态卡 + 单击下载) + manifest 记录 (export 何时生成 / 由谁 / 含哪些 dimension)
- **Trigger (close)**: `batch rows ≥30 && 字段齐套=100%` (累计 ≥30 个 export 实际产生 + 字段无缺失)
- **主交付 viz**: export panel (双格式状态卡) + manifest table (audit trail)
- **Predecessor**: Stage 5
- **Risk**: 证据不一致 (PDF 显示 ≠ xlsx 显示 · 数据来源不同) — 必须强制 single-source-of-truth 序列化
- **Anti-pattern**: xlsx 只是 PDF 截图截图 / xlsx 字段命名与 PDF 不一致

## NOT-IN-ROADMAP (event-triggered, 不进 stage 顺序)

- **3D 几何 viewer (vtk.js / three.js)**: 显式 REJECTED in this rollout (Codex bundle 数字 + Sarah / Kai disagreement resolution)。如某 case 出现需要 streamline / iso-surface 的科学问题，单独 RFC，不进 stage
- **trame backend WebSocket**: 显式 REJECTED (启动慢 + 长连接 ops 复杂)
- **/learn vs /pro 合并**: David 显式说**保留双轨**——前门 vs 证据面，不合并
- **ANSYS / STAR-CCM+ 案例 import**: 当前不在 scope (10 case OpenFOAM benchmark 自给自足)
- **multi-physics (heat + flow + structural)**: post-Stage-6 evaluation, may never come

## 反模式 (David 警告)

最关键的一个：**"把报告页伪装成工作台"**。表现：

- 在已有的 8-section 验证报告上加一个 "运行" 按钮就声称是 workbench
- CompareTab 的 iframe 嵌一个修改器面板，假装可编辑
- /pro dashboard 用 "工作流" 标题但实际只是 link list

**Stage 2-6 必须 surface 真实可交互的 viz primitive，不是文字 + 链接**。每个 stage 的 trigger 显式要求 viz primitive 能渲染 (e.g., S2 trigger 要求 ≥8 case 有 basics endpoint 数据 → CaseFrame SVG 真能渲染 ≥8 case 几何)。

## Codex disagreement resolutions (lock-in)

| 争议 | Resolution |
|---|---|
| **Maya 极简 vs David 怕物理错** | Story 常显仅 3 张风险卡；fvSchemes/fvSolution 错误进 RED checkpoint，可展开证据，不回到长文 |
| **Kai trame 完整 vs Sarah 嫌长连接** | 不上 trame；`/learn` 全 HTTP+PNG/SVG；`/pro/run` 用户**点 Live 才开 SSE** |
| **Lin guided vs Sarah 嫌烦** | guided tour 首访默认 **3 步**；首屏可"跳过并记住"；之后只在 **checkpoint fail 再唤起** |

## Maturity coupling

| Event | 累计 maturity 影响 |
|---|---|
| Stage 1 LANDED (this commit, 7537049) | +0.02 |
| Stage 2 CaseFrame 落地 + ≥8 case basics 渲染 | +0.05 |
| Stage 3 MeshTrust QC band 落地 + ≥8 case 数据 | +0.04 |
| Stage 4 GuardedRun + tour ≥5 类 preflight 覆盖 | +0.05 |
| Stage 5 GoldOps overlay + batch + 3 anchor 完整率 100% | +0.06 |
| Stage 6 ExportPack PDF+xlsx + ≥30 batch rows | +0.04 |
| **6 stage 全部完成** | **target maturity ≈ 0.94** (起点 0.68 + 累计 +0.26) |

未达成 stage = maturity 不增（不强制推进）。Stage trigger 永不满足 = 项目重心已转向其他 surface（合法）。

## 关键非-stage 决策（已锁定）

- **`/learn` 与 `/pro` 双轨**: 保留。前门 vs 证据面分离，不合并。
- **`LearnCaseDetailPage` 3294 LOC**: 拆 (Stage 1 ✅)，不重写。
- **3D viz 库**: 不引入。手写 SVG + 后端 PNG。
- **Calendar deadline**: 永不写。所有 trigger signal-driven。
- **第一周 (post-Stage-1)**: David 钦定的具体一件事 = "`workbench-basics` endpoint + CaseFrame 首屏" (= Stage 2 MVP)
