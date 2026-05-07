# B-ext-4 弧战略复盘 · 中文 delta 摘要

> 续 B-ext-3（DEC-V61-185）；目标 verdict pass ≥ 1/3；做了 anti-mesh-cycle 提示强化 + F11（run-history 补全）+ F12（LDC NaN 警告）+ R7/R8/R9 三轮跑。

---

## 一句话结论

**charter 目标（verdict pass ≥ 1/3）连续第 3 个弧未达**（B-ext-2、B-ext-3、B-ext-4 累计 5 次 R-iteration 全为 0/3）。但 B-ext-4 拿下两个真里程碑：**R8 backward_step 第一次由 persona 自驱跑出 /solve POST 200 + measurement.yaml（converged=True）**；F11 + F12 全部端到端验证。剩下的 gap 已经不是"还有一个 workbench bug 没修"，而是结构性的：F13（/solve 502 在压力下出现）、F14（DeepSeek API read timeout）、persona 行为（max_steps / token budget 不够走完 Step 6 verdict-formation）。**B-ext-4 按 V133 round-cap=3 在此封盘**，未尽事项进 B-ext-5 战略转向（不是再来一轮）。

---

## 数字对比 R7 → R8 → R9

| 指标 | R7 (post anti-mesh) | R8 (post F11+F12) | R9 (max_steps=120, +1M) |
|---|---|---|---|
| /solve POST 200（persona 自驱） | 0/3 | **1/3 ✅ backward_step** | 0/3（502 + DeepSeek timeout 双重打击）|
| Step 6 调用 | 0/3 | 1/3 backward_step | 部分（naca0012/pipe_expansion 都是 502 retry loop 触发的 /run-history GET，不算真 Step 6）|
| submit_verdict | 0/3 | 0/3 | 0/3 |
| **Verdict pass** | **0/3** | **0/3** | **0/3** |
| naca0012 mesh-cycle | 6× POST /mesh | 6× | 10× |
| pipe_expansion mesh-cycle | 4× | 1× ✅ | 3× |
| /solve 502 事件 | 0 | 0 | **11×（F13 新发现）**|
| DeepSeek timeout | 0 | 0 | **1×（F14 新发现）**|
| 累积 V130 sample 跑数 | 24 | 27 | 30 |
| V130 violation | 0 | 0 | 0 |

**R8 是整个 B-ext-2/3/4 弧的最高点**：backward_step 自驱跑出 `reports/imported_..1e6fcecf/runs/2026-05-07T10-37-10Z/measurement.yaml`，残差 p=6.5e-7、continuity=9.9e-12、success=True。R9 没复现这一信号——backward_step 在 step 20 就被 DeepSeek 的 read timeout 干掉了，连 Step 4 都没到。

## R9 三个 cell 的真实退出原因

| cell | steps | 退出 | 关键路径 |
|---|---|---|---|
| naca0012 / experienced_fluent | 120/120 | max_steps_reached | 6× /solve 502 + 反复 mesh-cycle，从未拿到 /solve 200 |
| backward_step / novice | 20/120 | DeepSeek read timeout | 还在 Step 1-2 工具发现期就被外部 API 干掉 |
| pipe_expansion / debug | 113/120 | input_token_budget_exceeded | 11× POST /setup-bc-**400**（from_stl_patches=1 路径下 bc_contract validation 拒绝其 inlet/outlet/walls 划分）+ 5× /solve 502 |

总计：253 步、8M 输入 token、81K 输出 token、31.7 分钟。**0 个 verdict pass**。

## 落地交付（B-ext-4 真做了什么）

### 1. F11 修复（DEC-V61-188）
`/solve` 路由现在每次都会调 `write_run_artifacts()` 把 run_id + residuals + 收敛状态写到 `reports/{case_id}/runs/{run_id}/measurement.yaml`，无论 OpenFOAM 收没收敛。`SolveSummary.run_id` 字段在 schema 里返回给 persona。R8 backward_step 端到端验证通过。

### 2. F12 缓解（DEC-V61-189）
两路并进：
- **persona 提示**：3 个 prompt 文件（novice / experienced_fluent / debug）的 Step 4 加了 "`from_stl_patches=1` is mandatory for non-LDC geometry"，例子用 NACA0012 + backward_step 实际物理参数。
- **workbench 信号**：`SetupBcSummary` 加 `warnings: list[str]`；LDC 路径检测 bbox aspect > 3.0 时返回非 cube 警告（"lid_velocity=(1,0,0)/Re=100 calibrated for cavity tutorial cube; re-POST with from_stl_patches=1..."）。

R8 backward_step 显式引用了 "LDC-wrong run" 然后正确 re-POST，证明 prompt+warning 机制有效。

