# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 4 Invocation H — A6 outer-iter semantics + per-case promote_to_fail"
    contract: Notion DEC-V61-045 (Final Wave)
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-005 full: A6 field-agnostic + per-inner-solve counting; impinging_jet A6 spurious)
    depends_on:
      - All Waves 1-3 landed (through 8d9a74a)

    scope_tracks:
      - Track 8 (CA-005 full): Redesign A6 to use outer-iteration (first-solve-per-Time=) residuals
      - Track 2 extension: Wire per-case promote_to_fail from YAML into _derive_contract_status

    allowed_files:
      - src/convergence_attestor.py                        (Track 8 primary — A6 redesign)
      - ui/backend/services/validation_report.py           (Track 2 extension — promote_to_fail wiring)
      - ui/backend/tests/test_convergence_attestor.py      (A6 tests)
      - ui/backend/tests/test_validation_report.py         (promote_to_fail tests)

    read_only_context:
      - knowledge/attestor_thresholds.yaml  (promote_to_fail field already defined, currently [] for all cases)
      - reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantFoam (real test case)
      - reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam (regression guard)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-005 evidence)

    forbidden_files:
      - knowledge/** (tolerance & hard-floor protection)
      - scripts/** (Wave 3 landed)
      - src/comparator_gates.py (Wave 1 B landed)
      - src/task_runner.py (Wave 3 F landed)

    autonomy: TOOL-SCOPE

---

## Track 8: A6 outer-iteration semantics redesign

### Problem (Codex DEC-038 CA-005 full)

Current A6 at `src/convergence_attestor.py:413+` reads every `Initial residual` line per field across every inner PBiCGStab/GAMG solve. In multi-corrector PIMPLE or buoyantFoam coupled runs, each Time= block has many inner solves per field. When residuals repeat across inner solves within a single outer step, the algorithm misinterprets this as "stuck" when actually it's normal inner-loop behavior.

**Symptom on real impinging_jet log**: A6 fires HAZARD on p_rgh (0.07 decades across ~50 inner-solve lines), contradicting DEC-038 expectation that impinging_jet fails only via A4, not A6.

### Required fix

Redesign A6 to count OUTER iteration residuals only:

```python
def _parse_outer_iteration_residuals(log_path: Path) -> dict[str, list[float]]:
    """Return per-field sequence of outer-iteration Initial residuals.

    Logic: iterate through log lines. Recognize block boundaries via
    `^Time = N\n` markers. Within each Time= block, the FIRST
    `Solving for <field>, Initial residual = X, ...` line per field is
    the outer-iteration residual (outer-step initial guess). Subsequent
    `Solving for <field>, Initial residual = Y` lines within the same
    block are INNER corrector passes — exclude them.

    Handles:
    - simpleFoam: 1 outer iteration per Time block → 1 residual per field
    - pimpleFoam/buoyantFoam: N outer correctors + M inner — use only the
      first per-field entry of each Time= block
    - laminar runs: no turbulence fields present → silently omit them
    """
```

Then rewrite `_check_a6_no_progress`:
- Use `_parse_outer_iteration_residuals()` instead of `_parse_residual_timeline()`
- Window: last `thresholds.no_progress_window` Time= blocks per field
- Criterion: `decade_range = log10(max/min)` over the window
- FAIL only when `decade_range <= thresholds.no_progress_decade_frac` (preserving CA-006 boundary)
- If `< 2` outer iterations available per field (window underfilled) → PASS (insufficient data, not stuck)

**Expected verdict changes on real logs**:
- LDC: A6 PASS (converges cleanly — unchanged)
- impinging_jet: A6 PASS (p_rgh outer residuals progress; previous HAZARD was spurious)
- BFS: A6 FAIL or HAZARD (residuals genuinely stuck — outer-iter semantics preserves this)
- DHC: A6 varies depending on case

### Test updates

Existing tests in `test_convergence_attestor.py` that rely on per-inner-solve A6 behavior may need regeneration. Look for tests that construct synthetic logs with repeated `Solving for X, Initial residual = ...` WITHOUT Time= block boundaries — those were relying on the old buggy behavior. Update them to include Time= markers per outer step.

Specifically examine `test_a6_decade_range_exactly_1_fires_fail` (Wave 1 C) — it may need Time= markers added to be semantically valid under the new A6.

Add new test: **test_a6_impinging_jet_real_log_not_fire** — use the actual impinging_jet log file (guard-skip if absent). Assert `_check_a6_no_progress(log, thresholds=load_thresholds("impinging_jet")).verdict == "PASS"`.

Add new test: **test_a6_outer_iter_vs_inner_solve_distinction** — synthetic log with 50 Time= blocks, each containing 3 inner p_rgh solves with residuals decreasing sharply within each block but outer-iteration initial-residual trend over the 50 blocks being flat. Assert A6 FAIL (old code would also see this as flat because per-inner counting; new code should see this as flat per outer-iter AND fire). This guards the "outer counting works" invariant.

Add new test: **test_a6_pass_when_outer_iter_progresses_despite_inner_repeats** — synthetic log with 50 Time= blocks, each inner repeats the same residual but outer-iteration initial-residual decays by >1 decade across the window. Assert A6 PASS (only the fix enables this — old code would FAIL this because inner residuals repeated).

## Track 2 extension: per-case promote_to_fail wiring

### Problem

`_derive_contract_status` at `ui/backend/services/validation_report.py` has `_HAZARD_TIER_CONCERNS` wired (Wave 2 D). But there's no mechanism to promote specific HAZARD concerns to FAIL per-case from the YAML `promote_to_fail` field.

### Required fix

Extend `_derive_contract_status` with an optional `thresholds: Optional[Thresholds]` parameter:

```python
def _derive_contract_status(
    gs_ref: GoldStandardReference,
    measurement: MeasuredValue | None,
    preconditions: list[Precondition],
    audit_concerns: list[AuditConcern],
    thresholds: Optional["Thresholds"] = None,  # NEW
) -> tuple[ContractStatus, ...]:
```

After the existing `has_hazard_tier` check:

```python
if has_hazard_tier:
    # NEW: check per-case promote_to_fail
    if thresholds is not None and thresholds.promote_to_fail:
        promoted_concerns = [
            c for c in audit_concerns
            if c.concern_type in thresholds.promote_to_fail
            and c.concern_type in _HAZARD_TIER_CONCERNS
        ]
        if promoted_concerns:
            # Per-case escalation: HAZARD concern → FAIL
            deviation_pct = 0.0
            if gs_ref.ref_value != 0.0:
                deviation_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0
            return ("FAIL", deviation_pct, None, lower, upper)
    # Default HAZARD path
    return ("HAZARD", deviation_pct, None, lower, upper)
```

Callers that want per-case promotion pass `thresholds=load_thresholds(case_id)`. The `Thresholds` class (Wave 1 A) already has `promote_to_fail: frozenset[str]`.

### Callers

Existing call sites:
- `ui/backend/services/validation_report.py` line ~748, ~764, ~855: check if they have access to a case_id. If yes, pass `thresholds=load_thresholds(case_id)`. If the case_id is not immediately available, pass `thresholds=None` (default; preserves current HAZARD behavior).
- `scripts/phase5_audit_run.py::_audit_fixture_doc` — it has `case_id` directly. Pass `thresholds=load_thresholds(case_id)` where the Track 5 recompute happens.

Backward compat: the `thresholds=None` default preserves Wave 2 D behavior (HAZARD never promoted). No existing callers break.

### Import handling

`_derive_contract_status` is in `ui/backend/services/validation_report.py`. It imports `Thresholds` from `src.convergence_attestor`. If this creates a circular import with the attestor → validation_report chain, use `TYPE_CHECKING` or lazy-import inside the function.

## Acceptance Checks

### Track 8 (A6)

CHK-1: Real impinging_jet log: `_check_a6_no_progress(log, thresholds=load_thresholds("impinging_jet")).verdict == "PASS"` (previously spurious HAZARD).

CHK-2: Real LDC log: `_check_a6_no_progress(log, thresholds=load_thresholds("lid_driven_cavity")).verdict == "PASS"` (regression guard — LDC must stay clean).

CHK-3: Synthetic log with 50 Time= blocks, outer-iter residual flat (0.5 per block for 50 blocks) → A6 FAIL.

CHK-4: Synthetic log with 50 Time= blocks, outer-iter residual decays 1e-1 → 1e-4 → A6 PASS.

CHK-5: Synthetic log with <2 outer iterations → A6 PASS (insufficient data).

CHK-6: Synthetic log with 50 Time= blocks each containing 3 inner p_rgh solves: outer residuals flat, inner residuals also flat. Both old and new A6 flag as FAIL (sanity).

CHK-7: Synthetic log with 50 Time= blocks, inner residuals within-block flat but outer decays: new A6 PASS. Old A6 would FAIL. **This is the key distinguishing test.**

### Track 2 extension

CHK-8: `_derive_contract_status(gs, m, [], [AuditConcern("CONTINUITY_NOT_CONVERGED", ...)], thresholds=Thresholds(...promote_to_fail=frozenset({"CONTINUITY_NOT_CONVERGED"})))` returns `status=FAIL` (promoted).

CHK-9: Same concern + `thresholds=None` returns `status=HAZARD` (default).

CHK-10: Same concern + `thresholds=Thresholds(...promote_to_fail=frozenset())` (empty) returns `status=HAZARD` (explicit empty = no promotion).

### Full suite regression

CHK-11: `.venv/bin/python -m pytest ui/backend/tests/ tests/test_task_runner.py tests/test_auto_verifier/ -q` passes with no new failures. Report exact count.

CHK-12: Any existing test that breaks from A6 semantics change must be updated in-scope. Document every touched test.

## Reject Conditions

REJ-1: Edits outside allowed_files (especially knowledge/gold_standards).
REJ-2: Changing `_derive_contract_status` signature in a backward-incompatible way (new param MUST be optional with default None).
REJ-3: Removing per-inner-solve parsing code entirely — keep `_parse_residual_timeline` as-is since A3 still uses it. Only A6 switches to outer-iter parsing.
REJ-4: Modifying gold_standards/*.yaml to change expected_verdict on any case.
REJ-5: Skipping CHK-7 (the distinguishing test) — it's the proof that the fix actually does what it claims.

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 4 H

## Files modified
- src/convergence_attestor.py [+N/-M]
- ui/backend/services/validation_report.py [+N/-M]
- ui/backend/tests/test_convergence_attestor.py [+N/-M]
- ui/backend/tests/test_validation_report.py [+N/-M]

## Changes summary
- Track 8: _parse_outer_iteration_residuals + A6 rewrite
- Track 2 extension: thresholds param in _derive_contract_status + promote_to_fail branch

## Acceptance checks self-verified
- CHK-1..12: PASS/FAIL + evidence

## Real-log sanity
- impinging_jet A6 verdict change: HAZARD → PASS (expected)
- LDC A6 verdict: PASS (regression preserved)

## Existing tests touched
- per-file summary of what changed and why

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
