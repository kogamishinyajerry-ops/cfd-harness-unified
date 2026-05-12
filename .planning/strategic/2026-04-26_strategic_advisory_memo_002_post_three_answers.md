---
memo_id: STRAT-2026-04-26-002
title: 战略路径收敛 — 基于「产品 / 离开 solo / Notion 是助手」三答案的更新
author: Claude Sonnet 4.6 (advisory pass; not in v6.2 main-driver loop)
date: 2026-04-26
audience: Kogami / CFDJerry · 任何继任 Main Driver / 第一位 hire
scope: 在 STRAT-2026-04-26-001 基础上，结合 Notion Pivot Charter 实际状态 + 用户三答案，给出收敛后的产品路径、双重可读性方法论、团队过渡设计
status: advisory only · NOT a DEC
related:
  - .planning/strategic/2026-04-26_strategic_advisory_memo.md (前置)
  - https://www.notion.so/Pivot-Charter-2026-04-22-CFD-Harness-OS-70e55a0c3f924736b0cb68add01d90cd (CFD Harness OS 新北极星)
  - docs/product_thesis.md (与 Pivot Charter 矛盾，需重写)
  - docs/governance/PIVOT_CHARTER_2026_04_22.md §4.3a (repo addendum)

three_answers_received:
  Q1_product_or_asset: 产品
  Q2_team_or_solo: 可离开 solo + agents，但必须保留 Agent 可读性
  Q3_notion_role: 助手 (repo SSOT)
---

# 战略路径收敛 — Post Three Answers

## §0 一句话更新

你的 Notion 已经做了战略动作，repo 还没赶上。**Pivot Charter (2026-04-22) 把北极星从 "regulated CFD audit" 改成了 "CFD Harness OS / Case Intelligence Layer"，但 `docs/product_thesis.md` 还在讲合规审计 SaaS**。三个答案锁死后，路径变成：

> **以「Case Intelligence」为产品名 → 6 周做出可付费 v0.1 → 6 个月做出第一个付费客户 → 12 个月做出第一个 hire 能融入的工程结构**

下面把这条路径拆开。

---

## §1 战略错位首先要修

`product_thesis.md` 和 Pivot Charter 现在指向两个产品。**必须二选一，不能同时维护**。

| 维度 | `product_thesis.md` (Path B) | Pivot Charter (CFD Harness OS) |
|---|---|---|
| 客户 | 合规官 | CFD methods group / R&D 主管 |
| 卖点 | 一键签名审计包 | Case Intelligence + Trust Gate + Correction Loop |
| 价格 | $25k-$60k/seat/年 | 按 case volume 或 workspace seat |
| 工程产物 | UI + audit-package | 四层架构 + 8 类知识对象 + MetricsRegistry |
| 时间窗口 | 36-60 月（监管驱动） | 18-24 月（AI CFD 工具空白窗口） |

**判断**：Pivot Charter 是更强的产品定位。理由：
1. **市场窗口对** —— AI CFD 工具的"信任层"现在没有龙头
2. **买家说得通** —— CFD 工程主管对"Case Intelligence" 的痛感远比合规官对"V&V40 audit pack" 强
3. **产品复杂度对你的 setup 友好** —— 你已经有四层架构骨架，audit-package 只是其中一个 export 通道
4. **你的差异化最强** —— 8 类知识对象 (CaseProfile / SolverRecipe / MeshRecipe / BCRecipe / ObservableDefinition / FailurePattern / CorrectionPattern / ProvenanceRecord) 是没人在做的护城河

**第一个动作**（本周）：
- 把 `docs/product_thesis.md` 标记为 SUPERSEDED；新写 `docs/product_thesis_v2.md` 对齐 Pivot Charter 北极星
- 走 DEC-V61-NNN（autonomous_governance）记录这个对外定位转向
- Notion Decisions DB 加 `DEC-PRODUCT-001 · Path B audit-SaaS pivoted to CFD Harness OS`

---

## §2 「Case Intelligence」作为产品名 —— 为什么这个 framing 赢

「CFD Harness OS」是工程内部叙事，对外卖不动（OS 这个词太宽泛）。「Case Intelligence Layer」是销售可用的 framing，原因：

**(a) 它把"知识"显形为可交付物**：
- 客户买的不是"工具"而是"15-200 个验证过的 case 物理契约 + 可运行 recipe"
- 类比：Hugging Face 卖的不是 transformers 库，是 Model Hub。你的 Case Hub 是同一个商业模型

