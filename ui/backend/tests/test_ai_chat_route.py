"""Route-level tests for POST /api/ai-chat (DEC-V61-118).

Provider is monkeypatched per-test so we exercise the route's error
mapping without hitting any real network.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import ai_chat as ai_chat_route
from ui.backend.services.llm_provider import (
    ChatRequest,
    ChatResponse,
    LLMAuthError,
    LLMConfigError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
)


def _make_app(provider: LLMProvider) -> FastAPI:
    app = FastAPI()
    app.include_router(ai_chat_route.router, prefix="/api")

    # Monkey the per-request factory so tests don't depend on
    # process-level env. Use a closure to inject the test provider.
    def _override() -> LLMProvider:
        return provider

    # Replace the symbol in the route module (imported at top, so we
    # have to assign onto the module that holds the reference).
    ai_chat_route.get_default_provider = _override  # type: ignore[assignment]
    return app


class _StubProvider(LLMProvider):
    def __init__(self, response: ChatResponse | None = None, exc: Exception | None = None):
        self._response = response
        self._exc = exc
        self.calls: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


def _ok_payload(content: str = "test reply") -> dict[str, Any]:
    return {
        "messages": [{"role": "user", "content": content}],
        "model": "deepseek-v4-pro",
    }


# ────────── Success path ──────────


def test_ai_chat_returns_200_on_success():
    provider = _StubProvider(
        response=ChatResponse(
            content="hi back",
            model_used="deepseek-v4-pro",
            fallback_used=False,
            usage={"total_tokens": 10},
        )
    )
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "hi back"
    assert body["model_used"] == "deepseek-v4-pro"
    assert body["fallback_used"] is False
    assert len(provider.calls) == 1


def test_ai_chat_passes_through_fallback_used_flag():
    provider = _StubProvider(
        response=ChatResponse(
            content="recovered",
            model_used="deepseek-v4-flash",
            fallback_used=True,
            usage={"total_tokens": 8},
        )
    )
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["fallback_used"] is True
    assert body["model_used"] == "deepseek-v4-flash"


def test_ai_chat_mock_mode_surfaces_in_model_used():
    """Frontend distinguishes mock mode by model_used == 'mock'."""
    provider = _StubProvider(
        response=ChatResponse(
            content="[mock] you said: hi",
            model_used="mock",
            fallback_used=False,
        )
    )
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload("hi"))
    assert resp.status_code == 200
    assert resp.json()["model_used"] == "mock"


# ────────── Error mapping ──────────


def test_ai_chat_returns_401_on_auth_error():
    provider = _StubProvider(exc=LLMAuthError("bad key"))
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert "DEEPSEEK_API_KEY" in detail


def test_ai_chat_returns_429_on_rate_limit():
    provider = _StubProvider(exc=LLMRateLimitError("rate limited"))
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 429


def test_ai_chat_returns_502_on_upstream_error():
    provider = _StubProvider(exc=LLMUpstreamError("upstream down"))
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 502


def test_ai_chat_returns_502_on_timeout():
    provider = _StubProvider(exc=LLMTimeoutError("timed out"))
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 502


def test_ai_chat_returns_500_on_config_error():
    provider = _StubProvider(exc=LLMConfigError("missing config"))
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 500


# ────────── Request validation ──────────


def test_ai_chat_returns_422_on_empty_messages():
    provider = _StubProvider(
        response=ChatResponse(content="", model_used="x")
    )
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json={"messages": []})
    assert resp.status_code == 422


def test_ai_chat_returns_422_on_invalid_role():
    provider = _StubProvider(
        response=ChatResponse(content="", model_used="x")
    )
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json={"messages": [{"role": "robot", "content": "hi"}]},
    )
    assert resp.status_code == 422


def test_ai_chat_returns_422_on_unknown_model():
    provider = _StubProvider(
        response=ChatResponse(content="", model_used="x")
    )
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "model": "gpt-4",
        },
    )
    assert resp.status_code == 422


def test_ai_chat_does_not_leak_api_key_in_error_detail():
    """Error responses must not echo any value that looks like a key."""
    provider = _StubProvider(
        exc=LLMAuthError("DeepSeek auth failed (status 401)")
    )
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    # Detail string should be the generic "authentication failed"
    # template, not the raw exception message which could in theory
    # contain implementation details.
    assert "sk-" not in detail
    # Generic safe template per route handler.
    assert "authentication failed" in detail.lower()
