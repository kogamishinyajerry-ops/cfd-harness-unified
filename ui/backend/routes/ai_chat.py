"""AI chat endpoint (DEC-V61-118 V1).

POST /api/ai-chat — non-streaming chat with the configured LLM provider.
V1 ships the foundation; V61-119 layers SSE streaming + governance
context onto a distinct ``/api/ai-coach/stream`` route.

Provider is resolved per-request via the factory so tests can monkey-
patch ``get_default_provider`` to inject a mock.

Security (Codex R1 P1): the route is GUARDED to loopback-only callers.
DeepSeek calls spend the server's API key, so an accidentally-exposed
deployment must NOT serve as an open relay. The guard rejects any
remote address outside ``127.0.0.1`` / ``::1`` / ``localhost`` with
HTTP 403. The guard helper lives in :mod:`._loopback_guard` (extracted
in V61-119 so the new ``ai_coach`` route can reuse the exact same
semantics — no copy-paste).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from ui.backend.routes._loopback_guard import require_loopback
from ui.backend.services.llm_provider import (
    ChatRequest,
    ChatResponse,
    LLMAuthError,
    LLMBadRequestError,
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
async def ai_chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Execute a chat completion against the configured LLM provider.

    Status code mapping:
      * 200 — success
      * 400 — caller's request rejected by upstream (oversized,
              invalid format, etc — fix the request and retry)
      * 401 — upstream auth failure (bad/missing API key)
      * 403 — non-loopback caller without explicit override
      * 429 — upstream rate-limit (exhausted including fallback)
      * 502 — upstream timeout / 5xx / malformed response
      * 500 — provider misconfiguration / unexpected
    """
    require_loopback(http_request, route_label="/api/ai-chat")

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
    except LLMBadRequestError as exc:
        # Codex R1 P2: the upstream rejected the request (oversized,
        # malformed, etc). The CALLER must fix it; retrying with a
        # fallback model would just produce the same 4xx.
        logger.warning("AI chat bad request: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=(
                "LLM provider rejected the request "
                "(likely oversized or malformed payload); adjust and retry"
            ),
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
