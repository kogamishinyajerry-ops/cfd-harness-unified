---
decision_id: DEC-ADWM-006
timestamp: 2026-04-18T23:58 local
autonomous_governance: true
reversibility: reversible (localized src/ + tests; git revert if CHK fails)
notion_sync_status: PENDING
---

# DEC-ADWM-006: Self-APPROVE EX-1-010 Fix Plan Packet; dispatch to Codex

## Decision summary

`circular_cylinder_wake.yaml` physics_contract precondition #2
already documents the canonical-band-shortcut silent-pass hazard
at `src/foam_agent_adapter.py:6800-6808` (Re in [50,200] →
`strouhal_number = 0.165` hardcoded). The static contract_status
emits `COMPATIBLE_WITH_SILENT_PASS_HAZARD` on every cylinder PASS,
but no RUNTIME signal distinguishes runs where the shortcut
actually fired (Re in band) from runs where strouhal_number was
solver-derived (Re out of band).

EX-1-010 adds producer→consumer wiring mirroring EX-1-009:
- Producer records `strouhal_canonical_band_shortcut_fired`
  boolean in `key_quantities` when canonical_st path taken
- Consumer enriches `audit_concern` with
  `:strouhal_canonical_band_shortcut_fired` suffix when the flag
  is True on a SILENT_PASS_HAZARD run

Hard floor #1 (gold numeric fields) NOT touched — CHK-9 binding.
The enrichment is purely semantic; no behavior change to
`strouhal_number` returned value.

## Scope justification

Scope matches EX-1-009 precisely (producer→consumer wiring for
a second silent-pass hazard):
- Single-purpose wiring slice
- ≤40 lines src/ change budget
- Test coverage in same commit
- Full test suite gate (CHK-7)
- Backwards-compat gate (CHK-11 — EX-1-009 spalding enrichment
  must still work)

## Cycle budget

2 cycles (consistent with EX-1-009 precedent).

## Dispatch plan

- Codex receives `/tmp/codex_ex1_010_instruction.md`
- opus47-main finalizes commit locally if Codex sandbox blocks
  `git commit` (recurring pattern) with
  `Execution-by: codex-gpt54` trailer
- Pre-dispatch SHA256 capture on
  `knowledge/gold_standards/circular_cylinder_wake.yaml`:
  `dac441697706e61177afe82c8c581986ba44677cac6d5c70538aaa3778974b14`

## Reversibility

- `git revert` reverses the commit if cycle 2 also FAILs
- No gold-standard or whitelist.yaml edits — revert affects only
  src/ and tests/

## Hard-floor compliance

- #1 (GS numeric fields): protected by CHK-9 SHA256 binding
- #2 (禁区 dispatch): src/ + tests/ via Codex
- #7 (trailer): `Execution-by: codex-gpt54` on the code commit

## Notion mirror TODO

When MCP reachable: write to Decisions DB with
autonomous_governance=true; link to EX-1-010 slice_metrics.yaml
+ fix_plan_packet.md. (DEC-ADWM-001..005 still PENDING.)
