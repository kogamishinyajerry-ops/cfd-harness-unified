# METRICS_AND_TRUST_GATES — P1 主交付物 spec · 四类 metric + 三态 TrustGate

**Status**: Draft v0.1 (repo-side accepting-clause mirror · Notion SSOT is primary)
**Effective**: — (pending promote, see SPEC_PROMOTION_GATE §2)
**Notion SSOT**: <https://www.notion.so/METRICS_AND_TRUST_GATES-ecee8d970e8148ec8c714eba8f250110>
**Scope**: P1 deliverable — MetricsRegistry (pointwise / integrated / spectral / residual) + TrustGate (PASS / WARN / FAIL)

---

## §0 This repo-side stub

The canonical Draft content lives in Notion. This repo-side file
exists as a **minimal mirror** to host **accepting clauses** required
by upstream specs under SPEC_PROMOTION_GATE §7.2 (Cat 2 Scope
Delegation · consumer spec must write accepting clause).

When METRICS_AND_TRUST_GATES promotes from Draft v0.1 → Active v1.0
(per SPEC_PROMOTION_GATE §2), the full spec content will be
consolidated here.

## §4 Tolerance Policy (accepts delegation)

**accepts delegation from VERSION_COMPATIBILITY_POLICY §8.2 · tolerance values**

METRICS_AND_TRUST_GATES is the authoritative location for **tolerance
numerical values + tolerance policy semantics**. The upstream
`CaseProfile.tolerance_policy` field is populated per the rules
defined in this section (once promoted).

Design notes (pre-promote):
- Each metric class (pointwise / integrated / spectral / residual)
  has its own tolerance schema (absolute / relative / hybrid)
- Per-case override via `CaseProfile.tolerance_policy[<observable_name>]`
- TrustGate三态 merge 规则见 VERSION_COMPATIBILITY_POLICY §3 (aspirational)

**Status of this accepting clause**: landed as Draft accepting clause per SPEC_PROMOTION_GATE §7.2 item (3) — consumer spec is Draft v0.1, accepting clause先在 Draft 版本落地是合法的，但 VCP v1.0 promote commit 必须与本 accepting clause commit 在同一 PR（已满足：Opus Option X action V-3 + VCP §9.1 scope_delegations 表同 commit landing）。

## §5 Cross-refs

- VERSION_COMPATIBILITY_POLICY v1.0 `docs/specs/VERSION_COMPATIBILITY_POLICY.md` §9.1 scope_delegations
- Notion Draft v0.1 for full spec
- SPEC_PROMOTION_GATE.md §7.2 (Cat 2 rules)

## §6 修订记录

| 版本 | 日期 | 修订者 | 说明 |
|---|---|---|---|
| v0.1-stub | 2026-04-24 | Claude Code · Opus Gate Option X V-3 | 首发 stub；Notion Draft v0.1 继续作为 primary；此 stub 只承载 VCP §8.2 的 accepting clause |
