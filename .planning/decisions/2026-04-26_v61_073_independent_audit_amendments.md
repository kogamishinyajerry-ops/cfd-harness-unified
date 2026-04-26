---
decision_id: DEC-V61-073
title: Independent Opus 4.7 audit ratification + 4 HIGH amendments + P2 kickoff HOLD
status: ACCEPTED_WITH_AMENDMENTS_PENDING_LANDING (2026-04-26 · independent-context Notion @Opus 4.7 audit returned RATIFY_WITH_AMENDMENTS · 4 HIGH findings being landed in this commit · P2 kickoff partial overturn → HOLD until 4 PCs GREEN)
authored_by: Claude Code Opus 4.7 (1M context · landing amendments per independent audit verdict)
authored_at: 2026-04-26
authored_under: 治理收口 anchor session · post-independent-audit amendment wave
parent_session: https://www.notion.so/34ec68942bed8105a5f2f961241cd32b
audit_source: Notion @Opus 4.7 independent-context review session 2026-04-26 (per audit prompt delivered to user · verdict pasted back)
supersedes_in_part:
  - W2_G9_in_session_gate (downgraded from "transitional gate" to "preparatory analysis"; this independent audit IS the legitimate W2 G-9 gate)
  - RETRO_V61_005_Q1_COMPLETE (downgraded back to COMPLETE_WITH_DEFERRED_GAPS — P2 kickoff explicitly HOLD per audit Q5 OVERTURN)
