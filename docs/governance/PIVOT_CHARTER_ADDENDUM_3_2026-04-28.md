# Pivot Charter Addendum 3 · CAE-Workbench Interaction Pivot

**Status**: Active (2026-04-28 · Kogami APPROVE_WITH_COMMENTS · 4 findings addressed inline · CFDJerry explicit ratification 2026-04-28 · DEC-V61-093 Accepted)
**Effective**: 2026-04-28 — operative for all subsequent milestones (M-VIZ → M-RENDER-API → M-PANELS → M-AI-COPILOT → M7-redefined → M8-redefined)
**Authority**: 首席架构官 (CFDJerry) · drafted by Claude Code Opus 4.7 (1M context) under his direction
**Notion SSOT**:
- Sub-page under Pivot Charter (canonical): https://www.notion.so/350c68942bed814aa314e9e2b39d7d67
- Standalone copy (searchability):           https://www.notion.so/350c68942bed81a6a20cc935ed20a10b
- Ratifying DEC in Decisions DB:             https://www.notion.so/350c68942bed818dae03c0a9bf64b49c

---

## §0 这个文件的定位

Pivot Charter 主体的 SSOT 在 Notion（Pivot Charter 2026-04-22 + Addendum 1 user-as-first-customer + Addendum 2 reserved/Path-B）。本文件是 repo 侧的**Addendum 3 局部权威**——承载产品交互范式 (Engineer-in-the-loop CAE workbench) 的工程执行约束，因为这一条直接决定后续所有 milestone 的 UI 设计、前端架构选择、后端渲染端点边界。

本文件与 Notion 冲突时：
- 对 §3 (产品交互范式硬约束) 与 §4 (新增 milestones) → 以本文件为准（工程执行面）
- 对 §1-§2 (愿景、与 Pivot Charter 主体的关系) → 以 Notion 为准

任何对 §3-§4 的修订都必须在 Notion Charter Addendum 3 同步追加 "repo-side pointer" 链接到本文件最新 commit。

---

## §1 触发原因

2026-04-28，M5.1 Accepted 当日，CFDJerry 在尝试 M5.0 manual UI dogfood 时给出关键 UX 批评：

> "我要我的工作台能对标 ANSYS，我能清楚的执行每个功能步骤，能实时看到主区域渲染出来的 CAD/网格/仿真云图等等，可以平移/旋转/放大视角，只是我借助这套系统，可以提供几乎所有步骤的自动化方案。然而，能自动化不意味着系统就管自己一路走到底，最后给个报告让用户确认，而是应该让用户能够像操作 ANSYS Fluent 一样，控制每个操作细节，只是很多操作细节已经被我们的项目自动化训练过了，可以点击'AI 处理'，执行自动化设置、操作、让主区域内容更新，但是不自动跳转下一步，而是要工程师点击'下一步'。"

调查确认（DEC-V61-092 修复 nav-discoverability 后的 UI 状态）：

- 当前 ImportPage / EditCasePage / MeshWizardPage / WizardRunPage 是离散的 SSE-wizard 路由，无 3D 视口，无 step-tree，无每步 AI 显式按钮。
- 当前交互范式 = "agentic-wizard"：上传 → 后端 scaffold → 编辑 YAML → 跑 wizard → 看结果，AI 隐式驱动，工程师被动。
- 这与"工程师驾驶 + AI 副驾驶"的工业 CAE 软件标准范式（ANSYS Fluent / Simcenter / OpenFOAM-GUI / Helyx）不兼容。

**这不是 nav-discoverability 修复（DEC-V61-092 已闭）能解决的问题。** 这是产品定义级别的转向。

---

## §2 与 Pivot Charter 主体的关系

Addendum 3 是对 Pivot Charter 主体（2026-04-22）+ Addendum 1（2026-04-26 user-as-first-customer）的**补充**，不是替换：

| 仍然有效（不受 Addendum 3 影响） | Addendum 3 改变的 |
|---|---|
| Pivot Charter §4.3a 冻结语义（10 case Whitelist + 5 reserved slot） | 产品对外的交互范式叙事 |
| Addendum 1 imported-case PASS_WITH_DISCLAIMER 上限（V61-091 已落） | 当前 SSE-wizard 前端架构 |
| Addendum 2 Path-B 紧急回退（保留未触发） | 当前 ImportPage / EditCasePage 等离散路由的 UX 角色 |
| ADR-001 四面 import 方向 | M7 / M8 的当前定义（重定位，见 §4） |
| DEC-V61-087 v6.2 三层治理 | — |
| DEC-V61-089 两轨不变量 (Track A/B) | — |
| RETRO-V61-001 风险触发器 | — |
| Path A 招募绑定门槛 | — |

后端服务（gmsh / FoamAgent / TrustGate / KnowledgeDB / 验证管线）**全部保留并复用**。Addendum 3 改的是**前端壳层 + 新增渲染端点**，不动 trust-core / line-A / 验证内核。

---

## §3 产品交互范式硬约束（载入式）

CFDJerry 在 2026-04-28 的三点确认（"全 yes"）作为本约束的来源：

