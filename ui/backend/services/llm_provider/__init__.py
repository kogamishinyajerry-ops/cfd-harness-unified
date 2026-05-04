"""LLM provider abstraction (DEC-V61-118 + V61-119).

Public surface for the workbench's free-form chat path. Distinct from
``services.ai_actions`` which handles deterministic structured actions
(rule-based BC classifier + envelope contract).

V61-118 added the non-streaming ``chat`` path + DeepSeek V4 Pro primary
+ V4 Flash fallback. V61-119 added streaming (``chat_stream`` +
:class:`ChatStreamChunk`) for the AI coach SSE route. LLM-side tool
calling and mid-stream fallback remain explicitly deferred.
"""
from __future__ import annotations

from ui.backend.services.llm_provider.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    LLMAuthError,
    LLMBadRequestError,
    LLMConfigError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    MockLLMProvider,
)
from ui.backend.services.llm_provider.deepseek import DeepSeekProvider
from ui.backend.services.llm_provider.factory import (
    close_cached_provider,
    get_default_provider,
)

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatStreamChunk",
    "DeepSeekProvider",
    "close_cached_provider",
    "LLMAuthError",
    "LLMBadRequestError",
    "LLMConfigError",
    "LLMProvider",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMUpstreamError",
    "MockLLMProvider",
    "get_default_provider",
]
