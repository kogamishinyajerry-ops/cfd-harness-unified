# EX-1-009 Fix Plan Packet — Spalding-fallback audit_concern emission

- Packet owner: opus47-main (ADWM v5.2 self-Gate)
- Slice ID: EX-1-009
- Trigger: Contract-status dashboard "Tier-1 future" remediation line #4
  (turbulent_flat_plate: Cf>0.01 Spalding substitution audit)
- Self-APPROVE: DEC-ADWM-005
- Execution plane: dispatch to Codex (src/ 禁区 per hard floor #2)

## §1 Problem statement

`src/foam_agent_adapter.py::_extract_flat_plate_cf` (around line 6961)
applies a SILENT fallback when the per-cell extracted `Cf > 0.01`:

```python
if Cf > 0.01:
    x_local = x_target / U_ref
    Re_x = U_ref * x_local / nu_val
    Cf = 0.0576 / (Re_x**0.2) if Re_x > 0 else Cf  # Spalding
cf_values.append(Cf)
```

The original extracted value is discarded and replaced with a literature
formula. The aggregation (`sum(cf_values)/len(cf_values)`) then returns
a mean that may be mostly or entirely fallback-derived. Nothing in
`key_quantities` records that the fallback fired.

Downstream, `result_comparator` compares the aggregated `cf_skin_friction`
against gold `ref_value=0.0076` and PASSes — even if the actual solver
extraction was physically unreliable. This is the silent-pass hazard
the gold YAML's `physics_contract.contract_status =
COMPATIBLE_WITH_SILENT_PASS_HAZARD` already flags STATICALLY.

What's missing: a RUNTIME signal. Currently a given run is indistinguishable
from another on this axis — the audit_concern is constant regardless of
whether fallback actually fired on that run.

## §2 Scope

Minimal producer→consumer wiring slice:

**Producer (src/foam_agent_adapter.py):**
- Record a boolean `cf_spalding_fallback_activated` and an integer
  `cf_spalding_fallback_count` in `key_quantities` when Cf>0.01 branch fires.
- No numeric change to the returned `cf_skin_friction` mean — the fallback
  value continues to be used as before. This is TRUTH-EMISSION, not
  behavior change.

**Consumer (src/error_attributor.py):**
- Extend `_resolve_audit_concern(task_spec, comparison)` signature to
  also accept `exec_result: ExecutionResult` (or read via composition).
- When the base concern prefix is `COMPATIBLE_WITH_SILENT_PASS_HAZARD`
  AND `exec_result.key_quantities.get("cf_spalding_fallback_activated")
  is True`, return the enriched string
  `COMPATIBLE_WITH_SILENT_PASS_HAZARD:spalding_fallback_confirmed`.
- When the flag is False or absent, return the bare prefix unchanged
  (backwards compatible).

**Tests:**
- New test in `tests/test_error_attributor.py::TestAuditConcern`:
  asserts enriched suffix when fallback=True.
- New test: asserts bare prefix when fallback=False.
- New test in `tests/test_foam_agent_adapter.py`: asserts `key_quantities`
  contains `cf_spalding_fallback_activated` and count when a synthetic
  Cf>0.01 input is fed.

## §3 Scope explicit NOT

- Do NOT change `cf_skin_friction` numeric returned value
- Do NOT change `knowledge/gold_standards/turbulent_flat_plate.yaml` —
  hard floor #1 locked; contract_status stays COMPATIBLE_WITH_SILENT_PASS_HAZARD
- Do NOT change `whitelist.yaml` or solver settings
- Do NOT modify `_compute_wall_gradient` logic or Cf aggregation path
- Do NOT remove the Spalding fallback; it remains the numerical return
- Do NOT adjust tolerance

## §4 CHK table

| CHK | Target | Binding? | Evidence path |
|---|---|---|---|
| CHK-1 | `cf_spalding_fallback_activated` appears in key_quantities when Cf>0.01 synthesized | binding | new adapter unit test |
| CHK-2 | `cf_spalding_fallback_count >= 1` when fallback fires; `== 0` when not | binding | new adapter unit test |
| CHK-3 | `cf_skin_friction` numeric value bit-identical to prior behavior (no regression) | binding | existing adapter test still passes; synthetic input comparison |
| CHK-4 | `_resolve_audit_concern` returns `...HAZARD:spalding_fallback_confirmed` when flag=True | binding | new error_attributor test |
| CHK-5 | `_resolve_audit_concern` returns bare `...HAZARD` when flag=False or missing | binding | new error_attributor test + existing test still passes |
| CHK-6 | `AttributionReport.audit_concern` string propagates enriched form | binding | new error_attributor test |
| CHK-7 | Full test suite remains green (252 → 255+) | binding | `python3 -m pytest tests/ -q` |
| CHK-8 | Diff size ≤ 60 lines in src/ | non-binding | `git diff --stat src/` |
| CHK-9 | Gold YAML for turbulent_flat_plate unchanged (SHA256 bit-identical) | binding hard floor #1 | `shasum -a 256` pre/post |
| CHK-10 | No new public API surface; all changes to private helpers + key_quantities dict keys | binding | diff review |

## §5 Cycle budget

- Budget: 2 cycles
- COND-1: cycle 1 PASS all CHK → APPROVE, close slice
- COND-2: cycle 1 any CHK 1-7 FAIL, but fixable → cycle 2 patch
- COND-3: cycle 2 still FAIL → FUSE + external-Gate escalation
- COND-4: CHK-9 FAIL (gold SHA256 change) → IMMEDIATE REJECT + investigate

## §6 Hard-floor compliance

- #1 GS tolerance/numeric: NOT TOUCHED (CHK-9 binding)
- #2 禁区 → Codex: src/ edits dispatched (both adapter + error_attributor)
- #7 Execution-by trailer: codex-gpt54 on the src/ commit

## §7 Dispatch brief for Codex

See `/tmp/codex_ex1_009_instruction.md` (next step).

## §8 Expected commit shape

One squash commit:
- `src/foam_agent_adapter.py` +8 lines (flag tracking in `_extract_flat_plate_cf`)
- `src/error_attributor.py` +15 lines (signature extension + enrichment branch)
- `tests/test_foam_agent_adapter.py` +30 lines (2-3 new tests)
- `tests/test_error_attributor.py` +20 lines (2-3 new tests)

Trailer: `Execution-by: codex-gpt54`

---

Produced: 2026-04-18 (ADWM v5.2 autonomous continuation session)
