---
decision_id: DEC-V63-A-charter
title: V63-A Industrial Scale-Up Arc · charter DEC · elevated from plan-file at user ratification 2026-05-14
status: Accepted
parent_dec: V62-A-close
phase: V63-A charter (Industrial Scale-Up · ratified 2026-05-14)
notion_sync_status: pending
---

# DEC-V63-A-charter · V63-A Industrial Scale-Up Arc

## Status

**Accepted 2026-05-14** — elevated from `.planning/2026-05-14_v63_charter.md`
(renamed from `_draft` in B38 commit chain at user ratification).

V62-A close DEC `DEC-V62-A-close` (Accepted same B38 chain) records the 6/6
Done dim MET evidence; this charter DEC anchors `parent_dec` for V63-A
sub-DECs (M-D11-DRAFT first · Tier 1 dispatch unblocked).

V63-B (Frontend Activation) + V63-C (M6 Operationalization) move to
Alternatives Appendix in plan-file (per B38 commit `docs(v63-plan)`).

## North Star (verbatim from plan-file V63-A §)

> **让 advisor stack 在 ≥5 个独立工业 case 上以 100% adoption 跑通 ·
> V-series corpus 扩张到 V100+ · 收齐 V62-A surfaced deferred items (D11 /
> D6 HTTP / D10 catalog / case substrate 扩展) · 产出 ≥3 篇工业级 e2e
> validation report.**

## Done Definition (verbatim from plan-file V63-A · all 6 dims must hit)

| # | 维度 | 起点 (V62-A close) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Distinct numerics class · 100% adoption | 3 classes (steady-laminar-CHT-multi-stream / compressible-DES-acoustic / compressible_shock_density_based) | **≥ 5 classes 100% adoption PASS** | `grep -E "100% adoption" .planning/retrospectives/*stack_track_c*.md \| sort -u` |
| 2 | V-series corpus size | V51+ (~824 LOC in methodology) | **≥ V100 distinct V-rows landed** | `grep -cE "^### V[0-9]+ ·" .planning/methodology/industrial_case_solver_findings.md` |
| 3 | D-class advisor LANDED | 2 (D6 + D10) | **≥ 3 LANDED (D11 candidate)** | `grep -E "D-class.*LANDED" .planning/cross_cuts/advisor_coverage_*.md` |
| 4 | Industrial e2e validation report | 0 (Track C retros are session-shape · not full prep→solve→postp) | **≥ 3 cases with full report (prep → solver → postp · convergence + comparison + V-row attribution)** | `ls .planning/validation_reports/v63_*.md \| wc -l` |
| 5 | V62-A carry-over closure | 6 items deferred | **≥ 4 / 6 items closed (D11 + D6 HTTP + D10 catalog scope + case substrate)** | each closed via sub-DEC with V-row + retro chain |
| 6 | V-row truth-capture rate (canonical case) | 1/9 (case_006 post TRACK-3-rerun) | **≥ 5/9 on ≥1 canonical case · ≥ 3/9 on ≥3 cases** | retro §V-row attribution counter |

**任一未达成 = V63-A 不 close**, 启动 root-cause retro。

## 反命题 (anti-Done · failure modes · per plan-file)

- ❌ 5 cases all on same numerics class → fails dim #1 (must be **distinct** classes)
- ❌ V-row count crossed 100 by inflating with same-pattern entries → fails dim #2 spirit (须 distinct failure-mode signature)
- ❌ D11 LANDED but no case exercises V94 face-label loss → 孤儿 advisor (per V62-A 反命题 template)
- ❌ Validation report counts case_011 + case_016 + case_006 already covered by V62-A retros (no new evidence)

## Cross-cutting code paths (V63-A predicted ≥ 3 → charter scope satisfied per v2.3)

1. `ui/backend/services/geometry_ingest/stl_face_label_validator.py` (新建 by M-D11-DRAFT · sub-DEC pending B39)
2. `ui/backend/routes/ai_review.py` (extended by M-D6-HTTP-WIRE · stl_bbox_set field addition)
3. `ui/backend/services/geometry_ingest/bc_type_name_validity_advisor.py` (extended by M-D10-CATALOG-AUDIT · catalog expansion when case evidence demands)
4. `case_006/inputs/*.yaml` + `*.json` (M-CASE-006-SUBSTRATE · substrate input-manifest extension)
5. `.planning/methodology/industrial_case_solver_findings.md` (V-series corpus extension · M-V100-LANDING)
6. `.planning/validation_reports/v63_*.md` (new dir · M-VAL-REPORT-{1,2,3} new artifacts)

6+ paths confirmed → V63-A is **charter-scoped** by v2.3 §"DEC scope-driven".

## V62-A 资产复用清单 (sediment-driven reuse · per plan-file §5 V63-A row "V62-A 资产复用度 5/5")

