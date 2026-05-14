# ARC-GOAL · V63-A Industrial Scale-Up Arc

**Plan SSOT**: [.planning/2026-05-14_v63_charter.md](2026-05-14_v63_charter.md)
**Charter DEC**: [.planning/decisions/2026-05-14_v63_charter_dec.md](decisions/2026-05-14_v63_charter_dec.md) (DEC-V63-A-charter Accepted 2026-05-14)
**Predecessor**: [V62-A advisor stack closure arc · CLOSED 2026-05-14](ARC-GOAL-V62-A-CLOSED.md) (6/6 Done dims MET ✓ · `DEC-V62-A-close` Accepted)
**Started**: 2026-05-14 (same B38 commit chain as V62-A close)
**Mode**: milestone-driven (no calendar)
**Selected**: V63-A "Industrial Scale-Up" · user-ratified 2026-05-14 from 3 candidates (V63-B + V63-C → Alternatives Appendix in plan-file)

> 读这个文件 90 秒能回答：「这个 arc 完了没？」「该不该开新 arc？」「下个 session 接什么？」

---

## North Star（一句话）

> **让 advisor stack 在 ≥5 个独立工业 case 上以 100% adoption 跑通 · V-series corpus 扩张到 V100+ · 收齐 V62-A surfaced deferred items (D11 / D6 HTTP / D10 catalog / case substrate 扩展) · 产出 ≥3 篇工业级 e2e validation report.**

---

## Done Definition（必须全部命中）

| # | 维度 | 起点 (V62 close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Distinct numerics class · 100% adoption | 3 classes (steady-laminar-CHT-multi-stream / compressible-DES-acoustic / compressible_shock_density_based) | **≥ 5 classes 100% adoption PASS** | `grep -E "100% adoption" .planning/retrospectives/*stack_track_c*.md \| sort -u` |
| 2 | V-series corpus size | V51+ (824 LOC in methodology) | **≥ V100 distinct V-rows landed** | `grep -cE "^### V[0-9]+ ·" .planning/methodology/industrial_case_solver_findings.md` |
| 3 | D-class advisor LANDED | 2 (D6 + D10) | **≥ 3 LANDED (D11 candidate)** | `grep -E "D-class.*LANDED" .planning/cross_cuts/advisor_coverage_*.md` |
| 4 | Industrial e2e validation report | 0 (Track C retros are session-shape · not full prep→solve→postp) | **≥ 3 cases with full report (prep → solver → postp · convergence + comparison + V-row attribution)** | `ls .planning/validation_reports/v63_*.md \| wc -l` |
| 5 | V62-A carry-over closure | 6 items deferred | **≥ 4 / 6 items closed (D11 + D6 HTTP + D10 catalog scope + case substrate)** | each closed via sub-DEC with V-row + retro chain |
| 6 | V-row truth-capture rate (canonical case) | 1/9 (case_006 post TRACK-3-rerun) | **≥ 5/9 on ≥1 canonical case · ≥ 3/9 on ≥3 cases** | retro §V-row attribution counter |

**任一未达成 = V63-A 不 close**，启动 root-cause retro。

---

## Done 条件**不算** Done 的反命题（防 scale-shipped-but-not-real）

