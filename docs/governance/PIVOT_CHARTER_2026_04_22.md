# PIVOT_CHARTER_2026_04_22 — Repo-side addendum

**Status**: Active v1.0-pivot
**Effective**: 2026-04-22 (§ main charter) · 2026-04-24 (§4.3a 本文件新增)
**Authority**: 首席架构官 Opus 4.7
**Notion SSOT**: <https://www.notion.so/Pivot-Charter-2026-04-22-CFD-Harness-OS-70e55a0c3f924736b0cb68add01d90cd>

---

## §0 这个文件的定位

Pivot Charter 的 SSOT 在 Notion。本文件是 repo 侧的**局部权威**——只
承载 §4.3a "冻结语义细则"，因为这一条直接决定 repo 中哪些 commit 被
允许、哪些必须开 Gate。repo tooling（pre-commit / CI / DEC intake
gate）需要本地可解析的文本做断言，不能每次都打 Notion API。

本文件与 Notion 冲突时：
- 对 §4.3a（冻结语义） → 以本文件为准（因为这是工程执行面）
- 对 §1-§4.3 / §5-§9（愿景、架构、路线图、角色） → 以 Notion 为准

任何对 §4.3a 的修订都必须在 Notion Charter 里同步追加 "repo-side
pointer" 链接到本文件最新 commit。

## §4.3a 冻结语义细则（新增 · 2026-04-24）

承接 Opus 4.7 Pivot Post-Hoc Review §1 裁决（ADJUST — 必须细化）。

Foundation-Freeze 的约束原文（§4.3）是"P1 完工前不新增 Gold Standard
case；15-case Whitelist 是当前天花板"。"新增" 的语义必须细化，否则
"我们只是 refine" 的口径会在一周内把约束架空。

### (a) 严禁行为（HARD NO）

W1 §4.3a 生效起，任何 commit / DEC / Notion 操作**不得**做以下事项
（违反 = Opus Gate 硬底板 2 级别，需独立 Gate 签字才能 revert）：

1. **新 case_id 进入 Whitelist**
   - `knowledge/whitelist.yaml` 的 `cases[].id` 列表**行数不增**
   - 15 个天花板 = 当前实际 10 个 case + 5 slot 保留（P1 完工前不填）

2. **现有 case 的 case_type 升级**
   - Type II (demonstration-grade) → Type I (authoritative) 升级 HARD NO
   - Type III (alias) → Type I/II 升级 HARD NO
   - 升级 = 必须开新 DEC + 新 intake + 新 Gate（按 DEC-V61-053 F1-M1
     Stage 0 intake template §methodology v2.0）— P1 之后再做

3. **新增 primary scalar gate**
   - 任何 case 的 `audit_real_run_measurement.yaml` 的
     `primary_scalar_gates[]` 数组**不得新增元素**
   - 收紧已有 gate 的 tolerance（见 (b)）允许，但不得新增 quantity

### (b) 允许行为（OK · 单 commit 自签即可）

以下行为继续按现有 autonomous_governance / Codex-per-risky-PR 规则
运作，不触发 Foundation-Freeze 审查：

1. **bug fix** — 任何已存在 extractor / comparator / adapter 的 bug 修复
2. **extractor 修复** — 包含新增 fail-soft guard、cache bug、numerical-
   stability patch
3. **文档完善** — README / spec / governance / ADR / RETRO / DEC docs
4. **已有 gate 的 tolerance 收紧** — e.g. 5% → 3%（OK）；**放宽不允许**。
   **防绕过尾句 (Opus 追签 AC-1 · 2026-04-25)**：若 tolerance 收紧
   导致任一已 close case 的 verdict 翻转 (PASS → FAIL 或 PASS_WITH_
   DEVIATIONS → FAIL)，**自动升格为 (c) 灰区**需开 Gate。提交 PR 前
   必须 re-run 当前 fixture 的 comparator 并在 commit message 记录
   0 verdict 翻转；否则 Codex review + Opus Gate 介入。
