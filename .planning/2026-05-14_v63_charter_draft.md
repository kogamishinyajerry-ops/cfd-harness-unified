# V63 Charter · Draft Plan-File (3 Candidates · Awaiting User Ratification)

**Status**: `Draft (awaiting user ratification)`
**Plan SSOT**: (placeholder · elevate this file's path here once user selects candidate)
**Predecessor**: V62-A Advisor Stack Closure Arc (closing — 4/6 Done dims MET · Tier 1+2 closed · remaining M-RADAR-V4 + M-V63 in Tier 3)
**Mode**: milestone-driven (no calendar · sustains V61-198 + V62-A precedent)
**Drafted**: 2026-05-14 (in parallel with B36 M-RADAR-V4 build · no file conflict)

> This is a **plan-file**, **not a DEC**. No frontmatter. No `status: Accepted`. User picks one candidate among V63-A / V63-B / V63-C; that selection elevates the file (or its successor) to plan SSOT and unblocks first sub-DEC drafting. v2.3 round-1 loosen rule applies: this draft does **not** sync to Notion (only Accepted DECs do).

---

## Why a 3-candidate plan-file (not a single North Star)

V62-A demonstrated stack-level operationalization on the **mechanism layer** (assembly + 2 routes + 4Q audit + DRIFT-V2 + 2 D-class + 5 Track C retros + 3 distinct numerics classes validated). The next arc has three structurally different **strategic directions** — each viable, each non-overlapping in payoff shape, each consuming different parts of the V62-A asset base. The user, not the planning author, picks the direction.

Comparison table at §5 narrows the trade-off; recommendation at §6 is one to two sentences, deliberately non-prescriptive.

---

## V62-A 未尽事项 (carry-over deferred items · 6 surfaced)

These were surfaced during V62-A but explicitly deferred. Each candidate addresses a different subset:

| # | Item | Source | V62-A disposition | Natural V63 candidate |
|---|---|---|---|---|
| 1 | **D11 `stl_face_label_validator`** | TRACK-1 §8 enh #3 (V94 face-label loss class open) | deferred · D-class candidate | V63-A |
| 2 | **D10 catalog completeness audit** | TRACK-3-rerun retro · STANDARD_OPENFOAM_BCS 61 / ~200 ESI BCs | deferred · case-driven not spec-audit | V63-A |
| 3 | **case_006 substrate input-manifest extension** | TRACK-3-rerun retro · V-row capture 1/9 → 3/9 | deferred · sub-DEC scope | V63-A |
| 4 | **D6 HTTP wire-up** | REQ-SCHEMA-EXPAND scope exclusion (stl_bbox_set not in 5-field set) | deferred · follow-up sub-DEC | V63-A or V63-B |
| 5 | **Frontend wiring of `/api/ai-review` + `/api/ai-diagnose`** | B24+B25 deferred | deferred · workbench UX scope | V63-B |
| 6 | **M-DRIFT-V2 `/api/ai-diagnose` route integration** | DRIFT-V2 sub-DEC §deferred | deferred · audit-mode-default | V63-A or V63-B |

Whichever candidate is chosen, **un-chosen items stay in their natural homes** for future arcs — none are dropped.

---

## Candidate V63-A · "Industrial Scale-Up"

### North Star (一句话)

> **让 advisor stack 在 ≥5 个独立工业 case 上以 100% adoption 跑通 · V-series corpus 扩张到 V100+ · 收齐 V62-A surfaced deferred items (D11 / D6 HTTP / D10 catalog / case substrate 扩展) · 产出 ≥3 篇工业级 e2e validation report.**

### Done Definition (6 dims · all must hit)

| # | 维度 | 起点 (V62 close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Distinct numerics class · 100% adoption | 3 classes (steady-laminar-CHT-multi-stream / compressible-DES-acoustic / compressible_shock_density_based) | **≥ 5 classes 100% adoption PASS** | `grep -E "100% adoption" .planning/retrospectives/*stack_track_c*.md \| sort -u` |
| 2 | V-series corpus size | V51+ (824 LOC in methodology) | **≥ V100 distinct V-rows landed** | `grep -cE "^### V[0-9]+ ·" .planning/methodology/industrial_case_solver_findings.md` |
| 3 | D-class advisor LANDED | 2 (D6 + D10) | **≥ 3 LANDED (D11 candidate)** | `grep -E "D-class.*LANDED" .planning/cross_cuts/advisor_coverage_*.md` |
| 4 | Industrial e2e validation report | 0 (Track C retros are session-shape · not full prep→solve→postp) | **≥ 3 cases with full report (prep → solver → postp · convergence + comparison + V-row attribution)** | `ls .planning/validation_reports/v63_*.md \| wc -l` |
| 5 | V62-A carry-over closure | 6 items deferred | **≥ 4 / 6 items closed (D11 + D6 HTTP + D10 catalog scope + case substrate)** | each closed via sub-DEC with V-row + retro chain |
| 6 | V-row truth-capture rate (canonical case) | 1/9 (case_006 post TRACK-3-rerun) | **≥ 5/9 on ≥1 canonical case · ≥ 3/9 on ≥3 cases** | retro §V-row attribution counter |

### 反命题 (anti-Done · failure modes)

- ❌ 5 cases all on same numerics class → fails dim #1 (must be **distinct** classes)
- ❌ V-row count crossed 100 by inflating with same-pattern entries → fails dim #2 spirit (须 distinct failure-mode signature)
- ❌ D11 LANDED but no case exercises V94 face-label loss → 孤儿 advisor (per V62-A 反命题 template)
- ❌ Validation report counts case_011 + case_016 + case_006 already covered by V62-A retros (no new evidence)

### Triggered redirect (命中 → 修改 plan)

| 条件 | 动作 |
|---|---|
| 商业 CAE AI GA 拿到 ≥3 工业 case ship 证据 | OSS 准备拉前 · V63 部分 milestone defer |
| 任一 milestone 卡 ≥3 周 | 跳过 + retro · 不死等 |
| 用户工作焦点偏离 ≥1 周 (frontend / OSS pull) | 每 Tier 末 redirect 复审 |

### Tier 状态板

#### Tier 1 · 解锁性 (parallel · independent)

- [ ] **M-D11-DRAFT** stl_face_label_validator advisor draft · V94 face-label loss coverage
- [ ] **M-D6-HTTP-WIRE** D6 extra_body_advisor HTTP route plumb · close REQ-SCHEMA-EXPAND scope-out
- [ ] **M-D10-CATALOG-AUDIT** STANDARD_OPENFOAM_BCS catalog 61 → ≥100 BCs · case-driven (not spec-audit-driven) — only extend when case evidence demands

#### Tier 2 · case 扩张

- [ ] **M-CASE-EXT-1** 4th distinct numerics class case (candidate: incompressible-LES-multi-fan / two-phase-VOF / heat-transfer-conjugate-radiation)
- [ ] **M-CASE-EXT-2** 5th distinct numerics class case
- [ ] **M-V100-LANDING** V-series corpus expansion from V51+ to V100 · ≥ 49 net-new distinct V-rows · TRUE NEW signatures (not aliased duplicates)
- [ ] **M-CASE-006-SUBSTRATE** case_006 input-manifest extension (thin_wall_inputs.yaml + interface_bodies.json + interface_specs.json) · V-row capture 1/9 → 3/9

#### Tier 3 · validation reports + close

- [ ] **M-VAL-REPORT-1** Industrial e2e validation report 1 (full prep→solver→postp · convergence + comparison + V-row attribution)
- [ ] **M-VAL-REPORT-2** Validation report 2
- [ ] **M-VAL-REPORT-3** Validation report 3
- [ ] **M-RADAR-V5** Capability radar v5 · scale-up signals (case count / V-row count / e2e report count)
- [ ] **M-V64** V63-A close DEC + V64 charter draft

### 关键依赖图 (V63-A)

```
M-D11-DRAFT       ─┐
M-D6-HTTP-WIRE    ─┤
M-D10-CATALOG     ─┘
       │
       ↓
M-CASE-EXT-1 ──→ M-CASE-EXT-2 ─┐
                                ├──→ M-V100-LANDING ──→ M-VAL-REPORT-{1,2,3}
M-CASE-006-SUBSTRATE  ────────→ ┘                            │
                                                              ↓
                                                       M-RADAR-V5 ──→ M-V64
```

---

## Candidate V63-B · "Frontend Activation"

### North Star (一句话)

> **`/api/ai-review` + `/api/ai-diagnose` 真正接到 workbench UI · 用户能在浏览器里跑 stack-driven CFD prep · workbench 五步主线 (per blueprint v3) feature coverage ≥80% · advisor stack 第一次成为"用户可见的 advisor"而不仅是"API 可见的 advisor".**

### Done Definition (6 dims · all must hit)

| # | 维度 | 起点 (V62 close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Frontend route wiring | 0 (routes LANDED · UI 未消费) | **2/2 routes consumed by ≥1 workbench page each** | `grep -rE "fetch.*ai-(review\|diagnose)" ui/frontend/src/ \| wc -l ≥ 2` |
| 2 | Workbench 5-step coverage (blueprint v3) | ~unknown%, baseline scan in M-FRONTEND-BASELINE | **≥ 80% feature coverage** | `.planning/audits/v63_workbench_coverage.md` 5-step matrix signed |
| 3 | 4Q gate at UI boundary | per-route LLM-offline OK · UI 未审 | **UI 整链路 4Q gate audit + sign-off** | `.planning/audits/v63_ui_4q_audit.md` exists + signed |
| 4 | Dogfood walkthrough | 0 (no user-driven e2e prep flow on record) | **≥ 1 完整 dogfood log: 用户 (or Claude Code session as user proxy) 从浏览器 e2e 跑通 prep flow** | `.planning/dogfood/v63_workbench_dogfood_1.md` 含浏览器截图序列 + V-row 引用 + advisor finding 触发记录 |
| 5 | Industrial-tier UI polish (per Apple-tier feedback) | unknown baseline | **5-step spine + Engineer Control Rail + Artifacts panel 通过 6-pillar audit ≥80%** | `/gsd-ui-review` UI-REVIEW.md ≥80% per-pillar |
| 6 | V62-A carry-over closure | 6 items deferred | **≥ 2/6 closed (frontend wiring + DRIFT-V2 /ai-diagnose route integration)** | sub-DEC chain |

### 反命题

- ❌ UI 加按钮但调 advisor 是 fake / mock → 失败 (V130 advisor-not-driver: AI must actually advise · not stub)
- ❌ 5-step spine rendered but workbench can't run a real industrial case in browser e2e → 失败
- ❌ /api/ai-diagnose 接进 UI 但 LLM-offline 时 UI 报错 → 失败 (违反 V130)
- ❌ Apple-tier polish without functional dogfood (不能"能跑通" ≠ "可交付")

### Triggered redirect

| 条件 | 动作 |
|---|---|
| Frontend pull effort 失控 (>3 weeks single milestone) | 切到 V63-A 或 V63-C |
| Workbench parity build-out 与 N2-N6 (blueprint v3 collapse) overlap ≥50% | 合并 V63-B 与 blueprint v3 roadmap (single SSOT) |
| 商业 CAE AI demo polish ship → 战略压力上 UX | V63-B 拉前 · case 数后置 |

### Tier 状态板

#### Tier 1 · 解锁性 (frontend baseline)

- [ ] **M-FRONTEND-BASELINE** 当前 workbench UI baseline 量化 audit · 5-step coverage / route consumption / UX gap 三维量化
- [ ] **M-ROUTE-WIRE-REVIEW** Wire `/api/ai-review` to ≥1 workbench page · advisor finding rendering · V-row evidence rendering
- [ ] **M-ROUTE-WIRE-DIAGNOSE** Wire `/api/ai-diagnose` to ≥1 workbench page · similarity match rendering
- [ ] **M-UI-4Q-AUDIT** UI 整链路 4Q gate audit (LLM-offline 时所有路径仍可达)

#### Tier 2 · workbench parity + dogfood

- [ ] **M-5STEP-SPINE-1** 5-step spine renderable + 80% feature coverage on Step 1-2 (geometry + meshing)
- [ ] **M-5STEP-SPINE-2** Step 3-5 (physics + BC + solver/postp) coverage
- [ ] **M-CONTROL-RAIL** Engineer Control Rail (per blueprint v3 region 4) functional
- [ ] **M-ARTIFACTS-PANEL** Artifacts panel (per blueprint v3) renderable from real workbench output
- [ ] **M-UI-POLISH-1** Apple-tier polish round 1 · 6-pillar audit ≥75%
- [ ] **M-DRIFT-V2-DIAGNOSE** M-DRIFT-V2 audit-mode wire into /api/ai-diagnose

#### Tier 3 · dogfood + close

- [ ] **M-DOGFOOD-1** User (or Claude Code session as proxy) e2e workbench walkthrough · 1 industrial case · browser screenshot sequence
- [ ] **M-UI-POLISH-2** 6-pillar audit ≥80%
- [ ] **M-RADAR-V5** Capability radar v5 · workbench UX axis activation
- [ ] **M-V64** V63-B close DEC + V64 charter draft

### 关键依赖图 (V63-B)

```
M-FRONTEND-BASELINE  ──┐
                       ├──→  M-ROUTE-WIRE-REVIEW    ──┐
                       │                              ├──→  M-UI-4Q-AUDIT
                       └──→  M-ROUTE-WIRE-DIAGNOSE  ──┘            │
                                                                    ↓
M-5STEP-SPINE-1  ──→  M-5STEP-SPINE-2  ──→  M-CONTROL-RAIL  ──→  M-ARTIFACTS-PANEL
                                                                    │
M-UI-POLISH-1   ──→  M-DRIFT-V2-DIAGNOSE  ──→  M-DOGFOOD-1 ────────→ │
                                                                    ↓
                                                          M-UI-POLISH-2  ──→  M-RADAR-V5 ──→ M-V64
```

---

## Candidate V63-C · "M6 Operationalization" (Claude-Code-Session-As-Advisor)

### North Star (一句话)

> **把 [feedback_claude_code_is_the_advisor] thesis 操作化 — Claude Code session 本身是 M6 advisor · 直接驱动 V-series corpus retrieval / autonomous workflow / 死法模式判断 / e2e 工业 CFD case 决策 · 不依赖 frontend · 不依赖 workbench UI · 就是 session 本身能 e2e 完成 ≥3 工业级 CFD case · 工件留 audit-trail 在 V-series corpus + .planning/.**

### Done Definition (6 dims · all must hit)

| # | 维度 | 起点 (V62 close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Claude Code session e2e CFD case 完成度 | 0 (V62-A Track C 只到 advisor 推 finding · 未到 solver 收敛 + postp validation) | **≥ 3 cases · session 主导 prep → solver → postp 全链路 · 留完整工件** | `ls .planning/dogfood/claude_session_e2e_*.md \| wc -l ≥ 3` 且每篇含 solver log + 收敛图 + V-row attribution |
| 2 | V-series corpus session-tier retrieval recall | 未测 (V-series 现状 lookup 靠 grep) | **≥ 80% recall@5 on ≥20 canonical query** | `.planning/evals/v_series_recall_test.md` 含 20 query + expected V-row + actual top-5 |
| 3 | Autonomous workflow chain length | V62-A Track C ≤ 1 session 一个 case | **≥ 1 case session-chain ≥5 stages (geometry → mesh → physics → BC → solver → postp) 全 advisor-aware** | dogfood log 含 stage 分段 + advisor 调用次数 |
| 4 | Death-pattern detection (per [feedback_claude_code_is_the_advisor]) | implicit (无显式 dataset) | **≥ 10 distinct death-pattern V-row signatures explicitly catalogued · ≥ 3 detected in live session** | `.planning/methodology/death_patterns.md` 含 10 patterns + detection trail |
| 5 | LLM-offline gate at session-tier | per-advisor OK · session-tier 未审 | **session-tier 4Q gate audit: Claude Code session 假设 LLM 可调时 advisor 不退化 · LLM offline 时 ≥1 graceful-degradation 路径** | `.planning/audits/v63_session_tier_4q_audit.md` signed |
| 6 | V-series corpus growth (canonical evals + new patterns) | V51+ | **≥ V80 distinct V-rows · 含 ≥10 death-pattern signatures** | grep count |

### 反命题

- ❌ Session "完成" 一个 case 但没 solver 收敛 (跑了 mesh 没跑 solver) → 失败
- ❌ 10 death-pattern 都是已有 V-row 的 rename / alias → 失败 (须 net-new)
- ❌ Session-tier 4Q gate 假设 LLM 必须可调 → 失败 (违反 V130)
- ❌ Recall@5 通过 cherry-pick query 集 → 失败 (须 canonical query, 不是为了过 metric 而设计的)

### Triggered redirect

| 条件 | 动作 |
|---|---|
| Claude Code CLI 单 session 跑不完 1 case 工业级 e2e (context exhausted) | retro · 评估 1M ctx 是否真够 · 可能需 multi-session chain via /resume |
| Death-pattern detection 退化为 V-row 标签 game (无新洞察) | 切到 V63-A scale-up |
| Frontend 拉力变强 (用户压力) | 切到 V63-B |

### Tier 状态板

#### Tier 1 · 解锁性 (session-as-advisor protocol)

- [ ] **M-SESSION-PROTOCOL** Claude Code session-as-advisor 协议草稿 · 含 stage 切分 / advisor 调用 / V-row attribution / artifact 留痕规则
- [ ] **M-V-SERIES-RECALL-EVAL** V-series corpus recall@5 测试集 (20 canonical query) · 建立 baseline
- [ ] **M-SESSION-4Q-AUDIT** session-tier 4Q gate · LLM-offline degradation path 设计 + sign-off

#### Tier 2 · e2e + death-pattern

- [ ] **M-SESSION-E2E-1** Claude Code session e2e CFD case 1 · 全链路工件 + retro
- [ ] **M-SESSION-E2E-2** session e2e case 2
- [ ] **M-DEATH-PATTERN-CATALOG** ≥10 distinct death-pattern V-row signatures catalogued
- [ ] **M-V80-LANDING** V-row corpus V51+ → V80+

#### Tier 3 · validation + close

- [ ] **M-SESSION-E2E-3** session e2e case 3
- [ ] **M-V-SERIES-RECALL-PASS** Recall@5 ≥80% on 20 canonical query
- [ ] **M-RADAR-V5** Capability radar v5 · session-as-advisor axis
- [ ] **M-V64** V63-C close DEC + V64 charter draft

### 关键依赖图 (V63-C)

```
M-SESSION-PROTOCOL  ──→  M-V-SERIES-RECALL-EVAL  ──→  M-SESSION-4Q-AUDIT
                                                            │
                                                            ↓
                                              M-SESSION-E2E-1  ──┐
                                              M-SESSION-E2E-2  ──┤──→ M-DEATH-PATTERN-CATALOG
                                                                  │           │
                                                                  │           ↓
                                                                  └──→ M-V80-LANDING
                                                                              │
                                                                              ↓
                                                                    M-SESSION-E2E-3
                                                                              │
                                                                              ↓
                                                                M-V-SERIES-RECALL-PASS
                                                                              │
                                                                              ↓
                                                                    M-RADAR-V5 ──→ M-V64
```

---

## §5 · 4-dim comparison table

| 维度 | V63-A Industrial Scale-Up | V63-B Frontend Activation | V63-C M6 Operationalization |
|---|---|---|---|
| **工程实现风险** (1 低 · 5 高) | **2** | **4** | **3** |
| narrative | V62-A 资产可直接复用 · advisor 加宽 + case 扩张是线性外推 · 已知 risk 集中在 catalog 完整性 + 工业 case STEP 准备难度 | 全新前端工作 + workbench parity + Apple-tier polish + 5-step spine 集成 · UI 失控 risk 高 · 多 LANDED 但孤立的前端组件可能拖累集成 | session-as-advisor 是新协议 · V-series recall eval 是新 infrastructure · 1M ctx 单 session 跑工业 case 是真实工程不确定性 |
| **战略价值** (1 incremental · 5 transform) | **3** | **4** | **5** |
| narrative | 工业 case 数 + V-row corpus 是 incremental 但稳定增值 · 商业 CAE AI 对手主要在此 axis (Siemens GA / ANSYS GenAI 都强调 case-coverage) · 不 transform 但 strong moat | 用户可见性 transform (advisor stack 第一次"用户能 dogfood") · workbench parity 解锁 OSS 准备 · 但仍 module-level (UI is wrapper) | M6 charter (per [feedback_claude_code_is_the_advisor]) 的真实操作化 · 把"AI = advisor 不是 driver" thesis 推到极限 · transform 整个 product 定位 (从"工作台" → "session-tier AI engineer") · 也是商业 CAE AI 最难复制的方向 (他们 stack 不在 Claude/Codex 上) |
| **用户 dogfood 距离** (1 近 · 5 远) | **3** | **1** | **2** |
| narrative | 用户能 dogfood 工业 case 报告但不能在浏览器或 conversation 里直接操作 · 距离 = 通过 .planning/ + 命令行 | 用户能直接浏览器 dogfood (这是最近的 distance) | 用户在 Claude Code conversation 内 dogfood (近, 但限于 conversation form factor · 不是浏览器) |
| **V62-A 资产复用度** (1 低 · 5 高) | **5** | **3** | **4** |
| narrative | advisor stack + V-series corpus + 4Q gate + DRIFT-V2 + Track C 方法全部直接复用 · 是最自然的 V62-A 扩展 | 复用 routes (M-ROUTE-AI-REVIEW + M-ROUTE-AI-DIAGNOSE) 但需要前端层新代码 · advisor stack 间接复用 (通过 route) | 复用 V-series corpus + advisor stack + Track C 方法 (session = 新型 Track C runner) · 不依赖 frontend · 高复用但需新 protocol layer |

---

## §6 · 推荐 (1-2 句 · 不硬推 · 用户战略决定)

**Plan-author observation** (not prescription): V63-A 是 V62-A 的自然路径延伸 · 风险最低、moat 最稳; V63-C 是战略价值最高、与 [feedback_claude_code_is_the_advisor] 真实命题对齐最强、也是商业 CAE AI 最难追的方向; V63-B 是用户 dogfood 距离最近但工程风险最高。三个都可行 · 选择取决于用户当下战略权重 (稳态产出 vs 用户可见性 vs M6 thesis 操作化)。

如需独立第二意见 · 推荐用户主动召唤 Kogami (v2.3 opt-in only): `bash scripts/governance/kogami_invoke.sh .planning/2026-05-14_v63_charter_draft.md V63-candidate-selection user-strategic-decision`

---

## §7 · 沿用 V62-A 不变规则 (无论选 A/B/C)

- LLM offline 四问门控 (V130 thesis · 每个新功能 PR/DEC/UI 改动必答四问: LLM 离线可跑? artifacts 输出? TrustGate 解释? AI 仅 advisory?)
- advisor 不是 driver · 只 advise · engineer (or Claude Code session) 最终决策
- 双 corpus drift-prevention hook (M-DRIFT v1 + V62 v2) 保留
- session-end Notion sync (仅 Status=Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven (≥3 共享代码路径 / governance-rule-change → full charter; 否则 sub-DEC 6 字段最小 schema)
- Spike-class 一等 scope class (≤30 LOC + 1 test + commit `confidence: <h/m/l>` · 不调 DEC / Codex / Kogami / Notion)
- Codex 1-sync-trigger (auth / signing / security boundary) · round cap = 3
- Kogami opt-in (用户主动召唤 only)
- pre-implementation surface-scan (per DEC-V61-088) optional except new routes/ / pages/
- counter 纯遥测

---

## §8 · v2.3 governance 合规

- 本文件 = plan-file Draft · **非 DEC** · 无 frontmatter · 不进 `.planning/decisions/`
- 用户选定 candidate 后:
  - 该 candidate 的 charter 升级为 V63 plan SSOT (本文件 path 或替换文件)
  - 首个 sub-DEC 落地时 · 跨 ≥3 共享代码路径 → elevate to full charter DEC (per v2.3 charter-trigger 规则)
  - 否则单个 sub-DEC 走 commit message + tests + 6 字段最小 schema
- Codex review: 各 candidate 的 security-boundary surface 不同
  - V63-A: D11 advisor 不触 security boundary · Codex skip default
  - V63-B: frontend 路由消费 + UI auth 边界 → 命中 1-sync-trigger 的子集需 Codex
  - V63-C: session-as-advisor protocol 不触 service-layer security · Codex skip default · 但 V-series recall eval 涉及 corpus-write 可能触发 byte-repro async post-merge
- Kogami opt-in
- 本 draft 不 sync Notion (per v2.3 round-1 "仅 Accepted DEC")

---

## §9 · 下一步 (user action required)

1. **用户选 candidate** (V63-A / V63-B / V63-C · 或要求合并 / 修改)
2. (可选) **召唤 Kogami** 做战略第二意见 · 见 §6 命令
3. 选定后:
   - 本 plan-file 升级为 V63 plan SSOT (重命名去掉 `_draft` 后缀 · 或替换为新文件)
   - ARC-GOAL.md 添加 V63 section · 引用本 plan-file
   - 首个 sub-DEC 起草

4. **本 draft 不 commit V62 close DEC** (那是 B38 范围 · 需先 B36 RADAR-V4 计算完才有 close 数据)

---

**End of V63 charter Draft.** V62-A 正在收尾 (B36 M-RADAR-V4 并行 build · B38 V62 close DEC 待 RADAR-V4 后启动). 等用户选定 candidate.
