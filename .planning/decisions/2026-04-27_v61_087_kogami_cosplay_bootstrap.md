---
decision_id: DEC-V61-087
title: Kogami-Claude-cosplay 战略审查 sub-agent bootstrap · 三层职责分离 · v6.1 → v6.2 governance 演进
status: Proposed (2026-04-27 · awaiting Codex review on design before implementation · max 3 review rounds per design-dispute convergence rule)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-27
authored_under: governance evolution session post-DEC-V61-075 closure (P2-T2 docker_openfoam substantialization complete · counter at 52)
parent_dec:
  - RETRO-V61-001 (counter rules · Codex risk-tier triggers · self-pass-rate honesty principle · post-R3 defect handling)
  - DEC-V61-073 (governance closure framework · §10.5 sampling audit · §11 anti-drift rules · 4 PCs framework)
  - DEC-V61-085 (Pivot Charter §4.7 CLASS-1/2/3 framework · CFDJerry-pending ratification)
parent_specs: []  # this DEC creates new governance contract; no upstream code spec
autonomous_governance: true
autonomous_governance_counter_v61: 53
autonomous_governance_counter_v61_provenance: |
  STATE.md last_updated 2026-04-27T00:30 records counter 51 → 52 at V61-075 closeout.
  Between V61-075 (counter 52) and this DEC, no autonomous_governance: true DECs have landed.
  Per Interpretation B (STATE.md = SSOT, established by V61-086 provenance precedent),
  this DEC advances 52 → 53.

  Strict-bookkeeping Interpretation A would also yield 53 in this case (no intermediate
  silent advances since V61-075), so both interpretations agree here. Recording 53.
external_gate_self_estimated_pass_rate: 0.55
external_gate_self_estimated_pass_rate_rationale: |
  Honest-low estimate. The dominant unknown is Q1 (Claude Code Task tool context-isolation
  feasibility) — if Task tool prompts inherit ANY parent-session priors (system prompt,
  cached context), the entire context-isolation contract in §3 collapses and the design
  must be re-architected. Q2-Q4 are lower-risk verification problems.

  Self-pass-rate ≤ 70% therefore mandates pre-merge Codex review per RETRO-V61-001 honesty
  principle. This is consistent with the "design-stage proposal" nature of this DEC —
  Codex reviews the design BEFORE implementation, not after.
