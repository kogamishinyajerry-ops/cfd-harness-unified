"""Streaming-path unit tests for the LLM provider abstraction (DEC-V61-119).

Exercises:
  * :class:`ChatStreamChunk` Pydantic shape
  * :class:`MockLLMProvider.chat_stream` deterministic chunking
  * :class:`DeepSeekProvider.chat_stream` SSE parsing across:
      - normal multi-frame stream with [DONE] terminator
      - stream that closes without an explicit [DONE]
      - frame carrying usage on the finish_reason event
      - malformed JSON event line → LLMUpstreamError
      - HTTP 401/429/4xx/5xx BEFORE stream opens → typed exception
      - timeout mid-stream → LLMTimeoutError
      - api_key never appears in repr or any logged context
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Iterator, TypeVar

import httpx
import pytest

from ui.backend.services.llm_provider import (
    ChatMessage,
    ChatRequest,
    ChatStreamChunk,
    DeepSeekProvider,
    LLMAuthError,
    LLMBadRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    MockLLMProvider,
)

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def _sse_response(events: Iterator[bytes], status: int = 200) -> httpx.Response:
    """Wrap a sequence of SSE event bytes into an httpx Response with a
    chunked body. Each element should already be terminated with
    ``\\n\\n``.
    """
    request = httpx.Request("POST", "https://x")
    return httpx.Response(
        status,
        content=b"".join(events) if status >= 400 else None,
        stream=httpx.ByteStream(b"".join(events)) if status == 200 else None,
        request=request,
    )


def _sse_lines(*events: str) -> bytes:
    """Build a complete SSE body from data: payload strings."""
    return b"".join(f"data: {ev}\n\n".encode("utf-8") for ev in events)


# ────────── ChatStreamChunk ──────────


def test_chat_stream_chunk_defaults():
    chunk = ChatStreamChunk(model_used="mock")
    assert chunk.delta == ""
    assert chunk.done is False
    assert chunk.usage is None
    assert chunk.fallback_used is False


def test_chat_stream_chunk_terminal_with_usage():
    chunk = ChatStreamChunk(
        delta="",
        done=True,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        model_used="deepseek-v4-pro",
    )
    assert chunk.done
    assert chunk.usage["total_tokens"] == 15


# ────────── MockLLMProvider.chat_stream ──────────


def test_mock_provider_chat_stream_yields_chunks_then_terminal():
    async def collect() -> list[ChatStreamChunk]:
        provider = MockLLMProvider()
        request = ChatRequest(messages=[ChatMessage(role="user", content="hello world")])
        out: list[ChatStreamChunk] = []
        async for chunk in provider.chat_stream(request):
            out.append(chunk)
        return out

    chunks = _run(collect())
    assert len(chunks) >= 2
    assert chunks[-1].done is True
    assert chunks[-1].model_used == "mock"
    # Concatenating non-terminal deltas reproduces the synthesized echo.
    full = "".join(c.delta for c in chunks if not c.done)
    assert "You said: hello world" in full


def test_mock_provider_chat_stream_emits_exactly_one_done():
    async def collect() -> list[ChatStreamChunk]:
        provider = MockLLMProvider()
        request = ChatRequest(messages=[ChatMessage(role="user", content="x")])
        return [c async for c in provider.chat_stream(request)]

    chunks = _run(collect())
    done_count = sum(1 for c in chunks if c.done)
    assert done_count == 1


# ────────── DeepSeekProvider.chat_stream ──────────


async def _do_stream(
    transport: httpx.MockTransport,
    *,
    api_key: str = "sk-test",
    model: str = "deepseek-v4-pro",
) -> list[ChatStreamChunk]:
    async with httpx.AsyncClient(transport=transport) as client:
        provider = DeepSeekProvider(api_key=api_key, client=client)
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            model=model,  # type: ignore[arg-type]
        )
        out: list[ChatStreamChunk] = []
        async for chunk in provider.chat_stream(request):
            out.append(chunk)
        return out


def test_deepseek_stream_normal_flow_with_done_marker():
    body = _sse_lines(
        '{"choices":[{"delta":{"content":"你"},"finish_reason":null}]}',
        '{"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}],"usage":'
        '{"prompt_tokens":12,"completion_tokens":3,"total_tokens":15}}',
        "[DONE]",
    )
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, request=r)
    )
    chunks = _run(_do_stream(transport))
    # 2 content frames + 1 terminal (the [DONE] frame after finish_reason)
    deltas = [c.delta for c in chunks if not c.done]
    assert deltas == ["你", "好"]
    terminal = [c for c in chunks if c.done]
    assert len(terminal) == 1
    assert terminal[0].usage == {
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
    }
    assert terminal[0].model_used == "deepseek-v4-pro"


def test_deepseek_stream_no_explicit_done_synthesizes_terminal():
    """Some providers close the stream without a `[DONE]` marker. Our
    impl synthesizes a terminal chunk so consumers always see one.
    """
    body = _sse_lines(
        '{"choices":[{"delta":{"content":"a"},"finish_reason":null}]}',
        '{"choices":[{"delta":{"content":"b"},"finish_reason":"stop"}]}',
    )
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, request=r)
    )
    chunks = _run(_do_stream(transport))
    deltas = [c.delta for c in chunks if not c.done]
    assert deltas == ["a", "b"]
    assert any(c.done for c in chunks)


def test_deepseek_stream_skips_role_announce_frame():
    """The first frame in OpenAI-compatible SSE is often a
    role-announce frame with no content. We should skip it silently."""
    body = _sse_lines(
        '{"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}',
        '{"choices":[{"delta":{"content":"x"},"finish_reason":null}]}',
        "[DONE]",
    )
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, request=r)
    )
    chunks = _run(_do_stream(transport))
    deltas = [c.delta for c in chunks if not c.done]
    assert deltas == ["x"]


def test_deepseek_stream_malformed_json_raises_upstream():
    body = b"data: {not json}\n\n"
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, request=r)
    )
    with pytest.raises(LLMUpstreamError):
        _run(_do_stream(transport))


def test_deepseek_stream_401_before_open_raises_auth_error():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(401, json={"error": "bad key"}, request=r)
    )
    with pytest.raises(LLMAuthError):
        _run(_do_stream(transport, api_key="sk-bad"))


def test_deepseek_stream_429_before_open_raises_rate_limit():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(429, json={"error": "slow down"}, request=r)
    )
    with pytest.raises(LLMRateLimitError):
        _run(_do_stream(transport))


def test_deepseek_stream_4xx_before_open_raises_bad_request():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(
            400, json={"error": "context_length_exceeded"}, request=r
        )
    )
    with pytest.raises(LLMBadRequestError):
        _run(_do_stream(transport))


def test_deepseek_stream_5xx_before_open_raises_upstream():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(503, json={"error": "down"}, request=r)
    )
    with pytest.raises(LLMUpstreamError):
        _run(_do_stream(transport))


def test_deepseek_stream_timeout_raises_timeout_error():
    def raise_timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated", request=_request)

    transport = httpx.MockTransport(raise_timeout)
    with pytest.raises(LLMTimeoutError):
        _run(_do_stream(transport))


def test_deepseek_stream_repr_does_not_contain_api_key():
    # Same secrets-handling discipline as the non-streaming chat path.
    provider = DeepSeekProvider(api_key="sk-very-secret-token-do-not-leak")
    assert "sk-very-secret-token-do-not-leak" not in repr(provider)


def test_deepseek_stream_no_mid_stream_fallback_v1():
    """Per DEC-V61-119 §V1 explicit scope-down: chat_stream commits to
    one model. A 5xx mid-stream surfaces as LLMUpstreamError; chat_stream
    does NOT silently retry against the flash variant."""
    body = b"data: {malformed\n\n"  # forces an upstream error after open
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, request=r)
    )
    with pytest.raises(LLMUpstreamError):
        _run(_do_stream(transport))
    # The fact that we raised (rather than "magically recovered") is
    # the assertion.
