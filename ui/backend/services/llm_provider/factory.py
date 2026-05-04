"""Factory for the default LLM provider.

Codex R1 P3 (V61-118): the factory returns a SINGLETON provider so
all requests share one long-lived ``httpx.AsyncClient`` (HTTP
keep-alive across chat turns, no per-request DNS+TLS handshake).
:func:`reset_default_provider` is exposed for test isolation; tests
that exercise the singleton lifecycle call it in a fixture.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading

from ui.backend.services.llm_provider.base import (
    LLMProvider,
    MockLLMProvider,
)
from ui.backend.services.llm_provider.deepseek import (
    MAX_CHAT_DURATION_SECONDS,
    DeepSeekProvider,
)

logger = logging.getLogger(__name__)

_API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"

# Cached singleton + a recording of WHICH key the cache was built
# for. If the key changes between calls (e.g. a test monkeypatches
# the env var without going through reset_default_provider), the
# cache is invalidated on the next call. This keeps tests robust
# without leaking long-lived clients across env-var flips.
_lock = threading.Lock()
_cached_provider: LLMProvider | None = None
_cached_key_fingerprint: str | None = None


def _fingerprint(api_key: str) -> str:
    """Stable but non-revealing tag of the active key. Codex R2 P2:
    a length-only fingerprint collides on same-length key rotations
    (DeepSeek keys are uniformly 35 chars, so two distinct keys would
    cache-hit). Use a SHA-256 of the key bytes — distinguishes any
    distinct keys; never reveals key contents in cache state.

    Returns ``"none"`` when no key is set, ``"sha256:<64hex>"`` when
    set. The fingerprint is held only in-process memory (cached for
    invalidation comparison) and never logged."""
    if not api_key:
        return "none"
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# Codex R4 P2 + R5 P1: closing an evicted provider EAGERLY tears the
# shared httpx.AsyncClient out from under any in-flight request that's
# still using the old singleton. Delay the close by enough time for
# the longest possible single ``chat()`` call to complete — that's a
# primary-model attempt that consumes its full read timeout, followed
# by an immediate fallback that consumes another full read timeout.
# Sourcing the bound from ``MAX_CHAT_DURATION_SECONDS`` (defined next
# to the timeout itself) means future timeout changes scale this
# automatically. The +30s buffer covers httpx connect/cleanup overhead
# and small async scheduling jitter. Sync test contexts with no running
# loop close immediately (no concurrent requests).
_EVICTED_PROVIDER_CLOSE_DELAY_SECONDS = MAX_CHAT_DURATION_SECONDS + 30.0


async def _delayed_aclose(provider: LLMProvider, delay: float) -> None:
    aclose = getattr(provider, "aclose", None)
    if aclose is None:
        return
    try:
        await asyncio.sleep(delay)
        await aclose()
    except Exception:
        logger.debug(
            "Best-effort delayed aclose of evicted provider failed", exc_info=True
        )


def _schedule_aclose(provider: LLMProvider) -> None:
    """Close an evicted provider's underlying client.

    Codex R3 P2-2: same-length key rotations trigger a cache rebuild;
    without explicit cleanup the old DeepSeekProvider's persistent
    AsyncClient leaked.

    Codex R4 P2: cleanup must wait for in-flight requests on the old
    singleton to finish before the AsyncClient is torn down. We
    schedule the close on the running event loop with a fixed delay
    that exceeds the per-request read timeout, so any chat that
    already grabbed a reference to the evicted provider has time to
    complete. Sync test paths close immediately (no concurrent
    requests in those scenarios).
    """
    aclose = getattr(provider, "aclose", None)
    if aclose is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        loop.create_task(
            _delayed_aclose(provider, _EVICTED_PROVIDER_CLOSE_DELAY_SECONDS)
        )
        return
    # No running loop — sync test/cleanup path. Close immediately;
    # callers in this scenario don't have concurrent in-flight uses
    # of the evicted provider.
    try:
        asyncio.run(aclose())
    except Exception:
        logger.debug("Best-effort aclose of evicted provider failed", exc_info=True)


def get_default_provider() -> LLMProvider:
    """Return the LLM provider configured for the current environment.

    Production: ``DEEPSEEK_API_KEY`` set → :class:`DeepSeekProvider`
    (singleton with long-lived AsyncClient).
    Dev / CI:    ``DEEPSEEK_API_KEY`` unset → :class:`MockLLMProvider`.

    The mock-mode path logs a warning the first time so the operator
    notices when they expected real calls. The frontend surfaces a
    "demo mode" banner via the ``model_used="mock"`` field so silent
    mock-in-prod is detectable from both sides.
    """
    global _cached_provider, _cached_key_fingerprint

    api_key = os.environ.get(_API_KEY_ENV_VAR, "").strip()
    fingerprint = _fingerprint(api_key)

    evicted: LLMProvider | None = None
    with _lock:
        if (
            _cached_provider is not None
            and _cached_key_fingerprint == fingerprint
        ):
            return _cached_provider
        # Env changed (or first call) — rebuild. Hold the previously
        # cached provider for cleanup AFTER releasing the lock so we
        # don't run async work under it.
        evicted = _cached_provider
        if not api_key:
            logger.warning(
                "%s is unset — using MockLLMProvider. Real LLM calls disabled.",
                _API_KEY_ENV_VAR,
            )
            _cached_provider = MockLLMProvider()
        else:
            _cached_provider = DeepSeekProvider(api_key=api_key)
        _cached_key_fingerprint = fingerprint
        result = _cached_provider

    if evicted is not None:
        _schedule_aclose(evicted)
    return result


def reset_default_provider() -> None:
    """Clear the singleton cache. Used by FastAPI lifespan-shutdown
    to release the persistent AsyncClient cleanly, and by tests that
    flip ``DEEPSEEK_API_KEY`` and need a fresh provider per case.

    Note: this does NOT call ``aclose()`` on the cached provider —
    the caller is responsible for that if needed (the FastAPI
    lifespan-shutdown calls ``aclose()`` then ``reset_default_provider()``).
    """
    global _cached_provider, _cached_key_fingerprint
    with _lock:
        _cached_provider = None
        _cached_key_fingerprint = None
