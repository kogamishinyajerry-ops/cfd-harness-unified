# KNOWLEDGE_OBJECT_MODEL — P4 主交付物 spec · 8 类知识对象

**Status**: Draft v0.1 (repo-side accepting-clause mirror · Notion SSOT is primary)
**Effective**: — (pending promote, see SPEC_PROMOTION_GATE §2)
**Notion SSOT**: <https://www.notion.so/KNOWLEDGE_OBJECT_MODEL-ee2315ed162e41c0845dc44f474d8bf5>
**Scope**: P4 deliverable — 8 类 Knowledge Plane objects (CaseProfile, GoldStandard, SimulationObject, ExecutionArtifacts, Provenance, FailurePattern, CorrectionPattern, AttributionReport)

---

## §0 This repo-side stub

The canonical Draft content lives in Notion. This repo-side file
exists as a **minimal mirror** to host **accepting clauses** required
by upstream specs under SPEC_PROMOTION_GATE §7.2 (Cat 2 Scope
Delegation).

When KNOWLEDGE_OBJECT_MODEL promotes from Draft v0.1 → Active v1.0
(per SPEC_PROMOTION_GATE §2), the full spec content will be
consolidated here. G-6 backfill (commit 88d7a8e) already landed
`knowledge/schemas/risk_flag_registry.yaml` + 10 `.planning/case_profiles/*.yaml`
stubs; these will migrate to the canonical `knowledge/case_profiles/` path
at promote time.

## §1 Object Definitions (accepts delegation)

**accepts delegation from VERSION_COMPATIBILITY_POLICY §8.1 · Plane 内部 object schema**

KNOWLEDGE_OBJECT_MODEL is the authoritative location for **Knowledge
Plane 的 8 类对象 schema 定义**。VERSION_COMPATIBILITY_POLICY 不定义
这些 schema（只引用），依赖本 spec 提供。

Design notes (pre-promote):
- 8 objects listed in `Scope` above; each has its own schema.json
  under `knowledge/schemas/`
- `CaseProfile.version_metadata` field populates the four-tuple per VCP §2
- `CaseProfile.risk_flags` field populates per `knowledge/schemas/risk_flag_registry.yaml`
- `CaseProfile.tolerance_policy` field populates per `METRICS_AND_TRUST_GATES §4`

**Status of this accepting clause**: landed as Draft accepting clause per SPEC_PROMOTION_GATE §7.2 item (3) — consumer spec is Draft v0.1, accepting clause先在 Draft 版本落地是合法的，但 VCP v1.0 promote commit 必须与本 accepting clause commit 在同一 PR（已满足：Opus Option X action V-3 + VCP §9.1 scope_delegations 表同 commit landing）。

## §2 Cross-refs

- VERSION_COMPATIBILITY_POLICY v1.0 `docs/specs/VERSION_COMPATIBILITY_POLICY.md` §9.1 scope_delegations
- `knowledge/schemas/risk_flag_registry.yaml` (landed G-6 · 88d7a8e)
- `.planning/case_profiles/*.yaml` (landed G-6 · 88d7a8e; to migrate to `knowledge/case_profiles/` at promote)
- Notion Draft v0.1 for full spec
- SPEC_PROMOTION_GATE.md §7.2 (Cat 2 rules)

## §3 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v0.1-stub | 2026-04-24 | Claude Code · Opus Gate Option X V-3 | 首发 stub；Notion Draft v0.1 继续作为 primary；此 stub 只承载 VCP §8.1 的 accepting clause |
