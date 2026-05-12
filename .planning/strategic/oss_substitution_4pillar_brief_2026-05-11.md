# OSS-Substitution + AI-Advisor 4-Pillar Charter — Strategic Review Brief

**Purpose**: Kogami strategic-layer independent review on whether to admit a charter-scope arc proposing four pillars (RAG advisor enhancement, SALOME CAD-healing bridge, MeshGraphNet mesh diagnostic, SU2 + mmg adjoint) into the post-N6 / post-V198 work pipeline.

**Author**: Claude Code Opus 4.7 (1M context) — main session
**Date**: 2026-05-11
**Trigger**: User-summoned strategic-layer review (v2.3 Kogami opt-in path)
**Why Kogami, not Codex**: scope spans ≥3 modules + introduces 3 new external dependencies (SALOME 9.15, PhysicsNeMo MeshGraphNet, SU2 v8.1) + interacts with governance rules (advisor philosophy, four-question gate, monthly-industrial-case substrate). Code-level blind-spot review is premature until territory + philosophy alignment is settled.

---

## 1. Strategic Input (verbatim user hand-off brief)

> The following is the strategic mandate handed to the main session, recorded verbatim. Kogami should treat it as the user's strategic intent — not as a finished proposal.

### 1.1 战略背景

cfd-harness-unified 在 2026-05-07 完成两次战略转向（V130 advisor pivot + V198 APU bay industrial pivot）后，定位锁定为 **"无商业 CFD 软件 · LLM 离线可跑 · AI 仅 advisor · TrustGate 治理"** 的开源 CFD 工业工作台。APU bay 943k cells 算例（DEC-V61-198）证明工作台已具备工业 CFD 能力。

下一阶段（1-3 月战术窗口）目标：把工作台从"能跑工业算例"推到"AI 顾问加成的 OSS 工业 CFD 工作台"，重点增强 CFD 自动化与跨场景泛化能力。前序 Opus 调研会话识别四件"立即落地、不依赖商业软件、满足 advisor 哲学 + 四问门控"的工程任务。

### 1.2 核心约束 — 四问门控

每个新功能 PR / DEC / UI 改动必须显式自答四问，任一答否 = redesign：

1. LLM 离线时本功能能否跑？（必须能；最差降级为只展检索结果）
2. 是否有 artifacts 输出（落到磁盘 / 可审计 / 可重放）？
3. TrustGate 能否解释决策（top-K + diff + 推理依据）？
4. AI 仅 advisor，不替工程师写算例文件 / 不进 inner solver loop？

### 1.3 v2.3 治理对齐

- 跨 ≥3 模块 → 必须写完整 charter DEC
- 单功能 sub-DEC 走 commit message + tests，6 字段最小 schema
- Codex review round cap = 3；超过进 retro 队列
- Kogami 默认不召唤；仅用户主动要求战略层独立审查时调用（即本次调用本身）

### 1.4 四支柱清单（按建议执行顺序）

**支柱 1 · RAG-based BC & Solver 推荐 advisor（M6 落点 · Quick Win）**
- 目标：用户写 OF case，AI 给 review report + 推荐 BC / 物性 / solver 配置；不替写
- 技术栈：codex-relay 或本地 LLM / nomic-embed-text / 三层语料（OF tutorials + V-series + CFDLLMBench 110-case）
- 参考剥离：Foam-Agent 2.0 (arXiv 2509.18178) 的 hierarchical FAISS + Reviewer agent prompt schema —— **只剥 RAG + Reviewer 两层，绝不照搬整个 LangGraph operator pipeline**
- Acceptance：TrustGate top-3 similar case + diff；离线降级；artifacts 落 `.planning/advisor_sessions/`；CFDLLMBench 110-case recall 报告进 V-series
- 预估：8-12 人日

**支柱 2 · SALOME 9.15 GUI bridge → dirty CAD 修复流水线（M2 落点）**
- 目标：把 APU bay 项目手工 STEP mojibake decode + tessellation + healing 流程沉淀为一键功能；对位 STAR-CCM+ Surface Wrapper 但走 OSS
- 技术栈：SALOME 9.15.0 (2025-09 release) headless `salome -t script.py`；扩展现有 `cad-step-stl-prep` skill；Docker 化 SALOME 镜像 (~2GB)
- Acceptance：AI advisor 输出"建议 healing 步骤序列"由工程师确认；artifacts 落 `.planning/cad_healing/<case>/{input.step, healing.log, output.stl, report.md}`；TrustGate 解释每步 healing；APU bay 0507_APU.step 回归 case 已知 939k cells sHM 验证通过
- 预估：6-9 人日

