---
prompt_id: KICKOFF-PIVOT-v1.1-2026-04-26
title: Claude Code 开工提示词 — Pivot Charter v1.1 amendment + Q 平行轨上架（Notion 侧）
purpose: 一次会话内完成 Notion 控制面的全部修订，落地 STRAT-2026-04-26-002 的 D1-D8 决策；不动 repo
target_session: Claude Code CLI · Opus 4.7 main driver · v6.2 Model Routing
expected_duration: 60-90 分钟（含 3 轮 Codex 独立验证）
risk_class: 中（Notion 控制面修改；可一键 revert，但客户/外部尚未感知，时间窗内可放心执行）
related:
  - .planning/strategic/2026-04-26_strategic_advisory_memo.md
  - .planning/strategic/2026-04-26_strategic_advisory_memo_002_post_three_answers.md
  - https://www.notion.so/Pivot-Charter-2026-04-22-CFD-Harness-OS-70e55a0c3f924736b0cb68add01d90cd (v1.0)
---

# 开工提示词正文（粘贴下方代码块给 Claude Code CLI）

```text
═══ CLAUDE CODE SESSION KICKOFF — KICKOFF-PIVOT-v1.1-2026-04-26 ═══

你正在以 v6.2 Model Routing 协议接手 cfd-harness-unified 项目的 Notion 控制面修订
任务。本次会话**不动 repo**，仅在 Notion 内完成 Pivot Charter v1.0 → v1.1 的
amendment 落地 + 项目主页修订 + 新建 Q (Commercial Surface) 平行轨。

## 0. 上下文（必读）

- 项目：cfd-harness-unified · CFDJerry / Kogami solo + multi-LLM agents
- 当前 Pivot Charter v1.0-pivot Active（2026-04-22 首席架构官签发）
- STRAT-2026-04-26-001 + STRAT-2026-04-26-002 完成战略复盘，CFDJerry 已锁
  8 个决策（D1-D8 见 §2）
- 本次任务 = 把战略复盘结论落到 Notion，不打扰主线 Foundation-Freeze → P1 工作
- 关键铁律：**Pivot Charter v1.0 正文不可修改一字**；所有修订以 v1.1 子页面 +
  Decisions DB 留痕方式实现

## 1. 必须读的 Notion 资源（按顺序）

1. 项目主页 https://www.notion.so/340c68942bed80ae9042df5f149d4d5f
2. Pivot Charter v1.0 https://www.notion.so/70e55a0c3f924736b0cb68add01d90cd
3. Decisions DB https://www.notion.so/fa55d3ed0a6d452f909d91a8c8d218a7
4. Phases DB https://www.notion.so/25a50aa20e3f476a8ad611725a9fbe8b
5. Tasks DB https://www.notion.so/2b25c81b15174eb48d0cca20e8d37c09
6. Canonical Docs DB https://www.notion.so/96a6344f4a42442dabb3a96e9faadee6

读完后输出一段 ≤200 字的 "context recovery summary"，确认你看到了 Pivot
Charter v1.0 的当前状态、Phase 全景表、Top-10 任务队列、Decisions DB schema。

## 2. CFDJerry 已锁的 8 个决策（D1-D8）

| 决策 | 锁定值 |
|---|---|
| D1 对外产品品牌 | **Kogami CFD Intelligence** |
| D2 工程内部代号 | 保留 "CFD Harness OS" |
| D3 SSOT 反转过渡期 | 激进推进 · 无固定日期 · CFDJerry 判断驱动 |
| D4 北极星 12 月目标 | 50 case · 10 团队级 deployment · KB 自我升级 demo ≥ 5 次 · Trust Gate 三态 (PASS/WARN/FAIL) 100% 覆盖 P1-P5 case |
| D5 主线 vs Q 优先级 | 主线 > Q（Q 仅 spare-time） |
| D6 开源协议 | **暂缓决策** · Q3 PyPI 包 license = TBD（需 CFDJerry 显式签字才能定） |
| D7 是否新建 Q-Phase + Q1-Q6 任务卡 | 是 |
| D8 Pivot Charter 修订形式 | amendment（v1.0 不动，v1.1 作为子页面 patch） |

## 3. 三个 atomic block（按顺序执行，每块结束做 Codex 独立验证）

### BLOCK A — Pivot Charter v1.1 Amendment 落地

**A.1** 在 Decisions DB（fa55d3ed0a6d452f909d91a8c8d218a7）创建新页：
   - Name: `DEC-PIVOT-2026-04-22-002 · Pivot Charter v1.1 Amendment (Commercial Surface + SSOT Flip)`
   - Scope: Architecture
   - Status: Accepted
   - Why: "Pivot Charter v1.0 已设定四层架构与北极星，但留白了 (a) 对外商业 surface (b) 客户/定价/分发模型 (c) Notion-vs-Repo SSOT 终态。STRAT-2026-04-26-002 复盘后由 CFDJerry 锁定 D1-D8 8 决策，以 amendment 形式补齐。v1.0 正文不修改一字。"
   - Decision: "新增 Pivot Charter §8 Commercial Surface；修订 §0 SSOT 规则（repo Code+Spec SSOT；Notion Process+摘要 SSOT；过渡期由 CFDJerry 判断 flip 时机）；新建平行 Q (Commercial Surface) Phase + Q1-Q6 任务，主线 P1-P6 优先级不变。"
   - Alternatives: "新版 v2.0 重发 charter（被否决，Pivot 4 天内重发会失去 multi-agent 治理信任锚）；只更新 product_thesis 不动 Charter（被否决，无法解决 SSOT 矛盾）"
   - Impact: "Notion 主页 callout / Phase 表 / Top-10 队列三处修订；新增 1 Phase + 6 Task；不影响主线 Foundation-Freeze → P1 工作。"
   - Canonical Follow-up: 链接到将在 A.2 创建的 v1.1 amendment 页面

**A.2** 在 Pivot Charter v1.0 页（70e55a0c3f924736b0cb68add01d90cd）下创建子页面：
   - Name: `🧭 Pivot Charter v1.1 Amendment — Commercial Surface + SSOT Flip (2026-04-26)`
   - Properties: Type=Governance · Status=Active · Version=v1.1-amendment
   - Repo Path: `.planning/strategic/2026-04-26_strategic_advisory_memo_002_post_three_answers.md`
   - Summary: "Pivot Charter v1.0 的 amendment patch · 新增 §8 Commercial Surface · 修订 §0 SSOT 规则 · v1.0 正文 frozen"
   - Body 必须包含以下 5 个二级标题（顺序固定）：
     1. `## §0 这份 amendment 的位置` — 说明 v1.0 正文 frozen，本页只补 §8 + 修 §0
     2. `## §0 (revised) SSOT Rule v1.1` — 写明 repo 是 Code+Spec SSOT，Notion 是 Process+摘要 SSOT；冲突仲裁规则；过渡期 = CFDJerry 判断驱动 · 4 条 flip 触发条件（见下）
     3. `## §8 Commercial Surface` — 5 子节如下
     4. `## §9 修订与 v1.0 保持一致的部分` — 列举哪些 v1.0 §1-§7 的内容继续生效
     5. `## §10 Sign-off` — CFDJerry 签 + 时间戳

