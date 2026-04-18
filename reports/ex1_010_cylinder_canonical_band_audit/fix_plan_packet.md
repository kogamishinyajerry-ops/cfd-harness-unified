# EX-1-010 Fix Plan Packet — cylinder canonical-band-shortcut audit emission

- Packet owner: opus47-main (ADWM v5.2 self-Gate)
- Slice ID: EX-1-010
- Trigger: `circular_cylinder_wake.yaml` physics_contract
  SILENT_PASS_HAZARD precondition #2 explicitly calls out
  `canonical_st=0.165 if 50<=Re<=200 else None` as the hazard
  source (adapter lines 6800-6808). Runtime signal missing.
- Self-APPROVE: DEC-ADWM-006
- Execution plane: dispatch to Codex (src/ 禁区 per hard floor #2)

## §1 Problem statement

`src/foam_agent_adapter.py::_extract_cylinder_strouhal` sets
`key_quantities["strouhal_number"] = 0.165` whenever the task
Re falls in `[50.0, 200.0]`:

```python
canonical_st = 0.165 if 50.0 <= Re <= 200.0 else None
if canonical_st is not None:
    key_quantities["strouhal_number"] = canonical_st
```

This is a hardcoded canonical-band shortcut, not a measurement
of solver output. The circular_cylinder_wake gold YAML already
documents this at `physics_contract.preconditions[1]` and sets
`contract_status: COMPATIBLE_WITH_SILENT_PASS_HAZARD` with
`contract_status_detail` explicitly noting:
"strouhal_number is a shortcut that should be audited as
'canonical-band shortcut fired' when key_quantities[
'strouhal_number']==0.165 exactly while Re in [50,200]."

What's missing: the RUNTIME signal. The static contract_status
flags every PASS run identically; there is no way to tell from
the AttributionReport whether a particular run's PASS was
partially underwritten by the shortcut. EX-1-006 and EX-1-009
established the producer→consumer audit_concern wiring pattern
for exactly this class of hazard. This slice extends it.

## §2 Scope

Minimal producer→consumer wiring slice:

**Producer (src/foam_agent_adapter.py):**
- Inside `_extract_cylinder_strouhal`, when `canonical_st is
  not None`, record `strouhal_canonical_band_shortcut_fired =
  True` in `key_quantities` alongside the existing
  `strouhal_number` write.
- When `canonical_st is None` (Re outside [50,200]) or the
  function returns without setting strouhal_number, do NOT
  write the flag — downstream `.get(..., False)` handles
  absence.
- No change to `strouhal_number` numeric value or any other
  observable. TRUTH-EMISSION only.

**Consumer (src/error_attributor.py):**
- Extend `_resolve_audit_concern` enrichment logic to check
  the cylinder flag in addition to the existing Spalding flag:

  ```python
  if concern == "COMPATIBLE_WITH_SILENT_PASS_HAZARD" and exec_result is not None:
      kq = exec_result.key_quantities or {}
      if kq.get("cf_spalding_fallback_activated") is True:
          return f"{concern}:spalding_fallback_confirmed"
      if kq.get("strouhal_canonical_band_shortcut_fired") is True:
          return f"{concern}:strouhal_canonical_band_shortcut_fired"
  return concern
  ```

- The two suffixes are mutually exclusive in practice
  (flat-plate tasks don't emit the cylinder flag; cylinder
  tasks don't emit the Spalding flag). Order matters only if
  a single task somehow emitted both, which is not a real
  scenario in the current whitelist — the sequential if-check
  is correct.

**Tests:**
- New test in `tests/test_foam_agent_adapter.py`:
  `test_extract_cylinder_strouhal_records_canonical_band_shortcut`
  — asserts flag=True when Re=100 canonical band fires.
- New test: `test_extract_cylinder_strouhal_no_shortcut_flag_outside_band`
  — asserts flag absent (or False) when Re outside [50,200].
- New test in `tests/test_error_attributor.py::TestAuditConcern`:
  `test_silent_pass_hazard_enriches_with_canonical_band_shortcut_flag`
- New test: `test_silent_pass_hazard_strouhal_flag_false_unchanged`

## §3 Scope explicit NOT

- Do NOT change `strouhal_number` numeric value (0.165 when
  canonical band; solver-derived otherwise) — binding CHK-3
- Do NOT touch `knowledge/gold_standards/circular_cylinder_wake.yaml`
  — hard floor #1 locked (SHA256 dac44169...974b14 pre-
  captured for binding check). Narrative contract_status_detail
  already documents the hazard from G3 restructure.
- Do NOT change `pressure_coefficient_rms_near_cylinder` or
  `p_rms_near_cylinder` logic
- Do NOT modify `_compute_wall_gradient` or any unrelated
  extractor paths
- Do NOT remove the canonical_st shortcut; it remains as the
  numerical return (documented hazard)
- Do NOT add new public API surface
- Do NOT touch `whitelist.yaml`

## §4 CHK table

| CHK | Target | Binding? | Evidence path |
|---|---|---|---|
| CHK-1 | `strouhal_canonical_band_shortcut_fired` appears in key_quantities as True when Re=100 | binding | new adapter unit test |
| CHK-2 | Flag absent or False when Re outside [50,200] | binding | new adapter unit test |
| CHK-3 | `strouhal_number` numeric bit-identical to prior behavior (0.165 in-band, solver-derived out-of-band) | binding | existing adapter tests still pass; synthetic comparison |
| CHK-4 | `_resolve_audit_concern` returns `...HAZARD:strouhal_canonical_band_shortcut_fired` when flag=True | binding | new error_attributor test |
| CHK-5 | Returns bare `...HAZARD` when flag=False or missing (backwards compat) | binding | new error_attributor test + existing tests |
| CHK-6 | `AttributionReport.audit_concern` propagates enriched string end-to-end | binding | new error_attributor test via `attribute()` |
| CHK-7 | Full test suite remains green (256 → 260+) | binding | `python3 -m pytest tests/ -q` |
| CHK-8 | Diff size ≤ 40 lines in src/ | non-binding | `git diff --stat src/` |
| CHK-9 | Gold YAML SHA256 bit-identical (dac44169...974b14) | binding hard floor #1 | `shasum -a 256` pre/post |
| CHK-10 | No new public API surface; all changes to private helpers + key_quantities keys | binding | diff review |
| CHK-11 | Existing EX-1-009 spalding enrichment still works (no regression) | binding | existing test_silent_pass_hazard_enriches_with_spalding_fallback_flag still passes |

## §5 Cycle budget

- Budget: 2 cycles
- COND-1: cycle 1 PASS all CHK → APPROVE, close slice
- COND-2: cycle 1 any CHK 1-7/11 FAIL, but fixable → cycle 2 patch
- COND-3: cycle 2 still FAIL → FUSE + external-Gate escalation
- COND-4: CHK-9 FAIL (gold SHA256 change) → IMMEDIATE REJECT + investigate

## §6 Hard-floor compliance

- #1 GS tolerance/numeric: NOT TOUCHED (CHK-9 binding)
- #2 禁区 → Codex: src/ edits dispatched (both adapter + error_attributor)
- #7 Execution-by trailer: codex-gpt54 on the src/ commit

## §7 Dispatch brief for Codex

See `/tmp/codex_ex1_010_instruction.md`.

## §8 Expected commit shape

One squash commit:
- `src/foam_agent_adapter.py` +3 lines
- `src/error_attributor.py` +3 lines (one extra if-branch)
- `tests/test_foam_agent_adapter.py` +~30 lines (2 tests)
- `tests/test_error_attributor.py` +~25 lines (2 tests)

Trailer: `Execution-by: codex-gpt54`

---

Produced: 2026-04-18 (ADWM v5.2 autonomous continuation; post-EX-1-009)
