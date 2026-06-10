# cfd-harness-unified · Project CLAUDE.md

> Project-specific Claude Code configuration. Inherits from `~/CLAUDE.md` (user-level).
> See user-level for: 模型分工规则 v2.3 (Kogami opt-in · Codex round cap=3 · DEC scope-driven), Codex 调用规则, Subagent 优先原则.
>
> **Established by DEC-V61-087** (Accepted 2026-04-27); **简化 by DEC-V61-133** (B+ governance simplification, 2026-05-07).

---

## Three-layer governance (v2.3 · 2026-05-07 · DEC-V61-133)

This project uses three review layers, with strategic layer **opt-in** post-V133:

| Layer | Reviewer | Trigger | Output location |
|---|---|---|---|
| **Strategic** (opt-in) | Kogami-Claude-cosplay (`claude -p` subprocess, `--tools ""`) | **User explicitly invokes** when wanting an independent strategic review (auto-triggers废止) | `.planning/reviews/kogami/<topic>_<date>/` |
| **Code** | Codex GPT-5.4 / GPT-5.5 (relay CLI) | per RETRO-V61-001 risk-tier · v2.2 1-sync-trigger (security boundary / auth / signing) · **round cap = 3** per V133 | `reports/codex_tool_reports/` |
| **Archive** | git + GitHub（Notion 已废止 2026-06-10 · DEC-V92-notion-retirement） | DEC landing + post-incident retro | `.planning/decisions/` + `.planning/retrospectives/`（GitHub remote = 人可读门户） |

**v2.3 changes from v6.2**:
- Strategic layer is opt-in only; Codex APPROVE alone is sufficient gate for high-risk PR merge (no longer double-necessary)
- Codex round cap = 3 (R0 + 2 fix iterations); after R3 user ratifies remaining P1 or remaining P2/P3 → retro queue
- User remains final authority (can invoke Kogami any time, or override Codex)

## When to consider invoking Kogami (advisory · not mandatory · per V133)

The auto-trigger conditions from old v6.2 are now examples of **when invoking might be high-value** — not requirements:

- Phase-close arcs (post-merge) where strategic narrative coherence matters
- Charter / governance-rule-change DECs where independent second opinion is desired
- Post-incident retros where blind-spot hypothesis benefits from external eyes
- High-risk PRs after Codex APPROVE when blast radius is large

**To invoke**: `bash scripts/governance/kogami_invoke.sh <artifact> <topic> <trigger>` (unchanged path; only the auto-trigger gate is removed).

**Skip clauses unchanged**:
- Single-file ≤50 LOC routine commit (no Kogami value added)
- Codex APPROVE'd verbatim-exception path
- docs-only CLASS-1 changes
- Kogami review of Kogami review (anti-recursion)
- Modification of Kogami's own files (P-1..P-5) — still requires user + Codex ratification

## Strategic package authoring (high-risk PR only)

Author must produce two YAML files alongside the linked DEC:
- `intent_summary.md` — see DEC-V61-087 §4.4 schema (`roadmap_milestone`, `business_goal`, `affected_subsystems`, optional `rationale`)
- `merge_risk_summary.md` — see DEC §4.4 schema (`risk_class`, `reversibility`, `blast_radius`, optional `rationale`)

Validation: `python3 scripts/governance/validate_strategic_package.py --intent <p> --risk <p>`
Schema-invalid → wrapper exits non-zero → review not triggered → fix schema first.

## Counter rules (per DEC-V61-087 §5 + RETRO-V61-001)

- `autonomous_governance_counter_v61` continues to be the RETRO-V61-001 telemetry counter (pure telemetry · no STOP threshold; arc-size audit metric only)
- 每个 `autonomous_governance: true` 的 DEC **+1**；`autonomous_governance: false` 的 DEC（external gate）**不计入**，但 retro counter 表中标 `N/A` 并列出以呈现完整决策弧
- Kogami review artifacts are **NOT** counted (advisory chain · counter +0)
- Kogami CHANGES_REQUIRED on a DEC blocks the DEC from advancing to Status=Accepted
- Kogami INCONCLUSIVE does NOT block but requires entry in next RETRO; 3+ INCONCLUSIVE within counter ≤5 triggers mini-retro
- Counter Interpretation B (STATE.md `last_updated` = SSOT) is canonical going forward (per W3 Kogami P2-2 finding)