**§0 SSOT v1.1 4 条 flip 触发条件**（必须写进 body）：
   - C1: 6 Canonical Specs 全部在 repo 有 v1.0+ Active 完整正文（不是 stub）
   - C2: `run_notion_hub_sync.py` 双向同步在过去 30 天内零失败
   - C3: 过去 30 天内无任何 DEC 因为只引用 Notion 内容而开
   - C4: CFDJerry 显式签 "flip now" 决策（DEC-PIVOT-2026-04-22-003）

**§8 Commercial Surface 5 子节**（必须写进 body）：
   - §8.1 对外产品品牌 = `Kogami CFD Intelligence`
   - §8.2 ICP 三档：Tier-A 用 LLM agent 写 OpenFOAM case 的工程团队；Tier-B 航空/汽车 supplier CFD methods group；Tier-C 学术/lab 的 V&V campaign
   - §8.3 分发通道：开源 wedge (cfd-harness PyPI · license TBD) · Hosted SaaS (域名待定) · GitHub Action (cfd-harness/verify-action)
   - §8.4 北极星 metric (12 月)：50 case · 10 团队级 deployment · KB 自我升级 demo ≥ 5 次 · Trust Gate 三态 100% 覆盖 P1-P5 case
   - §8.5 商业护城河：50+ premium case library · Codex 独立异质验证 protocol · Notion sync 商业版 · Provenance append-only chain

