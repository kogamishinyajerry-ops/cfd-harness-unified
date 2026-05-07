"""Persona-side LLM clients for the B-arc dogfood harness.

Three thin HTTP wrappers (Anthropic / DeepSeek / OpenAI-compat) sharing
a common `LLMClient` Protocol. Each takes a list of messages + tool
definitions and returns the next assistant message (text or tool_use).

NOT a replacement for `ui/backend/services/llm_provider/` — that lives
on the workbench side for `/api/cases/.../ai-{review,diagnose}` chat
calls. Personas need a multi-turn tool-use loop with structured tool
calls, not single-shot review/diagnose; hence a separate class
hierarchy.

Hard rule: `build_client(model)` aborts if model id resolves to an
Opus variant. Charter DEC-V61-162 forbids Opus personas to mitigate
Opus-reads-Opus echo chamber.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)


# F14 mitigation (DEC-V61-192, B-ext-5): R9 backward_step crashed at
# step 20 after a 15.5-min wait on DeepSeek; the original `timeout=60.0`
# was a single value that httpx applied per phase, but slow trickle-byte
# responses kept the read socket below the per-byte read deadline. Fix:
# explicit per-phase timeouts (connect=10s, read=180s) + 1 retry on
# the network-class exceptions that R9 surfaced.
_DEFAULT_TIMEOUT: httpx.Timeout = httpx.Timeout(
    connect=10.0, read=180.0, write=30.0, pool=30.0
)
_RETRYABLE_EXC: tuple[type[BaseException], ...] = (
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
)


def _resolve_timeout(timeout: float | httpx.Timeout | None) -> httpx.Timeout:
    """Back-compat: accept a float (legacy callers) or `httpx.Timeout`.

    A bare float gets coerced to per-phase Timeout with read=value but
    other phases capped to keep handshake fast.
    """
    if timeout is None:
        return _DEFAULT_TIMEOUT
    if isinstance(timeout, httpx.Timeout):
        return timeout
    # legacy float — keep read=timeout (as caller intended) but use
    # tighter connect/write so we don't block on dead DNS / dead writes
    return httpx.Timeout(
        connect=min(10.0, float(timeout)),
        read=float(timeout),
        write=min(30.0, float(timeout)),
        pool=min(30.0, float(timeout)),
    )


def _post_with_retry(
    client: httpx.Client,
    url: str,
    *,
    json: dict[str, Any],
    headers: dict[str, str],
    retries: int = 1,
    backoff_s: float = 5.0,
) -> httpx.Response:
    """POST with retry on transient network errors (F14 mitigation).

    `retries=1` → up to 2 total attempts. We retry only on the
    transient-network class; HTTP 4xx/5xx are returned to caller (they
    handle non-2xx via raise_for_status). The original exception from
    the final attempt re-raises.
    """
    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return client.post(url, json=json, headers=headers)
        except _RETRYABLE_EXC as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning(
                    "POST %s failed (attempt %d/%d): %s; retrying in %.1fs",
                    url,
                    attempt + 1,
                    retries + 1,
                    exc.__class__.__name__,
                    backoff_s,
                )
                time.sleep(backoff_s)
                continue
            raise
    # unreachable — loop either returns or re-raises
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolDef:
    """Tool definition exposed to the persona LLM."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A tool_use issued by the model."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AssistantMessage:
    """One step of model output: text + zero-or-more tool calls."""

    text: str
    tool_calls: tuple[ToolCall, ...]
    raw_usage: dict[str, int]


class LLMClient(Protocol):
    """Common surface for the three persona-side providers."""

    model_id: str

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> AssistantMessage:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# Opus guard
# ---------------------------------------------------------------------------


_OPUS_PATTERNS = ("opus", "claude-opus")


class OpusPersonaForbidden(RuntimeError):
    """Raised when a caller tries to instantiate an Opus persona client."""


