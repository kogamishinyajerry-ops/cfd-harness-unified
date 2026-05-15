# ARC-GOAL · V65-A Industrial Coverage Deepening Arc · **ACTIVE 2026-05-15**

> **V65-A ACTIVE 2026-05-15 · 0/6 Done dims · Charter DEC `decisions/2026-05-15_v65_charter_dec.md` Accepted · Successor: TBD (V66 themes deferred to V65-A close)**

**Plan SSOT**: this charter is "lean charter" (no separate plan-file `_draft.md`) · Done dims + Tier seeds inherited directly from charter DEC body
**Charter DEC**: [.planning/decisions/2026-05-15_v65_charter_dec.md](decisions/2026-05-15_v65_charter_dec.md) (DEC-V65-A-charter Accepted 2026-05-15)
**Predecessor**: [V64-A Validation Maturity · CLOSED 2026-05-15](ARC-GOAL-V64-A-CLOSED.md) (6/6 Done dims MET ✓ · `DEC-V64-A-close` Accepted · Done #1 via §3.1 MARGINAL ratify · Done #4 via §3.2 multi-case rebadge ratify)
**Started**: 2026-05-15 (B72 commit chain · same-day cadence with V64-A close B71 · sustains V63→V64 same-day pattern)
**Mode**: milestone-driven (no calendar)
**Selected**: V65-A "Industrial Coverage Deepening" · user-ratified 2026-05-15 from 4 candidate themes seeded in V64-A close DEC §9.1 (V65-B AI Advisor Stack Build-out + V65-C Product M1-M6 Roadmap Continuation + V65-D Canonical Coverage Closure remain un-selected · natural homes for un-absorbed V63-A carry-over #7/#8 frontend wiring deferred V66-or-later)

> 读这个文件 90 秒能回答：「这个 arc 完了没？」「该不该开新 arc？」「下个 session 接什么？」

---

## North Star（一句话）

> **把 V64-A 留下的 5 个 carry-over 真升级到 evidence-firm · case_004 rotor LE/TE F-NEW-3.1 fix 跑通 + case_006 ONERA M6 thermo-FPE Layer 3 收敛 + case_016 m219 cavity 3-axis 解 + ≥2 net-new 工业 case e2e（候选: APU bay 通风 / NACA 高 AoA 失速 / Sandia Flame D / 2nd TBL 不同 Re）· V101..V106 6 candidates 至少 4 个 LANDED 进 V-series corpus · 让 V64-A 1D analytical strict-FULL 的方法论真正落到 industrial-grade 工程报告而不只是停留在教科书 1D 公式对比。**

> V65-A is the **industrial-grade companion** to V64-A's 1D analytical strict-FULL trio. V64-A demonstrated stack against canonical analytical solutions (Schlichting machine-precision) + accumulated honest engineering evidence on V63-A PARTIAL cases. V65-A converts that into evidence-firm industrial reports — F-NEW-3.1 rotor fix + thermo Layer 3 + ≥2 net-new industrial cases + 4+/6 V101+ canonical-formalization.

---

## Done Definition（必须全部命中）

| # | 维度 | 起点 (V64-A close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | V64-A carry-over absorption | 5 items deferred (V64-A close §8) | **5 / 5 全部 LANDED 或重分类** | each closed via V65-A sub-DEC with V-row + retro chain · 5-item mapping in Tier 1/2 below |
| 2 | V101+ promotion 进 V-series corpus | V100 (V64-A close · 6 candidates §7.2 staged) | **≥ 4 / 6 candidates LANDED V101..V106** | `grep -cE "^### V10[1-6] ·" .planning/methodology/industrial_case_solver_findings.md ≥ 4` · per-row distinct-signature + ≥2-case witness OR canonical reference attribution |
| 3 | Net-new 工业 case e2e | 0 net-new V65-A industrial cases | **≥ 2 篇 industrial FULL or strong-PARTIAL** | candidate set: APU bay 通风 / NACA 高 AoA 失速 / Sandia Flame D / 2nd TBL 不同 Re · 每篇含 solver 收敛 + geometry/physics complexity ≥ V63-A baseline + V-row attribution |
| 4 | Industrial-grade FULL reports | V64-A 3 strict-FULL 1D analytical (Poiseuille / Couette / Pipe) **NOT counted** | **≥ 3 篇带 experimental/literature comparison + V-row attribution** · 工业级 (not 1D analytical教科书) | `ls .planning/validation_reports/v65_*_FULL.md \| wc -l ≥ 3` · 每篇含 solver 收敛 + experimental/literature delta table + V-row attribution + geometry/physics 复杂度 ≥ V63-A 工业 case baseline |
| 5 | Canonical-artifact ledger formalization | V64-A V105 candidate (wedge-axis 1 instance) + V106 candidate (limitTemperature 1 application) | **wedge-axis 2nd witness LANDED + thermo-FPE template 2nd application LANDED** | V105 + V106 each via dedicated sub-DEC + V-row promotion (LANDED) |
| 6 | V-row truth-capture rate (sub-DEC scope) | V64-A: clause-1 over-met 2/1 · clause-2 over-met 3/2 | **clause-1 ≥1 case ≥7/9 (carry-forward OR new) · clause-2 ≥2 cases ≥5/9 · 不准 alias 灌水** | retro §V-row attribution counter · distinct-signature enforced per V62/V63/V64 precedent |

**任一未达成 = V65-A 不 close**, 启动 root-cause retro per V64-A close §3 PARTIAL semantics precedent (§3.1 MARGINAL extension + §3.2 multi-case rebadge available as ratification paths if applicable).

> Note: Done #4 explicitly excludes V64-A 1D analytical strict-FULL trio (Poiseuille / Couette / Hagen-Poiseuille). V65-A's industrial-grade bar requires solver + geometry complexity beyond textbook 1D analytical canonical. 1D analytical reports may still appear in V65-A scope (e.g., V105 wedge-axis 2nd witness on a 1D-equiv axisymmetric case) but do NOT count toward Done #4.

---

## Done 条件**不算** Done 的反命题（防 paper-validation · per V64-A precedent）

- ❌ Industrial FULL report 跑 solver 但 residual oscillating / 不收敛 → 失败 (real convergence required)
- ❌ Literature comparison cherry-picks query point 使 delta 看上去小 → 失败 (canonical baseline required)
- ❌ Industrial-grade FULL via 1D analytical disguise → 失败 (Done #4 industrial complexity required)
- ❌ V101+ promotion via alias inflation (renamed V51+ rows) → 失败 (distinct-signature required)
- ❌ Carry-over closure via "rebadge without engineering evidence body" → 失败 (V63 §3.1 + V64 §3.2 precedents require ≥1 sub-DEC honest evidence per case)
- ❌ V101+ promotion without ≥2-case witness OR canonical reference attribution → 失败 (V101+ criterion stricter than V51-V100 baseline)
- ❌ Net-new industrial case skipping advisor stack run pre-flag → 失败 (V64-A §3.2 precedent: case-side limit must be advisor-pre-flagged)

---

## 触发性 redirect 条件（命中 → 修改 plan，不算 Done）

| 条件 | 动作 |
|---|---|
| case_004 F-NEW-3.1 LE/TE fix attempt ≥ 3 周 无 \|M_x\| sign correction | 切到 substitute rotor case OR mark V102 QUESTIONABLE perpetual |
| APU bay 工业 case e2e 卡 ≥ 3 周（STL clean / sHM / STAR-CCM+ via CodeBuddy 任一）| 切到 NACA stall 或 Sandia Flame D 作为 net-new industrial primary · 不死等 APU bay |
| 任一 V101+ promotion 不满足 distinct-signature OR ≥2-case witness OR canonical reference | mark candidate QUESTIONABLE · 不灌水 · 等 V66+ |
| Industrial FULL report 试图通过 1D analytical 路径绕过 Done #4 | 失败 per §"反命题" #3 · 切到真工业 case 路径 |
| 商业 CAE AI 拿到工业 case validation 证据 ≥3 篇 ship | OSS 准备拉前 (切到 V65-C 候选合并 OR V66+) |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决 (继续 / 接受 / 推 sub-DEC · per V133) |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| 实验数据访问受阻 ≥ 2 周 | 切到 handbook correlation OR alternative literature source |
| §3.1 MARGINAL ratify 路径 滥用（primary-physics-component residual artifact 试图标 MARGINAL）| 失败 per V64-A §3.1 governance precedent · §3.1 only applies to canonical-OpenFOAM-geometry-artifact on non-primary-physics-component |
| §3.2 multi-case rebadge 滥用（无 ≥1 sub-DEC honest engineering evidence body 即 rebadge） | 失败 per V64-A §3.2 governance precedent · §3.2 requires within-arc precedent + per-case sub-DEC body |

---

## Tier 状态板（每 milestone 完成时打勾 + 填 commit hash · V64-A carry-over absorption mapped per item）

### Tier 1 · 解锁性 (V64-A carry-over absorption + V101 highest-confidence promote · parallel · independent)

- [ ] **M-V65A-V101-PROMOTE** — V101 case_004 F-NEW-3 `section_wire()` chord-axis convention bug → V-series V101 row promotion · V64-A B57+B63 EMPIRICALLY CONFIRMED |M_x| 37× shift · distinct-signature criterion met · primary V101 landing · single-row promotion · highest-confidence Tier 1 milestone · **commit: `_____`**
- [ ] **M-V65A-CASE-004-LE-TE-FIX** — case_004 NREL Phase VI F-NEW-3.1 LE/TE orientation fix attempt · `scripts/build_cad.py::section_wire()` v2 LE/TE tangential repair · re-tessellate STL · re-run simpleFoam + Cp/Ct + Δ vs NREL UAE Seq S · **V64-A carry-over #1 absorption** · primary V102 promotion source · **commit: `_____`**
- [ ] **M-V65A-CASE-006-THERMO-LAYER3** — case_006 ONERA M6 thermo-FPE Layer 3 fix · sutherland restore + limitTemperature [110, 2000]K + URF v4 + PIMPLE p-coupling stability + rhoCentralFoam OR rhoPimpleFoam variant · **V64-A carry-over #5 partial absorption** · primary V106 promotion source (1st of 2-case template) · **commit: `_____`**
- [ ] **M-V65A-CASE-016-3AXIS** — case_016 m219 cavity DES-acoustic 3-axis fix · combined thermo stability + PIMPLE p-coupling + controlDict window extension · **V64-A carry-over #5 partial absorption** · 2nd witness paired with M-V65A-CASE-006-THERMO-LAYER3 for V106 template confirmation · **commit: `_____`**

### Tier 2 · solver run + experimental comparison + V101+ promotion + net-new industrial cases

- [ ] **M-V65A-CASE-APU-BAY** — APU bay 通风 net-new industrial case e2e · leverages `~/Desktop/apu-bay-ventilation-cht/` 503 MB FreeCAD-cleaned STL + sHM 89,745 cells validated baseline + STAR-CCM+ via CodeBuddy delivery precedent · simpleFoam (or chtMultiRegionFoam) + advisor stack run + V-row attribution · primary net-new industrial Done #3 contribution · **commit: `_____`**
- [ ] **M-V65A-CASE-NACA-STALL** — NACA airfoil 高 AoA 失速 net-new industrial case · separation-class 2nd witness for F-NEW-15 inlet BL thickness mismatch · **V64-A carry-over #2 absorption** · V104 promotion path · NACA 0012 or NACA 4412 at ≥12° AoA · kOmegaSST RANS + advisor stack + experimental comparison · 2nd net-new industrial Done #3 contribution · **commit: `_____`**
- [ ] **M-V65A-CASE-SANDIA-FLAME-D** *(candidate · alternate)* — Sandia Flame D reacting-low-Mach net-new industrial case · canonical TNF reference · reactingFoam + flamelet OR EDC + Sandia experimental DB comparison · V106 thermo-FPE template 2nd application candidate (combustion thermo-FPE distinct-signature) · **commit: `_____`**
- [ ] **M-V65A-CASE-TBL-2ND-RE** — 2nd TBL case at different Re vs case_021 NASA TMR · disambiguates F-NEW-C Cf-canonical-choice + F-NEW-low-Re transition trigger · **V64-A carry-over #3 absorption** · V103 promotion source · **commit: `_____`**
- [ ] **M-V65A-V102-PROMOTE** — V102 case_004 F-NEW-3.1 LE/TE tangential orientation root cause (post M-V65A-CASE-004-LE-TE-FIX) · V102 lands only if M-V65A-CASE-004-LE-TE-FIX produces sign correction + Cp within FULL band OR else stays QUESTIONABLE · **commit: `_____`**
- [ ] **M-V65A-V103-PROMOTE** — V103 split (Cf-canonical-choice + low-Re-transition · 2 rows possible) post M-V65A-CASE-TBL-2ND-RE · distinct-signature criterion · **commit: `_____`**
- [ ] **M-V65A-V104-PROMOTE** — V104 case_022 BFS inlet BL thickness mismatch · separation 2nd witness via M-V65A-CASE-NACA-STALL · distinct-signature met if NACA stall surfaces consistent inlet-BC sensitivity · **commit: `_____`**
- [ ] **M-V65A-V105-WEDGE-AXIS-2ND** — V105 wedge-axis residual plateau canonical OpenFOAM artifact 2nd witness · candidate: axisymmetric jet (round jet centerline) OR pipe at higher Re (case_027 was lower Re · Re_τ ≥ 1000 candidate) · **V64-A carry-over #4 absorption** · §3.1 MARGINAL → FULL precedent applicable if 2nd witness reproduces canonical artifact pattern · Done #5 first half · **commit: `_____`**
- [ ] **M-V65A-V106-THERMO-TEMPLATE-2ND** — V106 limitTemperature substrate fix template 2nd application · paired with M-V65A-CASE-006-THERMO-LAYER3 (1st re-application post V64-A B61) + Sandia Flame D OR case_016 3-axis (2-case template confirmation) · **V64-A carry-over #5 absorption** · Done #5 second half · **commit: `_____`**
- [ ] **M-V65A-VAL-FULL-1** — 1st V65-A industrial-grade FULL validation report · candidate base case: M-V65A-CASE-APU-BAY OR M-V65A-CASE-NACA-STALL · solver convergence + experimental delta < literature tolerance + V-row attribution · **commit: `_____`**
- [ ] **M-V65A-VAL-FULL-2** — 2nd V65-A industrial-grade FULL validation report · **commit: `_____`**
- [ ] **M-V65A-VAL-FULL-3** — 3rd V65-A industrial-grade FULL validation report · **commit: `_____`**

### Tier 3 · close

- [ ] **M-V65A-V63A-CARRY-FRONTEND** *(optional · default deferred)* — V63-A carry-over #7 frontend wiring `/api/ai-review` + `/api/ai-diagnose` (may surface if V65-A industrial case demands UI; default V66-or-later) · **commit: `_____`**
- [ ] **M-RADAR-V7-A** Capability radar v7 · industrial coverage deepening signals (FULL report count industrial-grade · V101+ promotion count · canonical-artifact ledger 2nd witness count · carry-over absorption count) · **commit: `_____`**
- [ ] **M-V66-A** V65-A close DEC + V66 charter draft (per V63 → V64 → V65 succession precedent · V66 themes seeded from V65-A close §9 placeholder) · **commit: `_____`**

---

## V64-A carry-over absorption mapping (Done #1 explicit · per V64-A close §8)

| V64-A item | V64-A source sub-DEC | V65-A absorbing milestone | Status |
|---|---|---|---|
| #1 F-NEW-3.1 case_004 LE/TE orientation fix attempt | B63 `DEC-V64-A-sub-M-V64A-CASE-004-BLADE-CAD-FIX` §F-NEW-3.1 | M-V65A-CASE-004-LE-TE-FIX (Tier 1) | pending |
| #2 F-NEW-15 inlet-BC sensitivity 2nd separation case | B66 `DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS` §F-NEW-15 | M-V65A-CASE-NACA-STALL (Tier 2) | pending |
| #3 V103 candidate Cf-canonical-choice + low-Re-transition 2nd incompressible TBL case | B64 `DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP` §F-NEW-C + §F-NEW-low-Re | M-V65A-CASE-TBL-2ND-RE (Tier 2) → M-V65A-V103-PROMOTE | pending |
| #4 V105 candidate wedge-axis residual plateau 2nd canonical artifact witness | B70 `DEC-V64-A-sub-M-V64A-VAL-FULL-PIPE` §residual transparency | M-V65A-V105-WEDGE-AXIS-2ND (Tier 2) | pending |
| #5 V106 candidate `limitTemperature` substrate fix template 2nd thermo-FPE case | B61 `DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX` §V-candidate v3-new-1 | M-V65A-CASE-006-THERMO-LAYER3 + M-V65A-CASE-016-3AXIS (Tier 1) + M-V65A-V106-THERMO-TEMPLATE-2ND (Tier 2) | pending |

Done #1 ≥ 5/5 = all 5 absorbed (LANDED OR mark QUESTIONABLE / re-classify with documented rationale per V64-A redirect precedent).

---

## V101+ promotion queue (Done #2 explicit · per V64-A close §7.2)

| V101+ row | V64-A source | V65-A landing milestone | Promotion criterion | Status |
|---|---|---|---|---|
| **V101** | B57 + B63 case_004 F-NEW-3 chord-axis convention | M-V65A-V101-PROMOTE (Tier 1) | EMPIRICALLY CONFIRMED V64-A · distinct-signature met · ≥2-case witness via B57 + B63 cross-evidence within case_004 | candidate firm · pending landing |
| **V102** | B63 case_004 F-NEW-3.1 LE/TE orientation | M-V65A-V102-PROMOTE (Tier 2) post M-V65A-CASE-004-LE-TE-FIX | needs 2nd-pass verification: |M_x| sign + Cp band OR else QUESTIONABLE | candidate ~50% · gated on Tier-1 fix attempt yield |
| **V103** | B64 case_021 NASA TMR · 2 sub-signatures (F-NEW-C + F-NEW-low-Re) | M-V65A-V103-PROMOTE (Tier 2) post M-V65A-CASE-TBL-2ND-RE | needs 2nd TBL case to disambiguate · 2 rows possible | candidate ~60% · split possible |
| **V104** | B66 case_022 BFS · F-NEW-15 inlet BL | M-V65A-V104-PROMOTE (Tier 2) post M-V65A-CASE-NACA-STALL | separation 2nd witness needed · NACA stall must surface consistent pattern | candidate ~60% |
| **V105** | B70 case_027 Pipe · wedge-axis residual canonical OpenFOAM artifact | M-V65A-V105-WEDGE-AXIS-2ND (Tier 2) | needs 2nd wedge/axisymmetric case · §3.1 MARGINAL precedent applicable | candidate ~70% |
| **V106** | B61 thermo-FPE fix · `limitTemperature` substrate template | M-V65A-V106-THERMO-TEMPLATE-2ND (Tier 2) post 2nd thermo-FPE case | template 2nd application + distinct-signature (combustion vs shock-startup) | candidate ~50% |

**Target: ≥ 4/6 LANDED (V101..V106)**. Honest expected-value 3.9/6 — borderline · M-V65A-V101-PROMOTE is highest-confidence Tier-1-eligible single-row landing to unblock counter.

---

## 进度计数器（每 session 末更新）

```
当前 V64-A carry-over absorption:                 0 / 5 (target 5/5 · Done #1)
                                                  待 LANDED: #1 F-NEW-3.1 fix · #2 NACA stall · #3 TBL 2nd Re · #4 wedge-axis 2nd · #5 thermo template 2nd
当前 V101+ promotion 进 V-series corpus:           0 / 6 (target ≥4/6 · Done #2)
                                                  candidate firmness: V101 firm · V105 ~70% · V103/V104 ~60% · V102/V106 ~50%
当前 Net-new 工业 case e2e:                       0 / 2 (target ≥2 industrial FULL or strong-PARTIAL · Done #3)
                                                  candidate set: APU bay · NACA stall · Sandia Flame D · 2nd TBL
当前 Industrial-grade FULL reports:               0 / 3 (target ≥3 工业级 · Done #4 · 1D analytical NOT counted)
                                                  V64-A 1D analytical trio (Poiseuille / Couette / Pipe) excluded from V65-A Done #4 counting
当前 Canonical-artifact ledger 2nd witnesses:     0 / 2 (target wedge-axis 2nd + thermo-FPE template 2nd · Done #5)
当前 V-row truth-capture rate:                    clause-1 ≥7/9: 0 net-new (case_011 7/9 V64-A carry-forward可继承)
                                                  clause-2 ≥5/9 on ≥2 cases: 0 net-new (case_004 5/9 + case_006 5/9 + case_011 7/9 V64-A carry-forward可继承)
当前 Done dims MET:                               0 / 6
```

最后更新时间：`2026-05-15 **ARC ACTIVATED · B72 V65-A charter Accepted · ARC-GOAL initialized · 0/6 Done dims · 0 sub-DECs LANDED yet** · counter +1 charter · 更新人：Claude Code Opus 4.7 session main`

---

## 关键依赖图

```
M-V65A-V101-PROMOTE          ─┐
M-V65A-CASE-004-LE-TE-FIX    ─┤  Tier 1 (carry-over absorption · parallel · independent)
M-V65A-CASE-006-THERMO-LAYER3 ┤
M-V65A-CASE-016-3AXIS        ─┘
       │
       ↓
M-V65A-CASE-APU-BAY        ─┬─→  M-V65A-V102-PROMOTE  ─┐
M-V65A-CASE-NACA-STALL     ─┤                          │
M-V65A-CASE-TBL-2ND-RE     ─┤                          │
M-V65A-CASE-SANDIA-FLAME-D ─┘                          │
       │                                               │
       └→ M-V65A-V103-PROMOTE → M-V65A-V104-PROMOTE   ─┤
                  │                                    │
                  ↓                                    │
       M-V65A-V105-WEDGE-AXIS-2ND  ─→  M-V65A-V106-THERMO-TEMPLATE-2ND
                                                       │
       M-V65A-VAL-FULL-1 → M-V65A-VAL-FULL-2 → M-V65A-VAL-FULL-3
                                                       │
                                                       ↓
                                          M-RADAR-V7-A  ─→  M-V66-A
```

Tier 1 milestones parallel-safe (different case dirs · different artifact families). Tier 2 industrial cases parallel-safe. V101+ promotions sequenced post-case landing. M-V65A-V101-PROMOTE is Tier-1-eligible single-row promotion (V64-A B57+B63 evidence firm) — unblocks Done #2 counter immediately.

---

## V64-A + V63-A + V62-A 资产复用清单 (per V65-A charter DEC §"V64-A asset reuse manifest")

V65-A is "Industrial Coverage Deepening" precisely because V64-A asset reuse is **≥ 95%** for V65-A scope (per V64-A close §9.1). Direct reuse manifest (no new framework / no new architectural primitive in V65-A baseline scope):

- `advisor_stack.py` 12 LANDED advisors (11 V62-A + D11 V63-A + solver_block_advisor V64-A B55) — direct reuse
- 4Q cross-feature audit framework (`test_4q_gate_stack_acceptance.py`) — direct reuse
- `/api/ai-review` route (HTTP plumbing · 6-field schema) — direct reuse · no extension for V65-A scope (frontend wiring still deferred V66+)
- M-DRIFT v1 + V62 v2 (corpus drift-prevention hooks) — direct reuse · V101+ rows go through commit-time + route-time hooks
- V-series corpus convention (V51+ → V100 · single-row-per-failure-mode · numerics-class tagging) — direct reuse + V101+ extension
- 12 case substrates (V63-A 3 + V64-A 6 net-new incompressible + V64-A 3 D11 cross-val) — direct reuse + case_004/006/016 iteration (substrate v5/v4/v4)
- D11 stl_face_label_validator cross-val pattern — direct reuse · V105 wedge-axis 2nd witness + V104 separation 2nd witness may exercise D11 cross-val
- Track C dual-path methodology (HTTP TestClient + direct assemble_stack) — direct reuse · per-FULL report 4Q + env -i LLM-offline rerun
- 14 V64-A validation reports (11 PARTIAL + 2 FULL + 1 MARGINAL ratified) — reference + upgrade target for case_004/006/016 chains
- **§3.1 MARGINAL → FULL semantics** (V64-A close · NEW precedent) — available as ratification path · explicitly anticipated for V105 wedge-axis 2nd witness · NEEDS user ratification per (d) clause
- **§3.2 multi-case PARTIAL → FULL rebadge semantics** (V64-A close · NEW precedent) — available as ratification path for V65-A net-new industrial cases if honest engineering evidence body executed per case + within-arc precedent established + user explicit ratification
- V64-A 1D analytical strict-FULL trio (Poiseuille / Couette / Pipe) — reference baseline (canonical convention) · NOT direct reuse for industrial Done #4 (V65-A bar higher)

---

## 沿用 V62-A + V63-A + V64-A 不变规则

- LLM offline 四问门控 (V130 thesis · 每个新功能 PR/DEC/UI 改动必答四问)
- advisor 不是 driver · 只 advise · engineer (or Claude Code session) 最终决策
- 双 corpus drift-prevention hook (M-DRIFT v1 + V62 v2) 保留
- session-end Notion sync (仅 Status=Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven: ≥3 共享代码路径 / governance-rule-change → charter; else sub-DEC 6-field minimum schema
- Spike-class 一等 scope class (≤30 LOC + 1 test + commit `confidence: <h/m/l>` · 不调 DEC / Codex / Kogami / Notion)
- Codex 1-sync-trigger (auth/signing/security boundary) · round cap = 3
- Kogami opt-in (用户主动召唤 only · auto-trigger 全废 per v2.3)
- pre-implementation surface-scan (per DEC-V61-088) optional except new routes/ / pages/
- counter 纯遥测
- V-row distinct-signature enforcement (不准 alias 灌水)
- **PARTIAL semantics precedents (V63 close §3.1 + V64 close §3.1 MARGINAL extension + V64 close §3.2 multi-case rebadge)**: V65-A inherits all 3 · ratification paths available subject to V63/V64 stated criteria + user explicit ratification

---

## v2.3 governance 合规（V65-A scope）

- V65-A 跨 ≥3 共享代码路径 (case substrate v4/v5 + solver runtime case_004/006/016 + net-new industrial case dirs + V-series corpus V101+ + advisor stack optional extension + validation_reports/v65/) → **charter-level DEC** Accepted via `DEC-V65-A-charter` (2026-05-15 B72)
- Codex review per-milestone (nominal):
  - All V65-A Tier 1/2/3 milestones currently anticipated to **NOT** touch routes/ or pages/ (frontend wiring still deferred V66+) → Codex skip default
  - **Optional V65-A advisor extension** (per Tier 2 net-new industrial case discovery · separation-class / combustion-class / rotating-machinery follow-up) → if new advisor file is added that is route-adjacent (like V64-A B55 `solver_block_advisor.py`) → 1-sync-trigger applies and Codex pre-merge required per v2.2
- Round cap = 3 per V133 unchanged
- Kogami opt-in (用户主动召唤)
- counter 纯遥测 (V65-A 重启 autonomous_governance counter · V64-A counter +20 ledger preserved in V64-A close DEC §10)
- CODEX_OVERRIDE_REASON for V65-A charter cadence-floor push: "V65-A charter docs-only governance · 4Q satisfied · no routes/auth/signing touched · v2.3 §DEC scope-driven charter-class exemption"

---

## 下一步建议（每次会话末由 main session 写）

> **2026-05-15 B72 V65-A charter Accepted · ARC-GOAL initialized · arc activated** · 6/6 Done dims pending · 0 sub-DECs LANDED yet.
>
> **下一会话候选** (highest-confidence Tier-1 first per V64-A close §7.2 V101 firm + V101+ promotion criteria):
>
> 1. **B73 = M-V65A-V101-PROMOTE** (Tier 1 · highest-confidence single-row V-series promotion · V64-A B57+B63 EMPIRICALLY CONFIRMED evidence · no new case run required · ≥2-case witness met via B57+B63 cross-evidence within case_004 · canonical reference attribution via NREL/TP-500-29955 + Schlichting convention · 推 Done #2 0/6 → 1/6 immediately · 推 Done #1 carry-over absorption indirect prep)
> 2. **B74 candidate = M-V65A-CASE-006-THERMO-LAYER3** (Tier 1 carry-over #5 first half · paired V106 source · combined sutherland + limitTemperature + URF v4 + p-coupling stability)
> 3. **B75 candidate = M-V65A-CASE-004-LE-TE-FIX** (Tier 1 carry-over #1 · `scripts/build_cad.py::section_wire()` v2 LE/TE tangential repair · primary V102 promotion source)
> 4. **B76 candidate = M-V65A-CASE-APU-BAY** (Tier 2 net-new industrial · `~/Desktop/apu-bay-ventilation-cht/` external geometry asset baseline + STAR-CCM+ via CodeBuddy precedent · primary Done #3 contribution)
>
> **推荐 sequencing**: B73 single-row V101 LAND (low risk · high signal) → B74 + B75 + B76 parallel-dispatchable (independent code paths) once B73 anchors V101+ promotion convention. **Avoid** premature net-new industrial case dispatch (B76 APU bay) before Tier 1 carry-over absorption demonstrates yield · per V64-A 1D-analytical-pivot lesson — start where evidence is firmest.