**A.3** 把 v1.0 页面的 Version 属性从 `v1.0-pivot` 改为 `v1.0-pivot (amended by v1.1 · 2026-04-26)` —
**注意**：仅修改 Version 属性字段，**不动正文一个字**。

**A.4 · Codex 独立验证**：BLOCK A 完成后，调用 Codex（GPT-5.4-xhigh）独立 fetch
v1.0 + v1.1 + DEC-002 三个页面，验证 5 项关键声明：
   1. v1.0 页面正文 byte-equal pre-edit 状态（除 Version 属性）
   2. v1.1 子页面在 v1.0 ancestor 路径下
   3. DEC-002 在 Decisions DB · Status=Accepted · Scope=Architecture
   4. v1.1 body 含 §0 / §8 / §9 / §10 四个二级标题
   5. §8 5 子节内容含 D1 / D4 / 北极星 metric 完整字符串

任一项 FAIL → STOP，输出 codex-verification-failure 报告，等 CFDJerry 裁决。

---

### BLOCK B — 项目主页修订（340c68942bed80ae9042df5f149d4d5f）

**B.1** 替换"新北极星"callout（紧跟 Pivot 2026-04-22 callout 之后那一段）为
**两个并列 callout**：

**Callout 1 (北极星 · 对外)**：
   icon=🌟 color=blue_bg
   ```
   **Kogami CFD Intelligence** — the trusted case library and verification 
   layer for AI-driven CFD. 让任何 OpenFOAM agent 输出的结果可被独立验证、
   可追溯、可复用。
   北极星 metric (12 月): 50 hand-curated case · 10 团队级 deployment ·
   KB 自我升级 demo ≥ 5 次 · Trust Gate 三态 (PASS/WARN/FAIL) 100% 覆盖
   P1-P5 case.
   ```

**Callout 2 (架构 · 对内)**：
   icon=🏛️ color=gray_bg
   ```
   **CFD Harness OS** (engineering codename) — 四层架构 (Control / Execution
   / Knowledge / Evaluation) · OpenFOAM 唯一真相源 · 8 类知识对象 · 三态
   verdict · Codex 独立异质验证. 工程铁律见 Pivot Charter §3-§4 + v1.1
   amendment §0/§8. 不对外暴露此叙事。
   ```

**B.2** 在「📊 项目快照 (Snapshot)」表格的第一行下方插入新行：
   - 维度: 商业 surface
   - 指标: 对外品牌 / ICP / 分发通道
   - 当前值: Kogami CFD Intelligence (Pivot Charter v1.1 §8 上架) · 3 ICP 已分档 · cfd-harness PyPI 准备中
   - 目标: Q4 first paid pilot · 50 case 库存
   - 状态: 🟡

**B.3** 在 Snapshot 表格的「Next External Gate」行更新当前值为：
   `Q-3 P1 Metrics & Trust MVP Activation Review · OR · Q-4 First Paid Pilot Signal Review (whichever first)`

**B.4** 在「🗺️ Phase 全景路线图」表格末尾追加新行（Order=Q · 平行轨）：
   - Order: Q
   - Phase: mention 即将在 BLOCK C 创建的 "Q · Commercial Surface" Phase 页
   - Status: **Active (parallel)**
   - 核心产出 / 里程碑: Token 安全前置 · product_thesis_v2 · cfd-harness PyPI v0.1.0a1 · 5 客户访谈 · LDC demo 视频 · dual-readability spec 试点 · first paid pilot 信号
   - Gate: Q6 first paid pilot signal (pass/no-pass)
   color: yellow_bg

