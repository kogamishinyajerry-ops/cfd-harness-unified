# DEC-V61-075 P2-T2.1+T2.2 · Codex pre-merge review · Round 2

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: T2.1 unstaged after R1 P2 closure (preflight note added)
- **Date**: 2026-04-26
- **Codex command**: `codex review --uncommitted --title "... R2 · addresses R1 P2"`

## Findings

### 1. P2 — Pre-flight note never reaches the real DOCKER_OPENFOAM execution path

In any execution path that still goes through `DockerOpenFOAMExecutor.execute()` — including `TaskRunner(executor_mode=DOCKER_OPENFOAM)` — the new `docker_openfoam_preflight_failed` note is never observed, because R1's patch only added a new side API on `FoamAgentExecutor` and did not switch existing callers over to it. As a result, Docker SDK/container/case-dir failures are still indistinguishable from ordinary solver failures downstream, even though the code documents the note as a stable branch point.

**Location**: `src/foam_agent_adapter.py:873-875`

### 2. P3 — Vacuous legacy `execute()` back-compat test patches the method it tests

`test_legacy_execute_path_still_returns_execution_result` patched `FoamAgentExecutor.execute` and then asserted the return type of `executor.execute(...)`. It would keep passing even if the real implementation later started returning `RunReport` or otherwise broke the legacy `CFDExecutor` contract. False confidence — does not catch the regression it claims to guard against.

**Location**: `tests/test_foam_agent_adapter_run_report.py:205-206`

## R3 closure

* P2: Updated `DockerOpenFOAMExecutor.execute()` to call `wrapped.execute_with_run_report()` when `wrapped` exposes the bridge method (initially `hasattr` — replaced in R3). New tests `test_docker_openfoam_wrapper_propagates_preflight_note_via_bridge` + `test_docker_openfoam_wrapper_falls_back_to_legacy_path_for_plain_cfdexecutor` pin both paths.
* P3: Replaced vacuous test with `test_legacy_execute_signature_returns_execution_result_per_protocol`, using:
  - `isinstance(FoamAgentExecutor(), CFDExecutor)` structural Protocol check
  - `typing.get_type_hints(FoamAgentExecutor.execute)["return"] is ExecutionResult` annotation pin
  Catches accidental broadening to a `Union` or swap to `RunReport`.

## Final disposition

R3 introduced 2 new findings (P2 TaskRunner notes drop, P3 unsafe `hasattr`); R4 introduced 2 new (legacy path symmetry, Notion summary persistence); R5 APPROVE. Rolled into commit b2ea911.
