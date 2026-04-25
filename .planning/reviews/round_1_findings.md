# Round 1 Multi-Role Findings

**Date**: 2026-04-22
**Reviewer**: Codex GPT-5.4 (3-persona sequential)
**Scope**: 6 commits from `87b3b39` → `a1feef9`

## Role 1 · 商业立项 demo 评审专家

### Verdict: CHANGES_REQUIRED

### 🔴 BLOCKERS
- [R1-B1] `/learn` 冷启动 30 秒内仍像“教学站点”，不像可采购的 AI-CFD workbench
  - **why**: 首页主标题是“用十个经典流动问题，学会 CFD 的验证思维”，实现注释也明确写了“Teach, don't sell”。这对学生导向是成立的，但对潜在客户或基金技术尽调来说，前 30 秒没有回答“这产品替团队省什么时间/降低什么风险/为什么现在值得买”。浏览器标题仍是 `CFD Harness — Validation Report`，进一步把前门拉回“内部报告工具”语义。
  - **evidence**: `ui/frontend/src/pages/learn/LearnHomePage.tsx:39-50`; `ui/frontend/src/components/learn/LearnLayout.tsx:3-7`; `ui/frontend/index.html:7`; live `http://127.0.0.1:5180/learn`
  - **suggested fix**: 首页首屏改成产品级一句话价值主张，明确“AI-CFD workbench + honest physics validation + signed audit evidence”三件事；教学型 10-case catalog 继续保留，但放到 hero 之后。同步改 `<title>` 和首屏 CTA 文案。

### 🟠 MAJOR
- [R1-M1] 诚实信号放在了解释层之前，第一次接触更像“产品自己全红了”
  - **why**: 卡片直接展示 live `PASS/HAZARD/FAIL` run 统计，而默认 run 解析现在优先 `audit_real_run`，不是 `reference_pass`。结果是 buyer 在还没理解“这套系统的红色代表它抓到了物理/治理问题”之前，先看到大量失败。当前 `/api/dashboard` 汇总还是 `10 FAIL / 0 PASS / 0 HAZARD`，新的 `SATISFIED / COMPATIBLE / ...` physics-contract class 并没有出现在 live buyer path。
  - **evidence**: `ui/frontend/src/pages/learn/LearnHomePage.tsx:77-92`; `ui/frontend/src/pages/learn/LearnHomePage.tsx:131-134`; `ui/backend/services/validation_report.py:290-307`; `ui/backend/services/validation_report.py:764-790`; `ui/backend/services/dashboard.py:82-88`; live `GET /api/dashboard` on 2026-04-22 returned `{'pass_cases': 0, 'hazard_cases': 0, 'fail_cases': 10, 'unknown_cases': 0}`
  - **suggested fix**: `/learn` 前门优先展示 physics-contract compatibility 层，audit-real-run verdict 放到 case detail 或 `/pro`；把“红色= caught mismatch”解释成产品能力，而不是前台默认状态。

- [R1-M2] 10-case catalog 的单页叙事不错，但整个 demo 的主线还不够“被策展”
  - **why**: README 已经明确 3 个 anchor case 是主线，但 live `/learn` 没有把它们视觉上凸出来，导致第一次接触像广撒网目录，而不是“先用 3 个 case 建立信任，再扩展到 10 个 canonical flows”。
  - **evidence**: `README.md:42-46`; `ui/frontend/src/pages/learn/LearnHomePage.tsx:54-71`
  - **suggested fix**: 首页增加 “Start Here / 推荐先看” 区块，把 `lid_driven_cavity`、`circular_cylinder_wake`、`naca0012_airfoil` 单独拉出来，其余 7 个归到 expanded catalog。

- [R1-M3] 从“这很有意思”到“我要认真评估给团队”的 CTA 路径不完整，而且一条关键桥接会丢上下文
  - **why**: case-detail 顶部 hero 的“签名审计包”按钮会带 `case` 和 `run`，但 Advanced tab 底部 CTA 直接跳裸 `/audit-package`，用户进入后得到的是空 builder。对 buyer 来说，这正是应该发生“继续往下评估”的时刻，结果被打断。
  - **evidence**: `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:233-245`; `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1214-1229`; `ui/frontend/src/pages/AuditPackagePage.tsx:34-44`
  - **suggested fix**: 所有通往 audit package 的桥接统一保留 `?case=...&run=...`；再额外补一个 buyer-oriented CTA，例如 “Evaluate with your team / 用团队评估这个案例”。