| V62-A asset | V63-A reuse pattern |
|---|---|
| `advisor_stack.py` (~534 LOC · dispatch + composition) | **Direct reuse**. M-D11-DRAFT adds D11 to `_normalize_*` + `assemble_stack` dispatch table; same composition pattern as D10. No assembly-layer modification. |
| 10 LANDED advisors (A1/A2-v2/A3/A4/A5/A7/A8/A10/D6/D10) | **Direct reuse**. V63-A `+1 LANDED` target is D11 via same single-case-land precedent as A2 v1/D6/D10. Other 10 advisors fire unchanged across new cases. |
| `/api/ai-review` + `/api/ai-diagnose` routes (HTTP plumbing) | **Direct reuse for ai-review** (M-D6-HTTP-WIRE adds stl_bbox_set field with existing auto-discovery pattern from REQ-SCHEMA-EXPAND). ai-diagnose route reuse depends on V63-A retro discovery (not Tier 1 path). |
| 4Q cross-feature audit framework (`test_4q_gate_stack_acceptance.py`) | **Direct reuse**. Each new V63-A advisor + case extension runs the existing 4-test Q1-Q4 acceptance suite (LLM-offline gate · sha256 invariant · monkeypatch.delenv harness) plus inline 4Q gate in commit/PR. |
| M-DRIFT-V2 (`v_series_drift_guard.py` 269 LOC) | **Direct reuse audit-mode default**. V63-A new V-rows (V100+ corpus expansion) go through commit-time M-DRIFT v1 + route-time M-DRIFT v2 at `/api/ai-review` boundary. Strict-mode opt-in still per route query param. |
| REQ-SCHEMA-EXPAND (5 wire-form fields) | **Direct reuse + extension**. V63-A M-D6-HTTP-WIRE adds stl_bbox_set (6th field) following same auto-discovery + rehydration pattern. Backward compatibility preserved. |
| V99-WIDEN (shm_dict_validator alias resolution) | **Direct reuse**. New cases on `name:` alias paths get noise-pollution suppression for free. No re-extension. |
| Track C dual-path methodology (HTTP TestClient + direct assemble_stack) | **Direct reuse**. M-CASE-EXT-{1,2} new cases follow TRACK-2/3-rerun template (both paths · adoption %% · 4Q gate inline · env -i LLM-offline rerun). |
| V-series corpus convention (V51+ industrial sediment · numerics-class tagging) | **Direct reuse + extension**. V51 → V100 trajectory follows same single-row-per-failure-mode pattern · NEW signatures only (per dim #2 anti-命题 "no inflation of aliased duplicates"). |

**Reuse summary**: V62-A asset reuse is **≥ 90%** for V63-A scope · V63-A adds 1 new advisor (D11) + new cases + validation reports, **no new framework / no new architectural primitive**.

## 6 carry-over deferred items · priority (per plan-file §V62-A 未尽事项 + V63-A Tier 状态板)

V62-A surfaced 6 carry-over items. V63-A absorbs 4 (Tier 1 + Tier 2);
2 stay deferred past V63-A:

| Priority | Item | V63-A milestone | Why this order |
|---|---|---|---|
| **P1 first** | D11 `stl_face_label_validator` | **M-D11-DRAFT** (Tier 1) | V94 face-label loss class is open since V61-198; TRACK-1 §8 enh #3 explicit. Single-case land precedent established by A2 v1/D6/D10 · cheapest land path · unblocks V63-A advisor count to 3. **B39 candidate** per task brief. |
| P2 | D6 HTTP wire-up (stl_bbox_set) | **M-D6-HTTP-WIRE** (Tier 1) | REQ-SCHEMA-EXPAND scope-out close · single-file pattern extension · backward compatible. Unblocks D6 HTTP-path advisor count for future Track C. |
| P3 | D10 catalog completeness audit | **M-D10-CATALOG-AUDIT** (Tier 1 · case-driven) | Low urgency · STANDARD_OPENFOAM_BCS 61/~200 is sufficient for known cases · only extend when V63 case evidence demands false-unknown-warning fix. Triggered, not pushed. |
| P4 | case_006 substrate extension | **M-CASE-006-SUBSTRATE** (Tier 2) | thin_wall_inputs + interface_bodies + interface_specs synthesis from existing evidence/v1/face_geometry.json · pushes V-row capture 1/9 → 3/9 for TRACK-5 demonstration. |
| **deferred (not V63-A)** | Frontend wiring of `/api/ai-review` + `/api/ai-diagnose` | (V63-B-or-later natural home) | V63-A is Industrial Scale-Up not Frontend Activation. Wiring belongs in V63-B candidate per plan-file §"V62-A 未尽事项" mapping. Revisit when V63-B-or-later opens. |
| **deferred (not V63-A)** | M-DRIFT-V2 `/api/ai-diagnose` route integration | (V63-B-or-later · coupled with frontend wiring) | DRIFT-V2 audit-mode default is sufficient for V63-A scope (no diagnose-path scale-up in V63-A); coupled with carry-over #5 frontend wiring. |

**V63-A Done dim #5 absorption target**: ≥ 4/6 carry-over items closed.
At V63-A close, items 1-4 above must all close (M-D11-DRAFT + M-D6-HTTP-WIRE +
M-D10-CATALOG-AUDIT + M-CASE-006-SUBSTRATE) → 4/6 = exact target.

## Tier dependency map (per plan-file V63-A §"关键依赖图")

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

## Triggered redirect (命中 → 修改 plan · per plan-file V63-A §)

| 条件 | 动作 |
|---|---|
| 商业 CAE AI GA 拿到 ≥3 工业 case ship 证据 | OSS 准备拉前 · V63 部分 milestone defer |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| 用户工作焦点偏离 ≥ 1 周 (frontend / OSS pull) | 每 Tier 末 redirect 复审 |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决 (继续 / 接受 / 推 sub-DEC) |
| 工业 case STEP 准备难度阻塞 ≥ 2 周 | 切到 carry-over P3/P4 优先级 / catalog 工作 |

## v2.3 governance compliance

- **DEC scope**: V63-A predicts 6+ shared code paths (per §Cross-cutting
  code paths) → **charter-level DEC required**. This file satisfies
  the requirement; first V63-A sub-DEC (M-D11-DRAFT in B39) sets
  `parent_dec: V63-A-charter`.
- **Codex review**: per V63-A milestone scope:
  - M-D11-DRAFT: D11 advisor source · not security boundary · Codex skip default per v2.3 1-sync-trigger
  - M-D6-HTTP-WIRE: routes/ai_review.py extension · qualifies as security-boundary touch · **Codex review required** pre-merge (1-sync-trigger)
  - M-D10-CATALOG-AUDIT: catalog data extension · not security boundary · Codex skip default
  - M-CASE-006-SUBSTRATE: input data files · not security boundary · Codex skip default
  - M-VAL-REPORT-*: docs only · Codex skip default
- **Round cap = 3** per V133 unchanged. After R3, remaining P1 → user
  ratification; remaining P2/P3 → retro queue.
- **Kogami**: opt-in only per V133; user may invoke on charter / high-risk
  PR / post-incident retro per their judgment. No auto-trigger.
- **Notion sync**: session-end batch only · only Status=Accepted DECs
  sync per v2.3 round-1 loosen. This charter (Accepted) qualifies for
  session-end batch (12+ DECs queued including V62-A close + V63-A charter).
- **Spike-class**: V63-A may accept spike-class commits (≤30 LOC + 1
  test + commit `confidence:<h/m/l>` · no DEC / Codex / Kogami / Notion)
  for surface scans · low-risk fixes.
- **Counter**: V63-A starts a new arc-counter (autonomous_governance
  telemetry · pure-telemetry per V133); V62-A counter +11 ledger
  preserved in V62-A close DEC §10.

## Inherited rules from V62-A (sustained · per plan-file V63-A §7)

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

## Asset re-anchoring (where SSOTs live in V63-A)

- **Plan SSOT**: `.planning/2026-05-14_v63_charter.md` (renamed from `_draft` in B38)
- **ARC-GOAL active**: `.planning/ARC-GOAL.md` (initialized fresh in B38)
- **ARC-GOAL V62-A frozen**: `.planning/ARC-GOAL-V62-A-CLOSED.md` (rename from prior `ARC-GOAL.md`)
- **Charter DEC**: this file (`DEC-V63-A-charter`)
- **Predecessor close**: `DEC-V62-A-close` (parent)
- **Codebase intel**: `.planning/intel/` continues active (unchanged)
- **V-series corpus**: `.planning/methodology/industrial_case_solver_findings.md` extends V51+ → V100+ in V63-A

## confidence

**med**. High confidence on:
- V62-A asset reuse manifest (concrete file paths · concrete sub-DEC chain · concrete patterns demonstrated 5 Track C runs)
- 6 Done dimensions are operationally measurable (file existence · grep counts · numerical thresholds)
- Carry-over absorption boundary (4 V63-A · 2 deferred · clean mapping)

Medium confidence on:
- Case discovery & STEP preparation timeline. V63-A Tier 2 case extension
  (M-CASE-EXT-1 + M-CASE-EXT-2) requires 2 distinct numerics class cases
  beyond the 3 already covered. Candidates (incompressible-LES-multi-fan /
  two-phase-VOF / heat-transfer-conjugate-radiation) need STEP+manifest
  preparation effort estimated > 1 milestone each. Pacing risk noted in
  plan-file §"Triggered redirect" condition "工业 case STEP 准备难度阻塞 ≥ 2 周".
- D11 single-case land precedent (V94 face-label loss) is the cheapest path
  but requires post-land cross-validation case ≥ 1 more (per A2 v1 / D6 / D10
  precedent expectations).
- V-row corpus V51+ → V100+ requires ~49 NEW distinct signatures. New case
  yield rate is empirically ~5-10 V-rows per case (V62-A B-arc data). Floor
  is achievable; ceiling discovery rate is uncertain.

These medium-confidence dimensions are scoped to forward-looking V63-A
execution; charter itself (scope · Done def · governance fit · asset
reuse · carry-over absorption) is data-grounded.

---

**End of V63-A charter DEC.** V63-A arc anchored. First sub-DEC
(M-D11-DRAFT) candidate for B39 per task brief; ARC-GOAL.md
V63-A active arc skeleton initialized in same B38 commit chain.
Notion sync pending session-end batch.
