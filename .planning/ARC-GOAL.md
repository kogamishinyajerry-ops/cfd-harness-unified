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

- [ ] **M-V64A-MESH-GEN-V2** case_004 NREL Phase VI MRF mesh gen v2 · 解锁 solver execution · commit: `_____` · V63-A carry-over #2 first half
- [ ] **M-V64A-CASE-011-NONDEGEN** case_011 plate-fin HX non-degenerate substrate 替换 · OR PARTIAL semantics 用户裁决 rebadge · commit: `_____` · V63-A carry-over #1
- [ ] **M-V64A-CASE-006-SUBSTRATE-V2** case_006 substrate iteration 2 · V-row 3/9 → 5/9 (V26-V28/V31/V32 + D4 ≥2 captured) · commit: `_____` · V63-A carry-over #6

### Tier 2 · solver run + experimental comparison

- [ ] **M-V64A-VAL-FULL-1** case_004 NREL Phase VI MRF FULL validation report · mesh v2 + solver convergence + NREL UAE Sequence S 实验对比 (≥3 wind speed points) · commit: `_____`
- [ ] **M-V64A-VAL-FULL-2** case_011 (or non-degenerate substitute) FULL validation report · solver convergence + plate-fin HX literature/handbook 对比 · commit: `_____`
- [ ] **M-V64A-VAL-FULL-3** 3rd FULL report · **candidate (cheapest path)**: case_016 window extension + Heller-Bliss SPL comparison (solver already converged 8.5e-8 · only on-disk window extension needed) · alternative: case_009 Sandia Flame D vs Sandia experimental DB · or case_016 ONERA M6 shock-position · commit: `_____`
- [ ] **M-V64A-MESH-CONV-STUDY** mesh convergence study (h/2 + h/4) 在 ≥1 case 上 monotonic convergence trend · commit: `_____`

### Tier 3 · close

- [ ] **M-V64A-D11-CROSS-VAL** D11 cross-validation on case_018/019/020 (V63-A carry-over #4) · commit: `_____`
- [ ] **M-RADAR-V6-A** Capability radar v6 · validation maturity signals (FULL report count / literature delta / mesh convergence stability) · commit: `_____`
- [ ] **M-V65-A** V64-A close DEC + V65 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 FULL validation reports (real solver convergence + literature delta):
                                                  0 / 3 (start) · PARTIAL-to-FULL conversion 0/3 起点
当前 canonical literature comparisons:            0 / 3 (start)
当前 mesh convergence study (h/2 + h/4 monotonic): 0 / 1 (start · case TBD)
当前 V63-A PARTIAL upgrade closure:               0 / ≥2 (start · target 2/3 · over-met 3/3)
当前 V63-A carry-over closure:                    0 / ≥4 (start · 8 items deferred · target #1+#2+≥2 of {#3/#4/#6})
当前 V-row truth-capture rate:                    clause-1 baseline V63-A 2/1 (case_011 7/9 + case_004 5/9) · 起点 carry-forward · V64-A 自身 capture 0/9 cases (start)
当前 Done dims MET:                               0 / 6 (V64-A active · M-V64A-VAL-CASE-016-FULL B53 first sub-DEC candidate cheapest unblock)
```

最后更新时间：`2026-05-15 (V64-A arc 初始化 · ARC-GOAL.md fresh skeleton from V63-A close · 6 Done dims set per V64-A charter DEC · DEC-V64-A-charter Accepted · plan-file ratified 2026-05-15 · V63-A ARC-GOAL frozen at ARC-GOAL-V63-A-CLOSED.md · V64-A Tier 1 dispatch unblocked · M-V64A-VAL-CASE-016-FULL B53 candidate per task brief · ARC-GOAL 协议: B52/B53 双方都改 ARC-GOAL 需手动合并 · 更新人：Claude Code Opus 4.7 session main · B52 V63→V64 governance transition)`

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

> **2026-05-15 V63-A CLOSE + V64-A charter Accepted** · V64-A North Star ratified · plan-file `2026-05-15_v64_charter.md` (renamed from `_draft`) + charter DEC `2026-05-15_v64_charter_dec.md` Accepted.
>
> **下一会话候选** (按 cheapest-path-first 排序):
> 1. **M-V64A-VAL-CASE-016-FULL** (Tier 2 · cheapest unblock · solver already converged 8.5e-8 · only on-disk window extension + FW-H FFT to compute SPL + Heller-Bliss canonical comparison · 实验数据可文献获取 · 可能 1 milestone 直接拿到 1 FULL report)
> 2. **M-V64A-CASE-006-SUBSTRATE-V2** (Tier 1 · 中等成本 · V-row 3/9 → 5/9 capture from V26-V28/V31/V32 + D4 · 已有 evidence/v1/face_geometry.json 可衍生)
> 3. **M-V64A-MESH-GEN-V2** (Tier 1 · 中等成本 · case_004 unblock · 需 STEP roundtrip + sHM tuning · NREL UAE 实验数据公开)
> 4. **M-V64A-CASE-011-NONDEGEN** (Tier 1 · 高成本 · 须 substrate 选择 + 物理替换 · 或 PARTIAL 用户裁决 rebadge)
>
> **推荐**：**M-V64A-VAL-CASE-016-FULL** (B53) — cheapest unblock per task brief · solver 已 converged 8.5e-8 · 仅 window 延长 · 单 sub-DEC 即可拿到 1 FULL report + 1 literature comparison + 推进 Done #1 0/3 → 1/3 + Done #2 0/3 → 1/3 · 起点最高 ROI。