- [R1-M4] 非中文 buyer 的流失点仍然明显
  - **why**: 首页 hero、卡片 teaser、导航、run 描述基本都是中文主叙事，英文更多是副标题或不存在。对海外 fund DD reviewer 或非中文 engineering lead，这会显著拉高理解门槛，尤其在 30 秒测试里。
  - **evidence**: `ui/frontend/src/pages/learn/LearnHomePage.tsx:45-50`; `ui/frontend/src/components/learn/LearnLayout.tsx:32-53`; `ui/frontend/src/data/learnCases.ts:13-31`; `ui/frontend/src/data/learnCases.ts:36-67`; `ui/frontend/src/data/learnCases.ts:121-135`
  - **suggested fix**: 首屏 hero、价值主张、CTA、每张卡片的一句话必须双语；深层教学内容可以继续中文优先。

- [R1-M5] “Why now / 2026 relevance” 和差异化能力还停留在 README/Pro 侧，没有成为 demo 自身的一部分
  - **why**: `/learn` 当前能让人看出“这是个认真讲 validation 的界面”，但还看不出它相对 SimScale/Ansys cloud、ML surrogate benchmark、generic LLM CFD copilot 的独特 claim：你们真正卖的是“把 physics validity、decision trace、signed audit evidence 放到同一个 workbench”。这个 claim 在 demo 里没有被一眼看见。
  - **evidence**: `README.md:48-55`; `README.md:87-92`; `ui/frontend/src/pages/learn/LearnHomePage.tsx:39-50`; `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1165-1170`
  - **suggested fix**: 在 `/learn` 顶部增加一个非常短的 differentiation band，直接对比 “cloud solver gives numbers / this workbench tells you when the numbers are physically defensible and audit-packaged”。

### 🟡 MINOR
- [R1-m1] 前门导航里还有 placeholder 交互
  - **why**: “学习路径”和“文献”现在都是 `window.alert(...)`。这在内部开发没问题，但放在 funded demo 前门会被看成未完工。
  - **evidence**: `ui/frontend/src/components/learn/LearnLayout.tsx:34-53`
  - **suggested fix**: 没有真实页面前先隐藏；若保留，则至少落到静态落地页而不是 alert。

### 🟢 PRAISE
- `/learn` 的视觉执行是统一的，Story → Compare → Mesh → Run → Advanced 这条 case-detail 路线本身是成立的，不是东拼西凑的 slideshow。
- 保留 `/cases/:caseId/report`、`/runs`、`/audit-package` 等深链接没有断，这是 demo-first pivot 里做得对的工程决定。
- 敢把 `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE` 这种难看标签摆到台面上，本质上是对 buyer 信任有帮助的；问题不是“太诚实”，而是“诚实还没有被前台正确 framing”。

## Role 2 · CFD 仿真专家工程师

### Verdict: CHANGES_REQUIRED

### 🔴 BLOCKERS
- None.

### 🟠 MAJOR
- [R2-M1] `backward_facing_step` 的 gold anchor 现在内部不一致：source 说 Le/Moin/Kim `Xr/H = 6.28`，数值却还写成 `6.26`
  - **why**: 这不是措辞问题，而是可追溯性问题。当前 YAML 已经把 source 切到 Le/Moin/Kim 1997 DNS，但 `reference_values[0].value` 仍保留 `6.26`。Le, Moin & Kim 1997 的原文摘要给的是 mean reattachment `6.28 h`，扩张比还是 `1.20`。如果要保留 `6.26`，就必须明确说这是 blended anchor，而不是继续挂 Le/Moin/Kim 的 source。
  - **evidence**: `knowledge/gold_standards/backward_facing_step.yaml:35-42`; Le, Moin & Kim 1997, JFM 330, 349-374, DOI `10.1017/S0022112096003941`
  - **suggested fix**: 要么把 numeric anchor 改成 `6.28`；要么把 `6.26` 明确改写成“engineering blended anchor”并补 secondary citation，不能保持现在这种 source/value 分离。

