# POLICY_COMMITMENTS_LEDGER — Cat 3 策略承诺登记册

**Status**: Active
**Effective**: 2026-04-24 (first entry landed alongside VCP v1.0 promote)
**Authority**: SPEC_PROMOTION_GATE.md §7.3 (Cat 3 · Policy Commitment)
**Review Cadence**: Every policy entry is audited in the quarterly phase-close retro (per RETRO-V61-001 trigger #1).

---

## 目的

Cat 3 "Policy Commitment" 类型的"不做清单"条目无法通过代码层断言，只能
通过治理承诺落地。本 ledger 是这些承诺的**唯一权威登记册**，确保：
- 每条承诺有 `id / source_spec / source_section / commitment_text / created_at / review_cadence / next_review_due / decision_ref` 完整元数据
- 每条承诺在季度 retro 中强制 audit（下一次 retro 必须 explicit cover 所有 `next_review_due <= retro_date` 的条目）
- 每条承诺有 `DEC-POLICY-*` 作为首次签字依据

## 条目

### POL-VCP-001

```yaml
id: POL-VCP-001
source_spec: VERSION_COMPATIBILITY_POLICY
source_section: "§8.5 不要求跨 solver apples-to-apples 数值比较"
commitment_text: |
  跨 solver 家族（OpenFOAM ESI ↔ OpenFOAM.com ↔ SU2 ↔ Code_Saturne ↔ ...）
  的数值结果默认**不做 apples-to-apples 比较**。跨 family 数值差异视为
  solver-implementation-difference 而非 physics-disagreement；只能通过
  BenchmarkManifest 层面的 evaluation_protocol 做 relative benchmark。
  ESI/.com 分支内部数值一致的 case pair 属于特殊情况，需在
  knowledge/schemas/solver_family_registry.yaml 的
  cross_family_numeric_compatible_pairs 登记方可启用 WARN 而非 HARD_FAIL。
created_at: "2026-04-24"
review_cadence: quarterly
next_review_due: "2026-07-24"
decision_ref: DEC-POLICY-VCP-001
```

---

## Schema 约束

新增条目时：
1. `id` 格式 `POL-<source_spec_slug>-NNN`（`VCP` 是 VERSION_COMPATIBILITY_POLICY 的 slug）
2. `commitment_text` 必须**自足可读**——reviewer 在 retro 时不翻原 spec 就能判断承诺是否仍然合理
3. `review_cadence` default `quarterly`。higher cadence (e.g. `monthly`) 允许；lower 需 Opus Gate 签字
4. `decision_ref` 必须指向 Decisions DB 的 `DEC-POLICY-<spec_slug>-NNN` 条目，否则视为孤儿
5. 退休承诺：不删除条目，增加 `retired_at` + `retired_reason` + `successor_policy` (可选) 字段

## Retro audit 义务

每次 **quarterly phase-close retro** 必须在 retro doc 中 explicit 列出：
- 所有 `next_review_due <= retro_date` 的条目
- 每条的 audit verdict: `REAFFIRM` / `AMEND` / `RETIRE`
- AMEND/RETIRE 需开新 `DEC-POLICY-*`

缺少 audit 义务 = retro 本身 CHANGES_REQUIRED (等同硬门触发)。

---

## Cross-refs

- `docs/specs/SPEC_PROMOTION_GATE.md` §7.3 (Cat 3 evidence requirement)
- `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` RETRO-V61-001 (retro cadence rules)
- Notion Decisions DB — `DEC-POLICY-*` series
