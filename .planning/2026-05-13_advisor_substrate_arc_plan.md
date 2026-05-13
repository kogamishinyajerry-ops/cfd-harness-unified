# Advisor Substrate Arc · 开发计划

**Generated**: 2026-05-13 by Claude Code Opus 4.7 session
**Status**: Active · milestone-driven · NO calendar deadlines
**Predecessor**: DEC-V61-198 (industrial-case substrate pivot)
**Successor placeholder**: V62 charter (drafted in M-V62 milestone, content TBD)
**Format**: ROADMAP-style (not a DEC · per user preference 2026-05-13)

---

## 1. North Star

> **让 "Claude Code session = 工业级 CFD advisor" 这个命题从单 case anecdote 升级为跨 6 个工业 case 的可复现实证 + advisor stack 代码层闭环。**

反命题（如果只达到下面就算 arc 失败）：

- ❌ V-series 加了 26 行但 advisor stack 没新 land 1 个 → 失败（只 sediment 不 advisor）
- ❌ A4-A8 全 land 但 Track C 仍卡在 1 case → 失败（写了 advisor 没验证）
- ❌ Track C 通过 6 case 但都靠人工 walkthrough · advisor stack 没接管 → 失败（M6 charter 没实证）

---

## 2. Arc-level Done Definition

Arc 闭环触发条件（全部满足）：

| 维度 | 起点 (2026-05-13) | Done 阈值 |
|---|---|---|
| Track C session 完成 case 数 | 1 (case_010 only) | **≥ 6** |
| Advisor stack LANDED | 4 (A1/A2-v2/A3/A7) | **≥ 8** (含 ≥ 1 D-class) |
| V-series 行数 | 84 | **≥ 100** |
| 工业 case end-to-end solver 跑通的 numerics class | 1 (compressible-buoyant-RANS) | **≥ 3** |
| 雷达图左半轴均分 (CAD/网格/物理/求解器/后处理) | 6.4 | **≥ 7.2** |
| 雷达图右半轴均分 (CLI/AI/审计) | 8.7 | **≥ 8.7（维持）** |
| 商业 CAE AI 预测分（监控用，不是 done 条件） | STAR-CCM+ AI = 2 | 若 ≥ 5 触发战略复审 |

任一未达成 → arc 不 close，启动 retro 分析 root cause 决定调整 plan 还是延伸。

---

## 3. Milestone 清单（无日历 · 按依赖排序）

依赖关系标注：`(deps: M-X, M-Y)`

### Tier 1 · 解锁性 milestones（先做）

| ID | 内容 | 类型 | 影响雷达轴 | 依赖 |
|---|---|---|---|---|
| **M-A4** | A4 `face_orientation` advisor land · sub-DEC under V61-198 | 代码 | 网格 + CAD + AI | 无 |
| **M-V81** | V81 inlet/outlet validator close · sub-DEC closure | 代码 | CAD + AI | 无 |
| **M-DRIFT** | Corpus drift-prevention pre-commit hook | spike-class | 审计 | 无 |
| **M-TRACK-2** | Track C session 2 · case_011 plate-fin compact HX | Track C | AI · 可重现 | 无 |
| **M-APU-RESTORE** | APU bay v6N B+ STL surgery (apu_intake patch restore + buoyantPimpleFoam 切换 first iter) | spike-class | CAD + 求解器 | 无 (可选) |

**Tier 1 exit signal**：≥ 1 advisor 新 LANDED (M-A4) + Track C 累计 2 case (M-TRACK-2) + V81 closed。如果 M-A4 做不下去，提前 surface 给 main session reasoning。

### Tier 2 · advisor 加宽（Tier 1 之后）

