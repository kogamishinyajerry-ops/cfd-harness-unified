---
type: ops
id: OPS-2026-04-25-001
title: Dual-Track Parallel Development Plan · ADR-002 Governance × 10-Case Simulation
status: ACTIVE
created: 2026-04-25
expires: 2026-05-19  # W5 default flip; OPS retires after that date
authors: [Claude Code Opus 4.7 CLI]
reviewers: [Notion Opus 4.7 (audit 2026-04-25)]
notion_url: https://www.notion.so/OPS-2026-04-25-Claude-Code-ADR-002-10-case-34dc68942bed81d88ef5f8add0d01d0a
counter_impact: none  # OPS 不计入 v6.1 autonomous_governance counter
related:
  - ADR-002-four-plane-runtime-enforcement.md (line A)
  - DEC-V61-047 / V61-048 / V61-049 (line B)
amendment_log:
  - 2026-04-25T19:30 Claude Code CLI · §5 BLOCKER + §2/§7 COMMENT amendments per Opus 4.7 audit
  - 2026-04-25T21:25 Claude Code CLI · MP-G retroactive — added §3 CI pre-flight assertion per RETRO-V61-006 addendum 2 + ops_note_protocol.md §5 sixth mandatory rule
expected_signal_source: ".github/workflows/ci.yml backend-tests · last success commit 0229af9 (run 24925115531) · 2026-04-25T06:55"
---

# OPS-2026-04-25-001 · Dual-Track Parallel Development Plan

> **Status**: ACTIVE 2026-04-25T19:30 (Notion Opus 4.7 ACCEPT_WITH_COMMENTS · 3 mandatory amendments landed). Auto-retires 2026-05-19 (W5 default flip).
>
> **Mirror**: This file is git-of-record. The Notion page (link in frontmatter) is the human-readable mirror with audit callouts.

---

## 1. 背景

ADR-002 W4 prep 在 2026-04-25 单日交付 6 个 commit (b10ca9e → e213bbe), W4 prep 弧已在 Codex GPT-5.4-xhigh R2 APPROVE_WITH_COMMENTS 处 clean-close. 剩余 W4 任务只有一行 CI flip (`continue-on-error: true → false`), 必须等 dogfood window (2026-04-25 → 2026-05-09 ≥5 天) 观察期完成.

用户提出在新 Claude Code 会话中并行推进 10-case 仿真深度优化 (DEC-V61-047 / V61-048 / V61-049 弧). 两条线必须并行, 不能互相污染.

## 2. 双线划分 · 文件 ownership 矩阵

### 线 A · ADR-002 治理线 (当前会话 · dogfood 静默期)
- `src/_plane_guard.py` — meta_path finder + A13 watchdog + A18 wired writer + atexit hook + repo-root path resolution
- `src/_plane_assignment.py` — Plane enum + PLANE_OF SSOT dict
- `src/__init__.py` — **SOLE OWNERSHIP** (auto-install hook 是 ADR-002 W3 critical 改动; 线 B 修改需经线 A review)
- `.importlinter` — 5-contract byte-identical generated
- `scripts/gen_importlinter.py` — SSOT generator with `--check`
- `scripts/plane_guard_rollback_eval.py` — 14-day rolling-window evaluator CLI
- `scripts/check_track_isolation.py` — this OPS dual-track isolation guard (warn-not-block)
- `.github/workflows/plane_guard_rollback_cron.yml` — weekly Monday 09:00 UTC
- `docs/adr/ADR-002-four-plane-runtime-enforcement.md` — frozen Accepted spec
- `tests/test_plane_guard*.py`, `tests/test_plane_assignment_ssot.py`, `tests/test_gen_importlinter.py`
- `reports/plane_guard/` — runtime telemetry .jsonl (gitignored)

### 线 B · 10-case 仿真线 (新会话)
- `knowledge/gold_standards/<case>.yaml` (10 case 全部)
- `knowledge/schemas/risk_flag_registry.yaml` — **PRIMARY OWNERSHIP** (additive-only schema evolution; 删字段或改 type 走 amendment DEC)
- `src/foam_agent_adapter.py`, `src/comparator_gates.py`, `src/result_comparator.py` (Execution + Evaluation 平面)
- `src/cylinder_*.py`, `src/airfoil_*.py`, `src/wall_gradient.py`, `src/plane_channel_*.py` (per-case extractors)
- `reports/<case>/report.md`, `reports/phase5_audit/*`, `reports/phase5_fields/<case>/*`
- `whitelist_cases/<case>/*`, `ui/frontend/public/flow-fields/<case>/*`
- `tests/test_phase_e2e.py`, `tests/test_foam_agent_adapter.py`, `tests/test_<case>*.py`
- `.planning/decisions/2026-04-23_cfd_cylinder_multidim_dec053.md`

