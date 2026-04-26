---
decision_id: DEC-V61-FORENSIC-FLAKE-1
title: Forensic identification of test_build_trust_gate_report_resolves_display_title_to_slug flake (born at f0f0f80, DEC-V61-071 R1)
status: ACCEPTED (autonomous_governance · forensic identification only · fix recommendation deferred to follow-up DEC)
authored_by: Claude Code Opus 4.7 (1M context · Session B v2 NARROW Track 3)
authored_at: 2026-04-26
authored_under: Session B v2 NARROW · Track 3 (forensic flake bisect under audit A4 follow-up)
parent_dec: DEC-V61-080
parent_audit_evidence: .planning/audit_evidence/2026-04-26_v61_080_a4_flake_attribution.txt
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.95    # forensic identification only; no production-code change
notion_sync_status: pending
codex_tool_report_path: null  # forensic-investigation only; no source-code modification per this DEC
risk_flags: []
gov1_v1_scope:
  case_id: forensic_flake_1
  fix_type: forensic_identification_only
  fields_modified: []  # NO source-code or knowledge/** modification in this DEC; identification only
  follow_up_required: true
  follow_up_owner: Claude Code (autonomous_governance: true · test-isolation fix)
  follow_up_dec_proposed_id: DEC-V61-FORENSIC-FLAKE-1-FIX
