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


def _make_page(page_id, name, flow_type="INTERNAL", geometry_type="SIMPLE_GRID",
               steady_state="STEADY", compressibility="INCOMPRESSIBLE", description=""):
    """构建符合 Notion API 页面格式的 mock 数据"""
    return {
        "id": page_id,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": name}]},
            "FlowType": {"type": "select", "select": {"name": flow_type}},
            "GeometryType": {"type": "select", "select": {"name": geometry_type}},
            "SteadyState": {"type": "select", "select": {"name": steady_state}},
            "Compressibility": {"type": "select", "select": {"name": compressibility}},
            "Acceptance Criteria": {"type": "rich_text", "rich_text": [{"plain_text": description}]},
        },
    }


class TestListPendingTasks:
    def test_returns_task_specs(self, client):
        rows = [_make_page("abc123", "Lid-Driven Cavity", flow_type="INTERNAL")]
        client._fetch_tasks = MagicMock(return_value=rows)
        tasks = client.list_pending_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "Lid-Driven Cavity"
        assert tasks[0].flow_type == FlowType.INTERNAL
        client._fetch_tasks.assert_called_once_with(filter_status="Ready")

    def test_empty_list(self, client):
        client._fetch_tasks = MagicMock(return_value=[])
        assert client.list_pending_tasks() == []

    def test_multiple_tasks(self, client):
        rows = [
            _make_page("p1", "A", flow_type="INTERNAL"),
            _make_page("p2", "B", flow_type="EXTERNAL"),
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
        assert call_kwargs[1]["properties"]["Status"] == {"status": {"id": "c?pc", "name": "Done"}}

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
        assert props["Status"] == {"status": {"id": "vBjn", "name": "Review"}}


class TestClientInit:
    def test_raises_without_token(self, monkeypatch):
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        client = NotionClient(token=None)
        assert client._client is None



class TestParseTask:
    def test_parse_minimal(self):
        row = _make_page("x", "Test", flow_type="EXTERNAL",
                         geometry_type="CUSTOM", steady_state="TRANSIENT",
                         compressibility="COMPRESSIBLE")
        spec = NotionClient._parse_task(row)
        assert spec.name == "Test"
        assert spec.flow_type == FlowType.EXTERNAL
        assert spec.geometry_type == GeometryType.CUSTOM
        assert spec.steady_state == SteadyState.TRANSIENT
        assert spec.compressibility == Compressibility.COMPRESSIBLE

    def test_parse_with_defaults(self):
        row = _make_page("y", "X")
        spec = NotionClient._parse_task(row)
        assert spec.name == "X"
        assert spec.flow_type == FlowType.INTERNAL
        assert spec.geometry_type == GeometryType.SIMPLE_GRID
        assert spec.steady_state == SteadyState.STEADY
        assert spec.compressibility == Compressibility.INCOMPRESSIBLE

    def test_extracts_description(self):
        row = _make_page("z", "Y", description="do something")
        spec = NotionClient._parse_task(row)
        assert spec.description == "do something"

    def test_extracts_notion_id(self):
        row = _make_page("abc123", "Z")
        spec = NotionClient._parse_task(row)
        assert spec.notion_task_id == "abc123"
