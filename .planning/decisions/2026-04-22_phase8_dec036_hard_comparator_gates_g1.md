---
decision_id: DEC-V61-036
timestamp: 2026-04-22T12:00 local
scope: |
  Phase 8 Sprint 1 — Hard comparator gates. THIS DEC lands G1 only
  (missing-target-quantity). G2–G6 land as DEC-V61-036b after Codex
  round 1. G1 is the foundational PASS-washing fix surfaced by user's
  2026-04-22 deep review: both acceptance drivers silently substitute
  the first numeric `key_quantities` entry as `measurement.value` when
  the case-specific extractor did not emit the gold's target quantity.
  Duct flow measured at `hydraulic_diameter=0.1`, BFS at
  `U_residual_magnitude=0.044` — passed as "measurement" and compared
  to gold's friction_factor / Xr_over_H, accidentally landing within
  tolerance bands and washing to PASS/HAZARD. G1 kills the fallback:
  if the gold's quantity (with aliases) cannot be found in the run's
  key_quantities, `measurement.value = None`, extraction_source =
  "no_numeric_quantity", and `_derive_contract_status` forces FAIL
  with a MISSING_TARGET_QUANTITY audit concern.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (pre-merge required per self-pass-rate ≤ 0.70)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 21 → 22. RETRO-V61-002 covered 20;
  next retro at counter=30 per cadence rule #2.
reversibility: |
  Partially reversible — schema change `MeasuredValue.value: float → float|None`
  is backward-compatible for reads (old fixtures with 0.0 still load),
  but regenerated audit_real_run fixtures will carry `value: null` for
  the 7 silently-substituting cases, which is a change the frontend must
  handle. Revert = 5 files restored + fixtures regenerated.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
github_merge_sha: pending
github_merge_method: pre-merge Codex verdict required
external_gate_self_estimated_pass_rate: 0.65
  (Cross-file schema touch + verdict engine edit + fixture regeneration —
  Codex pre-merge required per RETRO-V61-001 rule: ≤0.70 → pre-merge.
  Expected surface: (a) measurement.value None vs 0.0 boundary handling
  in frontend renders; (b) backward compat for fixtures that had
  extraction_source="comparator_deviation" already correct; (c) alias
  handling for quantity-name comparison in _derive_contract_status;
  (d) test updates where 7 cases flip from PASS/HAZARD to FAIL.)
supersedes: null
superseded_by: null
upstream: |
  - User deep-review 2026-04-22: "BFS reattachment_length 列 'U_residual_magnitude'
    / duct_flow friction_factor 列 'hydraulic_diameter' — 不是同一个量。"
  - Deep-plan subagent 036 root-cause trace:
    * scripts/phase5_audit_run.py::_primary_scalar (L76-91) first-numeric fallback
    * scripts/p2_acceptance_run.py::_extract_primary_measurement (L64-86) same bug
    * src/result_comparator.py already correctly gates G1 via
      _lookup_with_alias; the drivers BYPASS that gate.
  - DEC-V61-035 (default → audit_real_run): surfaced honest 7 FAILs but
    6 of those FAILs are still MIS-QUANTITIES, not real measurements.
    This DEC makes the FAILs semantically correct.
---

# DEC-V61-036: Hard comparator gate G1 — missing target quantity

## Why now

User's 2026-04-22 CFD deep-review caught that `measurement.value`
displayed in the UI was from the **wrong quantity** for 7 of the 10
whitelist cases:

| case | gold expects | actual measured | current verdict |
|---|---|---|---|
| BFS | `reattachment_length` (Xr/H ≈ 6.26) | `U_residual_magnitude` ≈ 0.044 | FAIL +0.48% (accidentally close to gold's range) |
| duct_flow | `friction_factor` (f ≈ 0.0185) | `hydraulic_diameter` = 0.1 | FAIL +440% |
| plane_channel | `u_mean_profile` | `U_max_approx` | FAIL |
| DHC | `nusselt_number` | `temperature_diff` | FAIL |
| RBC | `nusselt_number` | `temperature_diff` | FAIL |
| turbulent pipe | `friction_factor` | `U_max_approx` | FAIL |
| impinging jet | `nusselt_number` | `wall_heat_flux` | FAIL |

The deviations happen to surface as large FAILs today (thanks to
DEC-V61-035 flipping default → audit_real_run), but that's
**arithmetic accident**. The fundamental error is that a different
scalar is being compared to gold — the FAIL status isn't an honest
physics FAIL, it's a schema FAIL masquerading as physics.

## What lands (this DEC)

### 1. Schema: `MeasuredValue` allows absent value + carries quantity name
- `ui/backend/schemas/validation.py::MeasuredValue`
- `value: float` → `value: float | None`
- New field: `quantity: str | None = None`

### 2. Driver refactor — strict-lookup, no first-numeric fallback
- `scripts/phase5_audit_run.py::_primary_scalar` → becomes
  `_primary_scalar(report, expected_quantity)`; uses
  `result_comparator._lookup_with_alias(key_quantities, expected_quantity)`;
  on miss returns `(expected_quantity, None, "no_numeric_quantity")`.
- `scripts/p2_acceptance_run.py::_extract_primary_measurement` → same refactor.
- Both callers (`_audit_fixture_doc`, `_write_fixture`) load the gold
  YAML and pass gold's canonical `quantity` into the extractor.

### 3. Verdict engine: hard-FAIL on missing value
- `ui/backend/services/validation_report.py::_derive_contract_status`
- New branch at top: if `measurement is None` or `measurement.value is None`
  → return `("FAIL", None, None, lower, upper)`.
- `_make_measurement`: accept `value: None` (was `if "value" not in m: return None`).
- `_make_audit_concerns`: when `measurement_doc["measurement"]["extraction_source"] == "no_numeric_quantity"`,
  inject `AuditConcern(concern_type="MISSING_TARGET_QUANTITY", ...)`.

### 4. Fixture regeneration
- 7 audit_real_run fixtures regenerated; `value: null, quantity: "<gold_name>",
  extraction_source: "no_numeric_quantity"`.
- LDC + 3 correctly-extracting cases unaffected.

### 5. Tests updated
- `test_dashboard_has_cases_and_summary`: `fail_cases >= 7` (was `>= 1`).
- `test_validation_report_default_prefers_audit_real_run`: measurement.value is None, contract_status FAIL, MISSING_TARGET_QUANTITY in concern types.
- New `test_g1_missing_target_quantity_fails`: synthetic no-match → FAIL.
- New `test_g1_ldc_passes`: LDC u_centerline present → PASS unchanged.

## What is NOT in this DEC

- **G2 unit mismatch** (follow-up DEC-036b) — needs canonical-unit table design.
- **G3/G4 VTK gates** (follow-up DEC-036c) — new `src/comparator_gates.py`.
- **G5/G6 log gates** (follow-up DEC-036d) — extends `_parse_log_residuals`.
- **DEC-038 attestor** — lands separately, pre-extraction.

Splitting into 4 sub-DECs keeps each Codex round tight (≤200 LOC).

## Regression + Codex

Pre-merge Codex review mandatory (self-pass 0.65 ≤ 0.70 threshold).
Post-Codex: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → 142+ pass.

## Counter

21 → 22.

## Related

- DEC-V61-035 (default → audit_real_run) — surfaced the bug by making
  honest verdicts visible; this DEC makes those verdicts semantically correct.
- DEC-V61-038 (convergence attestor) — pairs pre-extraction; composes AND-gated with 036.
- Phase 8 Sprint 1 = {036a G1, 036b G2, 038 A1-A6} landing together.
