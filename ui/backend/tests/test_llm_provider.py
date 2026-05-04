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
    LLMBadRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    MockLLMProvider,
    close_cached_provider,
    get_default_provider,
)
from ui.backend.services.llm_provider.base import LLMProviderError  # noqa: F401
from ui.backend.services.llm_provider.factory import reset_default_provider

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


# ────────── Codex R1 P2: 4xx (non-auth/non-rate-limit) bypasses fallback ──────────


def test_deepseek_400_raises_bad_request_no_fallback():
    """A 400 (e.g. context_length_exceeded) is the caller's problem.
    Don't waste a flash retry — same payload would just produce the
    same 400. R1 P2 regression."""
    call_count = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return _make_response(400, {"error": "context_length_exceeded"})

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMBadRequestError):
        _run(_do_chat(transport))
    # Critically: only ONE call. No fallback retry.
    assert call_count["n"] == 1


def test_deepseek_422_raises_bad_request_no_fallback():
    call_count = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return _make_response(422, {"error": "invalid_request"})

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMBadRequestError):
        _run(_do_chat(transport))
    assert call_count["n"] == 1


def test_deepseek_404_raises_bad_request_no_fallback():
    """Any unexpected non-401/403/429 4xx should be non-retryable."""
    call_count = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return _make_response(404, {"error": "not found"})

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMBadRequestError):
        _run(_do_chat(transport))
    assert call_count["n"] == 1


# ────────── Codex R1 P3: provider singleton (long-lived AsyncClient) ──────────


def test_factory_returns_same_instance_across_calls(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-singleton-test")
    reset_default_provider()
    p1 = get_default_provider()
    p2 = get_default_provider()
    assert p1 is p2  # singleton


def test_factory_rebuilds_when_env_changes(monkeypatch):
    """Test isolation: flipping DEEPSEEK_API_KEY in the env must
    invalidate the cache so we don't serve a real provider after the
    test set the env to empty."""
    reset_default_provider()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-first")
    p1 = get_default_provider()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-second")
    p2 = get_default_provider()
    assert p1 is not p2  # rebuilt
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    p3 = get_default_provider()
    assert isinstance(p3, MockLLMProvider)


def test_factory_rebuilds_on_same_length_key_rotation(monkeypatch):
    """Codex R2 P2 regression: a SHA-256 fingerprint distinguishes
    distinct keys regardless of length. The previous length-only
    fingerprint collided on same-length rotations (DeepSeek keys are
    uniformly 35 chars), causing later chats to keep sending the
    stale credential after a rotation."""
    reset_default_provider()
    # Two distinct keys with identical length.
    key_a = "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 35 chars
    key_b = "sk-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"  # 35 chars
    assert len(key_a) == len(key_b)
    assert key_a != key_b
    monkeypatch.setenv("DEEPSEEK_API_KEY", key_a)
    p1 = get_default_provider()
    monkeypatch.setenv("DEEPSEEK_API_KEY", key_b)
    p2 = get_default_provider()
    assert p1 is not p2, "same-length key rotation must invalidate cache"


def test_close_cached_provider_calls_aclose_and_clears_cache(monkeypatch):
    """Codex R8 P2 regression: the documented lifespan close path
    must actually call aclose on the cached provider AND clear the
    cache so a subsequent get_default_provider builds a fresh one."""
    reset_default_provider()
    aclose_calls: list[str] = []

    class _RecordingProvider(MockLLMProvider):
        async def aclose(self) -> None:
            aclose_calls.append("closed")

    from ui.backend.services.llm_provider import factory as factory_module

    monkeypatch.setattr(
        factory_module,
        "DeepSeekProvider",
        lambda api_key: _RecordingProvider(),
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-lifespan-test-1234567890abcdef")
    p1 = get_default_provider()
    assert isinstance(p1, _RecordingProvider)

    asyncio.run(close_cached_provider())
    assert aclose_calls == ["closed"]

    # Subsequent get_default_provider builds a new instance (cache cleared).
    p2 = get_default_provider()
    assert p2 is not p1


def test_close_cached_provider_is_noop_when_cache_empty():
    """Idempotent: safe to call from lifespan-shutdown even if no
    provider was ever requested."""
    reset_default_provider()
    asyncio.run(close_cached_provider())  # should not raise


def test_factory_drops_evicted_provider_without_close(monkeypatch):
    """V1 cleanup contract (post-Codex R7): the factory does NOT call
    aclose on the displaced provider. Lifespan-shutdown is the only
    close path. In-process key rotation is documented as unsupported
    (DEC-V61-118 §risk register R5). A test that flips the env var
    therefore observes a fresh-instance singleton; the previous
    provider is left for GC."""
    reset_default_provider()

    aclose_calls: list[str] = []

    class _RecordingProvider(MockLLMProvider):
        def __init__(self, tag: str) -> None:
            super().__init__()
            self._tag = tag

        async def aclose(self) -> None:
            aclose_calls.append(self._tag)

    from ui.backend.services.llm_provider import factory as factory_module

    counter = {"n": 0}

    def _fake_deepseek_provider(api_key: str) -> _RecordingProvider:
        counter["n"] += 1
        return _RecordingProvider(f"p{counter['n']}")

    monkeypatch.setattr(factory_module, "DeepSeekProvider", _fake_deepseek_provider)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    p1 = get_default_provider()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    p2 = get_default_provider()
    assert p1 is not p2
    # No automatic aclose on rebuild. The test caller can do it
    # manually if they want to verify lifecycle:
    assert aclose_calls == [], (
        f"factory must NOT call aclose on evicted provider; got {aclose_calls}"
    )


def test_factory_reset_clears_cache(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-cache-test")
    reset_default_provider()
    p1 = get_default_provider()
    reset_default_provider()
    p2 = get_default_provider()
    assert p1 is not p2  # cache was cleared


def test_factory_does_not_log_api_key_in_fingerprint(monkeypatch, caplog):
    secret = "sk-NEVER-LEAK-SINGLETON-1234567890abcdef"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    reset_default_provider()
    caplog.set_level(logging.DEBUG)
    get_default_provider()
    for record in caplog.records:
        assert secret not in record.getMessage()


def test_deepseek_aclose_is_idempotent():
    """aclose can be called twice without error (e.g. lifespan
    shutdown after a test that already cleaned up)."""
    provider = DeepSeekProvider(api_key="sk-aclose-test")
    _run(provider.aclose())
    _run(provider.aclose())  # no error


def test_deepseek_aclose_does_not_close_injected_client():
    """If the caller injected an httpx client (test path), the
    provider must NOT close it on aclose() — the caller owns its
    lifetime."""

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: _make_response(200, _success_body()))
        ) as client:
            provider = DeepSeekProvider(api_key="sk-test", client=client)
            await provider.aclose()
            # Client should still be usable.
            assert not client.is_closed

    _run(scenario())


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
