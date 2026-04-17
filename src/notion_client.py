"""Notion API 读写封装 — 真实 API 实现"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from notion_client import Client

from .models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
    ExecutionResult,
)


class NotionClient:
    """Notion API 客户端

    数据库架构（cfd-harness-unified 控制平面）：
        tasks:          2b25c81b15174eb48d0cca20e8d37c09  # ⚡ Tasks
        sessions:       7905136d58de43a09cc365dec52ba51b  # 📝 Sessions
        decisions:      fa55d3ed0a6d452f909d91a8c8d218a7  # ⚖️ Decisions
        canonical_docs: 96a6344f4a42442dabb3a96e9faadee6  # 📚 Canonical Docs
        phases:         25a50aa20e3f476a8ad611725a9fbe8b  # 🔄 Phases
    """

    # Notion Status 字段选项 ID 映射（从 DB schema 获取）
    _STATUS_ID_MAP = {
        "Done": "c?pc",
        "Ready": "lIe}",
        "Inbox": "<XF",
        "In Progress": ";FjG",
        "Waiting": "ollp",
        "Review": "vBjn",
    }

    def __init__(
        self,
        token: Optional[str] = None,
        database_ids: Optional[Dict[str, str]] = None,
    ) -> None:
        import os
        self._token = token or os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
        self._database_ids = database_ids or {}
        self._client = Client(auth=self._token, notion_version="2022-06-28") if self._token else None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def list_pending_tasks(self) -> List[TaskSpec]:
        """从 Notion Tasks 数据库读取状态为 Ready 的任务列表"""
        raw = self._fetch_tasks(filter_status="Ready")
        return [self._parse_task(row) for row in raw]

    def write_execution_result(
        self,
        task_spec: TaskSpec,
        result: ExecutionResult,
        summary: str,
    ) -> None:
        """把执行结果摘要回写到对应 Notion Task 页面"""
        if task_spec.notion_task_id is None:
            return
        status_name = "Done" if result.success else "Review"
        self._update_page(
            page_id=task_spec.notion_task_id,
            properties={
                "Status": {"status": {"id": self._resolve_status_id(status_name), "name": status_name}},
            },
        )

    # ------------------------------------------------------------------
    # 内部方法（Notion API 真实调用）
    # ------------------------------------------------------------------

    def _fetch_tasks(self, filter_status: str) -> List[Dict[str, Any]]:
        """向 Notion API 查询任务列表"""
        if self._client is None:
            raise NotImplementedError("Notion token 未配置")
        db_id = self._database_ids.get("tasks")
        if not db_id:
            raise ValueError("database_ids['tasks'] 未配置")
        response = self._client.request(
            path=f"/databases/{db_id}/query",
            method="POST",
            body={"filter": {"property": "Status", "status": {"equals": filter_status}}},
        )
        return response.get("results", [])

    def _update_page(self, page_id: str, properties: Dict[str, Any]) -> None:
        """更新 Notion 页面属性"""
        if self._client is None:
            raise NotImplementedError("Notion token 未配置")
        self._client.request(
            path=f"/pages/{page_id}",
            method="PATCH",
            body={"properties": properties},
        )

    @staticmethod
    def _resolve_status_id(status_name: str) -> str:
        """根据 Status 选项名称解析对应的 Notion 选项 ID"""
        return NotionClient._STATUS_ID_MAP.get(status_name, "")

    # ------------------------------------------------------------------
    # 解析辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_task(row: Dict[str, Any]) -> TaskSpec:
        """把 Notion 行数据解析为 TaskSpec"""
        props = row.get("properties", {})

        def get_title(field: str) -> str:
            segments = props.get(field, {}).get("title", [])
            return "".join(s.get("plain_text", "") for s in segments)

        def get_rich_text(field: str) -> str:
            segments = props.get(field, {}).get("rich_text", [])
            return "".join(s.get("plain_text", "") for s in segments)

        def get_select(field: str) -> Optional[str]:
            sel = props.get(field, {}).get("select")
            return sel.get("name") if sel else None

        return TaskSpec(
            name=get_title("Name") or "unnamed",
            geometry_type=GeometryType(get_select("GeometryType") or "SIMPLE_GRID"),
            flow_type=FlowType(get_select("FlowType") or "INTERNAL"),
            steady_state=SteadyState(get_select("SteadyState") or "STEADY"),
            compressibility=Compressibility(get_select("Compressibility") or "INCOMPRESSIBLE"),
            Re=None,
            Ma=None,
            boundary_conditions={},
            description=get_rich_text("Acceptance Criteria"),
            notion_task_id=row.get("id"),
        )
