---
decision_id: DEC-ADWM-003
timestamp: 2026-04-18T21:45 local
autonomous_governance: true
reversibility: reversible (single-commit revert)
notion_sync_status: synced 2026-04-19 (Decisions DB page https://www.notion.so/346c68942bed811d9fd0ead3fd810e64; confirmed by re-probe 2026-04-20T12:20)
---

# DEC-ADWM-003: Self-APPROVE EX-1-G3 Fix Plan Packet, dispatch Codex

## Decision summary
Under ADWM v5.2 granted authority, opus47-main self-approves the EX-1-G3
Fix Plan Packet (`reports/ex1_g3_cylinder_restructure/fix_plan_packet.md`)
and dispatches it to codex-gpt54 for execution. CHK-1..10 binding criteria
apply; CHK-4 (byte-identical numerics) is the invariant-preservation gate.

## Trigger / evidence
- 10-case contract_status dashboard (2026-04-18T20:55): 9/10
  producer→consumer coverage; cylinder_wake silently skipped because
  `physics_contract` is comment-encoded and `yaml.safe_load` returns None.
- Consumer path: `src/error_attributor.py:_resolve_audit_concern:42`
  reads `data.get("physics_contract")`.
- G3 goal in activation plan (.planning/adwm/2026-04-18_activation_plan.md §2).

## Alternatives considered
- **A. Modify consumer to parse YAML comments**: rejected — brittle,
  non-standard, every future YAML edit risks breakage.
- **B. Leave comment form, add consumer fallback reading a sidecar file**:
  rejected — fragments source of truth.
- **C. Structured promotion in gold_standards**: CHOSEN — 1-to-1 semantic
  lift, zero numeric drift, consumer requires no change.

## Chosen: Option C (structured promotion) via Codex dispatch
Fix Plan Packet approved 2026-04-18T21:45 local. Cycle budget 2.

## External-Gate pass-through likelihood
- 90% (higher than G1 because pure restructure, no physics risk)
- Down-weights:
  - Small risk of accidental whitespace/numeric drift in the 4
    reference_values blocks (CHK-4 mitigates).
  - Small risk that the alias file consumer path differs — CHK-3 forces
    a consumer unit test that exercises both case_ids.

## Reversibility
- Fully reversible: single `git revert`.
- No downstream consumer depends on the current null-audit_concern state
  for cylinder_wake; the dashboard explicitly flags this as a gap to close.

## Hard-floor touches
- #1 (GS tolerance): NOT TOUCHED — CHK-4 enforces numeric byte-identity.
- #2 (禁区 dispatch-to-Codex): ACTIVE — both gold_standard files
  dispatched to codex-gpt54.
- #7 (trailer): CHK-10 requires `Execution-by: codex-gpt54` on resulting commit.

## Cycle protocol
- Cycle 1 budget: one Codex dispatch round with §2.1 structured lift.
- If cycle 1 FAIL CHK-3: Codex adds the required consumer test.
- If cycle 2 FAIL CHK-1/2 or CHK-4: FUSE → document as "G3 deferred to
  direct opus47-main edit under ADWM temporary-bypass authority" in a
  DEC-ADWM-004.

## Notion mirror TODO
When MCP reachable: Decisions DB entry with this file verbatim.
