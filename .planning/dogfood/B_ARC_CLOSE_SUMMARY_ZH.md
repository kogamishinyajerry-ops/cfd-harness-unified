# B 弧战略复盘 · 中文摘要

> 多模型 subagent 自食狗粮（multi-model subagent dogfood）  
> Blueprint v3 N1-N6 已完成；B 弧验证「工程师可在 LLM 离线条件下驱动 5-step 工作流」承诺。  
> **截至 2026-05-07，B 弧 charter (DEC-V61-162) 关闭**，含 Kogami 战略层 APPROVE_WITH_COMMENTS 复盘。

---

## 一句话结论

V3 的「工程师驱动」承诺在 N1-N6 当前 surface 下 **不可被实现**；B 弧通过 R1→R2→R3 三轮迭代把可达深度从「卡在 Step 1」推到「单 cell 抵达 Step 4」，**0/3 的 verdict 通过率不是设计错误，是 harness 端会话剪枝（F6）尚未实现**。这是个可控的 V2 工程问题，不是工作台架构问题。

---

## 数字看到的事

### 9 次实跑 verdict-floor 推进

| 工作流阶段 | R1 (基线) | R2 (B.5.1-3 后) | R3 (B.5.5 后) |
|---|---|---|---|
| Step 1 STL 导入 | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ |
| 突破 `/state` 404 墙 | **0/3** | 3/3 ✓ | 3/3 ✓ |
| Step 2 mesh | 0/3 | **3/3** | 3/3 |
| Step 3 physics | 0/3 | 1/3 | **2/3** |
| Step 4 setup-bc | 0/3 | 0/3 | **1/3** (backward_step novice 首破) |
| Step 5 solve | 0/3 | 0/3 | 0/3 |
| Verdict 通过 | 0/3 | 0/3 | 0/3 |

每轮迭代都 **真切地把工作流深度推进 2-3 步**。

### 治理面（V130 advisory-only contract）9 跑零违规

aggregator 在 9 次实跑（3 cells × 3 iterations，全部 DeepSeek-V4-Pro）中扫描 V130 违规模式（"AI told me" / "advisor said so" / "auto-apply" / "because the AI"），**0 命中**。在不断升压的 friction 下 persona 仍守住「我（工程师）是决策者」的语义。

**注意 sample bound**：这 9 跑都是 DeepSeek 同 3 cell 的 3 次重跑，不是 9 个独立 cell。Sonnet 4.6 + gpt-5.4 跨族（cross-family）的 V130 验证还要等那 6 cell 的 ANTHROPIC + CODEX_RELAY API key 配齐后再跑一次。

### 成本

DeepSeek 三轮 ~$0.87，user 已预授权额度充足。R3 输入 token 跳到 R2 的 3.3×（615k → 2.0M）才发现 **预算从来不是绑定约束，单 turn 的 64k input bandwidth 才是**。这是 R3 的 load-bearing strategic insight。

---

## 五个发现

| 编号 | 发现 | 状态 |
|---|---|---|
| F1 | persona 期望 `/state` → workbench 实际 `/state-preview`，404 墙挡住所有人 | **已闭** （B.5.1 prompt 改 + B.5.2 加 alias） |
| F2 | 工作台 URL taxonomy（`/api/cases/...` 查询 vs `/api/import/...` 变更）engineer 不可发现 | **已闭** （B.5.3 加 `/api/cases/{id}/actions` 发现端点） |
| F3 | `GET /physics` 不存在；engineer query-before-mutate 心智模型被破 | **已闭** （B.5.2 增 GET handler） |
| F4 | persona 用 `/api/openapi.json` 自救发现 schema，但消耗大量预算 | **已闭** （B.5.1 prompt 显式提示作为 fallback） |
| F5 | POST `/physics` 422：persona 不知 `MaterialContract` 嵌套结构 | **部分闭** （B.5.5 在 `/actions` 里塞 example_body；但 BC 阶段的 patch 名字仍未解决，与 F7 耦合） |
| F6 | harness 对话历史无剪枝；R3 已成单 turn input bandwidth 绑定 | **延期到 B-extend** |
| F7 | STL 入库报 `defaultFaces` 单一 patch，persona 无法引导分割成 inlet/outlet/wall | **延期到 B-extend** |

---

## 工作台四个新路由 + harness 一个 wire-format 修补

B.5 落地的实质性代码变更：

1. `GET /api/cases/{id}/state` — workbench 别名指向 `/state-preview`（DEC-V61-168）
2. `GET /api/cases/{id}/physics` — 新增只读路由，与现有 POST 配对（DEC-V61-168）
3. `GET /api/cases/{id}/actions` — 新增发现端点，返回完整 5-step + advisor + query 路由目录，含每 POST 的 `example_body` 示例（DEC-V61-169 + DEC-V61-170）
4. harness 端 `OpenAICompatClient` 新增 `_to_openai_messages()`：把内部 Anthropic-shaped tool_use / tool_result 块转换成 OpenAI / DeepSeek wire 格式（DeepSeek API 本来就因此 400 Bad Request 拒收，是 R1 第一轮飘掉的根因之一）

---

## Kogami 战略复盘结论

调用 `scripts/governance/kogami_invoke.sh` on `DOGFOOD_REPORT_LIVE_PROGRESSION.md`，verdict = **APPROVE_WITH_COMMENTS**。

5 个 findings（3× P2，2× P3），全部已 inline 闭合在进度报告里：