### (a) 3D 视口是产品中心（HARD YES）

- 主工作区域必须有可平移 / 旋转 / 缩放的 3D 视口
- 视口必须能渲染：(1) 导入的 CAD 几何（STL 三角面片）、(2) 生成的 polyMesh（线框 + 表面）、(3) 仿真结果场（标量云图 / 矢量箭头 / 流线，至少标量云图作为 MVP）
- JSON 卡片 / YAML 编辑器**降级为辅助面板**，不再是任何步骤的中心
- 视口在所有步骤（Geometry / Mesh / Setup / Solve / Results）都常驻；步骤切换更新视口内容，不重建容器

### (b) 工程师驾驶 + AI 每步副驾驶（HARD YES）

- 每个步骤是独立 panel，用户**主动**进入 / 退出 / 重做
- 每个 panel 提供两种操作模式：
  1. **手动模式**：用户填写参数 / 选择 BC / 调整 mesh 尺寸 — 全控制权，与传统 CAE 软件等价
  2. **AI 处理模式**：用户点 `[AI 处理]` 按钮 → 系统执行该步骤的自动化（已训练好的逻辑） → 视口内容更新、参数面板回填 → **不自动跳转下一步**
- "下一步"是**用户显式动作**：每个 panel 底部 `[下一步 →]` 按钮，门控在"当前步骤已提交"（例：mesh 步骤要求 polyMesh 存在 + 网格质量检查通过）
- "上一步"始终可用，回退时已做的工作 (mesh / setup) 保留，不丢失
- **严禁**：autopilot 一键跑完整个流程然后给报告。autopilot 即使技术上可行，UI 必须不暴露这种入口。

### (c) ANSYS Fluent 5 步框架作为模板（HARD YES）

工作流锚定为 5 步，对标 Fluent Workbench：

| 步骤 | Fluent 等价 | 我们的 MVP 实现 | AI 处理能力 |
|---|---|---|---|
| **1. Geometry** | DesignModeler / SpaceClaim 导入 | STL upload + 几何检查 + 视口渲染 | AI: 单位猜测 / patch 命名建议 |
| **2. Mesh** | Meshing 模块 | gmsh 自动六面体/四面体 + 视口预览 + 质量检查 | AI: 网格尺寸推荐（基于 bbox + 雷诺数） |
| **3. Setup** | Cell Zone Conditions / Boundary Conditions / Models | 物理模型 + BC + 材料 panel | AI: 推荐求解器 / 推荐 BC 类型（基于几何 + 流型） |
| **4. Solution** | Run Calculation | FoamAgentExecutor 调用 + 实时残差曲线 | AI: 推荐 URF / 推荐迭代步数 |
| **5. Results** | Reports / Plots / Contours | 视口云图 + 关键量提取 + Trust-Gate verdict 卡片 | AI: 异常识别 / 验收建议（基于 case_profile） |

每步可独立反复迭代（"重新跑 mesh" / "改 BC 重新 solve"），不强制线性单向。

### (d) 严禁的实现走向

1. **AI 一键自动化整流**：不允许实现一个 "/auto-run" 按钮跑完整 5 步并自动 commit。
2. **隐藏的 AI 行为**：用户没点 `[AI 处理]` 时，UI 不能在背后自动调用 AI（除了显示已选项的智能提示，提示 ≠ 操作）。
3. **JSON / YAML 作为主交互面**：YAML 编辑器允许保留作为 power-user advanced panel，但不能是默认或主路径。
4. **wizard SSE 自动跳路由**：当前 wizard.SSE 的"自动跑 mock solver 然后跳报告"必须重塑为"显示进度 + 用户点'查看结果'才进入下一 panel"。

---

## §4 Roadmap 影响 · 新 milestones + 旧 milestones 重定位

### (a) 新增 4 个前端 + 端点 milestones（先于 M7/M8）

| Milestone | 范围 | 依赖 | 估期 | Path A 门槛 |
|---|---|---|---|---|
| **M-VIZ** · 3D 视口基建 | vtk.js 或 three.js 选型 + 嵌入 + camera control + STL/glTF 加载 | none — 第一个动 | 2-3 weeks | independent |
| **M-RENDER-API** · 后端渲染端点 | `/api/cases/<id>/geometry/render` (STL→glTF) · `/api/cases/<id>/mesh/render` (polyMesh→线框 glTF) · `/api/cases/<id>/results/<run>/field/<name>` (采样标量场) | M-VIZ 的输入格式定义 | 1-2 weeks | independent |
| **M-PANELS** · Step-Tree + Task-Panel 架构 | 5-step 左侧树 + 中间视口 + 右侧 task-panel + bottom 状态栏 三栏 layout · `[AI 处理]` / `[下一步]` / `[上一步]` 三按钮契约 | M-VIZ + M-RENDER-API | 2-3 weeks | independent |
| **M-AI-COPILOT** · 每步 AI 钮 wire-up | 把现有自动化（gmsh 推荐尺寸 / scaffold 默认值 / FoamAgent 默认参数）包装成每步的 `[AI 处理]` 端点 + UI hookup | M-PANELS | 1-2 weeks | independent |