### SHARED (require explicit ack tag)
任一线修改前需在 commit message 标 `[shared]` 或 `[cross-track-ack]` tag 并在 PR 描述点名对方线影响评估:
- `.gitignore`
- `pyproject.toml`
- `requirements*.txt`
- `.pre-commit-config.yaml`
- `.planning/STATE.md` (详 §6 同步协议)
- `tests/conftest.py` (详 §5 反例)

## 3. 隔离机制

### 物理隔离 (主防线)
- 文件路径: 线 A 的 ~10 个核心文件与线 B 的 case 路径 **directory 零重合**
- 运行时: `CFD_HARNESS_PLANE_GUARD` 默认 `off`, 线 B 完全感知不到 finder 存在
- CI: W4 stage-1 的 WARN-mode dogfood pytest step 是 `continue-on-error: true` (non-blocking)
- Notion 决策 DB: 两条线的 DEC frontmatter 互不引用

### 程序隔离 (硬加固 · per Opus §3 audit recommendation)
- **`scripts/check_track_isolation.py`** + `.pre-commit-config.yaml` `commit-msg` hook (warn-not-block)
- 检测 commit diff 中跨线文件改动; commit message 未标 `[shared]` / `[cross-track-ack]` / `[deps]` / `[ops]` 之一时 stderr warn 但不阻断 commit
- 拒绝 CODEOWNERS (重型工具与单 user 双 AI 会话场景错配); 拒绝 hard-block (false-positive 阻碍合法跨线如 §4.1 新增 src 模块)
- 自动随 OPS expires (2026-05-19) 失效; 该日期后该 hook 仍在 config 中但脚本本身可短路

### CI infrastructure pre-flight (MP-G retroactive · 2026-04-25T21:25)

Per `docs/methodology/ops_note_protocol.md` §5 sixth mandatory rule (added in same commit), this OPS has been retroactively augmented with the CI-healthy pre-flight assertion:

- **Frontmatter**: `expected_signal_source: ".github/workflows/ci.yml backend-tests · last success commit 0229af9 (run 24925115531) · 2026-04-25T06:55"`
- **Verification command**: `gh run list --limit=5 --json conclusion | jq -r '.[].conclusion' | sort | uniq -c` — at least 1 of last 5 must be `success`
- **At OPS authoring (2026-04-25T18:55)**: this assertion would have **failed** (40 consecutive failures pre-`0208929`). The dogfood window was effectively dead-on-arrival until commit `0208929` (CI deps fix) + `0229af9` (first successful run). RETRO-V61-006 addendum 2 captures the post-mortem. Going forward, any future OPS must satisfy this pre-flight at DRAFT → ACTIVE flip time.

## 4. 协调协议 · 3 个潜在交叉点 (都不阻塞)

### 4.1 新增 src.* 模块时 (线 B 触发)
1. 在 `src/_plane_assignment.py` 的 PLANE_OF dict 添加 `'src.<new>': Plane.<EXECUTION|EVALUATION>`
2. 运行 `python3 scripts/gen_importlinter.py` 重生成 `.importlinter`
3. 运行 `python3 scripts/gen_importlinter.py --check` 验证 byte-identical exit 0
4. `.venv/bin/lint-imports --config .importlinter` 验证 5 contracts kept 0 broken
5. Commit message 标 `[cross-track-ack]` tag
6. 违反: CI 上 ADR-001 import contract 步骤会失败 (hard-blocker)

### 4.2 修改既有 src.*.py 时 (线 B 常态)
线 B 修改 `src/foam_agent_adapter.py` 等既有模块不需要任何线 A 同步. 同 plane 内修改不触发四平面契约.

### 4.3 dogfood window 信号 (线 A 主动观察)
线 B 的 PR 推到 origin/main 后会自动触发 W4 stage-1 dogfood pytest. 线 A 在 5/9 之后 review artifact uploads 中的 `fixture_frame_confusion.jsonl` + `sys_modules_pollution.jsonl`. 线 B 不需要主动响应.

## 5. 反例清单 · 哪些操作会污染另一条线

- ❌ 线 B 直接编辑 `src/_plane_guard.py` / `src/_plane_assignment.py` (线 A 唯一所有权)
- ❌ 线 B 手工编辑 `.importlinter` (必须通过 `gen_importlinter.py` 重生成)
- ❌ 线 B 修改 `.github/workflows/plane_guard_rollback_cron.yml`
- ❌ 线 B 修改 `docs/adr/ADR-002*.md` (Accepted · 任何修改需走 amendment DEC)
- ❌ 线 A 在 dogfood window 期间修改 `src/_plane_guard.py` / `src/__init__.py` (破坏信号一致性 · 除非 hot-fix 致命缺陷)
- ❌ 任意一条线在不知会另一条的情况下修改 `.planning/STATE.md` 的 status 字段 (双线撞 commit · 用 last_updated timestamp 排序解决)

