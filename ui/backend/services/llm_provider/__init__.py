"""LLM provider abstraction (DEC-V61-118).

Public surface for the workbench's free-form chat path. Distinct from
``services.ai_actions`` which handles deterministic structured actions
(rule-based BC classifier + envelope contract). This package is the
plumbing for V61-119's governance-aware coaching — V1 is a minimal
non-streaming chat with DeepSeek V4 Pro primary + V4 Flash fallback.

Streaming, tool-calling, and governance system-prompt composition are
explicitly out-of-scope here and land in V61-119.
"""
from __future__ import annotations

from ui.backend.services.llm_provider.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
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
