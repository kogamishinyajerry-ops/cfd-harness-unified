# cfd-harness-unified 项目演化史

> 一个AI-CFD工作台从"自以为对"到"经得起审查"的完整历程
>
> 作者：项目历史探索者 Agent Team
> 日期：2026-04-27
> 状态：第一稿（持续更新中）

---

## 序章：一个尴尬的事实

2026年4月，一个用AI写CFD（计算流体力学）代码的开发者发现了一个令人不安的现象：

他的代码在自测时通过率是**80%**，但经过独立的AI审查工具Codex的第一次审查后，通过率是——**0%**。

这个项目就是**cfd-harness-unified**。

---

## 第一部分：起源（2026年4月13日）

### 黎明

2026年4月13日凌晨1点28分，一个新的Git提交被推送到了仓库：

```
commit 327562c
Author: JerryKogami
Date:   Mon Apr 13 01:28:42 2026 +0800

feat(cfd-harness): Phase 0 complete — unified AI-CFD knowledge compiler
```

这是cfd-harness-unified项目的第一个commit。

### 项目愿景

根据最初的`PROJECT.md`，这个项目的核心意图是：

> 统一知识治理层 + Foam-Agent 执行引擎，建立个人 CFD 知识图谱。

项目的架构流程非常清晰：

```
Notion TaskSpec
    ↓
task_runner.py（编排器）
    ├── knowledge_db.py（加载 Gold Standard + CorrectionSpec）
    ├── foam_agent_adapter.py（调用 CFDExecutor Protocol）
    │       ├── MockExecutor（测试用）
    │       └── FoamAgentExecutor（占位符）
    ├── result_comparator.py（结果 vs Gold Standard）
    └── correction_recorder.py（偏差 → CorrectionSpec）
    ↓
回写结果摘要到 Notion
```

### Phase 0的遗产

Phase 0建立了这个项目的六大核心组件：

| 组件 | 作用 |
|------|------|
| `models.py` | 数据模型定义 |
| `knowledge_db.py` | 黄金标准知识库 |
| `foam_agent_adapter.py` | CFD执行引擎适配器 |
| `result_comparator.py` | 结果比对器 |
| `correction_recorder.py` | 偏差记录器 |
| `task_runner.py` | 任务编排器 |

Phase 0带来了**87个测试，覆盖率97.71%**。

### 约束与边界

从第一天起，项目就明确了"不做什么"：

- **不做**：不自建NL→OpenFOAM生成能力（Foam-Agent已覆盖）
- **不做**：不自建求解器
- **不做**：不管理OpenFOAM安装

这是一个**集成者**的角色，而非**构建者**。

---

## 第二部分：黄金标准体系建立（2026年4月14-19日）

### 知识库结构

项目建立了完整的知识库体系：

```
knowledge/
├── whitelist.yaml          # 冷启动白名单：10条经典验证案例
├── gold_standards/         # 每个案例的黄金标准数据
│   ├── lid_driven_cavity.yaml
│   ├── backward_facing_step.yaml
│   ├── circular_cylinder_wake.yaml
│   └── ...
├── corrections/            # 165个偏差修正记录
├── attestor_thresholds.yaml # 验收阈值配置
└── workbench_basics/       # 工作台基础知识
```

### 10个经典基准案例

根据`whitelist.yaml`，项目覆盖了10个经典CFD案例：

| 案例 | 类型 | 湍流模型 | 参考文献 |
|------|------|----------|----------|
| Lid-Driven Cavity | 内部/稳态 | 层流 | Ghia 1982 |
| Backward-Facing Step | 内部/稳态 | k-epsilon | Driver & Seegmiller 1985 |
| Circular Cylinder Wake | 外部/瞬态 | k-omega SST | Williamson 1996 |
| ... | ... | ... | ... |

### 物理契约的诞生

每个黄金标准都包含一个**物理契约**（Physics Contract）：

```yaml
physics_contract:
  - observable: "u_centerline"
    ref_value: 0.8412  # from Ghia 1982
    tolerance: 0.05    # ±5%
    precondition: "mesh resolution Y+ < 1"
```

这不仅仅是一个数字，而是一整套验证逻辑：
- 前置条件（mesh resolution Y+ < 1）
- 参考值（来自权威文献）
- 容差范围（±5%相对误差）