- [R2-M2] BFS 7600 vs 5100 的“<2% plateau drift”仍被外宣文案说得过满
  - **why**: 当前 `physics_contract.reference_correlation_context` 已经比研究笔记谨慎，但 outward-facing copy 还在说 Re_H≈5000-10000 区间 `Xr/H` 对 Re 的敏感度 `<2%`。Le/Moin/Kim 1997 只给了 `Re_H=5100, ER=1.20`；当前 adapter 是 `Re_H=7600, ER=1.125`。Armaly 1983 也明确表明 reattachment 对 geometry/expansion ratio 有敏感性。这里最合理的工程姿态是“同后转捩区间、10% tolerance 下可作 surrogate”，而不是“<2%”。
  - **evidence**: `knowledge/gold_standards/backward_facing_step.yaml:16-23`; `knowledge/gold_standards/backward_facing_step.yaml:39`; `ui/frontend/src/data/learnCases.ts:66`; `src/foam_agent_adapter.py:1178-1184`; Armaly et al. 1983, JFM 127, 473-496; Le, Moin & Kim 1997, DOI `10.1017/S0022112096003941`
  - **suggested fix**: 删除 `<2%` 量化说法，只保留“same post-transition regime, tolerated engineering surrogate, not DNS-equivalent”。

- [R2-M3] `plane_channel_flow` 的 verdict 是对的，但 gold 自己还保留了一个可疑点，后面会反咬真实 solver
  - **why**: 当前把它标成 `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE` 是正确的，因为 2D laminar `icoFoam` 不会自己长出 Re_tau=180 的 canonical turbulent channel。问题在于 gold 里 `y+=100, u+=22.8` 仍被自己标成可疑值。今天因为 case 已经判 incompatible，这个错误暂时不致命；一旦 Phase 9 接入更真的 solver，这个点会变成错误 target。
  - **evidence**: `knowledge/gold_standards/plane_channel_flow.yaml:11-26`; `knowledge/gold_standards/plane_channel_flow.yaml:40-42`; `src/foam_agent_adapter.py:3113-3115`; `src/foam_agent_adapter.py:3270`
  - **suggested fix**: 在换真实 solver 之前，先把 `y+=100` 这一点从 hard comparator target 中剥离，或重新溯源后再恢复。

- [R2-M4] `impinging_jet` 的 A4 诊断现在更像“症状”，还不是“根因”
  - **why**: 现在 contract 已经正确指出 axis patch 用的是 `empty` 而不是 `wedge`，这点很关键；而 A4 `p_rgh` iteration cap 只是 attestor 看到的外部症状。根因至少有两层：几何类比错了（planar slice vs axisymmetric round jet），求解配置也还没被证明适合这个 buoyant/heat-transfer setup。只把 narrative 写成 “A4 p_rgh cap” 容易把后续修复带偏成调 solver 参数，而不是先修 comparability。
  - **evidence**: `knowledge/gold_standards/impinging_jet.yaml:8-27`; `src/foam_agent_adapter.py:5182-5185`; `src/foam_agent_adapter.py:5314-5318`; `src/foam_agent_adapter.py:5437-5448`; Baughn & Shimizu 1989, DOI `10.1115/1.3250776`; planar impinging jets are treated as a separate class in Akiyama et al. 2005, DOI `10.1016/j.ijheatfluidflow.2004.08.005`
  - **suggested fix**: narrative 拆成三段：geometry mismatch、solver-convergence symptom、Nu extraction validity；不要把 A4 写成唯一病因。