| ID | 内容 | 类型 | 影响雷达轴 | 依赖 |
|---|---|---|---|---|
| **M-A6** | A6 `hvac_adpi.py` advisor land | 代码 | 物理 + AI | M-A4（保持 sub-DEC 节奏） |
| **M-A8** | A8 `shm_dict_validator.py` advisor land | 代码 | 网格 + AI | M-A4 |
| **M-A5** | A5 unallocated 填充 · ≥ 1 候选 drafted | research → spec | AI | M-A4/A6/A8 任一 |
| **M-D6** | D6 `extra_body_in_fluid` advisor: drafted → ready-to-land | promotion | AI | M-A6（保持 D-class promotion gate 经验） |
| **M-TRACK-3** | Track C session 3 · case_004 NREL Phase VI MRF | Track C | AI · 可重现 | M-TRACK-2 (pacing) |
| **M-TRACK-4** | Track C session 4 · case_009 Sandia Flame D reacting | Track C | 物理 + AI | M-TRACK-3 |

**Tier 2 exit signal**：累计 7 LANDED advisor + Track C 4 case + D6 进 ready-to-land。

### Tier 3 · 收口 + V62 charter（Tier 2 之后）

| ID | 内容 | 类型 | 影响雷达轴 | 依赖 |
|---|---|---|---|---|
| **M-D9-D10** | D9/D10 advisor candidate promotion · harvest-003 cycle 实质推进 | promotion | AI | M-D6 |
| **M-XCLASS** | 跨 numerics-class 第二案例（推荐 case_002a 二次访 with apu_intake restored，或 case_010 v1.5 production run） | new Track C session | 求解器 + 物理 | M-APU-RESTORE 或 M-TRACK-2 |
| **M-TRACK-5** | Track C session 5 · CHT 或 acoustic 复访 | Track C | AI | M-TRACK-4 |
| **M-TRACK-6** | Track C session 6 · 最后一 case 类型 | Track C | AI | M-TRACK-5 |
| **M-V100** | V-series 行数 ≥ 100 · milestone marker | sediment | AI · 审计 | sum(Tier 1/2/3 sediment) ≥ 16 V-row |
| **M-RADAR-V2** | 重画 capability radar · 验证左半轴是否真的拉上来 | governance | 全雷达 | M-V100 |
| **M-V62** | V61-198 arc close DEC + V62 charter draft | charter | governance | M-RADAR-V2 |

**Tier 3 exit = Arc Done**：M-V62 完成 + 全部 Done Definition 维度达标 → arc closed → V62 charter 接手。

---

## 4. 战略框架

### 持续投资 ✅

1. **Advisor stack code land**（A4/A5/A6/A8/D6-D10）— 项目核心 moat
2. **Track C M6 e2e 验证**（pacing ≈ 1 session per 2 weeks · 跨 6 case substrate）— thesis 实证
3. **V-series sediment**（每 case 1-3 行 V-row · auto-sync to runtime corpus）— knowledge moat
4. **Sub-DEC under V61-198 / V62** pattern 保持

### 故意不投资 ❌

1. **HPC 扩展性**（cluster / 1000+ cores）— 4-core ARM 是 substrate 边界
2. **多场耦合 FSI / multi-physics chain** — 超 substrate 边界
3. **Polyhedral mesh / wrapped meshing 仿制** — OpenFOAM 限制不去补
4. **工业 GUI / web dashboard 后处理** — ParaView script 路线已成熟
5. **N2-N6 workbench frontend parity** — v2.3 unlock 但**不在本 arc**
6. **新 numerics class case 启动**（cavitation / DEM / EHD） — 现有 10 类已是 substrate 充分
7. **OSS release / pilot user** — 太早，advisor stack 还在 build · 留给 V62

### 触发性条件（命中时本 plan 需要 redirect）

- ☑️ **Track C ≥ 2 个 case 同类 advisor 盲点重复** → harvest-003 提前到本 arc，新建 M-HARVEST milestone
- ☑️ **商业 CAE AI 预测分进 ≥ 5**（如 Siemens Industrial Copilot GA） → 战略复审，可能拉前 OSS readiness 路径，V62 charter 内容会变
- ☑️ **Advisor stack 出现 cross-cutting refactor 需求**（≥ 3 个 service 文件 schema 变） → 升级为完整 charter DEC，本 plan 升级到 V62 phase 0
- ☑️ **任一 milestone 卡 3 周** → 不死等，跳过 + retro