- ❌ 5 cases all on same numerics class → 失败 (违反 dim #1 "distinct" 要求)
- ❌ V-row count 100 但是 alias / 重复 pattern 灌水 → 失败 (违反 dim #2 spirit, 须 distinct failure-mode signature)
- ❌ D11 LANDED 但无 case 触发 V94 face-label loss → 孤儿 advisor (per V62-A 反命题 template)
- ❌ Validation report 复用 case_011 / case_016 / case_006 V62-A 已覆盖证据 → 失败 (无 net-new evidence)

---

## 触发性 redirect 条件（命中 → 修改 plan，不算 Done）

| 条件 | 动作 |
|---|---|
| 商业 CAE AI GA 拿到 ≥3 工业 case ship 证据 (Siemens / ANSYS GenAI) | OSS 准备拉前 · V63 部分 milestone defer |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| 用户工作焦点偏离 ≥1 周 (frontend / OSS pull) | 每 Tier 末 review redirect (V63-B 待启或 fold blueprint v3) |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决（继续 / 接受 / 推 sub-DEC） |
| 工业 case STEP 准备难度阻塞 ≥ 2 周 | 切到 carry-over P3/P4 优先级 / catalog 工作 |

---

## Tier 状态板（每 milestone 完成时打勾 + 填 commit hash）

### Tier 1 · 解锁性（V62-A carry-over items · parallel · independent）

- [x] **M-D11-DRAFT** stl_face_label_validator advisor LANDED · V94 face-label-loss class · 3 detection paths (orphan / duplicate / missing-ref) · commit: `57944fe` (feat) → `fa34c3c` (11 advisor tests · 4Q gate inline · case_011 V94 regression) · sub-DEC `DEC-V63-A-sub-D11` Accepted (2026-05-14 · stl_face_label_validator.py 21 KB · evidence_v_rows=(V94,) · single-case land per A2 v1 / D6 / D10 precedent · stack registration in advisor_stack.py line 183 + dispatch line 741-758 · ai_review.py stl_face_normals wire field at line 209 + auto-discover at line 736 · 74/74 tests green = 11 D11 advisor + 4 D11 stack-dispatch + 2 D11 route-wire + 26 stack regression + 31 ai_review regression · case_011 v1 V94 3-row replay green · V62-A TRACK-1 §8 enhancement #3 CLOSE-VALIDATED ✓ · carry-over #1 closed · LANDED counter 10 → 11 · D-class literal 2/3 ✓ → 3/3 ✓ MET on V63-A Done dim #3 · 4Q gate inline PASS · confidence: med · pre-merge Codex skipped per v2.3 1-sync-trigger no security boundary)
- [x] **M-D6-HTTP-WIRE** D6 extra_body_advisor HTTP route plumb · closes REQ-SCHEMA-EXPAND stl_bbox_set scope-out · commit: `_____` (B40 chain · 4 commits feat + feat + test + docs · sub-DEC `DEC-V63-A-sub-M-D6-HTTP-WIRE` Accepted (2026-05-14 · `routes/ai_review.py` stl_bbox_set wire field at line 223 + auto-discover from `<case_dir>/cad/stl_bbox_set.json` OR `<case_dir>/manifest.json` field at lines 760-781 · `services/advisor_stack.py` D6 dispatch routing rule at lines 866-895 + V55 in `_V_ROWS_PER_ADVISOR` at line 180 + `_normalize_extra_body` at line 393 + `extra_body_advisor` module load at line 165 · 71/71 tests green = 3 D6 stack + 5 D6 route + 26 stack regression + 33 ai_review regression + 4 parametrize fan-out · V62-A REQ-SCHEMA-EXPAND §"this sub-DEC does NOT add" item 1 CLOSED ✓ · V63-A carry-over #4 closed · routes/ai_review.py 1-sync-trigger Codex pre-merge MANDATORY per v2.3 · confidence: med · 4Q gate inline PASS · Codex review pending B40 final)
- [x] **M-D10-CATALOG-AUDIT** STANDARD_OPENFOAM_BCS catalog 80 → 138 BCs (≥100 floor cleared with +38 LOC headroom) · case-driven extension (3 LANDED cases case_006/011/016 · all 25 distinct BCs already recognized · 0/25 unrecognized) + ESI v2412 mainline canonical closure (58 new entries: wall velocity / LES inlets / radiation / multiphase contact-angle / prgh-pressure / atm wallFunctions / compressible::ns mirrors / cyclic extensions) · disjoint invariant retained (STANDARD ∩ FOAM_EXTEND_ONLY = ∅ · STANDARD ∩ SENTINEL = ∅) · 19/19 D10 tests (13 old + 6 new V63-A) · 67/67 D10+adjacent advisors PASS · sub-DEC `DEC-V63-A-sub-M-D10-CATALOG-AUDIT` Accepted (B41 · 2026-05-14 · `bc_type_name_validity_advisor.py` STANDARD_OPENFOAM_BCS expanded + module docstring V63-A audit note · `test_bc_type_name_validity_advisor.py` 6 V63-A tests · `routes/ai_review.py` untouched (parallel-safe with B40) · `services/advisor_stack.py` untouched · catalog policy append-only · zero logic mutation · zero security boundary · Codex skip per v2.3 1-sync-trigger · 4Q gate inline PASS · confidence: med · V63-A carry-over #2 closed) · commit: `_____` (B41)

### Tier 2 · case 扩张

- [ ] **M-CASE-EXT-1** 4th distinct numerics class case (candidate: incompressible-LES-multi-fan / two-phase-VOF / heat-transfer-conjugate-radiation) · commit: `_____`
- [ ] **M-CASE-EXT-2** 5th distinct numerics class case · commit: `_____`
- [ ] **M-V100-LANDING** V-series corpus expansion from V51+ to V100 · ≥ 49 net-new distinct V-rows · TRUE NEW signatures (not aliased duplicates) · commit: `_____`
- [ ] **M-CASE-006-SUBSTRATE** case_006 input-manifest extension (thin_wall_inputs.yaml + interface_bodies.json + interface_specs.json) · V-row capture 1/9 → 3/9 · commit: `_____`

### Tier 3 · validation reports + close

- [ ] **M-VAL-REPORT-1** Industrial e2e validation report 1 (full prep→solver→postp · convergence + comparison + V-row attribution) · commit: `_____`
- [ ] **M-VAL-REPORT-2** Validation report 2 · commit: `_____`
- [ ] **M-VAL-REPORT-3** Validation report 3 · commit: `_____`
- [ ] **M-RADAR-V5** Capability radar v5 · scale-up signals (case count / V-row count / e2e report count) · commit: `_____`
- [ ] **M-V64** V63-A close DEC + V64 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 distinct numerics class 100% adoption PASS:  3 / 5     (V62-A 起点 · 待 M-CASE-EXT-{1,2} 扩张)
当前 V-series corpus size:                        V51+ / V100   (V62-A 起点 · 待 M-V100-LANDING)
当前 D-class advisor LANDED:                      **3 / 3 ✓ MET**   (D6 + D10 V62-A + D11 B39 · Done dim #3 MET ✓)
当前 Industrial e2e validation report:            0 / 3     (V62-A Track C 为 session-shape · 待 M-VAL-REPORT-{1,2,3})
当前 V62-A carry-over closure:                    **3 / ≥4**   (item #1 D11 stl_face_label_validator B39 closed ✓ · item #2 D10 STANDARD_OPENFOAM_BCS catalog 80→138 B41 closed ✓ · item #4 D6 HTTP wire-up B40 closed ✓ · 仍 3 items pending: case substrate / frontend wiring / ai_diagnose drift)
当前 V-row truth-capture rate (canonical):        1 / 9 on case_006 (V62-A TRACK-3-rerun 起点 · 待扩到 ≥5/9 + ≥3/9 on ≥3 cases)
当前 Done dims MET:                               **1 / 6**   (Done dim #3 D-class 3/3 MET ✓ via B39 D11 land)
```

最后更新时间：`2026-05-14 (V63-A arc 初始化 · ARC-GOAL.md fresh skeleton from V62-A close · 6 Done dims set per V63-A charter DEC · DEC-V63-A-charter Accepted · plan-file ratified 2026-05-14 · V62-A ARC-GOAL frozen at ARC-GOAL-V62-A-CLOSED.md · V63-A Tier 1 dispatch unblocked · M-D11-DRAFT B39 candidate per task brief · ARC-GOAL 协议: B38/B39 双方都改 ARC-GOAL 需手动合并 · 更新人：Claude Code Opus 4.7 session main · B38 V62→V63 governance transition) · B40 update: M-D6-HTTP-WIRE [x] LANDED · sub-DEC DEC-V63-A-sub-M-D6-HTTP-WIRE Accepted (2026-05-14 · 71/71 tests green · V62-A REQ-SCHEMA-EXPAND §"does NOT add" item 1 closed · carry-over closure 1/≥4 → 2/≥4 · routes/ai_review.py 1-sync-trigger Codex pre-merge MANDATORY per v2.3 · pending Codex APPROVE before push) · B41 update: M-D10-CATALOG-AUDIT [x] LANDED · sub-DEC DEC-V63-A-sub-M-D10-CATALOG-AUDIT Accepted (2026-05-14 · STANDARD_OPENFOAM_BCS 80→138 BCs · 19/19 D10 tests + 67/67 D10+adjacent tests green · 3 LANDED case BC sets all 0/N unrecognized pre+post · disjoint invariant retained · catalog policy append-only · carry-over closure 2/≥4 → 3/≥4 · catalog-data-extension · zero logic mutation · zero security boundary · Codex skip per v2.3 1-sync-trigger · confidence: med · B40+B41 ARC-GOAL concat-merged manually per 双方都改协议)`

---

## 关键依赖图

```
M-D11-DRAFT       ─┐
M-D6-HTTP-WIRE    ─┤  Tier 1 (parallel · independent)
M-D10-CATALOG     ─┘
       │
       ↓
M-CASE-EXT-1 ──→ M-CASE-EXT-2 ─┐
                                ├──→ M-V100-LANDING ──→ M-VAL-REPORT-{1,2,3}
M-CASE-006-SUBSTRATE  ────────→ ┘                            │
                                                              ↓
                                                       M-RADAR-V5 ──→ M-V64
```

Tier 1 milestones are parallel-safe (independent code paths · independent advisors). Tier 2 case extension blocks Tier 3 validation reports (validation report requires LANDED case substrate). M-CASE-006-SUBSTRATE is parallel-safe with M-CASE-EXT-{1,2} (different case dirs).

---

## V62-A 资产复用清单（per V63-A charter DEC §"V62-A 资产复用清单"）

V63-A is the "Industrial Scale-Up" choice precisely because V62-A asset
reuse is ≥ 90%. Direct reuse manifest (no new framework / no new
architectural primitive):

- `advisor_stack.py` ~534 LOC dispatch + composition (D11 adds to dispatch table same pattern as D10)
- 10 LANDED advisors (A1/A2-v2/A3/A4/A5/A7/A8/A10/D6/D10) fire unchanged across new cases
- `/api/ai-review` route (M-D6-HTTP-WIRE extends with stl_bbox_set field · same auto-discovery pattern as REQ-SCHEMA-EXPAND)
- 4Q cross-feature audit framework (`test_4q_gate_stack_acceptance.py` reused for each V63-A milestone)
- M-DRIFT-V2 audit-mode default at `/api/ai-review` boundary (new V-rows go through commit-time M-DRIFT v1 + route-time v2)
- REQ-SCHEMA-EXPAND 5 wire-form fields + auto-discovery + rehydration (extended to 6 with stl_bbox_set)
- V99-WIDEN shm_dict alias resolution (new cases on `name:` alias paths inherit noise-pollution suppression)
- Track C dual-path methodology (HTTP TestClient + direct assemble_stack · adoption %% · 4Q gate inline · env -i LLM-offline rerun)
- V-series corpus convention (single-row-per-failure-mode · numerics-class tagging · NEW signatures only per anti-命题)

---

## 沿用 V62-A 不变规则

- LLM offline 四问门控 (V130 thesis)
- advisor 不是 driver · 只 advise · engineer (or Claude Code session) 最终决策
- 双 corpus drift-prevention hook (M-DRIFT v1 + V62 v2) 保留
- session-end Notion sync (仅 Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven: ≥3 共享代码路径 / governance-rule-change → charter
- Codex 1-sync-trigger (auth/signing/security boundary · 路由扩展 命中) · ≥3 round cap
- Kogami opt-in (用户主动召唤 only)
- Spike-class 一等 scope class (≤30 LOC + 1 test + commit `confidence: <h/m/l>`)
- pre-implementation surface-scan (per DEC-V61-088) optional except new routes/ / pages/
- counter 纯遥测

---

## v2.3 governance 合规（V63-A scope）

- V63-A 跨 ≥3 共享代码路径 (D11 advisor + ai_review route extension + V-series corpus + case substrate + validation reports) → **charter-level DEC** Accepted via `DEC-V63-A-charter`
- Codex review per-milestone:
  - M-D6-HTTP-WIRE (route extension) → **Codex pre-merge 必走** (1-sync-trigger 命中)
  - 其他 Tier 1/2/3 milestones → Codex skip default (no security boundary)
- Kogami opt-in (用户主动召唤)
- counter 纯遥测 (V63-A 重启 autonomous_governance counter · V62-A counter +11 ledger preserved in V62-A close DEC §10)

---

## 下一步建议（每次会话末由 main session 写）

> **2026-05-14 V62-A CLOSE + V63-A charter Accepted** · V63-A North Star ratified · plan-file `2026-05-14_v63_charter.md` (renamed from `_draft`) + charter DEC `2026-05-14_v63_charter_dec.md`.
>
> **下一会话候选**：
> 1. **M-D11-DRAFT** (Tier 1 · cheapest path · D-class literal 2 → 3 unblock · B39 candidate per task brief)
> 2. **M-D6-HTTP-WIRE** (parallel-safe · routes/ai_review.py extension · Codex pre-merge required)
> 3. **M-D10-CATALOG-AUDIT** (case-driven · low urgency · trigger when first false-unknown surfaces)
>
> **推荐**：**M-D11-DRAFT** — single-case land precedent established by A2 v1/D6/D10 · cheapest unblock path · sets V63-A first-sub-DEC chain.
