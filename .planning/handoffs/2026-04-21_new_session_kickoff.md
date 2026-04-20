# 新 Claude Code Session 开工交棒 — cfd-harness-unified

**Date**: 2026-04-21
**Handed off by**: Claude Opus 4.7 (1M context) · session 2026-04-20/21
**Handed to**: 新的 Claude Code session (推荐 Opus 4.7)
**Repo**: https://github.com/kogamishinyajerry-ops/cfd-harness-unified
**Working dir**: `~/Desktop/cfd-harness-unified`
**Main SHA at handoff**: `b05b7d7`

---

## 接棒 5 分钟读这一段

- **Phase 0..5 已 merged 18 PR**（#2..#18）。Phase 5 **有 1 个 Codex-blocking** 待处理：PR-5d.1
- **External-gate queue 空**（Q-1/Q-2/Q-new 都关了）
- **回归 325 passed + 1 skipped**（3 个 pre-existing `test_validation_report.py` failures 是历史遗留，不是你的作用）
- **v6.1 autonomous_governance counter = 15**（已远超 hard-floor-4 阈值 ≥10，overdue retrospective）
- **Case 9 (Impinging Jet) + Case 10 (Rayleigh-Bénard) 文献 re-source** 仍 HOLD（PDF paywalled）
- **§5d Docker dashboard 验证**未做（等用户启 Docker Desktop）

---

## 立即可做的事（优先级排序）

### P0 — PR-5d.1 收尾 Phase 5（如果用户选 X1）

Codex 4 轮审查返回 **CHANGES_REQUIRED**：

| 级别 | 问题 | 修法 |
|---|---|---|
| HIGH #1 | POST 签名空证据包；接受 nonexistent case_id | 拒绝未知 case_id → 404；(可选)要求 resolved run_output_dir |
| HIGH #2 | `generated_at` 每次调用重盖 → ZIP hash + HMAC 飘动 | 改成从输入推导稳定值（如 `sha256(case_id|run_id|repo_sha)`），或移出 canonical payload |
| MEDIUM | V&V40 checklist 不忠实于 FDA 2023 CM&S guidance | 改名 "Internal V&V evidence summary"，移除 skeleton bundle 里没有的字段引用 |

规模 ~140 LOC + ~60 tests。详见 `.planning/decisions/2026-04-21_phase5_5d_screen6_ui.md` 和 `reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md`。

决策路径 X1/X2/X3/X4 在 DEC-V61-018 里枚举。**用户需要先给选择**。

### P1 — v6.1 counter 复盘

counter 15 远超阈值 10。**用户主导**一次正式复盘（回顾 DEC-V61-012..018，评估 Codex 命中率，决定是否调整阈值或重置计数）。

### P2 — §5d Docker dashboard 真实验证

需要用户本地：
```bash
docker --version   # 确认 daemon 可启
docker pull openfoamplus/of_v2212_centos72   # 或等价镜像
~/.docker/bin/docker-desktop-cli start   # 或 GUI 打开
```
然后我调 UI backend `/api/cases/{id}/runs/{rid}/audit-package/build` + runs 接口，跑 10 case，截图 Screen 4/5/6，写 `reports/post_phase5_acceptance/<date>.md`。

### P3 — Case 9/10 文献 re-source

Behnad 2013 (DOI `10.1016/j.ijheatfluidflow.2013.03.003`) + Chaivat 2006 (DOI `10.1016/j.ijheatmasstransfer.2005.07.039`) 两篇在 Elsevier paywall 后。**用户**用机构账号拿到 PDF 后，放到 repo 任意位置 ping 我，开 DEC-V61-019 更新 Cases 9+10 gold。

### P4 — 技术债清理

- **3 个 `ui/backend/tests/test_validation_report.py` failures**（DEC-V61-006 之后没更新，DHC Nu=30→8.8 / TFP SST→laminar 遗留）
- `datetime.datetime.utcnow()` deprecation in `correction_recorder.py:76` + `knowledge_db.py:220`
- `foam_agent_adapter.py` 7000 行单文件（拆分重构，但要先 freeze API）
- Codex-queued M2 (sidecar v2 with kid/alg/domain) + L2 (canonical JSON spec public)

---

## 治理 SSOT 位置

