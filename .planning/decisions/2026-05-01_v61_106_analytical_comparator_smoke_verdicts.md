---
decision_id: DEC-V61-106
title: Analytical-comparator smoke verdicts — let adversarial cases declare physics-correctness checks the residual-only smoke runner can't catch
status: Proposed (2026-05-01 · authored under user direction "全权授予你开发，全都按你的建议来" after DEC-V61-104 Phase 1.5 closure exposed iter01's actual defect class — slow convergence + need for qualitative physics validation, not obstacle subtraction failure)
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
codex_tool_report_path: (TBD — runs after implementation)
notion_sync_status: pending (project rules say sync after acceptance; sync after Codex chain closes)

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
