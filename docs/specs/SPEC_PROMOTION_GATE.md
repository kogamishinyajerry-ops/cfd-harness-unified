# SPEC_PROMOTION_GATE — Canonical Spec Draft → Active 审查标准

**Status**: Active v1.1
**Effective**: 2026-04-24 (v1.0) · 2026-04-24 (v1.1 — G-D refined inline during VCP rc2 mini-retro · Opus Gate signed Option X, see §8 changelog)
**Authority**: Opus 4.7 Independent Gate · Pivot 2026-04-22 Post-Hoc Review §2 + G-D Refinement Gate 2026-04-24
**Supersedes**: 无（本文件为 Pivot 后新建）
**Notion SSOT**: <https://www.notion.so/Pivot-Charter-2026-04-22-CFD-Harness-OS-70e55a0c3f924736b0cb68add01d90cd>

---

## §1 目的与适用范围

Pivot 2026-04-22 之后，6 份 Canonical Spec (METRICS_AND_TRUST_GATES,
EXECUTOR_ABSTRACTION, DATASET_TASK_SIM_PROTOCOL, KNOWLEDGE_OBJECT_MODEL,
SURROGATE_BACKEND_PLUGIN_SPEC, DIFFERENTIABLE_LAB_SCOPE) 同时处于 Draft
v0.1。各自写了 §6 Deliverables，但无统一的 Draft → Active 审查标准，会
在 P1-P6 反复产生"够不够 Active"的口水战。

本文件是 6 份 Spec（及未来新增的 Canonical Spec）Draft → Active 的
**强制审查标准**。任何 Spec 从 Draft 晋升 Active 都必须同时满足 §2 的
6 条通用硬门 AND §3 的该 Spec 单独 blocker。

GOV-1 (VERSION_COMPATIBILITY_POLICY v0.1 → v1.0) 是本文件的第一位
consumer；其 Active 晋升也要过本文件的 6 门。

## §2 通用硬门（6 条 · AND 逻辑）

晋升 Active 前必须同时满足：

| # | 门 | 验证方式 |
|---|---|---|
| G-A | Deliverables 清单 ≥ 80% 已 merge 到 `main` | PR 列表对照 spec §6；剩余 ≤ 20% 必须挂 follow-up DEC，frontmatter 显式列出 |
| G-B | 至少 1 个端到端冒烟案例跑通（非单测） | `scripts/` 下有可复现冒烟入口；输出写入 `reports/<spec-name>/smoke/` |
| G-C | 与上下游 spec 的接口类型已 cross-ref | spec 文档的 "Interface Surface" 段显式引用上下游 spec 的类型名 + 版本号 |
| G-D | 本 spec 的 "不做清单" 每条必须显式标注类别（Cat 1/2/3, §7）并满足对应 evidence 要求 | Cat 1 → 回归测试 / importlinter / grep-based CI assertion；Cat 2 → §9.1 `scope_delegations` 表 + consumer spec 的 accepting clause；Cat 3 → `docs/governance/POLICY_COMMITMENTS_LEDGER.md` entry + `DEC-POLICY-*` |
| G-E | Decisions DB 至少 1 条 `DEC-PIVOT-P{n}-*` 记录关键设计取舍 | Notion Decisions DB 查询；frontmatter `spec_ref: <spec-name>` |
| G-F | 独立异构验证（Codex 或人工）签字 **无 HIGH** | `reports/codex_tool_reports/<spec-name>_promotion.log`；或 review issue |

**AND 逻辑说明**：6 门**同时**满足。任一不满足 → spec 维持 Draft，由 owner
补齐后重新提交 Gate。不允许"5/6 通过 + 一条豁免"的软裁决。

## §3 各 Spec 单独 blocker 表

每份 spec 在满足 §2 通用 6 门的基础上，额外满足下列单独 blocker。

