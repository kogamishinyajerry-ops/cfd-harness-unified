"""Tests for scripts/dogfood/workbench_tools.py — allowlist + executor."""
from __future__ import annotations

import httpx
import pytest

from scripts.dogfood.llm_clients import ToolCall
from scripts.dogfood.workbench_tools import (
    WorkbenchToolError,
    WorkbenchToolExecutor,
    _resolve_path,
    workbench_tool_defs,
)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "/api/cases/x/state",
        "http://localhost:8000/api/cases/x/state",
        "http://127.0.0.1:8000/api/cases/x/state",
    ],
)
def test_resolve_path_accepts_localhost_api(url: str) -> None:
    path = _resolve_path(url)
    assert path.startswith("/api/")


@pytest.mark.parametrize(
    "url, reason",
    [
        ("file:///etc/passwd", "scheme"),
        ("ftp://example.com/foo", "scheme"),
        ("http://evil.com/api/x", "host"),
        ("http://localhost:8000/", "path"),
        ("http://localhost:8000/admin", "path"),
        ("http://localhost:9000/api/x", "host"),
    ],
)
def test_resolve_path_rejects_off_allowlist(url: str, reason: str) -> None:
    with pytest.raises(WorkbenchToolError):
        _resolve_path(url)


# ---------------------------------------------------------------------------
# Tool defs
# ---------------------------------------------------------------------------


def test_workbench_tool_defs_exposes_get_and_post() -> None:
    defs = workbench_tool_defs()
    names = {t.name for t in defs}
    assert names == {"http_get", "http_post"}
    for t in defs:
        assert "rationale" in t.input_schema["required"]


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def _executor_with_handler(handler) -> WorkbenchToolExecutor:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://localhost:8000")
    return WorkbenchToolExecutor(client=client)


def test_executor_get_success() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"step": "geometry"})

    ex = _executor_with_handler(handler)
    result = ex.execute(
        ToolCall(
            call_id="c1",
            tool_name="http_get",
            arguments={"url": "/api/cases/x/state", "rationale": "check"},
        )
    )
    assert result.ok is True
    assert result.status == 200
    assert "geometry" in result.body_text
    ex.close()


def test_executor_post_success_with_body() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["method"] = req.method
        captured["body"] = req.read()
        return httpx.Response(201, json={"applied": True})

    ex = _executor_with_handler(handler)
    result = ex.execute(
        ToolCall(
            call_id="c2",
            tool_name="http_post",
            arguments={
                "url": "/api/cases/x/mesh",
                "json": {"sizing": "fine"},
                "rationale": "engineer-driven mesh refinement",
            },
        )
    )
    assert result.ok is True
    assert captured["method"] == "POST"
    assert b"sizing" in captured["body"]
    ex.close()


def test_executor_rejects_off_allowlist_url() -> None:
    ex = _executor_with_handler(lambda r: httpx.Response(200))
    result = ex.execute(
        ToolCall(
            call_id="c",
            tool_name="http_get",
            arguments={"url": "http://evil.com/api/x", "rationale": "bad"},
        )
    )
    assert result.ok is False
    assert result.error and "host" in result.error.lower()
    ex.close()


def test_executor_truncates_large_response() -> None:
    big = "x" * (3 * 1024 * 1024)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=big)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://localhost:8000")
    ex = WorkbenchToolExecutor(client=client, bytes_cap=64 * 1024)
    result = ex.execute(
        ToolCall(
            call_id="c",
            tool_name="http_get",
            arguments={"url": "/api/cases/x/state", "rationale": "huge"},
        )
    )
    assert result.truncated_at_bytes == 64 * 1024
    assert "[truncated_at_bytes=" in result.body_text
    ex.close()


def test_executor_rejects_unknown_tool() -> None:
    ex = _executor_with_handler(lambda r: httpx.Response(200))
    result = ex.execute(
        ToolCall(call_id="c", tool_name="exec_shell", arguments={})
    )
    assert result.ok is False
    assert "unknown tool" in (result.error or "")
    ex.close()


def test_executor_missing_url_argument() -> None:
    ex = _executor_with_handler(lambda r: httpx.Response(200))
    result = ex.execute(
        ToolCall(call_id="c", tool_name="http_get", arguments={"rationale": "x"})
    )
    assert result.ok is False
    assert "missing" in (result.error or "").lower()
    ex.close()