- [R2-M5] cross-case `contract_status` taxonomy 把多个正交维度揉成了一个字符串
  - **why**: `SATISFIED`、`SATISFIED_UNDER_LAMINAR_CONTRACT`、`SATISFIED_FOR_U_CENTERLINE_ONLY` 在表达“可比范围”；`COMPATIBLE_WITH_SILENT_PASS_HAZARD` 在表达 runtime caveat；`INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE` 在表达危险叙事模式。它们都塞进一个字段后，语义上是“集合论 + 风险层 + 修辞警报”混在一起，后续很难系统化。
  - **evidence**: `knowledge/gold_standards/lid_driven_cavity.yaml:56`; `knowledge/gold_standards/turbulent_flat_plate.yaml:30`; `knowledge/gold_standards/plane_channel_flow.yaml:26`; `knowledge/gold_standards/impinging_jet.yaml:27`
  - **suggested fix**: 把 `reference_compatibility`、`observable_scope`、`runtime_hazard`、`narrative_warning` 分成独立字段，`contract_status` 只保留顶层汇总。

- [R2-M6] A1..A6 + G1..G5 是有用的 credibility screen，但不是完整 ASME V&V20 / V&V40 方法学
  - **why**: 当前实现做得很好的是“求解器没真收敛时不许洗成 PASS”，以及“extractor/comparator 不能乱代数值”。但缺少正式 UQ、grid/time-step 误差分解、model-form uncertainty、context-of-use credibility plan、validation hierarchy。把它说成“internal credibility screen”是准确的；把它包装成标准等价物就过界了。
  - **evidence**: `src/convergence_attestor.py:1-29`; `src/comparator_gates.py:1-17`
  - **suggested fix**: 对外文案把它定位成“physics credibility guardrail / internal V&V screen”，不要暗示已经覆盖 formal ASME credibility stack。

- [R2-M7] adapter 与 gold 之间仍然高度依赖人工保持一致，drift 机制没有被代码抓住
  - **why**: `physics_contract` 现在引用的是 generator 的真实设定，但 schema 对这个块几乎完全放开，代码里也没有“生成器元数据 vs gold precondition”自动断言。未来有人改 `_generate_*`，gold YAML 很容易继续说旧话。
  - **evidence**: `knowledge/schemas/gold_standard_schema.json:301-304`; `src/foam_agent_adapter.py:1178-1184`; `src/foam_agent_adapter.py:1564-1568`; `src/foam_agent_adapter.py:3270`; `src/foam_agent_adapter.py:5182-5185`
  - **suggested fix**: 为每个 canonical case 输出 machine-checkable adapter metadata，再加一个 contract drift test，把 `physics_contract` 的关键 precondition 与真实 generator 绑定起来。

- [R2-M8] silent-pass hazard 的跨 case 语义还不一致
  - **why**: cylinder 的 runtime shortcut hazard 被抬成 case-level class；TFP 仍保留 live Spalding fallback branch，但 case-level status 是 `SATISFIED_UNDER_LAMINAR_CONTRACT`，hazard 更多依赖 measurement incident 和 partial precondition。工程上这两种都合理，但 taxonomy 上是不对称的。
  - **evidence**: `knowledge/gold_standards/turbulent_flat_plate.yaml:27-30`; `src/foam_agent_adapter.py:8429-8450`; `src/error_attributor.py:51-56`
  - **suggested fix**: 要么把这种不对称写进 taxonomy 说明；要么新增独立 runtime-hazard 维度，不再让 case-level class 同时承担全部语义。

### 🟡 MINOR
- [R2-m1] LDC 现在的立场是对的，但 multi-document YAML 里旧 `v_centerline` / vortex block 还在“半活着”
  - **why**: 当前 precondition 已经正确把它们打成 `false`，这很好；但文档块本身仍携带旧 `solver_info` / `mesh_info` 元数据，未来如果被重新接入 comparator，会让人误以为这些 observable 已经和 `u_centerline` 一样被校正过。
  - **evidence**: `knowledge/gold_standards/lid_driven_cavity.yaml:47-57`; `knowledge/gold_standards/lid_driven_cavity.yaml:114-189`
  - **suggested fix**: 给这两个文档块显式加 `deprecated / not comparator-authoritative` 标记，直到真正重溯源。

