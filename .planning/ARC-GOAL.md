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
- [ ] **M-V64A-MESH-CONV-STUDY** mesh convergence study (h/2 + h/4) 在 ≥1 case 上 monotonic convergence trend · commit: `_____`

### Tier 3 · close

- [ ] **M-V64A-D11-CROSS-VAL** D11 cross-validation on case_018/019/020 (V63-A carry-over #4) · commit: `_____`
- [ ] **M-RADAR-V6-A** Capability radar v6 · validation maturity signals (FULL report count / literature delta / mesh convergence stability) · commit: `_____`
- [ ] **M-V65-A** V64-A close DEC + V65 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 FULL validation reports (real solver convergence + literature delta):
                                                  **0 / 3 strict** (B53 case_016 + B56 case_004 PARTIAL v2 · 2 honest attempts · NO inflation · M-V64A-VAL-FULL-2 + M-V64A-VAL-FULL-3 path 重选 [case_009 / case_006 ONERA M6 / case_011 non-degen / case_004 case-spec fix sub-DEC])
当前 canonical literature comparisons:            **1 / 3** (B56 case_004 NREL UAE Sequence S 7 m/s comparison performed · Δ Cp +1051% honestly reported · Done #2 dim 要求 comparison made not Δ within tolerance)
当前 mesh convergence study (h/2 + h/4 monotonic): 0 / 1 (start · case TBD · M-V64A-MESH-CONV-STUDY)
当前 V63-A PARTIAL upgrade closure:               0 / ≥2 (case_004 V63-A PARTIAL → V64-A PARTIAL v2 NOT upgraded · case_016 V63-A PARTIAL → V64-A PARTIAL v2 NOT upgraded · target 2/3 over-met 3/3)
当前 V63-A carry-over closure:                    **2 / ≥4** (#2 first half mesh gen v2 closed B54 ✓ · #6 case_006 substrate v2 closed B55 ✓ · 待 #2 second half [case_004 solver case-spec fix] + #1/#3/#4 中 ≥2)
当前 V-row truth-capture rate:                    clause-1 over-met 3/2 (case_011 7/9 + case_004 5/9 + case_006 5/9 firm · B55 V27+V28 LANDED solver_block_advisor) · clause-2 ≥3/9 on ≥3 cases over-met 3/3 carry-forward · ≥7/9 on 1 case carry-forward case_011 7/9
当前 Done dims MET:                               0 / 6 (V64-A active · Tier 1 全部 closed [B53 + B54 + B55] · Tier 2 first FULL B56 attempted PARTIAL v2 · 待 strict FULL × 3 + mesh conv + PARTIAL→FULL upgrade)
```

最后更新时间：`2026-05-15 (V64-A B55 + B56 dual-dispatch landed · B55 case_006 substrate v2 5/9 firm · solver_block_advisor LANDED #11 advisor stack-wide + Codex round-1 fix verbatim 2× P2 closed · B56 case_004 first FULL attempt PARTIAL v2 · Done #2 0→1 canonical literature comparison · Done #1 stays 0/3 strict no inflation · 2 sub-DECs Notion synced 361c68942bed81539184f80e396436b2 + 361c68942bed8100b87dd21bafa8080e · 更新人：Claude Code Opus 4.7 session main)`

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

> **2026-05-15 B55 + B56 dual-dispatch landed** · Tier 1 全部 closed (B53 case_016 PARTIAL v2 · B54 mesh gen v2 · B55 case_006 substrate v2 5/9 firm) · Tier 2 first FULL attempt B56 case_004 PARTIAL v2 verdict · 2 sub-DECs Notion synced. **关键经验**: Done #1 strict FULL 不能靠 cheapest-path 拿到 — case_016 thermo-FPE 阻、case_004 case-spec 阻 (rotation direction + 3° pitch 错配) · 必须真正修 case-spec 才能 push 0→1/3 strict FULL.
>
> **下一会话候选** (按推进 Done #1 strict FULL · ROI 排序):
>
> 1. **M-V64A-CASE-004-CASE-SPEC-FIX** (Tier 2 · NEW sub-DEC · B56 follow-up · 高 ROI · 修 case_004 rotation direction + 3° → 0° pitch · 重跑 simpleFoam · 拿 Done #1 0→1/3 strict FULL · NREL UAE Seq S 实验数据已经 ready · 阻力：需要 case.yaml 编辑 + 重跑 solver · 成本中等)
> 2. **M-V64A-MESH-CONV-STUDY** (Tier 2 · 推 Done #3 0→1 · case_004 mesh v2 919k 已经 ready · 再 sHM 跑 h/2 (≈460k) + h/4 (≈230k) refinement · case_004 是天然候选因为 mesh v2 LANDED · 副产品: 推进 Done #5 carry-over #2 second half [solver run] 或 reframe 为 mesh sensitivity)
> 3. **M-V64A-VAL-FULL-2** (Tier 2 · 第二次 FULL 尝试 · candidate substitution: case_009 Sandia Flame D vs Sandia experimental DB · 或 case_011 non-degen substrate swap · 或 case_006 ONERA M6 shock-position vs canonical M6 wing data · 成本最高但 Done #1 strict 必经)
> 4. **M-V64A-D11-CROSS-VAL** (Tier 3 · parallel-safe · D11 stl_face_label_validator 上 case_018/019/020 · V63-A carry-over #4 closure · 不阻 Tier 2 FULL path)
>
> **推荐并行**：**B57 = M-V64A-CASE-004-CASE-SPEC-FIX**（修 case_004 拿 strict FULL · Done #1 唯一近期可达路径）+ **B58 = M-V64A-MESH-CONV-STUDY**（case_004 mesh v2 + sHM h/2 + h/4 · 推 Done #3 0→1 · 副产品验证 mesh 不是 case_004 不收敛 root cause）。两个 milestone 共享 case_004 ready state · 但 B57 编辑 case.yaml + 重跑 solver · B58 跑 sHM refinement levels · scope-disjoint · 可真并行.