---

## 第三部分：Docker化与执行引擎（2026年4月14-20日）

### Phase 0 → Phase 1

```
fc21f47 feat: Phase 0 complete — FoamAgentExecutor, Gold Standards, hub sync
0f3cb2b feat(foam_agent): upgrade FoamAgentExecutor to Docker + OpenFOAM
a9e8931 docs: Phase 1 active — FoamAgentExecutor Docker upgrade, 103 tests
```

从MockExecutor升级到真实的Docker + OpenFOAM执行环境，这是一个质的飞跃。

### 执行引擎架构

```
foam_agent_adapter.py
├── MockExecutor        # 测试用，返回预设结果
└── FoamAgentExecutor   # Docker容器中的真实OpenFOAM
```

关键设计决策：
- **Docker隔离**：每次运行在独立容器中
- **OpenFOAM兼容**：支持OF8、OF10、OF12
- **求解器自动路由**：根据雷诺数自动选择icoFoam/simpleFoam/pimpleFoam

---

## 第四部分：Phase 3-5 闭环验证（2026年4月20-22日）

### Phase 3：全量E2E闭环验证

```
85878a6 feat(Phase 3): 完成 P0 全量E2E闭环验证 + 4新几何生成器
```

Phase 3完成了第一次真正的端到端验证循环。

### Phase 4：误差自动归因链

```
323e4db feat(Phase 4 C3): 误差自动归因链 — AttributionReport + ErrorAttributor
```

ErrorAttributor是项目的一个关键创新——它不仅告诉你"错了"，还告诉你"为什么错"：

- 是求解器设置问题？
- 是网格分辨率不够？
- 是边界条件配置错误？
- 是物理模型选择不当？

### Phase 5：Solver级归因

```
8362a6e feat(Phase 5): T3 ErrorAttributor solver-level归因 + kqWallFunction OF10修复
```

Phase 5将归因深入到求解器级别。

---

## 第五部分：治理体系的诞生（2026年4月20-21日）

### v6.1自主治理规则

根据`RETRO-V61-001`的记录，2026年4月20日建立了v6.1自主治理规则：

```
DEC-V61-001 (Counter 1): v6.1 cutover
DEC-V61-002 (Counter 2): Path B election
DEC-V61-003 (Counter 3): Phase 1-4 MVP
...
DEC-V61-012 (Counter 10 ⚠): PR-5a manifest builder — 触发阈值
```

### Counter系统

v6.1的核心是一个**Counter系统**：

- Counter从0开始计算
- 每次自主决策（autonomous_governance: true）递增
- Counter ≥ 10 触发审查策略检查
- Counter ≥ 20 触发正式回顾

### 第一次现实检验

Counter 9→10 的跨越发生在PR-5c（HMAC签名模块）之前。根据记录：

> "Kogami approved: continue autonomous PR-5c, self-dispatch Codex review post-merge"

这是一个关键的治理决策——不是停止，而是**改变审查策略**。

---

## 第六部分：Codex 5轮审查的启示（2026年4月21日）

### RETRO-V61-001：Counter-16回顾

2026年4月21日凌晨4:50，完成了第一次重大回顾——RETRO-V61-001。

核心发现：

| 指标 | 数值 |
|------|------|
| 审查的DEC数量 | 19个（Counter 1→16）|
| Codex审查轮数 | 平均5轮 |
| 第一轮通过率 | 0% |
| 累计Token消耗 | 526,798 |

### 震惊的发现：自评 vs 实际

| DEC | 自我估计 | Codex实际 verdict |
|-----|----------|-------------------|
| V61-014 | 93% | APPROVED_WITH_NOTES |
| V61-015 | 92% | APPROVED_WITH_NOTES |
| V61-016 | 88% | APPROVED_WITH_NOTES |
| **V61-018** | **60%** | **CHANGES_REQUIRED** |
| V61-019 | 90% | APPROVED_WITH_NOTES |

**V61-018是唯一一个诚实面对不确定性（60%）的DEC，而它果然失败了。**

### Codex发现的真实问题

Round 4（PR-5d）单独一轮就捕获了2个**HIGH**级别问题：

1. **HIGH #1**：签名路由会为空案例ID生成空签名包——在受监管审查中，**签署一份没有证据的审计包比没有签名更糟糕**

