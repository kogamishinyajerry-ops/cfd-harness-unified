---
memo_id: STRAT-2026-04-26-001
title: 战略架构顾问备忘录 — cfd-harness-unified 北极星收敛
author: Claude Sonnet 4.6 (advisory pass; not in v6.2 main-driver loop)
date: 2026-04-26
audience: Kogami / CFDJerry, 任何继任 Main Driver
scope: 综合 repo + Notion 控制面 + Pivot Charter + 6 Canonical Specs + Codex review arcs，回答四问 — 架构、价值、产品形态/交互、开发路径
status: advisory only · NOT a DEC · 任何采纳条目须开 DEC
related:
  - docs/product_thesis.md (2026-04-20 Path-B election)
  - docs/governance/PIVOT_CHARTER_2026_04_22.md
  - docs/specs/SPEC_PROMOTION_GATE.md
  - .planning/retrospectives/2026-04-22_v61_counter32_retrospective.md
  - .planning/decisions/2026-04-22_demo_first_convergence_dec046_multi_persona_codex_review.md
  - .planning/external_gate_queue.md
---

# 战略架构顾问备忘录

## §0 一句话定位（不同于 product_thesis.md）

你正在打造的不是「合规审计 SaaS」，而是 **「AI 时代 CFD 物理可信度的最小可信内核（Trusted Kernel）」** ——
一个把 *物理契约 → 异质验证 → 不可抵赖凭证 → 治理留痕* 串联成单条管线的中间件。`product_thesis.md` 把它包装成合规产品是**次优定位**：合规市场买你的"凭证"，但 AI-CFD 市场买你的"内核"。两者用同一套代码，但叙事、定价、分发渠道完全不同。

下面分四章把这个判断的依据和落地路径讲透。

---

## §1 项目架构现状 — 四层切片

把 repo + Notion 一起切片，能看到一个**四层结构**，每层成熟度不一：

| 层 | 物理位置 | 当前成熟度 | 真正壁垒度 |
|---|---|---|---|
| L1 知识层 (Knowledge Plane) | `knowledge/whitelist.yaml` (10 cases) + `knowledge/gold_standards/*.yaml` (15 文件) + `physics_contract` 块 | **8/10 PASS · 2 HOLD (paywalled)** · 但很多 `gold_standard` 是合并多论文的 blended anchor (e.g. BFS Le/Moin/Kim + Driver) | **高** — 物理契约的精确性是无法被 LLM 一夜复制的。Q-5 LDC 的 Ghia 重转录、Q-2 R-A-relabel、DEC-V61-050 ψ 提取器都是真实 domain expertise |
| L2 验证层 (Verification Plane) | `src/auto_verifier/` (L1+L2+L3) + `src/audit_package/` (HMAC + L4 manifest) + 残差/收敛 attestor A1..A6 (DEC-V61-038) + 5 hard gates G1-G5 (DEC-V61-036) | **运行中** · LDC ATTEST_PASS · byte-reproducibility 已验证 · `comparator_verdict` 三态分裂 (contract / profile / attestation) | **高** — 这是产品的工程性壁垒。把 attestor + gate + suggestion + signing 串成一条**确定性、可重放、可审计**的管线，比单独任何一块都难复制 |
| L3 治理层 (Governance Plane) | `docs/specs/SPEC_PROMOTION_GATE.md` + `docs/governance/PIVOT_CHARTER_2026_04_22.md §4.3a` + `docs/governance/POLICY_COMMITMENTS_LEDGER.md` + ADWM autonomous-governance counter + Codex 独立验证 protocol | **超规格** · 6 Canonical Specs 全部 Draft v0.1 · 6 道硬门审查标准已签发 · Foundation-Freeze 生效中 | **极高 · 但当前未变现** — 多 LLM 协同 + counter 自治 + Codex 独立异质验证这套**方法论**本身是可独立产品化的资产，但目前完全是内部工具 |
| L4 表面层 (Surface Plane) | `ui/backend/` FastAPI 17 routes + `ui/frontend/` React (`/learn` 教学壳 + `/pro` evidence 壳) + `run_notion_hub_sync.py` 双向同步 | **教学壳 demo-ready · pro 壳 evidence-heavy** · 默认路由已翻 / → /learn (DEC-V61-035) | **低** — UI 不是壁垒，是包装。当前的两壳分裂表明你也知道这一点 |

