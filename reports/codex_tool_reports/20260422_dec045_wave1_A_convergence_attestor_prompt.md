# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 1 Invocation A — convergence_attestor.py fixes"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (BLOCK, 5 blockers)
    scope_tracks:
      - Track 1: Land YAML loader (CA-004 remediation)
      - Track 4: A1 consumes exit_code (CA-003 remediation)
      - CA-005 partial: A3 per-field residual targets
      - CA-006 nit: A6 "stuck" uses <= 1.0 not < 1.0
      - CA-007 nit: A4 gap-block consecutiveness fix

    allowed_files:
      - src/convergence_attestor.py           (primary edit surface)

    read_only_context:
      - knowledge/attestor_thresholds.yaml    (YAML schema Claude pre-wrote; loader must parse this)
      - src/comparator_gates.py               (parse_solver_log consumer; don't modify)
      - src/foam_agent_adapter.py             (ExecutionResult shape reference; don't modify)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md  (findings source)
      - scripts/phase5_audit_run.py           (caller; backward-compat target but DON'T EDIT)
      - ui/backend/tests/test_convergence_attestor.py (existing test shape; DON'T EDIT — separate invocation)

    forbidden_files:
      - any file not in allowed_files list (read-only context is OK to read, NOT edit)
      - especially: knowledge/gold_standards/** (hard-floor 1)
      - especially: tests/** and ui/backend/tests/** (separate Codex invocation)
      - especially: scripts/phase5_audit_run.py (Wave 2/3 scope)

    autonomy: TOOL-SCOPE (within src/convergence_attestor.py, full architectural freedom)

---

## Detailed work spec

### 1. Thresholds dataclass + loader (Track 1)

Add a dataclass `Thresholds` matching the YAML schema. Add a loader function that reads `knowledge/attestor_thresholds.yaml`, applies per-case overrides, and returns a resolved `Thresholds` instance. Loader is idempotent and cacheable (module-level cache acceptable; invalidation on case_id change).

```python
@dataclass(frozen=True)
class Thresholds:
    continuity_floor: float
    residual_floor: float
    residual_floor_per_field: dict[str, float]  # field → target; defaultdict-like
    iteration_cap_detector_count: int
    bounding_recurrence_frac_threshold: float
    bounding_recurrence_window: int
    no_progress_decade_frac: float
    no_progress_window: int
    promote_to_fail: frozenset[str] = field(default_factory=frozenset)
    case_id: Optional[str] = None   # for logging/debug only

def load_thresholds(
    case_id: Optional[str] = None,
    yaml_path: Optional[Path] = None,
) -> Thresholds:
    """Load YAML and resolve per-case overrides. Returns defaults-only
    instance if case_id is None or case not present in YAML."""
```

Design constraints:
- Use `yaml.safe_load` (import `yaml`; it's available — project dep).
- Default YAML path: `Path(__file__).resolve().parent.parent / "knowledge" / "attestor_thresholds.yaml"` (repo-relative).
- If YAML missing → return hardcoded-constant defaults + log WARN. Do NOT raise.
- If YAML schema_version != 1 → log WARN but continue with best-effort parse.
- Unknown top-level keys in YAML → log WARN, continue.
- Unknown per-field keys in residual_floor_per_field → accept (forward-compat).
- `promote_to_fail` is a list in YAML; convert to frozenset.
- Merge logic for per_case override:
  - Start with defaults
  - For each key in per_case[case_id], override defaults
  - For residual_floor_per_field: per-case dict REPLACES defaults (not merge) — document this choice explicitly in code comment. If you think merge is safer, implement merge and justify in your response.
  - Actually: recommended implementation is MERGE (per_case values override, unmentioned defaults preserved). Please use merge semantics.

### 2. `_check_a1_solver_crash` — consume exit code (Track 4)

Current signature: `_check_a1_solver_crash(log_path: Path) -> AttestorCheck`

New signature: `_check_a1_solver_crash(log_path: Path, execution_result: Any = None) -> AttestorCheck`

Semantics:
- If `execution_result is not None`:
  - Check `getattr(execution_result, "success", None)`. If `False` → FAIL with concern_type `SOLVER_CRASH_LOG` and evidence includes exit_code if available (`getattr(execution_result, "exit_code", None)`).
- Then ALSO check log for FATAL markers (independent signal).
- FAIL verdict if EITHER exit indicates failure OR log has FATAL marker.
- Regex widen: currently only `^Floating point exception`. Expand to match:
  - `FOAM FATAL IO ERROR`
  - `FOAM FATAL ERROR`
  - `^Floating point exception`
  - `Floating exception` (anywhere)
- Avoid matching the startup banner `sigFpe : Enabling floating point exception trapping` (current code handles this; preserve).

Use duck-typing (`getattr`) — do NOT `from src.foam_agent_adapter import ExecutionResult` to avoid circular import risk. `execution_result` param typed as `Any = None`.

### 3. `_check_a3_residual_floor` — per-field targets (CA-005 partial)

Current: one `A3_RESIDUAL_FLOOR` for all fields.

New: pull per-field target from `thresholds.residual_floor_per_field.get(field_name, thresholds.residual_floor)`.

Field names seen in real logs: Ux, Uy, Uz, p, p_rgh, k, epsilon, omega, h, nuTilda, T.

Updated summary/detail strings should include the per-field target when reporting offenders (not just one global threshold).

### 4. CA-006: A6 decade check boundary

Current: `if decade_range < A6_PROGRESS_DECADE_FRAC` → FAIL (stuck).

New: `if decade_range <= thresholds.no_progress_decade_frac` → FAIL. Also use `thresholds.no_progress_decade_frac` not module constant.

### 5. CA-007: A4 gap-block consecutiveness

Current behavior per Codex finding: blocks with no pressure solve are filtered out before consecutive-check. So `[cap, gap, cap, cap]` looks like `[cap, cap, cap]` = 3 consecutive → A4 FAIL.

New behavior: preserve gap blocks in the sequence; streak resets to 0 on a gap. `[cap, gap, cap, cap]` = max streak 2 → A4 PASS.

Implement: walk the full per-block cap-count sequence (including `0` for gaps), count consecutive caps, track max streak, FAIL if `max_streak >= thresholds.iteration_cap_detector_count`.

### 6. Thread thresholds through all checks

All `_check_a[2-6]_*` take `thresholds: Thresholds` param. `_check_a1_*` takes `execution_result`. All module-constant uses (A2_CONTINUITY_FLOOR, A3_RESIDUAL_FLOOR, A5_*, A6_*) replaced by `thresholds.<field>`.

KEEP module constants for backward compat as defaults in `load_thresholds` fallback path (when YAML missing). Rename if naming clashes, but they should still exist.

### 7. `attest()` main function signature update

```python
def attest(
    log_path: Optional[Path],
    execution_result: Any = None,
    case_id: Optional[str] = None,
    thresholds: Optional[Thresholds] = None,
) -> AttestationResult:
    """Run all 6 checks and aggregate verdict.

    Parameters
    ----------
    log_path : Path or None
        Solver log. None → ATTEST_NOT_APPLICABLE.
    execution_result : Any, optional
        Duck-typed object with .success and .exit_code attrs. Used by A1.
    case_id : str, optional
        Whitelist case ID for per-case YAML override lookup.
    thresholds : Thresholds, optional
        Pre-resolved thresholds. If None, calls load_thresholds(case_id).
    """
```

Backward compat: `attest(log_path)` still works (execution_result=None, case_id=None, thresholds defaults).

---

## Acceptance Checks (CHK-N)

CHK-1: Existing `scripts/phase5_audit_run.py:383` caller `attestation = attest(solver_log)` must still work unchanged (no required new args).

CHK-2: Existing `ui/backend/tests/test_convergence_attestor.py` tests that call `attest(log)` should still pass without test modifications. If the tests had hardcoded old threshold constants (e.g., `A2_CONTINUITY_FLOOR`), those constants must still be importable at module level (even if internally the value comes from YAML).

CHK-3: `load_thresholds()` without args returns `Thresholds` instance with YAML-defaults values (not missing keys, not None values).

CHK-4: `load_thresholds("impinging_jet")` returns Thresholds with `residual_floor_per_field["p_rgh"] == 5.0e-3` (per-case override applied).

CHK-5: `load_thresholds("nonexistent_case_xyz")` returns Thresholds with defaults (no raise, no per-case lookup error).

CHK-6: If `knowledge/attestor_thresholds.yaml` is renamed/moved, `load_thresholds()` returns hardcoded-constant defaults and logs WARN (graceful degradation).

CHK-7: `_check_a1_solver_crash(log_path, execution_result=mock(success=False, exit_code=139))` returns `verdict=FAIL` regardless of log content.

CHK-8: `_check_a1_solver_crash(log_path, execution_result=mock(success=True))` with log containing `Floating exception` returns `verdict=FAIL` (log signal alone).

CHK-9: `_check_a3_residual_floor` on a log with `p_rgh Initial residual = 6e-3` + thresholds from `impinging_jet` → PASS (6e-3 <= 5e-3? No wait, 6e-3 > 5e-3. Let me redo: threshold for p_rgh=5e-3 case-override; final p_rgh residual=6e-3 > 5e-3 → HAZARD). Verify the per-field path is taken. Synthetic test data is fine.

CHK-10: CA-006: `_check_a6_no_progress` on a log where max decade_range across fields is exactly 1.0 → FAIL (not PASS). Previously `< 1.0` would have been PASS at 1.0.

CHK-11: CA-007: `_check_a4_iteration_cap` on a block sequence `[cap, gap, cap, cap]` (where gap has 0 pressure solves) returns PASS. Max consecutive = 2, below threshold 3.

CHK-12: `_check_a4_iteration_cap` on `[cap, cap, cap]` consecutive → FAIL as before.

CHK-13: `attest(None)` returns `overall=ATTEST_NOT_APPLICABLE` (unchanged behavior).

CHK-14: `attest(log, execution_result=mock(success=False))` returns `overall=ATTEST_FAIL` with A1 in checks even if log is otherwise clean.

## Reject Conditions (REJ-N)

REJ-1: Any edit to files outside `allowed_files`. In particular: do NOT edit scripts/, tests/, or ui/backend/.
REJ-2: Removing module-level A2/A3/A5/A6 constants (existing code imports them).
REJ-3: Changing `_check_a*` function NAMES (existing tests may import them directly).
REJ-4: Breaking backward compat for `attest(log_path)` one-arg call.
REJ-5: Importing ExecutionResult from foam_agent_adapter (circular import risk).
REJ-6: Making loader raise on missing YAML (must gracefully fall back).

## Output format

After applying changes, emit a structured report:

```
# Codex Diff Report — DEC-V61-045 Wave 1 A

## Files modified
- path/to/file [+N/-M lines]

## Changes summary
- bullet list per track

## Acceptance checks self-verified
- CHK-1: PASS/FAIL + evidence
- CHK-N: PASS/FAIL + evidence

## Deviations from spec (if any)
- [what deviated + why]

## Tokens used
<auto>
```

## Hints for implementation

- `from pathlib import Path` is already imported
- `yaml` import needs to be added
- Consider extracting `load_thresholds` to a helper module if convergence_attestor.py grows too large, but prefer keeping in one file for this DEC.
- Module-level cache: `@functools.lru_cache(maxsize=32)` on load_thresholds is fine if Thresholds is hashable (frozen dataclass with frozenset field is hashable; dict field is NOT — you may need to freeze the dict to tuple-of-pairs for hashability, or skip caching).
- For testability: expose `_DEFAULT_THRESHOLDS` at module level as the hardcoded fallback instance.

---

[/CLAUDE → CODEX TOOL INVOCATION]