**支柱 3 · MeshGraphNet pretrained 网格诊断 advisor（M2.5 落点）**
- 目标：STL 进 sHM 之前，AI 预测高 skewness / 高 aspect-ratio 区域，给工程师 refine 建议
- 技术栈：NVIDIA PhysicsNeMo MeshGraphNet (Apache 2.0) 预训练 checkpoint；优选 X-MeshGraphNet (arXiv 2411.17164) 直接吃 STL point cloud + k-NN graph 跳过 mesh-generation 中间步；本地 PyTorch CPU/MPS 推理；ground truth 用 APU bay 943k cells checkMesh 结果
- Acceptance：输出预测热力图 + 推荐 sHM refinement level；**只推荐不自动 refine**；artifacts 落 `.planning/mesh_advisor/<case>/{prediction.vtu, report.md}`；TrustGate 显示模型置信度 + 与 V-series APU bay ground truth 偏差对比
- 预估：10-14 人日

**支柱 4 · SU2 v8.1 + mmg 5.8 adjoint workbench skill（M4 落点）**
- 目标：引入 SU2 作为第二 solver，解锁 OF 体验差的 adjoint shape optimization 场景；AI 帮用户从 OF case 转 SU2 .cfg 并跑 adjoint sensitivity
- 技术栈：SU2 v8.1 (2024 release) binary + Python wrapper；mmg 5.8 (2024-2025 含 OpenMP) 做 adjoint adapt；现有 `su2-harness` skill 壳子扩展
- Acceptance：demo NACA0012 OF case → 生成 SU2 .cfg → 跑 adjoint sensitivity → mmg adapt → 二次跑；AI 仅生成模板，**不自动 submit run**；artifacts 落 `.planning/su2_runs/<case>/{cfg, adjoint.log, sensitivity.vtu, report.md}`；TrustGate 解释每个 cfg 字段为什么是这个值 + 与 OF 等价配置 diff；V-series 新增 SU2 adjoint NACA0012 案例
- 预估：12-15 人日

### 1.5 反对清单（charter 必须 codify）

| 别做 | 原因 |
|---|---|
| 集成 PINN / Modulus Sym 作 solver | 2025 reviews 指 ill-conditioning + 误差 floor，工业不 ready |
| 等 PDE Foundation Model（Aurora 除外） | 距 production ≥12 月 |
| 照抄 Foam-Agent operator pipeline | 与 advisor 哲学正面冲突，只剥 RAG + Reviewer |
| GenCFD / Diffusion solver-replacement | 训练成本 + 工业算例验证缺失 |
| 自训 advisor LLM | 86gs/CRS relay + RAG 已覆盖 80% 价值 |
| RL closed-loop 自动 AMR | 与 advisor 哲学冲突；改"推荐 region 工程师按按钮" |

### 1.6 总人日 & 排程

- 36-50 工程日（单人 7-10 周；Opus + Codex 并行可压到 4-6 周）
- 建议执行顺序：P1 → P2（与 P1 可并行）→ P3（等 P1 UI 样板）→ P4（最后；可作 spike）

---

## 2. Fact Corrections (main-session reconciliation vs strategic input)

### 2.1 命名层不匹配

Brief 用 "M2.5 / M4 / M6" 落点命名，但仓库实际跑的是 **Blueprint v3 N1-N6 + 之后的 BlueprintV4 territory**：

- `.planning/strategic/n3_n6_outline_2026-05-07.md` codify **BlueprintV4 = "压缩 / 多相 / 辐射 / FSI / 多引擎"**
- `2026-05-07_v61_n6_phase_close.md` 写 "Subsequent work (M3+ in roadmap_v2: compressibility, multiphase, multi-engine) crosses into BlueprintV4 territory"
- roadmap_v2 (memory only) 的 "M2 / M2.5 / M4 / M6" 命名 **从未在 ROADMAP.md / blueprint v3 文件里 codify**，是 memory-only 概念命名

四支柱的实际 territory 归属（main-session 评估）：
- **P1 RAG advisor**：N6 续作 / N6.6+ 续 sub-DEC，**不是** BlueprintV4 物理扩展
- **P2 SALOME healing**：V198 工件链续作（A1 cad_ingest_freecad.py 仍未抽，见 §2.2），**不是** BlueprintV4
- **P3 MeshGraphNet**：N2.4 checkmesh_advisor 续作 / advisor 层扩展，**不是** BlueprintV4
- **P4 SU2 adjoint**：✅ **唯一**完美对齐 BlueprintV4 "多引擎"

