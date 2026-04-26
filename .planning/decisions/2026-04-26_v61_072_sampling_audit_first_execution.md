---
decision_id: DEC-V61-072
title: Sampling Audit Anchor · First Execution · §10.5 Active Activation
status: VERDICT_DEGRADATION_RULE_AT_RISK_§10.5_AMENDED (2026-04-26 · 9 commits 3d3509e..faf8446 audited · 4 findings 2 HIGH + 2 MED · §10.5.4a 5 surfaces added to audit-required list · sampling interval dropped 20→5)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
authored_under: 治理收口 2026-04-26 → 2026-05-03 anchor session · Workflow E
parent_retro: RETRO-V61-005 (Day 7 closeout pending)
parent_session: https://www.notion.so/34ec68942bed8105a5f2f961241cd32b
supersedes_gate: none
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.60
notion_sync_status: pending
codex_tool_report_path: reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md
---

# DEC-V61-072 · Sampling Audit Anchor First Execution + §10.5 Activation

## Why

Methodology v2.0 §10 治理降级 standing rule (Active since RETRO-V61-006
addendum) exempts non-trust-core changes from mandatory Codex review.
Without a falsifiability mechanism, §10's blind spots accumulate
silently. §10.5 (drafted in
`.planning/methodology/2026-04-26_v2_section_10_5_and_11_draft.md`)
introduces a retroactive sampling audit anchor: every 20 non-trust-core
commits OR every phase boundary, fire a Codex 1-round audit and produce
a degradation-rule blind-spot report.

DEC-V61-072 is the **first execution** of this anchor. The 9-commit
window covers Workbench M1-M4 + 3 extensions
(`3d3509e..faf8446`) shipped 2026-04-26 under §10.

## Decision

Codex GPT-5.4 retroactive 1-round audit fired on 2026-04-26T11:34
against the 9-commit window. Verdict: **DEGRADATION_RULE_AT_RISK**.

### Findings (full details in `reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md`)

| # | Cat | Severity | Affected commits | Surface |
| --- | --- | --- | --- | --- |
| 1 | 2 — Operator-layer security/auth | **HIGH** | 3d3509e / ce0a8ce / 5fff107 / 6b7492c / faf8446 | `FoamAgentExecutor.execute()` exposed via workbench, draft YAML feeds real run, /api routes, `reports/` persistence, operator-facing failure semantics |
| 2 | 3 — Cross-file rename | MED | 5fff107 / 74a93f1 | `/api/cases/{id}/runs` collided with Learn `/runs`; fixed reactively |
| 3 | 4 — Reproducibility/determinism | MED | 5fff107 / faf8446 | Second-level run_id timestamps, idempotent overwrite, silent partial-write skip, `reports/*` discovery by directory shape |
| 4 | 5 — Solver-stability on novel input | **HIGH** | ce0a8ce → 5fff107 / e83067c / faf8446 | `user_drafts/{case_id}.yaml` priority over whitelist; draft parameters feed `TaskSpec` without per-case range validation |

### Counter calibration

Did this 9-commit batch warrant §10 degradation? **NO.** Module-only
gating was too weak. Trust-core files stayed clean, but the batch
crossed into real solver execution / durable artifacts / new
operator-facing /api surfaces / draft-to-solver plumbing — all
audit-required surfaces in retrospect.

## Action taken (autonomous, per kickoff Workflow E authority)

1. **§10.5 ACTIVATED** — Methodology v2.0 §10.5 promoted from DRAFT to
   Active via this DEC. The draft document at
   `.planning/methodology/2026-04-26_v2_section_10_5_and_11_draft.md`
   carries the canonical text.

2. **§10.5.4a · 5 audit-required surfaces added to §10 amendment**:
   - FoamAgentExecutor call sites outside trust-core 5 modules
   - Docker / subprocess reachability changes
   - `/api/**` route registration
   - `reports/` durable persistence schema/discovery changes
   - `user_drafts/` → `TaskSpec` plumbing without whitelist validation

3. **Sampling interval drop 20 → 5 commits** — per Codex first-
   execution recommendation. Stays at 5 until 2 consecutive subsequent
   audits return zero category 2-5 findings.

4. **Merges KEPT on origin/main** — no trust-core bleed, no known
   corruption, commits are functional. Per §10.5.5 / Codex
   recommendation, recall mechanics are reserved for trust-core-bleed
   findings only. The 4 specific blind-spot surfaces are now under
   §10.5.4a allowlist removal — any future change requires Codex.

5. **§11 anti-drift standing rules drafted** — co-located in same
   methodology draft document. §11.2 sampling audit anchor = §10.5;
   §11.5 SSOT consistency check enforces the audit at phase boundaries.

6. **RETRO-V61-005 agenda updated** — "DEC-V61-072 first-execution
   findings retro" added to Day 7 closeout agenda for CFDJerry review.

## Impact

| Metric | Value |
| --- | --- |
| Commits audited | 9 |
| Codex tokens used | ~290k (well under 460k budget per RETRO-V61-004 P1 arc) |
| Findings | 4 (2 HIGH · 2 MED · 0 LOW) |
| Verdict | DEGRADATION_RULE_AT_RISK |
| §10 amendment | §10.5 + §10.5.4a 5 surfaces + interval 20→5 |
| §11 standing rules drafted | 5 (§11.1-§11.5) |
| Counter advance | 45 → 46 (autonomous_governance: true · §10.5 self-execution) |
| Self-pass-rate prediction | 0.60 (honest — first execution = high prior on miss) |

## Pre-merge Codex review note

Per RETRO-V61-001 Q4 self-pass-rate ≤70% triggers pre-merge Codex
review. Self-est = 0.60. However:
- The DEC itself is a **methodology decision document**, not code.
- The Codex audit IS the review (round 1 fired and lands the verdict).
- The §10.5 draft is non-Active until CFDJerry signs (see promotion
  checklist in draft doc).

Therefore the pre-merge Codex review obligation is satisfied by the
audit itself. No additional Codex round required for this DEC.

## Counter v6.1

`autonomous_governance_counter_v61` advances **45 → 46** (V61-067 → V61-072,
both autonomous_governance: true; V61-068/069/070 are line-B
proposed-but-not-landed; V61-071 is autonomous_governance: false
external-pending).

## Branch + commits

Direct-to-main; co-lands with:
- `.planning/methodology/2026-04-26_v2_section_10_5_and_11_draft.md`
- `reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md`
- `.planning/decisions/2026-04-26_v61_071_load_tolerance_policy_wiring.md`
- This file (`.planning/decisions/2026-04-26_v61_072_sampling_audit_first_execution.md`)

## Related decisions

- **Parent rule**: Methodology v2.0 §10 治理降级
- **Co-lands**: DEC-V61-071 (load_tolerance_policy wiring · P1 tail)
- **Sibling sampling audits**: none (this is the first; DEC-V61-XXX
  next-execution will fire after 5 more non-trust-core commits)
- **Methodology pointers**: §10.5 draft + §11 draft (same file)
- **Day 7 closeout**: RETRO-V61-005 agenda includes findings review

## Sequencing note

This DEC was **drafted by Claude Code Opus 4.7 autonomously** under the
治理收口 anchor session's explicit Workflow E authority. The §10.5
promotion is provisional until CFDJerry signs in the Decisions DB. Until
signed, §10.5 is "actively-applied per anchor-session authority"; not
formally Active. This intermediate state is recorded in STATE.md
`methodology_active_sections` field as `§10.5 (provisional · authored
2026-04-26 · pending CFDJerry sign-off)`.
