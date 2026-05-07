"""Tests for scripts/dogfood/llm_clients.py — Opus guard + factory + parsers."""
from __future__ import annotations

import json

import httpx
import pytest

from scripts.dogfood.llm_clients import (
    AnthropicClient,
    DeepSeekClient,
    Gpt54Client,
    OpenAICompatClient,
    OpusPersonaForbidden,
    ToolDef,
    assert_non_opus,
    build_client,
)


# ---------------------------------------------------------------------------
# Opus guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_id",
    [
        "claude-opus-4-7",
        "claude-opus-4-7[1m]",
        "claude-Opus-4-7",
        "OPUS-4",
        "anthropic/claude-opus-4",
        "opus",
        "Claude-Opus",
        "some-prefix-opus-suffix",
    ],
)
def test_opus_guard_rejects_opus_variants(model_id: str) -> None:
    with pytest.raises(OpusPersonaForbidden):
        assert_non_opus(model_id)


@pytest.mark.parametrize(
    "model_id",
    [
        "claude-sonnet-4-6",
        "deepseek-chat",
        "gpt-5.4",
        "gpt-5.5",
        "claude-haiku-4-5",
    ],
)
def test_opus_guard_passes_non_opus(model_id: str) -> None:
    assert_non_opus(model_id)


def test_factory_rejects_opus_family_anthropic() -> None:
    with pytest.raises(OpusPersonaForbidden):
        build_client("anthropic", "claude-opus-4-7", api_key="test")


def test_factory_rejects_opus_family_openai_compat() -> None:
    with pytest.raises(OpusPersonaForbidden):
        build_client("openai_compat", "claude-opus-via-openai", api_key="test")


def test_factory_unknown_family() -> None:
    with pytest.raises(ValueError):
        build_client("unknown", "some-model")


# ---------------------------------------------------------------------------
# Anthropic client wire shape
# ---------------------------------------------------------------------------


def test_anthropic_client_text_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "hello world"}],
                "usage": {"input_tokens": 10, "output_tokens": 4},
            },
        )

    transport = httpx.MockTransport(handler)
    client = AnthropicClient(
        model_id="claude-sonnet-4-6",
        api_key="sk-test",
        transport=transport,
    )
    msg = client.chat(
        system="be helpful",
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
    )
    assert msg.text == "hello world"
    assert msg.tool_calls == ()
    assert msg.raw_usage == {"input_tokens": 10, "output_tokens": 4}
    assert captured["url"].endswith("/v1/messages")
    body = captured["body"]
    assert body["model"] == "claude-sonnet-4-6"
    client.close()


def test_anthropic_client_tool_use_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "fetching state"},
                    {
                        "type": "tool_use",
                        "id": "tu_1",
                        "name": "http_get",
                        "input": {"url": "/api/cases/x", "rationale": "check state"},
                    },
                ],
                "usage": {"input_tokens": 12, "output_tokens": 9},
            },
        )

    transport = httpx.MockTransport(handler)
    client = AnthropicClient(
        model_id="claude-sonnet-4-6",
        api_key="sk-test",
        transport=transport,
    )
    msg = client.chat(
        system="be careful",
        messages=[{"role": "user", "content": "do it"}],
        tools=[
            ToolDef(name="http_get", description="GET", input_schema={"type": "object"}),
        ],
    )
    assert len(msg.tool_calls) == 1
    call = msg.tool_calls[0]
    assert call.tool_name == "http_get"
    assert call.arguments == {"url": "/api/cases/x", "rationale": "check state"}
    assert call.call_id == "tu_1"
    client.close()


# ---------------------------------------------------------------------------
# OpenAI-compat parsing (covers DeepSeek + gpt-5.4)
# ---------------------------------------------------------------------------


def test_openai_compat_parses_string_arguments() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "decided",
                            "tool_calls": [
                                {
                                    "id": "call_a",
                                    "type": "function",
                                    "function": {
                                        "name": "http_post",
                                        "arguments": json.dumps(
                                            {"url": "/api/cases/y/mesh", "rationale": "engineer-driven"}
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 8, "completion_tokens": 7},
            },
        )

    transport = httpx.MockTransport(handler)
    client = OpenAICompatClient(
        model_id="gpt-5.4",
        api_key="sk-test",
        base_url="https://relay.example/v1",
        api_key_env="UNUSED",
        transport=transport,
    )
    msg = client.chat(
        system="be terse",
        messages=[{"role": "user", "content": "go"}],
        tools=[ToolDef(name="http_post", description="POST", input_schema={"type": "object"})],
    )
    assert msg.text == "decided"
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].arguments["url"] == "/api/cases/y/mesh"
    assert msg.tool_calls[0].arguments["rationale"] == "engineer-driven"
    client.close()


