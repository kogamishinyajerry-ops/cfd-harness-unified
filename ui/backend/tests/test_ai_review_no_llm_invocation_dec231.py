"""DEC-V61-231 · machine-checked invariant: POST /ai-review invokes ZERO LLM.

`ui.backend.routes.ai_review._try_llm_enhance` late-imports `get_default_provider`
*only* as an importability probe — the presence of an importable provider is recorded
as the "enhancement" signal, but the provider is NEVER instantiated or called on this
route (real LLM grounding is fanned out to /ai-chat and /cases/{id}/ai-review, which
carry their own loopback + auth gating). This keeps the 4-question advisory-only gate
honest: the advisor-stack base report is the whole payload; the LLM adds nothing on POST.

Until now that invariant lived only in a source comment (ai_review.py:686-692). This module
makes it MACHINE-CHECKED two complementary ways:
  - a BEHAVIORAL guard (patch the provider factory, assert call_count==0);
  - a STATIC import-path-robust tripwire (`_provider_invocations`) that is itself
    proven non-hollow by `test_tripwire_is_not_hollow_*` (Codex R0→R2 hardening).
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from unittest.mock import MagicMock

import ui.backend.services.llm_provider as llm_pkg
from ui.backend.routes import ai_review as ai_review_route


# --------------------------------------------------------------------------- #
# Static detector — import-path-robust (Codex R0 ISSUE-3 + R1/R2 alias gaps).
# --------------------------------------------------------------------------- #
def _provider_invocations(source: str) -> list[str]:
    """Return the provider-invocation sites in `source` (AST, no execution).

    Robust against import aliasing AND AST-visible assignment rebinding:
      1. resolve local bindings of `get_default_provider` from import statements
         (honouring `as` aliases) + `llm_provider` package aliases;
      2. follow assignment rebindings (`f = gdp` / `f = p.get_default_provider`) to a
         FIXPOINT so a 1+-hop alias cannot launder the call;
      3. flag any call to a bound factory name + any `.chat/.review/.complete(...)` etc.
    Out of scope (NOT AST-visible): dynamic getattr/eval dispatch — guarded behaviorally.
    """
    tree = ast.parse(textwrap.dedent(source))
    factory_aliases: set[str] = {"get_default_provider"}
    package_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name == "get_default_provider":
                    factory_aliases.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if "llm_provider" in a.name:
                    package_aliases.add(a.asname or a.name.split(".")[0])

    changed = True
    while changed:  # fixpoint over assignment rebindings
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            v = node.value
            is_provider_expr = (
                (isinstance(v, ast.Name) and v.id in factory_aliases)
                or (isinstance(v, ast.Attribute) and v.attr == "get_default_provider")
            )
            if not is_provider_expr:
                continue
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id not in factory_aliases:
                    factory_aliases.add(tgt.id)
                    changed = True

    invoke_attrs = {"get_default_provider", "chat", "review", "complete", "acomplete", "generate"}
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id in factory_aliases:
            hits.append(f"{fn.id}()")
        elif isinstance(fn, ast.Attribute) and fn.attr in invoke_attrs:
            hits.append(f"...{fn.attr}()")
    return hits


# --------------------------------------------------------------------------- #
# The invariant on the REAL route function.
# --------------------------------------------------------------------------- #
def test_try_llm_enhance_imports_but_never_invokes_provider(monkeypatch):
    """BEHAVIORAL: _try_llm_enhance may IMPORT get_default_provider but must NOT call it,
    nor invoke chat/review on any provider. Pins 'zero LLM call on POST /ai-review'."""
    factory_calls = {"n": 0}
    sentinel_provider = MagicMock(name="provider")

    def _tracking_factory():
        factory_calls["n"] += 1
        return sentinel_provider

    monkeypatch.setattr(llm_pkg, "get_default_provider", _tracking_factory, raising=False)

    ok, elapsed_ms = ai_review_route._try_llm_enhance({"verdict": "PASS", "advisors": []})

    assert ok is True
    assert factory_calls["n"] == 0, (
        "POST /ai-review invoked the LLM provider factory — violates the 4Q "
        "advisory-only zero-LLM-call invariant (DEC-V61-231)."
    )
    sentinel_provider.chat.assert_not_called()
    sentinel_provider.review.assert_not_called()
    assert isinstance(elapsed_ms, float)


def test_try_llm_enhance_degrades_to_false_when_provider_unimportable(monkeypatch):
    """BEHAVIORAL: if the provider package is not importable, the route still returns a
    complete base report (llm_enhanced=False) — the LLM is a pure addendum, never load-bearing."""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name.startswith("ui.backend.services.llm_provider"):
            raise ImportError("simulated: provider unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    ok, elapsed_ms = ai_review_route._try_llm_enhance({"verdict": "PASS"})

    assert ok is False
    assert isinstance(elapsed_ms, float)


def test_try_llm_enhance_static_tripwire_finds_no_invocation():
    """STATIC: the real _try_llm_enhance body contains ZERO provider invocation."""
    assert _provider_invocations(inspect.getsource(ai_review_route._try_llm_enhance)) == []


# --------------------------------------------------------------------------- #
# Prove the tripwire is NOT hollow (Codex R0→R2): it must flag every AST-visible bypass.
# --------------------------------------------------------------------------- #
def test_tripwire_is_not_hollow_catches_all_ast_visible_bypasses():
    bypasses = {
        "direct": "def f():\n from x.llm_provider import get_default_provider\n get_default_provider()\n",
        "pkg-attr": "def f():\n import x.llm_provider as p\n p.get_default_provider()\n",
        "import-alias": "def f():\n from x.llm_provider import get_default_provider as gdp\n gdp()\n",
        "assign-1hop": "def f():\n from x.llm_provider import get_default_provider as gdp\n g = gdp\n g()\n",
        "assign-2hop": "def f():\n from x.llm_provider import get_default_provider as gdp\n g = gdp\n h = g\n h()\n",
        "chat-call": "def f():\n prov = make()\n prov.chat('x')\n",
    }
    for label, src in bypasses.items():
        assert _provider_invocations(src), f"tripwire MISSED an AST-visible bypass: {label}"
    # control: the real import-only probe pattern must NOT be flagged (non-trivial test).
    clean = "def f():\n from x.llm_provider import get_default_provider  # probe only\n return True\n"
    assert _provider_invocations(clean) == []
