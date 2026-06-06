"""DEC-V61-231 · machine-checked invariant: POST /ai-review invokes ZERO LLM.

`ui.backend.routes.ai_review._try_llm_enhance` late-imports `get_default_provider`
*only* as an importability probe — the presence of an importable provider is recorded
as the "enhancement" signal, but the provider is NEVER instantiated or called on this
route (real LLM grounding is fanned out to /ai-chat and /cases/{id}/ai-review, which
carry their own loopback + auth gating). This keeps the 4-question advisory-only gate
honest: the advisor-stack base report is the whole payload; the LLM adds nothing on POST.

Until now that invariant lived only in a source comment (ai_review.py:686-692). This test
makes it MACHINE-CHECKED — a future edit that actually calls the provider here turns RED.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import ui.backend.services.llm_provider as llm_pkg
from ui.backend.routes import ai_review as ai_review_route


def test_try_llm_enhance_imports_but_never_invokes_provider(monkeypatch):
    """_try_llm_enhance may IMPORT get_default_provider but must NOT call it, nor invoke
    chat/review on any provider. Pins 'zero LLM call on POST /ai-review' (DEC-V61-231)."""
    factory_calls = {"n": 0}
    sentinel_provider = MagicMock(name="provider")

    def _tracking_factory():
        factory_calls["n"] += 1
        return sentinel_provider

    # `from ui.backend.services.llm_provider import get_default_provider` resolves via
    # getattr on the package, so patching the package attr intercepts the late import.
    monkeypatch.setattr(llm_pkg, "get_default_provider", _tracking_factory, raising=False)

    ok, elapsed_ms = ai_review_route._try_llm_enhance({"verdict": "PASS", "advisors": []})

    # Provider is importable → enhancement signal True, but the factory is the import-only
    # probe and must NEVER be called (the invariant).
    assert ok is True
    assert factory_calls["n"] == 0, (
        "POST /ai-review invoked the LLM provider factory — violates the 4Q "
        "advisory-only zero-LLM-call invariant (DEC-V61-231)."
    )
    sentinel_provider.chat.assert_not_called()
    sentinel_provider.review.assert_not_called()
    assert isinstance(elapsed_ms, float)


def test_try_llm_enhance_degrades_to_false_when_provider_unimportable(monkeypatch):
    """If the provider package is not importable, the route still returns a complete base
    report (llm_enhanced=False) — the LLM is a pure addendum, never load-bearing."""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "ui.backend.services.llm_provider" or name.startswith(
            "ui.backend.services.llm_provider"
        ):
            raise ImportError("simulated: provider unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    ok, elapsed_ms = ai_review_route._try_llm_enhance({"verdict": "PASS"})

    assert ok is False  # graceful degrade, no crash
    assert isinstance(elapsed_ms, float)
