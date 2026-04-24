# UI_SCRIPTS_BOUNDARY — `ui/**` 与 `scripts/**` 的治理边界

**Status**: Active
**Effective**: 2026-04-24
**Authority**: Accepting clause for `VERSION_COMPATIBILITY_POLICY §8.4` (Cat 2 Scope Delegation)
**Consumer of**: SPEC_PROMOTION_GATE.md §7.2

---

## 接受条款 (Accepting Clauses)

This file **accepts delegation from VERSION_COMPATIBILITY_POLICY §8.4 · `ui/**` 和 `scripts/**` 的版本策略**.

Scope taken by this document:
- 定义 `ui/**` 和 `scripts/**` 的**版本元数据规则**（是否要求四元组 / 何时需要 / 如何审计）
- **不**再往 VERSION_COMPATIBILITY_POLICY 回扔这些规则

---

## §1 `ui/**` 边界

### §1.1 版本元数据要求

`ui/backend/**` (FastAPI orchestrator) 和 `ui/frontend/**` (React/TS) **不**要求自身携带 VERSION_COMPATIBILITY_POLICY §2 的四元组。原因：
- UI 是 Control Plane 的 presentation layer，不产出 solver artefacts
- UI 消费 Execution/Evaluation/Knowledge 产物，这些产物自己带四元组
- `package.json` 的 `version` + `git rev-parse HEAD` 足够 UI 自我标识

### §1.2 版本 drift 处置

UI 从后端 API 收到的数据如带不一致四元组 → UI **不**自己做 drift check（属于 Evaluation Plane 的 TrustGate 职责）。UI 的职责是**忠实显示** verdict + drift flag，不做决策。

### §1.3 四层架构归属

`ui/backend/**` 归 **Control Plane 的 HTTP-edge subplane**（非 canonical 四层）。`ui/frontend/**` 是 **presentation**，不在四层 import contract scope 内。ADR-001 §3.2 排除 `ui.*` 是 **正式** exclusion，由本文件承接。

## §2 `scripts/**` 边界

### §2.1 版本元数据要求

`scripts/**` 分三类：
- **operational scripts**（`scripts/phase5_audit_run.py` 等产 artefact 的脚本）：**必须**在产出 artefact 中嵌入四元组（按 VCP §2.2 mapping 到对应 object 的 owner plane location）。但脚本文件本身无需声明版本
- **validator scripts**（`scripts/validate_gold_standards.py` 等纯校验脚本）：无版本元数据要求，靠 `scripts/<name>.py --version` CLI 输出 + git-sha 审计
- **one-shot migration scripts**（`scripts/migrate_*.py`）：必须在 script 顶部 docstring 声明 `source_schema_version` + `target_schema_version` + `landed_at_commit`

### §2.2 版本 drift 处置

脚本执行时**必须**对输入的版本四元组做 drift check（调用 P1-T1 之后的 `check_drift()` helper）。drift `HARD_FAIL` 时脚本 exit 1 并不产出 artefact；`WARN` 允许产出并在 stdout 标红。

### §2.3 四层架构归属

`scripts/**` 归**哪个 plane 取决于脚本的作用**：
- `scripts/phase5_audit_run.py` 是 Control Plane dispatcher（编排 execution + evaluation）
- `scripts/validate_gold_standards.py` 是 Knowledge Plane validator
- `scripts/generate_*.py` report 脚本是 Evaluation Plane

ADR-001 §3.2 将 `scripts.*` 排除 v1.0 contract scope 的理由是**脚本归属按 case 判断**，不适合一条通用规则。本文件只定义 boundary；具体归属在脚本开发时由作者在 docstring 声明。

## §3 未来硬化

本文件是 **Cat 2 accepting clause**，**不是** hard CI lint。若将来需要强制
执行（例如 "UI 产出的 API response 必须带 four-tuple"），需要：
1. 开 `DEC-PIVOT-P?-UI-*` 裁决
2. 实现 lint script + CI workflow
3. 更新本文件 §1/§2 从 "要求" 升为 "CI 强制"

## §4 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v1.0 | 2026-04-24 | Claude Code · Opus Gate Option X | 首发，承接 VCP §8.4 Cat 2 Scope Delegation |
