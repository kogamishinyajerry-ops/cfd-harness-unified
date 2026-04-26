"""DEC-V61-075 P2-T2.1 · FoamAgentExecutor.execute_with_run_report tests.

Covers the new canonical-RunReport bridge added in P2-T2.1 per
EXECUTOR_ABSTRACTION.md §6.1. The legacy ``execute()`` path stays on
``ExecutionResult`` (CFDExecutor Protocol back-compat — see DEC-V61-075
scope rationale); this file pins the new path's contract:

  - Returns a ``RunReport(mode=DOCKER_OPENFOAM, status=OK)`` regardless
    of solver outcome (success embeds in ``execution_result``).
  - ``contract_hash`` + ``version`` byte-equal a sibling
    ``DockerOpenFOAMExecutor()`` invocation (single-sourced spec hash).
  - Delegates to ``execute()`` exactly once (no re-run, no skip).
"""

from __future__ import annotations

from unittest.mock import patch

from src.executor import DockerOpenFOAMExecutor, ExecutorMode, ExecutorStatus
from src.foam_agent_adapter import FoamAgentExecutor
from src.models import (
    Compressibility,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)


def _make_task_spec() -> TaskSpec:
    return TaskSpec(
        name="t2_1_run_report_test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
    )


def _canned_success() -> ExecutionResult:
    return ExecutionResult(
        success=True,
        is_mock=False,
        residuals={"p": 1e-6, "U": 1e-6},
        key_quantities={"u_centerline": [0.0, 0.5, 1.0]},
        execution_time_s=12.3,
        raw_output_path="/tmp/cases/run_report_test",
    )


def _canned_failure() -> ExecutionResult:
    return ExecutionResult(
        success=False,
        is_mock=False,
        error_message="solver diverged",
        execution_time_s=4.2,
        raw_output_path=None,
    )


def test_execute_with_run_report_success_yields_ok_status_with_result():
    """Successful solver run → RunReport(status=OK, execution_result=result).

    Status=OK signals "executor attempted the run" per
    EXECUTOR_ABSTRACTION §6.1; the success/failure outcome rides inside
    execution_result.
    """
    executor = FoamAgentExecutor()
    canned = _canned_success()
    with patch.object(FoamAgentExecutor, "execute", return_value=canned) as mocked:
        report = executor.execute_with_run_report(_make_task_spec())

    mocked.assert_called_once()
    assert report.status is ExecutorStatus.OK
    assert report.execution_result is canned
    assert report.execution_result.success is True


def test_execute_with_run_report_failure_still_yields_ok_status():
    """Failed solver run also yields status=OK; success/failure rides in
    execution_result.

    Per EXECUTOR_ABSTRACTION §6.1, ExecutorStatus distinguishes executor
    *mode-level refusal* from run *outcome*. A diverged solver is a
    run-outcome failure (execution_result.success=False), not a
    mode-level refusal.
    """
    executor = FoamAgentExecutor()
    canned = _canned_failure()
    with patch.object(FoamAgentExecutor, "execute", return_value=canned):
        report = executor.execute_with_run_report(_make_task_spec())

    assert report.status is ExecutorStatus.OK
    assert report.execution_result is canned
    assert report.execution_result.success is False


def test_execute_with_run_report_emits_preflight_note_when_raw_output_absent():
    """Pre-flight failure (Docker unavailable, case-dir creation failed)
    surfaces as ``docker_openfoam_preflight_failed`` in RunReport.notes.

    Codex P2-T2.1 R1 P2 fix: status stays OK (introducing a non-OK
    status would require a §6.1 spec amendment that churns
    contract_hash on every signed manifest — out of scope for the
    "thin bridge" T2.1). The note gives downstream callers a stable
    branch point without parsing error_message strings.
    """
    executor = FoamAgentExecutor()
    canned = _canned_failure()  # raw_output_path=None
    with patch.object(FoamAgentExecutor, "execute", return_value=canned):
        report = executor.execute_with_run_report(_make_task_spec())

    assert report.status is ExecutorStatus.OK
    assert "docker_openfoam_preflight_failed" in report.notes
    assert len(report.notes) == 1


def test_execute_with_run_report_no_preflight_note_when_solver_failed_with_output():
    """Solver-runtime failure (divergence, timeout) keeps raw_output_path
    populated and MUST NOT emit the pre-flight note.

    Without this discrimination, the pre-flight note would falsely
    fire on every diverged solve and adopters could not tell environment
    failures from physics failures.
    """
    runtime_failure = ExecutionResult(
        success=False,
        is_mock=False,
        error_message="solver diverged at step 2400",
        residuals={"p": 1e2, "U": 1e3},
        execution_time_s=78.4,
        raw_output_path="/tmp/cases/diverged_run",  # solver actually ran
    )
    executor = FoamAgentExecutor()
    with patch.object(FoamAgentExecutor, "execute", return_value=runtime_failure):
        report = executor.execute_with_run_report(_make_task_spec())

    assert report.status is ExecutorStatus.OK
    assert "docker_openfoam_preflight_failed" not in report.notes
    assert report.notes == ()