def assert_non_opus(model_id: str) -> None:
    """Reject any model id whose lowercased form contains 'opus'.

    Charter DEC-V61-162 §threat-model: Opus-reads-Opus echo chamber
    invalidates dogfood signal. Personas must run on Sonnet 4.6 /
    DeepSeek V4 Pro / gpt-5.4 only.
    """
    lowered = model_id.lower()
    for pattern in _OPUS_PATTERNS:
        if pattern in lowered:
            raise OpusPersonaForbidden(
                f"Opus models are forbidden as personas (got {model_id!r}); "
                "use Sonnet 4.6 / DeepSeek V4 Pro / gpt-5.4 (charter DEC-V61-162)."
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fingerprint(secret: str | None) -> str:
    if not secret:
        return "<unset>"
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]


def _require_env(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise RuntimeError(f"Required env var {var!r} is not set")
    return value


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert harness-internal (Anthropic-shaped) messages to OpenAI/DeepSeek wire format.

    persona_runner emits assistant messages with `content: [{type:text}, {type:tool_use}]`
    and user follow-ups with `content: [{type:tool_result, tool_use_id, content, is_error}]`.

    OpenAI-compat APIs (DeepSeek, gpt-5.4 via 86gs) want:
      - assistant: {role: "assistant", content: <text>, tool_calls: [{id, type:"function", function:{name, arguments:json}}]}
      - tool result: {role: "tool", tool_call_id: <id>, content: <text>}
    """
    import json as _json

    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "assistant" and isinstance(content, list):
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(str(block.get("text") or ""))
                elif btype == "tool_use":
                    tool_calls.append(
                        {
                            "id": str(block.get("id") or ""),
                            "type": "function",
                            "function": {
                                "name": str(block.get("name") or ""),
                                "arguments": _json.dumps(
                                    block.get("input") or {},
                                    ensure_ascii=False,
                                ),
                            },
                        }
                    )
            converted: dict[str, Any] = {
                "role": "assistant",
                "content": "\n".join(p for p in text_parts if p) or None,
            }
            if tool_calls:
                converted["tool_calls"] = tool_calls
            out.append(converted)
            continue

        if role == "user" and isinstance(content, list):
            tool_results: list[dict[str, Any]] = []
            text_blocks: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    body = block.get("content")
                    if not isinstance(body, str):
                        body = _json.dumps(body, ensure_ascii=False)
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": str(block.get("tool_use_id") or ""),
                            "content": body,
                        }
                    )
                elif block.get("type") == "text":
                    text_blocks.append(str(block.get("text") or ""))
            if tool_results:
                out.extend(tool_results)
                continue
            if text_blocks:
                out.append({"role": "user", "content": "\n".join(text_blocks)})
                continue

        # fallthrough: pass through unmodified (string content, system msgs, etc.)
        out.append(msg)
    return out


# ---------------------------------------------------------------------------
# Anthropic (Sonnet 4.6)
# ---------------------------------------------------------------------------


class AnthropicClient:
    """Thin wrapper over the Anthropic Messages API for Sonnet 4.6 personas."""

    def __init__(
        self,
        *,
        model_id: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        timeout: float | httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        assert_non_opus(model_id)
        self.model_id = model_id
        self._api_key = api_key or _require_env("ANTHROPIC_API_KEY")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=_resolve_timeout(timeout), transport=transport
        )
        logger.info(
            "AnthropicClient model=%s key_fp=%s",
            model_id,
            _fingerprint(self._api_key),
        )

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> AssistantMessage:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]
        response = _post_with_retry(
            self._client,
            f"{self._base_url}/v1/messages",
            json=payload,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        call_id=str(block.get("id", "")),
                        tool_name=str(block.get("name", "")),
                        arguments=dict(block.get("input", {}) or {}),
                    )
                )
        return AssistantMessage(
            text="\n".join(text_parts).strip(),
            tool_calls=tuple(tool_calls),
            raw_usage=dict(data.get("usage", {}) or {}),
        )

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# OpenAI-compat (gpt-5.4 via 86gs relay) — also handles DeepSeek wire shape
# ---------------------------------------------------------------------------


class OpenAICompatClient:
    """Generic OpenAI chat-completions client.

    Used for both gpt-5.4 (via 86gs relay) and DeepSeek V4 Pro (whose
    wire format is OpenAI-compat). Tool calls are emitted via the
    `tool_calls` array on the assistant message; we map them back into
    our common `ToolCall` shape.
    """

    def __init__(
        self,
        *,
        model_id: str,
        api_key: str | None,
        base_url: str,
        api_key_env: str,
        timeout: float | httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        assert_non_opus(model_id)
        self.model_id = model_id
        self._api_key = api_key or _require_env(api_key_env)
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=_resolve_timeout(timeout), transport=transport
        )
        logger.info(
            "OpenAICompatClient model=%s base=%s key_fp=%s",
            model_id,
            base_url,
            _fingerprint(self._api_key),
        )

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> AssistantMessage:
        oai_messages = _to_openai_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, *oai_messages],
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]
        response = _post_with_retry(
            self._client,
            f"{self._base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {}) or {}
        text = (message.get("content") or "").strip()
        raw_calls = message.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for raw in raw_calls:
            fn = raw.get("function", {}) or {}
            arguments = fn.get("arguments") or "{}"
            if isinstance(arguments, str):
                import json

                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"_raw": arguments}
            if not isinstance(arguments, dict):
                arguments = {"_raw": arguments}
            tool_calls.append(
                ToolCall(
                    call_id=str(raw.get("id", "")),
                    tool_name=str(fn.get("name", "")),
                    arguments=arguments,
                )
            )
        return AssistantMessage(
            text=text,
            tool_calls=tuple(tool_calls),
            raw_usage=dict(data.get("usage", {}) or {}),
        )

    def close(self) -> None:
        self._client.close()


# Convenience constructors -------------------------------------------------


def DeepSeekClient(
    *,
    model_id: str = "deepseek-chat",
    api_key: str | None = None,
    base_url: str = "https://api.deepseek.com/v1",
    timeout: float | httpx.Timeout | None = None,
    transport: httpx.BaseTransport | None = None,
) -> OpenAICompatClient:
    return OpenAICompatClient(
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        api_key_env="DEEPSEEK_API_KEY",
        timeout=timeout,
        transport=transport,
    )


def Gpt54Client(
    *,
    model_id: str = "gpt-5.4",
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float | httpx.Timeout | None = None,
    transport: httpx.BaseTransport | None = None,
) -> OpenAICompatClient:
    base = base_url or os.environ.get(
        "DOGFOOD_GPT54_BASE_URL", "https://api.86gamestore.com/v1"
    )
    return OpenAICompatClient(
        model_id=model_id,
        api_key=api_key,
        base_url=base,
        api_key_env="CODEX_RELAY_API_KEY",
        timeout=timeout,
        transport=transport,
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


_FAMILY_BUILDERS = {
    "anthropic": lambda model_id, **kw: AnthropicClient(model_id=model_id, **kw),
    "deepseek": lambda model_id, **kw: DeepSeekClient(model_id=model_id, **kw),
    "openai_compat": lambda model_id, **kw: Gpt54Client(model_id=model_id, **kw),
}


def build_client(family: str, model_id: str, **kwargs: Any) -> LLMClient:
    """Resolve a persona-side LLM client by model family.

    family ∈ {"anthropic", "deepseek", "openai_compat"}
    Raises `OpusPersonaForbidden` if model_id resolves to Opus.
    """
    builder = _FAMILY_BUILDERS.get(family)
    if builder is None:
        raise ValueError(
            f"Unknown LLM family {family!r}; expected one of "
            f"{sorted(_FAMILY_BUILDERS)}"
        )
    assert_non_opus(model_id)
    return builder(model_id, **kwargs)


__all__ = [
    "AnthropicClient",
    "AssistantMessage",
    "DeepSeekClient",
    "Gpt54Client",
    "LLMClient",
    "OpenAICompatClient",
    "OpusPersonaForbidden",
    "ToolCall",
    "ToolDef",
    "assert_non_opus",
    "build_client",
]
