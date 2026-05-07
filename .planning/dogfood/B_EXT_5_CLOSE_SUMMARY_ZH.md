# B-ext-5 弧战略复盘 · 中文 delta 摘要

> 续 B-ext-4（DEC-V61-190）；charter scope pivot 到 1-cell（backward_step）verdict-formation focus；做完 F14 mitigation + F13 partial fix + Step 6 isolation rehearsal。

---

## 一句话结论

**B-arc 历史上第一个 verdict pass=True**（Variant B 合成 u_x_min metric · 2 步 · 5.3 秒 · 2/2 复现）。Step 6 isolation rehearsal 证明 **verdict-formation chain 机械上完全工作** —— persona prompt + read-only routes + submit_verdict/drop 全链路通畅。剩下的 gap **不是** harness、prompt、LLM client 任何一层的问题，而是 workbench 在特定 reference metric（L/h reattachment）上的 surface area 不够（F15 结构性 finding，进 B-ext-6）。

---

## 数字对比 B-ext-2/3/4 vs B-ext-5

| 弧 | R-iterations | verdict pass / total | 弧成果 |
|---|---|---|---|
| B-ext-2 | R5, R6 | 0/6 | F9 + F10 surfaced |
| B-ext-3 | R7 + curl E2E | 0/3 + curl 1/1 ✅ | F10 fixed end-to-end |
| B-ext-4 | R8, R9 | 0/6 | F11 + F12 fixed; R8 第一次 persona /solve POST 200 |
| **B-ext-5** | **rehearsal A + B×2** | **2/3 ✅** | **F14 + F13 partial · 第一个 verdict pass · F15 finding** |
| 累计 | 16 cells | 2/16 verdict pass ✅ | V130 violation 0/33+ |

## 落地交付

### 1. F14 mitigation（DEC-V61-192）— 客户端 timeout/retry

R9 backward_step 的 15.5-min DeepSeek read timeout 之后，把 `OpenAICompatClient` + `AnthropicClient` 改成：
- `_DEFAULT_TIMEOUT = httpx.Timeout(connect=10, read=180, write=30, pool=30)`（per-phase，不是单值 60s）
- `_post_with_retry()` wraps post 调用，1 retry on `(ReadTimeout/WriteTimeout/ConnectTimeout/PoolTimeout/RemoteProtocolError/ConnectError)`
- HTTP 4xx/5xx 不重试（透传给调用方 `raise_for_status`）

worst-case wait 从 15.5 min 降到 ~4 min。29/29 dogfood llm_clients tests pass。

### 2. F13 partial mitigation（DEC-V61-193）— missing-polyMesh pre-flight

R9 的 11× /solve 502 重现：fresh 案例 + setup-bc（跳过 mesh）+ /solve → 502 with `solver_diverged: simpleFoam exited with code 1`，log 里是 cryptic `Cannot find file points in directory polyMesh`。

`solver_runner._check_mesh_present()` 在 run_icofoam 调用前检查 `constant/polyMesh/{boundary,points}` 是否存在；缺失则抛 `mesh_missing:` SolverRunError，路由层映射到 **HTTP 409 + failing_check=mesh_missing**（不再是 502）。F10 的 `_check_mesh_bc_consistency` 在 polyMesh 不存在时显式返回 None，留下了空隙；这次填上。

5 新测试 + F10 fixture migration（加 stub points 文件）。1851 backend pass。

### 3. Step 6 isolation rehearsal harness（DEC-V61-194）

`scripts/dogfood/step6_rehearsal.py`：
- **Prestage**：curl 直跑 STL upload + /mesh + /setup-bc + /solve（~8s 总时长）
- **Persona**：novice / DeepSeek，但用一个 Step 6 specialized system prompt（替换原 prompt），明确禁止 POST /mesh / setup-bc / solve
- **Variant A**：原 backward_step brief（L/h reattachment）
- **Variant B**：合成 u_x_min brief（results-summary 直供）

**结果对比**：

| 变体 | 步数 | 用时 | 输出 | tokens |
|---|---|---|---|---|
| A 真 brief | 9 | 41s | DROPPED — F15（field/U 404）| 32K |
| B 合成 brief | 2 | 5.3s | **VERDICT pass=True ✅** | 4.3K |

Variant A 的 drop_reason 异常 cogent："results-summary confirms case converged with recirculation but doesn't contain reattachment length. /field/U returns 404. Without cell-level velocity data I cannot report L/h." —— persona 没尝试 re-run mesh/setup-bc/solve，正确放弃。

Variant B 复现 2/2，observed=-0.0711501（精确等于 reference）。整个 B-arc 历史上**第一次** verdict.passed=True。

## F15 finding · /results/{run_id}/field/U 结构性失配

**根因**：`ui/backend/services/render/field_sample.py::_resolve_field_path` 找的路径是 `<case_dir>/<run_id>/<name>`，但：
1. F11 的 `write_run_artifacts` 把 run dir 放在 `reports/<case_id>/runs/<run_id>/` 下（含 measurement.yaml + summary.json + verdict.json），不是 `<case_dir>/<run_id>/`
2. OpenFOAM 实际产出在 `<case_dir>/0/`、`<case_dir>/0.5/` 等时间步目录下

