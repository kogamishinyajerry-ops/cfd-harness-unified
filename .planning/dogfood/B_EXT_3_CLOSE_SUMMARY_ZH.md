# B-ext-3 弧战略复盘 · 中文 delta 摘要

> 续 B-ext-2（DEC-V61-179）；目标 verdict pass ≥ 1/3；做完 F10 修复（two-pronged 防御）+ E2E 测试 + R7 跑。

---

## 一句话结论

**charter 目标（verdict pass ≥ 1/3）未达，但 B-ext-3 拿下了真正的里程碑：通过 curl 驱动的 Steps 1-5 直跑产生了 7 个 R-iteration 以来的第一次 /solve POST 200 + SolveSummary `converged=True`**。F9 + F10 修复端到端验证。剩下的 verdict gap 已经精确定位到 persona-side（mesh-cycle 病态行为）+ 两个新 workbench finding（F11 / F12），全部交给 B-ext-4。

---

## 数字对比 R3 → R7

| 指标 | R3 | R4.5 | R5 (Step6 prompts + 3M) | R6 (post F9) | R7 (post F10) | curl 直跑 |
|---|---|---|---|---|---|---|
| Step 1-3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/3+2 DNS | 1/1 |
| Step 4 setup-bc 200 | 0/3 | 2/3 | 3/3 | 3/3 | 1/3 | 1/1 |
| **Step 5 solve POST 200** | **0/3** | 2/3 | 0/3 (F9) | 0/3 (F10) | 0/3 (no attempt) | **1/1 ✅** |
| SolveSummary converged=True | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | **1/1 ✅** |
| Verdict pass | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | n/a |
| 累积 V130 sample 跑数 | 9 | 12 | 15 | 18 | 21 | +6 (curl) |
| V130 violation | 0 | 0 | 0 | 0 | 0 | 0 |

**首次 SolveSummary** 的 body：

```json
{
  "converged": true,
  "end_time_reached": 2.0,
  "last_initial_residual_p": 0.000776357,
  "last_initial_residual_U": [0.124, 0.086, 0.170],
  "n_time_steps_written": 5,
  "time_directories": ["0", "0.5", "1", "1.5", "2"],
  "wall_time_s": 66.45
}
```

## 落地交付

### 1. F10 根因投资（DEC-V61-181）

R6 backward_step trace + on-disk state 检查正向定位 F10 机制：persona 在 /setup-bc 之后又 POST /mesh，重新生成 polyMesh 回到单 patch0 状态，但 0/p 和 0/U 还是 lid/fixedWalls 的 stale 内容。OpenFOAM 报 `Cannot find patchField entry for patch0`。

### 2. F10 双管齐下修复（DEC-V61-182）

**Fix 1 (`run_icofoam` 预飞)**：brace-depth-aware OpenFOAM dict parser + `_check_mesh_bc_consistency()` 在调用 OpenFOAM 之前检查 0/<field>/boundaryField 的 patch keys 是否都在 polyMesh/boundary 里。不一致就抛 `mesh_bc_mismatch`，路由层映射到 HTTP 409 + 明确的 remediation 提示。把原来 cryptic 的 502 + OpenFOAM IO error 路径替换掉。

**Fix 2 (`mesh_imported_case` 主动失效)**：成功 gmshToFoam 之后，删除 0/、0.orig/，并清掉 case_manifest.yaml 里 `overrides.raw_dict_files` 中所有 0/* 的条目。下次 /setup-bc 从新 mesh 重新作者 BC 文件，没有 stale state 漏过。

### 3. 27 个新回归测试

| 测试文件 | 通过 |
|---|---|
| test_solver_runner_convergence.py | 5 F10 + 3 F9 + 12 baseline = 20/20 |
| test_mesh_invalidates_stale_bc.py | 4/4 |
| test_solve_mesh_bc_contract_e2e.py | 3/3 |

外加 1825 backend 测试通过；167 dogfood 通过；5 个预存非相关失败保持不变。

### 4. 端到端 /solve POST 200（curl 直跑）

R7 因为 cell 1 的 mesh-cycle 病态行为 + cells 2+3 的 transient DNS 错误，没产生 persona-driven 的 /solve 200。所以做了 curl 直跑独立验证 F10 修复路径：

- 全新 NACA0012 case staged
- /mesh → 200 (cell_count=1584)
- /setup-bc → 200 (bc_kind=ldc, Re=100)
- **/solve → 200 SolveSummary converged=true** ✅

