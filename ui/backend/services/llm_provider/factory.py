"""Factory for the default LLM provider.

The factory caches a singleton provider so all requests share one
long-lived ``httpx.AsyncClient`` (HTTP keep-alive across chat turns,
no per-request DNS+TLS handshake; Codex V61-118 R1 P3).

Cleanup contract (V1 scope, post-R7):
  * The active singleton is closed by the FastAPI ``lifespan``
    shutdown hook — call :func:`get_default_provider` once during
    startup, then ``await provider.aclose()`` during shutdown.
  * In-process key rotation is NOT a supported workflow; rotating
    ``DEEPSEEK_API_KEY`` requires restarting the process for clean
    teardown of the previous provider's underlying client. The
    factory invalidates the cache on key changes so subsequent
    requests use the NEW key, but the displaced provider is left
    for GC. See DEC-V61-118 §risk register R5 for the rationale —
    earlier drain-based and time-delayed eviction designs exposed
    cross-loop race surfaces (Codex R3-R7) that exceeded V1 scope.

:func:`reset_default_provider` is exposed for tests that flip the
key env-var between cases. It does NOT close the previously cached
provider — tests that need a clean teardown ``await provider.aclose()``
explicitly.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading

from ui.backend.services.llm_provider.base import (
    LLMProvider,
    MockLLMProvider,
)
from ui.backend.services.llm_provider.deepseek import DeepSeekProvider

logger = logging.getLogger(__name__)

_API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"

# Cached singleton + a fingerprint of the active key. The fingerprint
# is a SHA-256 hash so distinct keys with the same length still
# invalidate the cache (Codex R2 P2). Held only in-process memory;
# never logged.
_lock = threading.Lock()
_cached_provider: LLMProvider | None = None
_cached_key_fingerprint: str | None = None


def _fingerprint(api_key: str) -> str:
    """Stable but non-revealing tag of the active key.

    Returns ``"none"`` when no key is set, ``"sha256:<64hex>"`` when
    set. The fingerprint is held only in-process memory (cached for
    invalidation comparison) and never logged.
    """
    if not api_key:
        return "none"
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def get_default_provider() -> LLMProvider:
    """Return the LLM provider configured for the current environment.

    Production: ``DEEPSEEK_API_KEY`` set → :class:`DeepSeekProvider`
    (singleton with long-lived AsyncClient).
    Dev / CI:    ``DEEPSEEK_API_KEY`` unset → :class:`MockLLMProvider`.

    The mock-mode path logs a warning so the operator notices when
    they expected real calls. The frontend surfaces a "demo mode"
    banner via the ``model_used="mock"`` field on every response so
    silent mock-in-prod is detectable from both sides.
    """
    global _cached_provider, _cached_key_fingerprint

    api_key = os.environ.get(_API_KEY_ENV_VAR, "").strip()
    fingerprint = _fingerprint(api_key)

    with _lock:
        if (
            _cached_provider is not None
            and _cached_key_fingerprint == fingerprint
        ):
            return _cached_provider
        # Env changed (or first call) — rebuild. The previous cached
        # provider (if any) is dropped from the cache here; explicit
        # close is the caller's job (lifespan-shutdown closes the
        # final active singleton; in-process rotation is not supported
        # per V1 scope — see module docstring).
        if not api_key:
            logger.warning(
                "%s is unset — using MockLLMProvider. Real LLM calls disabled.",
                _API_KEY_ENV_VAR,
            )
            _cached_provider = MockLLMProvider()
        else:
            _cached_provider = DeepSeekProvider(api_key=api_key)
        _cached_key_fingerprint = fingerprint
        return _cached_provider


def reset_default_provider() -> None:
    """Clear the singleton cache. Used by tests that flip
    ``DEEPSEEK_API_KEY`` and need a fresh provider per case.

    Does NOT call ``aclose()`` on the cached provider — tests that
    need a clean teardown ``await provider.aclose()`` explicitly
    against the reference they kept. Production lifecycle goes through
    :func:`close_cached_provider` from the FastAPI ``lifespan`` hook.
    """
    global _cached_provider, _cached_key_fingerprint
    with _lock:
        _cached_provider = None
        _cached_key_fingerprint = None


async def close_cached_provider() -> None:
    """Close the active singleton (if any) and clear the cache.

    Wired into the FastAPI ``lifespan`` shutdown handler in
    :mod:`ui.backend.main` so the long-lived ``httpx.AsyncClient``
    held by :class:`DeepSeekProvider` is torn down cleanly when the
    server stops accepting new requests. Idempotent: safe to call
    even if no provider has been built yet.

    Calling this during normal app lifecycle does NOT affect a
    process that's still serving traffic — by the time uvicorn fires
    the lifespan-shutdown, no new ``/api/ai-chat`` requests will
    arrive, so there is no race surface. Codex R3-R7 chain
    deliberately scoped the cleanup to this single call site
    (DEC-V61-118 §risk register R6).
    """
    global _cached_provider, _cached_key_fingerprint
    with _lock:
        provider = _cached_provider
        _cached_provider = None
        _cached_key_fingerprint = None
    if provider is None:
        return
    aclose = getattr(provider, "aclose", None)
    if aclose is None:
        return
    try:
        await aclose()
    except Exception:
        logger.exception("aclose of cached LLM provider failed")