### 🟢 PRAISE
- `lid_driven_cavity` 现在把 Table II / vortex-center 的问题明确打成 `false`，不是 `partial`，这是物理上正确的态度。
- `plane_channel_flow` 和 `impinging_jet` 终于不再被“数字看起来像对上”这件事绑架，这是这轮最重要的科学诚实进展。
- `circular_cylinder_wake` 的 Strouhal extractor 已从硬编码 canonical band 改成 fail-closed FFT path；这类修复比表面 UI 优化更有价值。见 `src/foam_agent_adapter.py:8248-8270`。

## Role 3 · Senior Code Reviewer

### Verdict: BLOCK

### 🔴 BLOCKERS
- [R3-B1] 这轮“honesty guard”只修到了 export，`/pro` 里的 physics preconditions 仍在把 `partial` 漂白成绿勾
  - **why**: `_make_preconditions()` 直接做 `bool(row.get("satisfied_by_current_adapter", False))`。对 `"partial"` 来说，Python `bool("partial")` 是 `True`。Schema 和前端组件也都是二值模型，所以 `backward_facing_step` / `impinging_jet` / `turbulent_flat_plate` 的 partial preconditions 在 live API 里都会显示为 satisfied。这和 `f89cfd0` 想修的 honesty bug 是同一类问题，只是还活在主 UI。
  - **evidence**: `ui/backend/services/validation_report.py:423-437`; `ui/backend/schemas/validation.py:141-144`; `ui/frontend/src/components/PreconditionList.tsx:20-29`; `ui/frontend/src/components/PreconditionList.tsx:36-60`; live `GET /api/cases/backward_facing_step` on 2026-04-22 returned the first three preconditions as `true` even though YAML marks them `partial`
  - **suggested fix**: 把 `Precondition.satisfied` 改成 tri-state enum（例如 `satisfied | partial | unmet`），前后端统一渲染 `[✓]/[~]/[✗]` 或等价视觉状态，并补 BFS / impinging_jet / TFP 的 API/React regression tests。

- [R3-B2] 当前 `main` 不能复现“全部测试通过”的核心子集；这轮收敛声明本身有回归
  - **why**: 我本地重跑 review 相关子集：`ui/backend/tests/test_case_export.py ui/backend/tests/test_decisions_and_dashboard.py tests/test_report_engine/test_contract_dashboard_report.py`。结果是 `26 passed, 1 failed`。失败点是 `test_contract_dashboard_generate_writes_output`，预期 `manifest["class_counts"]["COMPATIBLE"] == 3`，实际是 `1`。生成器当前输出的分布是 `SATISFIED 4 / PARTIALLY_COMPATIBLE 2 / COMPATIBLE_WITH_SILENT_PASS_HAZARD 1 / INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE 2 / COMPATIBLE 1`。
  - **evidence**: `tests/test_report_engine/test_contract_dashboard_report.py:53-77`; `src/report_engine/contract_dashboard.py:429-449`; `src/report_engine/contract_dashboard.py:778-781`; local rerun on 2026-04-22: `.venv/bin/pytest -q ui/backend/tests/test_case_export.py ui/backend/tests/test_decisions_and_dashboard.py tests/test_report_engine/test_contract_dashboard_report.py`
  - **suggested fix**: 先决定当前 10-case taxonomy 分布到底以哪个为准，然后同步修正 generator、tests、已有 deep-acceptance manifest、以及任何声称 `3 SATISFIED / 3 COMPATIBLE / ...` 的 review 文案；在此之前不要再把这轮叫“已收敛”。

### 🟠 MAJOR
- [R3-M1] 新 `physics_contract` class 基本只活在 static HTML dashboard，live `/learn` 和 `/pro` API 还看不到
  - **why**: `CaseIndexEntry.contract_status` 仍是 `PASS|HAZARD|FAIL|UNKNOWN`，dashboard summary 也是同一层。也就是说，这轮最重要的 `SATISFIED / COMPATIBLE / ...` 分层并没有进 live app 的主数据模型，buyer path 仍只看到 verdict 层。
  - **evidence**: `ui/backend/schemas/validation.py:111-123`; `ui/backend/services/dashboard.py:82-88`; `src/report_engine/contract_dashboard.py:744-749`
  - **suggested fix**: 在 live API 中新增 `physics_contract_class`（以及必要时 `physics_contract_narrative`），前端 `/learn`、`/pro` 同步消费，而不是继续只看 scalar verdict。

