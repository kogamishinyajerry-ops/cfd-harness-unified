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
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)


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
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        assert_non_opus(model_id)
        self.model_id = model_id
        self._api_key = api_key or _require_env("ANTHROPIC_API_KEY")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, transport=transport)
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
        response = self._client.post(
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
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        assert_non_opus(model_id)
        self.model_id = model_id
        self._api_key = api_key or _require_env(api_key_env)
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, transport=transport)
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
        payload: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, *messages],
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
        response = self._client.post(
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
    timeout: float = 60.0,
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
    timeout: float = 60.0,
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
