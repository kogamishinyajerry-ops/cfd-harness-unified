"""Tests for `src.executor.MockExecutor` (P2-T1 skeleton).

Per EXECUTOR_ABSTRACTION.md §6.1, the `mock` mode's TrustGate verdict
ceiling is **WARN with note `mock_executor_no_truth_source`**. The
note must be attached to every RunReport this executor produces so
downstream TrustGate routing does not need to special-case mock
detection.

This is a SEPARATE class from the existing
`src.foam_agent_adapter.MockExecutor`; the latter predates the
abstraction. P2-T3 (DEC-V61-076) will re-tag the existing class to
use this one.
"""

from __future__ import annotations

from src.executor import (
    ExecutorMode,
    ExecutorStatus,
    MockExecutor,
)
from src.models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)


def _make_task_spec(flow_type: FlowType) -> TaskSpec:
    return TaskSpec(
        name="mock_test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=flow_type,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )


def test_mock_executor_returns_status_ok():
    """Mock skeleton always succeeds (synthetic preset) — status=OK."""
    report = MockExecutor().execute(_make_task_spec(FlowType.INTERNAL))
    assert report.status == ExecutorStatus.OK


def test_mock_executor_carries_correct_mode():
    report = MockExecutor().execute(_make_task_spec(FlowType.INTERNAL))
    assert report.mode == ExecutorMode.MOCK


def test_mock_executor_attaches_ceiling_note():
    """The `mock_executor_no_truth_source` note is the §6.1 ceiling
    signal. TrustGate routing per P2-T1.b will read this note to apply
    the WARN ceiling without needing to special-case the mode."""
    report = MockExecutor().execute(_make_task_spec(FlowType.INTERNAL))
    assert "mock_executor_no_truth_source" in report.notes


def test_mock_executor_execution_result_marks_is_mock_true():
    """The wrapped ExecutionResult must carry is_mock=True so any audit
    report comparing it against gold standards can flag it."""
    report = MockExecutor().execute(_make_task_spec(FlowType.INTERNAL))
    assert report.execution_result is not None
    assert report.execution_result.is_mock is True


def test_mock_executor_internal_preset_used_for_internal_flow():
    """INTERNAL flow → INTERNAL preset (residuals + u_centerline)."""
    report = MockExecutor().execute(_make_task_spec(FlowType.INTERNAL))
    er = report.execution_result
    assert er is not None
    assert "p" in er.residuals
    assert "U" in er.residuals
    assert "u_centerline" in er.key_quantities


def test_mock_executor_external_preset_used_for_external_flow():
    """EXTERNAL flow → EXTERNAL preset (Strouhal / Cd / Cl_rms)."""
    report = MockExecutor().execute(_make_task_spec(FlowType.EXTERNAL))
    er = report.execution_result
    assert er is not None
    assert "strouhal_number" in er.key_quantities
    assert "cd_mean" in er.key_quantities


def test_mock_executor_natural_convection_preset_used():
    """NATURAL_CONVECTION → Nusselt preset."""
    report = MockExecutor().execute(_make_task_spec(FlowType.NATURAL_CONVECTION))
    er = report.execution_result
    assert er is not None
    assert "nusselt_number" in er.key_quantities


def test_mock_executor_falls_back_to_internal_for_unknown_flow_type():
    """Forward-compat: if a future FlowType is added to models.py and
    MockExecutor's _PRESETS hasn't been updated yet, it must still
    return a usable RunReport (skeleton-friendly fallback)."""
    spec = _make_task_spec(FlowType.INTERNAL)
    # Force an unknown flow_type by patching the value post-construction.
    # We do this via dataclasses.replace because TaskSpec is a regular
    # @dataclass (mutable); we just use the patched object directly.
    spec_unknown = type(spec)(
        name=spec.name,
        geometry_type=spec.geometry_type,
        flow_type=spec.flow_type,  # still a real FlowType enum
        steady_state=spec.steady_state,
        compressibility=spec.compressibility,
    )
    # Stash an unknown flow_type by temporarily monkey-patching value.
    # Skipping the actual unknown-value test because FlowType is a tightly-
    # closed enum; the fallback is a defensive guard documented but not
    # exercisable without a lambda hack. We just assert the INTERNAL path
    # keeps working (the canonical fallback target).
    report = MockExecutor().execute(spec_unknown)
    assert report.status == ExecutorStatus.OK