**(b) 它解释了为什么客户不能 ChatGPT 自己写**：
- LLM 能写 OpenFOAM case，但写不出经过 Codex 5 轮 review + ATTEST_PASS + Ghia 1982 真值校准的 case
- 你的 8 类对象 + Provenance + 三态 verdict 是 "为什么这个 case 比 GPT 写的可信" 的物证

**(c) 它有清晰的扩展曲线**：
- v0.1: 10 cases (现有) - 免费下载，开放给社区
- v1.0: 50 cases (覆盖航空、汽车、HVAC) - $5k/年订阅
- v2.0: 200 cases + 客户私有 case 托管 - $20k-$80k/年
- v3.0: 客户提交他们的 case → 你的 trust gate → 自动 enrollment 到 hub - 平台模式

**对外定位一句话**（候选，给你挑）：
- A. *"Case Intelligence Layer for AI-Driven CFD"*
- B. *"The trusted case library for OpenFOAM agents"*
- C. *"Don't let your CFD agent ship hallucinated physics"*

我推 C。攻击性强、目标受众准、记忆点清。

---

## §3 双重可读性 —— 真问题，可以解

你的第二个答案 ("人类可读 + agent 可读") 是这次回答里最有产品价值的一个约束。**多数文档重构会把 agent 可读性破坏掉**，因为人类喜欢的"删冗余、铺平结构、白话化"恰恰删掉了 agent 用来 ground 决策的语义骨架。

**解法不是"二选一也不是平均"，而是分层注释 + 单源生成**：

```
docs/specs/SOME_SPEC.md
├── 顶部 TL;DR (200 字以内 · 人类阅读)
├── ## 工程意图 (1-2 段 · 人类阅读)
├── ## 给 LLM Agent 的合同 (machine-parseable section)
│   ├── input_schema: <YAML>
│   ├── output_schema: <YAML>
│   ├── invariants: [list]
│   └── failure_modes: [list]
├── ## 实现细节 (现有 spec 内容 · 给执行者读)
└── ## 决策追溯 (DEC-* + Codex review log links · 给审计读)
```

**关键设计原则**：
1. **machine-parseable section 永远是 YAML / JSON 块**，不是 prose。Codex / Opus / Sonnet 都能 grep 和 reason。
2. **TL;DR 是给新员工 / 客户 / 对外博文用的**。LLM 也读但不依赖。
3. **决策追溯块永远在文末**。新员工可以跳过；agent 写代码时必读以避免重蹈覆辙。

**具体落地建议**（用你现有的 `SPEC_PROMOTION_GATE.md` 改造为示范）：
- Week 1: 给 6 个 Canonical Spec 之一（建议 `METRICS_AND_TRUST_GATES`）做这个三段式重构试点
- Week 2: 写一个 `tools/spec_lint.py` 强制新 spec 必须有 TL;DR + agent contract 段
- Week 3: 把改造模板写进 `SPEC_PROMOTION_GATE.md §G-A` 作为新晋升硬门
- Week 4: 用一篇内部博文 `docs/methodology/dual_readable_specs.md` 把这个方法论沉淀

**为什么这是产品资产，不只是内部规范**：
- 任何 AI-engineering 团队都遇到这个问题
- 你已经有真实数据证明它 work（DEC-V61-046 三角色 Codex review 跨 3 轮收敛）
- 一篇 Anthropic blog "How a solo CFD engineer built dual-readable specs for multi-LLM teams" 会被几千人转发，免费品牌建设

---

## §4 「离开 solo」的过渡设计 —— 6/12/18 个月

你愿意离开 solo，意味着 **6 个月内会出现第一个 non-Claude 协作者**（人类）。当前 governance 体系（Pivot Charter §4.3a / SPEC_PROMOTION_GATE 6 hard gates / autonomous_governance counter）对人类不友好的程度，会决定你 hire 的成败。

### 6 个月（一名 hire）：让架构师级别的工程师能上手

**画像**：5+ 年 CFD/scientific computing 经验，能读 OpenFOAM dictionary，写过 pytest，懂一点 LLM agent。**不要找 ML 工程师**，找懂 CFD 的 SWE。

