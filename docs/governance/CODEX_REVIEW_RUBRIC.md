# CODEX_REVIEW_RUBRIC — Codex independent review 审查义务

**Status**: Active (stub · v1.0)
**Effective**: 2026-04-24
**Authority**: SPEC_PROMOTION_GATE.md §7.4 (禁止跨类别伪装) · CLAUDE.md "Codex-per-risky-PR baseline"

---

## 目的

Codex 在 SPEC_PROMOTION_GATE promote review 中**必须**承担的 challenge
义务。本 rubric 目前是 stub —— 最小可行版本，只固化 G-D 类别伪装
challenge 的规则。未来会扩展覆盖所有 6 门的 review 标准。

## §1 G-D 类别伪装 challenge（MANDATORY）

Codex 在 review promote commit 时，**必须逐条 challenge** 每个 "不做
清单" 条目的类别归属：

### §1.1 Cat 1 vs Cat 2 challenge

Cat 2 "Scope Delegation" 的**合理性检验**：
- 被委托的 consumer spec 是否真的**有能力**承接此项？（举例：不能把"不定义 tolerance 数值"委托给 UI_SCRIPTS_BOUNDARY — tolerance 属于 Evaluation Plane，UI 无能力定义）
- accepting clause 是否**已经 landed**（不是口头承诺）？

若 Cat 2 实际应是 Cat 1（即有自然 lint/test 可写却用 delegation 躲）→ **CHANGES_REQUIRED**。

### §1.2 Cat 2 vs Cat 3 challenge

Cat 3 "Policy Commitment" 的**必要性检验**：
- 是否真的无法委托给任何 consumer spec？若能委托就不该是 Cat 3
- 是否真的无法通过 Cat 1 lint/test 实现？若能实现就不该是 Cat 3

若 Cat 3 实际应是 Cat 2（能委托）或 Cat 1（能 lint）→ **CHANGES_REQUIRED**。

### §1.3 Cross-category 拆分

若同一 "不做" 条目确实跨类（罕见），SPEC_PROMOTION_GATE §7.4 要求**拆成两条写**。Codex 遇到看似合理但跨类的条目 → 要求作者拆分。

## §2 未来扩展

以下 challenge 义务待后续 DEC 细化：
- G-A "Deliverables ≥80% merge" 的 merge 口径（哪些算 "merge"？follow-up DEC 是 open PR 算不算？）
- G-B "端到端冒烟案例" 的**最小覆盖**粒度
- G-C "上下游 cross-ref" 的**对称性**（ref 是双向还是单向？）
- G-F "无 HIGH" 的 HIGH 含义（repo 是否有 severity-scale 文档？）

## §3 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v1.0-stub | 2026-04-24 | Claude Code · Opus Gate Option X V-5 | 首发 stub；只含 G-D 类别伪装 challenge；其他门的 rubric 留给后续 DEC |