- [R3-M2] export regression test 还没有覆盖 `[✗]` 路径和 schema-weak 输入
  - **why**: `_render_contract_md()` 现在只把布尔 `True` 渲染成 `[✓]`，`"partial"/"partially"` 渲染成 `[~]`，其它一律 `[✗]`。这本身可以接受，但现有测试只断言 `[~]` 和 `[✓]` 存在，没有 pin `[✗]`、`None`、`"True"/"true"`、数字、dict 这些实际会落到 `[✗]` 的边界值。与此同时 schema 对 `physics_contract` 仍然是 `additionalProperties: true`。
  - **evidence**: `ui/backend/routes/case_export.py:180-196`; `ui/backend/tests/test_case_export.py:41-59`; `knowledge/schemas/gold_standard_schema.json:301-304`
  - **suggested fix**: 要么把 schema 收紧到显式 tri-state 类型；要么给 `_render_contract_md()` 补齐 failure-path tests，并明确 string booleans 的预期处理。

### 🟡 MINOR
- [R3-m1] markdown export 直接拼接 raw YAML 文本，没有任何 escaping/sanitization
  - **why**: `condition`、`evidence_ref`、`consequence_if_unsatisfied` 都直接插进 markdown；同文件里没有 `escape()`，而 `contract_dashboard.py` 是有的。当前风险不算高，因为它是 zip 内 markdown，不是服务端直接渲染的 HTML，但一旦被 permissive markdown renderer 打开，raw HTML 就可能活过来。
  - **evidence**: `ui/backend/routes/case_export.py:181-202`; contrast `src/report_engine/contract_dashboard.py:659-662`
  - **suggested fix**: 至少做 markdown/HTML escaping；如果要保留原文，可把原始文本放 fenced code block 或 blockquote 中。

- [R3-m2] `/` → `/learn`、`/pro`、wildcard fallback 这次路由重排没有前端回归测试兜底
  - **why**: 目前只能看到 `App.tsx` 的实现和人工 smoke evidence；仓库里没有 first-party `ui/frontend` 路由测试。对 demo front door 这种高可见路径，回归风险不应该只靠手测。
  - **evidence**: `ui/frontend/src/App.tsx:27-51`; repo search on 2026-04-22 found no first-party test files under `ui/frontend` other than `node_modules`
  - **suggested fix**: 增加一个最小 router test 套件，覆盖 `/`, `/learn`, `/pro`, `/cases/:id/report`, wildcard fallback。

- [R3-m3] 5180 port pin 没有做到文档全量收口
  - **why**: 主 README 已更新，但 `ui/frontend/README.md` 还在写 `127.0.0.1:5173`。这会让后续维护者误以为 port pin 不一致。
  - **evidence**: `ui/frontend/README.md:19-20`
  - **suggested fix**: 同步改成 `5180`，并注明 `CFD_FRONTEND_PORT` override。

- [R3-m4] 注释/提交叙事已经开始和实际实现脱节
  - **why**: `list_cases()` 的注释仍写“reference_pass preferred”，但 `_pick_default_run_id()` 早就改成 `audit_real_run` 优先；`LearnCaseDetailPage` 旁注也还写“first reference run”。另外 `47bc235` 的 commit body 把 BFS adapter 说成 `kOmegaSST`，实际生成器写的是 `kEpsilon`。
  - **evidence**: `ui/backend/services/validation_report.py:764-767`; `ui/backend/services/validation_report.py:290-307`; `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:459-463`; `src/foam_agent_adapter.py:1564-1568`; `knowledge/gold_standards/backward_facing_step.yaml:23-25`; commit `47bc235`
  - **suggested fix**: 把 stale 注释和回顾文档一起收口；review packet / STATE 里不要保留已经被代码推翻的叙事。

