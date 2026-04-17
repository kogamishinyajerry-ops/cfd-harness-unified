"""Explicit binding helpers for the official notion-client package."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, Type


class NotionAdapter(Protocol):
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> None:
        """Patch page properties."""

    def create_page(self, parent_data_source_id: str, properties: Dict[str, Any]) -> None:
        """Create a new page in a data source."""


def resolve_official_notion_client(
    import_module: Callable[[str], Any] = importlib.import_module,
    project_root: Optional[Path] = None,
) -> Type[Any]:
    """Resolve the external notion_client.Client without binding the local shadow module."""
    root = project_root or Path(__file__).resolve().parents[2]
    module = import_module("notion_client")
    module_file = Path(getattr(module, "__file__", ""))
    local_shadow = root / "src" / "notion_client.py"
    if module_file == local_shadow:
        raise ImportError(
            "Refusing to bind local src/notion_client.py; use the external notion-client package."
        )
    client_cls = getattr(module, "Client", None)
    if client_cls is None:
        raise ImportError("notion_client.Client is unavailable")
    return client_cls


class OfficialNotionAdapter:
    """Thin adapter around the official notion-client package."""

    def __init__(
        self,
        token: str,
        notion_version: str = "2022-06-28",
        client_cls: Optional[Type[Any]] = None,
    ) -> None:
        cls = client_cls or resolve_official_notion_client()
        self._client = cls(auth=token, notion_version=notion_version)

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> None:
        self._client.request(
            path=f"/pages/{page_id}",
            method="PATCH",
            body={"properties": properties},
        )

    def create_page(self, parent_data_source_id: str, properties: Dict[str, Any]) -> None:
        self._client.request(
            path="/pages",
            method="POST",
            body={
                "parent": {"data_source_id": parent_data_source_id},
                "properties": properties,
            },
        )
