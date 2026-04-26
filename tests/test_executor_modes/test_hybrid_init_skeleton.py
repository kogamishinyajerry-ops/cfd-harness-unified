"""Tests for `src.executor.HybridInitExecutor` (P2-T1 skeleton).

Skeleton always returns `MODE_NOT_APPLICABLE` per EXECUTOR_ABSTRACTION.md
§5.2: no surrogate exists yet → no case can satisfy the §5.1
byte-equality invariant → every case is "malformed for hybrid-init use"
by the strict reading. P2-T4 (DEC-V61-077) lands the real surrogate.
"""

from __future__ import annotations

from src.executor import (
    ExecutorMode,
    ExecutorStatus,
    HybridInitExecutor,
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
        name="hybrid_init_test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )


def test_hybrid_init_skeleton_returns_mode_not_applicable():
    """§5.2 escape: skeleton returns MODE_NOT_APPLICABLE for every case."""
    report = HybridInitExecutor().execute(_make_task_spec())
    assert report.status == ExecutorStatus.MODE_NOT_APPLICABLE


def test_hybrid_init_skeleton_has_correct_mode():
    report = HybridInitExecutor().execute(_make_task_spec())
    assert report.mode == ExecutorMode.HYBRID_INIT


def test_hybrid_init_skeleton_execution_result_is_none():
    """Per RunReport.__post_init__: non-OK status MUST have
    execution_result=None. The skeleton doesn't run a solver."""
    report = HybridInitExecutor().execute(_make_task_spec())
    assert report.execution_result is None


def test_hybrid_init_skeleton_attaches_distinguishing_note():
    """`hybrid_init_skeleton_no_surrogate` distinguishes the skeleton's
    blanket refusal from a P2-T4-era case-specific MODE_NOT_APPLICABLE.
    Without this note, a future TrustGate routing path could confuse
    skeleton-era refusals with real-era refusals."""
    report = HybridInitExecutor().execute(_make_task_spec())
    assert "hybrid_init_skeleton_no_surrogate" in report.notes


def test_hybrid_init_skeleton_carries_contract_hash_and_version():
    """Even for a refusal, the report must carry contract identity so
    P2-T1.b's manifest-tagging integration sees the right `executor`
    field metadata."""
    executor = HybridInitExecutor()
    report = executor.execute(_make_task_spec())
    assert report.contract_hash == executor.contract_hash
    assert report.version == executor.VERSION
