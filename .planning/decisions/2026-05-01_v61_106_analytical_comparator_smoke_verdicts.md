---
decision_id: DEC-V61-106
title: Analytical-comparator smoke verdicts — let adversarial cases declare physics-correctness checks the residual-only smoke runner can't catch
status: Accepted (2026-05-03 · Phase 1.1 (analytical_comparators schema + extractor wiring) + Phase 1.2 (analytical_comparator_pass expected_status) LANDED via commits 742f478 / 83a74e0 / ff95b71 with Codex R10→R11→post-comment-closure APPROVE_WITH_COMMENTS chain · Phase 1.3 (iter01 reclassification) BLOCKED at integration time and DEFERRED to follow-up DEC: empirical inspection of iter01 time directories revealed every time-step contains 21477 NaN entries — actual defect is solver divergence not slow convergence as the original DEC §Why hypothesis stated; backend's "finite residual" signal misleads because icoFoam log captures residual BEFORE field corruption catches up. iter01 stays at physics_validation_required (SKIPPED) until numerical setup is fixed (CFL / relaxation / icoFoam→simpleFoam — case originally declared simpleFoam in intent but route runs icoFoam). cfb13f5 dt sweep disproves CFL hypothesis and surfaces 2 deeper defects, queued for follow-up DEC. Phase 2 (sweep iter04/iter05/iter06 to analytical_comparator_pass) explicitly remains out-of-scope as documented in §Phase 2. User's 2026-05-03 autonomous-mode ratification "全权授予你开发" covers acceptance.)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-01
authored_under: tools/adversarial/results/iter01_v61_104_phase1_partial_findings.md §iter01 end-to-end re-test result (option 3 recommendation)
parent_decisions:
  - DEC-V61-104 (Interior obstacle topology · Phase 1.5 empirical correction proved the smoke runner's residual-only verdict is too narrow)
  - DEC-V61-105 (Adversarial smoke as hot-path regression gate · this DEC extends the smoke runner with a new verdict class)
  - RETRO-V61-053 (executable_smoke_test risk_flag · post-R3 defect surfaced by smoke testing motivated this verdict-class expansion)
parent_artifacts:
  - tools/adversarial/run_smoke.py (current smoke runner with 3 expected_status classes: converged / manual_bc_baseline / physics_validation_required)
  - ui/backend/services/case_solve/results_extractor.py (existing field parser + ResultsSummary dataclass with 9 measures)
  - tools/adversarial/cases/iter01/intent.json (canonical case that needs this — currently SKIP'd)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 70% (incremental extension of existing smoke_runner block schema · reuses existing extractor · low blast radius · the open question is whether Codex flags edge cases in the comparator DSL — float comparison tolerance, NaN handling, missing-field handling)
codex_tool_report_path: reports/codex_tool_reports/v61_106_r10_r11_chain.md
notion_sync_status: synced 2026-05-03 (https://www.notion.so/354c68942bed81fab7e2ce221f4f0940)

# Why now

DEC-V61-104 Phase 1.5 closure (2026-05-01) empirically proved the previous "obstacle subtraction broken" diagnosis was wrong. iter01's actual defect class is **slow convergence** (U residuals stay ~1.0 at step 250) combined with **need for qualitative physics validation** (the original adversarial intent was "verify bypass jet + downstream recirculation pattern" — a qualitative check, not a residual check).

The smoke runner today has 3 expected_status classes:
- `converged` — runs full pipeline + asserts `cont_err < 1e-3` and finite residuals
- `manual_bc_baseline` — skipped (uses legacy iter03 driver)
- `physics_validation_required` — **skipped permanently** because no comparator exists

The third class is a SKIP-forever cop-out. iter01, iter04 (rotated symmetry), and any future case where "the simulation runs but the physics needs domain-knowledge validation" all fall into a black hole — the smoke runner can't tell us if anything regressed, and the case becomes a permanent N/A in the verdict table.

# Scope

## Phase 1 · analytical_comparator schema + extractor wiring (1-2 days)

### 1.1 Add `analytical_comparators` field to intent.json `smoke_runner` block

```json
"smoke_runner": {
  "expected_status": "analytical_comparator_pass",
  "rationale": "...",
  "analytical_comparators": [
    {
      "measure": "u_magnitude_max",
      "op": ">=",
      "value": 1.2,
      "rationale": "Bypass jet around blade should accelerate above 1.2 m/s"
    },
    {
      "measure": "is_recirculating",
      "op": "==",
      "value": true,
      "rationale": "Downstream recirculation pocket should exist"
    }
  ]
}
```

Schema:
- `measure` — name from a fixed enum mapping to `ResultsSummary` fields: `final_time`, `cell_count`, `u_magnitude_min`, `u_magnitude_max`, `u_magnitude_mean`, `u_x_mean`, `u_x_min`, `u_x_max`, `is_recirculating`
- `op` — fixed enum: `>=`, `<=`, `==`, `>`, `<`, `!=`
- `value` — literal float or bool
- `rationale` — required free-text (drives Codex review of comparator soundness)

No expression DSL, no formulas. Engineer authors literal threshold values based on domain knowledge. Keeps the comparator easy to Codex-review and rules out class of "expression eval" security issues.

### 1.2 New expected_status: `analytical_comparator_pass`

Smoke runner behavior when expected_status == "analytical_comparator_pass":
1. Run full pipeline (import → mesh → BC → solve) — same as `converged`
2. After solve completes (with NO residual gate), call `extract_results_summary`
3. Evaluate each comparator in `analytical_comparators` array
4. Verdict = PASS iff all comparators pass; otherwise FAIL with which one(s) failed
5. Continuity error / residual values are reported but not gated

Gracefully degrade:
- If `extract_results_summary` raises (no time directory, malformed U) → verdict = FAIL with `extractor_error` reason
- If a comparator references an unknown `measure` → verdict = FAIL with `unknown_measure` (catches typos)
- If `value` type mismatches (e.g. `==` against a bool measure with a float value) → verdict = FAIL with `value_type_mismatch`

### 1.3 iter01 reclassification

Switch iter01 from `physics_validation_required` to `analytical_comparator_pass` with these comparators (rationale-driven):
- `u_magnitude_max >= 1.0` — bypass jet must accelerate (inlet is 0.8 m/s; with 4 mm gaps around an 80 mm tall blade the bypass should reach ≥1.0 m/s by continuity)
- `u_x_min < 0.0` — downstream recirculation must produce at least one cell with negative x-velocity (the wake)
- `cell_count == 7159` — meshing regression canary (locks the cell count we measured 2026-05-01)

These are loose enough to survive minor mesh/solver tweaks but tight enough to catch real physics regressions.

## Phase 2 · expand to other physics_validation_required cases (out-of-scope for this DEC)

After Phase 1 lands, sweep iter04 / iter05 / iter06 and any future cases that landed at `physics_validation_required`. Each gets its own analytical_comparator authored alongside its intent.json. This is per-case work, not framework work.

# Non-goals

- No expression DSL (`value_expr` with arithmetic) — keep comparators simple, literal values
- No new field extractors (use only the existing 9 measures from `ResultsSummary`)
- No paraview integration (existing `_parse_internal_field` is sufficient)
- No HTML/JSON report changes beyond extending the existing smoke verdict JSON

# Risk model

| risk | probability | mitigation |
|---|---|---|
| Comparator threshold drift (mesh tweak changes cell count, breaks regression canary) | medium | Author 3+ comparators per case so no single tight threshold gates the verdict; use `>=` / `<=` not `==` for derived quantities |
| Engineer authors a vacuous comparator (e.g. `u_mag_max >= 0.0`) | low | Codex review of the comparator block in PR; rationale field forces engineer to articulate domain reasoning |
| `extract_results_summary` raises on a case where solver succeeded but wrote partial output | low | Already-defensive code; surface as FAIL with extractor_error rather than crashing the smoke run |
| Float comparison ambiguity (`==` on float measure) | low | Document that `==` should only be used on boolean measures; add a smoke-runner-level warning when `==` is used on a float measure |

# Test plan

- `tools/adversarial/run_smoke.py` unit tests for the 5 comparator paths: pass / fail / unknown_measure / extractor_error / value_type_mismatch
- iter01 end-to-end smoke run with the new comparator block — should pass the 3 declared comparators, mark verdict PASS
- Backward compat: iter02-06 (currently `converged`) unchanged behavior
- Pre-push hook regex unchanged (this DEC touches `tools/adversarial/` not the regex'd hot paths)

# Codex chain expectations

self_estimated_pass_rate: 70% — Codex tends to find:
- Float comparison edge cases (`==` on floats)
- Missing input validation (does the runner crash if intent.json's `value` is a string by mistake?)
- Schema drift (multiple places define what's a valid `measure` enum)

Plan: 2-3 round chain to clean APPROVE.

# Out of scope (deliberately, for follow-up DECs)

- Multi-time-step trajectory comparators (e.g. "U_mag drops below 0.1 by t=10s") — needs richer extractor
- Surface-pressure comparators against a CSV reference — needs a new pressure parser
- Patch-level summaries (e.g. "max U on blade patch < 0.01") — needs boundary field parsing

## Closure note (2026-05-03)

### What landed

- **Phase 1.1** — `analytical_comparators` field added to `smoke_runner` block schema; extractor wiring at `tools/adversarial/comparators.py` evaluates each comparator against `ResultsSummary` fields with type-safe handling (rejects `bool` for float measures; rejects `±NaN`/`±Inf` via `math.isnan`/`math.isinf`)
- **Phase 1.2** — `analytical_comparator_pass` `expected_status` implemented in `tools/adversarial/run_smoke.py:330-365` with graceful degradation paths: `extractor_error` (extractor raises) / `unknown_measure` (typo) / `value_type_mismatch` (schema drift) / `extractor_import_failed` (cascading ModuleNotFoundError caught after Codex R10 finding 1)
- **Test coverage** — 3 R10-closure tests (`test_inf_actual_value_short_circuits_to_fail` / `test_negative_inf_actual_value_also_short_circuits` / `test_bool_actual_for_float_measure_rejected`) + 1 R11 non-blocking-comment closure test (`test_smoke_runner_lazy_import_handles_cascading_module_not_found`)
- **Implementation commits**: `742f478` (initial) → `83a74e0` (R10 closure) → `ff95b71` (R11 import-failure regression test)

### What was BLOCKED and deferred

**Phase 1.3 iter01 reclassification** — when migrating iter01 from `physics_validation_required` to `analytical_comparator_pass` with the proposed comparators (`u_magnitude_max >= 1.0`, `u_x_min < 0.0`, `cell_count == 7159`), end-to-end smoke run revealed a deeper defect: every time directory in iter01 (t=100/150/200/250) contains 21477 NaN entries. The icoFoam solver log captures the residual signal BEFORE field corruption propagates, so the "finite residual" verdict is misleading. The original DEC §Why characterized iter01's defect as "slow convergence" — empirical inspection corrected this to "solver divergence with delayed residual signal." The proposed comparator suite would correctly mark iter01 as FAIL (NaN propagation triggers `measure_inf` reject), but the underlying numerical-setup defect is out of scope for V61-106's framework-only contract.

**iter01 stays at `physics_validation_required` (SKIPPED)** with the rationale documented in `tools/adversarial/cases/iter01/intent.json:60-61` pointing at this DEC. Follow-up commit `cfb13f5` ("iter01 dt sweep") empirically disproved the CFL hypothesis and surfaces 2 deeper defects (icoFoam vs declared simpleFoam route mismatch + relaxation factor sensitivity); both are queued for a follow-up DEC.

**Phase 2 (sweep iter04/iter05/iter06)** explicitly remains out-of-scope per §Phase 2.

### Codex chain summary

- **R10** (commit `742f478`): CHANGES_REQUIRED · 2 valid findings (cascading import failure + bool/Inf type-guard gap)
- **R10 closure** (commit `83a74e0`): both findings closed inline + 3 new tests
- **R11** (commit `83a74e0`): APPROVE_WITH_COMMENTS · 0 blocking findings · 1 non-blocking comment (no smoke-level regression for `extractor_import_failed`)
- **R11 closure** (commit `ff95b71`): non-blocking comment closed via cascading-ModuleNotFoundError regression test

Self-pass-rate calibration: estimated 70% at DEC authoring; actual outcome 1 round of substantive CHANGES_REQUIRED before clean APPROVE — estimate was reasonable.

### Acceptance criteria status

- §Phase 1 framework (1.1 + 1.2) — **MET**
- §Phase 1.3 iter01 reclassification — **BLOCKED + DEFERRED** to follow-up DEC for numerical-setup fix
- §Phase 2 expand to other physics_validation_required cases — **OUT OF SCOPE per §Phase 2**

### Codex review re-trigger judgment (2026-05-03 closure-only commit)

This closure commit is docs-only (DEC body + frontmatter status flip); none of the RETRO-V61-001 risk-tier triggers fire (not multi-file frontend, not API contract, not solver, not foam_agent_adapter, not new geometry, not phase E2E batch ≥3 fail, not Docker+OpenFOAM). No new Codex review required for the closure commit itself; the implementation chain (R10→R11→post-comment closure) already cleared APPROVE_WITH_COMMENTS.
