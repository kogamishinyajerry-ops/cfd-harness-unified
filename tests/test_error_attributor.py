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

    def test_airfoil_cp_outside_chord_space_maps_to_geometry_mismatch(self, attributor):
        comparison = make_comparison(
            DeviationDetail(
                quantity="pressure_coefficient[x_over_c=0.0000]",
                expected=1.0,
                actual=0.0,
                relative_error=1.0,
            )
        )

        report = attributor.attribute(
            make_task(geometry_type=GeometryType.AIRFOIL, flow_type=FlowType.EXTERNAL, Re=3e6),
            make_exec_result(
                key_quantities={
                    "pressure_coefficient": [0.0, 0.0, 0.0],
                    "pressure_coefficient_x": [-1.9, 0.0, 1.9],
                }
            ),
            comparison,
        )

        assert report.primary_cause == "geometry_model_mismatch"
        assert report.confidence == pytest.approx(0.85)


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


class TestAuditConcern:
    """EX-1-006 Path A — producer→consumer wiring.

    ErrorAttributor reads physics_contract.contract_status from the gold
    standard YAML resolved via TASK_NAME_TO_CASE_ID and attaches an
    audit_concern tag to the returned AttributionReport. The tag is
    orthogonal to verdict: never emitted on FAIL paths, never mutates
    primary_cause / confidence / secondary_causes.
    """

    def _clean_pass(self):
        return ComparisonResult(passed=True, deviations=[], summary="PASS")

    def test_silent_pass_hazard_on_pass_emits_audit_concern(self, attributor):
        task = make_task(name="Turbulent Flat Plate (Zero Pressure Gradient)")
        report = attributor.attribute(task, make_exec_result(), self._clean_pass())
        assert report.audit_concern == "COMPATIBLE_WITH_SILENT_PASS_HAZARD"

    def test_literature_disguise_on_pass_emits_audit_concern(self, attributor):
        task = make_task(name="Axisymmetric Impinging Jet (Re=10000)")
        report = attributor.attribute(task, make_exec_result(), self._clean_pass())
        assert report.audit_concern == "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE"

    def test_plain_compatible_on_pass_yields_none(self, attributor):
        task = make_task(name="Lid-Driven Cavity")
        report = attributor.attribute(task, make_exec_result(), self._clean_pass())
        assert report.audit_concern is None

    def test_fail_path_never_emits_audit_concern(self, attributor):
        """Regression: even on a silent-pass-hazard case, FAIL verdict → audit_concern None."""
        task = make_task(name="Turbulent Flat Plate (Zero Pressure Gradient)")
        comparison = make_comparison(
            DeviationDetail(
                quantity="cf_skin_friction",
                expected=0.0076,
                actual=0.002,
                relative_error=0.74,
            )
        )
        report = attributor.attribute(task, make_exec_result(), comparison)
        assert report.audit_concern is None
        # Verdict-side attribution link unaffected by producer→consumer wiring
        assert report.chain_complete is True
        assert report.primary_cause != "unknown"

    def test_unknown_task_name_yields_none(self, attributor):
        """Robustness: case_id lookup miss → None (no exception)."""
        task = make_task(name="not-a-whitelist-case")
        report = attributor.attribute(task, make_exec_result(), self._clean_pass())
        assert report.audit_concern is None