### 2.2 V198 工件实际抽件状态（2026-05-11 grep 确认）

| # | 工件 | brief 假设 | 实际 |
|---|---|---|---|
| A1 | `ui/backend/services/geometry_ingest/cad_ingest_freecad.py` | 未抽（brief 暗示由 P2 sealed） | ❌ **未抽** — P2 起跑前必须先补，或 P2 charter 含 A1 |
| A2 | `ui/backend/services/geometry_ingest/virtual_interface_detector.py` | 未抽 | ✅ 已抽 |
| A3 | `ui/backend/services/geometry_ingest/geometry_surgery.py` | 未抽 | ✅ 已抽 |
| A4 | mass conservation pre-flight in `case_bc/writer.py` | 未抽 | ⚠️ 未确认（非 P2 阻塞） |
| A5 | `.planning/methodology/solver_convergence_playbook.md` | 未抽 | ✅ 已抽 — P1 RAG 注入可直接用 |
| B  | `.planning/methodology/industrial_case_solver_findings.md` | 未抽 | ✅ 已抽 — P1 RAG 注入可直接用 |

→ **P2 起跑前置 = A1 cad_ingest_freecad.py 抽件**。要么先抽，要么 P2 charter 把 A1 作为第一个 sub-DEC。

### 2.3 N6 AI Advisor Stack 已 closed

DEC-V61-156..161 + N6-CLOSE 2026-05-07 已 ship：
- `ui/backend/services/ai_advisor/corpus_loader.py` — keyword + section-anchor 检索，corpus_sha 指纹，stable chunk_id
- `review.py` / `diagnose.py` / `safety.py` / `fallback.py`
- `routes/ai_advisor.py` 两个 GET endpoint（loopback-guarded）
- 前端 `AIAdvisorPanel`
- corpus 来源 `docs/openfoam_corpus/`（5 手工 topic doc）

→ **P1 不是新建 advisor stack**，是对 N6 的增量增强：
- 新增 FAISS / hierarchical index 层（不取代现有 keyword + anchor）
- 新增 V-series + CFDLLMBench 注入到 corpus
- 复用 `CitedChunk` / `corpus_sha` / `chunk_id:sha16` 既有契约 — **不能破**

### 2.4 case_profiles pipeline 已有 8 个候选

`.planning/case_profiles/` 已存：
- case_002 APU bay (industrial reference, V198)
- case_002a / 002b APU bay variants
- case_003 CRM-HLS boundary layer (外流高 Re)
- case_004 NREL Phase VI MRF (旋转机械)
- case_005 RAE M2129 S-duct
- case_006 ONERA M6 transonic (可压缩高速)
- case_007 KCS ship VOF (多相)
- case_008 GLC305 IRT Lagrangian
- case_009 Sandia Flame D (燃烧)

→ V198 §S5 "月度工业算例 dogfood" **已经在排队** — brief 提的 "四支柱不能挤占月度 case" 风险**真实存在**，不是抽象担忧。

---

## 3. Strategic Decision Points (need Kogami adjudication)

### 3.1 Q1 · 一个 charter 还是两个？

四支柱跨 3 个 territory（N6+ / V198+ / V4）。三种 charter 拓扑选项：

| 选项 | 描述 | 利 | 弊 |
|---|---|---|---|
| **A. 单 charter** | DEC-V61-199 涵盖 P1..P4 + 声明跨 territory | 资源争抢统一治理；anti-list 一次性 codify；月度 case 节奏承诺写在一处 | charter scope 模糊；P4 V4 territory work 与其他三支柱治理 cadence 不同（V4 是物理扩展，可能需要更深 Kogami 介入） |
| **B. 双 charter** | DEC-V61-199 (P1+P2+P3 advisor/CAD/mesh) + DEC-V61-200 (P4 BlueprintV4-P1 多引擎 charter) | territory 边界清晰；V4 charter 留余地接纳后续 compressible / multiphase 等其他 V4 sub-DEC | 两个 charter 同时 propose 增加治理开销；P3 与 P4 在 TrustGate cross-engine verdict 上有耦合，跨 charter 难协调 |
| **C. P4 推迟到独立 V4 charter，P1+P2+P3 走一个 OSS-advisor charter** | DEC-V61-199 = P1+P2+P3；P4 在四支柱大局清晰后另开 V4 charter | 推迟最深水风险；P1+P2+P3 都是 advisor/工件层，治理 cadence 一致 | brief 期望"四支柱一次性立项"被部分否定；P4 SU2 binary 集成探索延后 |