## Tier 1 → Tier 2 escalation

If any of the following occurs, trigger an independent DEC for Tier 2 OS sandbox upgrade:
- Q1 canary regression test fails (`scripts/governance/verify_q1_canary.py`, dependency-triggered: claude CLI version change — runs in wrapper before each Kogami invocation if `claude --version` differs from baseline)
- Anthropic upgrades `claude` CLI and any §3.1 flag combo behavior changes
- Live governance incident attributed to Kogami exceeding isolation
- Q5 keyword sampling shows new content-leak vector (`scripts/governance/verify_q5_keyword_sampling.py`)
- OS platform changes (macOS → Linux requires re-verification)
- P-2.5 sampling audit finds ≥3 paraphrase laundering instances

Tier 2 implementation options (out-of-scope for DEC-V61-087):
- macOS `sandbox-exec -p '(deny default) (allow file-read* (subpath "$BUNDLE_DIR"))'` (deprecated but works)
- Docker container with bind-mount only briefing dir + `ANTHROPIC_API_KEY` injection
- Linux `bwrap` (bubblewrap) namespace isolation

## Files comprising the Kogami workflow (do NOT modify without Codex + user ratification)

- `.claude/agents/kogami-claude-cosplay.md` (P-1: agent system prompt)
- `scripts/governance/kogami_invoke.sh` (P-1.5: claude -p wrapper)
- `scripts/governance/kogami_brief.py` (P-2: briefing prompt builder)
- `scripts/governance/validate_strategic_package.py` (P-2.5: strategic package validator)
- `.planning/reviews/kogami/README.md` (P-3: review directory convention)
- `.planning/methodology/kogami_triggers.md` (P-4: trigger rules)
- `.planning/methodology/kogami_counter_rules.md` (P-5: counter rules)
- `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md` (P-7: this DEC)

## Verification scripts (run on `claude` CLI version change · NO calendar gating)

> Per 项目"禁用日期/调度门控"原则: scripts run on dependency triggers, not timers.
> Q1 canary auto-runs from `kogami_invoke.sh` when `claude --version` differs from `.planning/governance/claude_version_baseline.txt`.

- `python3 scripts/governance/verify_q1_canary.py` — Q1 canary regression test (target: 5/5 zero leaks)
- `python3 scripts/governance/verify_q5_keyword_sampling.py` — Q5 keyword sampling (target: 0 content hits)
- `python3 scripts/governance/verify_q4_counter_truth_table.py` — Q4 counter truth table compatibility (target: 0 drift)
- `bash scripts/governance/test_strategic_package.sh` — P-2.5 schema validator (target: 8/8 pass)

## Pre-implementation discipline (per DEC-V61-088 · 2026-05-03)

Before starting any non-trivial implementation work — **≥30 LOC OR new
top-level page/route/service file** — run a 2-step pre-implementation
surface scan and write findings to session memory:

1. **ROADMAP scan** — read the relevant ROADMAP §30/§60/§90-day section,
   identify whether the proposed feature maps to a known item, note its
   current status + planning artifact link.
2. **Existing-implementation grep** — `grep -rin "<feature_keyword>"` over
   `src/ ui/backend/ ui/frontend/src/ scripts/`; read first 60 lines of any
   matched file. If a substantial pre-existing implementation is found,
   STOP and surface to user with disposition options (a) extend / (b)
   parallel new / (c) refactor.

**Top-level file** = new file under `ui/backend/routes/*.py`,
`ui/backend/services/*.py` (top-level, not nested helper),
`ui/frontend/src/pages/**/*.tsx` (top-level page component), or
`scripts/*.py` (user-facing entry point). Internal helpers do NOT count.

**Skip clauses**: routine bugfix on already-located file · CLASS-1 docs-only ·
user explicitly says "rewrite X" · trivial single-file edit ≤10 LOC AND no
new top-level file. Trigger wins on conflict (a 9-LOC edit creating a new
top-level route file → scan mandatory).

