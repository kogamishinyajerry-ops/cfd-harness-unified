# DEC-V61-074 P2-T1.b.2 + T1.b.3 · Codex post-commit batched review · Round 1

- **Verdict (per commit)**: `69c0ed6` CHANGES_REQUIRED · `c7ede01` CHANGES_REQUIRED
- **Diff target**: 69c0ed6 (TaskRunner ExecutorMode dispatch) + c7ede01 (TrustGate routing)
- **Date**: 2026-04-26
- **Tokens used**: 351,123
- **Codex CLI run id**: bg0ukwdks (transcript: `dec_v61_074_t1b23_postcommit_round1.log`, gitignored)

## `69c0ed6` (T1.b.2) findings

### 1. MED — Short-circuit path bypasses Notion write-back

Non-OK `ExecutorAbc` runs never reach the shared Notion write-back, so a refused run stays `Ready` instead of moving to `Review`.

**Evidence**:
- `src/task_runner.py:340-345` returns immediately on non-OK status, before the normal write-back at `src/task_runner.py:393-397`
- `src/notion_client.py:59-74` already treats `result.success == False` as `Status = Review` — the short-circuit was bypassing an existing failure-handling contract
- Verified directly with a `future_remote` probe: `run_task(...)` returned the short-circuit report and `notion.write_execution_result.called == False`

**Suggested fix**: Keep the comparator/correction/attestor short-circuit, but route the non-OK path through the same finalization/write-back block, or explicitly call `write_execution_result(task_spec, synthetic_failed_result, summary)` before returning. Add a regression test around `tests/test_task_runner_executor_mode.py:199-243` that asserts refusal paths still write back once.

## `c7ede01` (T1.b.3) findings

### 1. MED — WARN ceiling leaves histogram/helpers incoherent

The WARN ceiling rewrites `overall` but leaves the histogram/helpers inconsistent, so routed WARN reports can claim "no warnings".

**Evidence**:
- `src/metrics/trust_gate.py:153-172` changes only `overall` and `notes`
- `src/metrics/trust_gate.py:100-114` derives `has_warnings` and `summary()` from `count_by_status`
- With an all-PASS base report, routing through `mock` or `hybrid_init` currently yields `overall=WARN`, `has_warnings=False`, and `TrustGate: WARN | PASS=2 WARN=0 FAIL=0`
- That is a public-API correctness bug, not just a cosmetic mismatch

**Suggested fix**: When a routing ceiling synthesizes a WARN, also synthesize coherent warning state for `count_by_status` / `has_warnings` / `summary()`, or introduce a distinct routed-status field and make those helpers explicitly routing-aware. Add assertions for `has_warnings`, `count_by_status`, and `summary()` in `tests/test_metrics/test_trust_gate_executor_mode_routing.py:88-124`.

### 2. LOW — `_extract_mode()` AttributeError on non-mapping payload

`_extract_mode()` is only defensive for malformed mappings; a non-mapping `executor` field still crashes with `AttributeError`.

**Evidence**:
- `src/metrics/trust_gate.py:136-149` calls `.get("mode")` on any truthy `executor_section`
- Probing with `'mock'`, `['mock']`, and `123` raises `AttributeError`
- Current tests cover `None`, missing-key dicts, and unknown mode strings only (`tests/test_metrics/test_trust_gate_executor_mode_routing.py:144-169`)

**Suggested fix**: Add `if not isinstance(executor_section, Mapping): return _EXECUTOR_MODE_DOCKER_OPENFOAM` before the `.get(...)`. Add one regression test for a non-dict `executor` payload.

## Hard-constraint checks (PASSED)

- T1.b.2: 32/32 tests passed (`tests/test_task_runner.py` + `test_task_runner_executor_mode.py`); mutual exclusion enforced at `src/task_runner.py:268-272`; MockExecutor aliasing correct at `:11-21` and `:311-316`; resolver "add a row" KeyError at `:317-323`; Control→Execution allowed by `.importlinter:26-73`.
- T1.b.3 plane boundary: `src/metrics/` has no `from src.executor` imports; `.importlinter` Contract 2 still permits the shape (`.importlinter:50-73`); 27/27 tests passed (`tests/test_metrics/test_trust_gate.py` + `test_trust_gate_executor_mode_routing.py`).

## R2 closure

Fix landed at commit `8d7f990` — see `dec_v61_074_t1b23_postcommit_round2.md`.
