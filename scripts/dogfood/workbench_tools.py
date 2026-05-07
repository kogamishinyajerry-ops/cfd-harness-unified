"""HTTP-only tool surface for personas talking to the workbench.

Two tools exposed: `http_get` and `http_post`. URL allowlist:
`localhost:8000/api/...` only. Response bytes-cap to keep persona
context bounded.

Per V130 Principle B: personas are engineer-as-applier. They CAN call
mutating workbench routes (Step 1-4 apply endpoints), but the harness
captures `rationale` text on each call so B.4 retro can grep for
"AI told me to apply X" violations.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from scripts.dogfood.llm_clients import ToolCall, ToolDef

logger = logging.getLogger(__name__)


_DEFAULT_BASE = "http://localhost:8000"
_ALLOWED_PATH_PREFIX = "/api/"
_DEFAULT_BYTES_CAP = 2 * 1024 * 1024  # 2 MiB


class WorkbenchToolError(RuntimeError):
    """Raised on disallowed URLs or transport errors."""


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned to the persona for its next turn."""

    call_id: str
    tool_name: str
    ok: bool
    status: int | None
    body_text: str
    truncated_at_bytes: int | None
    error: str | None = None

    def to_message_payload(self) -> dict[str, Any]:
        return {
            "tool_use_id": self.call_id,
            "ok": self.ok,
            "status": self.status,
            "body": self.body_text,
            "truncated_at_bytes": self.truncated_at_bytes,
            "error": self.error,
        }


_HTTP_GET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "Workbench API URL (must start with /api/ or http://localhost:8000/api/)"},
        "rationale": {"type": "string", "description": "Why you are making this call"},
    },
    "required": ["url", "rationale"],
}


_HTTP_POST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "Workbench API URL (must start with /api/ or http://localhost:8000/api/)"},
        "json": {"type": "object", "description": "JSON body for the POST"},
        "rationale": {
            "type": "string",
            "description": (
                "Why you are applying this mutation. NEVER 'AI advisor told me'; "
                "you are the engineer making the decision based on advisor evidence."
            ),
        },
    },
    "required": ["url", "rationale"],
}


def workbench_tool_defs() -> list[ToolDef]:
    return [
        ToolDef(
            name="http_get",
            description="GET against the workbench API. Use for read-only queries (case state, advisor review/diagnose, completeness).",
            input_schema=_HTTP_GET_SCHEMA,
        ),
        ToolDef(
            name="http_post",
            description="POST against the workbench API. Use for engineer-driven Step 1-4 mutations (import, mesh, physics, BC, solver).",
            input_schema=_HTTP_POST_SCHEMA,
        ),
    ]


def _resolve_path(url: str) -> str:
    """Validate URL is within `localhost:8000/api/...`; return the path."""
    parsed = urlparse(url)
    if parsed.scheme in ("", "http", "https"):
        if parsed.netloc and parsed.netloc not in {"localhost:8000", "127.0.0.1:8000"}:
            raise WorkbenchToolError(
                f"URL host not allowed: {parsed.netloc!r}; only localhost:8000"
            )
        path = parsed.path or "/"
    else:
        raise WorkbenchToolError(f"URL scheme not allowed: {parsed.scheme!r}")
    if not path.startswith(_ALLOWED_PATH_PREFIX):
        raise WorkbenchToolError(
            f"URL path must start with {_ALLOWED_PATH_PREFIX!r}; got {path!r}"
        )
    return path


def _truncate(text: str, cap_bytes: int) -> tuple[str, int | None]:
    encoded = text.encode("utf-8")
    if len(encoded) <= cap_bytes:
        return text, None
    truncated = encoded[:cap_bytes].decode("utf-8", errors="replace")
    return truncated + f"\n…[truncated_at_bytes={cap_bytes}]", cap_bytes


class WorkbenchToolExecutor:
    """Executes persona tool calls against the workbench HTTP surface."""

    def __init__(
        self,
        *,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 30.0,
        bytes_cap: int = _DEFAULT_BYTES_CAP,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._bytes_cap = bytes_cap
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def execute(self, call: ToolCall) -> ToolResult:
        if call.tool_name == "http_get":
            return self._do(call, method="GET")
        if call.tool_name == "http_post":
            return self._do(call, method="POST")
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            ok=False,
            status=None,
            body_text="",
            truncated_at_bytes=None,
            error=f"unknown tool: {call.tool_name!r}",
        )

    def _do(self, call: ToolCall, *, method: str) -> ToolResult:
        url = str(call.arguments.get("url", "")).strip()
        if not url:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                ok=False,
                status=None,
                body_text="",
                truncated_at_bytes=None,
                error="missing 'url' argument",
            )
        try:
            path = _resolve_path(url)
        except WorkbenchToolError as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                ok=False,
                status=None,
                body_text="",
                truncated_at_bytes=None,
                error=str(exc),
            )
        full_url = f"{self._base_url}{path}"
        try:
            if method == "GET":
                resp = self._client.get(full_url)
            else:
                body = call.arguments.get("json")
                resp = self._client.post(full_url, json=body if isinstance(body, dict) else {})
        except httpx.HTTPError as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                ok=False,
                status=None,
                body_text="",
                truncated_at_bytes=None,
                error=f"transport error: {exc!s}",
            )
        body_text, truncated_at = _truncate(resp.text, self._bytes_cap)
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            ok=resp.is_success,
            status=resp.status_code,
            body_text=body_text,
            truncated_at_bytes=truncated_at,
        )


__all__ = [
    "ToolResult",
    "WorkbenchToolError",
    "WorkbenchToolExecutor",
    "workbench_tool_defs",
]
