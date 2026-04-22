# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 2 Invocation E — tests for HAZARD tier + U_ref plumb"
    contract: Notion DEC-V61-045 PROPOSAL
    depends_on:
      - Wave 2 D landed (HAZARD tier in _derive_contract_status + U_ref plumb in _audit_fixture_doc)

    scope: Add test coverage for Wave 2 D changes. Do NOT modify existing
    tests unless their old expectations break from the new HAZARD tier
    semantics. For existing fixtures that flip PASS→HAZARD under the new
    logic, update expected_verdict with a one-line comment citing DEC-045
    Wave 2.

    allowed_files:
      - ui/backend/tests/test_validation_report.py
      - ui/backend/tests/test_convergence_attestor.py (for attest+verdict integration tests)
      - ui/backend/tests/fixtures/**.yaml (ONLY if fixtures flip PASS→HAZARD and that's the correct new behavior per DEC-045)

    read_only_context:
      - ui/backend/services/validation_report.py (post-D state)
      - scripts/phase5_audit_run.py (post-D state)
      - reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md

    forbidden_files:
      - src/** (already Wave 1 landed; don't re-touch)
      - knowledge/gold_standards/** (hard-floor 1)
      - any fixture file that represents genuine FAIL/PASS golden expectations
        unless you can justify the flip per Wave 2 spec

    autonomy: TOOL-SCOPE

---

## Tests to add

### In `ui/backend/tests/test_validation_report.py`

Import context:
```python
from ui.backend.services.validation_report import _derive_contract_status
from ui.backend.schemas.validation import (
    AuditConcern, GoldStandardReference, MeasuredValue, Precondition,
)
```

1. **test_hazard_tier_continuity_not_converged_forces_hazard**: in-band measurement + audit_concerns=[AuditConcern(concern_type="CONTINUITY_NOT_CONVERGED")]. Call `_derive_contract_status`. Assert status=="HAZARD", within_tolerance is None (not True), deviation_pct present.

2. **test_hazard_tier_residuals_above_target_forces_hazard**: same pattern with RESIDUALS_ABOVE_TARGET.

3. **test_hazard_tier_bounding_recurrent_forces_hazard**: same with BOUNDING_RECURRENT.

4. **test_hazard_tier_no_residual_progress_forces_hazard**: same with NO_RESIDUAL_PROGRESS.

5. **test_hard_fail_precedes_hazard_tier**: audit_concerns=[VELOCITY_OVERFLOW (hard-FAIL), CONTINUITY_NOT_CONVERGED (HAZARD-tier)]. Assert status=="FAIL" (hard-FAIL wins).

6. **test_no_concerns_in_band_stays_pass_regression**: clean measurement + no concerns + in-band → PASS. Guards against accidental HAZARD regression.

7. **test_hazard_tier_out_of_band_still_hazard**: in-band HAZARD concern trumps out-of-band silent-pass path. If a new tier interacts with existing SILENT_PASS_HAZARD, verify the final status is HAZARD not FAIL (unless hard-FAIL present).

### In `ui/backend/tests/test_convergence_attestor.py` (augment if needed)

8. **test_attest_and_verdict_integration_continuity_hazard**: end-to-end:
   - synthetic log with final `sum_local=5e-4` (> A2 1e-4 floor, < G5 1e-2)
   - `attest(log, case_id="lid_driven_cavity")` returns ATTEST_HAZARD with A2 concern
   - pass those concerns to `_derive_contract_status` with in-band measurement
   - assert final verdict = HAZARD

### For U_ref plumb (new file OR add to existing)

Recommend adding to `ui/backend/tests/test_phase5_audit_run.py` if it exists, else to `test_comparator_gates_g3_g4_g5.py`. Check which test file imports from `scripts.phase5_audit_run` — only if such a file already exists without hitting the `notion_client` import chain (if all existing scripts.phase5_audit_run tests are already broken by notion_client import error, skip this subsection and DOCUMENT in output report).

9. **test_resolve_u_ref_lid_driven_cavity**: `_resolve_u_ref(task_spec, "lid_driven_cavity")` returns (1.0, True).

10. **test_resolve_u_ref_backward_facing_step**: returns (44.2 or whatever) + True.

11. **test_resolve_u_ref_unknown_case_fallback**: returns (1.0, False).

12. **test_audit_fixture_doc_stamps_u_ref_unresolved_warn**: for unknown case, check that audit_concerns contains entry with concern_type=="U_REF_UNRESOLVED".

### Fixture update policy

If the new HAZARD tier logic flips any fixture file's `expected_verdict` from PASS to HAZARD, update the fixture file with:
```yaml
expected_verdict: HAZARD  # Was PASS pre-DEC-045 Wave 2; flipped per CA-001 fix
                         # (A2/A3/A5/A6 concerns now force HAZARD not PASS).
```

If a fixture previously had expected_verdict=PASS and now internally computes HAZARD, the fixture must be updated (or the test is broken). Document each such fixture in the output report.

**DO NOT flip FAIL→HAZARD or HAZARD→FAIL** — only PASS→HAZARD is permitted via this DEC. Any other flip indicates a regression.

## Acceptance Checks

CHK-1: All 7 new test_validation_report tests PASS locally (Codex verifies via pytest if sandbox permits, else marks "static").

CHK-2: Integration test (#8) PASSes.

CHK-3: U_ref tests #9-12 either PASS or are documented as "skipped due to notion_client import chain" with rationale.

CHK-4: Any fixture file edits documented with before/after expected_verdict + justification per fixture.

CHK-5: No existing test deleted.

## Reject Conditions

REJ-1: Edit outside allowed_files.
REJ-2: Modify fixture expected_verdict from FAIL to HAZARD or HAZARD to FAIL (only PASS→HAZARD allowed).
REJ-3: Add pyproject dependencies.
REJ-4: Implement Wave 3 or Wave 4 scope.

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 2 E

## Files modified
- ui/backend/tests/test_validation_report.py [+N/-M]
- ui/backend/tests/test_convergence_attestor.py [+N/-M]
- ui/backend/tests/fixtures/<case>.yaml  (if flipped + justified)

## Tests added
- per-test one-liner

## Fixture updates
- path: expected_verdict before → after + justification

## Existing tests touched
- file:line — what + why

## Self-verified
- CHK-1..5

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