| Spec | 单独 blocker | 当前核心 blocker（2026-04-24） |
|---|---|---|
| **METRICS_AND_TRUST_GATES** | tolerance 全部来自 `CaseProfile.tolerance_policy`（not hardcoded）；至少 1 个 case 跑通三态决策（PASS / WARN / FAIL）并产出 `reports/{case}/trust_verdict.yaml` | **GOV-1 未落** — CaseProfile 四元组元数据字段名无权威来源 |
| **EXECUTOR_ABSTRACTION** | `FoamAgentExecutor` 完成 `docker-openfoam` 封装 + `mock` + `hybrid-init` skeleton 三模式同时回归通过 | `src/foam_agent_adapter.py` 7000-line 重构（RETRO-V61-001 遗留项） |
| **DATASET_TASK_SIM_PROTOCOL** | 10 cases 完整迁移到 `case_families/` 目录 + manifest ↔ Whitelist CI 一致性绿 | KNOWLEDGE_OBJECT_MODEL 先 v1.0（schema 先冻结） |
| **KNOWLEDGE_OBJECT_MODEL** | 8 类对象 schema 冻结；append-only Provenance 运行期验证；≥ 3 FailurePattern + ≥ 3 CorrectionPattern 示例迁移 | Phase 5 audit package 的 provenance 回补未完 |
| **SURROGATE_BACKEND_PLUGIN_SPEC** | `NullSurrogateBackend` 上线；P1-P4 全部 v1.0 完成 | 串行依赖（P1-P4 链尾） |
| **DIFFERENTIABLE_LAB_SCOPE** | `src/diff_lab/**` 目录骨架；CI 独立 gate；主链路 import 禁入的 grep 绿 | ADR-001 层间 import 检查器（见 `docs/adr/ADR-001-*`） |

## §4 审批流程

1. **Owner 自检** — spec owner 填写 `.planning/spec_promotion/<spec-name>_gate_checklist.md`，6 门逐条打勾并贴证据链接
2. **Claude Code 主会话预审** — 对照本文件核对每一条门；不通过直接打回
3. **Codex 独立验证** — 触发 v6.2 §B 关键声明验证；输出写入 `reports/codex_tool_reports/<spec-name>_promotion.log`；**无 HIGH** 才放行
4. **Opus 4.7 Gate 签字** — 在 Notion 对应 spec 页面 `Status` 字段从 `Draft` 改为 `Active`，填写 `promotion_date` + `gate_verdict` 属性
5. **Repo stamp** — spec 文件 frontmatter `status: Active` + `effective: YYYY-MM-DD`；commit 消息必须引用本文件（`per SPEC_PROMOTION_GATE.md §2`）

## §5 不做清单

本文件明确**不做**：
- 不定义 Spec 内部结构（各 spec 自行决定章节）
- 不替代单独 blocker 表之外的业务规则（例如 METRICS 的三态决策语义）
- 不约束 Draft 阶段的迭代节奏（Draft 内部可以自由 v0.1 → v0.2）
- 不限制 spec 被 supersede 的路径（另起新 spec + 老 spec 标 Superseded 仍是允许的）

## §7 "不做清单" 类别分发 (G-D v1.1)

G-D 之所以有 v1.1 refinement：v1.0 把 3 种结构不同的 "不做" 压成一种
evidence 模板（回归测试 / CI lint），但 constraint-level spec 的 "不做"
通常是**策略性负断言**，无自然回归写法。v1.1 按类型分发。

### §7.1 Cat 1 · Capability Negation（能力否定）

声明 "这段代码不存在 / 这个功能被关闭 / 这条路径被禁止"。

**Evidence 要求**：至少一个 **回归测试 / CI lint / importlinter contract / grep-based CI assertion**，能在 main 分支被破坏时失败。

**举例**：`DIFFERENTIABLE_LAB_SCOPE §2` "主执行链 import 禁入" → `ADR-001 importlinter contract` 在 `.importlinter` 中定义。

### §7.2 Cat 2 · Scope Delegation（范围移交）

声明 "这个关切不由本 spec 承担，属于 spec X"。

**Evidence 要求**（三条全部满足）：
1. 本 spec §9.1 `scope_delegations` 表中每条写明 `item / delegated_to_spec / delegated_to_section / accepting_clause_sha`；
2. **consumer spec 必须在对应 section 显式写入 accepting clause**，格式：
   `"accepts delegation from <this spec>.§<n> · <item>"`；