### (b) 旧 milestones 重定位

| 旧定义（pre-Addendum-3） | 新定义（post-Addendum-3） |
|---|---|
| **M7** · production wire-up · imported-case run path | **M7** · Setup + Solve panel 接通 imported case 到 FoamAgentExecutor + V61-091 cap 自动激活（保持 Path-A 招募门槛） |
| **M8** · stranger dogfood | **M8** · stranger dogfood **on the new step-panel UI**（保持 Path-A 招募门槛 — 陌生人体验的是 Addendum 3 后的 UI，不是 SSE wizard） |
| **M5.0/M5.1/M6.0/M6.1**（已 Accepted） | **保持已 Accepted** · 它们的后端能力直接被 M-PANELS 各步消费，无需重做 |

### (c) 实施顺序约束（HARD ORDERING）

1. M-VIZ 先 — 没有视口，其他都是空架子
2. M-RENDER-API 紧随 — 视口需要数据
3. M-PANELS — 三栏 shell + 5 步框架
4. M-AI-COPILOT — 把现有自动化按"每步 opt-in"重新接入
5. M7（重定位后）— Setup + Solve panel 真正能跑
6. M8（重定位后）— 邀请陌生人验证整套

跳步会失败：例如不先做 M-VIZ 而直接做 M-PANELS = 三栏 shell 中间空白。

---

## §5 治理影响

### Codex 触发（per RETRO-V61-001）
- 本文档（charter-level docs）不直接触发 Codex（CLASS-1 docs-only 路径，跟 V61-086 / V61-089 一致）
- §4 列出的每个新 milestone 在实现时**全部**触发 Codex（多文件前端 + UX 改动 + 用户批评后的实现）

### Kogami 触发（per DEC-V61-087 §4 + project CLAUDE.md）
- 本 Addendum 是产品叙事级 pivot — 介于 "高风险 PR" 和 "autonomous_governance rule change" 之间
- **Kogami 必须触发**：理由是它改变了"v6.2 三层治理在 governing 什么" — 产品交互范式是 governance 的对象之一
- Kogami 输入 = DEC-V61-093 + 本 Addendum 文档 + intent_summary + merge_risk_summary

### CFDJerry ratification
- **必须**·pre-merge gate · STOP point

### Counter 影响
- DEC-V61-093（ratifying this Addendum）：autonomous_governance: true → counter 57 → 58
- Kogami review 不计数（per V61-087 §5 truth table）

### 与 §11.1 Workbench feature freeze 的关系
- §11.1 freeze 路径是 `ui/frontend/src/pages/workbench/*` 和 `ui/backend/services/workbench_*`
- M-PANELS 必然触及 `ui/frontend/src/pages/workbench/*`（重塑 ImportPage / EditCasePage 等）
- 选项一：在 M-PANELS 实施 DEC 中显式声明 `BREAK_FREEZE: <rationale referencing Addendum 3 §3>` 走 escape clause
- 选项二：等到 §11.1 freeze 自动失效（2026-05-19，dogfood window 结束 = 21 天后）再开始 M-PANELS — 但这与 Path A 招募节奏不兼容
- **本 Addendum 推荐选项一**：每个触及 freeze 路径的 PR 显式 BREAK_FREEZE，理由统一指向 Addendum 3 §3 硬约束

---

## §6 不可逆与可逆性

### 可逆部分
- §4 的 milestone 定义、估期、顺序：可在 M-VIZ 启动后基于实际进度调整
- §3.c 的 5-步框架内部细节（每步的 AI 处理具体能力）：可在每个 milestone 实施时演进

### 不可逆部分（一旦 Addendum 3 Accepted）
- §3.a/b/c 三条 HARD YES 约束：要修订必须开新 Addendum 4 + Kogami + CFDJerry ratify
- §3.d 的四条严禁实现走向：同上
- 后端服务复用决策（gmsh / FoamAgent / TrustGate 不重写）：同上

---

## §7 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v1.0-draft | 2026-04-28 | Claude Code Opus 4.7 + CFDJerry "全 yes" 三点确认 | 本文件创建（Status=Proposed） |
| v1.0-active | 2026-04-28 | Kogami APPROVE_WITH_COMMENTS · 4 findings addressed inline · CFDJerry ratify | 本文件 Status=Active · 通过 DEC-V61-093 |

---

**相关 Governance 文件**：
- `docs/governance/PIVOT_CHARTER_2026_04_22.md` — Pivot Charter 主体 §4.3a fragment
- `.planning/decisions/2026-04-28_v61_093_addendum_3_cae_workbench_pivot.md` — 本 Addendum 的 ratifying DEC
- `.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md` — Path A 招募绑定（Addendum 3 不解除门槛，但提升达门槛后的演示话语权）
- `.planning/decisions/2026-04-28_v61_091_m5_1_imported_case_verdict_cap.md` — V61-091 cap 在 Addendum 3 下继续生效，被 M7（重定位）激活
- `.planning/decisions/2026-04-28_v61_089_two_track_invariant.md` — Track A/B 两轨不变量保留
