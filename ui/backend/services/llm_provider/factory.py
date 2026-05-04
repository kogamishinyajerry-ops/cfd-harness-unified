"""Factory for the default LLM provider.

Codex R1 P3 (V61-118): the factory returns a SINGLETON provider so
all requests share one long-lived ``httpx.AsyncClient`` (HTTP
keep-alive across chat turns, no per-request DNS+TLS handshake).
:func:`reset_default_provider` is exposed for test isolation; tests
that exercise the singleton lifecycle call it in a fixture.
"""
from __future__ import annotations

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

# Cached singleton + a recording of WHICH key the cache was built
# for. If the key changes between calls (e.g. a test monkeypatches
# the env var without going through reset_default_provider), the
# cache is invalidated on the next call. This keeps tests robust
# without leaking long-lived clients across env-var flips.
_lock = threading.Lock()
_cached_provider: LLMProvider | None = None
_cached_key_fingerprint: str | None = None


def _fingerprint(api_key: str) -> str:
    """Stable but non-revealing tag of the active key. ``"none"`` for
    an absent key; ``"set:N"`` where N is the key length for a
    present one. Never includes any key bytes."""
    if not api_key:
        return "none"
    return f"set:{len(api_key)}"


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

    with _lock:
        if (
            _cached_provider is not None
            and _cached_key_fingerprint == fingerprint
        ):
            return _cached_provider
        # Env changed (or first call) — rebuild.
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