2. **HIGH #2**：字节可复现性被文档声明为核心契约，但被墙钟时间戳悄悄破坏

> "Round 4 alone justified the entire 5-round arc."
> ~263k tokens per HIGH finding caught.

### 教训总结

RETRO-V61-001总结了五条核心教训：

1. **Dispatcher审查清单**：审查调度器时，必须检查所有构造函数
2. **"静默错误路由"类别**：任何改变调度逻辑的PR应默认≤85%通过率
3. **参数归一化是已知分割点**：触碰适配器路由时应将构造路径覆盖作为第一优先级门控
4. **自评通过率诚实性**：≤70%的自评必须触发Codex pre-merge审查
5. **机械逐字例外规则**：需要5个条件全部满足才能跳过Codex

---

## 第七部分：PASS清洗风暴（2026年4月22日）

### DEC-V61-036：硬比较器门G1

2026年4月22日，用户深度审查发现了一个致命问题：

> "BFS再附长度列 'U_residual_magnitude' / duct_flow摩擦因子列 'hydraulic_diameter' — **不是同一个量**。"

这被称为**PASS清洗**（PASS-washing）——系统错误地将**错误量**通过了验证：

| 案例 | 黄金期望 | 实际测量 | 当前判决 |
|------|----------|----------|----------|
| BFS | 再附长度 (Xr/H ≈ 6.26) | U_residual_magnitude ≈ 0.044 | FAIL +0.48%（意外接近） |
| duct_flow | 摩擦因子 (f ≈ 0.0185) | hydraulic_diameter = 0.1 | FAIL +440% |

**7个案例都在测错量，但系统给出了PASS或接近PASS的判决。**

### G1门：缺失目标量

DEC-V61-036引入了G1硬比较器门：

```python
# 如果黄金目标量（及其别名）未在运行结果中找到：
measurement.value = None
extraction_source = "no_numeric_quantity"
# 强制FAIL并附带MISSING_TARGET_QUANTITY审计关注
```

### Phase 8冲刺：清理闭环

从DEC-V61-035到DEC-V61-041，Phase 8完成了一次完整的PASS清洗：

| DEC | 主题 | Codex轮数 | 最终判决 |
|-----|------|-----------|----------|
| V61-036 | G1缺失目标量门 | 2 | APPROVED |
| V61-038 | 收敛见证器A1-A6 | 0 | self-approved |
| V61-040 | UI见证器表面 | 3 | APPROVED |
| V61-042 | 壁面梯度辅助 | 4 | APPROVED（3 CHANGES_REQ） |
| V61-043 | plane_channel u+/y+发射器 | 2 | APPROVED（1 CHANGES_REQ） |
| V61-044 | NACA C3表面采样器 | 3 | APPROVED（2 CHANGES_REQ） |
| V61-041 | 柱体Strouhal FFT | 2 | APPROVED（1 CHANGES_REQ） |

**代码承载模块第一轮通过率：0%**——每个都至少需要一轮Codex审查。

---

## 第八部分：多层架构演进（2026年4月23-25日）

### 系统架构v1.0

项目逐步演进出了四层架构：

```
┌─────────────────────────────────────────────────────────┐
│  UI Layer (前端工作台)                                    │
├─────────────────────────────────────────────────────────┤
│  Evaluation Plane (评估层)                                 │
│  - metrics/           指标计算                              │
│  - comparator_gates.py 硬比较器门 G1-G5                    │
├─────────────────────────────────────────────────────────┤
│  Control Plane (控制层)                                    │
│  - task_runner.py     任务编排                             │
│  - convergence_attestor.py 收敛见证器 A1-A6               │
├─────────────────────────────────────────────────────────┤
│  Knowledge Plane (知识层)                                  │
│  - knowledge_db.py    知识库                              │
│  - gold_standards/     黄金标准                            │
└─────────────────────────────────────────────────────────┘
```

### 三态判决系统

传统的PASS/FAIL二态系统被升级为**三态判决**：

| 判决类型 | 含义 |
|----------|------|
| `contract_status` | 与黄金标准的数值对比 |
| `profile_verdict` | 剖面一致性（如17个采样点有多少在容差内）|
| `attestation` | 求解器收敛健康度（A1-A6六项检查）|

