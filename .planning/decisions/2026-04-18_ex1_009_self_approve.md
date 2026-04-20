---
decision_id: DEC-ADWM-005
timestamp: 2026-04-18T23:45 local
autonomous_governance: true
reversibility: reversible (localized src/ + tests; git revert if CHK fails)
notion_sync_status: synced 2026-04-19 (Decisions DB page https://www.notion.so/346c68942bed8153a974f817ad98de26; confirmed by re-probe 2026-04-20T12:20)
---

# DEC-ADWM-005: Self-APPROVE EX-1-009 Fix Plan Packet; dispatch to Codex

## Decision summary

Contract-status dashboard flags `turbulent_flat_plate` case #4 as
`COMPATIBLE_WITH_SILENT_PASS_HAZARD` with known silent-pass source
at `foam_agent_adapter.py:6924-6930` (Cf>0.01 Spalding substitution).
The static contract_status emits a constant audit_concern on every
PASS, but there is no RUNTIME signal distinguishing runs where the
fallback actually fired from runs where extraction was clean.

EX-1-009 adds producer→consumer wiring for the runtime signal:
- Producer records `cf_spalding_fallback_activated` boolean in
  `key_quantities`
- Consumer enriches `audit_concern` with `:spalding_fallback_confirmed`
  suffix when the flag is True on a PASS run

Hard floor #1 (gold numeric fields) NOT touched — CHK-9 makes this
a binding check. The enrichment is purely semantic (audit transparency);
no behavior change to `cf_skin_friction` returned value.

## Scope justification (why this slice is right-sized)

Scope matches G3 (EX-1-G3 cylinder_wake restructure):
- Single-purpose producer→consumer wiring
- ≤60 lines src/ change budget
- Test coverage accompanies in same commit
- Full test suite gate (CHK-7)

No speculative extension to other cases with similar silent-pass
prefixes (e.g. cylinder_strouhal canonical-band shortcut would be
analogous but out-of-scope for this slice).

## Cycle budget

2 cycles (consistent with G1, G3 precedent).

## Dispatch plan

- Codex receives `/tmp/codex_ex1_009_instruction.md` (self-contained
  task: src + tests + commit message)
- opus47-main finalizes commit (Codex sandbox `git commit` blocked)
  with `Execution-by: codex-gpt54` trailer
- Pre-dispatch SHA256 capture on
  `knowledge/gold_standards/turbulent_flat_plate.yaml` for hard
  floor #1 verification

## Reversibility

- Full `git revert` reverses the commit if cycle 2 also FAILs
- No gold-standard or whitelist.yaml edits — revert affects only
  src/ and tests/

## Hard-floor compliance

- #1 (GS numeric fields): protected by CHK-9 SHA256 binding check
- #2 (禁区 dispatch-to-Codex): src/ + tests/ via Codex
- #7 (trailer): `Execution-by: codex-gpt54` on the code commit

## Notion mirror TODO

When MCP reachable: write to Decisions DB with autonomous_governance=true
and link to EX-1-009 slice_metrics.yaml + fix_plan_packet.md.