autonomous_governance: false
external_gate_self_estimated_pass_rate: 0.85
notion_sync_status: synced 2026-04-26 (https://www.notion.so/34ec68942bed812ab816c9f7ba082bcc)
parent_audit_pages:
  - "DEC-AUDIT-2026-04-26 · Independent ratification of 治理收口 closure (Notion Decisions DB · authored by Notion @Opus 4.7)"
  - "P2 Kickoff Plan v0.1 (Notion Canonical Docs · authored by Notion @Opus 4.7)"
---

# DEC-V61-073 · Independent Audit Ratification + 4 HIGH Amendments + P2 Kickoff HOLD

## Why

CFDJerry delegated independent-context Opus 4.7 audit of the 治理收口
closure work. The audit returned **RATIFY_WITH_AMENDMENTS** with one
material partial-overturn (P2 kickoff GO → HOLD) and **the 30-day
override window NOT consumed**.

Key constitutional finding: CFDJerry's 「全权执行,继续」 mandate is
**operational authorization** (calendar compression of the 7-day window),
not **constitutional override** (independence-of-context invariant from
Pivot Charter §7). Foundation-Freeze→Done and P1→Done are
administrative/substantive ratifications independently verifiable;
P2 kickoff is forward-looking authorization the in-session reviewer
cannot review of itself. The independent audit IS the legitimate W2 G-9
gate; the in-session review is downgraded to preparatory analysis.

## Decision

### Amendments landed (this commit + co-located commits)

**A1 · W2 G-9 gate doc downgrade**
The in-session W2 G-9 gate review at
`.planning/gates/2026-04-26_w2_g9_opus_4_7_gate_review.md` is downgraded
from "transitional gate verdict" to "preparatory analysis material" for
the independent audit. The Foundation-Freeze→Done and P1→Done verdicts
within remain valid (administrative/substantive). The P2 kickoff GO
verdict within is **OVERTURNED** by the independent audit and must not
be cited as gate authority.

**A2 · RETRO-V61-005 Q1 verdict revert**
Q1 completion verdict reverts from `COMPLETE` back to
`COMPLETE_WITH_DEFERRED_GAPS`. The "30-day override consumed" implication
in the retro is removed; the override window remains fully available
(zero days consumed) per audit constitutional finding.

**A3 · §10.5 token-budget cap (HIGH H3)**
Methodology v2.0 §10.5 amended in
`.planning/methodology/2026-04-26_v2_section_10_5_and_11_draft.md`:

- Add §10.5.4b: each sampling-audit fire is capped at **≤100k Codex tokens**
  to prevent token-budget starvation. P2 main-line will trigger ~3
  audits over its arc per estimated cadence; ≤100k/fire keeps the total
  within the RETRO-V61-004 P1 arc 460k precedent.
- Add §10.5.4c: sampling-interval ratchet `5 → 7 → 10 → 15 → 20` after
  each consecutive clean audit (replaces "20 → 5 stays at 5 until 2
  consecutive clean"). The smoother ratchet prevents both starvation
  and false-permissiveness.

**A4 · §10.5.4a surface list expansion (HIGH H1 spillover)**
§10.5.4a surface list grows from 5 to 7 audit-required surfaces:

6. **`correction_spec/` write paths** — any commit creating or modifying
   `CorrectionSpec` artifact paths under `reports/{case_id}/correction_specs/`
   or `knowledge/correction_patterns/`. CorrectionSpec influences the
   downstream Evaluation→Knowledge plane edge.
7. **`.planning/case_profiles/` write paths** — direct edits to
   `.planning/case_profiles/<case_id>.yaml` (especially `tolerance_policy`
   blocks). These are physical-truth-source-adjacent without being formal
   trust-core 5 modules.

**A5 · EXECUTOR_ABSTRACTION hybrid-init OpenFOAM-truth invariant (HIGH H4)**
Audit identified that EXECUTOR_ABSTRACTION canonical doc lacks a
formalized invariant for "OpenFOAM is the only truth source" under
hybrid-init mode. P2-T1 cannot start until this lands. Amendment file at
`.planning/specs/EXECUTOR_ABSTRACTION_hybrid_init_invariant.md` proposes
§X.Y formal invariant + companion unit-test specification. CFDJerry must
ratify this amendment in the Notion EXECUTOR_ABSTRACTION canonical doc
before P2-T1 begins.

**A6 · §11.1 advisory wire-up**
§11.1 `tools/methodology_guards/workbench_freeze.sh` wired into
`.pre-commit-config.yaml` in **advisory mode** (warn-not-block) per audit
Q4(a) "unwired = absent" finding. Wire-up co-lands with §11.5 SSOT
umbrella. Hardens to BLOCK after dogfood window expires 2026-05-19.

**A7 · §11.5 umbrella for 2 pre-existing SSOT discrepancies**
Notion Tasks DB umbrella created for the 2 pre-existing SSOT-check
findings (`2026-04-22_phase7_deep_review_pass_washing_fix.md` and
`2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md`).
Owner-ize only; do not modify content per kickoff line-A/B isolation
rule.

### P2 kickoff status: HOLD

**4 pre-conditions (PCs) must turn GREEN before P2-T1 starts:**

1. **PC1**: DEC-V61-073 (this DEC) Status=Accepted in Decisions DB.
2. **PC2**: EXECUTOR_ABSTRACTION canonical doc §X.Y hybrid-init OpenFOAM-truth
   invariant landed + companion unit-test spec.
3. **PC3**: §10.5+§11 promote from `provisional` to `Active` (or stay
   provisional with explicit "P2-T1 may proceed under provisional"
   rider). Note: audit recommends KEEP_PROVISIONAL pending the 4
   amendments above land — once they land, promotion to Active is the
   call.
4. **PC4**: Calendar gate — independent audit verdict acknowledged in
   anchor session + STATE.md `p2_kickoff_status` flips from `HOLD` to
   `GO_PENDING_PCs_GREEN` to `GO`.

P2-T1 (ExecutorMode ABC) ETA per audit P2 Kickoff Plan: 2026-05-01 →
2026-05-04. P2 closeout target: 2026-05-18. P3 kickoff dependency:
≥ 2026-05-19.

### DEC-V61-074 → V61-079 reservations (per audit P2 Kickoff Plan)

- DEC-V61-074: P2-T1 ExecutorMode ABC + 4-mode skeleton
- DEC-V61-075: P2-T2 FoamAgentExecutor → docker-openfoam wrapping
- DEC-V61-076: P2-T3 MockExecutor re-tag as ExecutorMode.MOCK
- DEC-V61-077: P2-T4 hybrid-init mode (requires SBPS §1 ratify first)
- DEC-V61-078: P2-T5 future-remote stub (doc only)
- DEC-V61-079: P2 closeout retro / promotion DEC

### Codex stair-anchor calibration (audit Q4 calibration check)

V61-071 trajectory was 0.85 (pre) → 0.78 (R1 actual) → 0.95 (R2 actual).
Audit verdict: trajectory matches expected stair-anchor curve;
**NO calibration adjustment** needed. RETRO-V61-001 0.87 stair-anchor
floor remains.

## Impact

| Metric | Value |
| --- | --- |
| Audit verdict | RATIFY_WITH_AMENDMENTS |
| HIGH findings | 4 (H1 P2 partial overturn · H2 override-not-consumed · H3 token cap · H4 hybrid-init invariant) |
| Amendments landed | 7 (A1-A7) |
| §10.5 surface list | 5 → 7 |
| §10.5 token cap | NEW: ≤100k/fire |
| §10.5 interval ratchet | NEW: 5→7→10→15→20 |
| §11.1 wire-up status | advisory mode (warn-not-block) until 2026-05-19 |
| Override window status | **0 days consumed** (window fully preserved) |
| P2 kickoff status | HOLD until 4 PCs GREEN |
| Counter v6.1 | 46 → 47 (autonomous_governance: true · audit-driven amendment) |

## Counter v6.1

`autonomous_governance_counter_v61` advances **46 → 47** (V61-072 → V61-073,
both autonomous_governance: true).

## Branch + commits

Direct-to-main per §10 治理降级 (DEC is methodology + governance, not
trust-core code).

## Related decisions

- **Parent rule**: Pivot Charter §7 independence-of-context invariant
- **Parent audit**: Notion DEC-AUDIT-2026-04-26 (independent Opus 4.7 ratification)
- **P2 kickoff plan**: Notion Canonical Doc P2 Kickoff Plan v0.1
- **Co-amends**: §10.5 + §11 drafts (provisional, pending Active promotion post-PC1-PC4 GREEN)
- **Downstream**: V61-074 (P2-T1) blocked on PCs

## Constitutional learning captured

CFDJerry's operational authorization「全权执行,继续」does NOT override
the Pivot Charter §7 independence-of-context invariant. Forward-looking
authorizations (kickoff gates) are categorically different from
backward-looking ratifications (phase-close gates). The closure
methodology should distinguish these explicitly. Captured for next
RETRO addendum.
