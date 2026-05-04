"""Unit tests for the LLM provider abstraction (DEC-V61-118).

Coverage targets:
  - Pydantic validation on ChatRequest (non-empty messages, role
    constraints, temperature/max_tokens bounds)
  - DeepSeekProvider success path (200 with valid choices)
  - DeepSeekProvider error mapping (401 → LLMAuthError, 429 →
    LLMRateLimitError, 5xx → LLMUpstreamError, timeout →
    LLMTimeoutError)
  - DeepSeekProvider fallback chain (primary 5xx → flash retry,
    fallback_used=True; auth error → no fallback)
  - MockLLMProvider deterministic echo
  - factory.get_default_provider env-var gating
  - api_key never appears in repr or logged exception messages

Async tests use ``asyncio.run`` directly (no pytest-asyncio plugin in
this repo's test stack).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, TypeVar

import httpx
import pytest

from ui.backend.services.llm_provider import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    DeepSeekProvider,
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    MockLLMProvider,
    get_default_provider,
)
from ui.backend.services.llm_provider.base import LLMProviderError

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


# ────────── ChatRequest validation ──────────


def test_chat_request_rejects_empty_messages():
    with pytest.raises(ValueError):
        ChatRequest(messages=[])


def test_chat_request_rejects_two_system_messages():
    with pytest.raises(ValueError):
        ChatRequest(
            messages=[
                ChatMessage(role="system", content="a"),
                ChatMessage(role="system", content="b"),
                ChatMessage(role="user", content="hi"),
            ]
        )


def test_chat_request_rejects_system_not_first():
    with pytest.raises(ValueError):
        ChatRequest(
            messages=[
                ChatMessage(role="user", content="hi"),
                ChatMessage(role="system", content="late"),
            ]
        )


def test_chat_request_clamps_temperature_range():
    with pytest.raises(ValueError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            temperature=5.0,
        )


def test_chat_request_clamps_max_tokens_range():
    with pytest.raises(ValueError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            max_tokens=99999,
        )


def test_chat_message_rejects_empty_content():
    with pytest.raises(ValueError):
        ChatMessage(role="user", content="")


# ────────── DeepSeekProvider success path ──────────


def _make_response(status: int, payload):
    if isinstance(payload, dict):
        return httpx.Response(
            status, json=payload, request=httpx.Request("POST", "https://x")
        )
    return httpx.Response(
        status, text=payload, request=httpx.Request("POST", "https://x")
    )


def _success_body(content: str = "ok") -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }


async def _do_chat(
    transport: httpx.MockTransport,
    *,
    api_key: str = "sk-test",
    model: str | None = None,
) -> ChatResponse:
    async with httpx.AsyncClient(transport=transport) as client:
        provider = DeepSeekProvider(api_key=api_key, client=client)
        kwargs = {"messages": [ChatMessage(role="user", content="hi")]}
        if model is not None:
            kwargs["model"] = model
        return await provider.chat(ChatRequest(**kwargs))


def test_deepseek_success_path():
    transport = httpx.MockTransport(lambda r: _make_response(200, _success_body("hello")))
    response = _run(_do_chat(transport))
    assert isinstance(response, ChatResponse)
    assert response.content == "hello"
    assert response.model_used == "deepseek-v4-pro"
    assert response.fallback_used is False
    assert response.usage["total_tokens"] == 7


def test_deepseek_explicit_flash_no_fallback_attempted():
    """Caller asks for flash directly; no further fallback exists."""
    transport = httpx.MockTransport(lambda r: _make_response(200, _success_body("flashed")))
    response = _run(_do_chat(transport, model="deepseek-v4-flash"))
    assert response.model_used == "deepseek-v4-flash"
    assert response.fallback_used is False


# ────────── DeepSeekProvider error mapping ──────────


def test_deepseek_401_raises_auth_error():
    transport = httpx.MockTransport(lambda r: _make_response(401, {"error": "bad key"}))
    with pytest.raises(LLMAuthError):
        _run(_do_chat(transport, api_key="sk-bad"))


def test_deepseek_403_raises_auth_error():
    transport = httpx.MockTransport(lambda r: _make_response(403, {"error": "forbidden"}))
    with pytest.raises(LLMAuthError):
        _run(_do_chat(transport, api_key="sk-bad"))


def test_deepseek_malformed_response_raises_upstream():
    transport = httpx.MockTransport(lambda r: _make_response(200, {"no_choices": True}))
    with pytest.raises(LLMUpstreamError):
        _run(_do_chat(transport, model="deepseek-v4-flash"))


def test_deepseek_timeout_raises_timeout_error():
    def raise_timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("read timeout")

    transport = httpx.MockTransport(raise_timeout)
    with pytest.raises(LLMTimeoutError):
        _run(_do_chat(transport, model="deepseek-v4-flash"))


# ────────── DeepSeekProvider fallback chain ──────────


def test_deepseek_5xx_triggers_fallback_to_flash():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        body = request.read().decode()
        if call_count["n"] == 1:
            assert "deepseek-v4-pro" in body
            return _make_response(503, {"error": "upstream"})
        assert "deepseek-v4-flash" in body
        return _make_response(200, _success_body("recovered"))

    transport = httpx.MockTransport(handler)
    response = _run(_do_chat(transport))
    assert response.model_used == "deepseek-v4-flash"
    assert response.fallback_used is True
    assert response.content == "recovered"
    assert call_count["n"] == 2


def test_deepseek_429_triggers_fallback_to_flash():
    call_count = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_response(429, {"error": "too many"})
        return _make_response(200, _success_body("flash-served"))

    transport = httpx.MockTransport(handler)
    response = _run(_do_chat(transport))
    assert response.model_used == "deepseek-v4-flash"
    assert response.fallback_used is True


def test_deepseek_auth_error_does_not_trigger_fallback():
    """Auth errors propagate without retry — different model won't fix
    bad credentials, and a retry would just waste a quota slot."""
    call_count = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return _make_response(401, {"error": "bad"})

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMAuthError):
        _run(_do_chat(transport, api_key="sk-bad"))
    assert call_count["n"] == 1


def test_deepseek_both_models_fail_raises_last_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return _make_response(503, {"error": "down"})

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMUpstreamError):
        _run(_do_chat(transport))


# ────────── Secrets non-leakage ──────────


def test_deepseek_repr_does_not_include_api_key():
    secret = "sk-NEVER-LEAK-THIS-VALUE-1234567890"
    provider = DeepSeekProvider(api_key=secret)
    assert secret not in repr(provider)
    assert secret not in str(provider)


def test_deepseek_error_messages_do_not_include_api_key(caplog):
    secret = "sk-MUST-NOT-APPEAR-IN-LOGS-9876543210"

    def handler(_request: httpx.Request) -> httpx.Response:
        return _make_response(401, {"error": "bad"})

    transport = httpx.MockTransport(handler)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(LLMAuthError) as exc_info:
        _run(_do_chat(transport, api_key=secret))
    assert secret not in str(exc_info.value)
    for record in caplog.records:
        assert secret not in record.getMessage()


def test_deepseek_constructor_rejects_empty_key():
    with pytest.raises(ValueError):
        DeepSeekProvider(api_key="")


# ────────── MockLLMProvider ──────────


def test_mock_provider_echoes_last_user_message():
    provider = MockLLMProvider()
    response = _run(
        provider.chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="system", content="you are helpful"),
                    ChatMessage(role="user", content="alpha"),
                    ChatMessage(role="assistant", content="prev reply"),
                    ChatMessage(role="user", content="beta"),
                ]
            )
        )
    )
    assert "beta" in response.content
    assert response.model_used == "mock"
    assert response.fallback_used is False


def test_mock_provider_handles_only_system_message():
    provider = MockLLMProvider()
    response = _run(
        provider.chat(
            ChatRequest(messages=[ChatMessage(role="system", content="hi")])
        )
    )
    assert response.model_used == "mock"
    assert "No user message" in response.content


# ────────── Factory ──────────


def test_factory_returns_mock_when_env_unset(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    provider = get_default_provider()
    assert isinstance(provider, MockLLMProvider)


def test_factory_returns_mock_when_env_blank(monkeypatch):
    """Whitespace-only API key → still treat as unset."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
    provider = get_default_provider()
    assert isinstance(provider, MockLLMProvider)


def test_factory_returns_real_when_env_set(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-real-test-value")
    provider = get_default_provider()
    assert isinstance(provider, DeepSeekProvider)


def test_factory_logs_warning_in_mock_mode(monkeypatch, caplog):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    caplog.set_level(logging.WARNING)
    get_default_provider()
    assert any(
        "DEEPSEEK_API_KEY" in rec.getMessage()
        and "MockLLMProvider" in rec.getMessage()
        for rec in caplog.records
    )


# ────────── Sanity: error hierarchy ──────────


def test_all_errors_inherit_from_llm_provider_error():
    for cls in (LLMAuthError, LLMRateLimitError, LLMUpstreamError, LLMTimeoutError):
        assert issubclass(cls, LLMProviderError)
