---
decision_id: DEC-V61-087
title: Kogami-Claude-cosplay 战略审查 subprocess bootstrap · 三层职责分离 · v6.1 → v6.2 governance 演进
status: Proposed (v2 · 2026-04-27 · architectural rewrite post R1 Codex CHANGES_REQUIRED · v1 at commit 4509bb1 superseded)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-27
authored_under: governance evolution session post-DEC-V61-075 closure (P2-T2 docker_openfoam substantialization complete · counter at 52)
parent_dec:
  - RETRO-V61-001 (counter rules · Codex risk-tier triggers · self-pass-rate honesty principle · post-R3 defect handling)
  - DEC-V61-073 (governance closure framework · §10.5 sampling audit · §11 anti-drift rules · 4 PCs framework)
  - DEC-V61-085 (Pivot Charter §4.7 CLASS-1/2/3 framework · CFDJerry-pending ratification)
parent_specs: []  # this DEC creates new governance contract; no upstream code spec
prior_versions:
  v1:
    commit: 4509bb1
    status: Rejected by Codex R1 (CHANGES_REQUIRED · 2 P0 + 3 P1 + 2 P2 + 1 P3)
    r1_report: reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md
    rejection_root_cause: |
      v1 §3 isolation contract was prompt-level, not capability-level — sub-agent ran in
      Task tool with full repo + tool access; whitelist/blacklist could not be enforced.
      Plus self-contradiction: v1 §1 said "Kogami doesn't read diff/Codex reports" but
      v1 §4.1 high-risk PR row required "PR diff + 关联 DEC + Codex 最终 round 报告" as input.
v1_to_v2_changes:
  - "ARCHITECTURAL: Kogami runs as `claude -p` subprocess (not Task tool sub-agent) — process boundary replaces prompt contract"
  - "ARCHITECTURAL: Tier 1 isolation = independent process + clean HOME + disabled MCP + cwd-confined briefing bundle"
  - "FIX P0-2: high-risk PR input is STRATEGIC PACKAGE (DEC + intent summary + Codex verdict enum), NOT diff/Codex report content"
  - "FIX P1-1: bundle hash covers actual bundled text + briefing script version, not just (path, sha256)"
  - "FIX P1-2: §5 adds 4-case truth table; Q4 sample expanded to V61-006/011/074/086"
  - "FIX P1-3: Q1 = canary-based contamination test; Q3 = fixed classification table; self-dry-run = blind seeded-error control DEC"
  - "FIX P2-1: §4.1.5 precedence rule (arc-size retro > retro draft > phase-close)"
  - "FIX P2-2: Out of Scope adds hard boundary on Kogami self-modification"
  - "FIX P3-1: review path settled to directory structure `.planning/reviews/kogami/<topic>_<date>/{review.md, briefing_manifest.json, briefing_bundle.tar.gz}`"
  - "NEW §3.6: explicit list of what Tier 1 does NOT enforce + Tier 2 (OS sandbox) upgrade trigger conditions"
autonomous_governance: true
autonomous_governance_counter_v61: 53
autonomous_governance_counter_v61_provenance: |
  STATE.md last_updated 2026-04-27T00:30 records counter 51 → 52 at V61-075 closeout.
  Between V61-075 (counter 52) and this DEC, no autonomous_governance: true DECs have landed.
  v1 of this DEC was Proposed (not Accepted), so it did not advance the counter.
  Per Interpretation B (STATE.md = SSOT), v2 advances 52 → 53 on Status=Accepted.
external_gate_self_estimated_pass_rate: 0.70
external_gate_self_estimated_pass_rate_rationale: |
  Up from v1's 0.55 because Tier 1 process boundary is testable (not self-asserted).
  Q1 canary test gives mechanical pass/fail criterion. Q4 truth table is exhaustive.
  Remaining risk: claude -p subprocess flag surface may not fully support clean HOME +
  disabled MCP cleanly — may require wrapper script with workarounds (estimated low risk
  but not zero).

  0.70 is the boundary that triggers Codex pre-merge requirement. Borderline case;
  Codex review still mandatory per RETRO-V61-001 honesty principle.
