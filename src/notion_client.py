"""Notion API 读写封装（占位符实现，测试用 mock 替换）"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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

    真实使用时需配置 token 和 database_ids（见 config/notion_config.yaml）。
    测试时通过 mock 替换 _fetch_page / _update_page 等底层方法。
    """

    def __init__(
        self,
        token: Optional[str] = None,
        database_ids: Optional[Dict[str, str]] = None,
    ) -> None:
        self._token = token
        self._database_ids = database_ids or {}
        self._client: Any = None  # 真实 notion_client.Client 实例（占位符）

    # ------------------------------------------------------------------
    # 公开 API（单元测试 mock 这些方法）
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
        self._update_page(
            page_id=task_spec.notion_task_id,
            properties={
                "Status": "Done" if result.success else "Failed",
                "Summary": summary,
                "ExecutionTime": result.execution_time_s,
            },
        )

    # ------------------------------------------------------------------
    # 内部方法（占位符，供 mock 替换）
    # ------------------------------------------------------------------

    def _fetch_tasks(self, filter_status: str) -> List[Dict[str, Any]]:
        """向 Notion API 查询任务列表（占位符）"""
        raise NotImplementedError(
            "请配置 notion_config.yaml 并实例化真实 Notion 客户端"
        )

    def _update_page(self, page_id: str, properties: Dict[str, Any]) -> None:
        """更新 Notion 页面属性（占位符）"""
        raise NotImplementedError(
            "请配置 notion_config.yaml 并实例化真实 Notion 客户端"
        )

    # ------------------------------------------------------------------
    # 解析辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_task(row: Dict[str, Any]) -> TaskSpec:
        """把 Notion 行数据解析为 TaskSpec"""
        return TaskSpec(
            name=row.get("name", "unnamed"),
            geometry_type=GeometryType(row.get("geometry_type", "SIMPLE_GRID")),
            flow_type=FlowType(row.get("flow_type", "INTERNAL")),
            steady_state=SteadyState(row.get("steady_state", "STEADY")),
            compressibility=Compressibility(row.get("compressibility", "INCOMPRESSIBLE")),
            Re=row.get("Re"),
            Ma=row.get("Ma"),
            boundary_conditions=row.get("boundary_conditions", {}),
            description=row.get("description", ""),
            notion_task_id=row.get("notion_task_id"),
        )