codex_invocation_required: true
codex_invocation_rationale: |
  Trigger evaluation against RETRO-V61-001 risk-tier-driven Codex baseline (expanded
  triggers from RETRO-V61-001 itself):

  - Multi-file frontend changes? NO (zero JS/HTML/CSS/TSX in this DEC; deferred to impl).
  - API contract changes? NO directly (briefing script is internal tool).
  - OpenFOAM solver fix? NO.
  - foam_agent_adapter.py >5 LOC? NO.
  - New CFD geometry generator? NO.
  - Phase E2E batch ≥3 case failure? NO.
  - Docker + OpenFOAM joint debug? NO.
  - GSD/UI/UX change? NO directly (governance, not user-facing).
  - Security-sensitive operator endpoint? NO directly, but governance-sensitive: a flawed
    review chain design propagates to every future review.
  - Byte-reproducibility-sensitive path? NO (briefing manifest hash is new, not modifying
    existing canonical bytes).
  - Cross-≥3-file API schema rename? NO.

  However, this DEC introduces a NEW AUTONOMOUS REVIEW ROLE in the governance chain.
  By the SPIRIT of RETRO-V61-001 expanded triggers (security-sensitive operator paths,
  byte-reproducibility paths, cross-file schema rename — all "high-impact change with
  non-obvious failure modes"), this design qualifies. Combined with self-pass-rate 0.55
  (≤ 70% honesty principle threshold), pre-merge Codex review is mandatory.

  Codex review scope: review THIS DEC document as a design specification. Specifically
  verify (a) §3 context-isolation contract feasibility, (b) §5 counter rules consistency
  with RETRO-V61-001, (c) §4 trigger rules completeness vs. existing Codex triggers, and
  (d) Open Questions Q1-Q4 are answerable within Acceptance Criteria.
codex_max_rounds: 3
codex_max_rounds_rationale: |
  Design-level disputes that don't converge in 3 Codex rounds indicate a root design
  problem, not a patch space. If R3 still returns CHANGES_REQUIRED on substantive
  (not nit-pick) findings, this DEC reverts to user discussion — do NOT iterate to R4+.
  Contrast with V61-075 implementation DEC which ran R1-R5: implementation has more
  patch surface than design.
codex_tool_report_path: |
  reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r{N}.md (R1 mandatory; R2-R3
  conditional on CHANGES_REQUIRED).
notion_sync_status: pending (will sync after Status=Accepted)
session_summary_notion_url: pending
---

# DEC-V61-087 · Kogami-Claude-cosplay 战略审查 sub-agent bootstrap

## Why

### 当前 governance 链条的结构与摩擦

v6.1 体系下，project 决策评审分布在三个上下文：

| 角色 | 模型 | session 关系 | 主要价值 |
|---|---|---|---|
| Claude Code CLI | Opus 4.7 1M context | 主开发 session | 代码访问 + 工具调度 + 实现执行 |
| Notion @Opus 4.7 | Opus 4.7 (独立 session) | 与 CLI 独立上下文 | 战略审查、roadmap 复盘、ADR 仲裁 |
| Codex GPT-5.4 | 不同模型/不同训练 | 独立 CLI session | 代码层盲点审查 |

Notion @Opus 4.7 的核心价值（per RETRO-V61-001 §"Codex 经济"小节论证）来自其
**独立 session、独立工具、不被主 session narrative 污染**的属性 —— 这与 Codex
独立性是同一机制，只是 Codex 在代码层、Notion-Opus 在战略层。

但实际运行中暴露三个摩擦：

1. **异步 round-trip 慢**：Notion-Opus 每次审查需要手动同步 DEC + 上下文 → 等待响应 → 回填到 git。一次完整审查 cycle 约 30-60 分钟。
2. **工具能力不对称**：Notion-Opus 无法直接 `grep` 仓库、`git log` 历史、跑 `pytest`，只能基于人类粘贴的文本片段判断。
3. **可追溯性依赖手动同步**：DEC frontmatter `notion_sync_status` 字段的"signed"约定要靠人记得回填，断链风险持续存在。

### 替换方案的设计目标

**不是**简单地把 Notion-Opus 搬到 Claude Code 内。简单 sub-agent 会失去
"独立性"这个核心价值，退化为"Claude 自审"，等价于 RETRO-V61-001 已经反复验证
为不可靠的反模式（Claude 的 self-review = framing 污染 = 系统性盲点）。

**是**在 Claude Code 内构造一个**严格 context-isolated** 的审查角色（Kogami-Claude-cosplay），通过：

- 输入限定为 git canonical artifacts（不含主 session transcript / Codex log / working notes）
- 输入哈希可复现（相同输入 → 相同 briefing → 不同时间审查可以对比）
- 调用方式为 `Task` tool 的 fresh prompt（不继承父 conversation）

来在 Claude Code 内**模拟** Notion-Opus 的"看不到我心智活动"属性，同时保留 CLI 的工具优势。

Codex 的盲点审查机制完全不动 —— 不同模型 + 不同训练这个独立性来源在 sub-agent 路径上无法替代。

## Decision

### §1 三层职责架构

| 层 | 角色 | 输入 | 输出 | 触发 cadence | counter 计入 |
|---|---|---|---|---|---|
| 战略 | Kogami-cosplay | git canonical artifacts (隔离 briefing) | `.planning/reviews/kogami/<topic>_<date>.md` | phase-close / retro / high-risk PR final / arc-size retro | advisory = N/A |
| 代码 | Codex GPT-5.4 | PR diff + 修改文件 | `reports/codex_tool_reports/*.md` | RETRO-V61-001 risk-tier triggers (不变) | 不计入 |
| 归档 | Notion (write-only from Kogami) | git canonical artifacts (via 现有 sync) | Notion Decisions/Sessions/Reviews DB pages | DEC landing + post-incident retro (现有节奏) | 不计入 |

**关键边界**：
- Codex APPROVE + Kogami CHANGES_REQUIRED → **不能 merge**（双必要）
- Kogami APPROVE + Codex CHANGES_REQUIRED → 不能 merge（Codex 仍在前）
- Kogami 不读代码层细节（不审 diff），不重复 Codex 的工作
- Notion 不再承担 active review 角色，但保留 archive + audit 能力

### §2 7 产物清单

| # | 产物 | 路径 | 估计 LOC | Wave |
|---|---|---|---|---|
| P-1 | Kogami agent 定义 | `.claude/agents/kogami-claude-cosplay.md` | ~80 | W1 |
| P-2 | briefing 打包脚本 | `scripts/governance/kogami_brief.py` | ~150 | W1 |
| P-3 | review 目录约定 | `.planning/reviews/kogami/README.md` | ~40 | W1 |
| P-4 | 触发器规则文档 | `.planning/methodology/kogami_triggers.md` | ~60 | W2 |
| P-5 | counter 规则增补 | RETRO-V61-001 addendum 或 `.planning/methodology/kogami_counter_rules.md` | ~40 | W2 |
| P-6 | CLAUDE.md 段落 | `~/.claude/CLAUDE.md` (用户级) + 项目 `CLAUDE.md` (新增 §) | ~30 | W3 |
| P-7 | 本 DEC | `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md` | ~280（本文件） | W4 |

总估计：~680 LOC（多数为文档）+ 1 dry-run 验证产物

### §3 context-isolation 契约（设计的 load-bearing 假设）

#### §3.1 briefing 输入白名单（**只能**读这些）

- `.planning/PROJECT.md`（如存在）
- `.planning/ROADMAP.md`
- `.planning/STATE.md` —— frontmatter parse + body 摘要（≤500 tokens）
- 当前待审 artifact（DEC 文件 / RETRO 草稿 / PR diff）—— 完整内容
- 最近 N=5 份 DEC 的 `## Why` + `## Decision` 区段（不含 Codex round 细节、不含 frontmatter）
- 当前 milestone 内所有 RETRO 文件（完整）
- `.planning/methodology/*.md` 中标记为 Active 的章节

#### §3.2 briefing 输入黑名单（**禁止**访问）

- 主 session 的对话 transcript（无论形式 — 不能通过 prompt 注入、不能通过文件引用）
- `reports/codex_tool_reports/**`（避免 Codex framing 污染 Kogami 独立判断）
- `.planning/notes/**`、`.planning/handoffs/**`（working memory，非 canonical）
- `.planning/sessions/**`（session 临时记录）
- 任何 `*.draft.md`、`_DRAFT*.md`、`*-CHECKPOINT.json` 文件
- git stash、未 commit 的 working tree 内容
- 环境变量、shell 历史、`~/.claude/projects/*/memory/`

#### §3.3 输入哈希可复现

briefing 脚本输出 `manifest.json`：

```json
{
  "kogami_briefing_version": "1.0",
  "generated_at": "<ISO8601 UTC>",
  "artifact_under_review": {"path": "...", "sha256": "..."},
  "context_files": [
    {"path": ".planning/ROADMAP.md", "sha256": "...", "lines": 187},
    {"path": ".planning/STATE.md", "section": "frontmatter+body_summary", "sha256": "..."},
    ...
  ],
  "manifest_hash": "<sha256 of sorted (path, sha256) tuples>"
}
```

相同 manifest_hash → 相同输入空间 → 不同时间审查可以判定输入是否一致。
manifest 与 review 输出一起 commit 到 `.planning/reviews/kogami/<topic>_<date>/`。

#### §3.4 sub-agent 调用契约

- 通过 `Task` tool 调用，subagent_type = `general-purpose`（或专用 `kogami-cosplay` 如可注册）
- prompt = `.claude/agents/kogami-claude-cosplay.md` 全文 + briefing manifest + 待审 artifact
- 主 session **不传递** conversation history、prior tool results、user messages
- Kogami sub-agent 完成审查后返回 review markdown，主 session 仅做"写文件 + commit"操作（不重新解读、不基于 review 重新做战略判断）

#### §3.5 独立性自检要求

每份 Kogami review 必须包含 `## Independence Self-Check` section，列出：

- 它**没有**访问的资源（按 §3.2 黑名单逐项确认）
- 它**只**访问的输入文件 manifest hash
- 如果 review 内容引用了任何黑名单资源（如"主 session 提到..."、"Codex round 2 说..."），review **作废**，触发设计审查

### §4 触发器规则

#### §4.1 必须触发 Kogami review

| 触发条件 | 时机 | 待审 artifact |
|---|---|---|
| Phase-close（如有 phase-dir 工作） | phase 标记 COMPLETE 之前 | phase CONTEXT.md + PLAN.md + 实施 commits 摘要 |
| RETRO 草稿落 git | pre-Notion-sync | RETRO 草稿文件 |
| high-risk PR 通过 Codex APPROVE | merge 之前 | PR diff + 关联 DEC + Codex 最终 round 报告 |
| counter ≥ 20 时的 arc-size retro | 触发 retro 时 | 跨多 DEC 的弧追溯 |
| autonomous_governance 自身规则变更 | 任何修改 RETRO-V61-001 / 本 DEC 的提议 | 提议 DEC |

#### §4.2 不触发 Kogami review

- 单文件 ≤50 LOC 的 routine commit（trust path per Pivot Charter §4.7 framework）
- Codex 已 APPROVE 的 verbatim-exception 路径（per CLAUDE.md 5 条件）
- docs-only CLASS-1 改动（per V61-086 precedent）
- Kogami 自身 review 输出的 review（防止递归）

#### §4.3 与 Codex 触发的 disambiguation

- Codex 触发 → 看 PR diff（代码正确性是前提）
- Kogami 触发 → 看决策弧（战略适配性、roadmap 一致性）
- 同一 PR 可能两者都触发；**顺序固定**：Codex 先（代码层 gate），Kogami 后（战略层 gate）
- Kogami 不重复 Codex 的代码层发现；如果 Codex 已经标 P-level finding，Kogami 跳过该层，专注战略

### §5 counter 规则增补（与 RETRO-V61-001 兼容性核查见 Q4）

| 行为 | counter 增量 | frontmatter 字段 |
|---|---|---|
| Kogami 自身的 review 行为 | +0 (advisory chain) | 无（review 文件自身是产物） |
| Kogami 批准进入 merge 的决策 | 按该决策的 DEC autonomous_governance 字段计算（不双计） | DEC 增加 `kogami_review_status: APPROVED <date> <review_path>` |
| Kogami spawn 的 sub-agent（UAT/CFD-novice/doc-readability） | +0 (advisory chain) | sub-agent review 落 `.planning/reviews/kogami/spawned/` |
| Kogami 拒绝（CHANGES_REQUIRED） | DEC 不能 Proposed → Accepted | DEC 增加 `kogami_review_status: CHANGES_REQUIRED <date> <review_path>` |
| Kogami review 的存在 | **不**取代 Codex review | Codex 字段不变 |

**关键不变量**：
- Kogami 不引入新的 counter 计数路径（counter 仍然是 RETRO-V61-001 定义的 autonomous_governance: true 计数）
- Kogami 只是为现有 counter 路径增加一个 gate（必要不充分）
- 历史 DEC（V61-001..086）不需要回填 `kogami_review_status` —— Kogami 从 V61-088 开始适用

### §6 Notion 单向同步契约

- Kogami review 输出文件走现有 `.planning → Notion` sync 链路
- Sync 目标：复用现有 Notion Decisions DB（在 DEC 的 review 字段链接 Kogami review URL），或新建 Reviews DB（如现有 schema 不便）
- Kogami briefing 脚本（P-2）**禁止**调用 `mcp__claude_ai_Notion__*` 工具（在 §3.2 黑名单中）—— Kogami 通过 git 看到的就是它能看到的全部
- Notion-Opus-4.7 历史 review 不迁移到 Kogami 体系：保留作为历史归档，Notion-Opus session 资源回收
- 现有 DEC frontmatter 的 `notion_sync_status` 字段语义不变；新增 `kogami_review_status` 字段（独立于 notion_sync）

## Open Questions

实施 Wave 1-3 必须答出 Q1-Q4，作为 Acceptance Criteria 的硬性 evidence。

### Q1: Claude Code Task tool 是否真能做到 context isolation？

**问题**：`Task` tool 调用 sub-agent 时，prompt 是否会附带任何主 session 的隐性上下文（system prompt、cached context、tool result 缓存）？如果会，§3 整个隔离契约失效。

**验证方法**：
1. 写一个 dry-run agent，prompt 显式包含一段虚假"父 session 已经决定选 X"的 framing
2. 在主 session 中先讨论一个完全不同的话题（建立明显的 narrative）
3. 调用 sub-agent 让它独立判断同一话题
4. 如果 sub-agent 的判断偏向"父 session"或"主 session 话题"，说明被污染

**Pass criterion**：sub-agent 输出与主 session narrative 无可观察相关性（sample size = 5 次独立调用）

### Q2: briefing 脚本能否真正 deterministic？

**问题**：STATE.md 的 `last_updated` 字段当前是超长一段话，可能破坏 YAML frontmatter parsing。其他 frontmatter（DEC、RETRO）也可能有非标格式。

**验证方法**：
1. 跑 `python -c "import yaml; yaml.safe_load(open('.planning/STATE.md').read().split('---')[1])"` 看是否能解析
2. 对所有 `.planning/decisions/*.md` 做同样测试
3. 对所有 `.planning/retrospectives/*.md` 做同样测试

**Pass criterion**：所有目标文件 frontmatter 100% safe_load 通过；如有失败，briefing 脚本必须有显式 fallback（如：原文截取，明确标记 unparsed）

### Q3: Notion 单向同步会丢失什么？

**问题**：现有 Notion-Opus-4.7 review 包含 @提及上下文、Notion 评论 thread、user 与 Notion-Opus 的对话回合 —— 这些隐性信息是否在 git 上有等价记录？

**验证方法**：
1. 抽样 5 份历史 Notion-Opus review（最近 3 个月内）
2. 对每份 review，从对应 DEC + RETRO + commit message 中重建相同信息
3. 标记每份 review 中"git 没有等价记录"的信息条目

**Pass criterion**：≤1 份样本有重大信息缺失；如 ≥2 份缺失 → 单向方案需要补偿机制（如：DEC frontmatter 增加 `notion_review_thread_summary` 字段，强制 Kogami review 前由 user 手动摘要历史 Notion 讨论）

### Q4: counter 增补与 RETRO-V61-001 既有规则是否冲突？

**问题**：§5 引入 `kogami_review_status` 字段。该字段是否在 dry-run V61-072..086 的 counter 计算上产生与历史不一致的结果？

**验证方法**：
1. 取 V61-072、V61-074、V61-075、V61-086 四份 DEC
2. 假设它们都通过了（追溯）Kogami review APPROVED
3. 按 §5 规则重算 counter，与 STATE.md 现行记录对比

**Pass criterion**：counter 数值不变（§5 是 advisory layer，不重算 counter）；如果出现 counter 漂移 → §5 规则有 bug，必须修订

## Acceptance Criteria

- [ ] Codex APPROVE on this DEC design (≤3 rounds; if R3 still CHANGES_REQUIRED on substantive findings, revert to user discussion)
- [ ] 7 产物全部 git committed (P-1..P-7)
- [ ] Q1-Q4 全部有 implementation evidence（不仅 prose 答复，要有可验证 artifact：dry-run script、parse log、抽样表格、counter 重算表）
- [ ] 1 次 self-dry-run：用本 DEC 自身作为待审 artifact，让 Kogami review；review 输出落 `.planning/reviews/kogami/dec_v61_087_self_dryrun_<date>.md`；review 必须包含合理的批评点（不能只有 APPROVE 而无内容）
- [ ] 用户级 `~/.claude/CLAUDE.md` "模型分工规则" 段落更新（Kogami 加入三模型架构 → 四角色架构）
- [ ] 项目 `CLAUDE.md` 增补 Kogami 触发硬性规则段落
- [ ] STATE.md counter 推进 52 → 53；`progress.current_arc` 更新
- [ ] DEC 自身 Status: Proposed → Accepted；Notion sync 完成；frontmatter 回填 `notion_sync_status` + `session_summary_notion_url`

## Risks

| ID | 风险 | Mitigation |
|---|---|---|
| R-1 | context-isolation 实际失败 → Kogami 退化为 yes-and 镜子 | §3.5 独立性自检 + Q1 dry-run 强制验证；失败则 abort 整个 DEC |
| R-2 | 触发器频繁 → review 疲劳 → Kogami 输出质量下降 | §4.1 严格白名单不主动扩展；counter ≥ 30 时强制 retro 评估 Kogami 触发频率 |
| R-3 | counter 增补与 RETRO-V61-001 隐性冲突 | Q4 必须先验证；如冲突 → 优先保留 RETRO-V61-001 既有规则，修订 §5 |
| R-4 | Codex ≥3 round 不收敛 → 设计层面争议无法消解 | 严格 max 3 round 上限；R3 仍 CHANGES_REQUIRED 则本 DEC Status=Rejected，回 user 讨论 |
| R-5 | Kogami spawn 的 sub-agent 形成无限链 | §3 限定 Kogami 自身只能 spawn 1 层 sub-agent；sub-agent 不能再 spawn；递归调用在 P-2 briefing 脚本里硬性拒绝 |
| R-6 | briefing 脚本本身被污染（如读到了未声明的环境变量、隐藏 git config） | P-2 脚本必须用 `subprocess.run(env={})` 风格清空环境；CI 测试覆盖"脚本在最小环境下输出可复现" |
| R-7 | Kogami "独立性自检" 被 Kogami 自己绕过（声称没看，其实看了） | manifest hash 是客观证据；review 中如出现黑名单内容关键词，CI 检测器自动 reject |

## Out of Scope

明确**不做**的事，防止 scope creep：

- ❌ 不取代 Codex 代码审查（任何 RETRO-V61-001 risky PR 仍然必须走 Codex）
- ❌ 不自动 merge（Kogami APPROVE 是必要不充分条件；user 仍是最终 merge 决策者）
- ❌ 不取代人类（Kogami 是 advisory，user 仍可一票否决）
- ❌ 不引入新的 Notion DB schema（W1 默认复用现有 Decisions DB；如需新建 Reviews DB 必须独立 DEC）
- ❌ 本 DEC 不实现 Kogami spawn 的具体 sub-agent 类型（UAT、CFD-novice、doc-readability）—— 那是 Kogami acceptance 后的衍生工作，独立 DEC
- ❌ 不回填历史 DEC 的 `kogami_review_status` 字段；Kogami 从 V61-088 开始适用
- ❌ 不修改 Codex 触发规则；RETRO-V61-001 的 risk-tier baseline 完全保留
- ❌ 不引入新的 counter（counter 仍然是 autonomous_governance_counter_v61，不分裂）

## Implementation Plan（Status=Accepted 之后才执行）

| Wave | 产物 | 依赖 | 验证 |
|---|---|---|---|
| W1 | P-1 (agent def) + P-2 (briefing script) + P-3 (review dir README) | Codex APPROVE | Q1 + Q2 dry-run pass |
| W2 | P-4 (triggers doc) + P-5 (counter rules) | W1 complete | Q4 dry-run pass |
| W3 | P-6 (CLAUDE.md 段落) + self-dry-run | W2 complete | Q3 抽样表格 + self-dry-run review 输出合理 |
| W4 | P-7 (本 DEC Status update) + Notion sync | W3 complete | counter 52 → 53 + STATE.md 更新 |

每个 Wave 一次原子 commit；Wave 间由 user 显式 ACK 才进下一个（不 autonomous chain）。

## Process Note

本 DEC 在写入时未走 `/gsd-discuss-phase` 流程。原因：

- 项目 governance 的实际载体是 `.planning/decisions/` (86 份 DEC)，不是 `.planning/phases/` (仅 2 个 phase-dir)
- `/gsd-discuss-phase` 协议要求 phase 存在于 ROADMAP.md，但 ROADMAP.md 当前 main-line 是 workbench-closed-loop M1-M4 (COMPLETE)，没有 governance 类 phase
- 本次 user 在主 session 显式选择 "Path 2 — DEC-driven mode"（替代 Path 1 GSD discuss-phase）
- DEC 本身充当 design 文档，下游不进 `/gsd-plan-phase`；Implementation Plan §W1-W4 是 plan 等价物

如果项目未来全面采用 GSD phase-dir 模式，应另起 DEC 重构本流程。

---

**End of DEC-V61-087 design draft. Awaiting Codex review.**