**Commit-trailer discipline**:
- When prior implementation found: commit MUST carry
  `Surface-scan-found: <path> · disposition: extend|parallel|refactor`
- When scan finds nothing: commit SHOULD carry `Surface-scan: clean` (optional
  but encouraged — its absence is auditable).

**Interaction with §11 standing rules**: §11.1 freeze defaults to
extend-existing on workbench territory; parallel-new requires
BREAK_FREEZE rationale + Kogami acknowledgment. §11.4 quota accounting is
unchanged; what's new is awareness — check current quota before choosing
parallel-new vs extend on §11.4-tracked paths.

**Out of scope**: does NOT modify §10.5.4a audit-required surface gating
(supplements, does not replace).

See DEC-V61-088 for full rationale, Kogami review trail (2 rounds
APPROVE_WITH_COMMENTS · 9 governance-hygiene findings closed inline), and
RETRO follow-up on close-inline-vs-strict-text-validity convention.

## Inherited rules from `~/CLAUDE.md`

User-level CLAUDE.md is the cross-project baseline. Genuinely inherited (lives in global, this project just follows):
- Model routing (Opus 4.7 主驱动 + Codex 4-model 双引擎)
- Subagent 优先原则 (任务 push 主 context ≥35% 才考虑外包 · 1M ctx 校准)
- **Codex 协作守则** (跨项目通用 · global "Codex 协作守则" 节)：risk-tier 1-sync (auth/signing/安全边界) + 2-async-post-merge (byte-repro / 批量 ≥3 fail) · round cap = 3 · confidence 三档自标 · verbatim exception · "Codex 调用是 Claude Code 的责任"
- Codex relay (86gs xhigh primary, CRS high fallback · 命令样板 + backend 表在 global)
- 上下文压缩工作流 · GSD scope-driven 分流 · /goal 通用定位 · Anthropic Agent Canon

**Project-specific (defined HERE, NOT inherited)** — these were de-cfd-ified out of global on 2026-05-29:
- DEC scope-driven 完整 DEC 触发 (charter / 跨 ≥3 共享代码路径 / governance-rule-change) · sub-DEC 6-field 最小 schema
- Cadence floor THRESHOLD 30 · Surface-scan trailer (V61-088, optional) · Pre-implementation surface scan (V61-088)
- Counter telemetry rules (above) · retrospective cadence · external-gate handling
- ~~Notion 深度同步规则 + 指挥中枢一致性~~（已废止 2026-06-10 · DEC-V92-notion-retirement）· Kogami three-layer governance (above)
- /goal CFD-specific Patterns A-D (below)

Kogami strategic layer (per V61-087) is **opt-in only** post-V133 (user explicitly invokes); manual
invocation path operational with all contract files (P-1..P-5) preserved and Q1 canary verification intact.

---

## Project-specific governance detail

> De-cfd-ified out of global `~/CLAUDE.md` on 2026-05-29 — these rules are cfd-harness-unified-only
> and previously polluted every session. Cross-project rules stay in global (see "Inherited rules" above).

### Notion 渠道已废止（2026-06-10 · DEC-V92-notion-retirement · 外部门控=用户裁决）

原「Notion 深度同步规则」（2026-04-21）与「Notion 指挥中枢模型分工一致性」（2026-05-03）两节**全部废止**，
原文见 git history。归档层只走 git + GitHub：`.planning/decisions/` + `.planning/retrospectives/` = SSOT。
不再做任何 Notion sync；skill `notion-sync-cfd-harness` dormant；DEC frontmatter `notion_sync_status`
字段冻结为历史字段（新 DEC 写 `n/a` 或省略）。

**Session-end checklist（继承自原同步 checklist 的非 Notion 项）**：
1. 本会话新增 / 改动的 Accepted DEC 是否都已 commit（push 视用户指示）？
2. STATE.md 最新 timestamp 是否反映最新工作？
3. `external_gate_queue.md` 标 CLOSED 的项目是否都 strike-through？
4. `reports/codex_tool_reports/` 新增审查报告是否已链接到对应 DEC frontmatter `codex_tool_report_path`？