def test_execute_with_run_report_no_preflight_note_on_success():
    """Successful run MUST NOT emit the pre-flight note (defensive
    inverse of the discrimination test)."""
    executor = FoamAgentExecutor()
    with patch.object(FoamAgentExecutor, "execute", return_value=_canned_success()):
        report = executor.execute_with_run_report(_make_task_spec())

    assert report.status is ExecutorStatus.OK
    assert report.notes == ()


def test_execute_with_run_report_carries_docker_openfoam_mode():
    """RunReport.mode must be DOCKER_OPENFOAM — FoamAgentExecutor is the
    canonical truth-source for that mode (§6.1 routing input)."""
    executor = FoamAgentExecutor()
    with patch.object(FoamAgentExecutor, "execute", return_value=_canned_success()):
        report = executor.execute_with_run_report(_make_task_spec())

    assert report.mode is ExecutorMode.DOCKER_OPENFOAM


def test_execute_with_run_report_contract_hash_byte_equals_docker_openfoam_executor():
    """Single-source the spec-derived contract hash: the bridge must
    produce the byte-identical hash that DockerOpenFOAMExecutor.contract_hash
    reports — otherwise §3 / spike F-3 manifest-tagging drifts.

    A spec-file change flips both hashes in lockstep; a method-internal
    duplication of the SHA-256 derivation would silently desynchronize.
    """
    executor = FoamAgentExecutor()
    canonical = DockerOpenFOAMExecutor()
    with patch.object(FoamAgentExecutor, "execute", return_value=_canned_success()):
        report = executor.execute_with_run_report(_make_task_spec())

    assert report.contract_hash == canonical.contract_hash
    assert report.version == canonical.VERSION
    assert len(report.contract_hash) == 64  # SHA-256 hex


def test_execute_with_run_report_delegates_to_execute_exactly_once():
    """No re-run, no skip — the bridge wraps execute() one-to-one.

    Future maintainers must not add retry/caching logic here without
    updating this test (and DEC-V61-075 scope).
    """
    executor = FoamAgentExecutor()
    canned = _canned_success()
    spec = _make_task_spec()
    with patch.object(FoamAgentExecutor, "execute", return_value=canned) as mocked:
        executor.execute_with_run_report(spec)

    mocked.assert_called_once_with(spec)


def test_legacy_execute_signature_returns_execution_result_per_protocol():
    """T2.1 must NOT change ``FoamAgentExecutor.execute()`` signature.

    Codex P2-T2.1 R2 P3 fix: the previous version of this test patched
    ``FoamAgentExecutor.execute`` and then asserted the patched return
    type — vacuous, would still pass even if the real implementation
    started returning a ``RunReport`` and broke ~30 ``CFDExecutor``
    Protocol call sites.

    Now we (a) confirm structural ``CFDExecutor`` Protocol membership
    (mirrors ``tests/test_foam_agent_adapter.py:173``), and (b) pin the
    return-type annotation to ``ExecutionResult`` via
    ``typing.get_type_hints`` — catches accidental broadening to a
    ``Union`` or a swap to ``RunReport``.
    """
    import typing

    from src.models import CFDExecutor

    assert isinstance(FoamAgentExecutor(), CFDExecutor)
    hints = typing.get_type_hints(FoamAgentExecutor.execute)
    assert hints.get("return") is ExecutionResult


def test_docker_openfoam_wrapper_propagates_preflight_note_via_bridge():
    """DockerOpenFOAMExecutor.execute() must surface the
    ``docker_openfoam_preflight_failed`` note when the wrapped
    ``FoamAgentExecutor`` reports a pre-flight failure.

    Codex P2-T2.1 R2 P2 fix: without this propagation, the note added
    in ``execute_with_run_report`` would never reach
    ``TaskRunner(executor_mode=DOCKER_OPENFOAM)`` consumers — which
    Codex flagged as the actual reason the note matters.
    """
    from src.executor import DockerOpenFOAMExecutor

    canned = _canned_failure()  # raw_output_path=None → pre-flight signal
    real_foam = FoamAgentExecutor()
    with patch.object(FoamAgentExecutor, "execute", return_value=canned):
        wrapper = DockerOpenFOAMExecutor(wrapped=real_foam)
        report = wrapper.execute(_make_task_spec())

    assert report.status is ExecutorStatus.OK
    assert "docker_openfoam_preflight_failed" in report.notes


def test_docker_openfoam_wrapper_falls_back_to_legacy_path_for_plain_cfdexecutor():
    """Wrappers around plain ``CFDExecutor`` test doubles (MagicMock,
    custom plug-ins without the bridge method) MUST keep working.

    The ``hasattr`` structural-typing check in
    ``DockerOpenFOAMExecutor.execute()`` lets non-FoamAgent adapters
    skip the bridge path. This pins that fallback so the existing 5
    test_docker_openfoam_wrapper.py tests don't regress.
    """
    from unittest.mock import MagicMock

    from src.executor import DockerOpenFOAMExecutor

    canned = _canned_success()
    plain_executor = MagicMock(spec=["execute"])  # NO execute_with_run_report
    plain_executor.execute.return_value = canned

    wrapper = DockerOpenFOAMExecutor(wrapped=plain_executor)
    report = wrapper.execute(_make_task_spec())

    plain_executor.execute.assert_called_once()
    assert report.status is ExecutorStatus.OK
    assert report.execution_result is canned
    assert report.notes == ()  # no bridge → no pre-flight note