Main-session 倾向 **C**，但请 Kogami 拍。

### 3.2 Q2 · Foam-Agent FAISS 是否真胜过 N6 现有 keyword + anchor？

N6.1 corpus_loader 已实现 keyword + section-anchor weighted 2x + stable chunk_id。引入 FAISS 的前提：

- corpus 体量 ≥ 几千 chunks（否则 FAISS 索引 overhead > 检索收益）
- 语义相似度（不仅词汇相似）是真实需求 — 但 advisor 的 case-similarity 查询往往是"几何 + 物理参数 + Re 数"结构化匹配，未必需要 dense embedding
- nomic-embed-text 已在用，但用在 AeroPower-RAG 那个 RAG 系统里，cfd-harness-unified 的 corpus 是否真需要此 layer？

风险：**引入 FAISS 是为了对标 Foam-Agent 而非解真实瓶颈**。如果工业 corpus 不大到撑得起，反而拖累冷启动 + 增加 corpus_sha 契约破坏面。

请 Kogami 评估：P1 是否应该先做 V-series + CFDLLMBench 注入（corpus 扩展），观察 keyword + anchor 检索的真实失败模式，再决定是否引入 FAISS？

### 3.3 Q3 · MeshGraphNet vs N2.4 checkmesh_advisor 关系

N2.4 已落地 `mesh_quality/advisor` 模块（rules-based：基于 sizing field schema + cell-budget explainability）。P3 MeshGraphNet 是 ML-based 预测。两者关系：

- **并存**：rules-based 给确定性 boundary（cap warnings, etc.），ML 给概率性热力图。但工程师 UX 上看到两套 advisor 容易混淆
- **替换**：ML 取代 rules — 但 ML 推理需要预训练 checkpoint，离线四问 #1 答案变敏感；且 PhysicsNeMo MGN 预训练数据集不覆盖工业 CFD 几何（多是 academic benchmark）
- **分层**：rules-based 做 fast-path（毫秒），ML 做 slow-path（秒级 advisor 召唤时跑）

请 Kogami 拍方向，并评估 ML advisor 的 advisor-philosophy 兼容性（"模型置信度 = AI 自信，工程师按按钮" 是否仍是 advisor 而非伪 actor）。

### 3.4 Q4 · 月度工业 case 节奏的硬性约束怎么写进 charter？

V198 §S5 mandate "每月 1 个新工业 case"。四支柱 36-50 人日 = 7-10 周（单人）= 1.5-2.5 月。期间月度 case 节奏不能停（否则违背 V198 substrate 哲学）。

charter 是否应该硬性 codify：
- "每 4-week sprint 必须包含 ≥1 个新工业 case 的 6 个标准动作"？
- "任一支柱 sub-DEC 阻塞月度 case 进度 ≥2 周 → 强制暂停支柱推进，先消化 case backlog"？
- 或更软：在 charter body 列 risk，由每个 sub-DEC discuss-phase 各自处理？

---

## 4. Four-Question Gate Pre-Answers (per pillar)

| Pillar | Q1 LLM offline | Q2 artifacts | Q3 TrustGate | Q4 AI advisor only |
|---|---|---|---|---|
| **P1 RAG advisor 升级** | ✅ 离线降级 = 只展 retrieval，无 LLM 推荐文本 | ✅ `.planning/advisor_sessions/<sub-dec>/<case>.md` 每 session 落盘可重放 | ✅ top-K similar case + diff + 推理依据 已在 N6 契约 | ✅ AI 只 GET + advise；现有 V132 `MUTATING_ROUTES` 拦截不变 |
| **P2 SALOME healing** | ⚠️ **风险点** — SALOME 本身不需 LLM，但"AI 推荐 healing 步骤序列"需 LLM；离线时 advisor panel 不展推荐，工程师手动用 SALOME GUI healing —— 必须显式落 fallback 路径 | ✅ `.planning/cad_healing/<case>/{input.step, healing.log, output.stl, report.md}` | ✅ 每步 healing 显示"修了什么 / 为什么 / 几何变化量" | ✅ "AI 推荐 + 工程师确认按钮触发"是核心契约 |
| **P3 MeshGraphNet** | ⚠️ **风险点** — PyTorch 推理本地 OK，但预训练 checkpoint 是 NVIDIA 来源；首次启动需要下载，offline-first install 路径必须 codify | ✅ `.planning/mesh_advisor/<case>/{prediction.vtu, report.md}` | ✅ 模型置信度 + 与 ground truth 偏差对比 | ✅ "只推荐不自动 refine" |
| **P4 SU2 adjoint** | ✅ SU2 + mmg 都是本地 binary，无网；".cfg 生成 + adjoint 解读" 用 LLM，离线降级为只展 cfg 模板 | ✅ `.planning/su2_runs/<case>/{cfg, adjoint.log, sensitivity.vtu, report.md}` | ✅ 每字段解释 + OF 等价 diff | ✅ "AI 仅生成模板不自动 submit" |