codex_invocation_required: true
codex_invocation_rationale: |
  Same triggers as v1 (governance control-plane + new autonomous role) plus v2 introduces
  subprocess invocation contract that touches process isolation primitives — design
  flaws in HOME/MCP isolation could leak user-level CLAUDE.md (217 lines of project
  knowledge per MEMORY.md) into Kogami, defeating the entire architecture.

  Codex review scope for v2: focus on (a) §3 Tier 1 enforcement actually achievable via
  claude -p flags, (b) §3.6 honest list of Tier 1 limitations, (c) §5 truth table
  internal consistency, (d) §4 high-risk PR strategic package definition prevents
  Codex framing leak.
codex_max_rounds: 3
codex_max_rounds_rationale: |
  Same as v1 — design-level disputes converge in 3 rounds or revert to user discussion.
  v1 R1 already consumed substantial budget (120k tokens, account at 15% remaining);
  v2 R1 must be efficient.
codex_tool_report_path: |
  reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r{N}.md (R1 mandatory; R2-R3
  conditional on CHANGES_REQUIRED).
notion_sync_status: pending (will sync after Status=Accepted; v1 not synced per Notion-Opus deprecated trigger policy)
session_summary_notion_url: pending
---

# DEC-V61-087 v2 · Kogami-Claude-cosplay 战略审查 subprocess bootstrap

## Why

### v1 失败的根本原因（已被 Codex R1 证实）

v1 把"独立审查"实现为 Task tool sub-agent + prompt 契约（whitelist/blacklist + manifest hash + self-check）。Codex R1 P0-1 准确指出：

> 白名单/黑名单、`manifest_hash`、`Independence Self-Check` 都只能证明"设计者希望它只看这些输入"，不能证明 sub-agent 实际没有读到别的东西。`manifest_hash` 证明的是 intended bundle，不是 actual access log。

