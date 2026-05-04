"""Shared loopback-only guard helpers (DEC-V61-118 + V61-119).

Extracted from ``routes/ai_chat.py`` so the V61-119 ``ai_coach``
streaming route can reuse the exact same guard semantics without
copy-paste. ``ai_chat.py`` was the original site (Codex R1-R4 chain
hardened it: proxy-header detection, full chain logging, override
env-var). Behavior is preserved verbatim.

The module exposes:
  * :data:`LOOPBACK_HOSTS` — IPv4/IPv6/socket fixture set
  * :data:`PROXY_FORWARDED_HEADERS` — header names that signal a proxy
  * :data:`NON_LOOPBACK_OVERRIDE_ENV` — env-var name for the bypass
  * :func:`is_loopback_request`
  * :func:`non_loopback_override_enabled`
  * :func:`client_label_for_log`
  * :func:`require_loopback` — raises HTTPException(403) on rejection
"""
from __future__ import annotations

import logging
import os

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# Loopback addresses accepted by the V1 route guard. IPv4 + IPv6 +
# Unix-socket clients (FastAPI/uvicorn surfaces ``None`` for socket-
# transport callers in some versions, treat that as loopback too).
# ``"testclient"`` is what fastapi.testclient.TestClient sets as
# client.host for in-process integration tests — by definition not
# a real network caller.
LOOPBACK_HOSTS = frozenset(
    {"127.0.0.1", "::1", "localhost", "testclient", None, ""}
)

# Codex R2 P1: a same-host reverse proxy presents
# ``client.host = 127.0.0.1`` even when the real caller is remote, so
# a peer-only loopback check is not sufficient. Presence of any of
# these forwarded headers signals a proxy chain — refuse to treat
# that request as loopback unless the operator has explicitly opted
# in via env.
PROXY_FORWARDED_HEADERS: tuple[str, ...] = (
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
    "forwarded",
)

NON_LOOPBACK_OVERRIDE_ENV = "AI_CHAT_ALLOW_NON_LOOPBACK"


def _request_has_proxy_headers(request: Request) -> bool:
    return any(h in request.headers for h in PROXY_FORWARDED_HEADERS)


def is_loopback_request(request: Request) -> bool:
    """True iff the request originated from a loopback peer AND no
    proxy-forwarded headers are present."""
    client = request.client
    if client is None:
        # No client info (testclient + some uvicorn modes). Only
        # treat as loopback when there are also no proxy-forwarded
        # headers; otherwise something is in front of us.
        return not _request_has_proxy_headers(request)
    if client.host not in LOOPBACK_HOSTS:
        return False
    # Peer is loopback BUT it could be a same-host reverse proxy.
    # Codex R2 P1: any forwarded header → assume proxy → not loopback.
    return not _request_has_proxy_headers(request)


def non_loopback_override_enabled() -> bool:
    """True iff the operator set ``AI_CHAT_ALLOW_NON_LOOPBACK=1``."""
    return os.environ.get(NON_LOOPBACK_OVERRIDE_ENV, "").strip() == "1"


def client_label_for_log(request: Request) -> str:
    """Build an audit-friendly identifier for the request's caller.

    Codex R3 P2-1: when a same-host reverse proxy trips the guard,
    ``request.client.host`` is the loopback proxy peer, not the real
    remote caller. The warning/info logs need the proxy-forwarded
    headers so operators can track who actually hit the endpoint.

    Codex R4 P1: do NOT pick a single forwarded hop as "the caller" —
    XFF is fully client-controlled and the leftmost entry can be
    spoofed, so an honest audit log records the entire chain
    verbatim. Operators interpret using their own knowledge of how
    many trusted proxies sit in front of the app.
    """
    parts: list[str] = []
    immediate_peer = request.client.host if request.client else "unknown"
    parts.append(f"peer={immediate_peer}")
    if xff := request.headers.get("x-forwarded-for"):
        parts.append(f"x-forwarded-for={xff!r}")
    if real_ip := request.headers.get("x-real-ip"):
        parts.append(f"x-real-ip={real_ip!r}")
    if forwarded := request.headers.get("forwarded"):
        parts.append(f"forwarded={forwarded!r}")
    return " ".join(parts)


def require_loopback(request: Request, *, route_label: str) -> None:
    """Raise HTTPException(403) when the request is non-loopback and
    no override is set. Logs the audit trail in either branch (reject
    or override-allow) so operators always know who hit the endpoint.

    ``route_label`` is the public path (e.g. ``/api/ai-chat``,
    ``/api/ai-coach/stream``) used in the rejection message and audit
    log; keeps the helper agnostic to the specific route.
    """
    if not is_loopback_request(request) and not non_loopback_override_enabled():
        logger.warning(
            "Rejecting %s from non-loopback host %s (set %s=1 to allow)",
            route_label,
            client_label_for_log(request),
            NON_LOOPBACK_OVERRIDE_ENV,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                f"{route_label} is restricted to loopback callers; "
                f"set {NON_LOOPBACK_OVERRIDE_ENV}=1 to allow remote access "
                "(only with a trusted reverse proxy + auth in front)."
            ),
        )
    if not is_loopback_request(request):
        # Override active — log so the audit trail records the
        # remote caller; do NOT log the request body.
        logger.info(
            "Allowing %s from non-loopback host %s (override env=%s)",
            route_label,
            client_label_for_log(request),
            NON_LOOPBACK_OVERRIDE_ENV,
        )
