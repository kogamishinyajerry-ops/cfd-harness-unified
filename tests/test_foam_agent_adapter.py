"""tests/test_foam_agent_adapter.py — MockExecutor 和 FoamAgentExecutor 测试"""

import pytest
from src.foam_agent_adapter import FoamAgentExecutor, MockExecutor
from src.models import (
    CFDExecutor, Compressibility, FlowType, GeometryType,
    SteadyState, TaskSpec,
)


def make_task(flow_type: FlowType = FlowType.INTERNAL) -> TaskSpec:
    return TaskSpec(
        name="test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=flow_type,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
    )


class TestMockExecutor:
    def test_implements_protocol(self):
        assert isinstance(MockExecutor(), CFDExecutor)

    def test_internal_flow(self):
        result = MockExecutor().execute(make_task(FlowType.INTERNAL))
        assert result.success
        assert result.is_mock
        assert "u_centerline" in result.key_quantities
        assert result.execution_time_s > 0

    def test_external_flow(self):
        result = MockExecutor().execute(make_task(FlowType.EXTERNAL))
        assert result.success
        assert "strouhal_number" in result.key_quantities

    def test_natural_convection(self):
        result = MockExecutor().execute(make_task(FlowType.NATURAL_CONVECTION))
        assert result.success
        assert "nusselt_number" in result.key_quantities

    def test_residuals_present(self):
        result = MockExecutor().execute(make_task())
        assert isinstance(result.residuals, dict)
        assert len(result.residuals) > 0

    def test_raw_output_path_is_none(self):
        result = MockExecutor().execute(make_task())
        assert result.raw_output_path is None

    def test_independent_results(self):
        ex = MockExecutor()
        r1 = ex.execute(make_task(FlowType.INTERNAL))
        r2 = ex.execute(make_task(FlowType.INTERNAL))
        r1.key_quantities["u_centerline"] = None
        # r2 不受影响（dict 是独立副本）
        assert r2.key_quantities["u_centerline"] is not None


class TestFoamAgentExecutor:
    def test_foam_agent_not_found_returns_failed_result(self):
        """foam-agent 不可用时返回 success=False 的 ExecutionResult，不 crash。"""
        executor = FoamAgentExecutor()
        result = executor.execute(make_task())
        assert result.success is False
        assert result.is_mock is False
        assert result.error_message is not None
        assert "foam-agent" in result.error_message.lower()

    def test_not_protocol_instance_by_default(self):
        # FoamAgentExecutor 有 execute 方法，所以也满足 Protocol
        assert isinstance(FoamAgentExecutor(), CFDExecutor)
