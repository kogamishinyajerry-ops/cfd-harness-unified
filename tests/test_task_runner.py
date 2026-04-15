"""tests/test_task_runner.py — TaskRunner 单元测试"""

import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

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


class TestRunTask:
    def test_returns_run_report(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert isinstance(report, RunReport)

    def test_exec_result_is_mock(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.execution_result.is_mock

    def test_comparison_runs_when_gold_exists(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.comparison_result is not None

    def test_no_comparison_when_no_gold(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task(name="Unknown Task"))
        assert report.comparison_result is None

    def test_summary_not_empty(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert len(report.summary) > 0

    def test_notion_write_skipped_gracefully(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        # Notion not configured → should not raise
        report = runner.run_task(make_task())
        assert report is not None

    def test_correction_generated_on_deviation(self, mock_db):
        # 返回偏差很大的结果
        class BadExecutor:
            def execute(self, task_spec):
                return ExecutionResult(
                    success=True, is_mock=True,
                    key_quantities={"u_centerline": [9999.0]},  # way off
                )
        runner = TaskRunner(executor=BadExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.correction_spec is not None

    def test_no_correction_when_pass(self, mock_db):
        # 返回精确匹配的结果
        class PerfectExecutor:
            def execute(self, task_spec):
                return ExecutionResult(
                    success=True, is_mock=True,
                    key_quantities={"u_centerline": [0.025]},
                )
        runner = TaskRunner(executor=PerfectExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.correction_spec is None


class TestRunAll:
    def test_run_all_no_notion(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
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
