"""Tests for DockerOpenFOAMExecutor (P2-T1 skeleton wrapping FoamAgentExecutor).

P2-T2 will replace the wrapper-style delegation with the formal
docker-openfoam wrapping per spike F-3 migration plan. Until then, this
test file pins the skeleton's contract:
  - Delegates to the injected CFDExecutor's `execute(task_spec)`.
  - Packages the returned ExecutionResult into a RunReport(status=OK).
  - Carries the DOCKER_OPENFOAM mode identity in the RunReport.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.executor import (
    DockerOpenFOAMExecutor,
    ExecutorMode,
    ExecutorStatus,
)
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
        name="docker_openfoam_test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )


def _make_canned_result() -> ExecutionResult:
    return ExecutionResult(
        success=True,
        is_mock=False,
        residuals={"p": 1e-6, "U": 1e-6},
        key_quantities={"u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0]},
        execution_time_s=24.8,
        raw_output_path="/tmp/cases/test_run",
    )


def test_docker_openfoam_delegates_to_injected_executor():
    """Skeleton must call the injected CFDExecutor's execute() exactly once
    with the task_spec passed in."""
    canned = _make_canned_result()
    wrapped = MagicMock(spec=["execute"])
    wrapped.execute.return_value = canned

    executor = DockerOpenFOAMExecutor(wrapped=wrapped)
    task_spec = _make_task_spec()
    report = executor.execute(task_spec)

    wrapped.execute.assert_called_once_with(task_spec)
    assert report.execution_result is canned


def test_docker_openfoam_run_report_has_correct_mode_and_status():
    """RunReport must carry DOCKER_OPENFOAM mode and OK status when the
    wrapped executor returns a successful ExecutionResult."""
    wrapped = MagicMock(spec=["execute"])
    wrapped.execute.return_value = _make_canned_result()

    executor = DockerOpenFOAMExecutor(wrapped=wrapped)
    report = executor.execute(_make_task_spec())

    assert report.mode == ExecutorMode.DOCKER_OPENFOAM
    assert report.status == ExecutorStatus.OK


def test_docker_openfoam_run_report_carries_contract_hash_and_version():
    """RunReport.contract_hash + version must match the executor's
    own properties (no drift between executor identity and report)."""
    wrapped = MagicMock(spec=["execute"])
    wrapped.execute.return_value = _make_canned_result()

    executor = DockerOpenFOAMExecutor(wrapped=wrapped)
    report = executor.execute(_make_task_spec())

    assert report.contract_hash == executor.contract_hash
    assert report.version == executor.VERSION


def test_docker_openfoam_run_report_has_empty_notes_by_default():
    """No special notes for docker_openfoam — the full triad PASS/WARN/FAIL
    routing per §6.1 happens downstream in TrustGate, not at executor time."""
    wrapped = MagicMock(spec=["execute"])
    wrapped.execute.return_value = _make_canned_result()

    executor = DockerOpenFOAMExecutor(wrapped=wrapped)
    report = executor.execute(_make_task_spec())

    assert report.notes == ()


def test_docker_openfoam_can_be_constructed_without_wrapped_arg():
    """`wrapped=None` is allowed; lazy FoamAgentExecutor() construction
    happens on first execute() call. We do not exercise the lazy path here
    (it would need Docker running) — just verify construction succeeds."""
    executor = DockerOpenFOAMExecutor()
    assert executor.MODE == ExecutorMode.DOCKER_OPENFOAM
    # contract_hash is computed without touching the wrapped field, so it
    # works even when wrapped=None.
    assert len(executor.contract_hash) == 64
