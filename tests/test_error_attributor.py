"""tests/test_error_attributor.py — ErrorAttributor 直接单元测试"""

from unittest.mock import Mock

import pytest

from src.error_attributor import ErrorAttributor
from src.knowledge_db import KnowledgeDB
from src.models import (
    ComparisonResult,
    Compressibility,
    DeviationDetail,
    ErrorType,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)


@pytest.fixture
def mock_knowledge_db(tmp_path):
    db = Mock(spec=KnowledgeDB)
    db.query_cases.return_value = [{"id": "case-a"}, {"id": "case-b"}]
    db.list_solver_for_geometry.return_value = ["simpleFoam", "pimpleFoam"]
    db.list_turbulence_models.return_value = {
        GeometryType.SIMPLE_GRID.value: ["laminar", "k-epsilon"],
        GeometryType.BACKWARD_FACING_STEP.value: ["k-omega SST"],
        GeometryType.NATURAL_CONVECTION_CAVITY.value: ["k-omega SST"],
    }
    db.get_execution_chain.return_value = {
        "turbulence_model": "k-epsilon",
        "workspace": str(tmp_path),
    }
    db.get_solver_for_case.return_value = "buoyantSimpleFoam"
    return db


@pytest.fixture
def attributor(mock_knowledge_db):
    return ErrorAttributor(knowledge_db=mock_knowledge_db)


def make_task(**kwargs):
    defaults = dict(
        name="fixture-case",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=1000.0,
    )
    defaults.update(kwargs)
    return TaskSpec(**defaults)


def make_exec_result(**kwargs):
    defaults = dict(
        success=True,
        is_mock=False,
        residuals={"U": 1e-6},
        key_quantities={"u_centerline": [0.1, 0.2]},
        execution_time_s=1.0,
    )
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


def make_comparison(*deviations, passed=False, summary="comparison failed"):
    return ComparisonResult(
        passed=passed,
        deviations=list(deviations),
        summary=summary,
    )


class TestErrorTypes:
    def test_error_type_enum_coverage(self):
        expected = {
            "WRONG_BOUNDARY",
            "WRONG_SOLVER",
            "WRONG_TURBULENCE_MODEL",
            "WRONG_MESH",
            "CONVERGENCE_FAILURE",
            "QUANTITY_DEVIATION",
            "PARAMETER_PLUMBING_MISMATCH",
            "COMPARATOR_SCHEMA_MISMATCH",
            "GEOMETRY_MODEL_MISMATCH",
            "INSUFFICIENT_TRANSIENT_SAMPLING",
            "BUOYANT_ENERGY_SETUP_INCOMPLETE",
            "OTHER",
        }
        assert {error.value for error in ErrorType} == expected


class TestBuoyantEnergySetup:
    def test_missing_p_rgh_surfaces_buoyant_cause(self, attributor):
        task = make_task(
            flow_type=FlowType.NATURAL_CONVECTION,
            geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
        )
        exec_result = make_exec_result(
            success=False,
            error_message='Cannot find file "/tmp/case/0/p_rgh"',
            key_quantities={},
        )

        report = attributor.attribute(task, exec_result, make_comparison())

        assert report.chain_complete is True
        assert "buoyant" in report.primary_cause


class TestComparatorSchemaMismatch:
    def test_actual_none_maps_to_comparator_schema_mismatch(self, attributor):
        comparison = make_comparison(
            DeviationDetail(
                quantity="nusselt_number",
                expected=12.0,
                actual=None,
                relative_error=None,
            )
        )

        report = attributor.attribute(
            make_task(),
            make_exec_result(key_quantities={}),
            comparison,
        )

        assert report.primary_cause == "comparator_schema_mismatch"
        assert report.confidence == pytest.approx(0.8)


class TestGeometryModelMismatch:
    def test_bfs_reattachment_length_maps_to_geometry_mismatch(self, attributor):
        comparison = make_comparison(
            DeviationDetail(
                quantity="reattachment_length",
                expected=6.0,
                actual=2.5,
                relative_error=0.58,
            )
        )

        report = attributor.attribute(
            make_task(geometry_type=GeometryType.BACKWARD_FACING_STEP),
            make_exec_result(),
            comparison,
        )

        assert report.primary_cause == "geometry_model_mismatch"
        assert report.confidence == pytest.approx(0.75)


class TestInsufficientTransientSampling:
    def test_transient_case_without_strouhal_maps_to_sampling_issue(self, attributor):
        comparison = make_comparison(
            DeviationDetail(
                quantity="lift_coefficient_rms",
                expected=0.3,
                actual=0.1,
                relative_error=0.67,
            )
        )
        exec_result = make_exec_result(
            key_quantities={"lift_coefficient": [0.1, 0.2]}
        )

        report = attributor.attribute(
            make_task(steady_state=SteadyState.TRANSIENT),
            exec_result,
            comparison,
        )

        assert report.primary_cause == "insufficient_transient_sampling"
        assert report.confidence == pytest.approx(0.75)


class TestParameterPlumbingMismatch:
    def test_ra_with_deviations_maps_to_parameter_plumbing_mismatch(self, attributor):
        comparison = make_comparison(
            DeviationDetail(
                quantity="nusselt_number",
                expected=8.8,
                actual=4.1,
                relative_error=0.53,
            )
        )

        report = attributor.attribute(
            make_task(
                flow_type=FlowType.NATURAL_CONVECTION,
                geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
                Ra=1e6,
            ),
            make_exec_result(),
            comparison,
        )

        assert report.primary_cause == "parameter_plumbing_mismatch"
        assert report.confidence == pytest.approx(0.7)


class TestChainComplete:
    def test_successful_attribution_sets_chain_complete(self, attributor):
        comparison = make_comparison(
            DeviationDetail(
                quantity="u_centerline",
                expected=0.5,
                actual=0.3,
                relative_error=0.4,
            )
        )

        report = attributor.attribute(make_task(), make_exec_result(), comparison)

        assert report.chain_complete is True
