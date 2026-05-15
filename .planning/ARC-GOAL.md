# ARC-GOAL · V64-A Validation Maturity Arc

**Plan SSOT**: [.planning/2026-05-15_v64_charter.md](2026-05-15_v64_charter.md)
**Charter DEC**: [.planning/decisions/2026-05-15_v64_charter_dec.md](decisions/2026-05-15_v64_charter_dec.md) (DEC-V64-A-charter Accepted 2026-05-15)
**Predecessor**: [V63-A Industrial Scale-Up · CLOSED 2026-05-15](ARC-GOAL-V63-A-CLOSED.md) (6/6 Done dims MET ✓ · `DEC-V63-A-close` Accepted · Done #4 via user-ratified PARTIAL semantics §3.1)
**Started**: 2026-05-15 (same B52 commit chain as V63-A close)
**Mode**: milestone-driven (no calendar)
**Selected**: V64-A "Validation Maturity" · user-ratified 2026-05-15 from 3 candidates (V64-B Frontend Activation + V64-C OSS Readiness + M6 Operationalization → Alternatives Appendix in plan-file §4-§5)

> 读这个文件 90 秒能回答：「这个 arc 完了没？」「该不该开新 arc？」「下个 session 接什么？」

---

## North Star（一句话）

> **把 V63-A 的 2/3 PARTIAL validation reports 真正推到 FULL · 实际跑 OpenFOAM solver 到收敛 · case_004 mesh gen v2 + NREL UAE Sequence S 实验对比 · case_006 substrate full e2e · case_011 用 non-degenerate substrate 重做 · ≥3 篇工业级 FULL validation reports 真实验证收敛 + 文献对比 + V-row attribution · 让 V62/V63 advisor stack 第一次"经实验数据验证过"而不只是"advisor 自审 PASS".**

> Note: plan-file references "2/3 PARTIAL" but V63-A actually landed 3/3 PARTIAL (case_011 + case_004 + case_016). V64-A scope expands to "3/3 PARTIAL → FULL" with the 3rd being case_016 window-extension + Heller-Bliss SPL. North Star intent unchanged.

---

## Done Definition（必须全部命中）

| # | 维度 | 起点 (V63-A close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | FULL validation reports (real solver convergence + experimental/literature delta) | strict 0 / 3 FULL · PARTIAL-credit 3/3 (V63-A) | **≥ 3 FULL validation reports (solver 真实收敛 + experimental/literature delta < 文献声明 tolerance + V-row attribution)** | `ls .planning/validation_reports/v64_*_FULL.md \| wc -l` 且每篇含 (a) solver 收敛 residual plot (b) experimental/literature comparison delta table (c) V-row attribution |
| 2 | Numerical comparison vs canonical literature | 0 (V63-A 未做实验对比) | **≥ 3 canonical literature comparisons · 1 per FULL report (NREL UAE Sequence S / Heller-Bliss SPL / ONERA M6 shock-position / Sandia Flame D / 等)** | each FULL report §experimental comparison cites canonical reference + reports delta |
| 3 | Convergence stability test | implicit (V63-A 单跑) | **≥ 1 case 在 ≥2 mesh refinement levels (h/2 + h/4) 跑出 monotonic convergence trend** | mesh convergence study log in 1 FULL report |
| 4 | V63-A PARTIAL upgrade closure | 3 PARTIAL (case_011 + case_004 + case_016) | **≥ 2 / 3 PARTIAL upgraded to FULL OR explicitly re-classified with documented rationale** | sub-DEC chain `DEC-V64-A-sub-VAL-UPGRADE-*` |
| 5 | V63-A carry-over closure | 8 items deferred | **≥ 4 / 8 closed (#1 + #2 + ≥2 of {#3 / #4 / #6})** | each closed via sub-DEC with V-row + retro chain |
| 6 | V-row truth-capture rate (sub-DEC scope) | clause 1: ≥5/9 over-met 2/1 · clause 2: ≥3/9 on ≥3 cases 3/3 MET | **≥ 1 case 拿到 ≥7/9 · ≥2 cases 拿到 ≥5/9 · 不准 alias 灌水** | retro §V-row attribution counter |

**任一未达成 = V64-A 不 close**，启动 root-cause retro。

---

## Done 条件**不算** Done 的反命题（防 paper-validation）

- ❌ FULL report 跑 solver 但 residual oscillating / 不收敛 → 失败 (real convergence required)
- ❌ Literature comparison cherry-picks query point 使 delta 看上去小 → 失败 (须 canonical baseline · 1 standard experimental sequence)
- ❌ PARTIAL → FULL upgrade 通过"重写 PARTIAL semantics"绕过实际收敛 → 失败 (semantics revision must be user-ratified · not unilateral · per V63 close §3.1 precedent)
- ❌ Mesh convergence study 跑了但 trend 非 monotonic 仍标 PASS → 失败
- ❌ V-row alias 灌水 → 失败 (distinct signature required · per V62/V63 precedent)

---

## 触发性 redirect 条件（命中 → 修改 plan，不算 Done）

| 条件 | 动作 |
|---|---|
| case_011 substrate 永远 V93 degenerate · 无可换 non-degenerate substrate 路径 | 重新 classify PARTIAL semantics + 用户裁决 (per V63 close §3.1 precedent) |
| Mesh gen v2 (case_004) STEP 准备难度 ≥ 3 周 | 切到 case_009 Sandia Flame D / 其他 Tier 2 case 验证 |
| 商业 CAE AI 拿到工业 case validation 证据 ≥3 篇 ship | OSS 准备拉前 (切到 V64-C 或合并) |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决 (继续 / 接受 / 推 sub-DEC) |
| 实验数据 (NREL UAE / Heller-Bliss / ONERA M6 / Sandia Flame D) 访问受阻 ≥ 2 周 | 切到另一 case literature source / 降级 to handbook correlation |

---

## Tier 状态板（每 milestone 完成时打勾 + 填 commit hash）

### Tier 1 · 解锁性（mesh gen + substrate prep · parallel · independent）

- [x] **M-V64A-MESH-GEN-V2** case_004 NREL Phase VI MRF mesh gen v2 · commit chain `a45214a` (feat 7 system dicts) → `f8c8024` (run log + checkMesh) → `f52d5df` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-MESH-GEN-V2` Accepted (B54 · 2026-05-15 · **919k cells · checkMesh PASS-with-1-flag** · rotor + stator regions + MRF zone via topoSet · 2 advisor F-NEW findings surfaced · V63-A carry-over #2 first half CLOSED · M-V64A-VAL-FULL-1 directly unblocked · solver execution NOT in scope here · confidence: med · Notion synced)
- [ ] **M-V64A-CASE-011-NONDEGEN** case_011 plate-fin HX non-degenerate substrate 替换 · OR PARTIAL semantics 用户裁决 rebadge · commit: `_____` · V63-A carry-over #1
- [x] **M-V64A-CASE-006-SUBSTRATE-V2** case_006 substrate iteration 2 · V-row 3/9 → **5/9 firm** (V27 + V28 captured via solver_block_advisor LANDED · #11 advisor stack-wide) · commit chain `1729e97` (feat advisor + stack wire + substrate) → `bafa188` (retro V-row 3/9→5/9 firm verified) → `fbae48d` (sub-DEC) → `54a6d87` (Codex round-1 fix · 2× P2: V27 partial-fix branch + V28 symmetric-path field whitelist) · sub-DEC `DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2` Accepted (B55 · 2026-05-15 · Notion synced 361c68942bed81539184f80e396436b2 · stack advisor_count 8→9 · finding_count 12→17 · evidence_refs 20→22 V-rows · 10 new tests green · pure-function design · V130 advisory-only · V63-A carry-over #6 CLOSED · Done #6 over-met 3/2 [case_011 7/9 + case_004 5/9 + case_006 5/9] · confidence: med)

### Tier 2 · solver run + experimental comparison

- [x] **M-V64A-VAL-FULL-1** (B56 · first FULL attempt · **PARTIAL v2 verdict · Done #2 0→1 advanced**) · commit chain `cc8fc10` (feat simpleFoam + MRFProperties · 7 m/s baseline · 11 dicts) → `e5c5e78` (solver run + convergence + NREL UAE Seq S delta + V-row v2) → `f2ebdad` (sub-DEC Accepted) · sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-1` Accepted (2026-05-15 · Notion synced 361c68942bed8100b87dd21bafa8080e · simpleFoam force-stable quasi-steady iter ~200 但 0/6 residuals < 1e-4 across 2 URF settings · Cp ≈ 4.5 EXCEEDS Betz 0.59 → case-spec issue [rotation direction + 3° pitch vs Sequence S 0°] not solver/mesh · 7 m/s 选择 disclosed §3.1 over briefing 10 m/s · 10 V-rows witness · 3 rows newly upgraded "caught" → "field-validated load-bearing" [V29 BC-name validity · V30 thin-wall TE-sliver merged · V94 manifest-bridge] · 2 F-NEW rows surfaced [MRF torque sign-convention doc · blockMesh mm-native post-mesh unit-scale] · Done #1 stays 0/3 strict · Done #2 0→1/3 canonical comparison · confidence: med · briefing explicitly authorized "PARTIAL v2 不掩盖")
- [ ] **M-V64A-VAL-FULL-2** case_011 (or non-degenerate substitute) FULL validation report · solver convergence + plate-fin HX literature/handbook 对比 · commit: `_____`
- [x] **M-V64A-VAL-CASE-016-FULL** (B53 · charter §3 "cheapest unblock" attempt · **PARTIAL v2 verdict · charter premise refuted**) · commit chain `356be51` (feat controlDict 0.5→40ms) → `4e8522d` (validation report v2 PARTIAL · crash forensics) → `a7eb58c` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-VAL-CASE-016-FULL` Accepted (2026-05-15 · rhoPimpleFoam crashed t=1.24ms sigFpe FE_DIVBYZERO in libfluidThermophysicalModels · likely T-domain violation in shock startup · 2-axis problem [thermo stability + window extension] not 1-axis · NOT counted toward Done #1 FULL · Done #1 stays 0/3 · M-V64A-VAL-FULL-3 candidate path now reconsidered: case_009 Sandia Flame D OR case_006 ONERA M6 shock-position as fallback · confidence: med · 4Q gate inline PASS · briefing explicitly authorized "PARTIAL v2 · 不掩盖")
- [ ] **M-V64A-VAL-FULL-3** 3rd FULL report · **candidate path (case_016 charter-cheapest refuted via B53)**: case_009 Sandia Flame D vs Sandia experimental DB OR case_006 ONERA M6 shock-position OR case_016 with thermo-FPE bounding (sutherland T-clamps) · commit: `_____`
- [x] **M-V64A-MESH-CONV-STUDY** (B58 · **MONOTONIC PASS ✓** · case_004 h=919k / h/2=630k / h/4=566k · Cp + Ct 单调 across 3 levels · Δ Cp |h-h/4|/|h| = 8.47% · checkMesh PASS-w/-1-flag 三档 · transformPoints scale fix v2 · 副产品: mesh NOT root cause of case_004 不收敛 · 强化 F-NEW-3 case-spec attribution · 注: monotonic but NOT asymptotic · 完整 Richardson order quantification 需 h×2≈1.8M baseline) · commit chain `27d2ddf` (h/2 dicts + sHM 630k) → `94ecf97` (h/4 dicts + sHM 566k) → `23b3e0f` (solver + Richardson) → `c1f0877` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-MESH-CONV-STUDY` Accepted (B58 · 2026-05-15 · Notion synced 361c68942bed81758b3ec11f26c95f2c · confidence: med · counter +1)
- [x] **M-V64A-CASE-004-CASE-SPEC-FIX** (B57 · B56 follow-up · **PARTIAL v3 verdict** · 不在原 milestone 表 · 新增追加) · commit chain `90b5f38` (case-spec correction axis flip + 0° pitch + 11 v3 dicts) → `21ba39b` (solver v3 + Δ vs Seq S 7 m/s) → `843db0e` (sub-DEC Accepted) · 关键: M_x sign flip 经验证 (-10189 → +10077 N·m) · F_x sign flip 经验证 · |M_x| magnitude **基本不变** ~10000 N·m → Cp 仍 ≈4.55 (7.7× over Betz 0.593) · **F-NEW-3 root cause IDENTIFIED**: `scripts/build_cad.py::section_wire()` 行 294 `theta = math.radians(twist_deg + TIP_PITCH_DEG)` 产生 chord 沿 rotation axis (feathered) 而不是 NREL convention 的 chord in rotor plane → blade 当 feathered 转 · drag-driven torque · energy source ½ρω²R² 不是 ½ρU³ · 解释为何 axis-flip + pitch-zero 都不改 Cp magnitude · 2 scoped repair paths: (a) one-line section_wire fix (b) case substitution · 推荐 (b) case_006 ONERA M6 cheapest path · sub-DEC `DEC-V64-A-sub-M-V64A-CASE-004-CASE-SPEC-FIX` Accepted (Notion synced 361c68942bed81c593b7fe9b322907cb · confidence: med · counter +1 · "PARTIAL v3 不掩盖" 授权 by B57 dispatch reverse-condition)

### Tier 3 · close

- [ ] **M-V64A-D11-CROSS-VAL** D11 cross-validation on case_018/019/020 (V63-A carry-over #4) · commit: `_____`
- [ ] **M-RADAR-V6-A** Capability radar v6 · validation maturity signals (FULL report count / literature delta / mesh convergence stability) · commit: `_____`
- [ ] **M-V65-A** V64-A close DEC + V65 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 FULL validation reports (real solver convergence + literature delta):
                                                  **0 / 3 strict** (B53 case_016 + B56 case_004 + B57 case_004 v3 · 3 honest PARTIAL attempts · NO inflation · F-NEW-3 blade chord-axis bug 已确定 · M-V64A-VAL-FULL-2 path 切到 case_006 ONERA M6 [substrate ready] OR case_009 Sandia Flame D)
当前 canonical literature comparisons:            **1 / 3** (B56 case_004 NREL UAE Seq S 7 m/s 一次 · B57 v3 fix-rerun 同 baseline 不计 net-new · 待 case_006 ONERA M6 Schmitt-Charpin OR case_009 Sandia TNF)
当前 mesh convergence study (h/2 + h/4 monotonic): **1 / 1 ✓** (B58 case_004 三档 h=919k/h/2=630k/h/4=566k · Cp + Ct 单调 PASS · Δ Cp 8.47%)
当前 V63-A PARTIAL upgrade closure:               0 / ≥2 (case_004 V63-A PARTIAL → V64-A PARTIAL v3 NOT upgraded · case_016 V63-A PARTIAL → V64-A PARTIAL v2 NOT upgraded · target 2/3)
当前 V63-A carry-over closure:                    **2 / ≥4** (#2 first half mesh gen v2 closed B54 ✓ · #6 case_006 substrate v2 closed B55 ✓ · 待 #2 second half [需 F-NEW-3 fix 或 case sub] + #1/#3/#4 中 ≥2)
当前 V-row truth-capture rate:                    clause-1 over-met 3/2 (case_011 7/9 + case_004 5/9 + case_006 5/9) · case_004 V-row 12 rows after B57 (4 F-NEW rows · F-NEW-3 是 root cause · F-NEW-4 procedural · F-NEW-1 resolved) · clause-2 ≥3/9 on ≥3 cases over-met 3/3 · ≥7/9 on 1 case carry-forward case_011 7/9
当前 Done dims MET:                               **1 / 6 ✓** (V64-A Done #3 MET ✓ via B58 monotonic mesh-conv PASS · 待 strict FULL × 3 + PARTIAL→FULL upgrade ≥2 + Done #6 ≥7/9 on 1 case · Done #2 + #5 部分推进未 MET)
```

最后更新时间：`2026-05-15 (V64-A B57 + B58 dual-dispatch landed · B57 case_004 case-spec fix PARTIAL v3 · axis-flip + 0° pitch 经验证但 Cp 不变 · F-NEW-3 blade chord-axis convention bug ROOT CAUSE IDENTIFIED at scripts/build_cad.py::section_wire() line 294 · B58 mesh-conv MONOTONIC PASS · Done #3 0/1 → 1/1 ✓ 首个 Done dim MET · 副产品: mesh NOT root cause of case_004 不收敛 · 强化 F-NEW-3 case-spec attribution · 2 sub-DECs Notion synced 361c68942bed81c593b7fe9b322907cb + 361c68942bed81758b3ec11f26c95f2c · 更新人：Claude Code Opus 4.7 session main)`

---

## 关键依赖图

```
M-V64A-MESH-GEN-V2          ─┐
M-V64A-CASE-011-NONDEGEN    ─┤  Tier 1 (parallel · independent prep work)
M-V64A-CASE-006-SUBSTRATE-V2 ┘
       │
       ↓
M-V64A-VAL-FULL-1 ──→ M-V64A-VAL-FULL-2 ──→ M-V64A-VAL-FULL-3
       │                      │                      │
       └──→ M-V64A-MESH-CONV-STUDY ──→ M-V64A-D11-CROSS-VAL
                                              │
                                              ↓
                                       M-RADAR-V6-A ──→ M-V65-A
```

Tier 1 milestones parallel-safe (different case dirs · different infra). Tier 2 FULL reports depend on Tier 1 prep + solver execution. M-V64A-VAL-FULL-3 (case_016 window extension) is the cheapest path and may execute parallel-safe with Tier 1 prep (solver already converged · only window extension needed).

---

## V63-A + V62-A 资产复用清单（per V64-A charter DEC §"V63-A 资产复用清单"）

V64-A is the "Validation Maturity" choice precisely because V63-A asset reuse is ≥ 95% (per plan-file §6 4-dim assessment 5/5). Direct reuse manifest (no new framework / no new architectural primitive):

- `advisor_stack.py` (~534 LOC · 11 LANDED advisors A1/A2-v2/A3/A4/A5/A7/A8/A10/D6/D10/D11) — direct reuse
- 4Q cross-feature audit framework (`test_4q_gate_stack_acceptance.py`) — direct reuse
- `/api/ai-review` route HTTP plumbing (M-D6-HTTP-WIRE 6-field schema · V62-A + V63-A) — direct reuse · no extension required for V64-A scope (frontend wiring deferred to V64-B)
- M-DRIFT-V2 audit-mode default at `/api/ai-review` boundary — direct reuse
- REQ-SCHEMA-EXPAND (6 wire-form fields after M-D6-HTTP-WIRE) — direct reuse
- V99-WIDEN shm_dict_validator alias resolution — direct reuse
- Track C dual-path methodology (HTTP TestClient + direct assemble_stack · adoption %% · 4Q gate inline · env -i LLM-offline rerun) — direct reuse
- V-series corpus convention (V51+ → V100 · single-row-per-failure-mode · numerics-class tagging) — direct reuse + V101+ extension
- 3 case substrate (case_004 / case_006 / case_011 inputs/) — direct reuse + iteration (substrate v2)
- D11 stl_face_label_validator (single-case land green) — direct reuse + cross-validation (M-V64A-D11-CROSS-VAL)
- D10 STANDARD_OPENFOAM_BCS catalog (138 BCs) — direct reuse · case-driven extension only
- 3 V63-A PARTIAL validation reports — reference + upgrade target (additive or replacement)

---

## 沿用 V62-A + V63-A 不变规则

- LLM offline 四问门控 (V130 thesis)
- advisor 不是 driver · 只 advise · engineer (or Claude Code session) 最终决策
- 双 corpus drift-prevention hook (M-DRIFT v1 + V62 v2) 保留
- session-end Notion sync (仅 Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven: ≥3 共享代码路径 / governance-rule-change → charter
- Codex 1-sync-trigger (auth/signing/security boundary) · ≥3 round cap
- Kogami opt-in (用户主动召唤 only)
- Spike-class 一等 scope class (≤30 LOC + 1 test + commit `confidence: <h/m/l>`)
- pre-implementation surface-scan (per DEC-V61-088) optional except new routes/ / pages/
- counter 纯遥测
- V-row distinct-signature enforcement (不准 alias 灌水)
- **PARTIAL semantics precedent (V63 close §3.1)**: PARTIAL → FULL upgrade requires real solver convergence + literature comparison · semantics rebadge requires user ratification · NOT unilateral

---

## v2.3 governance 合规（V64-A scope）

- V64-A 跨 ≥3 共享代码路径 (case substrate v2 + solver runtime + validation_reports/ v64 dir + V-series corpus V101+ + mesh refinement infra) → **charter-level DEC** Accepted via `DEC-V64-A-charter`
- Codex review per-milestone (nominal):
  - All V64-A Tier 1/2/3 milestones currently anticipated to **NOT** touch routes/ or pages/ (frontend wiring deferred V64-B) → Codex skip default
  - If a milestone unexpectedly touches routes/ai_review.py or new pages/, 1-sync-trigger applies and Codex pre-merge required
- Kogami opt-in (用户主动召唤)
- counter 纯遥测 (V64-A 重启 autonomous_governance counter · V63-A counter +9 ledger preserved in V63-A close DEC §10)

---

## 下一步建议（每次会话末由 main session 写）

> **2026-05-15 B57 + B58 dual-dispatch landed** · 首个 Done dim MET (Done #3 monotonic mesh-conv ✓) · case_004 root cause F-NEW-3 锁定 (blade chord-axis convention bug · scripts/build_cad.py::section_wire() line 294 · feathered blade 不是 rotor plane) · case_004 已经 3 次 PARTIAL (v2 / v3 / case-spec fix) · cheapest fix path 走完，必须 (a) one-line section_wire() blade CAD fix + 4th 尝试 OR (b) case substitution.
>
> **关键判断**: case_004 vs 切到 case_006 ONERA M6 · 后者 cheapest 因为：
> - case_006 substrate v2 已经 closed (B55 · V-row 5/9 firm)
> - ONERA M6 transonic wing 是 **canonical 黄金标准** compressible RANS validation case
> - Schmitt-Charpin experimental Cp distribution at 7 wing sections 公开 + 文献广泛
> - rhoSimpleFoam steady transonic solver · advisor stack 已有 V-row 支持
> - 不需要碰 blade CAD bug (与 case_004 是 disjoint substrate)
>
> **下一会话候选** (按 Done #1 strict FULL ROI 排序):
>
> 1. **M-V64A-VAL-FULL-2 (case_006 ONERA M6)** (Tier 2 · 高 ROI · substrate ready · canonical experimental data ready · rhoSimpleFoam compressible RANS · 第 2 次真 FULL 尝试 · 推 Done #1 0→1/3 strict + Done #2 1→2/3 net-new comparison)
> 2. **M-V64A-D11-CROSS-VAL** (Tier 3 · parallel-safe · D11 stl_face_label_validator 上 case_018/019/020 · V63-A carry-over #4 closure · 不阻 Tier 2 FULL path · 推 Done #5 carry-over 2/4 → 3/4)
> 3. **M-V64A-CASE-004-BLADE-CAD-FIX** (Tier 2 · NEW sub-DEC · 修 scripts/build_cad.py section_wire() blade chord-axis convention · 4th 解 v4 simpleFoam 尝试 · 较 (1) 风险高因为 fix 是否拿真收敛仍 unknown · 但能 close case_004 carry-over · 列为 follow-up)
> 4. **M-V64A-VAL-FULL-3 (case_009 Sandia Flame D)** (Tier 2 · 较高成本 · 还需 case_009 substrate prep · 串行后于 (1)) 
>
> **推荐并行**：**B59 = M-V64A-VAL-FULL-2 (case_006 ONERA M6)**（2nd FULL 尝试 · substrate ready · Schmitt-Charpin canonical · 推 Done #1 0→1/3 strict）+ **B60 = M-V64A-D11-CROSS-VAL**（Tier 3 parallel-safe · D11 cross-case 验证 · 推 Done #5 carry-over 2/4 → 3/4 · 完全 disjoint scope 不碰 case_006）。两个 brief scope-disjoint · 真并行.
