# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 2 Invocation D — HAZARD tier wiring + U_ref plumb"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (B2 — U_ref not plumbed)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-001 — A2/A3/A5/A6 ignored in verdict)
    depends_on:
      - 61c7cd1 Wave 1 A (Thresholds loader + A1 exit + A3 per-field)
      - 9e6f30f Wave 1 B (VTK reader)
      - 49ba6e5 Wave 1 C (tests for A/B)

    scope_tracks:
      - Track 2 (primary): Wire HAZARD tier in _derive_contract_status for A2/A3/A5/A6 concerns
      - Track 6 (bundled): Plumb U_ref from task_spec.boundary_conditions through _audit_fixture_doc

    allowed_files:
      - ui/backend/services/validation_report.py   (Track 2 primary)
      - scripts/phase5_audit_run.py                (Track 6 primary; also fixture_doc orchestration)

    read_only_context:
      - src/convergence_attestor.py (Wave 1 A state; Thresholds dataclass + load_thresholds available)
      - src/comparator_gates.py (Wave 1 B state)
      - src/models.py (TaskSpec.boundary_conditions: Dict[str, Any])
      - knowledge/whitelist.yaml (case definitions + flow_type mapping)
      - knowledge/gold_standards/*.yaml (per-case boundary reference; READ ONLY — hard-floor 1)
      - .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md

    forbidden_files:
      - any file not in allowed_files
      - ESPECIALLY: knowledge/gold_standards/** (hard-floor 1 — tolerance changes forbidden)
      - tests/** and ui/backend/tests/** (separate Codex E invocation)
      - src/convergence_attestor.py (already landed Wave 1 A; don't re-edit)
      - src/comparator_gates.py (already landed Wave 1 B)

    autonomy: TOOL-SCOPE

---

## Track 2: HAZARD tier wiring in `_derive_contract_status`

### Current state (ui/backend/services/validation_report.py:537-660)

```python
_HARD_FAIL_CONCERNS = {
    "MISSING_TARGET_QUANTITY",     # G1
    "VELOCITY_OVERFLOW",           # G3
    "TURBULENCE_NEGATIVE",         # G4
    "CONTINUITY_DIVERGED",         # G5
    "SOLVER_CRASH_LOG",            # A1
    "SOLVER_ITERATION_CAP",        # A4
}
# A2/A3/A5/A6 currently: recorded as concerns but DO NOT affect contract_status
```

The current comment explicitly says "A2/A3/A5/A6 are HAZARD tier — they record concerns but don't hard-FAIL (some cases physically operate at high residuals; promotion to FAIL via per-case override lands in a future DEC)."

**This is the bug.** "Don't hard-FAIL" was the correct intent but the code doesn't wire HAZARD status either. Result: an in-band scalar with CONTINUITY_NOT_CONVERGED concern returns PASS, which is wrong.

### Required fix

Add `_HAZARD_TIER_CONCERNS` set:

```python
_HAZARD_TIER_CONCERNS = {
    "CONTINUITY_NOT_CONVERGED",    # A2
    "RESIDUALS_ABOVE_TARGET",       # A3
    "BOUNDING_RECURRENT",           # A5
    "NO_RESIDUAL_PROGRESS",         # A6
}
```

Extend verdict logic in `_derive_contract_status`:

```python
has_hazard_tier = any(
    c.concern_type in _HAZARD_TIER_CONCERNS for c in audit_concerns
)
```

Insert after hard-FAIL check, before tolerance check:

```python
# (existing hard-FAIL branch unchanged)

# NEW: HAZARD tier — trustworthy measurement but convergence is suspect
if has_hazard_tier:
    # Measurement may still be computable; report the deviation number,
    # but force contract_status=HAZARD and null `within_tolerance` because
    # "within band" is meaningless when the run hasn't physically converged.
    deviation_pct = 0.0
    if gs_ref.ref_value != 0.0:
        deviation_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0
    return ("HAZARD", deviation_pct, None, lower, upper)

# (existing tolerance-band check continues)
```

Preserve the existing `has_silent_pass_hazard` path as-is (DEC-036 heritage). Order of precedence: hard-FAIL first, then new HAZARD tier, then silent-pass-hazard, then tolerance band.

### Per-case promotion (deferred from Wave 4)

Do NOT implement promote_to_fail per-case lookup in this invocation — that's Wave 4 work. Current YAML has `promote_to_fail: []` for all cases, so this deferral doesn't change behavior.

If you believe promotion is straightforward to add now, you MAY add a scaffolding stub like:
```python
# TODO(Wave 4): read Thresholds.promote_to_fail for case and upgrade HAZARD→FAIL
```
at the new HAZARD branch, but do NOT implement actual promotion logic.

---

## Track 6: U_ref plumbing in `_audit_fixture_doc`

### Current state (scripts/phase5_audit_run.py:292-410)

```python
def _audit_fixture_doc(
    case_id: str,
    report: TaskExecutionReport,
    commit_sha: str | None,
    *,
    field_artifacts_ref: "dict | None" = None,
    phase7a_timestamp: str | None = None,
    u_ref: float = 1.0,         # <-- always defaults to 1.0
) -> dict:
    ...
    gate_violations = check_all_gates(
        log_path=log_path,
        vtk_dir=vtk_dir,
        U_ref=u_ref,          # <-- uses parameter (but caller never passes it)
    )
```

Caller at line 563 calls `_audit_fixture_doc(case_id, report, commit_sha, field_artifacts_ref=..., phase7a_timestamp=ts)` without `u_ref` → always 1.0. Codex DEC-036b B2 finding.

### Required fix

1. **Add helper** `_resolve_u_ref(task_spec, case_id) -> tuple[float, bool]`:
   - Returns `(u_ref, resolved: bool)`
   - Logic:
     - Look up `task_spec.boundary_conditions` (a dict)
     - Per flow_type heuristic (read flow_type from task_spec or infer from case_id):
       - Internal / pipe / duct / channel: inlet velocity magnitude
       - LDC / lid-driven: lid velocity (boundary with velocity where patch name matches "lid"/"top")
       - External / airfoil / cylinder: free-stream velocity
       - Buoyancy / thermal: reference natural-convection velocity (sqrt(g*beta*dT*L) or 0.01 if not available)
     - If boundary_conditions dict is missing / empty / doesn't yield a scalar: return `(1.0, False)`
   - This is heuristic; don't over-engineer. Best-effort with fallback.

2. **Call `_resolve_u_ref` in the main caller** (line ~563) and pass to `_audit_fixture_doc`:
   ```python
   task_spec = _load_task_spec(case_id)   # helper may exist; if not, skip this step
   u_ref, u_ref_resolved = _resolve_u_ref(task_spec, case_id)
   doc = _audit_fixture_doc(
       case_id, report, commit_sha,
       field_artifacts_ref=field_artifacts_ref,
       phase7a_timestamp=ts,
       u_ref=u_ref,
       u_ref_resolved=u_ref_resolved,
   )
   ```

3. **Inside `_audit_fixture_doc`**, if `u_ref_resolved=False`, stamp a WARN concern:
   ```python
   # New parameter
   u_ref_resolved: bool = True

   if not u_ref_resolved:
       audit_concerns.append(AuditConcernDict({
           "concern_type": "U_REF_UNRESOLVED",
           "summary": (f"G3 gate audited at default U_ref=1.0 because "
                       f"task_spec.boundary_conditions did not yield a "
                       f"resolvable reference velocity."),
           "detail": (...),
       }))
   ```

4. **Signature update** for `_audit_fixture_doc`: add `u_ref_resolved: bool = True` param. Preserve backward compat (default True means old callers with explicit u_ref still work).

### If TaskSpec loading is complex

If `_load_task_spec(case_id)` doesn't exist or is non-trivial to wire, you may:
- Option A: use `report.task_spec` if the report object carries it (check models.py)
- Option B: load whitelist.yaml directly and extract boundary_conditions
- Option C: punt — use a simple mapping `_CASE_U_REF_REGISTRY: dict[str, float]` hardcoded for the 10 whitelist cases, with comment pointing to future work

**Option C is acceptable** if Options A/B are too invasive. The important deliverable is: `u_ref` is no longer always 1.0 for the 10 known cases.

Suggested mapping (verify against knowledge/whitelist.yaml):
```python
_CASE_U_REF_REGISTRY = {
    "lid_driven_cavity": 1.0,
    "backward_facing_step": 44.2,          # inlet
    "circular_cylinder_wake": 1.0,
    "turbulent_flat_plate": 69.4,          # inlet
    "plane_channel_flow": 1.0,             # normalized
    "differential_heated_cavity": 0.01,    # characteristic buoyancy scale
    "naca0012_airfoil": 51.5,              # free-stream
    "duct_flow": 10.0,                     # check against whitelist
    "axisymmetric_impinging_jet": 5.0,     # jet exit
    "rayleigh_benard_convection": 0.005,   # buoyancy characteristic
}
```
If you use Option C, add `u_ref_resolved=True` for cases in the registry and `False` for unknown.

---

## Acceptance Checks

CHK-1: `_derive_contract_status` with `measurement.value=in_band` and `audit_concerns=[CONTINUITY_NOT_CONVERGED]` returns `status=HAZARD` (previously returned PASS).

CHK-2: `_derive_contract_status` with `measurement.value=in_band` and `audit_concerns=[RESIDUALS_ABOVE_TARGET]` returns `status=HAZARD`.

CHK-3: `_derive_contract_status` with `audit_concerns=[VELOCITY_OVERFLOW]` (hard-FAIL) + `[CONTINUITY_NOT_CONVERGED]` (HAZARD) returns `status=FAIL` (hard-FAIL takes precedence).

CHK-4: `_derive_contract_status` with no concerns + `measurement.value=in_band` returns `status=PASS` (regression guard — clean path unchanged).

CHK-5: `_derive_contract_status` with no concerns + `measurement.value=out_of_band` returns `status=HAZARD` via existing COMPATIBLE_WITH_SILENT_PASS_HAZARD path (existing behavior preserved).

CHK-6: `_audit_fixture_doc(case_id="lid_driven_cavity", ...)` called WITHOUT explicit u_ref: now internally resolves to LDC lid velocity (1.0) and passes it to `check_all_gates`. Verify via log/trace that u_ref=1.0 not default-fallback.

CHK-7: `_audit_fixture_doc(case_id="backward_facing_step", ...)`: u_ref resolves to BFS inlet velocity (44.2 or whatever whitelist specifies, NOT 1.0).

CHK-8: `_audit_fixture_doc(case_id="unknown_case_xyz", ...)`: u_ref falls back to 1.0 AND `audit_concerns` contains entry with `concern_type=U_REF_UNRESOLVED`.

CHK-9: Existing tests in `ui/backend/tests/` must still pass (Codex will run pytest with PYTHONPYCACHEPREFIX workaround on convergence_attestor + comparator_gates tests; broader tests are Claude's responsibility).

CHK-10: No change to existing HARD_FAIL_CONCERNS set (A2/A3/A5/A6 concerns don't become hard-FAIL; they become HAZARD).

## Reject Conditions

REJ-1: Edits outside `allowed_files`. In particular: DO NOT touch knowledge/gold_standards/ (hard-floor 1).
REJ-2: Implementing Wave 3 scope (TaskRunner reordering).
REJ-3: Implementing Wave 4 scope (per-case promote_to_fail enforcement; A6 outer-iteration semantics rewrite).
REJ-4: Breaking backward compat for `_derive_contract_status` callers (the 3 call sites in validation_report.py + test files). Signature should be unchanged; only internal logic extended.
REJ-5: Removing the existing `_HARD_FAIL_CONCERNS` set or any of its entries.
REJ-6: Making U_ref extraction raise on unknown case (must return fallback gracefully).
REJ-7: Committing any change that modifies fixture files under `ui/backend/tests/fixtures/` — those represent golden verdict state and flipping PASS→HAZARD is Claude's verification step (test coverage lands in Codex E).

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 2 D

## Files modified
- ui/backend/services/validation_report.py [+N/-M]
- scripts/phase5_audit_run.py [+N/-M]

## Changes summary
- Track 2 HAZARD tier: new _HAZARD_TIER_CONCERNS set + verdict branch
- Track 6 U_ref plumb: _resolve_u_ref helper + caller wire-through + WARN concern

## Decisions made (Option A/B/C for U_ref)
- Which approach chosen + why

## Acceptance checks self-verified
- CHK-1..10: PASS/FAIL + evidence

## Deviations from spec (if any)
- ...

## Fixture state impact warning
- List any test fixture file under ui/backend/tests/fixtures/ that would
  need updated expected_verdict after this change lands (Claude regenerates
  as separate commit, not this Codex run).
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
