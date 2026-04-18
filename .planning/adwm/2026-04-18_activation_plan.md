# ADWM Activation Plan · cfd-harness-unified

- 时间戳: 2026-04-18T20:45 (local)
- 启动者: Kogami Shinya (CFDJerry)
- 驱动: Main Opus 4.7（ADWM v5.2 准治理权）
- 硬底板: 10 项全部 ACTIVE（见启动提示词）
- Notion Sessions DB 同步: **PENDING** — MCP 当前 Server not found，本文件为本地等效记录，Notion 回通后补写 "ADWM Activation · 2026-04-18 20:45"

## 1. 当前状态诊断（3 句）

1. **方法论层已成熟**: 10/10 whitelist 已打 physics_contract, EX-1-006 生产者→消费者通道上线, audit_concern 能把 3/10 silent-pass-hazard 顺向外显; EX-1 rolling override_rate 稳定在 0.143 (n=7), 无规则触发.
2. **可信度层暴露关键缺口**: EX-1-007 B1 post-commit 测量 Nu=66.25 (gold=30), 根因是 `_extract_nc_nusselt` 取 local mid-height 梯度而非 mean wall-integrated 积分 — 粗糙的 80-uniform 基线靠欠解析 BL 凑到 Nu=5.85 掩盖了这个 bug; B1 壁面压缩网格把它暴露了出来. 这是 project 终极目标（15-case 可信 GS 比对）的直接阻塞项.
3. **交付层尚未成型**: 目前没有任何 case 产出档1/档2/档3 demo-ready 材料（Before/After/Reference 叠加图 + Error Convergence Narrative）; NACA0012 Wave 3 已 closeout DEC-EX-A 永久 deviation; PL-1 仍 FROZEN 等 D5.

## 2. 本次 ADWM 期内目标（3-5 项，按价值排序）

### G1 — EX-1-008: `_extract_nc_nusselt` mean-Nu 重构（最高价值）

