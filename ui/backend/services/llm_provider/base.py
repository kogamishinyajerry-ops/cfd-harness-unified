"""LLMProvider abstraction + Pydantic request/response models + error hierarchy.

Provider implementations live alongside this module (``deepseek.py``);
the abstraction is intentionally minimal in V1 — just enough to
support multi-vendor hot-swap if DeepSeek goes down or pricing
changes. V1 only ships the DeepSeek adapter plus a Mock for tests +
no-key dev workflows.

Error hierarchy is typed so the route handler can map upstream
failures to clean HTTP status codes (401/429/502/500) without
string-matching exception messages.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ────────── Models ──────────

ChatRole = Literal["system", "user", "assistant"]
DeepSeekModelId = Literal["deepseek-v4-pro", "deepseek-v4-flash"]


class ChatMessage(BaseModel):
    """One turn in a chat conversation. Role + content only — V1 has no
    structured tool-call payloads (deferred to V61-119)."""

    role: ChatRole
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Inbound chat request. Validates non-empty messages and clamps
    temperature/max_tokens to safe ranges."""

    messages: list[ChatMessage] = Field(min_length=1)
    model: DeepSeekModelId = "deepseek-v4-pro"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)

    @field_validator("messages")
    @classmethod
    def _at_most_one_system(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        # OpenAI/DeepSeek convention: at most one system message, and
        # it must be the first if present. Catch malformed requests
        # before they reach the upstream.
        system_indices = [i for i, m in enumerate(v) if m.role == "system"]
        if len(system_indices) > 1:
            raise ValueError("at most one system message allowed")
        if system_indices and system_indices[0] != 0:
            raise ValueError("system message must be the first message")
        return v


class ChatResponse(BaseModel):
    """Outbound chat response. ``model_used`` and ``fallback_used``
    expose the actual path so the frontend can surface degraded modes
    transparently (mock mode banner, fallback warning, etc)."""

    content: str
    model_used: str
    fallback_used: bool = False
    usage: dict[str, int] = Field(default_factory=dict)


# ────────── Error hierarchy ──────────


class LLMProviderError(Exception):
    """Base for all LLM provider errors. Routes catch this and
    translate to HTTP status codes via the per-subclass mapping."""


class LLMAuthError(LLMProviderError):
    """Upstream returned 401/403 — bad API key. Does NOT trigger
    fallback (different model won't fix auth)."""


class LLMRateLimitError(LLMProviderError):
    """Upstream returned 429 — over quota. Triggers fallback to a
    cheaper / less-loaded model variant when available."""


class LLMBadRequestError(LLMProviderError):
    """Upstream 4xx (non-auth, non-rate-limit). The request itself is
    malformed/oversized/otherwise unacceptable; retrying with a
    different model would just waste another quota slot. Codex R1 P2:
    do NOT trigger fallback for these. Routes should map to 400 so
    the caller can fix their request."""


class LLMUpstreamError(LLMProviderError):
    """Upstream 5xx or malformed response. Triggers fallback (the
    backend service is having a bad time, alternate variant might
    be on a different shard)."""


class LLMTimeoutError(LLMProviderError):
    """Client-side timeout (httpx.TimeoutException). Treated as a
    fallback-eligible failure — the alternate variant may answer
    faster."""


class LLMConfigError(LLMProviderError):
    """Provider misconfiguration (missing API key, etc). Does NOT
    trigger fallback — this is a deployment problem, not a transient
    upstream issue."""


# ────────── Provider interface ──────────


class LLMProvider(ABC):
    """Minimal async chat interface. V1 has one method; V61-119 will
    add ``stream_chat`` + tool-calling support."""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat completion. May raise any LLMProviderError
        subclass; callers decide whether to retry/fallback based on
        the typed exception."""


# ────────── Mock provider for tests + no-key dev workflows ──────────


class MockLLMProvider(LLMProvider):
    """Synthetic-response provider used when ``DEEPSEEK_API_KEY`` is
    unset (dev workflows + CI). Echoes the last user message with a
    fixed prefix so tests can assert deterministic behavior. The
    response sets ``model_used="mock"`` so the frontend can surface a
    "demo mode" banner instead of silently behaving as if real."""

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # Find the last user message for the synthetic echo. Fall back
        # to a generic response if there is no user message (a request
        # with only a system message is valid input but unusual).
        last_user = next(
            (m for m in reversed(request.messages) if m.role == "user"),
            None,
        )
        if last_user is None:
            content = (
                "[Mock LLM Provider · DEEPSEEK_API_KEY unset] "
                "No user message in request."
            )
        else:
            content = (
                "[Mock LLM Provider · DEEPSEEK_API_KEY unset] "
                f"You said: {last_user.content}"
            )
        return ChatResponse(
            content=content,
            model_used="mock",
            fallback_used=False,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
