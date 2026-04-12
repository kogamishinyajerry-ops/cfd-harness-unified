"""tests/test_notion_client.py — NotionClient 单元测试（mock 底层方法）"""

import pytest
from unittest.mock import MagicMock, patch

from src.models import (
    Compressibility, ExecutionResult, FlowType, GeometryType,
    SteadyState, TaskSpec,
)
from src.notion_client import NotionClient


@pytest.fixture
def client():
    return NotionClient(token="fake-token", database_ids={"tasks": "fake-db-id"})


class TestListPendingTasks:
    def test_returns_task_specs(self, client):
        rows = [
            {
                "name": "Lid-Driven Cavity",
                "geometry_type": "SIMPLE_GRID",
                "flow_type": "INTERNAL",
                "steady_state": "STEADY",
                "compressibility": "INCOMPRESSIBLE",
                "Re": 100,
                "notion_task_id": "abc123",
            }
        ]
        client._fetch_tasks = MagicMock(return_value=rows)
        tasks = client.list_pending_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "Lid-Driven Cavity"
        assert tasks[0].Re == 100
        assert tasks[0].flow_type == FlowType.INTERNAL
        client._fetch_tasks.assert_called_once_with(filter_status="Ready")

    def test_empty_list(self, client):
        client._fetch_tasks = MagicMock(return_value=[])
        assert client.list_pending_tasks() == []

    def test_multiple_tasks(self, client):
        rows = [
            {"name": "A", "geometry_type": "SIMPLE_GRID", "flow_type": "INTERNAL",
             "steady_state": "STEADY", "compressibility": "INCOMPRESSIBLE"},
            {"name": "B", "geometry_type": "BODY_IN_CHANNEL", "flow_type": "EXTERNAL",
             "steady_state": "TRANSIENT", "compressibility": "INCOMPRESSIBLE"},
        ]
        client._fetch_tasks = MagicMock(return_value=rows)
        tasks = client.list_pending_tasks()
        assert len(tasks) == 2
        assert tasks[1].flow_type == FlowType.EXTERNAL


class TestWriteExecutionResult:
    def test_writes_success(self, client):
        client._update_page = MagicMock()
        spec = TaskSpec(
            name="test", geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL, steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE, notion_task_id="page-1"
        )
        result = ExecutionResult(success=True, is_mock=True, execution_time_s=0.5)
        client.write_execution_result(spec, result, summary="OK")
        client._update_page.assert_called_once()
        call_kwargs = client._update_page.call_args
        assert call_kwargs[1]["page_id"] == "page-1"
        assert call_kwargs[1]["properties"]["Status"] == "Done"

    def test_skips_when_no_task_id(self, client):
        client._update_page = MagicMock()
        spec = TaskSpec(
            name="test", geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL, steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
        )
        result = ExecutionResult(success=True, is_mock=True)
        client.write_execution_result(spec, result, summary="ok")
        client._update_page.assert_not_called()

    def test_writes_failed(self, client):
        client._update_page = MagicMock()
        spec = TaskSpec(
            name="test", geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL, steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE, notion_task_id="p2"
        )
        result = ExecutionResult(success=False, is_mock=False)
        client.write_execution_result(spec, result, summary="fail")
        props = client._update_page.call_args[1]["properties"]
        assert props["Status"] == "Failed"


class TestFetchTasksRaisesNotImplemented:
    def test_raises(self, client):
        with pytest.raises(NotImplementedError):
            client._fetch_tasks("Ready")

    def test_update_raises(self, client):
        with pytest.raises(NotImplementedError):
            client._update_page("id", {})


class TestParseTask:
    def test_parse_minimal(self):
        row = {
            "name": "Test",
            "geometry_type": "CUSTOM",
            "flow_type": "EXTERNAL",
            "steady_state": "TRANSIENT",
            "compressibility": "COMPRESSIBLE",
        }
        spec = NotionClient._parse_task(row)
        assert spec.name == "Test"
        assert spec.geometry_type == GeometryType.CUSTOM
        assert spec.compressibility == Compressibility.COMPRESSIBLE

    def test_parse_with_defaults(self):
        row = {"name": "X"}
        spec = NotionClient._parse_task(row)
        assert spec.flow_type == FlowType.INTERNAL