**关键洞察**：这三个维度独立变化。代码可能数值偏差（contract FAIL），但求解器健康（attestation PASS）。

---

## 第九部分：P1-Arc完成与新挑战（2026年4月25日）

### P1 Arc完成回顾

```
2026-04-25_p1_arc_complete_retrospective.md
```

P1（Metrics & Trust）弧标志着项目进入了一个新阶段——从"建立基础"转向"确保可信"。

### 关键成就

截至2026年4月25日：

- ✅ 10个经典CFD基准案例全部建立
- ✅ 8个通过物理契约验证
- ✅ 三态判决系统运行稳定
- ✅ Codex审查协议完全文档化
- ✅ HMAC签名审计包可导出

### 待解决问题

- 2个案例因文献被锁定而暂停
- `foam_agent_adapter.py` 7000行单片问题待重构
- 一些测试fixtures需要更新

---

## 第十部分：v6.2三层治理架构（2026年4月26-27日）

### 三层治理的诞生

2026年4月27日，DEC-V61-087建立了v6.2三层治理架构：

```
┌─────────────────────────────────────────────────────────────┐
│  Strategic Layer (战略层)                                    │
│  Kogami-Claude-cosplay (claude -p subprocess)              │
│  触发条件：重大PR、RETRO草案、高风险变更                       │
├─────────────────────────────────────────────────────────────┤
│  Code Layer (代码层)                                         │
│  Codex GPT-5.4 (独立CLI)                                    │
│  触发条件：风险等级触发器（per RETRO-V61-001）                │
├─────────────────────────────────────────────────────────────┤
│  Archive Layer (归档层)                                      │
│  Notion (只写，通过现有同步)                                  │
│  触发条件：DEC落地 + 事后回顾                                 │
└─────────────────────────────────────────────────────────────┘
```

### Kogami触发清单

在执行以下操作前，必须运行`bash scripts/governance/kogami_invoke.sh`：

- [ ] Phase关闭（如果使用phase-dir模型）
- [ ] RETRO草案提交git后、Notion同步前
- [ ] Codex APPROVE后的高风险PR
- [ ] counter ≥ 20 arc-size retro
- [ ] 任何自主治理规则变更DEC

### 可以跳过Kogami的情况

- 单文件≤50 LOC的例行提交
- Codex APPROVE的逐字例外路径
- 仅文档CLASS-1变更
- Kogami对Kogami审查的反递归

---

## 第十一部分：技术债务与持续演进

### 已识别的技术债务

根据多个RETRO文件，项目积累了一些技术债务：

1. **`datetime.datetime.utcnow()` 弃用**
   - 位置：`correction_recorder.py:76`, `knowledge_db.py:220`
   - 建议：迁移到`datetime.datetime.now(datetime.timezone.utc)`

2. **`foam_agent_adapter.py` 7000行单片**
   - 状态：API冻结后重构
   - 风险：高

3. **测试fixtures老化**
   - 3个pre-existing测试失败（DHC Nu=30→8.8, TFP SST→laminar legacy）
   - 需要同步更新

### 验证脚本体系

v6.2建立了完整的验证脚本体系：

```bash
# Q1金丝雀回归测试（目标：5/5零泄露）
python3 scripts/governance/verify_q1_canary.py

# Q5关键词采样（目标：0内容命中）
python3 scripts/governance/verify_q5_keyword_sampling.py

# Q4计数器真值表兼容性（目标：0漂移）
python3 scripts/governance/verify_q4_counter_truth_table.py

# P-2.5战略包验证器（目标：8/8通过）
bash scripts/governance/test_strategic_package.sh
```

---

## 第十二部分：项目现状（2026年4月27日）

### 最新提交

```
f764294 feat(governance): DEC-V61-087 W4-A · dependency-triggered Q1 canary + Notion sync automation
a09b49c docs(state): DEC-V61-087 W4 closeout · v6.2 governance bootstrap CLOSED-LOOP COMPLETE
```

### 项目规模统计

| 指标 | 数值 |
|------|------|
| **总提交数** | **837条** |
| 开发天数 | 15天 |
| 日均提交 | 56次 |
| 源代码文件 | 61个Python文件 |
| 测试文件 | 78个Python测试 |
| 决策文件 | **82个DEC** |
| 回顾文件 | **10个RETRO** |
| Codex审查报告 | **73个** |
| 知识库条目 | 165个corrections |