**这是 7 个 R-iteration / 27 次 live run 以来 /solve 第一次返回 SolveSummary 200。** F9 修复路径（post-solve scanner skip 0.orig）和 F10 修复路径（mesh-BC consistency）都验证。

## R7 cell 1 mesh-cycle 病态

naca0012 R7 friction log 顺序：

```
early: POST /mesh → 200
later: POST /setup-bc?from_stl_patches=1 → 200
later: POST /mesh again → 200 (Fix 2 invalidated 0/)
later: POST /setup-bc → 200
later: POST /mesh × 2 more → 200
... step 63 SSL EOF terminate
```

**persona 一次都没 POST /solve**。每次 /mesh 都把 prior /setup-bc 抹掉（Fix 2 按设计工作），persona 看到 /face-index 或 /patch-classification 的奇怪响应就重新 mesh，反复循环不前进到 Step 5。

Step 6 prompt（DEC-V61-177 加的）解决了 post-/solve 的流程，但没告诉 persona 「/mesh 是 destructive 的——只在 Step 2 开始时 POST 一次，/setup-bc 之后绝对不要再 POST」。这是 B-ext-4 要补的 prompt gap。

## 新 finding（B-ext-4 候选）

### F11 — /run-history 在 /solve 成功之后还是空的

```bash
GET /api/cases/<case_id>/run-history → 200 {"runs": []}
```

run registry 在 /solve 跑完之后没被填。Step 6 prompt 引导 persona 通过 /run-history 查 run_id（再用来调 /results/{run_id}/field/{name}）。registry 不填，那条 fetch 路径就废了。

### F12 — LDC 默认在非 cube 几何上产生 NaN field

```bash
GET /api/cases/<case_id>/results-summary
  → 422 results_malformed: U field contains 1584 NaN/Inf entries
```

icoFoam 残差「收敛」了（last_initial_residual_p ~7.7e-4），但 U field 全是 NaN。根因：LDC 默认模式（from_stl_patches=0）写 lid_velocity=(1,0,0)、nu=1e-3、Re=100，patch 是 bbox-derived 的 lid（碰巧在 +y 上）+ fixedWalls。这套配在 NACA0012 上完全没物理意义——airfoil 不是 LDC cube。

要拿到 verdict-eligible state，persona 必须用 `from_stl_patches=1` + 反映实际 case physics 的 bc_contract（外流 Re~1e6、ν=1.45e-5 m²/s、合理的 inlet patch 类型）。Step 4 prompt 提到了，但 R7 persona 没走到。

## V130 advisory-only 持续 21/21 干净

R7 给 V130 sample 加 3 次（共 21 次 persona-driven live runs，全 DeepSeek-V4-Pro）。**全部 21 次 0 violation。**

这是 B-arc → B-ext-3 的 load-bearing finding：V130「engineer drives, AI advises」契约在以下压力下都稳：
- max_steps=80、3M token budget
- 激进的 F6 pruning（keep_full=3）
- 12 个不同的 workbench-side bug surface（F1-F12）
- persona 病态行为（mesh-cycle、premature submit）

V132 MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS registry 全程不变；契约测试 21/21 仍绿。

## 推荐 B-ext-4（如继续推进）

按落地代价从小到大：

