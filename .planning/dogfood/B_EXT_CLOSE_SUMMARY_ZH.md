# B-extend 弧战略复盘 · 中文 delta 摘要

> 续 B 弧（DEC-V61-171）；目标 verdict pass ≥ 1/3；做完 F6 + F7 修复 + 收紧 prune + 提预算后再跑 R4 / R4.5。

---

## 一句话结论

**charter 目标（verdict pass ≥ 1/3）未达**，但**到达 Step 5 的 cell 数从 R3 的 0/3 跳到 R4.5 的 2/3**——bottleneck 从「workbench 不可发现」进化到「async solve job lifecycle persona 不会处理」。这是 B-ext-2 的明确入口。

---

## 数字对比

| 指标 | R3 (B 弧关闭) | R4 (F6+F7 修复) | R4.5 (tighter prune + 1.5M budget) |
|---|---|---|---|
| Step 1 import | 3/3 | 3/3 | 3/3 |
| Step 2 mesh | 3/3 | 3/3 | 3/3 |
| Step 3 physics 200 | 2/3 | 2/3 | 3/3 |
| Step 4 setup-bc 200 | 0/3 | 1/3 | 2/3 |
| **Step 5 solve POST 200** | **0/3** | **0/3** | **2/3** ✅ 突破 |
| Verdict pass | 0/3 | 0/3 | 0/3 ⚠ 未达 |
| 终止原因 | budget 全部 | budget 全部 | max_steps×2 / budget×1 |
| 平均 tokens / cell | ~660k | ~648k | ~1.33M |
| 平均墙钟 / cell | ~85s | ~140s | ~390s |

R3 → R4.5 单 cell 推进 1-3 个 step。F6 修复（会话剪枝）+ F7 修复（patch-split 路由暴露）+ R4.5 的 prune_keep_full=3 + 1.5M token + max_steps=50 + http_put 工具，**联合把 Step 5 突破**。

## 五个修复落地

1. **B-ext.1（DEC-V61-173 · F6）**：`persona_runner._prune_messages()`——保留初始 brief 与最近 K 个 turn-pair 完整，把更早的 tool_result.content 压成一行 stub `[pruned for context · tool_use_id=... · is_error=...]`。R4 / R4.5 中实际触发 7-15 次 / cell。
2. **B-ext.2（DEC-V61-174 · F7）**：
   - `/api/cases/{id}/actions` 新加 3 个 query 项：`patch_classification` / `face_annotations` / `face_index`（指向已有 workbench 路由）
   - Step 4 setup_bc description 重写：`defaultFaces` 单 patch 时必须先 split
   - 三个 persona prompt 都加 "Step 4 prerequisite — patch-split" 段
   - **harness 工具表新增 `http_put`**——face-annotations / patch-classification 是 PUT 不是 POST，否则修复无效（B-ext.2 实施过程中发现，inline 修复）

## 突破：Step 5 第一次被触达

backward_step novice R4.5：

```
Step 1 import ✓ → Step 2 mesh ✓ → Step 3 physics ✓ (3 次 422 后)
→ Step 4 setup-bc ✓ → Step 5 solve POST 200 ✓ → solve POST 200 (多次) → setup-bc 200 (多次)
→ max_steps_reached at 50 turns
```

naca0012 experienced_fluent R4.5：

```
Step 1 ✓ → Step 2 ✓ → Step 3 ✓ → /setup-bc 404 (404 一次) → /api/openapi.json discovery
→ Step 4 setup-bc 200 → Step 5 solve-stream POST 200 ✓ → bc-contract POST 200
→ max_steps_reached at 50 turns
```

pipe_expansion debug R4.5：仍卡 Step 4——多次 setup-bc 400，patch-split 流程没走通；F7 prompts 在 backward_step 工作但在 pipe_expansion 上失败。debug persona 风格更谨慎，多 turn 用于 patch-classification + face-annotations 调研，预算先于 setup-bc 200 耗尽。**F7 在 single-shell 几何上还有 model-specific 友好度问题**。

