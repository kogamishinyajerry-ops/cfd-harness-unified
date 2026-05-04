"""Factory for the default LLM provider.

Reads ``DEEPSEEK_API_KEY`` from env. If set, returns the real
DeepSeekProvider; if unset, returns MockLLMProvider with a startup
warning so a misconfigured deployment doesn't silently serve mock
responses indefinitely.
"""
from __future__ import annotations

import logging
import os

from ui.backend.services.llm_provider.base import (
    LLMProvider,
    MockLLMProvider,
)
from ui.backend.services.llm_provider.deepseek import DeepSeekProvider

logger = logging.getLogger(__name__)

_API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"


def get_default_provider() -> LLMProvider:
    """Return the LLM provider configured for the current environment.

    Production: ``DEEPSEEK_API_KEY`` set → :class:`DeepSeekProvider`.
    Dev / CI:    ``DEEPSEEK_API_KEY`` unset → :class:`MockLLMProvider`.

    The mock-mode path logs a warning so the operator notices when
    they expected real calls. The frontend separately surfaces a
    "demo mode" banner via the ``model_used="mock"`` field on the
    response, so silent mock-in-prod is detectable from both sides.
    """
    api_key = os.environ.get(_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        logger.warning(
            "%s is unset — using MockLLMProvider. Real LLM calls disabled.",
            _API_KEY_ENV_VAR,
        )
        return MockLLMProvider()
    return DeepSeekProvider(api_key=api_key)
