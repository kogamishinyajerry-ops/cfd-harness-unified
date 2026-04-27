# DEC-V61-075 P2-T2.1+T2.2 · Codex pre-merge review · Round 4

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: T2.1 unstaged after R3 P2+P3 closures (`_OK_PATH_PROPAGATED_NOTES` + `isinstance` dispatch)
- **Date**: 2026-04-26
- **Codex command**: `codex review --uncommitted --title "... R4 · bridge + wrapper isinstance + TaskRunner OK-path note propagation"`

## Findings

### 1. P2-A — Legacy `executor=` path doesn't produce the preflight note

The R3 propagation is confined to the `self._executor_abc` branch, while the legacy `executor=` branch still calls `FoamAgentExecutor.execute()` directly and never produces `docker_openfoam_preflight_failed`. That matters in current repo workflows: `scripts/p2_acceptance_run.py`, `scripts/phase5_audit_run.py`, and `ui/backend/services/wizard_drivers.py` all construct `TaskRunner(executor=FoamAgentExecutor())`. Docker SDK/container outages in the main acceptance, audit, and UI flows still collapse into the same generic `❌ Failed` summary the patch is trying to distinguish.

**Location**: `src/task_runner.py:400-403`

### 2. P2-B — `NotionClient.write_execution_result()` does not persist summary

The new signal is appended to `summary`, but `NotionClient.write_execution_result()` does not store that summary anywhere — it only updates the task `Status`. In any run that uses the Notion control plane, a `docker_openfoam_preflight_failed` condition is therefore still indistinguishable from an ordinary solver failure, so the operator-facing note never reaches one of the repo's primary consumers.

**Location**: `src/task_runner.py:447-454`

## R5 closure

* **P2-A**: Legacy branch in `run_task` now detects when `self._executor` is a `FoamAgentExecutor` and inline-checks `not exec_result.success and exec_result.raw_output_path is None` — emits the same `docker_openfoam_preflight_failed` note symmetrically. Production scripts (3 listed by Codex) get the same operator signal.
  - Added 2 tests: `test_legacy_foam_agent_executor_path_emits_preflight_note` + `test_legacy_foam_agent_runtime_failure_does_NOT_emit_preflight_note` for legacy-path discrimination.
* **P2-B**: Pushed back as out-of-scope for T2.1. NotionClient summary persistence is a control-plane DB-schema concern (would require adding a `Summary` rich_text property to the Notion Tasks DB), not an executor abstraction concern. The summary reaches stdout/log consumers + audit-package manifests today; Notion persistence is a separate DEC. Documented in commit b2ea911 message.

## Final disposition

R5 APPROVE. Bundle landed at commit b2ea911.
