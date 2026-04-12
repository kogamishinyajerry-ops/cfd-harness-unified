"""tests/test_e2e_mock.py — 端到端集成测试（全 Mock 模式）

覆盖完整流程：whitelist → KnowledgeDB → TaskRunner → RunReport
"""

import pytest
import yaml
from pathlib import Path

from src.knowledge_db import KnowledgeDB
from src.foam_agent_adapter import MockExecutor
from src.task_runner import TaskRunner


@pytest.fixture
def full_knowledge_dir(tmp_path):
    """包含 3 条白名单案例的完整知识库"""
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
            },
            {
                "id": "backward_facing_step",
                "name": "Backward-Facing Step",
                "flow_type": "INTERNAL",
                "geometry_type": "BACKWARD_FACING_STEP",
                "compressibility": "INCOMPRESSIBLE",
                "steady_state": "STEADY",
                "parameters": {"Re": 7600},
                "gold_standard": {
                    "quantity": "reattachment_length",
                    "reference_values": [{"value": 6.26}],
                    "tolerance": 0.10,
                },
            },
            {
                "id": "circular_cylinder_wake",
                "name": "Circular Cylinder Wake",
                "flow_type": "EXTERNAL",
                "geometry_type": "BODY_IN_CHANNEL",
                "compressibility": "INCOMPRESSIBLE",
                "steady_state": "TRANSIENT",
                "parameters": {"Re": 100},
                "gold_standard": {
                    "quantity": "strouhal_number",
                    "reference_values": [{"value": 0.165}],
                    "tolerance": 0.05,
                },
            },
        ]
    }
    (tmp_path / "whitelist.yaml").write_text(yaml.dump(wl, allow_unicode=True))
    (tmp_path / "corrections").mkdir()
    return tmp_path


class TestE2EMockFullFlow:
    def test_all_whitelist_cases_load(self, full_knowledge_dir):
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        cases = db.list_whitelist_cases()
        assert len(cases) == 3

    def test_run_lid_driven_cavity(self, full_knowledge_dir):
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        cases = db.list_whitelist_cases()
        lid_task = next(c for c in cases if c.name == "Lid-Driven Cavity")

        runner = TaskRunner(executor=MockExecutor(), knowledge_db=db)
        report = runner.run_task(lid_task)

        assert report.execution_result.success
        assert report.execution_result.is_mock
        assert report.comparison_result is not None
        assert "Success" in report.summary

    def test_run_circular_cylinder(self, full_knowledge_dir):
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        cases = db.list_whitelist_cases()
        cyl_task = next(c for c in cases if c.name == "Circular Cylinder Wake")

        runner = TaskRunner(executor=MockExecutor(), knowledge_db=db)
        report = runner.run_task(cyl_task)

        assert report.execution_result.success
        assert report.comparison_result is not None

    def test_correction_saved_on_deviation(self, full_knowledge_dir):
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        from src.models import ExecutionResult

        class OffExecutor:
            def execute(self, task_spec):
                # strouhal_number way off
                return ExecutionResult(
                    success=True, is_mock=True,
                    key_quantities={"strouhal_number": 0.999},
                )

        cases = db.list_whitelist_cases()
        cyl_task = next(c for c in cases if c.name == "Circular Cylinder Wake")

        runner = TaskRunner(executor=OffExecutor(), knowledge_db=db)
        report = runner.run_task(cyl_task)

        assert report.correction_spec is not None
        corrections_dir = full_knowledge_dir / "corrections"
        yaml_files = list(corrections_dir.glob("*.yaml"))
        assert len(yaml_files) == 1

    def test_loaded_correction_round_trips(self, full_knowledge_dir):
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        from src.models import ExecutionResult

        class OffExecutor:
            def execute(self, task_spec):
                return ExecutionResult(
                    success=True, is_mock=True,
                    key_quantities={"strouhal_number": 0.5},
                )

        cases = db.list_whitelist_cases()
        cyl_task = next(c for c in cases if c.name == "Circular Cylinder Wake")

        runner = TaskRunner(executor=OffExecutor(), knowledge_db=db)
        runner.run_task(cyl_task)

        loaded = db.load_corrections(task_name="Circular Cylinder Wake")
        assert len(loaded) == 1
        assert loaded[0].task_spec_name == "Circular Cylinder Wake"

    def test_report_summary_structure(self, full_knowledge_dir):
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        cases = db.list_whitelist_cases()
        runner = TaskRunner(executor=MockExecutor(), knowledge_db=db)
        report = runner.run_task(cases[0])
        # Summary should contain status and comparison result
        assert "Success" in report.summary or "Failed" in report.summary
        assert "|" in report.summary  # 结构分隔符

    def test_backward_facing_step_no_gold_quantity_in_mock(self, full_knowledge_dir):
        """MockExecutor 对 INTERNAL 流动不返回 reattachment_length，验证比较失败但不崩溃"""
        db = KnowledgeDB(knowledge_dir=full_knowledge_dir)
        cases = db.list_whitelist_cases()
        step_task = next(c for c in cases if c.name == "Backward-Facing Step")

        runner = TaskRunner(executor=MockExecutor(), knowledge_db=db)
        report = runner.run_task(step_task)

        # MockExecutor 返回 u_centerline，没有 reattachment_length → 比较失败
        assert report.execution_result.success
        assert report.comparison_result is not None
        assert not report.comparison_result.passed  # gold 里有 quantity 但 result 没有
