# B-ext-6 弧战略复盘 · 中文 delta 摘要

> 续 B-ext-5（DEC-V61-194）；charter 单一目标 = F15 fix + Variant A 真 brief 走到 submit_verdict（不 drop）。一次 R-iteration 拿下。

---

## 一句话结论

**B-ext-6 charter 顶层目标一次就达** —— Variant A 真 backward_step brief（L/h reattachment）从 R5.4 的 submit_drop 切到 submit_verdict 真发出（passed=False observed=0.0），整个 B-arc **第一次** 在真 brief 上把 verdict-formation chain 端到端跑通。F15 两层（路径 mismatch + 标量 only parser）全部修掉。passed=True 不是本弧目标，是 B-ext-7 战场。

---

## 数字对比 B-ext-5 → B-ext-6

| 指标 | B-ext-5 (Variant A) | B-ext-6 (Variant A v2 post-F15) |
|---|---|---|
| `/field/U` | 404 | **200 ✅** |
| 字节 | 0 | **33,948** (2829 cells × 3 × 4) |
| 出口 | submit_drop | **submit_verdict ✅** |
| 步数 | 9 | 12 |
| observed | n/a | 0.0（无 cell 位置算不了 L/h，诚实 0）|
| reference | 6.0 ± 10% | 6.0 ± 10% |
| passed | n/a | False（这一步本来就不是目标）|

## 累计 B-arc verdict 统计

| 弧 | submit_verdict 次数 | 其中 passed=True | 其中真 brief |
|---|---|---|---|
| B-ext-2 | 0 | 0 | 0 |
| B-ext-3 | 0 | 0 | 0 |
| B-ext-4 | 0 | 0 | 0 |
| B-ext-5 | 2（Variant B × 2 合成）| **2 ✅** | 0 |
| **B-ext-6** | **1（Variant A v2 真）** | 0 | **1 ✅** |
| **累计** | **3** | **2** | **1** |

## 落地交付（F15 两层全修）

### Layer 1 · 路径 mismatch fix

`ui/backend/routes/case_solve.py::solve` 在 run_icofoam 成功后加：

```python
if result.time_directories:
    final_time_name = result.time_directories[-1]
    target = case_dir / final_time_name
    link = case_dir / run_id
    if target.is_dir() and not link.exists():
        link.symlink_to(final_time_name, target_is_directory=True)
```

`<case_dir>/<run_id>` symlink 到 `<final_time>`（如 `<case_dir>/2`），让现有的 `/field/{name}` 路由解析到 OpenFOAM 时间步文件。best-effort：FS 不支持 symlink 静默 fallback 到原 404。

### Layer 2 · vector field parser

`ui/backend/services/render/field_sample.py` 加：
- `_INTERNAL_NONUNIFORM_VECTOR_RE` 匹配 `internalField nonuniform List<vector> N (...)`
- `_VECTOR_TRIPLE_RE` 抽取每个 `(vx vy vz)`
- `_parse_internal_vector_field()` 返回 flat float32 array(3*cell_count)
- `_VECTOR_FIELD_NAMES = {U, Uavg, U.air, U.water}` + `_is_vector_field(name)` dispatch
- `FieldSampleResult.components_per_cell: int = 1`（默认 scalar）
- `build_field_payload` 按 vector/scalar 派发 + cache 生命周期 preserves shape

`ui/backend/routes/geometry_render.py` 出口加 `X-Field-Components: {1|3}` header，前端 + persona 都用这个 split bytes。

## Variant A v2 验证（live live live）

实际跑出来的：

```
Variant A — real backward_step brief (L/h reattachment)
Running persona novice/deepseek-chat (max_steps=30) ...
  → VERDICT pass=False observed=0.0 ref=6.0±0.1rel
    steps=12 in_tok=380K elapsed=90.7s
```

调用链路：
1. `/run-history` 200 → 拿 run_id
2. `/results-summary` 200 → cell_count=2829 / u_x_min=-0.071 / is_recirculating=true
3. `/results/{run_id}/field/U` **200** ← 之前是 404
4. 解码 33948 bytes → 2829 cells × 3 × 4 bytes → 真 vector 数据
5. `submit_verdict(observed_value=0.0, rationale="无 cell 位置算不了 reattachment")` ✅

磁盘验证：
```
ls <case_dir>/
  ...
  2/                                       ← 真时间目录
  2026-05-07T12-19-10Z -> 2                ← 我们建的 symlink
```

cell 0 vector：`(-0.0109, 0.0067, -0.0001)`。物理量级正确（LDC defaults on backward_step），不是 NaN，不是 garbage——transport 通了。

## 为什么 passed=False