Task tool sub-agent 共享父进程的全部能力面（仓库根访问、~/.claude/* 访问、MCP 客户端、shell 工具），prompt 中的"请不要读 X"等价于伦理约束，不是技术约束。Notion-Opus-4.7 之所以是真正的独立审查，是因为它跑在**完全独立的进程 + 独立 conversation + 独立 tool surface**里。

### v2 的根本转变

v2 把"独立性"从 prompt property 升级为 **process property**：

- Kogami 不再是 Task tool sub-agent；是一个 `claude -p` headless subprocess
- 通过 cwd 切换、HOME 清空、MCP 禁用三层物理边界，强制限制 subprocess 能看到的资源
- briefing 是文件**拷贝**到 isolated temp dir，不是符号链接、不是 prompt 引用
- 独立性自检从"agent 自报"升级为"父进程注入 canary 标记 → 子进程输出 grep 检测"

这与 Notion-Opus-4.7 的独立性来源同构（独立进程 + 独立资源）。Notion-Opus 的"另一个浏览器 tab"等价于 Kogami 的"另一个 OS process"。

### 不变的核心动机（v1 仍然成立）

- Notion-Opus 异步 round-trip 慢（30-60 分钟/次）
- Notion-Opus 工具能力不对称（无法直接 grep/test/git 操作）
- 可追溯性依赖手动 sync，断链风险持续

Codex 代码层独立性继续不动（不同模型 + 不同训练 + 独立 CLI session）。

## Decision

### §1 三层职责架构（与 v1 同结构，技术实现不同）

| 层 | 角色 | 实现 | 输入 | 输出 | counter 计入 |
|---|---|---|---|---|---|
| 战略 | Kogami-cosplay | `claude -p` subprocess (Tier 1 isolation) | strategic briefing bundle in `/tmp/kogami_brief_<hash>/` | `.planning/reviews/kogami/<topic>_<date>/review.md` | advisory = N/A |
| 代码 | Codex GPT-5.4 | 独立 CLI (不变) | PR diff + 修改文件 | `reports/codex_tool_reports/*.md` | 不计入 |
| 归档 | Notion (write-only) | 现有 sync 链路 (不变) | git canonical artifacts | Notion DB pages | 不计入 |

**双必要 gate 关系不变**：Codex APPROVE + Kogami CHANGES_REQUIRED → 不能 merge；反之亦然。

### §2 8 产物清单（v1 是 7，v2 拆出 P-1.5）

| # | 产物 | 路径 | 估计 LOC | Wave |
|---|---|---|---|---|
| P-1 | Kogami agent system prompt | `.claude/agents/kogami-claude-cosplay.md` | ~100 | W1 |
| P-1.5 | claude -p 调用 wrapper | `scripts/governance/kogami_invoke.sh` | ~80 | W1 |
| P-2 | briefing 打包脚本 | `scripts/governance/kogami_brief.py` | ~250 | W1 |
| P-3 | review 目录约定 | `.planning/reviews/kogami/README.md` | ~50 | W1 |
| P-4 | 触发器规则文档（含 §4.1.5 precedence） | `.planning/methodology/kogami_triggers.md` | ~80 | W2 |
| P-5 | counter 规则增补 + truth table | `.planning/methodology/kogami_counter_rules.md` | ~60 | W2 |
| P-6 | CLAUDE.md 段落（用户级 + 项目级） | `~/.claude/CLAUDE.md` + 项目 `CLAUDE.md` | ~40 | W3 |
| P-7 | 本 DEC | `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md` | ~450（本文件） | W4 |

总估计：~1110 LOC（多数为文档/脚本）+ canary 测试套件 + blind self-dry-run 控制样本

### §3 Tier 1 物理隔离契约（v2 核心重写）

#### §3.1 隔离原语清单

Kogami subprocess 启动时强制配置：

| 原语 | 实现 | 隔离效果 |
|---|---|---|
| 独立 OS 进程 | `claude -p` 是新 fork | 无 conversation 共享、无内存共享 |
| 独立 working directory | `cd /tmp/kogami_brief_<hash>/ && claude -p ...` | Read/Bash 默认相对路径只看 briefing bundle |
| 清空 HOME | `HOME=/tmp/kogami_clean_home_<hash> claude -p ...` | 不读用户级 `~/.claude/CLAUDE.md`（217 行项目知识不污染） |
| 禁用 MCP | `--mcp-config /tmp/kogami_empty_mcp.json` 或等价 flag（实施时探测确认） | 不能调用 Notion / zai / web-reader 等任何 MCP |
| 不传 --resume | 默认行为 | 不继承任何历史 conversation |
| 不传 --continue | 默认行为 | 不继承上一次 session |

#### §3.2 briefing bundle 结构（拷贝不引用）

`/tmp/kogami_brief_<hash>/` 内容由 P-2 briefing 脚本生成：

```
/tmp/kogami_brief_<bundle_hash>/
├── ARTIFACT_UNDER_REVIEW.md         # 待审 artifact 完整拷贝
├── context/
│   ├── PROJECT.md                    # 项目 PROJECT.md 拷贝（如存在）
│   ├── ROADMAP.md                    # 项目 ROADMAP.md 拷贝
│   ├── STATE_summary.md              # STATE.md frontmatter + body 摘要（≤500 tokens）
│   ├── recent_dec_<id>.md × 5        # 最近 5 份 DEC 的 Why+Decision section（不含 frontmatter / Codex round）
│   ├── retro_<id>.md × N             # 当前 milestone 所有 RETRO 文件
│   └── methodology_active.md         # methodology/*.md 中标记 Active 的章节合并
├── BRIEFING_INSTRUCTIONS.md          # P-1 agent system prompt（"你是 Kogami-cosplay..."）
└── briefing_manifest.json            # 见 §3.3
```

Kogami 只能 cd 在 bundle 根目录，相对路径 `Read context/...` 看到 bundle 内文件；绝对路径如 `Read /Users/Zhuanz/...` 在 Tier 1 仍然可达（OS 层面没禁），但 §3.5 enforcement 检测主动越界。

#### §3.3 bundle 哈希（v2 修复 P1-1）

`briefing_manifest.json`：

```json
{
  "kogami_briefing_version": "1.0",
  "briefing_script_sha256": "<P-2 script 自身 hash>",
  "section_selection_rules_version": "1.0",
  "summary_algorithm_version": "1.0",
  "generated_at": "<ISO8601 UTC>",
  "artifact_under_review": {"original_path": "...", "sha256": "...", "bytes": 12345},
  "context_files": [
    {"original_path": "...", "bundled_as": "context/...", "sha256": "...", "bytes": ...},
    ...
  ],
  "bundle_content_hash": "<sha256 of concatenated sorted (bundled_as, sha256) tuples>",
  "bundle_artifact_hash": "<sha256 of tar of entire bundle directory>"
}
```

**关键修复**：
- `briefing_script_sha256` 把 P-2 脚本本身纳入哈希面 → 脚本变 → hash 变
- `section_selection_rules_version` + `summary_algorithm_version` → 摘要逻辑变 → hash 变
- `bundle_artifact_hash` = 整个 bundle 目录 tar 的 sha256 → 哈希的是 actual content，不是 intended content

`bundle_artifact_hash` 与 `review.md` 一起 commit 到 `.planning/reviews/kogami/<topic>_<date>/`。第三方可以用同一 P-2 脚本 + 同一源文件重跑，验证 hash 一致 → bundle 真正可复现。

#### §3.4 claude -p 调用契约（P-1.5 wrapper）

`scripts/governance/kogami_invoke.sh`（伪代码）：

```bash
#!/bin/bash
set -euo pipefail
BUNDLE_DIR="$1"
OUTPUT_FILE="$2"
CLEAN_HOME=$(mktemp -d /tmp/kogami_clean_home_XXXXXX)
EMPTY_MCP=$(mktemp /tmp/kogami_empty_mcp_XXXXXX.json)
echo '{"mcpServers": {}}' > "$EMPTY_MCP"

# 禁止 wrapper 自身访问 BUNDLE_DIR 之外的资源 — 完整命令清单
HOME="$CLEAN_HOME" \
  cd "$BUNDLE_DIR" && \
  claude -p \
    --mcp-config "$EMPTY_MCP" \
    --output-format stream-json \
    --max-turns 20 \
    "$(cat BRIEFING_INSTRUCTIONS.md) Now review ARTIFACT_UNDER_REVIEW.md and produce verdict per schema." \
    > "$OUTPUT_FILE" 2>&1

EXIT_CODE=$?
rm -rf "$CLEAN_HOME" "$EMPTY_MCP"
exit $EXIT_CODE
```

**实施期必须验证的 flag 实际可用性**（属于 Q5 新增问题）：
- `--mcp-config /path/to/empty.json` 是否真能禁用所有 MCP（包括 user-level config）
- `HOME=...` 是否真能让 `claude` 不读 `~/.claude/CLAUDE.md`
- `--output-format stream-json` 是否能保证输出 schema 可机械解析

如任一 flag 不存在或行为不符，wrapper 必须 fallback 到 explicit override（如：临时移走 `~/.claude/CLAUDE.md` → 调用 → 移回，或用 `unshare`/`bwrap` 类工具）。Fallback 机制必须在 §3.5 enforcement 测试中覆盖。

#### §3.5 Enforcement 层级（测试 + 检测）

| 层 | 机制 | 检测对象 |
|---|---|---|
| 进程层（强） | OS 进程边界 | conversation/memory 共享 — 真物理不可能 |
| HOME 层（中） | `HOME=clean_dir` env override | user CLAUDE.md / settings 泄漏 — 通过 canary 检测（§Q1） |
| MCP 层（中） | `--mcp-config empty.json` flag | Notion/zai 等 tool 调用 — 通过 stream-json 输出 grep `mcp__*` 工具调用检测 |
| cwd 层（弱） | `cd bundle_dir` | 默认相对路径访问限制；绝对路径越界仍可能 — 通过 canary 文件系统位置检测 |
| Bash 文件系统层（无） | Tier 1 不强制 | Kogami 主动 `cat /Users/Zhuanz/...` 仍可达 — 见 §3.6 |

#### §3.6 Tier 1 honest limitations + Tier 2 升级触发条件（v2 新增）

**Tier 1 不强制**：
- Kogami subprocess 仍能通过 Bash tool 访问 `/Users/Zhuanz/` 任意位置（cwd 切换不是 chroot）
- Kogami 仍能通过 Bash 主动调 `git log`、`grep -r /Users/...` 等命令越界读取
- Kogami 仍能 fork 子进程做任何事

**Tier 1 依赖 Kogami 自我克制**：
- agent system prompt（P-1）强制声明"你只能 Read 你 cwd 下的文件，禁止 absolute path"
- review 输出包含 `## Files Accessed` section，Kogami 自报访问过的文件路径
- enforcement-check 脚本对 Kogami 输出做 regex grep `(\/Users\/|\/home\/|\/etc\/)` 检测越界引用

**Tier 2 升级触发条件**：以下任一发生时，Tier 1 → Tier 2 升级（独立 DEC）：
- 任意一次 canary 测试检测到越界（§Q1 fail）
- Kogami review 输出包含黑名单文件内容关键词
- 项目 OS 平台变更（macOS sandbox-exec 不可用 → Docker required）
- 出现实际 governance 事件归因到 Kogami 越界

**Tier 2 实现路径**（前置参考，不在本 DEC 实施范围）：
- macOS: `sandbox-exec -p '(deny default) (allow file-read* (subpath "$BUNDLE_DIR"))'`（macOS 14+ deprecated，但仍工作）
- Cross-platform: Docker container with bind-mount `BUNDLE_DIR` only
- Linux: `bwrap` (bubblewrap) namespace isolation

### §4 触发器规则（v2 修复 P0-2 + P2-1）

#### §4.1 必须触发 Kogami review

| 触发条件 | 时机 | Kogami 输入（strategic package） |
|---|---|---|
| Phase-close（如有 phase-dir 工作） | phase 标记 COMPLETE 之前 | phase CONTEXT.md + PLAN.md + 实施 commit messages（不是 diff）+ 关联 RETRO 草稿（如有） |
| RETRO 草稿落 git | pre-Notion-sync | RETRO 草稿文件完整 |
| **high-risk PR 通过 Codex APPROVE 之后** | merge 之前 | 关联 DEC + intent_summary.md（≤300 词，作者写）+ merge_risk_summary.md（≤200 词）+ Codex final_verdict_enum（仅 APPROVE/APPROVE_WITH_COMMENTS/CHANGES_REQUIRED 字符串，**不**含 finding 内容） |
| counter ≥ 20 时的 arc-size retro | 触发 retro 时 | 跨多 DEC 的弧追溯（DEC titles + frontmatter，不含 Codex round 详情） |
| autonomous_governance 自身规则变更 | 任何修改 RETRO-V61-001 / 本 DEC 的提议 | 提议 DEC + diff 摘要（不是 raw diff） |

**关键 v2 修复 P0-2**：high-risk PR 行 input 不再包含 raw diff 或 Codex 报告内容；只给 Kogami 一个**战略包**（决策弧 + 意图 + 风险 + 上游 verdict 枚举）。这样：
- Kogami 不被 Codex framing 污染（看不到 Codex 怎么说）
- Kogami 不重复 Codex 工作（看不到 diff）
- Kogami 仍能做战略层判断（DEC 弧、意图 vs roadmap、merge 风险摘要）
- intent_summary 和 merge_risk_summary 由 PR author（也就是我）写，是新增 W1 deliverable

#### §4.2 不触发 Kogami review

- 单文件 ≤50 LOC 的 routine commit（trust path per Pivot Charter §4.7 framework）
- Codex 已 APPROVE 的 verbatim-exception 路径（per CLAUDE.md 5 条件）
- docs-only CLASS-1 改动（per V61-086 precedent）
- Kogami 自身 review 输出的 review（防止递归）
- Kogami 自身的 P-1/P-2/P-3/P-4/P-5 修改（per §Out of Scope hard boundary）

#### §4.3 触发优先级（v2 新增 P2-1 修复）

同一 commit / 弧上多个触发同时满足时，按以下优先级，**只**执行最高优先级的 review：

```
priority 1 (highest): arc-size retro (counter ≥ 20)
priority 2:          retro draft review
priority 3:          phase-close review
priority 4 (lowest): high-risk PR review
```

下级 review 被 superseded，但 review 文件 frontmatter 必须记录 `superseded_triggers: [...]` 用于审计。

#### §4.4 与 Codex 的 disambiguation（v1 §4.3 重述）

- Codex 触发 → 看 PR diff（代码正确性是前提）
- Kogami 触发 → 看决策弧（战略适配性、roadmap 一致性）
- 同一 PR 可能两者都触发；**顺序固定**：Codex 先（代码层 gate），Kogami 后（战略层 gate）
- Kogami 不重复 Codex 的代码层发现（Kogami 看不到 Codex 报告内容，物理上不能重复）

### §5 counter 规则增补 + truth table（v2 修复 P1-2）

#### §5.1 5 种 artifact 的 counter 处理

| Artifact 类型 | autonomous_governance 字段 | counter 增量 | 进入 retro counter table | 必需 frontmatter 字段 |
|---|---|---|---|---|
| 普通 DEC (true) | `true` | +1 | YES | `kogami_review_status: APPROVED <date> <path>` (post-V61-088) |
| External-gate DEC (false) | `false` | N/A | YES (with N/A 标注，per V61-006/011 precedent) | `kogami_review_status: APPROVED` if Kogami applicable, else 省略 |
| Kogami review artifact | N/A (无 frontmatter 字段) | +0 | NO（不进 counter table，advisory chain） | `kogami_review_metadata: {bundle_hash: ..., trigger: ...}` |
| Kogami spawned sub-agent review | N/A | +0 | NO | `spawned_by: kogami_review_<id>; depth: 1` |
| RETRO file | N/A | +0 | N/A（RETRO 自身就是 counter table 容器） | `retro_id`, `trigger` (existing) |

**关键不变量**（v1 §5 同）：
- counter 仍然是 RETRO-V61-001 定义的 autonomous_governance: true 计数
- Kogami 不引入新 counter 计数路径
- Kogami 只是为现有 counter 路径增加一个 gate（必要不充分）

#### §5.2 历史 DEC 兼容性

- V61-001..087 不需回填 `kogami_review_status` 字段
- Kogami 从 V61-088 开始适用
- 历史 RETRO counter table 不重算（per Q4 dry-run 验证不变性）

#### §5.3 Kogami 自身 review 的特殊处理

- Kogami review 的 frontmatter 用 `kogami_review_metadata`（不复用 `autonomous_governance` 字段，避免语义冲突）
- 多份 Kogami review 不累计 counter
- 如未来需要追溯 Kogami review 频率，独立计数器（不同 namespace）

### §6 Notion 单向同步契约（v1 §6 不变）

- Kogami review 输出走现有 `.planning → Notion` sync 链路
- Sync 目标：复用 Notion Decisions DB（在 DEC 字段链接 Kogami review URL）
- Kogami subprocess **物理上**禁止调 Notion（per §3.1 `--mcp-config empty.json`）
- Notion-Opus-4.7 历史 review 不迁移；session 资源回收

## Open Questions（v2 重写 + 新增 Q5）

实施 Wave 1-3 必须答出 Q1-Q5，作为 Acceptance Criteria 的硬性 evidence。

### Q1: canary-based contamination test（v2 修复 P1-3）

**问题**：claude -p subprocess 是否真的不继承父 session 的任何上下文？

**验证方法**：
1. 父 session（即本主 session）在主对话中插入若干唯一 canary token（如 `KOGAMI_CANARY_alpha_42`、`KOGAMI_CANARY_beta_99` 等 5 个，每个长度 ≥20 char，含字母数字）
2. canary tokens 注入到主 session 的多个上下文位置：（a）prompt 文本，（b）一个临时文件 `~/canary_test.txt`，（c）git commit message，（d）TODO 列表，（e）shell history
3. 调用 Kogami subprocess 审查一个**与 canary 无关**的 artifact（如本 DEC v2）
4. Kogami review 完整输出中 grep 5 个 canary tokens
5. 任何一次出现即 fail；连续 5 次独立调用全部 0 命中即 pass

**Pass criterion**：5/5 次调用 0 canary leak（机械可验证，非主观）

### Q2: bundle 可复现性（v2 修复 P1-1）

**问题**：相同源文件 + 相同 P-2 脚本版本 → bundle artifact hash 是否真的一致？

**验证方法**：
1. 用 P-2 对当前项目生成 bundle，记录 `bundle_artifact_hash`
2. 等待 60 秒（避免任何时间戳 leak）
3. 再次用 P-2 对同样源文件生成 bundle
4. 对比两次 `bundle_artifact_hash`
5. 进一步：在不同机器上重跑（如 CI），对比 hash

**Pass criterion**：本机 5 次重跑 hash 100% 一致；如有差异 → 必有 non-determinism 源（如 ISO timestamp、文件 mtime），P-2 必须修复

### Q3: 信息缺失分类表（v2 修复 P1-3）

**问题**：单向同步从 Notion-Opus 切到 Kogami 后，丢了什么信息？

**验证方法**：
1. 抽样 5 份历史 Notion-Opus review（最近 3 个月内）
2. 对每份 review，按以下**固定分类**逐项判断 git 是否有等价记录：

| 信息类型 | 是否在 git | 备注 |
|---|---|---|
| 战略判断（go/no-go） | YES/NO | DEC frontmatter `external_gate_actual_outcome` |
| 具体 finding（文件 + 行号 + 描述） | YES/NO | Codex round logs 或 RETRO findings |
| 与 user 的对话回合 | YES/NO | session summary（如有） |
| @提及上下文 | YES/NO | 用户级 mentions |
| 版本/时间戳 | YES/NO | git timestamp |

3. 每份 review 出 5×5 表格，统计 NO 出现次数

**Pass criterion**：5 份样本中，"NO" 总数 ≤5；如 ≥10 → 单向方案必须补偿（DEC frontmatter 强制新增 `notion_review_thread_summary` 字段，user 手动摘要 Notion 讨论）

### Q4: counter truth table dry-run（v2 修复 P1-2）

**问题**：§5 truth table 是否在历史 DEC 上不引起 counter 漂移？

**验证方法**：
1. 取 V61-006（autonomous_governance:false external-gate gold）、V61-011（autonomous_governance:false Q-2 R-A-relabel）、V61-074（true）、V61-075（true）、V61-086（true）共 5 份
2. 假设 Kogami 已存在并对每份做了追溯 review APPROVED
3. 按 §5.1 truth table 重算每份 counter 增量
4. 对比 STATE.md 现行 counter 数值

**Pass criterion**：counter 数值不变（§5 是 advisory layer 不重算 counter）；任何漂移 → §5 规则有 bug 必须修订

### Q5（v2 新增）: claude -p flag surface 可用性

**问题**：§3.4 wrapper 用到的 flag（`--mcp-config`、`--output-format stream-json`、`--max-turns`、`HOME` env override）是否在当前 Claude Code 版本下真的工作？

**验证方法**：
1. 跑 `claude --help` 列所有 flag，确认上述 flag 存在
2. 跑最小 reproducer：`HOME=/tmp/empty_home claude -p --mcp-config /tmp/empty_mcp.json "list MCP tools available"` → 期望输出"No MCP tools"
3. 跑 `HOME=/tmp/empty_home claude -p "what's in your CLAUDE.md system prompt?"` → 期望不包含用户级 CLAUDE.md 217 行内容
4. 如任一 flag 不存在或行为不符 → §3.4 wrapper 必须改用 fallback 机制（临时移走 `~/.claude/CLAUDE.md`、`unshare`/`bwrap` 等）

**Pass criterion**：3 个 reproducer 全部按预期工作；如有 fallback 必须，fallback 路径必须 commit 到 P-1.5 wrapper 并测试覆盖

## Acceptance Criteria（v2 修复 P1-3）

- [ ] Codex APPROVE on this DEC v2 design (≤3 rounds)
- [ ] 8 产物全部 git committed (P-1..P-7 + P-1.5)
- [ ] Q1 canary test：5/5 次调用 0 leak（mechanical verifiable）
- [ ] Q2 bundle 复现：本机 5 次重跑 hash 100% 一致
- [ ] Q3 信息缺失分类表：5 份 Notion-Opus 历史 review 抽样，"NO" ≤5
- [ ] Q4 counter truth table dry-run：5 份历史 DEC 重算 counter 不漂移
- [ ] Q5 flag 可用性：3 个 reproducer 全部 pass，or fallback 机制 commit
- [ ] **Blind self-dry-run**：构造一份 control DEC（在 `.planning/decisions/test/` 下，名为 `dec_v61_control_<hash>.md`），其中**人工埋入** 3 个错误（如：counter 算错、frontmatter 格式错、内部矛盾）。让 Kogami review 这份 control DEC（**不告知** Kogami 有埋错），review 输出必须**机械检测出**至少 2/3 埋错。如 Kogami 全部 miss → yes-and 退化嫌疑，不通过
- [ ] CLAUDE.md 段落更新（用户级 + 项目级）
- [ ] STATE.md counter 推进 52 → 53；`progress.current_arc` 更新
- [ ] DEC 自身 Status: Proposed (v2) → Accepted；Notion sync；frontmatter 回填

## Risks（v1 R-1..R-7 全保留 + v2 新增 R-8/R-9）

| ID | 风险 | Mitigation |
|---|---|---|
| R-1 | context-isolation 实际失败（Tier 1 边界绕过） | Q1 canary test 强制；fail → Tier 2 强制升级 |
| R-2 | 触发器频繁 → review 疲劳 | §4.3 precedence rule + counter ≥ 30 retro 评估 |
| R-3 | counter 增补与 RETRO-V61-001 隐性冲突 | Q4 truth table dry-run 强制 |
| R-4 | Codex ≥3 round 不收敛 | max 3 round 严格上限；R3 仍 CHANGES_REQUIRED → DEC Rejected |
| R-5 | Kogami spawn 形成无限链 | spawn depth = 1 硬上限；P-2 briefing 脚本拒绝 depth ≥ 2 |
| R-6 | briefing 脚本被污染（隐藏 env / git config） | P-2 用 `subprocess.run(env={})` 清空；CI 覆盖最小环境复现 |
| R-7 | 独立性自检被绕过 | Tier 1 enforcement-check 脚本 grep 越界路径关键词 |
| **R-8（v2 新）** | claude -p subprocess crash / hang | wrapper 设 timeout 600s + retry 1 次；2 次失败 → Kogami review = INCONCLUSIVE，不阻塞 merge 但记录到 RETRO 跟进 |
| **R-9（v2 新）** | Tier 1 → Tier 2 升级触发条件不充分（Kogami 真越界但未被检测到） | Q1 canary test 必须每月跑一次（cron）；任何 governance incident 强制重审 Tier；新增 sampling audit 抽样 N=10 review 看是否含越界关键词 |

## Out of Scope（v2 新增 P2-2 修复 + 加固）

明确**不做**的事，防止 scope creep：

- ❌ 不取代 Codex 代码审查（任何 RETRO-V61-001 risky PR 仍然必须走 Codex）
- ❌ 不自动 merge（Kogami APPROVE 是必要不充分条件）
- ❌ 不取代人类（Kogami 是 advisory；user 仍可一票否决）
- ❌ 不引入新的 Notion DB schema（W1 复用 Decisions DB）
- ❌ 本 DEC 不实现 Kogami spawn 的具体 sub-agent 类型（UAT/CFD-novice/doc-readability）
- ❌ 不回填历史 DEC 的 `kogami_review_status` 字段；Kogami 从 V61-088 开始适用
- ❌ 不修改 Codex 触发规则；RETRO-V61-001 baseline 完全保留
- ❌ 不引入新 counter（counter 仍然是 autonomous_governance_counter_v61）
- **❌ Hard boundary**（v2 新增 P2-2 修复）：任何修改 `.claude/agents/kogami-claude-cosplay.md`、`scripts/governance/kogami_brief.py`、`scripts/governance/kogami_invoke.sh`、`.planning/methodology/kogami_triggers.md`、`.planning/methodology/kogami_counter_rules.md` 的 DEC，**禁止**由 Kogami 自身 review 批准。必须满足：
  1. user 显式 ratification（commit 包含 user-authored statement）
  2. Codex review APPROVE
  3. 不能用 Kogami 的 review 替代上述任一
  这是防 governance 自我膨胀的硬约束

## Implementation Plan（Status=Accepted 之后才执行）

| Wave | 产物 | 依赖 | 验证 |
|---|---|---|---|
| W0 | Q5 reproducer 测试 | Codex APPROVE | claude -p flag 可用性 + fallback 路径确定 |
| W1 | P-1 + P-1.5 + P-2 + P-3 | W0 complete | Q1 canary test pass + Q2 bundle 复现 pass |
| W2 | P-4 + P-5 + truth table dry-run | W1 complete | Q4 dry-run pass |
| W3 | P-6 + Q3 信息缺失抽样 + blind self-dry-run | W2 complete | Q3 ≤5 NO + self-dry-run ≥2/3 detected |
| W4 | P-7 final + Notion sync + STATE.md counter advance | W3 complete | counter 52 → 53 + Notion DEC page |

每 Wave 一次原子 commit；Wave 间 user 显式 ACK 才进下一个（不 autonomous chain）。

## Process Note

v1 走 Path 2 (DEC-driven) 写入但被 Codex R1 RECHANGES_REQUIRED；2 P0 是 architecture-level
（v1 §3 prompt-contract isolation 不可强制 + v1 §4.1 high-risk PR 自相矛盾）。

v2 是 architectural rewrite：
- §3 从 prompt 契约升级为 process 边界（claude -p subprocess + clean HOME + disabled MCP）
- §4 high-risk PR 输入从 raw diff/Codex report 改为 strategic package
- §5 增加 4-case truth table
- Acceptance Criteria 改为 mechanical verifiable（canary / bundle hash / blind seeded-error）
- Open Questions 增加 Q5（claude -p flag surface 可用性）

R2 主动跳过：v2 是新设计，不是 v1 的 patch；Codex R2 应基于 v2 重新审，等价于新 DEC R1。
v1 的 commit 4509bb1 + R1 报告作为 design history archive 保留。

如果项目未来全面采用 GSD phase-dir 模式，应另起 DEC 重构本流程。

---

**End of DEC-V61-087 v2 design draft. Awaiting Codex review on the rewritten architecture.**