---

## 5. 风险登记

| ID | 风险 | 概率 | 缓解 |
|---|---|---|---|
| R1 | Track C session pacing 拖到 1/月 | 高 | 严格 1/2 周 · 若 1 月无新 session 触发"主线偏离"retro |
| R2 | A4/A6/A8 中 cross-topology evidence 永远到不了 2 case | 中 | 提前在 Tier 1 把 evidence 高概率的（A4/A8）先做，A6 放 Tier 2 缓冲 |
| R3 | 商业 CAE AI 评分预测涨到 ≥ 5 | 中 | M-RADAR-V2 触发战略复审 |
| R4 | Advisor stack cross-cutting refactor | 低 | 触发完整 charter DEC，arc 升级到 V62 |
| R5 | 跨 numerics-class 第二案例 substrate 太陌生 | 中 | 优先 case_002a/case_010 二次访问，不启动 case_017+ |
| R6 | 用户工作焦点偏离（demo / OSS / frontend pull） | 中 | 每 Tier 末尾 review，user 可 redirect |
| R7 | Multi-session context drift | 中 | STATE.md / RESUME.md / memory 维护 · 每 Tier 末必须更新 |

---

## 6. 检查点（无日历 · 按 milestone 触发）

每个 Tier 完成时执行：

1. **数字对账**：累计 LANDED advisor 数 / V-series 行数 / Track C case 数
2. **Retro**：写 `.planning/retrospectives/<date>_tier_N_check.md` · 实际 vs 计划
3. **下一 Tier 调整**：基于实际进度 redirect，不死守清单
4. **STATE.md 更新**

每个 Track C session 完成时单独写 retro（已是当前 cadence · 见 `2026-05-13_track_c_advisor_e2e_session_1_case_010.md`）。

---

## 7. 显式开放 / 可被用户拉回的方向

如果你说"加 X"，X 会进入本 plan：

- **N2-N6 workbench frontend parity** — v2.3 unlock 项，目前 defer
- **工业 GUI / web dashboard / Trame 后处理实时化** — defer
- **多语言 corpus（英文 V-series export）** — defer
- **HPC scaling validation** — defer
- **OSS release prep / pilot user onboarding** — defer 到 V62
- **新 numerics class case**（cavitation / DEM / EHD） — defer

---

## 8. 进展跟踪

实际进度 tracking 落在：

- **STATE.md** → `current_arc: advisor_substrate_arc · started 2026-05-13`
- **本文件** → 每个 milestone 完成时 strike-through 标记 + 添加 LANDED commit hash
- **`.planning/decisions/`** → sub-DEC for advisor land (M-A4 / M-A6 / M-A8 / M-V81)
- **`.planning/retrospectives/`** → 每 Track C session + 每 Tier 末

无 Notion sync（本文件不是 Accepted DEC · per v2.3 round-1 loosen · 仅 Accepted DEC sync）。

---

## 9. 命名理由

- 名称：**"Advisor Substrate Arc"**
- "Advisor" = 主线 = advisor stack code land + Claude Code session as advisor 实证
- "Substrate" = thesis = 一组工业 case 作为 advisor 真实工作的 substrate
- "Arc" = 跟 V61-198 / V62 同级的开发弧线名称

如果用户对名字不满意（"Advisor Substrate" 太抽象）可以改成例如：
- "AI Advisor Closure Arc"
- "M6 Charter Implementation Arc"
- "Track C Validation Arc"

---

## 10. 起点 commit

本文件 commit 后开始执行。首个动作建议 M-A4（advisor stack 节奏热身最自然的延续）。