### 提交频率热力图

| 日期 | 提交数 | 里程碑 |
|------|---------|--------|
| 04-13 | 16次 | Phase 0完成 |
| 04-14 | 17次 | |
| 04-15 | 9次 | |
| 04-16 | 3次 | |
| 04-17 | 12次 | |
| 04-18 | **49次** | 治理爆发 |
| 04-19 | 9次 | |
| 04-20 | **96次** | ⭐最高峰 |
| 04-21 | 72次 | |
| 04-22 | 64次 | |
| 04-23 | 61次 | |
| 04-24 | 38次 | |
| 04-25 | **129次** | 次高峰 |
| 04-26 | 83次 | |
| 04-27 | 23次 | v6.2完成 |

### 作者分布

| 作者 | 提交数 | 占比 |
|------|--------|------|
| claude-opus47-app | 523 | **62.5%** |
| JerryKogami | 119 | 14% |
| kogamishinyajerry-ops | 39 | 4.7% |

### 治理指标

- **Counter**: 当前运行中（v6.2重置）
- **Codex审查轮数**: 累计500+
- **Token消耗**: 百万级别
- **第一轮通过率**: ~0%（对于新代码）
- **平均审查轮数**: 4-5轮

---

## 第十三部分：项目启示录

### AI编程可信度的深度实验

这个项目最初的目标是解决"让CFD验证不再痛苦"。它意外地成为了一个关于**AI编程可信度**的深度实验。

核心发现：

1. **自评vs实际差距巨大**
   - AI自估通过率：80%
   - 独立审查第一轮通过率：0%
   - 达到最终通过所需轮数：平均5轮

2. **独立异质验证的价值**
   - 用另一个AI验证AI
   - "独立异质验证"协议可能成为AI系统可信度的标准
   - Codex捕获了人类审查者容易忽略的问题

3. **诚实是最好的策略**
   - 当自我估计≤70%时，触发强制pre-merge审查
   - 承认不确定性比伪装确定性更安全

### 对CFD工程师的价值

- **验证时间**：从30-60小时/案例降到分钟级
- **可追溯性**：每一步决策都有文献引用
- **可重复性**：同一输入、同一结果（byte-reproducible）

### 未来展望

根据项目的发展轨迹，cfd-harness-unified正在向以下方向演进：

1. **全自动化闭环**：从案例选择到审计包生成的完全自动化
2. **多学科扩展**：从CFD到热力学、结构力学的扩展
3. **协作工作台**：支持多用户并发验证
4. **标准化输出**：符合ISO/ASTM等标准的审计报告格式

---

## 附录A：关键决策索引

| DEC ID | 日期 | 主题 |
|--------|------|------|
| V61-001 | 04-20 | v6.1 cutover |
| V61-012 | 04-21 | Counter=10阈值触发 |
| V61-014 | 04-21 | HMAC签名模块 |
| V61-018 | 04-21 | CHANGES_REQUIRED（60%自评）|
| V61-036 | 04-22 | G1硬比较器门 |
| V61-038 | 04-22 | 收敛见证器A1-A6 |
| V61-040 | 04-22 | UI见证器表面 |
| V61-087 | 04-27 | v6.2 Kogami三层治理 |

---

## 附录B：Notion控制平面

### 5个Notion数据库

| 数据库 | ID | 用途 |
|--------|-----|------|
| Tasks | `2b25c81b15174eb48d0cca20e8d37c09` | 任务执行跟踪 |
| Sessions | `7905136d58de43a09cc365dec52ba51b` | 会话记录 |
| Decisions | `fa55d3ed0a6d452f909d91a8c8d218a7` | 决策留痕 |
| Canonical Docs | `96a6344f4a42442dabb3a96e9faadee6` | 文档索引 |
| Phases | `25a50aa20e3f476a8ad611725a9fbe8b` | 阶段控制 |

### 同步机制

DEC→Notion同步是**事件驱动**的（不是定时轮询），符合项目"禁用日期/调度门控"原则：