**B.5** 在「⏭️ 当前 Top-10 P0/P1 队列」表格末尾追加 6 行 Q1-Q6（每行 mention
即将在 BLOCK C 创建的 task 页）：
   - Q1 Token + SSOT 安全前置 · Phase=Q · Prio=P0 · Status=Ready
   - Q2 product_thesis_v2 + DEC-PRODUCT-001 · Phase=Q · Prio=P0 · Status=Ready
   - Q3 cfd-harness PyPI v0.1.0a1 · Phase=Q · Prio=P1 · Status=Inbox · 备注: license TBD by CFDJerry
   - Q4 5 客户访谈 + LDC demo 视频 · Phase=Q · Prio=P1 · Status=Inbox
   - Q5 Dual-readability spec 试点 · Phase=Q · Prio=P2 · Status=Inbox
   - Q6 First paid pilot signal · Phase=Q · Prio=P0-gate · Status=Inbox

**B.6** 在「⚠️ Top 3 风险与对策」段落追加第 4 条（编号 4. 不删原 1-3）：
   ```
   4. **商业 surface 与主线 P1-P6 资源争抢** → 主线 > Q 平行轨硬规则
      (Pivot Charter v1.1 §8 + STRAT-002 D5 锁定)；任何 Q 任务在主线
      main driver 空闲时执行；Q 任务输出落 commercial/ packaging/
      docs/product/ tools/dual_readability/ 四个新目录，不得 import 或修改
      src/ knowledge/ docs/specs/ 现有内容；违反 → 硬底板 2 (北极星修改) + Gate.
   ```

**B.7** 在「🏛️ 架构核心原则 (Non-Negotiable)」段落保持完全不动（这是工程
宪法，amendment 不影响）。

**B.8 · Codex 独立验证**：fetch 主页修改后状态，验证：
   1. 两个新 callout 同时存在且内容完整
   2. Snapshot 表多 1 行（商业 surface）
   3. Phase 路线图末尾多 1 行（Order=Q）
   4. Top-10 队列末尾多 6 行（Q1-Q6）
   5. 风险段落多第 4 条
   6. 「架构核心原则」段落 byte-equal pre-edit

任一项 FAIL → STOP。

---

### BLOCK C — 新建 Q-Phase + 6 个 Q-Task