**persona 自己说的**：U 字段拿到了，但**没有 cell 中心位置**（Cx, Cy, Cz）。L/h reattachment 需要在下壁面找 u_x 符号变化的 x 位置；没有 cell 坐标就只能给 0.0。这是诚实交付。

OpenFOAM `simpleFoam` / `icoFoam` 默认不写 cell 中心。需要 `postProcess -func writeCellCentres -time <final>` 在 Docker 里跑一遍。

## 没做的（明确进 B-ext-7）

1. **Cell-center 暴露**（B-ext-7.1）— post-solve `writeCellCentres` hook + `/field/Cx` 等
2. **Reattachment 计算**（B-ext-7.2）—选 option A 服务端算 + /results-summary 加字段，或 option B persona 端自己用 numpy 算
3. **真物理路径**（B-ext-7.3）— from_stl_patches=1 + simpleFoam + kOmegaSST + 命名 patch；让 LDC defaults 退出 backward_step 的 prestage
4. **Variant A v3 + close**（B-ext-7.4）— 跑真物理 + cell centers，目标 observed L/h 接近 Kim 1980 的 6.0±10%

如果 7.3 自己变成多 DEC 弧，拆成：
- B-ext-7：cell centers + reattachment scan（LDC defaults，physically-wrong-but-well-defined L/h）
- B-ext-8：真物理路径

## V130 / V132 contract

**V130 advisory-only：累计 B-arc ~36+ sample，violation = 0**。从 B-ext-2 开始就是。本弧没有 AI advisor 改动，纯 read-only route + 内部 mutation；persona 始终自驱 submit_verdict。**这条 sub-charter 是整个 B-arc 唯一 fully 达成的**。

V132：solve route 的 symlink 是 best-effort post-solve metadata write，包在 try/except OSError 里，不算新 mutation surface。registry 不更新。

## 测试 + 回归

- `test_field_sample.py`：20 旧 + 4 新 = 24 pass
- 4 新测试覆盖：vector 解析 / cache shape preserves / scalar 回归不变 / symlink 解析
- backend 全集：1855 pass（B-ext-5 时是 1851，+4 全是新加）
- 5 老存在的不相关失败 unchanged（test_case_export / test_convergence_attestor / test_decisions_and_dashboard / test_g1_missing_target_quantity ×2）

## 累积 counter

B-ext-6 cumulative = 3（charter + F15 fix + close）。

不触发 post-incident retro：没 Codex blind-spot、没 autonomous_governance 改动、没 重复 CHANGES_REQUIRED。 "charter goal achieved with explicitly-deferred stretch goal" 在 close DEC 摊开，独立 retro 没必要。

## 文件交付

- `.planning/decisions/2026-05-07_v61_195_b_ext_6_charter.md`
- `.planning/decisions/2026-05-07_v61_196_b_ext_6_1_f15_fix.md`
- `.planning/decisions/2026-05-07_v61_197_b_ext_6_close.md` — 本 DEC
- `.planning/dogfood/B_EXT_6_CLOSE_SUMMARY_ZH.md` — 本文档
- `ui/backend/services/render/field_sample.py` · `routes/geometry_render.py` · `routes/case_solve.py`
- `ui/backend/tests/test_field_sample.py`
- `.planning/dogfood/runs/step6_rehearsal_2026-05-07T12-19-03Z/`

## 一段话概括 B-ext 全弧的进展（2-6）

| 弧 | 阶段性突破 | 累计 verdict |
|---|---|---|
| B-ext-2 | F9 + F10 surfaced | 0 |
| B-ext-3 | F10 fixed end-to-end · 第一次 /solve POST 200（curl 直跑）| 0 |
| B-ext-4 | F11 + F12 fixed · R8 第一次 persona /solve POST 200 | 0 |
| B-ext-5 | F14 + F13 partial · 第一次 verdict pass=True（合成 metric）· F15 finding | 2（合成）|
| **B-ext-6** | **F15 fixed · 第一次真 brief 走到 submit_verdict** | 3 |
| 接下来 | B-ext-7：cell centers + 真 reattachment 计算 → passed=True 真 brief |  目标 4+ |

每一弧都拿下一个真信号。瓶颈从 5 个嵌套失败模式纠缠（B-ext-2/3/4），收窄到 1 个结构性 finding（B-ext-5 → 6），到现在 1 个明确剩余路径（B-ext-7 cell centers + 真物理）。

## References

- DEC-V61-179 · B-ext-2 close
- DEC-V61-185 · B-ext-3 close
- DEC-V61-190 · B-ext-4 close
- DEC-V61-194 · B-ext-5 close
- DEC-V61-195 · B-ext-6 charter
- DEC-V61-196 · F15 fix
- DEC-V61-197 · B-ext-6 close（本 DEC）
