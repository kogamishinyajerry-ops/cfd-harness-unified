# B-ext-2 弧战略复盘 · 中文 delta 摘要

> 续 B-extend（DEC-V61-175）；目标 verdict pass ≥ 1/3；做完 Step 6 prompt + max_steps=80 + 3M budget 跑 R5/R6。

---

## 一句话结论

**charter 目标（verdict pass ≥ 1/3）未达**，但 B-ext-2 不是空跑：交付了 Step 6 persona prompts、修了 F9 workbench bug（带 3 个回归测试）、定位了 F10（workbench-side BC patch-name mismatch），并且按 charter HARD bound 把 F10 escalate 给用户作为 B-ext-3 入口。

---

## 数字对比

| 指标 | R3 (B 弧关闭) | R4.5 (B-extend close) | R5 (Step 6 + 3M budget) | R6 (post F9 fix) |
|---|---|---|---|---|
| Step 1 import | 3/3 | 3/3 | 3/3 | 3/3 |
| Step 2 mesh | 3/3 | 3/3 | 3/3 | 3/3 |
| Step 3 physics 200 | 2/3 | 3/3 | 3/3 | 3/3 |
| Step 4 setup-bc 200 | 0/3 | 2/3 | 3/3 | 3/3 |
| **Step 5 solve POST 200** | **0/3** | **2/3** | **0/3** ❌ regression | **0/3** ❌ F10 wall |
| Verdict pass | 0/3 | 0/3 | 0/3 | 0/3 ⚠ 未达 |
| 终止原因 | budget × 3 | max_steps×2 / budget×1 | max_steps × 3 | max_steps × 3 |
| 平均 tokens / cell | ~660k | ~1.33M | ~2.40M | ~3.03M |

R5 看起来是 **回退**——Step 5 reach 从 R4.5 的 2/3 掉到 0/3。但根因不是 Step 6 prompt 失效，而是 R4.5 没触发的 F9 bug 在 R5 浮现：persona 终于完整跑过 setup-bc，背地里产生了 `0.orig` 备份目录，post-solve scanner 在 `sorted(..., key=lambda s: float(s))` 时炸了（ValueError）→ /solve 全部 500/502。

R6 修了 F9，结果 /solve 又全 502——根因是 **F10**：setup-bc 写出的 `0/p/boundaryField` 用的 patch 名（`patch0/patch1/...`）和实际 mesh 的 `polyMesh/boundary` 里的 patch 名（F7 patch-split 后是 `inlet/outlet/wall`）对不上。OpenFOAM 直接拒绝读 BC 文件（`Cannot find patchField entry for patch0`）。

## 落地交付

### 1. B-ext-2.1（DEC-V61-177）— 三个 persona prompt 加 "Step 6: post-processing & verdict" 段

每个 persona 的 Step 6 段写明：

- `POST /solve` **是同步阻塞的**——返回 200 = OpenFOAM 已跑完，body 里就是 `SolveSummary`（converged / residuals / n_time_steps_written / wall_time_s），没有 job ID 也没有 polling
- 拿到 200 之后**禁止**再 POST /solve 或 /setup-bc（除非改参数）
- Convergence 判断决策树：converged=true → 进 results-fetch；converged=false 但残差下降 → 调大 n_iterations 重 POST 一次；stalled/diverging → /ai-diagnose + 改 ONE 个 conservative 参数
- 优先级排序的 read-only 路由：results-summary → run-history → residual-history.png → results/{run_id}/field/{name} → field-artifacts manifest
- Verdict 提交协议：observed_value 是 brief.reference 同单位的数值标量；rationale 必须展示 obs → metric formula → value 的算式链

42/42 persona library + assignment + runner 测试通过。`http_put` rule 顺手统一到三个 persona（之前 F7 修复后只更新了部分）。

### 2. F9 修复（B-ext-2.2 inline · commit 8d0f13e）

**问题**：`solver_runner.py:471` 的 post-solve scanner 把容器里 `[0-9]*` 匹配到的目录列表用 `sorted(..., key=lambda s: float(s))` 排序。`setup-bc` 会把 `0/` 备份成 `0.orig/`，于是列表里出现 `0.orig`，`float("0.orig")` 抛 ValueError。

**修法**：抽 `_filter_numeric_time_dirs()` helper，先过滤非 float-parseable 名字再排序。同时 defense in depth：`.bak`、任意非数字后缀也都 drop；保留科学计数法（`1e-05`）。

**测试**：3 个新回归测试；solver_runner 套件 15/15 全过。

### 3. F10 定位（escalate 给 B-ext-3）

R6 解锁 F9 后 /solve 仍然全部 502。手动 `curl -sX POST .../solve` 复现，body 里能看到：

```json
{"detail":{"failing_check":"solver_diverged","detail":
"simpleFoam exited with code 1; see ... log.icoFoam ..."}}
```

`log.icoFoam`：

```
--> FOAM FATAL IO ERROR:
Cannot find patchField entry for patch0
file: /tmp/.../<case>/0/p/boundaryField from line 6 to line 7.
```

`setup-bc` 服务在 0/p/boundaryField 里写 `patch0`、`patch1`、…，而 mesh 实际的 boundary patch 名（F7 patch-split 完成后）是 `inlet`、`outlet`、`wall`。BC contract 在 setup-bc 和 polyMesh/boundary 之间断裂。

