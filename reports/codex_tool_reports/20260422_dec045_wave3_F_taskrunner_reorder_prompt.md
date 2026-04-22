# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 3 Invocation F — TaskRunner reorder + expected_verdict recompute"
    contract: Notion DEC-V61-045
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (B1)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-002)
    depends_on:
      - 61c7cd1 (Wave 1 A): Thresholds + attest signature w/ execution_result
      - 396cefe (Wave 2 D): HAZARD tier in _derive_contract_status + U_ref plumb
      - ad0bad2 (Wave 2 E): tests guard HAZARD tier

    scope_tracks:
      - Track 3 (CA-002): Move attestor pre-extraction in TaskRunner.run_task()
      - Track 5 (B1): Recompute expected_verdict in _audit_fixture_doc after all concerns stamped

    allowed_files:
      - src/task_runner.py                   (Track 3 primary)
      - src/models.py                        (RunReport schema extension for attestation field)
      - scripts/phase5_audit_run.py          (Track 5 primary)

    read_only_context:
      - src/convergence_attestor.py (Wave 1 A + 2 state; attest signature + AttestationResult)
      - src/comparator_gates.py (Wave 1 B state)
      - ui/backend/services/validation_report.py (_derive_contract_status reuse target)
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (B1 evidence)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-002 evidence)

    forbidden_files:
      - ui/backend/** (except as read-only context)
      - tests/** and ui/backend/tests/** (separate Codex G invocation)
      - knowledge/** (hard-floor 1 protection)
      - src/comparator_gates.py (already Wave 1 B landed; do not re-edit)
      - src/convergence_attestor.py (already Wave 1 A landed)

    autonomy: TOOL-SCOPE

---

## Track 3: Attestor pre-extraction in TaskRunner

### Current state (src/task_runner.py:98-153)

```python
def run_task(self, task_spec: TaskSpec) -> RunReport:
    # 1. Execute CFD
    exec_result = self._executor.execute(task_spec)

    # 2. Load gold
    gold = self._db.load_gold_standard(task_spec.name)
    comparison = None; correction = None

    # 3. Compare (BEFORE attestor — this is the bug)
    if gold is not None and exec_result.success:
        comparison = self._comparator.compare(exec_result, gold)
        if not comparison.passed:
            correction = self._recorder.record(task_spec, exec_result, comparison)
            ...

    # 5. Post-execute hook
    # 6. Summary
    # 7. Notion write

    return RunReport(...)
```

**Bug (Codex DEC-038 CA-002)**: comparator + correction run BEFORE attestor. A run that never physically converged still flows through scalar extraction + correction generation. "Attestor first" contract violated.

### Required fix

Reorder to: execute → **attest** → (if ATTEST_FAIL: short-circuit) → compare → correct.

```python
def run_task(self, task_spec: TaskSpec) -> RunReport:
    # 1. Execute CFD
    exec_result = self._executor.execute(task_spec)

    # 2. NEW: Attest convergence (pre-extraction)
    from .convergence_attestor import attest  # import here to avoid top-level cycle
    attestation = self._compute_attestation(exec_result, task_spec)  # returns AttestationResult
    # attestation may be ATTEST_PASS / ATTEST_HAZARD / ATTEST_FAIL / ATTEST_NOT_APPLICABLE

    # 3. Load gold
    gold = self._db.load_gold_standard(task_spec.name)
    comparison = None; correction = None

    # 4. Compare (only if attestor didn't FAIL — semantically: a non-converged
    #    run shouldn't produce a "measurement" since the solver state is suspect.
    #    HAZARD tier still allows comparison to proceed for diagnostic value.)
    if gold is not None and exec_result.success and attestation.overall != "ATTEST_FAIL":
        comparison = self._comparator.compare(exec_result, gold)
        if not comparison.passed:
            correction = self._recorder.record(task_spec, exec_result, comparison)
            ...

    # ... rest unchanged ...

    return RunReport(
        ...,
        attestation=attestation,  # NEW field
    )
```

New helper `_compute_attestation(self, exec_result, task_spec) -> AttestationResult`:

```python
def _compute_attestation(self, exec_result: ExecutionResult, task_spec: TaskSpec) -> "AttestationResult":
    """Run convergence attestor against the solver log. Handles missing log
    gracefully (returns ATTEST_NOT_APPLICABLE).

    Feeds execution_result to A1 so exit code is considered alongside log markers.
    case_id (task_spec.name) enables per-case threshold overrides from YAML.
    """
    from .convergence_attestor import attest

    log_path = self._resolve_log_path(exec_result)  # helper to find log.* under raw_output_path
    try:
        return attest(
            log_path=log_path,
            execution_result=exec_result,
            case_id=task_spec.name,
        )
    except Exception:
        logger.exception("Attestation failed; returning NOT_APPLICABLE")
        # Fail-safe: bad attestor call must NOT kill the whole task run
        from .convergence_attestor import AttestationResult
        return AttestationResult(overall="ATTEST_NOT_APPLICABLE", checks=[])

def _resolve_log_path(self, exec_result: ExecutionResult) -> Optional[Path]:
    """Find the solver log.* file under raw_output_path. Returns None if
    raw_output_path is missing or no log.* exists."""
    if not exec_result.raw_output_path:
        return None
    base = Path(exec_result.raw_output_path)
    if not base.is_dir():
        return None
    log_files = sorted(base.glob("log.*"))
    return log_files[-1] if log_files else None
```

### RunReport schema extension (src/models.py)

Add `attestation: Optional["AttestationResult"] = None` to `RunReport` dataclass.

Importantly: **keep backward compat**. Callers that don't access `.attestation` (UI, Notion writer, etc.) are unaffected. New UI code can opt-in to read it.

Avoid circular imports: use `TYPE_CHECKING` or lazy import for AttestationResult type annotation.

### Behavioral contract (new)

- `attestation is not None` always when `exec_result.success and raw_output_path is populated`
- `attestation.overall == "ATTEST_FAIL"` short-circuits comparator + correction generation; `comparison=None`, `correction=None`
- `attestation.overall == "ATTEST_HAZARD"` does NOT short-circuit; comparator still runs (physics scientist may want to see the numbers even if convergence is suspect)
- `attestation.overall == "ATTEST_PASS"` / "ATTEST_NOT_APPLICABLE": full pipeline runs as today

---

## Track 5: expected_verdict recompute in `_audit_fixture_doc`

### Current state (scripts/phase5_audit_run.py:481-487 region)

```python
verdict_hint = _compute_expected_verdict(
    gold=gold,
    comparator_report=report.comparison_result,
    extraction_source=extraction_source,
    value=value,
    audit_concerns=audit_concerns,
)
# verdict_hint written into doc["run_metadata"]["expected_verdict"]
# THEN attestor + gates run AFTER this assignment, appending more concerns
# but verdict_hint is NEVER recomputed.
```

**Bug (Codex DEC-036b B1)**: The fixture metadata and CLI print (`scripts/phase5_audit_run.py:748 verdict = doc["run_metadata"]["expected_verdict"]`) show stale PASS even after attestor/gates hard-fail concerns are appended.

### Required fix

After all concerns (attestor + G1-G5 + U_REF_UNRESOLVED + comparator_deviation) have been appended, recompute the final verdict using the same `_derive_contract_status` helper used by the backend:

```python
# At the end of _audit_fixture_doc, just before the return:

# DEC-V61-045 Track 5 / Codex DEC-036b B1 remediation:
# Recompute verdict using _derive_contract_status after ALL concerns (attestor,
# gates, U_ref WARN, comparator deviations) have been stamped. This replaces
# the early-bird `verdict_hint` computed before gates ran.
from ui.backend.services.validation_report import _derive_contract_status
from ui.backend.schemas.validation import (
    AuditConcern as _AC, MeasuredValue as _MV, Precondition as _P,
    GoldStandardReference as _GSR,
)
# Convert the locally-assembled dicts into the pydantic shapes _derive needs
gs_ref = _GSR(
    quantity=<gold quantity>,
    ref_value=<gold ref_value>,
    tolerance_pct=<gold tolerance_pct>,
    citation=<gold citation or "">,
)
m = _MV(
    value=value,   # may be None for MISSING_TARGET_QUANTITY hard-fail
    source=extraction_source,
    quantity=<quantity from doc>,
) if value is not None or extraction_source else None
concerns_pyd = [_AC(**c) for c in audit_concerns]
preconditions_pyd = [_P(**p) for p in preconditions]  # if preconditions list exists
final_status, *_ = _derive_contract_status(gs_ref, m, preconditions_pyd, concerns_pyd)
doc["run_metadata"]["actual_verdict"] = final_status   # NEW field
doc["run_metadata"]["expected_verdict"] = final_status  # OVERWRITE stale hint with recomputed
```

**Key constraint**: `expected_verdict` field name must NOT change (backward compat for downstream fixture consumers). The field VALUE becomes the recomputed verdict. `actual_verdict` is a new alias field for clarity.

Alternative approach (simpler): skip the type-conversion dance and construct a minimal mock of what `_derive_contract_status` needs via `types.SimpleNamespace` or similar. If clean conversion is complex, this is acceptable.

### Integration with Track 3

Now that TaskRunner runs attestor pre-extraction, report.comparison_result may be None when attestor FAIL short-circuits. _audit_fixture_doc must handle `comp is None` gracefully — this was already handled in existing code, but verify the new short-circuit path works.

Additionally: if `report.attestation` is available on the RunReport (Track 3), surface `attestation.overall` and `attestation.concerns` into doc so the fixture records both layers.

---

## Acceptance Checks

### Track 3 (TaskRunner)

CHK-1: `run_task(task_spec)` on an ATTEST_PASS log returns RunReport with `report.attestation.overall == "ATTEST_PASS"` and `report.comparison_result != None` (assuming gold + success).

CHK-2: `run_task(task_spec)` on an ATTEST_FAIL log (e.g., FOAM FATAL): returns RunReport with `report.attestation.overall == "ATTEST_FAIL"` AND `report.comparison_result == None` (comparator short-circuited).

CHK-3: `run_task(task_spec)` on ATTEST_HAZARD log: returns RunReport with `report.attestation.overall == "ATTEST_HAZARD"` AND `report.comparison_result != None` (HAZARD does NOT short-circuit).

CHK-4: Existing RunReport consumers (Notion writer, post-execute hook, AutoVerifier, tests that access `.comparison_result`, `.correction_spec`) work unchanged. Mock a minimal caller that accesses `report.task_spec.name` + `report.execution_result` + `report.comparison_result` — should not break.

CHK-5: When `raw_output_path` is None or nonexistent → attestation.overall == "ATTEST_NOT_APPLICABLE", task continues normally (comparator runs as before).

### Track 5 (verdict recompute)

CHK-6: Synthetic case: gold_value=10, tolerance=5%, measurement.value=10.5 (in-band), audit_concerns=[{"concern_type": "CONTINUITY_NOT_CONVERGED", ...}]. Before Track 5: verdict_hint="PASS" (stale). After Track 5: expected_verdict in fixture is "HAZARD".

CHK-7: Synthetic case with VELOCITY_OVERFLOW in audit_concerns + in-band scalar → expected_verdict="FAIL" (hard-fail takes precedence).

CHK-8: Clean case no concerns + in-band measurement → expected_verdict="PASS" (regression guard — Track 5 doesn't break clean cases).

CHK-9: CLI print at phase5_audit_run.py:748 now shows the RECOMPUTED verdict, not the pre-gates hint.

### Overall

CHK-10: Full pytest suite on `.venv/bin/python -m pytest ui/backend/tests/ -q` passes with no new failures. (Codex: run this if sandbox permits via `.venv/bin/python`; else static verification.)

CHK-11: No fixture expected_verdict flips beyond HAZARD tier logic from Wave 2. If any existing PASS→FAIL or FAIL→PASS flip happens, that indicates a regression — document each such case.

## Reject Conditions

REJ-1: Edits outside allowed_files.
REJ-2: Changing the name of `RunReport.comparison_result` or `.correction_spec`.
REJ-3: Breaking backward compat for any existing RunReport consumer (test it).
REJ-4: Removing the `expected_verdict` field from fixtures (rename OK only if all 10 fixture files updated in lockstep, which is NOT in scope — don't do it).
REJ-5: Introducing a hard `from src.convergence_attestor import ...` at top of `src/task_runner.py` if it causes a circular import. Use lazy import inside methods.
REJ-6: Making Track 3 short-circuit on ATTEST_HAZARD (only FAIL short-circuits).
REJ-7: Changing the `_compute_expected_verdict` helper's API or name (only the call site at end of _audit_fixture_doc is edited).

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 3 F

## Files modified
- src/task_runner.py [+N/-M]
- src/models.py [+N/-M]
- scripts/phase5_audit_run.py [+N/-M]

## Changes summary
- Track 3: attestor pre-extraction + short-circuit on ATTEST_FAIL + RunReport schema
- Track 5: verdict recompute using _derive_contract_status

## Acceptance checks self-verified
- CHK-1..11: PASS/FAIL + evidence

## Backward-compat test
- RunReport schema change summary + any caller that would break + mitigation

## Fixture impact forecast
- "After phase5_audit_run.py --all regenerates fixtures, which files will
  have expected_verdict flipped from PASS/HAZARD → FAIL or vice versa?"
- List, but DO NOT regenerate fixtures in this invocation.

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
