"""AI chat endpoint (DEC-V61-118 V1).

POST /api/ai-chat — non-streaming chat with the configured LLM provider.
V1 ships the foundation; V61-119 will add SSE streaming + tool calling
+ governance-aware system prompt composition.

Provider is resolved per-request via the factory so tests can monkey-
patch ``get_default_provider`` to inject a mock.

Security (Codex R1 P1): the route is GUARDED to loopback-only callers.
DeepSeek calls spend the server's API key, so an accidentally-exposed
deployment must NOT serve as an open relay. The guard rejects any
remote address outside ``127.0.0.1`` / ``::1`` / ``localhost`` with
HTTP 403. Operators who genuinely want to expose the route (e.g. a
trusted reverse proxy with its own auth in front) can set
``AI_CHAT_ALLOW_NON_LOOPBACK=1`` to bypass; the route logs the decision
so the override is auditable.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request

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

# Loopback addresses accepted by the V1 route guard. IPv4 + IPv6 +
# Unix-socket clients (FastAPI/uvicorn surfaces ``None`` for socket-
# transport callers in some versions, treat that as loopback too).
# ``"testclient"`` is what fastapi.testclient.TestClient sets as
# client.host for in-process integration tests — by definition not
# a real network caller.
_LOOPBACK_HOSTS = frozenset(
    {"127.0.0.1", "::1", "localhost", "testclient", None, ""}
)

# Codex R2 P1: a same-host reverse proxy presents ``client.host =
# 127.0.0.1`` even when the real caller is remote, so a peer-only
# loopback check is not sufficient. Presence of any of these forwarded
# headers signals a proxy chain — refuse to treat that request as
# loopback unless the operator has explicitly opted in via env.
_PROXY_FORWARDED_HEADERS = (
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
    "forwarded",
)

_NON_LOOPBACK_OVERRIDE_ENV = "AI_CHAT_ALLOW_NON_LOOPBACK"


def _request_has_proxy_headers(request: Request) -> bool:
    return any(h in request.headers for h in _PROXY_FORWARDED_HEADERS)


def _is_loopback_request(request: Request) -> bool:
    client = request.client
    if client is None:
        # No client info (testclient + some uvicorn modes). Only
        # treat as loopback when there are also no proxy-forwarded
        # headers; otherwise something is in front of us.
        return not _request_has_proxy_headers(request)
    if client.host not in _LOOPBACK_HOSTS:
        return False
    # Peer is loopback BUT it could be a same-host reverse proxy.
    # Codex R2 P1: any forwarded header → assume proxy → not loopback.
    return not _request_has_proxy_headers(request)


def _non_loopback_override_enabled() -> bool:
    return os.environ.get(_NON_LOOPBACK_OVERRIDE_ENV, "").strip() == "1"


def _client_label_for_log(request: Request) -> str:
    """Build an audit-friendly identifier for the request's caller.

    Codex R3 P2-1: when a same-host reverse proxy trips the guard,
    ``request.client.host`` is the loopback proxy peer, not the real
    remote caller. The warning/info logs need the X-Forwarded-For /
    X-Real-IP / Forwarded value so operators can track who actually
    hit the endpoint. We surface the forwarded address along with
    the immediate peer so the audit trail records both hops.
    """
    immediate_peer = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # XFF format is "client, proxy1, proxy2" — first hop is the
        # original caller per RFC convention.
        original = forwarded_for.split(",")[0].strip()
        if original:
            return f"{original} (via peer={immediate_peer})"
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return f"{real_ip.strip()} (via peer={immediate_peer})"
    forwarded = request.headers.get("forwarded")
    if forwarded:
        return f"{forwarded} (via peer={immediate_peer})"
    return immediate_peer


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
    if not _is_loopback_request(http_request) and not _non_loopback_override_enabled():
        # R3 P2-1: log the forwarded caller (XFF / Forwarded / X-Real-IP)
        # not just the loopback proxy peer, so audits can track who
        # actually hit the endpoint.
        logger.warning(
            "Rejecting /api/ai-chat from non-loopback host %s (set %s=1 to allow)",
            _client_label_for_log(http_request),
            _NON_LOOPBACK_OVERRIDE_ENV,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                "/api/ai-chat is restricted to loopback callers; "
                f"set {_NON_LOOPBACK_OVERRIDE_ENV}=1 to allow remote access "
                "(only with a trusted reverse proxy + auth in front)."
            ),
        )
    if not _is_loopback_request(http_request):
        # Override active — log so the audit trail records the
        # remote caller; do NOT log the request body (could include
        # sensitive prompts).
        logger.info(
            "Allowing /api/ai-chat from non-loopback host %s (override env=%s)",
            _client_label_for_log(http_request),
            _NON_LOOPBACK_OVERRIDE_ENV,
        )

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