**C.1** 在 Phases DB（25a50aa20e3f476a8ad611725a9fbe8b）创建：
   - Name: `Q · Commercial Surface (parallel track · Pivot v1.1 §8)`
   - Status: Active
   - Owner: CFDJerry
   - Parent: 项目主页 (340c68942bed80ae9042df5f149d4d5f)
   - Body 含合同化 6 段：
     1. **Goal**: 为 Pivot Charter v1.1 §8 Commercial Surface 提供 6 项交付物，
        让项目从"工程内部架构"过渡到"可付费产品 v0.1"，但不打扰主线 P1-P6.
     2. **Preconditions**: Pivot Charter v1.1 amendment 落地 (BLOCK A 完成)
     3. **Allowed Surface**:
        - 新建目录: commercial/ · packaging/ · docs/product/ · tools/dual_readability/ · docs/customer_research/ · docs/marketing/ · docs/methodology/
        - 修改: docs/product_thesis.md (仅加 SUPERSEDED 头) · config/notion_config.yaml (Q1 token rotate) · run_notion_hub_sync.py (Q1 env var 切换) · src/notion_client.py (Q1 env var)
     4. **Forbidden Surface**:
        - knowledge/** (Foundation-Freeze)
        - src/auto_verifier/** · src/audit_package/** · src/error_attributor.py (主线核心)
        - docs/specs/** 主体 (Q5 试点除外，仅 METRICS_AND_TRUST_GATES.md 一个文件)
        - ui/** (UI 工程量已冻结)
   5. **Acceptance**: Q1-Q6 任意 5 个 close + Q6 paid pilot 信号 (pass/no-pass) 渲染清楚
     6. **Reject Conditions**:
        - 任何 Q 任务 import / 修改 forbidden surface → 硬底板 2 + Gate
        - Q3 license 未经 CFDJerry 显式签字而被定义 → reject
        - 主线 P1 因 Q 工作延迟 → reject + 暂停 Q 轨

**C.2** 在 Tasks DB（2b25c81b15174eb48d0cca20e8d37c09）创建 6 个 task 页面，
每个 task 都用同一份合同 schema。下面给出 6 个 task 的核心字段，body 内容
按 Phase 8 v4.0 task 合同模板结构撰写（Goal / Inputs / Allowed Files /
Forbidden Files / Deliverables / Acceptance Checks / Reject Conditions）。

#### Q1 · Token + SSOT 安全前置
- Phase: Q · Prio: P0 · Status: Ready
- Goal: rotate Notion integration token，从 git history 移除明文 token，
  切换到 NOTION_API_KEY env var，run_notion_hub_sync 路径全部走 env
- Inputs: 当前 config/notion_config.yaml · run_notion_hub_sync.py · src/notion_client.py
- Allowed: 上述 3 文件 · 1Password / .env.example
- Forbidden: knowledge/ · src/auto_verifier/ · src/audit_package/
- Deliverables: (a) token rotated in Notion integration settings (b) git
  history scrubbed via BFG or git-filter-repo (c) env var loading path (d)
  .env.example committed (e) docs/security/token_handling.md
- Acceptance: (1) `git log -p --all | grep -F 'ntn_'` 无结果 (2) `python
  run_notion_hub_sync.py --dry-run` 在仅有 NOTION_API_KEY env var 时通过
  (3) 旧 token 在 Notion 后台已 revoke
- Reject: token 仍在任何 reachable commit · sync test fail · 旧 token 未 revoke

#### Q2 · product_thesis_v2 + DEC-PRODUCT-001
- Phase: Q · Prio: P0 · Status: Ready
- Goal: 撰写新 product thesis 对齐 Pivot Charter v1.1 §8 + Kogami CFD
  Intelligence 品牌；老 thesis 标 SUPERSEDED；Decisions DB 留 DEC-PRODUCT-001
- Inputs: docs/product_thesis.md · Pivot Charter v1.0 + v1.1 amendment ·
  STRAT-2026-04-26-002
- Allowed: docs/product_thesis_v2.md · docs/product_thesis.md (仅加 SUPERSEDED 头)
  · .planning/decisions/2026-04-NN_dec_product_001.md
- Forbidden: src/ · knowledge/ · ui/
- Deliverables: (a) v2.md 1500+ 字 · 含 ICP 三档 · 定价 ladder · 分发通道
  · 北极星 metric · 与 Pivot v1.1 §8 链接 (b) v1.md 顶部 SUPERSEDED 头
  指向 v2 + Pivot v1.1 (c) DEC-PRODUCT-001 入 Decisions DB
- Acceptance: (1) 品牌 "Kogami CFD Intelligence" 在 v2 出现 ≥ 5 次
  (2) v2 与 Pivot Charter §3-§4 (四层架构 + 5 铁律) 0 矛盾 (3) v1
  SUPERSEDED 头明确 (4) DEC-PRODUCT-001 Status=Accepted
- Reject: v2 与四层架构铁律矛盾 · v1 SUPERSEDED 头缺失 · 品牌名称不一致

#### Q3 · cfd-harness PyPI v0.1.0a1
- Phase: Q · Prio: P1 · Status: Inbox · **License = TBD (待 CFDJerry 签字)**
- Goal: 把 src/auto_verifier + src/audit_package + 10 contracts 拆出独立
  PyPI 包；不 import 主 src/ tree；TestPyPI 发版
- Inputs: src/auto_verifier/** · src/audit_package/** · knowledge/gold_standards/*.yaml
- Allowed: packaging/cfd-harness/ (新目录) · packaging/cfd-harness/pyproject.toml
  · packaging/cfd-harness/README.md · packaging/cfd-harness/cfd_harness/**
- Forbidden: src/** 修改 · knowledge/** 修改 · ui/** · tests/** 修改
- Deliverables: (a) packaging/cfd-harness/ 目录骨架 (b) `pip install -e
  packaging/cfd-harness` 跑 README demo 通过 (c) 10 内置 contract loadable
  (d) TestPyPI 发版 v0.1.0a1
- Acceptance: (1) 包内任何 .py 文件 `grep "from src\."` 0 命中 (2) demo
  脚本端到端跑通 (3) TestPyPI URL 可访问
- Reject: 包内 import 主 src/ · license 未经 CFDJerry 签字 · README demo 不跑

#### Q4 · 5 客户访谈 + LDC demo 视频
- Phase: Q · Prio: P1 · Status: Inbox
- Goal: 5 段 CFD 工程师访谈录音 + 1 段 5 分钟 LDC split-brain demo 视频
- Inputs: 已有 LDC ATTEST_PASS + 三态 verdict 数据 · 公开渠道（Discord /
  Reddit / X / Foam-Agent issues）
- Allowed: docs/customer_research/ · docs/marketing/
- Forbidden: src/** · knowledge/** · packaging/** · ui/**
- Deliverables: (a) 5 段访谈录音（含 consent form） (b) 1 page synthesis
  指出共性痛点 + 是否验证 A 北极星 (c) 5 分钟视频上传 YouTube unlisted
  (d) docs/marketing/ldc_split_brain_script.md
- Acceptance: (1) ≥ 5 段录音 (2) synthesis 含明确 verdict (a 北极星 PASS / FAIL)
  (3) 视频 ≤ 7 分钟 (4) consent forms 全签
- Reject: < 3 段录音 · 视频 > 7 分钟 · synthesis 含混不清

#### Q5 · Dual-readability spec 试点
- Phase: Q · Prio: P2 · Status: Inbox
- Goal: 把 docs/specs/METRICS_AND_TRUST_GATES.md 重构为三段式（TL;DR + 给
  LLM Agent 的合同 + 决策追溯），写 dual-readable methodology 博文
- Inputs: docs/specs/METRICS_AND_TRUST_GATES.md (现 stub) · Notion v0.1
  Draft 内容 · STRAT-002 §3 三段式模板
- Allowed: docs/specs/METRICS_AND_TRUST_GATES.md · docs/methodology/dual_readable_specs.md
  · tools/dual_readability/spec_lint.py
- Forbidden: src/** · knowledge/** · 其他 5 个 Canonical Spec
- Deliverables: (a) METRICS spec 三段式重构 (b) tools/dual_readability/
  spec_lint.py 强制 spec 必含 TL;DR + agent contract 块 (c) docs/methodology/
  dual_readable_specs.md 1500+ 字博文 (d) SPEC_PROMOTION_GATE.md §G-A
  追加 dual-readability 硬门
- Acceptance: (1) METRICS spec 通过 spec_lint (2) Codex 与人类同时 ground
  下游决策（CFDJerry 验收） (3) 博文可发布
- Reject: spec_lint 不可执行 · methodology overfits one spec · 博文 < 1000 字

#### Q6 · First paid pilot signal (gate)
- Phase: Q · Prio: P0-gate · Status: Inbox
- Goal: 1 家公司同意 $5k/月 60-day pilot 或明确 5 候选全部 NO
- Inputs: Q4 5 段访谈结果 · cfd-harness PyPI 包 · LDC demo 视频
- Allowed: 销售/沟通工作（不写代码）
- Forbidden: ALL（这是 gate，不是实现）
- Deliverables: (a) signed pilot agreement OR (b) 5 候选明确 NO + 重评估 Q 轨
- Acceptance: (1) ≥ 5 候选实际接触 (2) 渲染清晰 yes/no decision
- Reject: < 5 候选 · 无明确决策

**C.3 · Codex 独立验证**：fetch 新建的 Q-Phase + 6 task 页面，验证：
   1. Q-Phase 在 Phases DB · parent = 项目主页 · Status=Active
   2. 6 个 task 在 Tasks DB · 全部关联 Q-Phase
   3. 每个 task body 含 6 段合同结构
   4. Q3 任务 body 含 "License = TBD (待 CFDJerry 签字)"
   5. Q1 + Q2 + Q6 prio = P0 / P0-gate

任一项 FAIL → STOP。

---

## 4. 完成报告 template

3 个 BLOCK 全部 PASS 后，输出：

```
═══ KICKOFF-PIVOT-v1.1 EXECUTION REPORT ═══
Block A: PASS / Codex verify rounds: N
Block B: PASS / Codex verify rounds: N
Block C: PASS / Codex verify rounds: N

Notion artifacts created:
- DEC-PIVOT-2026-04-22-002 · <url>
- Pivot Charter v1.1 amendment · <url>
- Q · Commercial Surface Phase · <url>
- Q1..Q6 task pages · <urls>

Notion artifacts modified:
- 项目主页: 2 callout 替换 + Snapshot +1 行 + Phase 表 +1 行 + Top-10 +6 行 + 风险 +1 条
- Pivot Charter v1.0: Version 属性 only

Repo touched: NONE (本会话不动 repo)

Followup needed:
- CFDJerry 签 Q3 license 决策（否则 Q3 阻塞）
- 主线 main driver 决定何时启动 Q1（rotate token 是工程动作，需要 main driver 操作）
- 监测主线 P1 是否被 Q 轨干扰（按 Pivot v1.1 §8 主线 > Q 规则）

Next session: 主线 P1 继续 OR Q1 token rotate（CFDJerry 决定）
═════════════════════════════════════════════
```

## 5. 不可越过的边界

- **不动 repo**（含 .planning/STATE.md · 含 src/ · 含 knowledge/ · 含 docs/）
- **不动 Pivot Charter v1.0 正文**（只改 Version 属性）
- **不动 Foundation-Freeze 状态**（不改 15-case Whitelist）
- **不擅自定义 Q3 license**（D6 锁定 = TBD by CFDJerry）
- **不修改 6 个 Canonical Spec 的 Status**（仍是 Draft v0.1）
- **不删除任何已存在 DEC / Phase / Task**（全部 append-only）
- **任意 BLOCK 的 Codex 独立验证 FAIL → STOP** 等 CFDJerry，不要 retry > 1 次

## 6. v6.2 协议头（commit trailer 仅在最终 repo 工作时使用，本会话无 commit）

Execution-by: claude-code-opus47
Subagent: <id-if-dispatched>
Codex-verified: KICKOFF-PIVOT-v1.1@<notion-fetch-hash>
Heterogeneous-verifier: codex-gpt-5.4-xhigh

═══ END OF KICKOFF PROMPT ═══
```

---

## 使用说明

1. 复制上方代码块（不含 ```text 标记）粘贴到新开的 Claude Code CLI session 第一条消息
2. Claude Code 启动时会先读取 v6.2 Takeover Prompt（Notion 页 36e95c75491240faa25741eedcedc670），本提示词作为承接 task 触发
3. 如果 Claude Code 在任何 BLOCK 报 STOP，把它的 STOP 报告 + 你的裁决一并粘贴回 Notion 主页评论区或新开 Decisions DB 条目
4. 完成报告（§4）落地后，把 KICKOFF-PIVOT-v1.1 标记为 `notion_sync_status: synced` 在 Decisions DB DEC-PIVOT-002 行

## 异常处理

- **Codex 不可用** → BLOCK 内的独立验证降级为 Claude 自我 fetch 验证（在 STOP 报告中标注 `codex-unavailable-fallback-claude-self-verify`）
- **Notion API quota 命中** → STOP，等 24h 重试，不要分批跨多次会话
- **CFDJerry 中途撤回任一 D 决策** → STOP 当前 BLOCK，回滚已落地的 Notion 修改（Notion 页面历史可一键 revert），等新决策

---

**Memo END**