**关键观察**：
- L1 + L2 是**实质性产品**；L3 是**未释放的 IP**；L4 是**最容易被替换的层**
- 你目前在 L4 投入的工程比例（17 个 backend routes + React 双壳）和它的战略价值不成比例
- L3 的成熟度和体量（6 Canonical Specs + Pivot Charter + Spec Promotion Gate）远超一个单人项目应有的水平 —— 这是好事，但目前**只在内部消耗**，没有外溢成产品

---

## §2 Notion 中枢的真实价值（被低估）

`config/notion_config.yaml` + `run_notion_hub_sync.py` + 5 个 DB schema 看起来只是个项目管理工具，但放在产品视角下它是**整个项目最容易被外部客户复用的资产**。原因：

**(a) 你已经把 V&V 工作流"实例化"成了 schema**：
- Tasks DB (`2b25c81b...`) — 每个 case run 是一个 task
- Decisions DB (`fa55d3ed...`) — 每个 ADR / DEC 是不可变留痕
- Canonical Docs DB (`96a6344f...`) — Gold Standard / Spec / Correction 都是文档对象
- Phases DB (`25a50aa2...`) — 阶段 gate 状态
- Sessions DB (`7905136d...`) — 每次 LLM 协同会话

**这个 schema 几乎是一个标准的"V&V campaign 项目结构"**。Boeing CFD methods group、FDA V&V40 提交、NASA Langley validation campaign 现在都是用 Word + Excel + 邮件做这件事 —— 你的 Notion schema 就是它们 unmet 的需求。

**(b) 双向同步逻辑是现成的产品**：
`run_notion_hub_sync.py` 把 `knowledge/whitelist.yaml` → Tasks、`knowledge/gold_standards/` → Canonical Docs、`.planning/decisions/` → Decisions DB —— 这个 mapping 本身就是 **"把 V&V 工程项目结构化"** 的产品蓝图。

**战略含义**：
- Notion DB schema 应当作为**第一个对外公开的资产**（开源 schema + sync script），把它变成 OpenFOAM / SU2 社区的 *de facto* "V&V campaign 标准模板"。这是零成本的市场教育。
- 中长期，可以做一个 "V&V Workspace" 产品（Linear-for-CFD-validation），底层是 Notion-style schema，但提供专门的 case 状态机、决策追溯、签字流。这是 §4.3 候选 C 的具象化。

**立刻要修的安全问题**：`config/notion_config.yaml` 第 4 行的 `ntn_*` token 是明文。任何对外开源动作前必须 rotate 并改用 env var 或 secret manager；同时给 `run_notion_hub_sync.py` 加 `--token-env` 默认值校验拒绝读 yaml。

---

## §3 真正的差异化 — 你独有的三件事

把目前能找到的所有 AI-CFD / V&V / OpenFOAM 工具横切对比，你独有的是这三件：

**3.1 物理契约 schema 的"精度等级表态"**
其他工具的 reference value 都是单数字 + 容差。你的 `physics_contract` 块强制每个 precondition 写：
```yaml
- condition: "..."
  satisfied_by_current_adapter: true | false | partial
  evidence_ref: "<file:line> 或 DEC ID"
```
这是 **structured honesty**。`partial` 这个三态值（DEC-V61-046 R3-B1 才修好的 bool() bug）是 `compatible_with_silent_pass_hazard` 这个完整概念的语法显形。**没有任何商业 CFD 工具做这件事**。这本身可以注册成方法论商标 / 写论文 / 进 ASME V&V 标准提案。