```python
# notion_sync_dec.py 核心逻辑
1. 读取DEC frontmatter
2. 映射到Notion Decisions DB schema
3. 创建新页面或更新已有页面（按decision_id匹配）
4. 同步后回填 notion_sync_status 字段
```

---

## 附录C：会话历史（Sessions）

### 会话时间线

| 会话 | 日期 | 里程碑 |
|------|------|---------|
| S-001 | 04-13 | Phase 0完成，88个测试通过 |
| S-002 | 04-18 | ADWM v5.2深度验收 |
| S-003 | 04-20 | Claude Code中途停止gate触发 |
| S-004 | 04-21 | 新会话开工，v6.1 counter=15 |
| S-005 | 04-26 | RETRO-V61-006 Session B完成 |

### 模型协作模式

根据`.claude/MODEL_ROUTING.md`：

| 模型 | 职责 | 调用方式 |
|-----|------|---------|
| MiniMax-2.7 | 唯一开发指令交互窗口 | 直接执行 |
| Opus 4.6 | 复杂架构/深度规划 | Notion @Opus 4.6 |
| Codex GPT-5.4 | 代码审查60% + 并行开发40% | `/codex-gpt54` |
| Gemini 2.5 Flash | 快速调研/信息检索 | `/gemini-ccr` |

---

## 附录D：四平面架构（ADR-001）

项目采用严格的四层架构，强制执行禁止跨层导入：

```
┌─────────────────────────────────────────────────────────────┐
│  UI Plane (用户界面层)                                          │
│  ui/frontend/ + ui/backend/                                    │
└──────────────────────────┬────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│  Evaluation Plane (评估层)                                       │
│  src/auto_verifier/ + src/metrics/ + comparator_gates.py       │
└──────────────────────────┬────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│  Control Plane (控制层)                                         │
│  src/task_runner.py + convergence_attestor.py                   │
└──────────────────────────┬────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│  Knowledge Plane (知识层)                                       │
│  knowledge_db.py + gold_standards/ + whitelist.yaml            │
└─────────────────────────────────────────────────────────────┘
```

**硬边界规则**：Knowledge Plane的文件禁止被上层直接导入（import-linter在CI强制执行）。

---

## 附录E：A1..A6 + G3..G5门控系统

### 收敛见证器（A1..A6）

在提取任何数据之前，求解器必须通过这六项检查：

| 门 | 名称 | 检查内容 |
|----|------|----------|
| A1 | solver_exit_clean | 求解器正常退出（非崩溃/被杀）|
| A2 | continuity_floor | 连续性方程残差达到地板值 |
| A3 | residual_floor | 动量方程残差达到地板值 |
| A4 | solver_iteration_cap | 迭代次数未超过上限 |
| A5 | bounding_recurrence | 无异常的重 bounding 事件 |
| A6 | no_residual_progress | 不是残差无进展的假收敛 |

### 后提取硬门（G3..G5）

在通过A门后，数据提取后还要通过物理检查：

| 门 | 名称 | 检查内容 |
|----|------|----------|
| G3 | VELOCITY_OVERFLOW | \|U\|max > 100×U_ref |
| G4 | TURBULENCE_NEGATIVE | k/ε/ω < 0 |
| G5 | CONTINUITY_DIVERGED | sum_local > 1e-2 |

---

## 下一步

本文件将持续更新，记录项目的完整演化历程。

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-04-27 | 初始版本，13章节基础框架 |
| v1.1 | 2026-04-27 | 整合4个探索者报告，补充附录A-E |

---

## 续写提示词（下一个会话）

下一个会话请选择以下任一方向继续深挖：

### 方向A：Codex审查案例研究
深入分析`reports/codex_tool_reports/`中的Codex审查报告，提取：
- 每轮审查的具体发现（F1/F2...分类）
- token消耗趋势
- 修复模式总结

### 方向B：CFD案例验证史
还原每个案例从建立到验证通过的完整过程：
- `knowledge/gold_standards/`下15个YAML的演变
- `knowledge/corrections/`中165条修正的触发原因

### 方向C：治理演进深度分析
分析10个RETRO文件，追踪：
- v6.1→v6.2治理模式的演变
- 关键治理决策的上下文

### 方向D：ADWM相关探索
探索`.planning/adwm/`目录，理解：
- ADWM v5.2自我验收机制
- G1-G5系列的审查决策