### v6.1 retrospective cadence + external-gate（RETRO-V61-001）

**Retro 必须落地 `.planning/retrospectives/` 的硬性触发（2 类）**：
1. 任何 Phase 标记 COMPLETE 时（phase-close retro）
2. **post-R3 live-run defect** — Codex APPROVE 之后才在 smoke test / live run 发现的 bug。每个 post-R3 defect 写进 RETRO addendum 或 mini-retro，记录：(a) bug 类型（accessor / runtime-emergent）；(b) 为什么 Codex 静态 review 没捕获；(c) 要加进 intake template 的新 risk_flag。

已降级为可选（Opus 自评）：counter ≥ 20 arc-size retro、常规 CHANGES_REQUIRED retro（仅"重复同类型"或"严重盲点"才触发）。

> external-gate DEC 的 counter 处理见上方 "Counter rules" 节。

### /goal CFD-specific Patterns（本项目专用 · 通用 /goal 定位见全局文件）

**Pattern A · phase 执行收口**（最常用 · PLAN.md 在手）：
```text
/goal PLAN.md 里每个 Task 同时满足 (a) status: COMPLETED 且 (b) passes: true
（passes 仅当 E2E smoke / pytest / 手测三选一显式 verify 通过后才设为 true — 防 premature completion）；
所有 commit 带 confidence:<h/m/l> 标签；pytest -q tests/{phase}/ 全绿；
scripts/smoke/dogfood_loop.py 至少跑通一遍；
四问门控（LLM 离线 / artifacts / TrustGate / advisory-only）在对话里逐条 echo 通过；
或 turn 数 > 25 则停下让我接管。
```

**Pattern B · Codex review 闭环（round cap=3 自动落地）**：
```text
/goal Codex review 状态 = APPROVE，或 round 数达到 3
（达到 3 轮则把剩余 findings 写入 .planning/retrospectives/codex_round3_overflow_{phase}.md 并停下等我裁决）。
每轮 = codex-review-relay --base origin/main 完整输出粘入对话 → fix commit → 重新 push → 下一轮 review。
```

**Pattern C · spike-class 单 commit 闭环**：
```text
/goal 改动 ≤30 LOC（git diff --stat 证明）；新增 1 个测试且通过；commit message 含 confidence:<h/m/l>；
不触发 DEC / Codex / Kogami / Notion sync（这些路径必须 echo "skipped: spike-class" 入对话）；
或 turn 数 > 5 则停下检查是否其实是 sub-DEC 误判。
```

**Pattern D · V-series 工件提取**：
```text
/goal V20+ 工件全部 LANDED 到 .planning/intel/v_series/：（清单 1..N）。
每个工件 = codebase 路径引用 + ≥1 case 证据片段 + 跨 case 复用建议；V-series index 更新；
source session RESUME.md 标记 arc CLOSED；或 20 turn 后停下让我审视是否过度抽象。
```

**CFD-specific /goal 注意点**：
1. **OpenFOAM solver 分钟级**：评估器每 turn 触发，turn 数会被收敛过程吃掉。**总在条件里写 turn cap**。
2. **评估器只看对话**：让 Claude 把 `checkMesh` / `pytest` stdout 粘进 transcript，每 turn 末 echo 进度摘要。
3. **四问门控不能省**（advisor-not-driver SSOT）：condition 里包含「每个新文件/PR 把四问回答写入 commit body 或 PR description」。
4. **/goal 不触发 Kogami opt-in**。若命中 charter trigger（≥3 共享代码路径 / governance-rule-change），加 `若命中 charter trigger 立即 /goal clear 并报告`。
5. **Notion 已废止**（2026-06-10 · DEC-V92-notion-retirement）：归档只走 git/GitHub，/goal 无 sync 路径可并。

### 项目专用子代理（建议沉淀到 `.claude/agents/`）

- **cfd-physics-reviewer**：验证 OpenFOAM 物理/边界条件正确性
- ~~notion-sync-worker~~（已随 Notion 废止 2026-06-10）
- **v61-counter-auditor**：检查 v6.1 autonomous_governance counter