## Step 6 prompts 的局部信号

R6 中 pipe_expansion/debug 在没有任何 /solve POST 200 的情况下，**主动调用了 /results-summary 1× 和 /run-history 2×**。这说明 Step 6 prompt 内容确实进了 debug persona 的决策回路。但要验证 prompt 是否能驱动**全部 3 个 persona** 走完 Step 6 → submit_verdict，必须先修 F10。

## 为什么不再迭代 R7-R9

charter HARD bound 写："如果 5 R-iterations 不出 ≥1/3，escalate 给用户带 diagnosis（八成 workbench 侧 solve 问题）"。R5+R6 = 2 iterations，但我们已经**正向定位** F10 是 workbench-side BC contract bug。R7-R9 在 F10 没修的情况下只会重复 502，烧 DeepSeek 但不前进。诚实的路径是把 F10 拿出来当 B-ext-3 入口，先修 setup-bc → polyMesh/boundary 的 patch-name 契约，再 R7 验证 Step 6 prompt 能否端到端驱动 verdict。

## V130 contract: 持续绿（sample 扩到 21 跑）

R1+R2+R3+R4+R4.5+R5+R6 = 21 次实跑（3 cell × 7 iter，全部 DeepSeek-V4-Pro）。aggregator 扫描违规模式 → **0 命中**。即使在 max_steps=80 + 3M token 压力下 persona 仍守住「我决策 / engineer-as-applier」语义。仍 sample-bounded 到 DeepSeek；跨族验证仍待 6 个延期 cell。

## 推荐 B-ext-3（如继续推进）

按落地代价从小到大：

1. **F10 修复**（主 blocker）—— setup-bc 服务读 polyMesh/boundary 实际 patch 名，emit 匹配的 0/<field>/boundaryField 键值；或者在 solver-call layer 把 engineer 给的语义名（inlet/outlet/wall）remap 成 mesh 实际 patch 名再 invoke OpenFOAM
2. **加 integration test**：每个 charter case 的 Steps 1-5 完整跑一遍，必须出 /solve POST 200 + `converged` 字段
3. **R7 live 跑**：F10 修完后跑一轮，验证 Step 6 prompt 在 SolveSummary 真的返回时能否驱动 verdict pass ≥ 1/3
4. （可选）workbench-side：mesh-quality / actions catalogue payload 瘦身（来自 R4.5 close 的延期项）

(1)+(2)+(3) 单独应该能打到 verdict pass ≥ 1/3 在 R7。

## charter §verification（B-ext-2）

- ✅ B-ext-2.1 Step 6 prompts 落地 + 42/42 测试
- ✅ B-ext-2.2 R5 + R6 实跑 measurement + F9 修复 + 15/15 回归测试
- ✅ F10 正向定位 + concrete reproduction
- ❌ **verdict pass ≥ 1/3 未达**（0/3 R5; 0/3 R6）
- ✅ HARD bound escalation clause 满足（F10 是要求的 diagnosis）
- ✅ DOGFOOD_REPORT_LIVE_R5.md 已生成（涵盖 R5+R6）
- ✅ 中文 delta 摘要（本文档）

## 计数器

- B-ext-2 增量：**+4**（charter +1 + V61-177 +1 + V61-178 +1 + V61-179 +1）
- 累积 B 弧 + B-extend + B-ext-2：**+17**

## 战略层 takeaway

- **「engineer drives 5-step」承诺现在差最后一段还有两步**：从 N1-N6 完工到 verdict pass，差 F10 修 + Step 6 prompt 端到端验证 + 1 个 R7 跑
- **多模型 dogfood 的发现机制是 stepwise 自暴露的，仍然有效**：F1-F4 一轮就暴露；F5/F6/F7 第二轮；F8/F9 第三轮（B-extend）；F10 第四轮（B-ext-2）。每轮发现的是「上一轮修完后能看到的下一层」，没出现 noise。10 个 finding，10 次都是真问题
- **预算从来不是约束**——R5+R6 共消耗 ~$2-3（6 跑 × 6 iter 平均，DeepSeek-only）。**真正的约束**是 turn budget × workbench surface depth，所以**单 R 跑用更长 turns 比多跑更多 R 边际收益高**——但前提是 workbench surface 已经修干净；F10 没修时多跑 R 是浪费
- **不要急着声称 V3 done**——等 B-ext-3 修完 F10 + R7 跑到 verdict pass ≥ 1/3 再说，不然就是空话

## 引用

- 父：DEC-V61-176（B-ext-2 charter）
- B-ext-2.1：DEC-V61-177（Step 6 prompts）
- B-ext-2.2：DEC-V61-178（R5+R6 measurement + F9）
- B-ext-2.3：DEC-V61-179（关闭，本 DEC）
- 实跑工件：`.planning/dogfood/runs/live_2026_05_07_r5/`、`live_2026_05_07_r6/`
- 报告：`DOGFOOD_REPORT_LIVE_R5.md`（覆盖 R5+R6）
- 累积进度大表：`.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md`（建议下次 B-ext-3 关闭时再追加 R7 段）