### Opus 4.7 audit 2026-04-25 BLOCKER amendments (3 高价值污染向量)

- ❌ **线 B 修改 `requirements.txt` / `pyproject.toml` 依赖未通报线 A** — 依赖变更触发 CI 全 stage 重新跑 (含 W4 stage-1 dogfood pytest), 可能在 install 阶段引入新警告污染 `fixture_frame_confusion.jsonl` + `sys_modules_pollution.jsonl` 信号. 所有依赖变更必须在 commit message 标 `[deps]` 并在 PR 描述点名 dogfood window 影响评估.
- ❌ **线 B 修改 `knowledge/schemas/case_profile_schema.yaml` 字段为非 backward-compatible** — 删字段或改字段 type 会破线 A 的 P1-T3 CaseProfile loader 测试 (`tests/test_metrics/test_load_tolerance_policy.py`) 和 P1 arc end-to-end chain. 强制 additive-only schema evolution; 非加性变更走 amendment DEC + 同步更新 loader 测试.
- ❌ **线 B 在 `tests/conftest.py` 添加 import-time side effect 或覆盖 `_plane_guard_test_isolation` autouse fixture** — 线 A 已占该 fixture 防 dev env var 污染 + fork 继承 bug. 线 B 新增 fixture 必须 (i) 不重命名/不覆盖 `_plane_guard_test_isolation`; (ii) 不在 module-level 触发 `src.*` import (否则 plane_guard 启动顺序混乱); (iii) 任何新 autouse fixture 必须 explicit-OFF env var 兜底.

## 6. STATE.md 同步协议

两条线都会更新 `.planning/STATE.md` 的 `last_updated`. 冲突解决:
1. 提交前 `git pull --rebase origin main`
2. 如有 STATE.md `status` 字段冲突: 保留两条线的内容, 用 `" · "` 分隔 (不是覆盖)
3. `last_updated` 取较新者

## 7. 时间线

- **2026-04-25 → 2026-05-09** · 双线并行 (线 A 静默 dogfood + 线 B 主动 case 优化)
- **2026-05-09** · 线 A dogfood signal review (artifact 0 incidents 即可推进 W4 toggle PR)
- **2026-05-11** · W4 toggle PR deadline (Opus G-9 binding 2 · 一行 yaml flip)
- **2026-05-19** · W5 default flip `'off' → 'warn'` + OPS-2026-04-25-001 expires
- 线 B 节奏由该会话自定 (DEC-V61-047 / 048 弧推进)

### Opus 4.7 audit 2026-04-25 §7 deferred (mandatory)
- **DEC-V61-053 cylinder closeout** (attempt-8 endTime bump 60s 重跑) **推到 dogfood window 后** (2026-05-10+). 理由: 与线 A artifact 上传节奏共占 CI runner 时间窗口, dogfood window 内启动会让 5/9 review 难以区分 "plane_guard 噪音" vs "endTime-bump 重跑副作用". dogfood window 内 V61-053 保持 `IN_PROGRESS_DEMONSTRATION_GRADE` 不动; attempt-8 排在 W5 default flip 之后.
- **DEC-V61-049 LDC pilot 推到 W5 default flip 之后启动** (lid-driven cavity 是新案例引入, case_profile schema 改动概率高, 避开 schema 变更窗口). 线 B 新会话 ROADMAP 必须明示该 deferred 约束.
- **DEC-V61-047 / V61-048 在 dogfood window 内可正常推进** (047 → 048 排序合理).

## 8. Codex 调度独立性

两条线都可以独立调用 `/codex-gpt54` — 7 账号池支持并发, `cx-auto 20` 自动切号. ChatGPT-tier 仅支持 `gpt-5.4` (见方法论页面 2026-04-25 calibration callout).

## 9. 提交粒度建议

- **线 A**: W4 toggle PR 之前不再向 main push (dogfood window 静默期). 例外: bug-fix 致命缺陷 + 需要重启 dogfood window
- **线 B**: 每个 case 优化推荐独立 commit, commit message 标 `[case-N]` 或 `[line-b]` 前缀方便与线 A 区分

## 10. OPS 类型规范 (first-of-kind 配套)

本文件是 OPS 类型 governance artifact 的 first-of-kind. 详细 OPS 类型规范见 `docs/methodology/ops_note_protocol.md`. 关键规则:
- `type=ops` 不进 `autonomous_governance_counter_v61`
- 不需要 Codex review (doc-level only; isolation script 落地纳入 ADR-002-IMPL Codex post-merge audit 同窗口审查)
- 必须 Notion-mirror (Notion URL 在 frontmatter)
- `expires` 字段必填 (此文件 2026-05-19 自动 retire)
