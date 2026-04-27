# DEC-V61-075 P2-T2.1+T2.2 · Codex pre-merge review · Round 3

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: T2.1 unstaged after R2 P2+P3 closures (wrapper bridge + structural Protocol test)
- **Date**: 2026-04-26
- **Codex command**: `codex review --uncommitted --title "... R3 · addresses R2 P2 (wire preflight note into wrapper) + R2 P3 (non-vacuous Protocol back-compat test)"`

## Findings

### 1. P2 — `TaskRunner.run_task` drops `executor_run_report.notes` on the OK path

`TaskRunner.run_task()` only keeps `executor_run_report.execution_result` on the OK path and drops `executor_run_report.notes`. So a real `TaskRunner(executor_mode=DOCKER_OPENFOAM)` run will still surface only a generic failed `ExecutionResult` / `ATTEST_NOT_APPLICABLE` and never expose the new preflight distinction to summary, Notion, or TrustGate consumers.

**Location**: `src/foam_agent_adapter.py:874-882` (proximate); fix point in `src/task_runner.py` ABC dispatch branch.

### 2. P3 — `hasattr(wrapped, 'execute_with_run_report')` unsafe for bridge probe

A bare `MagicMock()` (no `spec`) reports every attribute as present via its `__getattr__`. So this branch fires for plain mock-based wrapped executors and skips the legacy `wrapped.execute()` path, returning the mock fabricated by the auto-attr `execute_with_run_report()` instead of a real `RunReport`. Breaks the legacy fallback for MagicMock-backed fixtures explicitly mentioned in the docstring unless every caller remembers to use a restrictive `spec`.

**Location**: `src/executor/docker_openfoam.py:81-82`

## R4 closure

* P2: Introduced module-level `_OK_PATH_PROPAGATED_NOTES = frozenset({"docker_openfoam_preflight_failed"})` whitelist. ABC dispatch branch in `run_task` filters notes through it; passes via new `_build_summary` `executor_notes` kwarg. Trust/manifest annotations like `mock_executor_no_truth_source` deliberately excluded — they belong on the AuditPackage manifest's `executor` section per T1.b.1, not in summary.
  - Added 4 tests in new `TestOkPathExecutorNotePropagation` class.
* P3: Replaced `hasattr` with `isinstance(wrapped, FoamAgentExecutor)` (lazy-imported in the wrapper). Test `MagicMock(spec=["execute"])` now correctly takes the legacy fallback path; `MagicMock(spec=FoamAgentExecutor)` would correctly take the bridge path. Existing 5 `test_docker_openfoam_wrapper.py` tests preserved.

## Final disposition

R4 introduced 2 new findings (legacy-path symmetry + Notion summary persistence); R5 APPROVE. Rolled into commit b2ea911.