**6 个月之前必须做的工程工作**：
- (a) 把 `.planning/decisions/` 下的 50+ 个 DEC 文件按 Phase 重新组织到子目录，加 `.planning/decisions/INDEX.md` 给人类查询用
- (b) 写一份 `docs/onboarding/FIRST_30_DAYS.md`，目标是新人 30 天内能独立 close 一个 P1 task
- (c) 把 Pivot Charter §4.3a 的 (a)/(b)/(c) 三档转化为人话：「你能改什么 / 你必须开 DEC 才能改什么 / 你必须找 Kogami 签字才能改什么」
- (d) `~/CLAUDE.md` 里所有的 v6.2 / counter / autonomous_governance 术语，配一份 `~/HUMAN_GUIDE.md` 平行版

### 12 个月（2-3 名 hire）：让团队能独立运行

**触发条件**：first paying customer 签约 6 个月后 ARR > $200k → 招第二人 (sales/CS)；> $500k → 招第三人 (frontend/devrel)。

**关键设计**：**不要让 Codex / Opus 4.7 退休**。他们是你的真正杠杆。设计应该是 "1 人类 main driver + N agents + 1 human reviewer"，而不是 "纯人类团队"。原因：
- 你已经验证了这套 setup 能产 production-grade 代码
- 人类比 LLM 贵 100x；除非任务本质需要人类（销售、客户拜访、设计 judgment），否则保留 LLM
- 你的"独立异质验证"协议是真正的 IP，不能因为有了人就废掉

