"""tests/test_models.py — 核心数据类型测试"""

import pytest
from src.models import (
    CFDExecutor,
    Compressibility,
    ComparisonResult,
    CorrectionSpec,
    DeviationDetail,
    ErrorType,
    ExecutionResult,
    FlowType,
    GeometryType,
    ImpactScope,
    SteadyState,
    TaskSpec,
)


class TestEnums:
    def test_flow_type_values(self):
        assert FlowType.INTERNAL.value == "INTERNAL"
        assert FlowType.EXTERNAL.value == "EXTERNAL"
        assert FlowType.NATURAL_CONVECTION.value == "NATURAL_CONVECTION"

    def test_geometry_type_values(self):
        assert GeometryType.SIMPLE_GRID.value == "SIMPLE_GRID"
        assert GeometryType.BACKWARD_FACING_STEP.value == "BACKWARD_FACING_STEP"
        assert GeometryType.BODY_IN_CHANNEL.value == "BODY_IN_CHANNEL"
        assert GeometryType.CUSTOM.value == "CUSTOM"

    def test_steady_state_values(self):
        assert SteadyState.STEADY.value == "STEADY"
        assert SteadyState.TRANSIENT.value == "TRANSIENT"

    def test_compressibility_values(self):
        assert Compressibility.INCOMPRESSIBLE.value == "INCOMPRESSIBLE"
        assert Compressibility.COMPRESSIBLE.value == "COMPRESSIBLE"

    def test_error_type_coverage(self):
        expected = {
            "WRONG_BOUNDARY", "WRONG_SOLVER", "WRONG_TURBULENCE_MODEL",
            "WRONG_MESH", "CONVERGENCE_FAILURE", "QUANTITY_DEVIATION",
            "PARAMETER_PLUMBING_MISMATCH", "COMPARATOR_SCHEMA_MISMATCH",
            "GEOMETRY_MODEL_MISMATCH", "INSUFFICIENT_TRANSIENT_SAMPLING",
            "BUOYANT_ENERGY_SETUP_INCOMPLETE", "OTHER"
        }
        assert {e.value for e in ErrorType} == expected

    def test_impact_scope_values(self):
        assert ImpactScope.LOCAL.value == "LOCAL"
        assert ImpactScope.CLASS.value == "CLASS"
        assert ImpactScope.GLOBAL.value == "GLOBAL"


class TestTaskSpec:
    def _make_spec(self, **kwargs):
        defaults = dict(
            name="test",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
        )
        defaults.update(kwargs)
        return TaskSpec(**defaults)

    def test_default_fields(self):
        spec = self._make_spec()
        assert spec.Re is None
        assert spec.Ma is None
        assert spec.boundary_conditions == {}
        assert spec.description == ""
        assert spec.notion_task_id is None

    def test_with_re(self):
        spec = self._make_spec(Re=100.0)
        assert spec.Re == 100.0

    def test_boundary_conditions_independent(self):
        spec1 = self._make_spec()
        spec2 = self._make_spec()
        spec1.boundary_conditions["a"] = 1
        assert "a" not in spec2.boundary_conditions


class TestExecutionResult:
    def test_mock_result(self):
        r = ExecutionResult(success=True, is_mock=True)
        assert r.success
        assert r.is_mock
        assert r.residuals == {}
        assert r.key_quantities == {}
        assert r.execution_time_s == 0.0
        assert r.raw_output_path is None
        assert r.error_message is None

    def test_failed_result(self):
        r = ExecutionResult(success=False, is_mock=False, error_message="timeout")
        assert not r.success
        assert r.error_message == "timeout"


class TestComparisonResult:
    def test_passed(self):
        cr = ComparisonResult(passed=True, summary="ok")
        assert cr.passed
        assert cr.deviations == []

    def test_with_deviations(self):
        d = DeviationDetail(quantity="u", expected=1.0, actual=1.2, relative_error=0.2)
        cr = ComparisonResult(passed=False, deviations=[d])
        assert not cr.passed
        assert cr.deviations[0].quantity == "u"


class TestCFDExecutorProtocol:
    def test_mock_implements_protocol(self):
        from src.foam_agent_adapter import MockExecutor
        executor = MockExecutor()
        assert isinstance(executor, CFDExecutor)