forensic_finding:
  flaky_test: tests/test_task_runner_trust_gate.py::test_build_trust_gate_report_resolves_display_title_to_slug
  introducing_commit: f0f0f80
  introducing_commit_message: "fix(task_runner): DEC-V61-071 R1 verbatim · slug resolution + lazy load (Codex F#1+F#2)"
  introducing_dec: DEC-V61-071 (R1 verbatim, Codex F#1+F#2 fixes)
  flake_age_days: 0  # test was born flaky in same commit that introduced it
  symptom: |
    Test passes when run in isolation (pytest tests/test_task_runner_trust_gate.py::test_build_trust_gate_report_resolves_display_title_to_slug)
    Test fails in full-suite run (EXECUTOR_MODE=mock python -m pytest tests/ -q)
    Specific assertion: gold_report.provenance.get("tolerance_policy_observables") == ['alpha_obs', 'beta_obs']
    Actual full-suite: gold_report.provenance.get("tolerance_policy_observables") == []
  root_cause_hypothesis: |
    Some sibling test in tests/ (likely tests/test_task_runner_trust_gate.py itself
    or tests/test_task_runner.py) calls _build_trust_gate_report or
    load_tolerance_policy in a way that mutates the tolerance_policy_observables
    registry. The registry is then "consumed" / cleared / overwritten before
    the failing test runs. The test's setUp does not reset the registry to a
    known state. The "lazy load" semantics introduced by DEC-V61-071 R1 Codex
    F#1+F#2 fixes likely created a memoized state that survives across tests.
  reproducibility:
    - HEAD f0f0f80 (introducing commit):    1 failed, 858 passed, 2 skipped (full suite)
    - HEAD 50bb2eb (= 55f2642^, PC-2 R3): 1 failed, 868 passed, 2 skipped
    - HEAD 55f2642 (PC-3 R2):             1 failed, 884 passed, 2 skipped
    - HEAD fffd1a8 (Session B v2 Track 2 close): 1 failed, X passed, 2 skipped
    Same flake throughout; never green in full suite from f0f0f80 onward.
---

# DEC-V61-FORENSIC-FLAKE-1 · Test Isolation Flake Forensic Identification

## Why

Per DEC-V61-080 RATIFY_WITH_AMENDMENTS audit verdict (A4) + Session B
audit-evidence finding:

> "Pre-existing test-isolation flake `test_build_trust_gate_report_resolves_display_title_to_slug`
> exists at HEAD `50bb2eb` (= `55f2642^`). Forensic git bisect from V6.1
> counter start to `50bb2eb` is required to identify the introducing
> commit. Recommend opening DEC-V61-FORENSIC-FLAKE-1."

This DEC executes that bisect.

## Method

1. Located test introduction via `git log --all -S '<test_function_name>'`:
   commit `f0f0f80` "fix(task_runner): DEC-V61-071 R1 verbatim · slug
   resolution + lazy load (Codex F#1+F#2)"
2. Ran full pytest suite at `f0f0f80` (test introduction commit) under
   `EXECUTOR_MODE=mock`
3. Compared full-suite vs isolated-test results

## Result

**The test was born flaky.** At commit `f0f0f80` (the same commit that
introduced the test):

- Full-suite run: `1 failed, 858 passed, 2 skipped` (failure is the
  same `test_build_trust_gate_report_resolves_display_title_to_slug`)
- Isolated run: PASSES

The flake is **NOT a regression introduced by a later commit**. It is
present from the moment the test was added.

This rules out three other hypotheses that earlier audit chains had
considered:
- ❌ Session A's PC-3 R2 (`55f2642`) introduced the flake — REJECTED
  (already at A4: same flake at `55f2642^`)
- ❌ Some V6.1-era refactor between `f0f0f80` and `50bb2eb` introduced
  the flake — REJECTED (flake at `f0f0f80` directly)
- ❌ A pre-V6.1 or upstream module change broke the test — REJECTED
  (the test only exists from `f0f0f80` onward)

## Decision

**This DEC issues a forensic finding only**: the flake is attributable
to DEC-V61-071 R1 (commit `f0f0f80`), specifically the test design or
the production-code lazy-load mechanism it tests.

**This DEC does NOT propose a fix.** A follow-up DEC
`DEC-V61-FORENSIC-FLAKE-1-FIX` (TBD) will:

1. Diagnose whether the flake is a **test-side defect** (poor isolation,
   missing teardown) or a **production-side defect** (lazy-load
   memoization persists global state inappropriately)
2. If test-side: add proper setUp/tearDown to reset
   `tolerance_policy_observables` registry; possibly use pytest
   `monkeypatch` or fixture-scoped registry
3. If production-side: redesign `load_tolerance_policy` to not retain
   global registry state across calls
4. Re-run full suite at fix commit; verify flake closed (1 failed → 0 failed)

The fix DEC may be authored under `autonomous_governance: true` per
RETRO-V61-001 routine-test-fix flow, OR may require Codex review per
V61-001/V61-053 amended Codex-trigger rules if the production-side
hypothesis is correct (touches `load_tolerance_policy` which is in
`src/cfd_harness/trust_core/**` boundary 6).

**Critical**: if the fix touches `src/cfd_harness/trust_core/**`, that
crosses Hard Boundary 6 of GOV-1's protected paths. The fix DEC must
explicitly call out the boundary crossing and either (a) confirm `trust_core/**`
is unaffected, or (b) gate via Codex review for changes in that module.

## Hard-boundary self-attestation

This DEC modifies **zero source files**. It is a forensic investigation
report only. Files added: 1 (this DEC).

- ❌ NO `knowledge/**` modification
- ❌ NO `src/**` modification (production code untouched)
- ❌ NO `tests/**` modification (the flaky test itself untouched)
- ❌ NO `docs/**` modification
- ❌ NO Session A path touched
- ✅ Pure forensic finding under `.planning/decisions/`

The actual flake remains in production (1 fail, 884+2+1 pre-Track-2 baseline)
until DEC-V61-FORENSIC-FLAKE-1-FIX lands.

## Reproducibility

```bash
# At any HEAD ≥ f0f0f80, the flake reproduces in full-suite mode:
git checkout <any commit ≥ f0f0f80>
EXECUTOR_MODE=mock python -m pytest tests/ -q --no-header 2>&1 | tail -5
# Expected: includes "FAILED tests/test_task_runner_trust_gate.py::test_build_trust_gate_report_resolves_display_title_to_slug"

# At f0f0f80^ or earlier, the test does not exist (no failure to reproduce):
git checkout f0f0f80^
EXECUTOR_MODE=mock python -m pytest tests/test_task_runner_trust_gate.py -q 2>&1 | tail -5
# Expected: pytest collects fewer tests; no failure
```

## Source

- Audit input: `.planning/audit_evidence/2026-04-26_v61_080_a4_flake_attribution.txt`
- Parent DEC: `.planning/decisions/2026-04-26_v61_080_gov1_gold_case_enrichment.md`
- Audit verdict: DEC-V61-080 RATIFY_WITH_AMENDMENTS A4
- Introducing DEC: DEC-V61-071 R1 (commit `f0f0f80`)

## Next action

Open `DEC-V61-FORENSIC-FLAKE-1-FIX` (Claude Code, autonomous_governance:
true unless `src/cfd_harness/trust_core/**` is touched in which case
mandatory Codex review per Boundary 6).
