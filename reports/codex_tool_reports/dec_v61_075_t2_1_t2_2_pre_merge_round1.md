# DEC-V61-075 P2-T2.1+T2.2 · Codex pre-merge review · Round 1

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: T2.1 unstaged (`src/foam_agent_adapter.py` + `tests/test_foam_agent_adapter_run_report.py`)
- **Date**: 2026-04-26
- **Codex command**: `codex review --uncommitted --title "DEC-V61-075 P2-T2.1 (TRUST-CORE WRITE) · FoamAgentExecutor.execute_with_run_report bridge"`
- **Note**: review-output captured as conversation summary (verbatim transcript not persisted to log file due to inline review pattern; Codex CLI stdout was inspected directly).

## Findings

### 1. P2 — Pre-flight failures hard-coded `status=ExecutorStatus.OK` in the new RunReport bridge

`FoamAgentExecutor.execute()` returns `ExecutionResult(success=False, error_message=...)` for pre-flight failures (Docker SDK missing, container stopped, case-dir creation failed) — cases where the executor never actually launched a solve. The new `execute_with_run_report` hard-coded `status=OK`, so any caller adopting the new API could not distinguish an attempted run from an executor refusal and would route environment/setup failures down the normal success-status path instead of short-circuiting on status.

**Location**: `src/foam_agent_adapter.py:848-850`

## R2 closure

* Emit `docker_openfoam_preflight_failed` note when `execution_result.success=False` AND `raw_output_path is None` (the only paths where pre-flight failed before any case dir was created).
* Status stays `OK` because promoting environment unavailability to a non-OK status would require amending `EXECUTOR_ABSTRACTION.md` §6.1 + `ExecutorStatus` enum (additive value), churning `spec_file_sha256` → all manifest contract_hashes drift. Out of scope for the "thin bridge" T2.1.
* Documented in method docstring + DEC body as known follow-up DEC opportunity.
* Added `test_execute_with_run_report_emits_preflight_note_when_raw_output_absent` + `test_execute_with_run_report_no_preflight_note_when_solver_failed_with_output` for discrimination + inverse coverage.

## Final disposition

R2 introduced 2 new findings (P2/P3 below); R3, R4 each introduced more cross-system findings; R5 returned APPROVE. Rolled into commit b2ea911.