def test_openai_compat_handles_malformed_arguments_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_b",
                                    "type": "function",
                                    "function": {
                                        "name": "http_get",
                                        "arguments": "{not_valid_json",
                                    },
                                }
                            ],
                        }
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = OpenAICompatClient(
        model_id="gpt-5.4",
        api_key="sk-test",
        base_url="https://relay.example/v1",
        api_key_env="UNUSED",
        transport=transport,
    )
    msg = client.chat(system="x", messages=[], tools=[])
    assert msg.tool_calls[0].arguments == {"_raw": "{not_valid_json"}
    client.close()


def test_deepseek_convenience_constructor_uses_correct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )
    client = DeepSeekClient(transport=transport)
    assert client.model_id == "deepseek-chat"
    msg = client.chat(system="x", messages=[], tools=[])
    assert msg.text == "ok"
    client.close()


def test_gpt54_convenience_constructor_uses_correct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_RELAY_API_KEY", "sk-relay-test")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )
    client = Gpt54Client(transport=transport)
    assert client.model_id == "gpt-5.4"
    client.close()


def test_anthropic_requires_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicClient(model_id="claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# F14 mitigation (DEC-V61-192): timeout per-phase + retry on transient errors
# ---------------------------------------------------------------------------


def test_default_timeout_is_per_phase_with_read_180s() -> None:
    """The default timeout should be a per-phase httpx.Timeout, not a single
    value that lets slow-trickle responses evade the read deadline (R9 F14)."""
    from scripts.dogfood.llm_clients import _DEFAULT_TIMEOUT

    assert isinstance(_DEFAULT_TIMEOUT, httpx.Timeout)
    assert _DEFAULT_TIMEOUT.read == 180.0
    assert _DEFAULT_TIMEOUT.connect == 10.0


def test_resolve_timeout_accepts_legacy_float() -> None:
    """Float timeouts (legacy callers) keep working, but get coerced to
    per-phase shape so connect/write don't inherit a long read value."""
    from scripts.dogfood.llm_clients import _resolve_timeout

    t = _resolve_timeout(60.0)
    assert isinstance(t, httpx.Timeout)
    assert t.read == 60.0
    assert t.connect == 10.0  # capped at 10
    assert t.write == 30.0  # capped at 30


def test_post_with_retry_succeeds_after_one_read_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAICompatClient retries once on httpx.ReadTimeout; second attempt
    returns a clean response. Mirrors the F14 R9 backward_step crash mode."""
    monkeypatch.setattr("scripts.dogfood.llm_clients.time.sleep", lambda _s: None)

    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ReadTimeout("simulated", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    client = OpenAICompatClient(
        model_id="gpt-5.4",
        api_key="sk-test",
        base_url="https://relay.example/v1",
        api_key_env="UNUSED",
        transport=transport,
    )
    msg = client.chat(system="x", messages=[], tools=[])
    assert msg.text == "ok"
    assert attempts["n"] == 2  # 1 retry consumed
    client.close()


def test_post_with_retry_reraises_after_exhausted_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two consecutive ReadTimeouts → second is re-raised to caller."""
    monkeypatch.setattr("scripts.dogfood.llm_clients.time.sleep", lambda _s: None)

    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ReadTimeout("simulated", request=request)

    transport = httpx.MockTransport(handler)
    client = OpenAICompatClient(
        model_id="gpt-5.4",
        api_key="sk-test",
        base_url="https://relay.example/v1",
        api_key_env="UNUSED",
        transport=transport,
    )
    with pytest.raises(httpx.ReadTimeout):
        client.chat(system="x", messages=[], tools=[])
    assert attempts["n"] == 2  # 1 initial + 1 retry
    client.close()


def test_post_with_retry_does_not_retry_on_4xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 4xx is NOT a network error and must not be retried; caller
    receives the response and lets raise_for_status surface it."""
    monkeypatch.setattr("scripts.dogfood.llm_clients.time.sleep", lambda _s: None)

    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    transport = httpx.MockTransport(handler)
    client = OpenAICompatClient(
        model_id="gpt-5.4",
        api_key="sk-test",
        base_url="https://relay.example/v1",
        api_key_env="UNUSED",
        transport=transport,
    )
    with pytest.raises(httpx.HTTPStatusError):
        client.chat(system="x", messages=[], tools=[])
    assert attempts["n"] == 1  # no retry on HTTP error
    client.close()


def test_anthropic_client_also_retries_on_read_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F14 retry applies to AnthropicClient too — same code path."""
    monkeypatch.setattr("scripts.dogfood.llm_clients.time.sleep", lambda _s: None)

    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.RemoteProtocolError("server hung up", request=request)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "recovered"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    transport = httpx.MockTransport(handler)
    client = AnthropicClient(
        model_id="claude-sonnet-4-6",
        api_key="sk-test",
        transport=transport,
    )
    msg = client.chat(system="x", messages=[{"role": "user", "content": "hi"}], tools=[])
    assert msg.text == "recovered"
    assert attempts["n"] == 2
    client.close()