3. 若 consumer spec 尚为 Draft，accepting clause 可先落在 Draft 版本，但本 spec 的 v1.0 promote commit 必须与 consumer spec 的 accepting clause commit **在同一 PR 或有明确 cross-reference 的连续 PR** 内落地（不允许孤岛承诺）。

**举例**：`VCP §8.2` "不定义 tolerance 数值" → 委托 `METRICS §4` → `METRICS §4` 需写 `"accepts delegation from VCP.§8.2 · tolerance values"`。

### §7.3 Cat 3 · Policy Commitment（策略承诺）

声明 "我们承诺不采用 Y 方向 / 不追求 Z 目标"。本质是治理承诺，无法通过代码层断言。

**Evidence 要求**（三条全部满足）：
1. 在 `docs/governance/POLICY_COMMITMENTS_LEDGER.md` 新增条目，字段：`id / source_spec / source_section / commitment_text / created_at / review_cadence (default: quarterly) / next_review_due`；
2. Ledger 自动纳入 retro 检查清单（在 RETRO-V61-001 的季度 phase-close retro 中强制 audit 所有 due 条目）；
3. commitment 条目在 Decisions DB 关联一条 `DEC-POLICY-*` 作为首次签字依据。

**举例**：`VCP §8.5` "不要求跨 solver apples-to-apples" → Ledger 条目 `POL-VCP-001` + `DEC-POLICY-VCP-001`。

### §7.4 禁止

同一 "不做" 条目**不得跨类别申报** — 必须二选一或三选一，选择理由简短记录在本 spec §9.1 旁注。若某条确实跨类（罕见），**拆成两条写**。

Codex review 在 promote 阶段**必须逐条 challenge** 类别归属——任何用 Cat 2/Cat 3 伪装绕过本应是 Cat 1 的条目 = CHANGES_REQUIRED（详见 `docs/governance/CODEX_REVIEW_RUBRIC.md`）。

---

## §8 Appendix · Schema 样例

### §8.1 `scope_delegations` (Cat 2)

在 consumer spec 的 §9.1 使用：

```yaml
scope_delegations:
  - item: "tolerance 数值"
    category: 2
    delegated_to_spec: METRICS_AND_TRUST_GATES
    delegated_to_section: "§4 Tolerance Policy"
    accepting_clause_sha: <commit SHA of consumer spec edit that landed accepting clause>
    accepting_clause_text: "accepts delegation from VCP.§8.2 · tolerance values"
```

### §8.2 POLICY_COMMITMENTS_LEDGER entry (Cat 3)

```yaml
- id: POL-VCP-001
  source_spec: VERSION_COMPATIBILITY_POLICY
  source_section: "§8.5 不要求跨 solver apples-to-apples"
  commitment_text: "跨 solver 数值对比默认不做 apples-to-apples，除非架构层显式放行"
  created_at: "2026-04-24"
  review_cadence: quarterly
  next_review_due: "2026-07-24"
  decision_ref: DEC-POLICY-VCP-001
```

---

## §9 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v1.0 | 2026-04-24 | Claude Code + Opus 4.7 Gate | 首发，承接 Pivot Post-Hoc Review §2 裁决 |
| v1.1 | 2026-04-24 | Opus 4.7 Gate (Option X) · Claude Code commit | G-D refined per first-usage evidence from VCP rc2. Splits "不做" items into 3 categories with differentiated evidence bars. Triggered under RETRO-V61-001 rule #3 (CHANGES_REQUIRED). Gate refinement itself is mini-retro-compliant (evidence-first, single DEC = `DEC-PIVOT-GATE-001`, reviewer = signing authority Opus 4.7). Structural invariants preserved: other 5 gates (A/B/C/E/F) unchanged; AND logic preserved.|

---

**相关 Governance 文件**：
- [Pivot Charter 2026-04-22](https://www.notion.so/Pivot-Charter-2026-04-22-CFD-Harness-OS-70e55a0c3f924736b0cb68add01d90cd) (Notion SSOT)
- `docs/governance/PIVOT_CHARTER_2026_04_22.md` §4.3a Foundation-Freeze 冻结语义细则
- `docs/adr/ADR-001-four-plane-import-enforcement.md` 四层 import 强制机制
- `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` RETRO-V61-001