**Kogami 重点审 P2 / P3 的 Q1 风险点** — 离线降级路径是否真的可兑现？

---

## 5. Conflict Map vs Existing Work

| 冲突点 | 严重度 | main-session 建议处理 |
|---|---|---|
| P1 ↔ N6 `ai_advisor/` 包 | ⚠️ 中 | charter 显式声明"扩展非重写"；FAISS 注入为 corpus_loader v2 而非新 service；保留 `Corpus.find_relevant` 契约 |
| P2 ↔ V198 A1 (cad_ingest_freecad.py 未抽) | ⚠️ 中-高 | P2 charter 含 A1 作为第一 sub-DEC，或 P2 启动前 V198 §S3 必须完成 |
| P3 ↔ N2.4 checkmesh_advisor (rules-based) | 🟡 中-低 | Q3 待 Kogami 拍方向（并存 / 替换 / 分层）|
| P4 ↔ SolverDriver Protocol (M1) | 🟡 中-低 | 新增 `SU2SolverDriver` 符合扩展；TrustGate cross-solver verdict 是 open question，charter 留 |
| 四支柱 ↔ V198 §S5 月度 case 节奏 | ⚠️ 中-高 | Q4 待 Kogami 拍硬性程度 |
| brief 用 "M2.5 / M4 / M6" 命名 | 🟢 低 | charter 改用 explicit territory tag："P1=N6+, P2=V198-fix-arc, P3=N2-advisor-ext, P4=V4-multi-engine-P1"|

---

## 6. Anti-List Codification

Brief §1.5 给的 6 条 anti-list 必须进 charter body "What we are explicitly NOT doing" 章节。理由：

- charter 是后续 sub-DEC 唯一可引用的"不可推翻"地基
- 没有显式 anti-list，sub-DEC 容易在 round-cap-3 内被 Codex 推回 "为什么不试 PINN 看看"
- v2.3 charter scope-driven 规则要求 governance-rule-scope 必须 codify — anti-list 就是 governance rule

请 Kogami 评估 anti-list 是否需要补充（如：是否要加 "不引入 Mesh-RL closed-loop"、"不取代 Foam-Agent adapter 作 OF executor" 等）。

---

## 7. Expected Kogami Output

请 Kogami 给：

1. **Verdict**：APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED / REJECT — 是否admit 此四支柱为 charter 候选
2. **Q1-Q4 answers**：直接拍四个 open strategic question 的方向
3. **Anti-list completeness**：anti-list 漏哪些
4. **Hidden strategic risks**：main-session 没列但 charter 落地后会暴露的战略风险
5. **Charter authoring posture**：是否同意 main-session 倾向方案 C（P1+P2+P3 单 charter + P4 独立 V4 charter）
6. **Path forward**：建议下一步是 (a) 直接落 charter / (b) 先补 V198 A1 工件 / (c) 先做 P1 spike 验证 RAG 升级路径 / (d) 其他

---

## 8. Out of Scope for This Brief

- 任何具体代码 diff / API 设计 — 由后续 sub-DEC 的 `/gsd-discuss-phase` 处理
- Codex review 触发条件 — v2.3 同步阻塞规则已 codify in CLAUDE.md
- Notion sync 时机 — session-end 批量
- Kogami 自身 invocation 节奏 — v2.3 已 codify 为 opt-in only

---

**End of brief**. Kogami 输出应落 `.planning/reviews/kogami/oss_substitution_4pillar_charter_scope_2026-05-11/{review.json, review.md, invoke_meta.json}`。
