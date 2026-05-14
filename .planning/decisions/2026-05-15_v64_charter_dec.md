---
decision_id: DEC-V64-A-charter
title: V64-A Validation Maturity Arc · charter DEC · elevated from plan-file at user ratification 2026-05-15
status: Accepted
parent_dec: V63-A-close
phase: V64-A charter (Validation Maturity · ratified 2026-05-15)
notion_sync_status: synced 2026-05-15 (https://www.notion.so/360c68942bed810f8d44e3ec681755cb)
authored_by: Claude Code Opus 4.7 (1M context) · main session B52
authored_at: 2026-05-15
confidence: med
---

# DEC-V64-A-charter · V64-A Validation Maturity Arc

## Status

**Accepted 2026-05-15** — elevated from `.planning/2026-05-15_v64_charter.md` (renamed from `_draft` in B52 commit chain at user ratification).

V63-A close DEC `DEC-V63-A-close` (Accepted same B52 chain) records the 6/6 Done dim MET evidence + PARTIAL semantics user-ratification §3.1; this charter DEC anchors `parent_dec` for V64-A sub-DECs (M-V64A-VAL-CASE-016-FULL first candidate · cheapest unblock path · solver already converged 8.5e-8, only window extension needed).

V64-B (Frontend Activation) + V64-C (OSS Readiness + M6 Operationalization) move to Alternatives Appendix in plan-file (per B52 commit `docs(v64-plan)`).

## North Star (verbatim from plan-file V64-A §North Star)

> **把 V63-A 的 2/3 PARTIAL validation reports 真正推到 FULL · 实际跑 OpenFOAM solver 到收敛 · case_004 mesh gen v2 + NREL UAE Sequence S 实验对比 · case_006 substrate full e2e · case_011 用 non-degenerate substrate 重做 · ≥3 篇工业级 FULL validation reports 真实验证收敛 + 文献对比 + V-row attribution · 让 V62/V63 advisor stack 第一次"经实验数据验证过"而不只是"advisor 自审 PASS".**

> Plan-file references "2/3 PARTIAL" but V63-A actually landed 3/3 PARTIAL (case_011 + case_004 + case_016). V64-A scope expands to "3/3 PARTIAL → FULL" with the 3rd being case_016 window-extension + Heller-Bliss SPL. North Star intent unchanged: 3 FULL reports with real solver convergence + literature comparison.

## Done Definition (verbatim from plan-file V64-A · all 6 dims must hit)

| # | 维度 | 起点 (V63-A close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | FULL validation reports (real solver convergence + experimental/literature delta) | strict 0 / 3 FULL · PARTIAL-credit 3/3 (V63-A) | **≥ 3 FULL validation reports (solver 真实收敛 + experimental/literature delta < 文献声明 tolerance + V-row attribution)** | `ls .planning/validation_reports/v64_*_FULL.md \| wc -l` 且每篇含 (a) solver 收敛 residual plot (b) experimental/literature comparison delta table (c) V-row attribution |
| 2 | Numerical comparison vs canonical literature | 0 (V63-A 未做实验对比) | **≥ 3 canonical literature comparisons · 1 per FULL report (NREL UAE Sequence S / Heller-Bliss SPL / ONERA M6 shock-position / Sandia Flame D / 等)** | each FULL report §experimental comparison cites canonical reference + reports delta |
| 3 | Convergence stability test | implicit (V63-A 单跑) | **≥ 1 case 在 ≥2 mesh refinement levels (h/2 + h/4) 跑出 monotonic convergence trend** | mesh convergence study log in 1 FULL report |
| 4 | V63-A PARTIAL upgrade closure | 3 PARTIAL (case_011 + case_004 + case_016) | **≥ 2 / 3 PARTIAL upgraded to FULL OR explicitly re-classified with documented rationale** | sub-DEC chain `DEC-V64-A-sub-VAL-UPGRADE-*` |
| 5 | V63-A carry-over closure | 8 items deferred | **≥ 4 / 8 closed (#1 + #2 + ≥2 of {#3 / #4 / #6})** | each closed via sub-DEC with V-row + retro chain |
| 6 | V-row truth-capture rate (sub-DEC scope) | clause 1: ≥5/9 over-met 2/1 · clause 2: ≥3/9 on ≥3 cases 3/3 MET | **≥ 1 case 拿到 ≥7/9 · ≥2 cases 拿到 ≥5/9 · 不准 alias 灌水** | retro §V-row attribution counter |

**任一未达成 = V64-A 不 close**, 启动 root-cause retro。

> Note: Done #4 starting point updated from plan-file's "2 PARTIAL" to "3 PARTIAL" reflecting V63-A actual landing (3/3 PARTIAL). Done #4 threshold "≥ 2 / 3 PARTIAL upgraded" preserves plan-file conservative bar; over-met to 3/3 is target.

## 反命题 (anti-Done · failure modes · per plan-file)

- ❌ FULL report 跑 solver 但 residual oscillating / 不收敛 → 失败 (real convergence required)
- ❌ Literature comparison cherry-picks query point 使 delta 看上去小 → 失败 (须 canonical baseline · 1 standard experimental sequence)
- ❌ PARTIAL → FULL upgrade 通过"重写 PARTIAL semantics"绕过实际收敛 → 失败 (semantics revision must be user-ratified · not unilateral · per V63 close §3.1 governance precedent)
- ❌ Mesh convergence study 跑了但 trend 非 monotonic 仍标 PASS → 失败
- ❌ V-row alias 灌水 → 失败 (distinct signature required · per V62/V63 precedent)

## Cross-cutting code paths (V64-A predicted ≥ 3 → charter scope satisfied per v2.3)

V64-A predicts the following shared code-path touches:

1. **`case_*/inputs/*.yaml` + `*.json` (substrate v2)** — case_011 non-degenerate substrate replacement (M-V64A-CASE-011-NONDEGEN) · case_004 mesh gen v2 input manifest (M-V64A-MESH-GEN-V2) · case_006 substrate iteration 2 (M-V64A-CASE-006-SUBSTRATE-V2)
2. **`case_*/system/*` + `case_*/constant/*` (solver runtime)** — case_016 controlDict window extension (M-V64A-VAL-FULL-3 candidate) · case_011 substrate-driven fvSchemes/fvSolution tuning · case_004 solver execution post mesh-v2
3. **`.planning/validation_reports/v64_*_FULL.md` (new dir tier)** — 3 FULL reports (M-V64A-VAL-FULL-1/2/3) replacing/supplementing the 3 V63-A PARTIAL reports with real solver convergence + literature comparison + V-row attribution
4. **Experimental/literature comparison sources** — NREL UAE Sequence S (case_004) · Heller-Bliss cavity tone SPL data (case_016) · ONERA M6 shock-position OR Sandia Flame D experimental DB (case_009 or case_016) · access route TBD per milestone
5. **`.planning/methodology/industrial_case_solver_findings.md` (V-row corpus)** — V101+ extensions from V64-A solver-run findings · distinct-signature enforced
6. **Mesh refinement infrastructure (h/2 + h/4 study)** — scripted refinement workflow for ≥1 case (M-V64A-MESH-CONV-STUDY) · candidate case TBD per Tier 2

5+ paths confirmed → V64-A is **charter-scoped** by v2.3 §"DEC scope-driven" (≥3 共享代码路径). Charter DEC required and filed (this file).

## V63-A 资产复用清单 (sediment-driven reuse · per plan-file §6 V64-A row "V63-A 资产复用度 5/5")

V64-A is the "Validation Maturity" choice precisely because V63-A asset reuse is **maximally high** (per plan-file §6 4-dim comparison table V64-A 资产复用 = 5/5 vs V64-B 3/5, V64-C 4/5). Direct reuse manifest (no new framework / no new architectural primitive):

| V63-A + V62-A asset | V64-A reuse pattern |
|---|---|
| `advisor_stack.py` (~534 LOC · 11 LANDED advisors A1/A2-v2/A3/A4/A5/A7/A8/A10/D6/D10/D11) | **Direct reuse**. V64-A runs the existing stack against substrate-v2 cases unchanged · no assembly-layer modification · advisors fire on new substrate inputs same as V63-A |
| 4Q cross-feature audit framework (`test_4q_gate_stack_acceptance.py`) | **Direct reuse**. V64-A milestone PRs run the existing 4-test Q1-Q4 acceptance suite (LLM-offline gate · sha256 invariant · monkeypatch.delenv harness) plus inline 4Q gate in commit |
| `/api/ai-review` route (HTTP plumbing · M-D6-HTTP-WIRE 6-field schema) | **Direct reuse**. V64-A substrate v2 cases consumed via same HTTP boundary · no route extension required for V64-A scope (frontend wiring deferred to V64-B) |
| M-DRIFT-V2 (`v_series_drift_guard.py` 269 LOC · audit-mode default) | **Direct reuse**. V64-A V101+ new V-rows go through commit-time M-DRIFT v1 + route-time M-DRIFT v2 at `/api/ai-review` boundary |
| REQ-SCHEMA-EXPAND (6 wire-form fields after M-D6-HTTP-WIRE) | **Direct reuse**. V64-A substrate v2 cases use existing 6-field schema · backward compatibility preserved |
| V99-WIDEN (shm_dict_validator alias resolution) | **Direct reuse**. New substrate paths on `name:` alias inherit noise-pollution suppression for free |
| Track C dual-path methodology (HTTP TestClient + direct assemble_stack) | **Direct reuse**. V64-A FULL validation reports include Track C session as advisor cross-check · dual-path adoption + 4Q gate inline · env -i LLM-offline rerun |
| V-series corpus convention (V51+ → V100 · single-row-per-failure-mode · numerics-class tagging) | **Direct reuse + extension**. V101+ trajectory follows same distinct-signature pattern · NEW signatures only (per Done #6 anti-命题) |
| 3 case substrate (case_004 / case_006 / case_011 inputs/) | **Direct reuse + iteration**. case_006 substrate-v2 (M-V64A-CASE-006-SUBSTRATE-V2 · V-row 3/9 → 5/9 target) · case_011 substrate replacement (M-V64A-CASE-011-NONDEGEN · non-degenerate physics) · case_004 mesh-v2 ingest on existing input manifest |
| D11 stl_face_label_validator (single-case land · case_011 V94 regression green) | **Direct reuse + cross-validation**. M-V64A-D11-CROSS-VAL exercises D11 on case_018/019/020 · per A2 v1 / D6 / D10 precedent post-land discipline |
| D10 STANDARD_OPENFOAM_BCS catalog (138 BCs) | **Direct reuse · case-driven extension**. Only extend toward ~200 ESI BCs when V64-A case evidence demands false-unknown fix (case-driven not spec-audit-driven) |
| 3 PARTIAL validation reports (case_011 / case_004 / case_016) | **Reference + upgrade target**. V64-A FULL reports either supplement (additive solver convergence layer) or replace (substrate swap requires new report) the V63-A PARTIAL reports · V64-A is the "PARTIAL → FULL" arc |
| V-series corpus V100 | **Direct reuse · expansion to V101+**. V64-A solver-run findings yield new distinct signatures · distinct-signature enforcement unchanged |

**Reuse summary**: V63-A asset reuse is **≥ 95%** for V64-A scope (plan-file §6 4-dim assessment 5/5) · V64-A adds **0 new advisors / 0 new framework / 0 new architectural primitive** · the addition is solver-run + literature-comparison + mesh-convergence study + substrate-v2 iteration.

## V64-A milestones (per plan-file §3 Tier 状态板 V64-A)

### Tier 1 · 解锁性 (mesh gen + substrate prep · parallel · independent)

- **M-V64A-MESH-GEN-V2** case_004 NREL Phase VI MRF mesh gen v2 · 解锁 solver execution (V63-A carry-over #2 first half)
- **M-V64A-CASE-011-NONDEGEN** case_011 plate-fin HX non-degenerate substrate 替换 · OR PARTIAL semantics 用户裁决 rebadge (V63-A carry-over #1)
- **M-V64A-CASE-006-SUBSTRATE-V2** case_006 substrate iteration 2 · V-row 3/9 → 5/9 (V26-V28/V31/V32 + D4 中 ≥2 captured · V63-A carry-over #6)

### Tier 2 · solver run + experimental comparison

- **M-V64A-VAL-FULL-1** case_004 NREL Phase VI MRF FULL validation report · mesh v2 + solver convergence + NREL UAE Sequence S 实验对比 (≥3 wind speed points)
- **M-V64A-VAL-FULL-2** case_011 (or non-degenerate substitute) FULL validation report · solver convergence + plate-fin HX literature/handbook 对比
- **M-V64A-VAL-FULL-3** 3rd FULL report · **candidate (cheapest path)**: case_016 window extension + Heller-Bliss SPL comparison (per V63-A close §8 #3 mapping · solver already converged 8.5e-8 · only on-disk window extension needed) · alternative: case_009 Sandia Flame D vs Sandia experimental DB · or case_016 ONERA M6 shock-position
- **M-V64A-MESH-CONV-STUDY** mesh convergence study (h/2 + h/4) 在 ≥1 case 上 monotonic convergence trend

### Tier 3 · close

- **M-V64A-D11-CROSS-VAL** D11 cross-validation on case_018/019/020 (V63-A carry-over #4)
- **M-RADAR-V6-A** Capability radar v6 · validation maturity signals (FULL report count / literature delta / mesh convergence stability)
- **M-V65-A** V64-A close DEC + V65 charter draft

## Triggered redirect (命中 → 修改 plan · per plan-file V64-A §)

| 条件 | 动作 |
|---|---|
| case_011 substrate 永远 V93 degenerate · 无可换 non-degenerate substrate 路径 | 重新 classify PARTIAL semantics + 用户裁决 (per V63 close §3.1 precedent) |
| Mesh gen v2 (case_004) STEP 准备难度 ≥ 3 周 | 切到 case_009 Sandia Flame D / 其他 Tier 2 case 验证 |
| 商业 CAE AI 拿到工业 case validation 证据 ≥3 篇 ship | OSS 准备拉前 (切到 V64-C 或合并) |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决 (继续 / 接受 / 推 sub-DEC) |
| 实验数据 (NREL UAE / Heller-Bliss / ONERA M6 / Sandia Flame D) 访问受阻 ≥ 2 周 | 切到另一 case literature source / 降级 to handbook correlation |

## v2.3 governance compliance

- **DEC scope**: V64-A predicts 5+ shared code paths (per §Cross-cutting code paths) → **charter-level DEC required**. This file satisfies the requirement; first V64-A sub-DEC (M-V64A-VAL-CASE-016-FULL候选 in B53 per task brief) sets `parent_dec: V64-A-charter`.
- **Codex review** per V64-A milestone scope:
  - M-V64A-VAL-FULL-* (validation reports · docs only) → Codex skip default per v2.3 1-sync-trigger
  - M-V64A-MESH-GEN-V2 / M-V64A-CASE-*-NONDEGEN/V2 (case input files · no security boundary) → Codex skip default
  - M-V64A-MESH-CONV-STUDY (mesh refinement scripts · no security boundary) → Codex skip default
  - M-V64A-D11-CROSS-VAL (advisor cross-validation · existing source) → Codex skip default
  - **No V64-A milestone presently anticipated to touch routes/ or pages/** (frontend wiring deferred to V64-B) → V64-A may not invoke 1-sync-trigger at all in nominal path
- **Round cap = 3** per V133 unchanged. After R3 remaining P1 → user ratification; remaining P2/P3 → retro queue.
- **Kogami**: opt-in only per V133; user may invoke on charter / high-risk PR / post-incident retro per their judgment. No auto-trigger.
- **Notion sync**: session-end batch only · only Status=Accepted DECs sync per v2.3 round-1. This charter (Accepted) qualifies for session-end batch (V63 close + V64 charter both queued).
- **Spike-class**: V64-A may accept spike-class commits (≤30 LOC + 1 test + commit `confidence:<h/m/l>` · no DEC / Codex / Kogami / Notion) for surface scans / low-risk fixes (e.g., case window controlDict value tweak in M-V64A-VAL-FULL-3 candidate may qualify as spike if no schema change).
- **Counter**: V64-A starts a new arc-counter (autonomous_governance pure-telemetry per V133); V63-A counter +9 ledger preserved in V63-A close DEC §10.
- **PARTIAL semantics precedent (V63-A §3.1)**: V64-A inherits the precedent; PARTIAL → FULL upgrade path requires real solver convergence + literature comparison · semantics rebadge (PARTIAL credit) requires user ratification (cannot be unilateral).

## Inherited rules from V62-A + V63-A (sustained · per plan-file §8)

- LLM offline four-question gate (V130 thesis · 每个新功能 PR/DEC/UI 改动必答四问: LLM 离线可跑? artifacts 输出? TrustGate 解释? AI 仅 advisory?)
- advisor-not-driver: stack composes advisors but never executes mutations on case directories
- M-DRIFT v1 + V62 v2 (双 corpus drift-prevention hook) preserved
- session-end Notion sync (only Status=Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven (≥3 shared code paths / governance-rule-change → full charter; else sub-DEC 6-field minimum schema)
- Spike-class one-tier scope class (≤30 LOC + 1 test + commit `confidence:<h/m/l>` · 不调 DEC / Codex / Kogami / Notion)
- Codex 1-sync-trigger (auth / signing / security boundary) · round cap = 3
- Kogami opt-in (用户主动召唤 only)
- pre-implementation surface-scan (per DEC-V61-088) optional except new routes/ / pages/
- counter 纯遥测
- V-row distinct-signature enforcement (不准 alias 灌水)

## Asset re-anchoring (where SSOTs live in V64-A)

- **Plan SSOT**: `.planning/2026-05-15_v64_charter.md` (renamed from `_draft` in B52)
- **ARC-GOAL active**: `.planning/ARC-GOAL.md` (initialized fresh in B52)
- **ARC-GOAL V63-A frozen**: `.planning/ARC-GOAL-V63-A-CLOSED.md` (rename from prior `ARC-GOAL.md`)
- **Charter DEC**: this file (`DEC-V64-A-charter`)
- **Predecessor close**: `DEC-V63-A-close` (parent)
- **V63-A 3 PARTIAL reports**: `.planning/validation_reports/v63_case_011_v5b_validation_report.md` + `v63_case_004_nrel_phase_vi_validation_report.md` + `v63_case_016_m219_cavity_des_acoustic_validation_report.md` (referenced for FULL upgrade)
- **V64-A FULL reports (new tier)**: `.planning/validation_reports/v64_*_FULL.md` (3 to be filed)
- **V-series corpus**: `.planning/methodology/industrial_case_solver_findings.md` (V100 → V101+ extends in V64-A)

## confidence

**med**. High confidence on:
- V63-A asset reuse manifest (concrete file paths · concrete sub-DEC chain · concrete patterns demonstrated)
- 6 Done dimensions are operationally measurable (FULL report count · literature delta · mesh convergence trend · PARTIAL upgrade count · carry-over closure · V-row attribution)
- Carry-over absorption boundary (6 V64-A · 2 deferred · clean mapping per V63 close §8)
- PARTIAL semantics precedent operationally inherited (V63 close §3.1 verbatim)

Medium confidence on:
- **Solver convergence outcomes**. case_011 non-degenerate substrate selection is a substrate-discovery problem (no guarantee the replacement substrate exists in catalogue · may require new STEP ingest). case_004 mesh gen v2 has known difficulty (V63-A M-VAL-REPORT-2 PARTIAL evidence). case_016 window extension is lowest-risk (solver already converged 8.5e-8 · mechanical extension).
- **Experimental data access**. NREL UAE Sequence S (case_004) · Heller-Bliss SPL (case_016) · ONERA M6 shock (alternative) · Sandia Flame D (case_009 if substituted) — each canonical reference has different access route (public dataset vs literature digitization vs handbook correlation). Plan-file §3 redirect condition acknowledges this gating.
- **Mesh convergence study** (M-V64A-MESH-CONV-STUDY) on ≥1 case is plausible but yield-uncertain — monotonic convergence trend over h/2 + h/4 may require case selection care (e.g., case_009 reacting-low-Mach is known to have multi-scale convergence challenges).
- **PARTIAL → FULL conversion rate**. V63-A converted 0/3 PARTIAL to FULL within its arc (V63-A landed PARTIAL directly · upgrade to FULL is V64-A scope). V64-A aims for 2/3 minimum · 3/3 over-met target. Plan-file flags case_011 substrate replacement as highest-risk; case_016 window extension as lowest-risk.

These medium-confidence dimensions are scoped to forward-looking V64-A execution; charter itself (scope · Done def · governance fit · asset reuse · carry-over absorption · PARTIAL precedent inheritance) is data-grounded and inherits V63 close §3.1 verbatim ratification.

---

**End of V64-A charter DEC.** V64-A arc anchored. First sub-DEC candidate: M-V64A-VAL-CASE-016-FULL (B53 · cheapest unblock per task brief · solver already converged 8.5e-8 · window extension + Heller-Bliss SPL). ARC-GOAL.md V64-A active arc skeleton initialized in same B52 commit chain. Notion sync pending session-end batch.
