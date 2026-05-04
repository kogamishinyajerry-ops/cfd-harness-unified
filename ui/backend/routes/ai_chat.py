"""AI chat endpoint (DEC-V61-118 V1).

POST /api/ai-chat — non-streaming chat with the configured LLM provider.
V1 ships the foundation; V61-119 will add SSE streaming + tool calling
+ governance-aware system prompt composition.

Provider is resolved per-request via the factory so tests can monkey-
patch ``get_default_provider`` to inject a mock.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ui.backend.services.llm_provider import (
    ChatRequest,
    ChatResponse,
    LLMAuthError,
    LLMConfigError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    get_default_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ai-chat", response_model=ChatResponse)
async def ai_chat(request: ChatRequest) -> ChatResponse:
    """Execute a chat completion against the configured LLM provider.

    Status code mapping:
      * 200 — success
      * 401 — upstream auth failure (bad/missing API key)
      * 429 — upstream rate-limit (exhausted including fallback)
      * 502 — upstream timeout / 5xx / malformed response
      * 500 — provider misconfiguration / unexpected
    """
    provider = get_default_provider()
    try:
        return await provider.chat(request)
    except LLMAuthError as exc:
        # Don't leak the underlying message (may include status code
        # but not key); use a generic frontend-safe string.
        logger.error("AI chat auth error: %s", exc)
        raise HTTPException(
            status_code=401,
            detail="LLM provider authentication failed; check DEEPSEEK_API_KEY",
        ) from exc
    except LLMRateLimitError as exc:
        logger.warning("AI chat rate-limited: %s", exc)
        raise HTTPException(
            status_code=429,
            detail="LLM provider rate-limited; please retry shortly",
        ) from exc
    except (LLMUpstreamError, LLMTimeoutError) as exc:
        logger.error("AI chat upstream error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider unavailable: {exc.__class__.__name__}",
        ) from exc
    except LLMConfigError as exc:
        logger.error("AI chat config error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="LLM provider misconfigured",
        ) from exc
    except LLMProviderError as exc:
        # Catch-all for any future LLMProviderError subclass we
        # haven't explicitly mapped above.
        logger.exception("AI chat unexpected provider error")
        raise HTTPException(
            status_code=500,
            detail=f"LLM provider error: {exc.__class__.__name__}",
        ) from exc
