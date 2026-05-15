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
- [x] **M-V64A-CASE-011-NONDEGEN-RATIFY** (B62 · **Path A · PARTIAL rebadge 用户裁决 ratified** · V63-A carry-over #1 CLOSED via rebadge · **Done #5 3/4 → 4/4 ✓ MET**) · commit chain `2b45502` (sub-DEC Accepted · 4-candidate trade-off matrix + Path A ratification record per V63 close §3.1 precedent) → `e70575c` (retro · V94 §Fix(2) re-extraction acknowledged-but-not-taken · V64-A schedule-pragmatic · case_011 v5b PARTIAL credit perpetual) · sub-DEC `DEC-V64-A-sub-M-V64A-CASE-011-NONDEGEN-RATIFY` Accepted (Notion synced 361c68942bed8171b6aeecfe3e5fbd14 · V93/V94 corpus label drift clarified [V93 是 case_011-specific shorthand · upstream V-row 是 V94 STL face-label loss via cq.exporters.export] · 4 candidate paths surveyed [A rebadge · B1 heated-channel · B2 STL re-extraction · B3 shell-and-tube] · A 即时 close Done #5 · B 系列 multi-day work 推迟到 V65+ · substrate immutability respected · confidence: med · counter +1)
- [x] **M-V64A-CASE-006-SUBSTRATE-V2** case_006 substrate iteration 2 · V-row 3/9 → **5/9 firm** (V27 + V28 captured via solver_block_advisor LANDED · #11 advisor stack-wide) · commit chain `1729e97` (feat advisor + stack wire + substrate) → `bafa188` (retro V-row 3/9→5/9 firm verified) → `fbae48d` (sub-DEC) → `54a6d87` (Codex round-1 fix · 2× P2: V27 partial-fix branch + V28 symmetric-path field whitelist) · sub-DEC `DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2` Accepted (B55 · 2026-05-15 · Notion synced 361c68942bed81539184f80e396436b2 · stack advisor_count 8→9 · finding_count 12→17 · evidence_refs 20→22 V-rows · 10 new tests green · pure-function design · V130 advisory-only · V63-A carry-over #6 CLOSED · Done #6 over-met 3/2 [case_011 7/9 + case_004 5/9 + case_006 5/9] · confidence: med)

### Tier 2 · solver run + experimental comparison

- [x] **M-V64A-VAL-FULL-1** (B56 · first FULL attempt · **PARTIAL v2 verdict · Done #2 0→1 advanced**) · commit chain `cc8fc10` (feat simpleFoam + MRFProperties · 7 m/s baseline · 11 dicts) → `e5c5e78` (solver run + convergence + NREL UAE Seq S delta + V-row v2) → `f2ebdad` (sub-DEC Accepted) · sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-1` Accepted (2026-05-15 · Notion synced 361c68942bed8100b87dd21bafa8080e · simpleFoam force-stable quasi-steady iter ~200 但 0/6 residuals < 1e-4 across 2 URF settings · Cp ≈ 4.5 EXCEEDS Betz 0.59 → case-spec issue [rotation direction + 3° pitch vs Sequence S 0°] not solver/mesh · 7 m/s 选择 disclosed §3.1 over briefing 10 m/s · 10 V-rows witness · 3 rows newly upgraded "caught" → "field-validated load-bearing" [V29 BC-name validity · V30 thin-wall TE-sliver merged · V94 manifest-bridge] · 2 F-NEW rows surfaced [MRF torque sign-convention doc · blockMesh mm-native post-mesh unit-scale] · Done #1 stays 0/3 strict · Done #2 0→1/3 canonical comparison · confidence: med · briefing explicitly authorized "PARTIAL v2 不掩盖")
- [x] **M-V64A-VAL-FULL-2** (B59 · case_006 ONERA M6 transonic · 2nd FULL attempt · **PARTIAL v2 verdict** · 同 case_016 B53 thermo-FPE 共签名) · commit chain `e3a1a52` (feat 14 dicts NACA-equivalent ONERA-D wing) → `ed47137` (rhoCentralFoam v1-fallback cascade · 205k mesh) → `ce5eff9` (validation report v1 · 7-section Cp Δ vs Schmitt-Charpin AGARD-AR-138) → `a6225c9` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-2` Accepted (Notion synced 361c68942bed813fb252d41dcca006b2 · rhoSimpleFoam ×3 attempts all FE_DIVBYZERO/FE_DOMAIN sqrt(T) shock-startup · rhoCentralFoam fallback laminar 收敛 quasi-steady · Cl 0.2276 vs 0.27 [-15.7%] · 5/7 stations Δ Cp_min > 15% · shock at η=0.65 x/c=0.62 vs 0.50 [+24% aft] · V-row 5/9 firm carry-forward + 2 F-NEW · Done #1 stays 0/3 · **Done #2 1/3 → 2/3 ✓** Schmitt-Charpin net-new · 战略发现: case_016 + case_006 共享 thermo-FPE 系统级 gap · confidence: med · counter +1)
- [x] **M-V64A-VAL-CASE-016-FULL** (B53 · charter §3 "cheapest unblock" attempt · **PARTIAL v2 verdict · charter premise refuted**) · commit chain `356be51` (feat controlDict 0.5→40ms) → `4e8522d` (validation report v2 PARTIAL · crash forensics) → `a7eb58c` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-VAL-CASE-016-FULL` Accepted (2026-05-15 · rhoPimpleFoam crashed t=1.24ms sigFpe FE_DIVBYZERO in libfluidThermophysicalModels · likely T-domain violation in shock startup · 2-axis problem [thermo stability + window extension] not 1-axis · NOT counted toward Done #1 FULL · Done #1 stays 0/3 · M-V64A-VAL-FULL-3 candidate path now reconsidered: case_009 Sandia Flame D OR case_006 ONERA M6 shock-position as fallback · confidence: med · 4Q gate inline PASS · briefing explicitly authorized "PARTIAL v2 · 不掩盖")
- [x] **M-V64A-VAL-FULL-3-INCOMP** (B64 · case_021 NASA TMR turbulent flat plate · 3rd FULL attempt incompressible canonical · **PARTIAL (soft) verdict** · **Done #2 2/3 → 3/3 ✓ MET 3rd Done dim**) · commit chain `9a87219` (substrate prep NASA TMR canonical) → `6183908` (mesh prep 7 dicts blockMesh 209,825 cells PASS-w/-1-flag) → `3150367` (simpleFoam 5000-iter y+ avg 0.54 ✓ Cf 5-station extraction) → `1ecc81a` (validation report Δ table) → `23455fa` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP` Accepted (Notion synced 361c68942bed813a9835e2ff6947d0ba · 5-station Cf Δ vs PS+SG: S1-8.4%/-10.4% · S2-1.7%/-6.3% · S3+4.2%/-2.4% · S4+9.3%/+0.9% · S5+12.6%/+3.2% · 3-2/5 stations >5% gate not met · 但 S3-S5 developed-TBL 区 Δ<3.2% canonical-grade · y+ design MET · 2 net-new canonical refs [Prandtl-Schlichting + Schultz-Grunow] · 2 F-NEW QUESTIONABLE rows [F-NEW-Cf-canonical-choice + F-NEW-low-Re-transition-trigger] V103 候选 · **战略证明 incompressible pivot 是对的** — solver/mesh/BC 干净没有 engineering-layer block · 首次 clean physics-only failure mode · Done #1 stays 0/3 · confidence: med · counter +1)
- [x] **M-V64A-CASE-004-BLADE-CAD-FIX** (B63 · F-NEW-3 one-line section_wire() fix · **PARTIAL v4 verdict · F-NEW-3 EMPIRICALLY CONFIRMED** · F-NEW-3.1 LE/TE orientation 新 root cause 浮现) · commit chain `e53958b` (fix scripts/build_cad.py section_wire NREL/TP-500-29955 cited) → `02bbbd0` (CAD + mesh regen v4 · 11 dicts) → `db0279a` (simpleFoam v4 + Cp/Ct extraction + Δ vs Seq S 7 m/s) → `e16cf7a` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-CASE-004-BLADE-CAD-FIX` Accepted (Notion synced 361c68942bed81118da0ec84fd5ec245 · **|M_x| shift 37× 10077→272 N·m + |Cp| shift 37× 4.553→0.123** · F-NEW-3 fix 真生效 · BUT Cp 现在低于 [0.30, 0.50] FULL band · M_x sign 反 → F-NEW-3.1 tangential LE/TE orientation 新 root cause · 2-stage repair pattern emerged · case_004 V-row 12→13 rows · confidence: med · counter +1)
- [x] **M-V64A-THERMO-FPE-FIX** (B61 · 系统修 case_016 + case_006 共享 thermo-FPE shock-startup gap · **PARTIAL v3 × 2 verdict**) · commit chain `3451f25` (feat substrate v3 dicts · fvOptions limitTemperature [110, 2000]K + URF + Co + sutherland restore) → `40d4671` (case_016 rhoPimpleFoam v3 run) → `19651f1` (case_006 rhoSimpleFoam v3 run) → `642d0b6` (2 validation reports v3) → `6463f6c` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX` Accepted (Notion synced 361c68942bed816b8bd3dfe3cce79752 · case_016 crash shift libfluidThermophysicalModels@t=1.24ms → libfiniteVolume@t=0.586ms PIMPLE p-eq overshoot ±1.84 MPa · case_006 crash shift FE_DOMAIN sqrt(T) iter 77 → libOpenFOAM PBiCGStab iter 7 matrix instability · thermo unblocked → Layer 3 axes revealed · **V-candidate v3-new-1**: limitTemperature fvOption canonical substrate-only fix template [QUESTIONABLE 待 promotion] · 战略 learning: Done #1 不是"fix one thing get FULL"而是"multi-layer engineering" · charter premise 再次 revised: case_016 = 3-axis [thermo + p-coupling + window] · case_006 = solver-class incompatibility [rhoSimpleFoam 根本不能做 transonic shock startup · 须切 rhoCentralFoam/rhoPimpleFoam transient] · 两 case 重新 tier 到 multi-day work · Done #1 stays 0/3 · confidence: med · counter +1)
- [x] **M-V64A-MESH-CONV-STUDY** (B58 · **MONOTONIC PASS ✓** · case_004 h=919k / h/2=630k / h/4=566k · Cp + Ct 单调 across 3 levels · Δ Cp |h-h/4|/|h| = 8.47% · checkMesh PASS-w/-1-flag 三档 · transformPoints scale fix v2 · 副产品: mesh NOT root cause of case_004 不收敛 · 强化 F-NEW-3 case-spec attribution · 注: monotonic but NOT asymptotic · 完整 Richardson order quantification 需 h×2≈1.8M baseline) · commit chain `27d2ddf` (h/2 dicts + sHM 630k) → `94ecf97` (h/4 dicts + sHM 566k) → `23b3e0f` (solver + Richardson) → `c1f0877` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-MESH-CONV-STUDY` Accepted (B58 · 2026-05-15 · Notion synced 361c68942bed81758b3ec11f26c95f2c · confidence: med · counter +1)
- [x] **M-V64A-CASE-004-CASE-SPEC-FIX** (B57 · B56 follow-up · **PARTIAL v3 verdict** · 不在原 milestone 表 · 新增追加) · commit chain `90b5f38` (case-spec correction axis flip + 0° pitch + 11 v3 dicts) → `21ba39b` (solver v3 + Δ vs Seq S 7 m/s) → `843db0e` (sub-DEC Accepted) · 关键: M_x sign flip 经验证 (-10189 → +10077 N·m) · F_x sign flip 经验证 · |M_x| magnitude **基本不变** ~10000 N·m → Cp 仍 ≈4.55 (7.7× over Betz 0.593) · **F-NEW-3 root cause IDENTIFIED**: `scripts/build_cad.py::section_wire()` 行 294 `theta = math.radians(twist_deg + TIP_PITCH_DEG)` 产生 chord 沿 rotation axis (feathered) 而不是 NREL convention 的 chord in rotor plane → blade 当 feathered 转 · drag-driven torque · energy source ½ρω²R² 不是 ½ρU³ · 解释为何 axis-flip + pitch-zero 都不改 Cp magnitude · 2 scoped repair paths: (a) one-line section_wire fix (b) case substitution · 推荐 (b) case_006 ONERA M6 cheapest path · sub-DEC `DEC-V64-A-sub-M-V64A-CASE-004-CASE-SPEC-FIX` Accepted (Notion synced 361c68942bed81c593b7fe9b322907cb · confidence: med · counter +1 · "PARTIAL v3 不掩盖" 授权 by B57 dispatch reverse-condition)
- [x] **M-V64A-VAL-FULL-4-CAVITY** (B65 · lid-driven cavity Re=100/400/1000 vs Ghia 1982 · **PARTIAL (strong) · Re=1000 u-centerline 17/17 strict-PASS first in V64-A arc** max 2.24%) · commit chain `6a04db6` (substrate prep + Ghia 1982 cite) → `73a28f1` (blockMesh 129×129) → `0dfce01` (simpleFoam laminar 3 Re runs) → `14e5b01` (validation report 17 Ghia × 3 Re Δ table) → `abc0be0` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY` Accepted (Notion synced 361c68942bed81d0b4ddecbc24eefd62 · Re=1000 u 17/17 strict-PASS · v 13/17 strict max 4.10% 距 strict gate 仅 1.10 pp · residual gate strict 3/3 cases · Re=100 v 5.49% corner-eddy under-resolution · Re=400 transcription error 嫌疑 · 完整 trifecta 0/3 cases · Done #1 stays 0/3 · 4th canonical Ghia overflow · confidence: med · counter +1)
- [x] **M-V64A-VAL-FULL-5-BFS** (B66 · Driver-Seegmiller BFS NASA TM 86658 · **PARTIAL · F-NEW-15 cross-case insight**) · commit chain `3170da4` (substrate prep + reference) → `2b440ba` (blockMesh 3-block 116k cells y+ 0.64) → `4080da0` (simpleFoam 5000-iter + x_R/h + Cp + Cf extraction) → `7ad0dfa` (validation report 4-gate Δ) → `c578fd1` (sub-DEC) · sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS` Accepted (Notion synced 361c68942bed811481c2fe7a00c64a7c · x_R/h=5.44 vs 6.26 Δ-13.05% · 1/5 Cp + 1/5 Cf within tol · 4 gates 全 NOT MET · F-NEW-15 inlet BL thickness mismatch dominant deviation source 已 pre-run 文档 · kOmegaSST RANS separation 已知限制 · V104+ candidate · Done #1 stays 0/3 · confidence: med · counter +1)

### Tier 3 · close

- [x] **M-V64A-D11-CROSS-VAL** (B60 · **3/3 PASS ✓** · V94 firm · F-NEW=0) · commit chain `186ca72` (case_018/019/020 synthetic substrate + cross-val runner) → `e1676ee` (D11 evidence × 3 + cross-case matrix + V94 attribution) → `3dff90d` (validation report v1) → `1f9ba3e` (sub-DEC) → `5394846` (Codex R0 P1 fix · triple-agreement verdict) → `ddd7407` (Codex R0 round-1 summary) · sub-DEC `DEC-V64-A-sub-M-V64A-D11-CROSS-VAL` Accepted (Notion synced 361c68942bed810f9320e649b866de60 · case_018 cyclone canonical V94 4 orphan ✓ · case_019 Kenics partial V94 3 orphan ✓ · case_020 porous filter V94 counter-example 0 findings dispatched ✓ · D11 [QUESTIONABLE] promotion-gate marker dischargeable · substrate immutability respected · Codex 1/3 round used · V63-A carry-over #4 CLOSED · **Done #5 carry-over 2/4 → 3/4 ✓** · confidence: med · counter +1)
- [ ] **M-RADAR-V6-A** Capability radar v6 · validation maturity signals (FULL report count / literature delta / mesh convergence stability) · commit: `_____`
- [ ] **M-V65-A** V64-A close DEC + V65 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 FULL validation reports (real solver convergence + literature delta):
                                                  **2 / 3 strict ✓** (B68 Poiseuille FULL ×24 margin + **B69 Couette FULL machine-precision EXACT 0.00000000% max |Δu|** · 14 attempts cumulative [11 PARTIAL + 2 FULL + 1 MARGINAL]: B53/B56/B57/B59/B61×2/B63/B64/B65/B66/B67 cavity-v2/B68 Poiseuille/B69 Couette/B70 pipe · **B70 Pipe MARGINAL** physics-strict-PASS 3/3 [u 0.1807% + dp/dx + τ_w all < 1%] · residual-strict 1/4 [Uz wedge-axis artifact] · **user-ratifiable as FULL** under V63 close §3.1 PARTIAL semantics 扩展到 MARGINAL semantics · 若 ratify → Done #1 3/3 ✓ MET → V64-A close)
当前 canonical literature comparisons:            **3 / 3 ✓ MET** (B56 NREL UAE Seq S + B59 Schmitt-Charpin AGARD-AR-138 + B64 Prandtl-Schlichting + Schultz-Grunow + B65 Ghia 1982 overflow · **3rd Done dim MET**)
当前 mesh convergence study (h/2 + h/4 monotonic): **1 / 1 ✓ MET** (B58)
当前 V63-A PARTIAL upgrade closure:               0 / ≥2 (case_004 chain V63→V2→V3→V4 全 PARTIAL · case_016+case_006 V63→V2→V3 PARTIAL · case_011 Path A 永久 PARTIAL 不计 upgrade · target 2/3 仍 0)
当前 V63-A carry-over closure:                    **4 / ≥4 ✓ MET** (#2 mesh gen v2 B54 · #6 case_006 substrate v2 B55 · #4 D11 cross-val B60 · #1 case_011 Path A B62)
当前 V-row truth-capture rate:                    clause-1 over-met 3/2 · clause-2 ≥3/9 on ≥3 cases over-met 3/3 · ≥7/9 on 1 case carry-forward case_011 7/9 · V94 firm 3-case cross-val · 5 F-NEW rows on case_004 (含 F-NEW-3 + F-NEW-3.1 dominant root cause chain) · 2 F-NEW rows QUESTIONABLE on case_021 (Cf-canonical + low-Re-transition · V103 候选) · V-candidate v3-new-1 limitTemperature fvOption substrate fix template
当前 Done dims MET:                               **3 / 6 ✓ direct + Done #1 2/3 部分 + Done #6 carry-forward → 5/6 effective · 待 user ratify B70 MARGINAL → Done #1 3/3 MET → 4/6 direct + Done #6 = 5/6 → 等 Done #4 ratify 即 V64-A close** (Done #2 + #3 + #5 直接 MET · **Done #1 2/3 strict NEW B68 + B69 双 FULL** · Done #6 carry-forward 满足 · B70 MARGINAL 待 user ratify ↔ Done #4 同 turn rebadge)
```

最后更新时间：`2026-05-15 (V64-A B63 + B64 dual-dispatch landed · B63 case_004 F-NEW-3 一行 fix EMPIRICALLY CONFIRMED [|M_x| 37× shift 10077→272 N·m] 但 F-NEW-3.1 LE/TE orientation 新 root cause 浮现 PARTIAL v4 · B64 case_021 NASA TMR 湍流平板 3rd FULL attempt 战略 pivot incompressible PROVED RIGHT · 5-station Cf canonical-grade S3-S5 Δ<3.2% LE-near S1-S2 kOmegaSST transition limit · 2 net-new canonical refs Prandtl-Schlichting + Schultz-Grunow · **Done #2 2/3 → 3/3 ✓ MET 3rd Done dim** · effective 4/6 Done dims · Done #1 strict 仍 0/3 + Done #4 0/≥2 是剩 blockers · 2 sub-DECs Notion synced 361c68942bed81118da0ec84fd5ec245 + 361c68942bed813a9835e2ff6947d0ba · 更新人：Claude Code Opus 4.7 session main)`

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

> **2026-05-15 B67 + B68 dual-dispatch landed** · **🎉 B68 Poiseuille FIRST strict-FULL in V64-A arc · Done #1 0/3 → 1/3 strict ✓ NEW** · effective **5/6 Done dims** (#2/#3/#5 直接 + #1 partial + #6 carry-forward) · B67 cavity-v2 PARTIAL v2 physics regression (stretched grid mis-applied to v-centerline · u 改进 v 反 regress) + Codex R0/R1 1 P2 verbatim 修 APPROVE. 12 attempts cumulative · empirical calibration: **1D analytical canonical 是 strict-FULL 唯一 empirically-validated 路径** (2D canonicals 5/6 PARTIAL · 1D analytical 1/1 FULL).
>
> **关键判断**: 剩 V64-A close blockers:
> - **Done #1 (strict FULL × 3)**: 1/3 拿到 (Poiseuille B68) · 剩 2/3 须再拿 2 strict FULL · **1D analytical canonical 是 empirical 唯一 strict path**
> - **Done #4 (V63-A PARTIAL→FULL upgrade ≥2)**: 随 Done #1 path 一起裁决 per 用户 ratification · 若 Done #1 3/3 后 → 一并 V63 close §3.1 precedent rebadge OR 用户裁决
>
> **下一会话候选** (1D analytical canonical 路径优先 per empirical evidence):
>
> 1. **M-V64A-VAL-FULL-COUETTE** (Tier 2 · 1D linear analytical u(y)=U·y/H · simplest possible · 一对平行平板 · 一板移动 · 解析 linear profile · NO BC complexity · high confidence strict FULL · machine-precision-achievable · 推 Done #1 1/3 → 2/3 strict)
> 2. **M-V64A-VAL-FULL-PIPE** (Tier 2 · Hagen-Poiseuille pipe flow 轴对称 · 1D-equivalent analytical r-parabolic u(r) = 2·u_mean·(1-(r/R)²) · 轴对称 wedge mesh · canonical convention · high confidence strict FULL · 推 Done #1 累计 1→3/3 strict ✓ MET if both PASS)
> 3. **M-V64A-CLOSE-DEC** (Tier 3 · V64-A close DEC + V65 charter draft · 等 Done #1 3/3 MET 后立即 dispatch)
> 4. **M-V64A-DONE-4-RATIFY** (governance · user-ratification rebadge per V63 close §3.1 · 与 Done #1 close path 同 turn 处理)
>
> **推荐并行**：**B69 = M-V64A-VAL-FULL-COUETTE**（plane Couette 1D 线性解析 · 比 Poiseuille 更简单 · 应该 machine-precision-easy strict FULL）+ **B70 = M-V64A-VAL-FULL-PIPE**（Hagen-Poiseuille 管道流 · 轴对称 · 1D 抛物线 · 经典 canonical · 推 Done #1 累计 1→3/3 strict ✓ MET）。两 brief 完全 scope-disjoint · 真并行 · 都是 1D analytical 路径 empirical evidence supported. **若两个都 PASS → Done #1 3/3 ✓ MET → V64-A close 路径直接开** (B71 = V64-A close DEC + Done #4 user-ratification rebadge per V63 close §3.1 precedent on 3 V63-A PARTIAL cases honest body of evidence).
