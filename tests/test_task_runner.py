"""tests/test_task_runner.py — TaskRunner 单元测试"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.task_runner import TaskRunner, RunReport
from src.foam_agent_adapter import FoamAgentExecutor, MockExecutor
from src.models import (
    Compressibility, ComparisonResult, CorrectionSpec, DeviationDetail,
    ErrorType, ExecutionResult, FlowType, GeometryType,
    ImpactScope, SteadyState, TaskSpec,
)


def make_task(name="Lid-Driven Cavity"):
    return TaskSpec(
        name=name,
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
        notion_task_id="task-1",
    )


class StaticExecutor:
    def __init__(self, result):
        self._result = result

    def execute(self, task_spec):
        return self._result


def _write_solver_log(tmp_path: Path, content: str) -> Path:
    output_dir = tmp_path / "solver_output"
    output_dir.mkdir()
    (output_dir / "log.simpleFoam").write_text(content, encoding="utf-8")
    return output_dir


def _make_stubbed_runner(
    execution_result: ExecutionResult,
    *,
    gold=None,
    case_id: str = "lid_driven_cavity",
    case_name: str = "Lid-Driven Cavity",
    comparison_result: ComparisonResult | None = None,
):
    notion = MagicMock()
    notion.write_execution_result.side_effect = NotImplementedError("Notion not configured")
    notion.list_pending_tasks.side_effect = NotImplementedError("Notion not configured")

    chain = {
        "case_id": case_id,
        "case_name": case_name,
        "geometry_type": "SIMPLE_GRID",
        "flow_type": "INTERNAL",
        "steady_state": "STEADY",
        "compressibility": "INCOMPRESSIBLE",
        "parameters": {"Re": 100},
        "boundary_conditions": {},
        "reference": "",
    }
    db = MagicMock()
    db.get_execution_chain.side_effect = lambda _: chain
    db.load_gold_standard.side_effect = (
        lambda key: gold if gold is not None and key in {case_id, case_name} else None
    )

    runner = TaskRunner(
        executor=StaticExecutor(execution_result),
        notion_client=notion,
        knowledge_db=db,
    )
    runner._comparator = MagicMock()
    runner._comparator.compare.return_value = (
        comparison_result or ComparisonResult(passed=True, summary="comparison ok")
    )
    runner._recorder = MagicMock()
    runner._attributor = MagicMock()
    return runner


@pytest.fixture
def mock_db(tmp_path):
    from src.knowledge_db import KnowledgeDB
    import yaml
    wl = {"cases": [
        {
            "id": "lid_driven_cavity",
            "name": "Lid-Driven Cavity",
            "flow_type": "INTERNAL",
            "geometry_type": "SIMPLE_GRID",
            "compressibility": "INCOMPRESSIBLE",
            "steady_state": "STEADY",
            "parameters": {"Re": 100},
            "gold_standard": {
                "quantity": "u_centerline",
                "reference_values": [{"y": 0.5, "u": 0.025}],
                "tolerance": 0.05,
            },
        }
    ]}
    (tmp_path / "whitelist.yaml").write_text(yaml.dump(wl))
    (tmp_path / "corrections").mkdir()
    return KnowledgeDB(knowledge_dir=tmp_path)


@pytest.fixture
def stub_notion():
    """Unconfigured NotionClient stub — raises NotImplementedError for any API call.

    TaskRunner swallows NotImplementedError from write_execution_result and
    list_pending_tasks, so injecting this keeps tests hermetic regardless of
    whether NOTION_TOKEN is set in the dev environment.
    """
    client = MagicMock()
    client.write_execution_result.side_effect = NotImplementedError("Notion not configured")
    client.list_pending_tasks.side_effect = NotImplementedError("Notion not configured")
    return client


class TestRunTask:
    def test_returns_run_report(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert isinstance(report, RunReport)

    def test_exec_result_is_mock(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.execution_result.is_mock

    def test_comparison_runs_when_gold_exists(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.comparison_result is not None

    def test_no_comparison_when_no_gold(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task(name="Unknown Task"))
        assert report.comparison_result is None

    def test_summary_not_empty(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert len(report.summary) > 0

    def test_notion_write_skipped_gracefully(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        # Notion not configured → should not raise
        report = runner.run_task(make_task())
        assert report is not None

    def test_correction_generated_on_deviation(self, mock_db, stub_notion):
        # 返回偏差很大的结果
        class BadExecutor:
            def execute(self, task_spec):
                return ExecutionResult(
                    success=True, is_mock=True,
                    key_quantities={"u_centerline": [9999.0]},  # way off
                )
        runner = TaskRunner(executor=BadExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.correction_spec is not None

    def test_no_correction_when_pass(self, mock_db, stub_notion):
        # 返回精确匹配的结果
        class PerfectExecutor:
            def execute(self, task_spec):
                return ExecutionResult(
                    success=True, is_mock=True,
                    key_quantities={"u_centerline": [0.025]},
                )
        runner = TaskRunner(executor=PerfectExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.correction_spec is None

    def test_run_task_attestor_pass_path_completes_pipeline(self, tmp_path):
        log_dir = _write_solver_log(
            tmp_path,
            "Time = 1\nExecutionTime = 1 s\nEnd\n",
        )
        exec_result = ExecutionResult(
            success=True,
            is_mock=False,
            key_quantities={"u_centerline": [0.025]},
            raw_output_path=str(log_dir),
            exit_code=0,
        )
        runner = _make_stubbed_runner(exec_result, gold=object())

        report = runner.run_task(make_task())

        assert report.attestation is not None
        assert report.attestation.overall == "ATTEST_PASS"
        assert report.comparison_result is not None
        runner._comparator.compare.assert_called_once()

    def test_run_task_attestor_fail_short_circuits_comparator(self, tmp_path):
        log_dir = _write_solver_log(
            tmp_path,
            "Time = 1\nFOAM FATAL ERROR: missing dict\nExiting\n",
        )
        exec_result = ExecutionResult(
            success=True,
            is_mock=False,
            key_quantities={"u_centerline": [0.025]},
            raw_output_path=str(log_dir),
            exit_code=0,
        )
        runner = _make_stubbed_runner(exec_result, gold=object())
        runner._comparator.compare.side_effect = AssertionError("compare must not run")

        report = runner.run_task(make_task())

        assert report.attestation is not None
        assert report.attestation.overall == "ATTEST_FAIL"
        assert report.comparison_result is None
        assert report.correction_spec is None
        runner._comparator.compare.assert_not_called()

    def test_run_task_attestor_hazard_does_not_short_circuit(self, tmp_path):
        log_dir = _write_solver_log(
            tmp_path,
            (
                "Time = 1\n"
                "time step continuity errors : "
                "sum local = 5e-04, global = 1e-06, cumulative = 1e-06\n"
                "ExecutionTime = 1 s\n"
                "End\n"
            ),
        )
        exec_result = ExecutionResult(
            success=True,
            is_mock=False,
            key_quantities={"u_centerline": [0.025]},
            raw_output_path=str(log_dir),
            exit_code=0,
        )
        runner = _make_stubbed_runner(exec_result, gold=object())

        report = runner.run_task(make_task())

        assert report.attestation is not None
        assert report.attestation.overall == "ATTEST_HAZARD"
        assert report.comparison_result is not None
        runner._comparator.compare.assert_called_once()

    def test_run_task_attestor_not_applicable_when_no_log(self):
        exec_result = ExecutionResult(
            success=True,
            is_mock=False,
            key_quantities={"u_centerline": [0.025]},
            raw_output_path=None,
            exit_code=0,
        )
        runner = _make_stubbed_runner(exec_result, gold=object())

        report = runner.run_task(make_task())

        assert report.attestation is not None
        assert report.attestation.overall == "ATTEST_NOT_APPLICABLE"
        assert report.comparison_result is not None
        runner._comparator.compare.assert_called_once()

    def test_run_task_attestor_not_applicable_when_raw_output_nonexistent(self, tmp_path):
        exec_result = ExecutionResult(
            success=True,
            is_mock=False,
            key_quantities={"u_centerline": [0.025]},
            raw_output_path=str(tmp_path / "missing-output"),
            exit_code=0,
        )
        runner = _make_stubbed_runner(exec_result, gold=object())

        report = runner.run_task(make_task())

        assert report.attestation is not None
        assert report.attestation.overall == "ATTEST_NOT_APPLICABLE"
        assert report.comparison_result is not None
        runner._comparator.compare.assert_called_once()


class TestRunAll:
    def test_run_all_no_notion(self, mock_db, stub_notion):
        runner = TaskRunner(executor=MockExecutor(), notion_client=stub_notion, knowledge_db=mock_db)
        # Notion not configured → empty list
        reports = runner.run_all()
        assert reports == []

    def test_run_all_with_mock_notion(self, mock_db):
        notion = MagicMock()
        notion.list_pending_tasks.return_value = [make_task(), make_task(name="Circular Cylinder Wake")]
        notion.write_execution_result.return_value = None
        runner = TaskRunner(executor=MockExecutor(), notion_client=notion, knowledge_db=mock_db)
        reports = runner.run_all()
        assert len(reports) == 2


class TestBuildSummary:
    def test_success_no_comparison(self):
        result = ExecutionResult(success=True, is_mock=True, execution_time_s=1.0)
        summary = TaskRunner._build_summary(result, None, None)
        assert "Success" in summary

    def test_fail_status(self):
        result = ExecutionResult(success=False, is_mock=False)
        summary = TaskRunner._build_summary(result, None, None)
        assert "Failed" in summary

    def test_comparison_pass(self):
        result = ExecutionResult(success=True, is_mock=True)
        comparison = ComparisonResult(passed=True, summary="ok")
        summary = TaskRunner._build_summary(result, comparison, None)
        assert "PASS" in summary

    def test_correction_in_summary(self):
        result = ExecutionResult(success=True, is_mock=True)
        comparison = ComparisonResult(passed=False, deviations=[
            DeviationDetail(quantity="x", expected=1.0, actual=2.0)
        ])
        correction = CorrectionSpec(
            error_type=ErrorType.QUANTITY_DEVIATION,
            wrong_output={}, correct_output={},
            human_reason="", evidence="",
            impact_scope=ImpactScope.LOCAL,
            root_cause="", fix_action="",
        )
        summary = TaskRunner._build_summary(result, comparison, correction)
        assert "CorrectionSpec" in summary


class TestRunReportSchema:
    def test_runreport_attestation_field_optional(self):
        report = RunReport(
            task_spec=make_task(),
            execution_result=ExecutionResult(success=True, is_mock=True),
            comparison_result=None,
            correction_spec=None,
            summary="ok",
        )

        assert report.attestation is None


class TestExecutorMode:
    def test_executor_mode_env_mock(self, mock_db):
        with patch.dict(os.environ, {"EXECUTOR_MODE": "mock"}):
            runner = TaskRunner(knowledge_db=mock_db)
            assert isinstance(runner._executor, MockExecutor)

    def test_executor_mode_env_foam_agent(self, mock_db):
        with patch.dict(os.environ, {"EXECUTOR_MODE": "foam_agent"}, clear=False):
            runner = TaskRunner(knowledge_db=mock_db)
            assert isinstance(runner._executor, FoamAgentExecutor)

    def test_executor_mode_env_invalid_raises(self, mock_db):
        with patch.dict(os.environ, {"EXECUTOR_MODE": "invalid_mode"}):
            with pytest.raises(ValueError, match="EXECUTOR_MODE"):
                TaskRunner(knowledge_db=mock_db)

    def test_executor_kwarg_overrides_env(self, mock_db):
        """explicit executor= takes precedence over EXECUTOR_MODE"""
        with patch.dict(os.environ, {"EXECUTOR_MODE": "foam_agent"}):
            runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
            assert isinstance(runner._executor, MockExecutor)


class TestRunBatchAttestation:
    def test_run_batch_blocks_backdoor_comparison_on_attest_fail(self, tmp_path):
        log_dir = _write_solver_log(
            tmp_path,
            "Time = 1\nFOAM FATAL ERROR: segmentation fault\nEnd\n",
        )
        exec_result = ExecutionResult(
            success=True,
            is_mock=False,
            key_quantities={"u_centerline": [0.025]},
            raw_output_path=str(log_dir),
            exit_code=0,
        )
        runner = _make_stubbed_runner(exec_result, gold=object())
        runner._comparator.compare.side_effect = AssertionError("compare must not run")
        runner._attributor.attribute.return_value = None

        batch = runner.run_batch(["lid_driven_cavity"])

        assert batch.failed == 1
        assert len(batch.results) == 1
        assert batch.results[0].summary == (
            "Comparison skipped because attestation failed before extraction"
        )
        runner._comparator.compare.assert_not_called()