### 3. anti-mesh-cycle 提示强化（DEC-V61-187）
3 个 prompt 加了 "Step 2 destructive-mesh warning"，提示 mesh 重建会清空 0/* 状态，需要在 setup-bc 之后避免再 POST /mesh。pipe_expansion 从 R7 的 4× /mesh 降到 R8 的 1×，证明对**正常 cell** 有效；naca0012 仍然 6-10× /mesh，说明 prompt 救不回那个 cell 的病态行为。

### 4. R8 端到端首次验证 F11
`reports/imported_2026-05-07T10-37-10Z_..1e6fcecf/runs/2026-05-07T10-37-10Z/measurement.yaml`：

```yaml
success: true
key_quantities:
  end_time_reached: 5.0
  n_time_steps_written: 26
residuals:
  p: 6.5e-7
  Ux/Uy/Uz: ~1e-6
  continuity: 9.9e-12
duration_s: ~58
```

## R9 暴露的两个新 finding

### F13 · /solve 返回 502 Bad Gateway（压力诱发）

R9 总共 11 次 502，naca0012 6 次 + pipe_expansion 5 次。`/api/health` 全程 200，`cfd-openfoam` 容器 35 小时 healthy；但 R9 跑期间起了一个 ephemeral 容器 `compassionate_neumann`（运行 42 分钟）残留在那。R7 的 curl 直跑、R8 的 backward_step **都拿过 /solve 200**，所以这不是一个确定性 regression，而是反复跑出来的压力故障——可能是 solver-spawn race 或者资源压力（OOM/disk）。

**B-ext-4 不修这个**。先诊断再修，进 B-ext-5。

### F14 · DeepSeek API read timeout

backward_step step 20 等了 15.5 分钟没等到 chat completion 响应，client 抛 `read operation timed out`。R7 + R8 没出过；R9 31 分钟内出了 1 次。这是**外部 API 不稳**，不是 workbench 问题。修法：`OpenAICompatClient` 加 per-request timeout + retry-on-read-timeout，或换模型 vendor（Codex relay 的 gpt-5.4）。

## 为什么这次不是 "再修一轮就行"

5 次 R-iteration 数据：

- B-ext-2 R5：F9 出现，0/3
- B-ext-2 R6：F10 出现，0/3
- B-ext-3 R7：anti-mesh-cycle，0/3
- B-ext-4 R8：F11 + F12 落地，**1/3 拿到 /solve 200 但 0/3 verdict**
- B-ext-4 R9：max_steps 120 + 4M tokens，**回到 0/3 /solve 200**（被 502 + DeepSeek timeout 打回起点）

每修一个就冒一个新 finding。**这不是缺陷修复曲线，是策略错配**。具体来说：
1. **3-cell × 3-persona × 1-外部模型** 的 charter 把 5 个独立失败模式（mesh-cycle / F9 / F10 / F11 / F12）+ 2 个新 finding（F13 / F14）都耦合在一个 verdict 指标上，导致每次只能解一个。
2. naca0012 在 5 次 R-iteration 里**从未到 /solve 200**——这个 cell 对 persona 来说几何/网格层就是地狱，不是修 workbench 能救的。
3. R8 的 1/3 /solve 200 来自最简单几何（backward_step channel）。换句话说**workbench 链路在简单 case 上其实通了**，gap 在 persona 的 max_steps + token budget 不够走完 Step 6。

## B-ext-5 推荐方向（不是 B-ext-4.5，是真转向）

1. **先诊断 F13**：workbench /solve 502 在压力下出现的根因。没解决之前，persona 成功率上限就是 1/3（仅 backward_step）。
2. **重选 charter cell**：naca0012 退出，换更简单的 airfoil case（flat-plate BL 或 Couette）。
3. **缩小 charter 到 1 cell（backward_step）+ 专注 verdict-formation**：R8 已经证明这条路通；剩下的就是给 persona 足够 budget 走完 Step 6 + submit_verdict。可以做成 B-ext-5.1 一个 sub-DEC。
4. **F14 mitigation**：客户端 timeout/retry 小补丁。
5. **Step 6 verdict-formation 单元 fixture**：预先 stage 一个收敛 case，让 persona 只跑 Step 6 流程，看 prompt + /results-summary + submit_verdict 链是否能在隔离环境下产 verdict pass。能就证明 gap 全在 /solve 上游；不能就 prompt 本身要重写。

## V130 contract 状态

整个 B-ext-4 弧（R7 + R8 + R9 + curl E2E + 中间迭代）累计 ~30 sample，**V130 violation = 0**。persona 始终自驱写入，AI advisory 路由从未自动 mutate。**contract 稳如磐石**。这一项 charter 已经强烈达成。

## 累积 counter

B-ext-4.4 +1 → cumulative B-ext-4 = 5（charter / 4.1 anti-mesh / 4.2 F11 / 4.3 F12 / 4.4 close）。

不触发 post-incident retro：没有 Codex APPROVE→CHANGES_REQUIRED 翻盘、没有 blind-spot 事故、没有 autonomous_governance 规则改动。"charter 未达"在 close DEC 里 explicit 摊出来了，不需要单写 retro。

## 文件交付

- `.planning/decisions/2026-05-07_v61_190_b_ext_4_4_r9_close.md` — 本 DEC（V61-190）
- `.planning/dogfood/runs/live_2026_05_07_r9/` — R9 原始 artifacts（3 个 cell 的 friction_log + result + spec）
- `.planning/dogfood/B_EXT_4_CLOSE_SUMMARY_ZH.md` — 本文档

## References

- DEC-V61-179 · B-ext-2 close
- DEC-V61-185 · B-ext-3 close
- DEC-V61-186 · B-ext-4 charter
- DEC-V61-187/188/189 · B-ext-4.1/4.2/4.3 fixes
- DEC-V61-190 · B-ext-4.4 close（本 DEC）
