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


# ────────── Codex R1 P2: 400 mapping for LLMBadRequestError ──────────


def test_ai_chat_returns_400_on_bad_request():
    """An LLMBadRequestError (e.g. context_length_exceeded) must
    surface as HTTP 400 — the caller fixes their request, not the
    server. Codex R1 P2."""
    from ui.backend.services.llm_provider import LLMBadRequestError

    provider = _StubProvider(exc=LLMBadRequestError("context_length_exceeded"))
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 400


# ────────── Codex R1 P1: loopback-only guard ──────────


def _make_remote_request_app(provider: LLMProvider) -> FastAPI:
    """Build the app and patch the request-introspection helper so
    the test can simulate a non-loopback caller without spinning up
    a real network listener."""
    from ui.backend.routes import ai_chat as route_module

    app = _make_app(provider)
    return app, route_module


def test_ai_chat_rejects_non_loopback_caller_without_override(monkeypatch):
    """A request with a remote client.host (not 127.0.0.1/::1/localhost)
    must be rejected with 403 unless AI_CHAT_ALLOW_NON_LOOPBACK=1."""
    from ui.backend.routes import ai_chat as route_module

    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)

    provider = _StubProvider(
        response=ChatResponse(content="should not see this", model_used="x")
    )
    app = _make_app(provider)
    # Patch the loopback check to simulate a non-loopback caller.
    monkeypatch.setattr(route_module, "_is_loopback_request", lambda req: False)

    client = TestClient(app)
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 403
    assert "AI_CHAT_ALLOW_NON_LOOPBACK" in resp.json()["detail"]
    # Provider was NOT called.
    assert len(provider.calls) == 0


def test_ai_chat_allows_non_loopback_with_explicit_override(monkeypatch):
    """The override env var unlocks remote callers (operator opted
    in to a trusted reverse proxy). Provider gets called normally."""
    from ui.backend.routes import ai_chat as route_module

    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    provider = _StubProvider(
        response=ChatResponse(content="ok", model_used="deepseek-v4-pro")
    )
    app = _make_app(provider)
    monkeypatch.setattr(route_module, "_is_loopback_request", lambda req: False)

    client = TestClient(app)
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 200
    assert len(provider.calls) == 1


def test_ai_chat_allows_loopback_caller_by_default():
    """The TestClient is loopback by definition (no client.host) —
    must succeed without override."""
    provider = _StubProvider(
        response=ChatResponse(content="ok", model_used="deepseek-v4-pro")
    )
    client = TestClient(_make_app(provider))
    resp = client.post("/api/ai-chat", json=_ok_payload())
    assert resp.status_code == 200


# ────────── Codex R2 P1: same-host reverse proxy bypass ──────────


def test_ai_chat_rejects_loopback_peer_with_xforwarded_for(monkeypatch):
    """nginx/Caddy on the same host presents client.host=127.0.0.1
    even when the real caller is remote. X-Forwarded-For signals a
    proxy chain → reject as non-loopback. R2 P1."""
    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    provider = _StubProvider(
        response=ChatResponse(content="should not reach", model_used="x")
    )
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert resp.status_code == 403
    assert len(provider.calls) == 0


def test_ai_chat_rejects_loopback_peer_with_x_real_ip(monkeypatch):
    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    provider = _StubProvider(
        response=ChatResponse(content="should not reach", model_used="x")
    )
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"X-Real-IP": "203.0.113.42"},
    )
    assert resp.status_code == 403


def test_ai_chat_rejects_loopback_peer_with_forwarded_header(monkeypatch):
    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    provider = _StubProvider(
        response=ChatResponse(content="should not reach", model_used="x")
    )
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"Forwarded": 'for="203.0.113.42"'},
    )
    assert resp.status_code == 403


def test_ai_chat_allows_proxy_chain_with_explicit_override(monkeypatch):
    """Operator explicitly opted in to a trusted reverse proxy with
    its own auth in front."""
    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    provider = _StubProvider(
        response=ChatResponse(content="ok", model_used="deepseek-v4-pro")
    )
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert resp.status_code == 200


# ────────── Codex R3 P2-1: log forwarded client IP ──────────


def test_ai_chat_403_log_includes_full_xff_chain(monkeypatch, caplog):
    """When XFF trips the guard, the rejection log must record the
    full chain verbatim (Codex R4 P1: don't pick a single hop as
    'the caller' — XFF is client-controlled, audit logs both hops
    and the operator interprets with knowledge of trusted-proxy
    count)."""
    import logging as _logging

    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    provider = _StubProvider(
        response=ChatResponse(content="x", model_used="x")
    )
    caplog.set_level(_logging.WARNING)
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"X-Forwarded-For": "203.0.113.99, 10.0.0.1"},
    )
    assert resp.status_code == 403
    # Both hops appear verbatim in the chain log.
    msgs = [rec.getMessage() for rec in caplog.records if rec.levelno >= _logging.WARNING]
    assert any(
        "203.0.113.99" in m and "10.0.0.1" in m and "x-forwarded-for" in m
        for m in msgs
    )


def test_ai_chat_403_log_includes_x_real_ip(monkeypatch, caplog):
    import logging as _logging

    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    provider = _StubProvider(
        response=ChatResponse(content="x", model_used="x")
    )
    caplog.set_level(_logging.WARNING)
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"X-Real-IP": "198.51.100.7"},
    )
    assert resp.status_code == 403
    msgs = [rec.getMessage() for rec in caplog.records if rec.levelno >= _logging.WARNING]
    assert any("198.51.100.7" in m and "x-real-ip" in m for m in msgs)


def test_ai_chat_override_log_includes_forwarded_caller(monkeypatch, caplog):
    """When the override is active, the audit log of the allowed
    request must still include the forwarded chain."""
    import logging as _logging

    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    provider = _StubProvider(
        response=ChatResponse(content="ok", model_used="deepseek-v4-pro")
    )
    caplog.set_level(_logging.INFO)
    client = TestClient(_make_app(provider))
    resp = client.post(
        "/api/ai-chat",
        json=_ok_payload(),
        headers={"X-Forwarded-For": "203.0.113.55"},
    )
    assert resp.status_code == 200
    assert any(
        "203.0.113.55" in rec.getMessage() and "Allowing" in rec.getMessage()
        for rec in caplog.records
        if rec.levelno >= _logging.INFO
    )
