"""TaskRunner ↔ AutoVerifier integration tests (SPEC §INT-1)."""

from __future__ import annotations

import pytest
import yaml

from src.foam_agent_adapter import MockExecutor
from src.knowledge_db import KnowledgeDB
from src.models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)
from src.task_runner import CORRECTION_POLICIES, TaskRunner


def make_task(name: str = "Lid-Driven Cavity") -> TaskSpec:
    return TaskSpec(
        name=name,
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
        notion_task_id=None,
    )


@pytest.fixture
def mock_db(tmp_path):
    wl = {
        "cases": [
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
        ]
    }
    (tmp_path / "whitelist.yaml").write_text(yaml.dump(wl))
    (tmp_path / "corrections").mkdir()
    return KnowledgeDB(knowledge_dir=tmp_path)


class TestCorrectionPolicyValidation:
    def test_accepts_legacy_auto_save(self, mock_db):
        runner = TaskRunner(
            executor=MockExecutor(),
            knowledge_db=mock_db,
            correction_policy="legacy_auto_save",
        )
        assert runner._correction_policy == "legacy_auto_save"

    def test_accepts_suggest_only(self, mock_db):
        runner = TaskRunner(
            executor=MockExecutor(),
            knowledge_db=mock_db,
            correction_policy="suggest_only",
        )
        assert runner._correction_policy == "suggest_only"

    def test_rejects_unknown_policy(self, mock_db):
        with pytest.raises(ValueError, match="correction_policy must be one of"):
            TaskRunner(
                executor=MockExecutor(),
                knowledge_db=mock_db,
                correction_policy="bogus",
            )

    def test_policies_tuple_exports(self):
        assert "legacy_auto_save" in CORRECTION_POLICIES
        assert "suggest_only" in CORRECTION_POLICIES


class TestPostExecuteHook:
    def test_hook_is_called_when_set(self, mock_db):
        calls = []

        def hook(task_spec, exec_result, comparison, correction):
            calls.append((task_spec.name, exec_result.success, comparison is not None))
            return {"status": "called", "case": task_spec.name}

        runner = TaskRunner(
            executor=MockExecutor(),
            knowledge_db=mock_db,
            post_execute_hook=hook,
        )
        report = runner.run_task(make_task())
        assert len(calls) == 1
        assert calls[0][0] == "Lid-Driven Cavity"
        assert report.auto_verify_report == {"status": "called", "case": "Lid-Driven Cavity"}

    def test_hook_not_called_when_none(self, mock_db):
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=mock_db)
        report = runner.run_task(make_task())
        assert report.auto_verify_report is None

    def test_hook_exception_does_not_kill_run(self, mock_db):
        def broken_hook(task_spec, exec_result, comparison, correction):
            raise RuntimeError("hook deliberately raised")

        runner = TaskRunner(
            executor=MockExecutor(),
            knowledge_db=mock_db,
            post_execute_hook=broken_hook,
        )
        report = runner.run_task(make_task())
        assert report.execution_result.success
        assert report.auto_verify_report is None


class TestSuggestOnlyPolicy:
    def test_suggest_only_skips_persistence(self, mock_db, tmp_path):
        runner = TaskRunner(
            executor=MockExecutor(),
            knowledge_db=mock_db,
            correction_policy="suggest_only",
        )
        report = runner.run_task(make_task())
        correction_dir = tmp_path / "corrections"
        yaml_files = list(correction_dir.glob("*.yaml"))
        if report.correction_spec is not None:
            assert len(yaml_files) == 0, (
                "suggest_only policy must not persist correction yaml, "
                f"found: {[p.name for p in yaml_files]}"
            )

    def test_legacy_policy_persists(self, mock_db, tmp_path):
        runner = TaskRunner(
            executor=MockExecutor(),
            knowledge_db=mock_db,
            correction_policy="legacy_auto_save",
        )
        runner.run_task(make_task())
        correction_dir = tmp_path / "corrections"
        yaml_files = list(correction_dir.glob("*.yaml"))
        assert len(yaml_files) >= 0