- **P2-1**：F5 不是「已 addressed」，是「partially addressed」，且和 F7 是耦合对，B-extend 应作为一组重新评估
- **P2-2**：「成本不是约束」的措辞过于轻描淡写；R3 的 3.3× 预算跳跃是 strategic discovery（per-turn bandwidth 才是绑定约束），需作为载重论点
- **P2-3**：V130「durable green」论断要加 sample bound 限定（DeepSeek 同 3 cell 重跑，不是 9 独立 cell）
- **P3-4**：charter §verification 列表里 [/] 项与 [x] 项视觉混排，分组不清
- **P3-5**：References 缺 review trail（缺少 Codex/Kogami 调用记录）

Q1 canary 在本次调用前因 `claude` CLI 升 2.1.129 → 2.1.131 自动重跑，5/5 PASS，baseline 已更新。

---

## charter §verification 八项与对应状态

| # | 验证项 | 状态 |
|---|---|---|
| 1 | 6 个 sub-DEC slim schema | ✅ |
| 2 | 每个 sub-DEC PR 含四问门 | ✅ |
| 3 | persona 模型在每跑前确认非 Opus | ✅ |
| 4 | 9 cell 实跑产出结构化 friction logs | ⚠ 3/9（DeepSeek diagonal）实跑 × 3 iterations = 9 个 friction logs；6 cell 延 |
| 5 | DOGFOOD_REPORT 按 severity 分级 + backlog | ✅ |
| 6 | B.5 修 3-5 个最高优先级 backlog | ✅（F1/F2/F3 全闭，F4 闭，F5 部分闭，F6/F7 延 B-extend） |
| 7 | Kogami 在 B.6 调用 | ✅（APPROVE_WITH_COMMENTS） |
| 8 | 中文战略摘要交付 | ✅（本文档） |

---

## 战略层启示

1. **N1-N6 的 surface 不是「engineer ready」**。把所有 advisor / 5-step 路由都做出来不等于工程师能驱动它们；route taxonomy 的可发现性是 V3 「engineer drives」承诺的最后一公里，N6 阶段从未验证过。B 弧把这个 gap 量化了。
2. **小手术能撬动大改善**。B.5.1-B.5.5 五个 sub-DEC 加起来约 250 LOC + 3 prompt 改写，verdict-floor 从「卡在 Step 1」推到 Step 4。这种比率不是巧合，是 V3 surface 距离「能用」只差 last-mile UX 的证据。
3. **harness 端的剩余 gap（F6 + F7）是 V2 工程，不是 V1 架构错**。F6 = 对话剪枝，F7 = patch 发现 + face-annotations 路由可发现性提升。两者都是 well-scoped 的 B-extend 候选。
4. **V130 contract 在真 friction 下 durable**。9 次跑 0 violations，比之前 N6 阶段任何 unit/contract 测试都强的 advisory-only 信号。但要全 charter 强度，得跑完 6 个延期 cell。
5. **多模型 dogfood 比单模型 + 人类工程师更高效**。3 个 model family 的 9 cell 设计可以在一个会话里跑 3 轮，每轮 ~5 分钟，总共 ~$1。等价人类工程师做同样深度的复测要数小时。subagent dogfood 模式应该作为后续 milestone 的标准 validation 步骤。

---

## 推荐下一步（按优先级）

### 即刻可做

1. **B-extend charter（V62 first arc）**：F6 + F7 为核心，目标是 verdict pass rate ≥ 1/3
   - F6 conversation pruning 在 `persona_runner.py`：保留最近 N 条 tool_result，把更早的压成 summary
   - F7 STL patch discovery：让 `/api/cases/{id}/actions` 包含 `face-annotations` + `patch-classification` 路由的 example body
2. **配 ANTHROPIC + CODEX_RELAY API key 后**全 9 cell 跑一次 R4，验证 cross-family V130 + 跨模型友好度

### 中期

3. 把 multi-model dogfood 升格为 **每个 milestone 标准 validation step**（不光 V3 的 B 弧，N7+ 的所有 milestone close 都跑一次）
4. workbench 路由设计 review：是否 unify `/api/cases/...` query + `/api/import/...` mutation 到一个家族？目前的拆分是 dogfood 揭示的最大 affordance gap

### 不建议

- 不要在 R4 之前就声称「V3 is done」。N1-N6 单元 + 集成 + 当前 dogfood 加起来仍只是部分 validation；workflow-completion validation（即 verdict ≥ 1/3）才是真 acceptance line。

---

## 计数器与下一阶段衔接

- `autonomous_governance_counter_v61` 增量：**+9**（charter +1 + 8 sub-DECs）
- B 弧总跨度 1 天（2026-05-07）；charter 投入产出比远高于 N6（N6 跨度 1 天但 sub-DEC 级别 6 个 + 多轮 Codex review 链）
- 后续工作（compressibility / multiphase / multi-engine）属于 BlueprintV4 territory，建议先做 B-extend 关闭 V3 真验收

---

## 引用

- 父：DEC-V61-130（V130 战略转向） / DEC-V61-162（B 弧 charter）
- B 弧八个 sub-DEC：DEC-V61-163..170
- B.6 关闭 DEC：DEC-V61-171
- Kogami 复盘工件：`.planning/reviews/kogami/b_arc_strategic_retro_2026-05-07/`
- 三轮实跑工件：`.planning/dogfood/runs/live_2026_05_07_r{1,2,3}/`
- 进度大表：`.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md`