5. **preflight 脚本加固** — 任何 `scripts/preflight_*.py` 加检查项
6. **UI / 前端 改动** — 不涉及 Whitelist / case_type / gate 语义时均允许
7. **测试补漏** — 新增 test case 不算新 case_id（测试 ≠ benchmark case）
8. **CI / Governance tooling** — import-linter / GitHub Actions / retro / Gate docs

### (c) 灰区（需开 Gate）

以下行为属于模糊地带，必须开 DEC + Opus 4.7 Gate 裁决（autonomous
governance 不足以放行）：

1. **已 close 的 DEC 追补 round N+1**
   - 例：DEC-V61-050 已在 R4 APPROVE clean-close。后续若发现新缺陷，
     开 round 5 属于灰区
   - 规则：按 F1-M2 两档门
     - 如果新 round 仅修 accessor-level / attribute-dereference bug
       且 ≤20 LOC → 允许 (autonomous)
     - 如果涉及任何 (a) 列禁行为 → HARD NO，必须开新 DEC
2. **extractor 参数的语义改动** — e.g. 给 streamfunction 从 trapezoidal
   换成 Poisson 解算器（算法级变更，非 bug fix）。
   **(b) 「extractor 修复」vs (c) 此条的 test-based 判定线 (Opus 追签
   AC-2 · 2026-04-25)**：对同一 fixture 跑修改前后的 comparator，
   观察 **primary_scalar deviation delta**：
   `|Δdeviation| ≤ max(0.1%, 10% × primary_scalar tolerance)` 则视为 
   (b) extractor 修复（autonomous）；否则属 (c) 算法级改动，需开 Gate。
   commit message 附 pre/post deviation 值 + delta 比较。
3. **Knowledge schema 向前兼容的扩字段** — 例如给 observable 加可选的
   `confidence_interval` — 读 P0 KNOWLEDGE_OBJECT_MODEL 的 v0.1 → v1.0
   进度判定；KNOWLEDGE 未 Active 前一律 HARD NO

### (d) Collateral · In-flight 豁免

- **DEC-V61-053** (cylinder Type I multi-dim, IN_PROGRESS_DEMONSTRATION_GRADE)
  的 D6-D8 扩展在 Pivot 当日 2026-04-22 已是 in-flight，**豁免追溯**。
  当前 Task #59 的最终 close（live OpenFOAM run → fixture 回填 → attestation
  ATTEST_PASS）不受 §4.3a 约束。
- **在本文件 (W1) 生效之前**，不得开 DEC-V61-054+ 任何新 multi-dim
  扩张；之后按 (a)/(b)/(c) 规则。

### (e) 解锁条件

P1 Active 完工 + Opus Gate 签字 Foundation-Freeze Done 后，Whitelist
天花板可按 Pivot Charter §7 下一步路线图决定是否解锁。§4.3a (a) 的
硬禁不会自动失效；需要 Opus Gate 显式签字解禁，并更新本文件 §4.3a
状态为 "Lifted by <DEC-PIVOT-P1-XXX>"。

## §5 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v1.0-pivot | 2026-04-22 | 首席架构官 Opus 4.7 | Pivot Charter 主体签发（Notion SSOT） |
| v1.0-pivot-repo-addendum | 2026-04-24 | Claude Code + Opus 4.7 Gate | §4.3a 冻结语义细则落 repo，本文件创建 |

---

**相关 Governance 文件**：
- `docs/specs/SPEC_PROMOTION_GATE.md` — 6 spec Draft → Active 审查标准
- `docs/adr/ADR-001-four-plane-import-enforcement.md` — 四层 import 强制
- `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` §Addendum 2026-04-24 — 5th retro trigger
- `.planning/retrospectives/2026-04-24_retro_v61_053_python_parity.md` — post-R3 live-run defect 方法论 addendum