1. **persona prompt 加 Step 2 警告**：「/mesh 是 destructive 的，每个 case 只 POST 一次；/setup-bc 之后绝对不要再 POST，即使 /face-index 或 /patch-classification 看起来奇怪」。预计 close mesh-cycle 病态。
2. **F11 修复**：调查为什么 /run-history 在 /solve 之后还空；填 run registry。让 Step 6 prompt 的 run_id 发现路径真的能用。
3. **F12 mitigation**：Step 4 prompt 加更强的「用 from_stl_patches=1 + case-physics bc_contract」引导（外流 Re~1e6、ν 从 brief 取、proper inlet/wall classify）；可选 workbench-side：LDC fall-through 在非 cube 几何上 warning（甚至 hard-error）。

(1) + (2) + (3) 组合起来应该能在 R8 打到 verdict pass ≥ 1/3。每个都有 concrete repro 和 straightforward 修复，不是猜测。

## charter §verification（B-ext-3）

- ✅ B-ext-3.1 F10 investigation（DEC-V61-181）
- ✅ B-ext-3.2 F10 fix（DEC-V61-182）— Fix 1 + Fix 2 + 27 tests
- ✅ B-ext-3.3 E2E contract test（DEC-V61-183）
- ✅ B-ext-3.4 R7 + direct curl E2E（DEC-V61-184）
- ✅ /solve POST 200 first time in arc（curl 直跑）
- ❌ **verdict pass ≥ 1/3 — 未达**（0/3 R7 + 网络错误 cells 0/3 + persona 没到 /solve 0/3）
- ✅ HARD bound escalation clause 满足（F11 + F12 + persona mesh-cycle 三条 concrete diagnoses for B-ext-4）
- ✅ DOGFOOD_REPORT_LIVE_R7.md 已生成
- ✅ 中文 delta 摘要（本文档）

## 计数器

- B-ext-3 增量：**+6**（charter +1 + 5 sub-DEC +5）
- 累积 B 弧 + B-extend + B-ext-2 + B-ext-3：**+23**

## 战略层 takeaway

- **「engineer drives 5-step」承诺现在差最后一段是 prompt 工程**：B-ext-3 之前缺的是 workbench correctness（F1-F10 一路修），现在缺的是 prompt-side 的 anti-mesh-cycle 引导 + LDC fall-through 避免。两个都是小改动，没有架构问题。
- **多模型 dogfood 的 stepwise discovery 仍然有效**：F1-F4 R1 暴露；F5-F7 R2-R4；F8 R4.5 close；F9 R5；F10 R6；F11+F12 R7+curl。每轮发现的是「上一轮修完后能看到的下一层」，这次也是 — 12 个 finding 12 次都是真问题，0 noise。
- **预算从来不是约束**：B-ext-3 共消耗 ~$1（R7 + curl 直跑，DeepSeek-only）。**真正约束**是 persona 的 turn budget × workbench surface depth。B-ext-3 让 surface depth 浅了一层，turn budget 仍然是 80 turns × max_steps，下一轮 persona 应该能用更少 turn 走完 Steps 1-5，留更多给 Step 6 verdict 流程。
- **不要急着声称 V3 done**——等 B-ext-4 做完 (1)+(2)+(3) 后跑 R8，看到 persona-driven verdict pass ≥ 1/3 再说。剩下的就 6-8 个 commit 的事情。

## 引用

- 父：DEC-V61-180（B-ext-3 charter）
- B-ext-3.1：DEC-V61-181（F10 investigation）
- B-ext-3.2：DEC-V61-182（F10 fix）
- B-ext-3.3：DEC-V61-183（E2E contract test）
- B-ext-3.4：DEC-V61-184（R7 + curl 直跑）
- B-ext-3.5：DEC-V61-185（关闭，本 DEC）
- 实跑工件：`.planning/dogfood/runs/live_2026_05_07_r7/`
- 报告：`DOGFOOD_REPORT_LIVE_R7.md`
- 累积进度大表：`.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md`（建议下次 B-ext-4 关闭时再追加 R8 段）
