# DEC-V61-087 R1 Codex Review

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-27
**Round**: R1 (max 3 per DEC self-imposed cap)
**DEC under review**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md` (commit 4509bb1)
**Tokens consumed**: 119,908
**Account used**: picassoer651@gmail.com (15% remaining at session start)

## Verdict

**CHANGES_REQUIRED**

## Summary

这个 DEC 的问题诊断基本成立：Notion-Opus 作为 active review gate 确实慢、弱、难追溯。
但当前替代方案把"独立性"写成了 prompt 契约，而不是 capability boundary；这使得 §3 的核心承诺、§4 的 high-risk PR 路径、§5 的兼容性证明、以及 Acceptance Criteria 一起失稳。

## Findings

### P0 (blocker, design 不能进入实施)

#### P0-1. §3 的 context-isolation 目前不可验证也不可强制执行

**Position**: §3.1-§3.5 (lines 148-202), Risks R-1/R-7 (317-323).

**问题描述**: 白名单/黑名单、`manifest_hash`、`Independence Self-Check` 都只能证明"设计者希望它只看这些输入"，不能证明 sub-agent 实际没有读到别的东西。尤其 §3.4 仍假定它运行在有完整仓库/工具能力的 Task tool 环境里；只要它能读 repo、读隐藏 memory、继承父 session 指令或 runtime priors，§3 的"模拟独立 session"就不成立。`manifest_hash` 证明的是 intended bundle，不是 actual access log。

**建议修订**: 把"隔离"从 prompt 约束改成执行边界。最小可接受方案是：先由脚本生成一个只含 allowlist 文件拷贝的独立 briefing bundle，再让 Kogami 只在该 bundle 上运行，不能见 repo root、session memory、Notion、Codex reports。如果 Claude Code Task tool 做不到这个边界，就不要声称它替代了 independent-context gate。

#### P0-2. high-risk PR 路径自相矛盾，且会直接破坏独立性主张

**Position**: §1 key boundary (127-129), §3.2 blacklist (161), §4.1 high-risk PR row (212), §4.3 (225-228).

**问题描述**: 文中一方面规定 Kogami "不审 diff""不读 `reports/codex_tool_reports/**`"，另一方面 high-risk PR 触发却要求输入 `PR diff + 关联 DEC + Codex 最终 round 报告`。这会同时造成两件事：一是 Kogami 被 Codex framing 污染，二是 Kogami 重复做了本应由 Codex 完成的工作。这个矛盾不解决，§4 的核心触发场景就没有一致实现。

**建议修订**: 二选一。要么维持独立性主张，则 high-risk PR 只给 Kogami 一个"战略包"而不是 diff/report，例如 DEC、变更意图摘要、merge risk summary、最终 verdict enum；要么承认 high-risk PR 路径不是 context-isolated review，而是 secondary advisory check，并把它从 §3 的独立性契约中拆出去。

### P1 (major, 必须修订才能 APPROVE)

#### P1-1. §3.3 的 manifest 哈希不足以证明 deterministic input，Q2 也测错了对象

**Position**: §3.3 (168-187), Q2 (269-279).

**问题描述**: 当前 `manifest_hash` 只哈希 `(path, sha256)`，没有把 briefing 生成逻辑本身纳入证明面，例如 `STATE.md` 的 `body summary ≤500 tokens`、最近 N=5 DEC 的选取顺序、Active 章节抽取规则、summary 算法版本。这样同一个源文件集合可以生成不同 briefing 文本而 `manifest_hash` 不变。Q2 的 `yaml.safe_load` 只能验证 frontmatter 可解析，不能验证 briefing 可复现。

**建议修订**: 哈希 actual bundled input text，而不是原始文件路径集合；把 `kogami_briefing_version`、section-selection rule、summary algorithm/version 一并纳入 hash；最好直接 commit 生成后的 briefing artifact，而不是只 commit `manifest.json`。

#### P1-2. §5/Q4 的 counter 兼容性验证样本过窄，没覆盖 N/A 语义边界

**Position**: §5 (230-243), Q4 (291-300), Acceptance line 310.

**问题描述**: Q4 只用 V61-072/074/075/086 做 dry-run，能测出"autonomous_governance:true 的 DEC 不会因为多一个 `kogami_review_status` 而 double count"，但测不出 RETRO-V61-001 Q5 的核心边界：`autonomous_governance:false` external-gate DEC 必须是 `N/A`，且"review artifact 自身"到底应不应该进 retro counter table。现在文中的 "Kogami advisory = N/A" 和既有 "external-gate DEC = N/A" 还不是一个清晰的机械语义。

**建议修订**: Q4 必须补一个 truth table：`DEC true / DEC false / review artifact / spawned review artifact` 各自是否出现在 counter table、是否增量、允许哪些 frontmatter 字段。样本至少加入 V61-006/V61-011 这类 `autonomous_governance:false` precedent。

#### P1-3. Acceptance Criteria 不能机械检测 yes-and 退化，也不能机械判定信息丢失

**Position**: Q1 (257-267), Q3 (280-289), Acceptance line 307.

**问题描述**: "无可观察相关性""重大信息缺失 ≤1""self-dry-run 必须包含合理批评点"都过于主观。一个被污染的 agent 完全可以给出表面上像批评的内容，仍然通过。尤其用"本 DEC 自身"做 self-dry-run，很容易让模型顺着文中显式 Open Questions 做形式化批评，不足以证明独立性。

**建议修订**: Q1 改成 canary-based contamination test；父 session 注入若干唯一标记，子 agent output 任何一次出现即 fail。Q3 改成固定缺失分类表。self-dry-run 改成"盲测有意埋错的控制样本"，而不是只审这份自带提示词的 DEC。

### P2 (minor, 可接受但建议修订)

#### P2-1. §4 触发器会在同一弧上产生重复审查

**Position**: §4.1 (210-214).

**问题描述**: phase-close、RETRO 草稿、counter≥20 arc-size retro 很容易在同一批 DEC/commit 上连续触发 2-3 次 Kogami review，token 成本会偏高。

**建议修订**: 增加 precedence 规则，例如 "retro draft review supersedes same-arc phase-close review；arc-size retro supersedes both"。

#### P2-2. Out of Scope 没有明确禁止 Kogami 自改自己的 prompt/scope/trigger surface

**Position**: Out of Scope (325-336), §4.1 governance-rule trigger (214).

**问题描述**: 现在只说"governance 规则变更要触发 Kogami review"，但没有禁止 Kogami 去审查它自己的 agent 定义、白黑名单、spawn policy、trigger doc。这会带来 governance 自我膨胀和自我合法化风险。

**建议修订**: 明写 hard boundary：任何修改 `.claude/agents/kogami-claude-cosplay.md`、`kogami_triggers.md`、白黑名单、spawn depth 的 DEC，不能由 Kogami 自身单独批准，至少需要 user ratification + Codex review。

### P3 (nit)

#### P3-1. review 输出路径约定前后不一致

**Position**: §1 table line 122 vs §3.3 line 187.

**问题描述**: 一处写单文件 `.planning/reviews/kogami/<topic>_<date>.md`，另一处写目录 `.planning/reviews/kogami/<topic>_<date>/`。

**建议修订**: 统一成"目录 + review.md + manifest.json"或"单文件 + sibling manifest"，不要混用。

## 整体评估

替换 Notion-Opus-4.7 的动机是成立的，但"异步慢 + 工具弱"只能证明现状有摩擦，不能自动推出"Task tool + cosplay prompt"就等价于独立上下文。当前设计最弱的点正是把独立性从 external property 退化成了 self-asserted property，所以核心论证还站不住。

`self-pass-rate = 0.55` 方向上诚实，不是主要问题；如果一定要挑，Q1 是 existential unknown，因此这个数字没有给设计增加多少安全边际。`max 3 round` 作为 design dispute cap 是合理的，但前提是 R2 必须处理架构问题，不是修措辞。

## 建议下一步

值得做 R2，但前提很明确：R2 必须把 §3 改成"物理/执行边界隔离"，并且重写 high-risk PR 输入契约与 Q1/Q4 验证矩阵。

如果作者坚持保留当前"fresh prompt + self-check = isolation"的主前提，则不建议消耗 R2，应该直接回 user 讨论，因为那时争议已经是 premise-level，不是 patch-level。

---

**Raw codex session log**: `reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.log` (2539 lines, includes tool exec trace + full review)