| 东西 | 位置 | 权威度 |
|---|---|---|
| 当前心跳 | `.planning/STATE.md` | 每日更新 |
| 决策清单 | `.planning/decisions/DEC-V61-*.md` (001..018) | 落地时 + Notion mirror |
| Gate 队列 | `.planning/external_gate_queue.md` | 当前空 |
| Codex 审查报告 | `reports/codex_tool_reports/` | 4 份 Phase 5 review |
| Phase 5 kickoff | `.planning/phase5_audit_package_builder_kickoff.md` | 完工 3.75/4 |
| **Notion Decisions DB** | data_source `54bb6521-2e59-4af5-93bd-17d55c7c34e1` | 人可读门户 |
| **Notion Project 根** | page `340c68942bed80ae9042df5f149d4d5f` | 含 Session Summary |

**冲突时以 git 为准。**

---

## 工具 / 命令速查

```bash
# 测试（我的 default matrix）
cd ~/Desktop/cfd-harness-unified
.venv/bin/python -m pytest \
  tests/test_foam_agent_adapter.py \
  tests/test_result_comparator.py \
  tests/test_task_runner.py \
  tests/test_e2e_mock.py \
  tests/test_correction_recorder.py \
  tests/test_knowledge_db.py \
  tests/test_auto_verifier \
  tests/test_audit_package \
  ui/backend/tests/test_audit_package_route.py \
  -q

# 预期: 325 passed + 1 skipped

# Frontend typecheck
cd ui/frontend && npx tsc --noEmit

# Codex post-merge review (唯一例外: 机械 verbatim fix 可跳过)
cx-auto 20 && codex exec "<review prompt>" 2>&1

# UI dev mode
./scripts/start-ui-dev.sh   # Vite 5173 + FastAPI 8000

# HMAC env for audit-package dev
export CFD_HARNESS_HMAC_SECRET="base64:$(openssl rand -base64 32)"
# 或 dev:
export CFD_HARNESS_HMAC_SECRET="text:dev-key"
```

---

## v6.1 治理规则摘要

- **autonomous turf**: `src/` `tests/` `docs/` `scripts/` `.planning/` `ui/` — 自主 merge (regular merge commit)
- **禁区**: `knowledge/gold_standards/**`, `knowledge/whitelist.yaml` `reference_values` — **external gate**
- **metadata 字段**（`turbulence_model`, `solver`, `parameters.*`）可自主改
- **Codex 强制审查**: gold_standards 修改、reference_values 修改、测试删除、UI breaking change、OpenFOAM solver 修复、`foam_agent_adapter.py` >5 行改动
- **Codex 跳过条件**: 修复是 Codex 自己上一轮 verbatim 推荐 + 机械 + atomic
- **commit trailer**: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- **每个 DEC**: frontmatter 含 `decision_id`, `autonomous_governance`, `claude_signoff`, `codex_tool_invoked`, `notion_sync_status`, `github_merge_sha`, `reversibility`, `upstream`

---

## subagent 使用铁律（新加 · 2026-04-21）

**项目长度已经超长 — subagent 是主要 context 管理机制**。详见 `~/CLAUDE.md` §"长项目 · Subagent 使用规则"。简述：

- **广度探索** (>3 Glob/Grep) → `Explore` agent ("very thorough")
- **多文件 bug 调查** → `gsd-debugger` 或 `general-purpose`
- **并行独立任务** → 多个 Agent 同一条消息并发
- **长文档 + 大测试 log parsing** → agent 交付摘要，不回灌原始
- **reject**: 单文件 Read、修改代码（主 session 做 Edit/Write）、重复问主 context 有的信息

---

## 最小确认 checklist（接棒后跑）

```bash
cd ~/Desktop/cfd-harness-unified && \
git status                                        # 应该清爽
git log --oneline -3                              # 最新 c5f5aa2/..../b05b7d7 系列
.venv/bin/python -m pytest tests/test_audit_package -q   # 58 + skipped
gh pr list --state open --limit 5                 # 应该 0 open
head -5 .planning/STATE.md                        # last_updated 2026-04-21T03:45
cat .planning/external_gate_queue.md | head -30   # Queue EMPTY
ls reports/codex_tool_reports/                    # 4 个 Phase 5 review reports
```

如果任何一条偏离预期：**先 git status + git log 再动手**，不要直接开代码修改。

---

## 本次交棒包含 3 个新规则（落在 `~/CLAUDE.md`）

1. **长项目 subagent 使用规则** — 何时必用/建议用/拒绝用 subagent
2. **Notion 深度同步规则** — checklist + git 冲突时的权威方
3. **auto-compact = 50%** — `~/.claude/settings.json` 的 `autoCompactWindow: 500000` 已经生效

---

**祝开工。我是 MiniMax 的老前辈，你是 Claude Code 的 Opus 4.7 successor — 如果 in doubt, git log + 读 DEC 文件。**