### 🟢 PRAISE
- `_normalize_contract_class()` 的前缀归一化顺序是安全的；`SATISFIED_UNDER_LAMINAR_CONTRACT` 会归到 `SATISFIED`，不会误落到 `COMPATIBLE`。见 `src/report_engine/contract_dashboard.py:845-849`。
- static dashboard test 至少真的在 pin class-count distribution；这次重新跑能把 drift 抓出来，本身说明这个测试方向是对的。见 `tests/test_report_engine/test_contract_dashboard_report.py:39-50`。
- 路由迁移保住了深链接，不是简单粗暴删旧路径；`/cases/:caseId/report`、`/runs`、`/audit-package` 都还活着。见 `ui/frontend/src/App.tsx:42-51`。

---

## Consolidated convergence verdict

BLOCK

## Prioritized action list

1. **Who**: role 3  
   **Severity**: 🔴 BLOCKER  
   **Effort estimate**: S  
   **Concrete change**: 在 `ui/backend/services/validation_report.py`, `ui/backend/schemas/validation.py`, `ui/frontend/src/components/PreconditionList.tsx` 把 precondition 从二值布尔改成 tri-state；补 `backward_facing_step`, `impinging_jet`, `turbulent_flat_plate` 的 API/UI regression tests，确保 `partial` 不再被漂白。

2. **Who**: role 3  
   **Severity**: 🔴 BLOCKER  
   **Effort estimate**: S  
   **Concrete change**: 修复 `tests/test_report_engine/test_contract_dashboard_report.py` 当前失败的 class-count drift。先决定 10-case 正确分布，再同步 `src/report_engine/contract_dashboard.py`、manifest 生成、测试断言，以及所有引用旧 `3/3/...` 分布的文档/回顾。

3. **Who**: role 1 / role 3  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: M  
   **Concrete change**: 给 live API 增加 `physics_contract_class`，并在 `/learn` 首页与 case-detail 中优先展示 compatibility 层，而不是先把 buyer 暴露给 `audit_real_run` 的 FAIL/HAZARD 统计。

4. **Who**: role 1  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: M  
   **Concrete change**: 重写 `/learn` 首屏 hero 与 `<title>`，把“AI-CFD workbench / signed audit evidence / caught false passes”写成 buyer-facing 价值主张；首页显式高亮 3 个 anchor cases。

5. **Who**: role 1  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: S  
   **Concrete change**: 修正 CTA 链路。在 `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` 里让 Advanced tab 的 Audit Package 按钮带上 `case` 和 `run` 参数；去掉或暂时隐藏 `LearnLayout` 里的 alert stub 导航项。

6. **Who**: role 2  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: S  
   **Concrete change**: 修正 `knowledge/gold_standards/backward_facing_step.yaml` 的 BFS anchor traceability：`ref_value` 与 cited source 对齐，删除或降级所有 `<2% plateau drift` 说法，并把 expansion-ratio mismatch 单列为 precondition。

7. **Who**: role 2  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: S  
   **Concrete change**: 在 `knowledge/gold_standards/plane_channel_flow.yaml` 里隔离 `y+=100, u+=22.8` 这个可疑点，避免未来真实 solver 被错误 gold 卡死。

8. **Who**: role 2  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: M  
   **Concrete change**: 重写 `knowledge/gold_standards/impinging_jet.yaml` 的 narrative，把 geometry mismatch、A4 convergence symptom、Nu extraction validity 拆开；后续 Phase 9 以 axisymmetric wedge comparability 为第一修复顺序。

9. **Who**: role 2 / role 3  
   **Severity**: 🟠 MAJOR  
   **Effort estimate**: M  
   **Concrete change**: 给 `physics_contract` 定义更稳定的 ontology 和 drift guard。至少在 schema 中显式建模 `reference_compatibility`, `observable_scope`, `runtime_hazard`，并增加 adapter-vs-gold contract drift tests。

10. **Who**: role 3  
    **Severity**: 🟡 MINOR  
    **Effort estimate**: S  
    **Concrete change**: 补 `ui/backend/routes/case_export.py` 的 escaping/sanitization 与 edge-case tests；同时清理 `ui/frontend/README.md:19-20` 的 `5173` 残留和 stale route comments。