**3.2 三态 verdict（contract / profile / attestation）+ HAZARD 等级**
LDC 是这套体系的最佳广告：
- `contract_status = FAIL`（标量 u_centerline 偏离 Ghia）
- `profile_verdict = PARTIAL` (11/17 within 5%)
- `attestation = ATTEST_PASS`（A1-A6 全绿，求解器收敛健康）

把这三个 verdict 同时打在 UI 上，是**直接给客户演示"为什么单一 PASS/FAIL 是诚实性灾难"**。这个 demo 的杀伤力不亚于 Tesla 自动驾驶第一次 demo lane-change。

**3.3 Codex-as-independent-verifier 协议**
RETRO-V61-003 (counter=32) 给出了硬数据：
- 5 个 code-bearing DEC（V61-040/042/043/044/041）的 Codex round-1 全部 CHANGES_REQUIRED
- DEC-046 是 3-persona 多角色 Codex review 走了 3 轮才 APPROVE_WITH_COMMENTS
- DEC-V61-045 单 DEC 跑了 4 wave + 2 Codex verify pass

**这意味着你的代码"自报 80% 通过率，独立验证只有 0% 一次过"**。这个 calibration delta 在所有 LLM-coding 产品里都是黑箱 —— 你已经把它白盒化了。**这套异质验证 protocol 应该是你下一篇博文 / 学术 paper / Anthropic 用例报告的核心**。

---

## §4 产品方向收敛 — 三条北极星深度评估

把第一次回复里的 A/B/C 用更严格的标准重新打分：

| 维度 | A. AI-CFD Trust Gate | B. Audit-Package SaaS (现 thesis) | C. AI-CFD Knowledge OS |
|---|---|---|---|
| 你独有 vs 别人能抄 | **极高** — Codex+attestor+contract 全栈 | 中 — ANSYS 2027 可能做 | **极高** — methodology + schema + agent loop 协议化 |
| 时间窗口 | **18-24 个月** — LLM CFD agent 还没赢家 | 36-60 个月 — 监管驱动慢 | **18 个月** — agent 工程方法论现在是空地 |
| 单一客户验证成本 | **低** — 找 5 个 LLM CFD 用户访谈即可 | 高 — 合规官买单要先过法务 | 中 — 需要 1 个 lighthouse 团队 |
| MVP 距离 | **4-6 周** — AutoVerifier 拆 PyPI 包即可 | **完成中** — 但客户验证未启动 | 8-12 周 — 需要把 Notion schema + governance loop 拆出来 |
| 第一年 ARR 上限 | $500k-$1M | $200k-$800k (慢) | $1M-$3M (lighthouse + community) |
| 5 年 TAM | $50M-$200M (AI CFD 工程团队) | $50M-$100M (regulated CFD) | $500M-$2B (AI 工程信任度产品) |
| 死亡风险 | LLM 大厂自建（NVIDIA Modulus 加 verifier） | ANSYS 加内置审计 | 概念过于前沿没人买 |
| 与现有代码契合度 | **9/10** — 最小改动 | 7/10 — UI/合规面要重做 | 6/10 — 要把 governance 抽象到产品层 |

**我的判断**（不是默认结论，是基于上面打分）：
1. **A 是 wedge** —— 4-6 周能给市场看到"差异化的最小可信产品"，零售转化效率最高
2. **C 是平台 endgame** —— 但需要先用 A 站住脚再走
3. **B 不再是主线** —— 它过于慢、买家说不通、ANSYS 反扑窗口短。但**不要废弃 B 的工程产物**：HMAC-signed audit package 是 A 客户的*高级特性*，是 C 客户的*核心数据格式*

具体说，**你应该在 4 周内做的产品形态**：

```
cfd-trust-gate (PyPI 包)
├── verify(case_dir, contract_id) -> Verdict   ← AutoVerifier 的最小入口
├── attestation(case_dir) -> A1..A6 status     ← convergence attestor
├── physics_contract.load(contract_id)         ← 加载 10 个 Gold Standard 之一
├── audit_package.build(...) -> signed bundle  ← 已有的 HMAC 签名包
└── notion_sync(workspace_id) -> bool          ← optional, sells the SSOT vision
```