- **为何最高**: 直接解锁 "B1 mesh 能否把 DHC 带进 gold 容差带" 的答案; 同时关闭 3 个 silent-pass-hazard 中技术上最可实施的那一个
- **路径**: 起草 Fix Plan Packet（CHK 列表 + 自审 APPROVE） → dispatch Codex 执行（src/** 禁区, 硬底板 #2 强制）
- **CHK 预置**:
  - CHK-1: hot_wall patch surface integration via `postProcess wallHeatFlux` OR 显式 ∫snGrad(T)dA
  - CHK-2: 在 B1 256² 网格上跑 Nu ∈ [25, 32]（gold ±15% 带）
  - CHK-3: 在 80²-uniform Ra=1e6 (rayleigh_benard) 上保持 Nu=10.5 bit-identical
  - CHK-4: 250/250 tests 保持绿
  - CHK-5: `Execution-by: codex-gpt54` trailer
- **预期时长**: 1-2 slice（1-3h wall）
- **可逆性**: reversible (git revert)

### G2 — 档1 Demo Package: 3 个干净 PASS case 的 Case Completion Report（高价值）

- **为何**: 项目终极目标的交付形态之一; ADWM 深度验收条件 (c) 的直接产物; 不触禁区, 我可直接写
- **目标 case**: lid_driven_cavity_benchmark, backward_facing_step_steady, cylinder_crossflow (Phase 7 PASS + EX-1-005 contract_status=COMPATIBLE 干净样本)
- **每份报告 9 节**: §1 case 概要 + §2 执行记录 + §3 场比对图（Before/After/Reference 叠加） + §4 CHK 表格 + §5 key_quantities 数值对比 + §6 contract_status + §7 评审级 3 行小结 + §8 可视化 + §9 纠错叙事
- **复用**: 已有 reports/lid_driven_cavity_benchmark/, backward_facing_step_steady/, cylinder_crossflow/ 目录
- **可逆性**: reversible

### G3 — circular_cylinder_wake YAML-comment → 结构化字段（中价值，1/10 覆盖缺口）

- **为何**: EX-1-006 发现的数据质量缺口 (yaml.safe_load 无法读 comment-encoded contract_status); 1/10 silently skipped by producer→consumer
- **路径**: 禁区 (knowledge/gold_standards/**) → dispatch Codex
- **CHK-1**: yaml.safe_load 能直接读到 contract_status
- **CHK-2**: ldc/BFS-style multi-doc 结构保留
- **CHK-3**: producer→consumer 10/10 通达
- **可逆性**: reversible

### G4 — 10-case physics_contract dashboard snapshot（中价值）

- **为何**: 单页可追溯的当前状态摘要; ADWM 深度验收包 §4 直接引用
- **路径**: reports/deep_acceptance/ 下新建 dashboard.md（非禁区, 可直接写）
- **内容**: 10 case × { verdict, contract_status, audit_concern, silent_pass_hazard_file_line, last_measurement }
- **可逆性**: reversible

### G5 — Decisions DB 本地等效 + Notion 回补队列（守规矩）

- **为何**: ADWM 准治理权使用纪律强要求; 每个治理级决策要留痕
- **路径**: `.planning/decisions/YYYY-MM-DD_<slug>.md` (本文件已创建首条)
- **Notion 回补条件**: MCP server 恢复 OR Kogami 深度验收触达
- **可逆性**: reversible

## 3. 自触发深度验收预估时间窗

- **预计**: 48–72 小时内 或 完成 G1+G2 时（取先到者）
- **明确触达条件**:
  - 若 G1 把 B1 Nu 带进 [25,32] → 深度验收条件 (a) Phase 级里程碑（EX-1-008 landing）
  - 若 G2 产出 3 份 Case Completion Report → 深度验收条件 (c) demo-ready 材料就绪
  - 若 Decisions autonomous_governance ≥ 5 条 → 深度验收条件 (b)
- **不会触达**: 15-case whitelist 移除（底板 #6）、GS tolerance 调整（底板 #1）、四 Plane 架构修改（底板 #5）均不在本期计划内

## 4. 本期准治理权行使清单

| 权力 | 计划行使 | 理由 |
|---|---|---|
| 起草并自审 Fix Plan Packet | ✅ G1 + G3 | src/ 和 knowledge/gold_standards/ 都是禁区 → 必走 Codex dispatch + 自签 APPROVE |
| 调整 Phase/Wave 执行顺序 | ⏸ 不计划 | Phase 8 已 complete, Phase 9 仍在 EX-1 轨道, 无需调整 |
| 冻结/解冻 Track | ⏸ 不计划 | PL-1 继续 FROZEN (C4 D5-gated); EX-1 继续活跃; SY-1 已完成 |
| 修订 Model Routing Policy | ⏸ 不计划 | v1.3 足够使用 |
| 修订滚动阈值 | ⏸ 不计划 | 当前 0.143 距 0.30 仍有 2× 余量, 无需调整 |
| 创建/归档/重排 Task | ✅ | 创建 EX-1-008 (#32) 和 Case Completion Report (#33) 任务 |
| 在 Sessions DB 追加 | ⚠️ PENDING | Notion 不可达, 本地等效记录 |
| 在 Decisions DB 记录 | ⚠️ PENDING | 同上 |

## 5. Kogami 回来时可否决性评估

| 项 | 若被否决需回滚的 artifacts |
|---|---|
| G1 EX-1-008 refactor | 1 个 commit (Codex execution-by); 测量结果 YAML; 若 CHK-2 未达带, 仍保留作为"B1 mesh 已极致但 gold 定义需重审"的证据 |
| G2 Case Completion Reports | 3 个 reports/ MD 文件 + 叠加图; 纯文档, 零副作用 |
| G3 cylinder restructure | 1 个 knowledge/gold_standards/ 修改 commit; producer→consumer 覆盖可回到 9/10 |
| G4 dashboard snapshot | 1 个 reports/ MD 文件; 纯文档 |
| G5 Decisions 本地文件 | 若 Notion 回通后发现双写冲突, 以 Notion 为准覆盖本地 |

## 6. 诚实项（违反"隐藏失败不被允许"会触发的自保条款）

- **EX-1-007 B1 50ec0a3 commit trailer**: 使用了 `Co-Authored-By:` 而非 ADWM 要求的 `Execution-by: opus47-main`/`codex-gpt54`. 背景: 该 commit 早于 ADWM 启动, 按时的 Model Routing v5.1 self-Gate 规则; 不追溯修订, 但此后所有新 commit 将带 ADWM-合规 trailer.
- **Notion Sessions DB 写入失败**: MCP server not found. 本地文件为等效记录, 但形式上未满足启动提示词第 3 步. 在深度验收包中单列为"基础设施缺口".
- **EX-1-008 成功概率诚实自估**: 约 60%. 不确定项 = (a) wallHeatFlux postProcess utility 在 buoyantFoam 下是否可靠 (Ra=1e10 的 mixed BC), (b) 面积分归一化是否与 gold Dhir 2001 定义一致.

## 7. 启动后立即执行序列

1. G5 落地: 本文件 + 首条 Decision 记录
2. G4 落地: 10-case dashboard snapshot
3. G1 起草 Fix Plan Packet → 自审 APPROVE → dispatch Codex（后台）
4. 等 Codex 期间: G2 档 1 demo Report 起草（LDC 先行）
5. Codex 回执后验证 CHK 表 → 若 PASS 则 commit → 若 FAIL 则切入 Fuse (2 cycle 上限, 同 NACA0012 Wave 3)
6. G3 起草 Fix Plan Packet → dispatch Codex

---

签发: opus47-main (ADWM v5.2 self-Gate)