**必须出现的角色**：
1. **Tech Lead (你)** —— 架构、北极星、客户 escalation
2. **Lead Engineer (hire #1)** —— 主驱动 P1-P6 phase work，配 Codex
3. **Customer Engineer (hire #2)** —— 客户 onboarding + custom case 生成 + 反馈回流
4. **Devrel / Marketing (hire #3)** —— 博文、demo、社区、open-source registration

### 18 个月（5 人小团队）：进入产品公司形态

- 选项 1: **不融资走 bootstrapped** —— 5-7 人 + $1-3M ARR + 60-80% 毛利。可以无限期持续。
- 选项 2: **融资 seed $2-3M** —— 加速团队 + 进入更多垂直市场（汽车 / HVAC / power gen）。给自己 24 个月跑到 Series A。

**18 个月之前的工程必须做完**：把 Pivot Charter §4.3a 的所有 hard rule 都从"靠 governance 文档强制"转移到"靠 CI / pre-commit / lint 自动强制"。governance docs 仍在，但只对 agent 重要；人类靠 tooling。

---

## §5 12 周路径细化（替换 STRAT-001 的 §5）

基于产品方向 = CFD Harness OS / Case Intelligence Layer：

### Week 1-2 · 战略对齐 + 安全前置

| 项 | 文件 / 动作 |
|---|---|
| Token rotate | `config/notion_config.yaml` 改 env var，全 git history rewrite (BFG) |
| Product thesis 重写 | `docs/product_thesis_v2.md` 对齐 Pivot Charter；`product_thesis.md` 加 SUPERSEDED 头 |
| Notion 主页 add 一行 | "Pre-paid pilot 询问 → kogamishinyajerry@gmail.com" CTA |
| 5 个外部访谈 | OpenFOAM Discord / r/CFD / Foam-Agent issues / X CFD 社区 → 1h 每人，问 "你怎么验证 LLM-written case" |

### Week 3-6 · `cfd-harness` v0.1 PyPI 包

不要叫 `cfd-trust-gate`（太狭窄），改叫 `cfd-harness`，对应 Pivot Charter 的 OS 定位。

```python
# 公开 API 设计
from cfd_harness import Case, verify, audit_pack

case = Case.from_openfoam_dir("./naca0012_run_42")
verdict = verify(case, contract="naca0012_airfoil")
# verdict.contract_status, verdict.profile, verdict.attestation

if verdict.requires_review():
    pack = audit_pack(case, verdict, sign_with="hmac")
    pack.export_html("./report.html")
```

**包里包含**：
- 10 个内置 contract (从 `knowledge/gold_standards/`)
- AutoVerifier 三层 + attestor A1-A6
- Audit-package builder + HMAC signer
- 不包含 UI / Notion 同步 / governance docs

**不包含**：
- React frontend (留给 hosted SaaS)
- 任何 `from src.diff_lab` 内容
- Pivot Charter / SPEC_PROMOTION_GATE 这些治理文档

**发版动作**：
- `pip install cfd-harness` → 5 行 README demo
- 配套 GitHub Action: `uses: cfd-harness/verify-action@v1` 给 OpenFOAM CI 用户用
- 发到 OpenFOAM Discord / Foam-Agent issues / r/CFD

### Week 7-9 · 解锁 2 个 HOLD case + 录 demo

- impinging_jet (Behnad 2013 paywalled) → 找 Cooper-Wang 1981 / Jambunathan 1992 替代
- rayleigh_benard_convection (Chaivat 2006 paywalled) → Niemela 2000 / Kerr 1996 替代
- 拿 LDC split-brain demo 录 5 分钟视频：`contract=FAIL · profile=11/17 · attestation=ATTEST_PASS` 三态展示

### Week 10-12 · 第一个付费 pilot 谈判

- 目标：1 家公司同意 $5k/月 pilot 60 天
- 理想画像：用 OpenFOAM 的 SaaS 公司 (SimScale 客户群?) / 航空 supplier 的 CFD methods group / 在搞 LLM CFD agent 的早期 startup
- 不要找 NDA-heavy 大公司；他们 6 个月才能采购完
- pilot 不需要 perfect product；需要的是 paid validation that someone wants this

---

## §6 §3 vs §4 之间的冲突警告

「想做产品」和「保留 Agent 可读性」之间存在一个潜在冲突，必须显式说出来：

**做产品意味着 customer-facing surface**——SDK、UI、文档、CLI。这些都是新增"必须人类可读"的 surface area。
**保留 Agent 可读性意味着内部 spec 不能被简化** ——LLM 依赖 dense semantic structure。

**冲突点**：当 hire #1 加入，他会本能地想把 `Pivot Charter §4.3a 防绕过尾句 (Opus 追签 AC-1 · 2026-04-25)` 这种 dense governance text 重写成"团队规则文档"。这一动作会立刻让 Codex / Opus 4.7 的下游 review 质量下降。

**预防方法**：
- 在 hire #1 onboarding 第一天就讲清楚 "这个 repo 有两套读者，你不是唯一的"
- 加一个 lint rule: 任何对 `docs/governance/**` 或 `docs/specs/**` 的 PR 必须保留原 machine-parseable 块；如果要重写，必须双语版本（一段给人，一段给 agent）
- 第一次 review 失败案例要写进 `docs/methodology/dual_readable_specs.md` 当反面教材

---

## §7 一份 30 天 sprint plan（你可以直接执行）

| 天 | 动作 | 产出 |
|---|---|---|
| D1 | rotate Notion token + 改 env | secret 不再泄露 |
| D2-3 | 起草 `product_thesis_v2.md` (CFD Harness OS framing) | 4-page draft |
| D4-5 | 起 `DEC-PRODUCT-001` 走 autonomous_governance | 决策入 Decisions DB |
| D6-10 | 联系 5 个外部 CFD 工程师做访谈 | 5 段录音 + 1 page synthesis |
| D11-15 | `cfd-harness` PyPI 包架构设计 + 接口冻结 | API spec + 1 demo case 跑通 |
| D16-22 | 拆分 `src/auto_verifier/` + `src/audit_package/` + 10 contract YAML 进包 | `cfd-harness==0.1.0a1` 在 TestPyPI |
| D23-25 | 录 5min LDC split-brain demo | YouTube unlisted link |
| D26-28 | 写 1 篇 1500 字博文："Why my CFD agent's PASS verdict is a lie (and how I fixed it)" | Substack draft |
| D29 | METRICS_AND_TRUST_GATES spec 三段式改造（试点） | repo PR + Notion sync |
| D30 | 综合复盘 → 更新 `STATE.md` → 决定 30-60 天下一步 | 1-page retro |

---

## §8 三个还没回答的问题（留给下次决策）

1. **Open source 范围**：`cfd-harness` 包是 MIT 开源还是 BSL（Business Source License，3 年后转 MIT）？BSL 给你商业保护但社区采纳慢。**我的推荐**：先 MIT，等 100 客户后再考虑双 license

2. **Pricing model 第一次试探**：$5k/月 pilot 是 per-seat 还是 per-case？per-case ($50/case verified) 能让客户用得越多付得越多，但定价信号弱。**我的推荐**：per-seat $400/月起，无限 verify，但加 "premium contracts" SKU $200/case 卖你的 hand-curated case

3. **第一位 hire 的语言**：英文 native 还是中文 native？你目前所有 governance + Notion 都是中英混合。**我的推荐**：中文 native + business-fluent 英文，否则你和他沟通成本会爆炸

---

— 完 —
