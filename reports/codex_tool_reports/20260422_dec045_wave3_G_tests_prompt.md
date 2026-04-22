# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 3 Invocation G — tests for attestor-first TaskRunner + verdict recompute"
    contract: Notion DEC-V61-045
    depends_on:
      - 5433e20 Wave 3 F (TaskRunner reorder + verdict recompute)

    scope: Add test coverage for Track 3 (TaskRunner attestor-first) + Track 5
    (expected_verdict recompute). Do NOT modify existing tests unless required
    by new RunReport.attestation field.

    allowed_files:
      - tests/test_task_runner.py                         (if exists; else create)
      - tests/test_auto_verifier/test_task_runner_integration.py   (existing — read, minimal touches)
      - ui/backend/tests/test_convergence_attestor.py     (integration with _audit_fixture_doc)

    read_only_context:
      - src/task_runner.py (post-Wave-3-F state)
      - src/models.py (ExecutionResult.exit_code new field; RunReport.attestation new field)
      - scripts/phase5_audit_run.py (verdict recompute site)
      - src/convergence_attestor.py
      - reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md

    forbidden_files:
      - src/** (already landed)
      - knowledge/**
      - scripts/phase5_audit_run.py

    autonomy: TOOL-SCOPE

---

## Tests to add

### Track 3 (TaskRunner attestor-first) — in `tests/test_task_runner.py`

1. **test_run_task_attestor_pass_path_completes_pipeline**: Build a mock TaskRunner (mock executor returning ExecutionResult with raw_output_path pointing to a tmp dir containing a synthetic clean `log.simpleFoam`). Call `run_task(mock_spec)`. Assert:
   - `report.attestation.overall == "ATTEST_PASS"`
   - `report.comparison_result is not None` (if gold_standard available via mocked _db)
   - Pipeline runs to completion

2. **test_run_task_attestor_fail_short_circuits_comparator**: Same setup but synthetic log contains `FOAM FATAL ERROR`. Assert:
   - `report.attestation.overall == "ATTEST_FAIL"`
   - `report.comparison_result is None`
   - `report.correction_spec is None`

3. **test_run_task_attestor_hazard_does_not_short_circuit**: Synthetic log with final `sum_local = 5e-4` (A2 HAZARD tier). Assert:
   - `report.attestation.overall == "ATTEST_HAZARD"`
   - `report.comparison_result is not None` (HAZARD does not short-circuit)

4. **test_run_task_attestor_not_applicable_when_no_log**: ExecutionResult.raw_output_path = None. Assert:
   - `report.attestation.overall == "ATTEST_NOT_APPLICABLE"`
   - Pipeline runs normally (compare if gold exists, etc.)

5. **test_run_task_attestor_not_applicable_when_raw_output_nonexistent**: raw_output_path = "/nonexistent/dir/xxx". Assert same as above.

6. **test_runreport_attestation_field_optional**: RunReport created without attestation kwarg still works (default None), ensures backward compat for any caller not yet updated.

7. **test_run_batch_blocks_backdoor_comparison_on_attest_fail**: Use `run_batch([case])` where case has ATTEST_FAIL log. Verify that `_ensure_batch_comparison()` does NOT fabricate a comparison on top of failed attestation.

### Track 5 (verdict recompute) — in `ui/backend/tests/test_convergence_attestor.py`

8. **test_audit_fixture_doc_recomputes_expected_verdict_to_hazard** (synthetic): Build a minimal `report` via SimpleNamespace with:
   - `comparison_result` carrying an in-band deviation
   - `execution_result.raw_output_path` pointing to a tmp dir with an A2-hazard log
   - `task_spec` = simple dict or None
   
   Call `_audit_fixture_doc(case_id="lid_driven_cavity", report, commit_sha="deadbee")`. Assert:
   - `doc["run_metadata"]["expected_verdict"] == "HAZARD"` (not PASS — recompute works)
   - `doc["run_metadata"]["actual_verdict"] == "HAZARD"`

9. **test_audit_fixture_doc_recomputes_to_fail_on_hard_concern**: Same setup but synthetic log has FOAM FATAL → A1 fires → HARD_FAIL. Assert `expected_verdict == "FAIL"`.

10. **test_audit_fixture_doc_clean_run_stays_pass_regression**: No concerns + in-band measurement. Assert `expected_verdict == "PASS"` (Track 5 doesn't break clean cases).

### Minimal existing-test touches

If `tests/test_task_runner.py::test_run_task_full_pipeline` or similar previously asserted `report.attestation` didn't exist (e.g., negative assertions like `not hasattr(report, 'attestation')`), update to allow the new field. Otherwise NO existing test changes.

## Acceptance Checks

CHK-1: All 7 new TaskRunner tests + 3 new audit_fixture_doc tests PASS locally via `.venv/bin/python -m pytest tests/test_task_runner.py ui/backend/tests/test_convergence_attestor.py -q`.

CHK-2: No existing test broken. Full `ui/backend/tests/ + tests/test_task_runner.py + tests/test_auto_verifier/` suite passes.

CHK-3: No fixture file edits.

## Reject Conditions

REJ-1: Edits outside allowed_files.
REJ-2: Mocking src/ code (stub at executor/db/comparator boundaries instead).
REJ-3: Changes that break Wave 1+2+3 F landed code.
REJ-4: Any network dependency in tests.
REJ-5: Using real OpenFOAM (all logs synthetic).

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 3 G

## Files modified
- tests/test_task_runner.py [+N/-M]  (or NEW)
- ui/backend/tests/test_convergence_attestor.py [+N/-M]

## Tests added
- per-test one-liner

## Existing tests touched
- file:line — what + why (expected: minimal)

## Self-verified
- CHK-1..3 results

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
