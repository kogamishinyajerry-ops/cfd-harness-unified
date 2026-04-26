"""Tests for `src.executor.FutureRemoteExecutor` (P2-T1 skeleton).

Per EXECUTOR_ABSTRACTION.md §6.1, `future_remote` is stub-only this
milestone — every execute() call returns `MODE_NOT_YET_IMPLEMENTED`.
DEC-V61-078 (P2-T5) will document the HPC contract; no real
implementation lands this milestone.
"""

from __future__ import annotations

from src.executor import (
    ExecutorMode,
    ExecutorStatus,
    FutureRemoteExecutor,
)
from src.models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)


def _make_task_spec() -> TaskSpec:
    return TaskSpec(
        name="future_remote_test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )


def test_future_remote_skeleton_returns_mode_not_yet_implemented():
    """§6.1 stub-only: every call returns MODE_NOT_YET_IMPLEMENTED."""
    report = FutureRemoteExecutor().execute(_make_task_spec())
    assert report.status == ExecutorStatus.MODE_NOT_YET_IMPLEMENTED


def test_future_remote_skeleton_has_correct_mode():
    report = FutureRemoteExecutor().execute(_make_task_spec())
    assert report.mode == ExecutorMode.FUTURE_REMOTE


def test_future_remote_skeleton_execution_result_is_none():
    """RunReport.__post_init__ enforces non-OK → execution_result=None."""
    report = FutureRemoteExecutor().execute(_make_task_spec())
    assert report.execution_result is None


def test_future_remote_skeleton_attaches_stub_note():
    """`future_remote_stub_only` is the §6.1 'TrustGate refuses to
    score' signal. P2-T1.b TrustGate routing reads this note + the
    status to surface `mode_not_yet_implemented` in the UI."""
    report = FutureRemoteExecutor().execute(_make_task_spec())
    assert "future_remote_stub_only" in report.notes


def test_future_remote_skeleton_carries_contract_hash_and_version():
    """Even for a stub refusal, contract identity must be preserved."""
    executor = FutureRemoteExecutor()
    report = executor.execute(_make_task_spec())
    assert report.contract_hash == executor.contract_hash
    assert report.version == executor.VERSION