这个包**不要 web、不要 React、不要 Notion 强依赖**。它是一个 `pip install cfd-trust-gate` 就能跑的库，让正在用 NVIDIA Modulus / Foam-Agent / 自建 LLM agent 的工程师**今天下午就能集成**。这是 A 的 wedge。

---

## §5 12 周 / 6 个月 / 18 个月路径

### 12 周 — 验证 A 北极星

**Week 1-2 · 客户问题验证**（不写代码）
- 在 OpenFOAM Discord、Foam-Agent issue tracker、r/CFD、几个 LLM CFD 工程师推上发"你怎么验证 LLM 写的 OpenFOAM case 是对的"问卷
- 目标：5 段录音 + 5 段书面回答
- 决策点：≥3 段能描述出"我现在没有 systematic 方法验证 agent output"，A 通过；否则回看 C

**Week 3-6 · cfd-trust-gate v0.1 PyPI 发版**
- 拆 `src/auto_verifier/` 为独立包，不依赖 ui/backend
- 拆 `src/audit_package/` 为可选子模块
- 把 10 个 `knowledge/gold_standards/*.yaml` 作为内置 contract library
- 写 `README.md` 一个杀伤力 demo：让 GPT-4 写一个 LDC OpenFOAM case → `verify()` 出 PARTIAL → 给出 correction suggestion
- **关键**：发版前 token rotate + 把所有 Pivot Charter / SPEC_PROMOTION_GATE / DEC-V61-* 隐藏到 `internal/` 子目录，不出现在 PyPI 包里

**Week 7-9 · 真正跑通剩下 2 个 HOLD case**
- impinging_jet (Behnad 2013 paywalled) — 找替代 Cooper-Wang 1981 / Jambunathan 1992 数据
- rayleigh_benard_convection (Chaivat 2006 paywalled) — Kerr 1996 / Niemela 2000 是更好的 anchor
- 目标：10/10 PASS，不是为了 contract claim，是为了 Week 10 demo 的"wall of green"

**Week 10-12 · 第一次外部 demo + 公开博文**
- 写 1 篇博文「Codex 5 轮才让我代码合格 —— 一个单人 + 多 agent 的 CFD 验证项目工程实录」（这是你独有的内容资产，没人能抄）
- 1 个 5-min demo 视频：LLM 写 case → trust gate verify → HAZARD 警示 → correction suggestion
- 把 Notion schema 公开成开源 template
- 决策点：博文 + 视频 上线 30 天后 GitHub stars > 100 / `pip install` > 200 / 邮件咨询 ≥ 3 → A 验证；否则回看 C

### 6 个月 — A 客户化 + C 雏形

如果 12 周 A 通过，6 个月节奏：
- 把 cfd-trust-gate 包装成 hosted service（最小 hosted SaaS：上传 case → 跑 verify → 出 PDF/JSON）
- 找 1-2 个 design partner 做 paid pilot（$2k-5k/月，免费换 60 天反馈）
- 开始把 `governance/` 层抽象成 *AI 工程信任度产品* 雏形 —— Codex review protocol + ADWM counter + Spec Promotion Gate 6 hard gates 这一套，对外讲叫 **"Multi-LLM Engineering Discipline"**。这是 C 的 v0.1。
- Notion 整合做成可选企业版：客户接他们自己的 Notion，自动落 Decisions / Sessions

### 18 个月 — A 站住，C 出场

- A 进入 100 客户 / $1M ARR 区间（按 $1k-$2k/年/座 + 10x team 价定价）
- C 在 1-2 家 lighthouse 客户（理想画像：Boeing R&D group, 或 Blue Origin 的内部 CFD 工具组）做内部部署
- B 的 audit-package 能力变成 A/C 的高级 SKU（不是独立产品线）
- 写一篇方法论 paper 投 ASME V&V 或 ICCFD —— 把 "physics contract + Codex verifier + ADWM counter" 作为 AI 工程实证方法论提交学术界