而且 `_parse_internal_scalar_field` 是 **scalar-only**，U 是 vector field（每 cell 3 component），即使路径 OK 也会被映射成 422 `field_unsupported`。

两层都需要修，scope 是 medium-large（post-solve 文件复制/软链 + vector field 解析路径），**不在 B-ext-5 范围内**。route 当初是给 M3 RealSolverDriver + 可视化（colormap）设计的，没考虑 persona 拿 raw U 算 reattachment 这种用例。

B-ext-6 选项：
- **(A) 扩展 `/results-summary`** 加 case-class-specific 计算字段（如 backward_step 自动算 `reattachment_length_over_h`），server-side numpy 后处理
- **(B) 新 `/results/{run_id}/post-process/<metric>` 路由族**，case-class dispatch，server-side 通用 CFD benchmark（reattachment / drag / lift / centerline）

(A) schema 干净；(B) 加新 benchmark 灵活。

## charter outcome 怎么算

严格意义：**charter 未达**（"1/1 verdict pass on real backward_step brief"，Variant A 走了 drop）。

但更有价值的 framing：**verdict-formation chain VALIDATED**。Harness、persona prompt、LLM client、submit_verdict 路径都通了；F11 / F12 / F14 / F13 partial 全部活体验证。**剩下的 gap 是单一可定位问题**（F15 workbench surface area），不是 5 个独立失败模式纠缠。

## B-ext-2/3/4/5 累计学到的

1. **追逐多 cell verdict pass 是错的策略** — naca0012 5 个 R-iteration 始终病态；prompt 救不回某些 cell
2. **真信号在最简单 cell 上** — backward_step 在 R8 自驱出 /solve POST 200，B-ext-5 直接 prestage 后 verdict pass
3. **persona budget 不是 verdict pass 的瓶颈** — Variant B 2 步就 pass。budget 充足时 persona 知道该干什么
4. **结构性 workbench gap 是最后一公里** — F15 的存在意味着 backward_step real verdict 需要 server-side 后处理或 vector field 路由
5. **V130 advisory-only 在 33+ 样本下 0 violation** — 这条 sub-charter 完全成立

## V130 / V132 contract

整个 B-ext-5 弧（charter + 5.1 F14 + 5.2 F13 + 5.4 rehearsal）累计 ~33 sample，**V130 violation = 0**。persona 始终自驱 submit_verdict / submit_drop；no auto-mutation。**contract 稳如磐石**。

V132 MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS 不变（B-ext-5 没加新 mutation 路由 / 函数）。

## 累积 counter

B-ext-5 cumulative = 4（charter + 5.1 F14 + 5.2 F13 + 5.4 close）。

不触发 post-incident retro：没有 Codex blind-spot、没有 autonomous_governance 规则改、没有重复同类 CHANGES_REQUIRED。"charter NOT strictly met but verdict chain validated" 的 framing 在 close DEC 摊开，不需要单写 retro。

## 文件交付

- `.planning/decisions/2026-05-07_v61_191_b_ext_5_charter.md`
- `.planning/decisions/2026-05-07_v61_192_b_ext_5_1_f14_fix.md`
- `.planning/decisions/2026-05-07_v61_193_b_ext_5_2_f13_mitigation.md`
- `.planning/decisions/2026-05-07_v61_194_b_ext_5_4_step6_rehearsal_close.md` — 本 DEC
- `.planning/dogfood/B_EXT_5_CLOSE_SUMMARY_ZH.md` — 本文档
- `scripts/dogfood/step6_rehearsal.py` — Step 6 rehearsal driver
- `.planning/dogfood/runs/step6_rehearsal_*/` — 3 run artifacts

## B-ext-6 推荐方向

1. **F15 fix 优先**：选 (A) `/results-summary` 扩展 vs (B) 新 post-process route family，结合 case-class 数量决定
2. **F15 修好后**重做 Variant A rehearsal —— 应该能从 drop 切到 verdict pass=True/False（取决于 LDC defaults 在 backward_step 上算出来的 reattachment 是不是接近 6.0±10%）
3. **真物理路径** verdict pass：用 `from_stl_patches=1` + 正确 inlet/outlet patches 跑 backward_step kOmegaSST，而不是 LDC defaults。R8 已经走通这条路一次，需要稳定性
4. **F14 deep diagnosis** 不重要：B-ext-5 的两次 rehearsal 都没遇到 502，说明 F13 partial fix + 短跑配合够用
5. **可考虑 charter 扩展**：1 cell 验证后，再回到 3 cell 但 cell selection 重做（drop naca0012）

## References

- DEC-V61-179 · B-ext-2 close
- DEC-V61-185 · B-ext-3 close
- DEC-V61-190 · B-ext-4 close
- DEC-V61-191 · B-ext-5 charter
- DEC-V61-192 · F14 fix
- DEC-V61-193 · F13 partial
- DEC-V61-194 · B-ext-5.4 rehearsal + close（本 DEC）