## V130 contract: 持续绿（sample 扩到 15 跑）

R1+R2+R3+R4+R4.5 = 15 次实跑（3 cell × 5 iter，全部 DeepSeek-V4-Pro）。aggregator 扫描违规模式 → **0 命中**。即使在 max_steps 压力下 persona 仍守住「我决策 / engineer-as-applier」语义。**仍 sample-bounded 到 DeepSeek**；跨族验证仍待 6 个延期 cell。

## 新发现 F8：async solve job lifecycle 是当前真 bottleneck

R4.5 first time workbench surface 不再是瓶颈。新瓶颈：

- POST `/solve` 立即返回 job ID，OpenFOAM 后台跑
- persona 必须 poll（`/run-history/{run_id}` / `/results-summary` / `/residual-history.png`）确认收敛
- 然后 fetch results / 计算 metric / submit_verdict
- 整个 post-solve 阶段约需 10-20 turns
- R4.5 max_steps=50 + 1.5M tokens 不够 (Steps 1-5 ~25-30 turns + post-processing ~10-20 turns)

## 推荐 B-ext-2（如继续推进）

按落地代价从小到大：

1. **persona prompt 加 "Step 6: post-processing & verdict" 段**——明确 solve job lifecycle / 轮询 → 读 residuals → 算 metric → submit_verdict（10 分钟）
2. **max_steps=80 + max_input_tokens=3M**（user 已说额度充裕）
3. （可选）workbench-side：加 `/solve-sync` opt-in 模式（保留现有 streaming 行为不变）
4. （可选）workbench-side：mesh-quality / actions catalogue 响应瘦身

(1) + (2) 单独应该能打到 verdict pass ≥ 1/3 在 R5。

## charter §verification（B-extend）

- ✅ B-ext.1 prune-window 测试 8/8
- ✅ B-ext.2 actions catalogue + http_put + persona prompts
- ✅ R4 + R4.5 实跑度量
- ❌ **verdict pass ≥ 1/3 未达**；轨迹正向（Step 5 reach 0/3 → 2/3）；F8 为新已识别 gap
- ✅ DOGFOOD_REPORT_LIVE_R4.md + R4_5.md 已生成
- ✅ 中文 delta 摘要（本文档）

## 计数器

- B-extend 增量：**+4**（charter +1 + 3 sub-DECs）
- 累积 B 弧 + B-extend：**+13** (B 弧 +9, B-extend +4)

## 战略层 takeaway

- **「engineer drives 5-step」承诺现在差最后一步**：从 N1-N6 完工到 verdict pass，差 6 个 commit + 1 个 R5 跑。
- **多模型 dogfood 的发现机制是 stepwise 自暴露的**：F1-F4 一轮就暴露；F5/F6/F7 第二轮；F8 第四轮才浮现。每轮发现的是「上一轮修完后能看到的下一层」。继续做有继续的边际信号。
- **预算从来不是约束**——R4.5 共消耗 ~$1.50（15 跑 × 5 iter，DeepSeek-only）。**真正的约束**是 turn budget（每轮 50 步 × 60 秒 = 50 分钟），所以**单 R 跑用更长 turns 比多跑更多 R 边际收益高**。
- **不要急着声称 V3 done**——等 R5 跑到 verdict pass ≥ 1/3 再说，不然就是空话。这次 B-extend 距离 done 只剩持续做 B-ext-2 即可。

## 引用

- 父：DEC-V61-171（B 弧关闭）
- B-extend：DEC-V61-172（charter）/ DEC-V61-173（F6 prune）/ DEC-V61-174（F7 patch + http_put）/ DEC-V61-175（关闭，本 DEC）
- 实跑工件：`.planning/dogfood/runs/live_2026_05_07_r4{,b}/`
- 报告：`DOGFOOD_REPORT_LIVE_R4.md` + `DOGFOOD_REPORT_LIVE_R4_5.md`
- 累积进度大表：`.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md`（建议下次 B-ext-2 关闭时再追加 R5 段）
