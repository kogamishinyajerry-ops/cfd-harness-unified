"""tests/test_correction_recorder.py — CorrectionRecorder 单元测试"""

import pytest
from src.correction_recorder import CorrectionRecorder
from src.models import (
    Compressibility, ComparisonResult, DeviationDetail,
    ErrorType, ExecutionResult, FlowType, GeometryType,
    ImpactScope, SteadyState, TaskSpec,
)


def make_task(**kwargs):
    defaults = dict(
        name="Lid-Driven Cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
    )
    defaults.update(kwargs)
    return TaskSpec(**defaults)


def make_exec_result(success=True, **kq):
    return ExecutionResult(
        success=success, is_mock=True,
        residuals={"p": 1e-6},
        key_quantities=kq or {"u_centerline": [0.1]},
    )


def make_comparison(passed=False, n_deviations=1):
    deviations = [
        DeviationDetail(quantity=f"u[{i}]", expected=0.025, actual=0.1, relative_error=3.0)
        for i in range(n_deviations)
    ]
    return ComparisonResult(passed=passed, deviations=deviations, summary="test")


class TestRecord:
    def test_returns_correction_spec(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison())
        from src.models import CorrectionSpec
        assert isinstance(spec, CorrectionSpec)

    def test_task_name_recorded(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(name="MyCase"), make_exec_result(), make_comparison())
        assert spec.task_spec_name == "MyCase"

    def test_created_at_set(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison())
        assert spec.created_at is not None
        assert "Z" in spec.created_at

    def test_needs_replay_true(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison())
        assert spec.needs_replay is True

    def test_convergence_failure_on_bad_result(self):
        rec = CorrectionRecorder()
        failed = make_exec_result(success=False)
        spec = rec.record(make_task(), failed, make_comparison())
        assert spec.error_type == ErrorType.CONVERGENCE_FAILURE

    def test_quantity_deviation_on_compare_fail(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison(n_deviations=1))
        assert spec.error_type == ErrorType.QUANTITY_DEVIATION

    def test_impact_local_single_deviation(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison(n_deviations=1))
        assert spec.impact_scope == ImpactScope.LOCAL

    def test_impact_class_many_deviations(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison(n_deviations=3))
        assert spec.impact_scope == ImpactScope.CLASS

    def test_wrong_output_contains_quantities(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(u_centerline=[0.1]), make_comparison())
        assert "key_quantities" in spec.wrong_output

    def test_correct_output_from_deviations(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison(n_deviations=1))
        assert len(spec.correct_output) == 1

    def test_evidence_not_empty(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison())
        assert len(spec.evidence) > 0

    def test_fix_action_not_empty(self):
        rec = CorrectionRecorder()
        spec = rec.record(make_task(), make_exec_result(), make_comparison())
        assert len(spec.fix_action) > 0