---

## §6 立刻要做的「停 / 启 / 续」

| 类别 | 项 | 理由 |
|---|---|---|
| **停** | 新增 Canonical Spec / 新增 Pivot Charter 子条款 / 新增 ADR | 6 spec 全 Draft，再加是字面意义的过度治理。先 promote 1-2 个再说 |
| 停 | 在 React 前端继续投入新功能 | 已有 UI 工程量过大，没有客户。冻结当前能力，全部精力给 PyPI 包 |
| 停 | Phase 9 / Phase 10 规划 | 在没有外部客户验证 A 之前，所有"未来 phase"都是猜测 |
| **启** | `cfd-trust-gate` PyPI 包拆包工作 | wedge 的最小动作 |
| 启 | 5 个外部工程师访谈（不卖产品，只问问题） | 验证 A 北极星 |
| 启 | Token rotate + secret manager | 任何对外动作的前置 |
| 启 | `learn-demo` 视频录制 | 你的 LDC 三态 verdict 是杀手 demo，没人在用 |
| **续** | Foundation-Freeze（不加 case） | 政策正确，但理由从"等 P1 完工"改成"等客户验证 A" |
| 续 | Codex 独立 review 流程 | 这是你的代码质量护城河，别动 |
| 续 | Notion DB SSOT | 但要把 token 入 secret，且把 schema 准备好"开源化" |
| 续 | 10 case PASS 收尾（解 paywalled HOLD） | 这是 demo 的"满绿墙" |

---

## §7 我留给你的三个开放战略问题

写完这份 memo 还剩三个我无法替你判断的问题，建议你单独想 2-3 天再决定。

**问题一**：你想做的是产品 or 资产？
- 产品 = $1M-$10M ARR，3-5 年退出，需要客户、销售、CS
- 资产 = 写一篇 ASME V&V paper 进标准、把方法论开源拿 GitHub 5k stars、用名声进顶级 CFD lab / 大厂职位
- 这两条路在 0-12 个月几乎一样（都要 PyPI + 客户验证 + 博文），但 12 个月后分叉。你要在心里先选

**问题二**：你愿意离开 solo + agents 模型吗？
- 当前 setup（你 + Opus + Codex + GLM）能撑到 $500k ARR 的天花板。再往上必须招人，但你目前的 governance 体系（Pivot Charter §4.3a / SPEC_PROMOTION_GATE 6 hard gates）对**人类协作者**的可读性极低
- 如果不愿离开，C 路径（platform play）做不到。如果愿意，要在 6 个月开始 hire 一名 GTM 人选

**问题三**：Notion 是助手还是产品？
- 助手：repo 是 SSOT，Notion 是镜像，token 自用
- 产品：开源 schema + sync script + workspace template，把"V&V campaign 项目结构"作为社区资产捐出去
- 这两个选项的张力在 `docs/governance/PIVOT_CHARTER §0` 已经写过（"对 §1-§4.3 / §5-§9 以 Notion 为准；对 §4.3a 以本文件为准"）—— 你已经感受到了双 SSOT 的代价。这次必须选

---

## §8 不签字、不加 DEC、不进 governance 队列

这份 memo 是**纯顾问意见**，不进 ADWM counter、不触 Foundation-Freeze、不需要 Codex review。任何被你采纳的条目，**必须开 DEC** 走正常 governance；这份 memo 本身不构成承诺。

如果你想把其中某条变成 actionable，建议路径：
1. 选 §6 表格里的 1-3 条「停 / 启」
2. 开 DEC-STRAT-001 引用本 memo + 选项
3. 走 autonomous_governance 路径（counter+1）或 Opus Gate（如果触 Pivot Charter §4.3a）
4. 落 commit + Notion sync

— 完 —
