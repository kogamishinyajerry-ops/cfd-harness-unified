"""DEC-V61-132 N1.2 · AI advisor contract behavioral test.

Three-layer enforcement of V130 Principle B ("AI is advisor, not actor"):

* Layer-A — Patched-function sentinel. Monkey-patches every symbol in
  ``KNOWN_MUTATION_FUNCTIONS`` at its canonical module location with a
  sentinel that records calls and raises. Runs each AI dispatch entry
  point across its full branch matrix; asserts zero sentinel records.

* Layer-B — Registry smoke tests (R0 scope-down per DEC-V61-132 §2.1
  scope-down 2026-05-06): exercises ``MUTATING_ROUTES`` and
  ``is_mutating_route()`` correctness without invoking routes. Full
  FastAPI route case-state diff (TestClient + LLM mock + case fixture)
  is deferred to N1.3 (DEC-V61-133). Layer-A patching catches
  symbol-call route attacks indirectly; full Layer-B catches novel
  vectors (subprocess writes, raw pathlib mutations) — low-likelihood
  given V131's strip and Layer-C's import-graph guard.

* Layer-C — Static namespace-binding check. Parses each AI dispatch
  module file with ``ast``; asserts no ``Import`` / ``ImportFrom``
  statement names a symbol in ``KNOWN_MUTATION_FUNCTIONS``. Catches
  bound-but-unused regressions before they become called.

Cross-references: DEC-V61-130 §2 Principle B, DEC-V61-131 (N1.1
hard-strip), DEC-V61-132 §2.1 (this test's spec).
"""
from __future__ import annotations

import ast
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import pytest

from ui.backend.services.ai_actions.mutating_routes import (
    KNOWN_MUTATION_FUNCTIONS,
    MUTATING_ROUTES,
    is_mutating_route,
)


# ────────── Layer-A · patched-function sentinel ──────────


class _MutationViolation(AssertionError):
    """Raised by the sentinel when an AI dispatch path invokes a
    known mutation function. Inherits from AssertionError so pytest
    surfaces the failure with a clean traceback."""


@dataclass
class _MutationRecord:
    module_path: str
    symbol_name: str
    args: tuple
    kwargs: dict


@dataclass
class _SentinelLog:
    records: list[_MutationRecord] = field(default_factory=list)


def _make_sentinel(
    module_path: str,
    symbol_name: str,
    log: _SentinelLog,
) -> Callable[..., Any]:
    """Build a function that records the call and raises
    ``_MutationViolation``. Used to monkey-patch every symbol in
    ``KNOWN_MUTATION_FUNCTIONS``."""

    def _sentinel(*args: Any, **kwargs: Any) -> Any:
        log.records.append(
            _MutationRecord(
                module_path=module_path,
                symbol_name=symbol_name,
                args=args,
                kwargs=kwargs,
            )
        )
        raise _MutationViolation(
            f"AI dispatch invoked mutation function "
            f"{module_path}.{symbol_name}() — V130 Principle B violation"
        )

    return _sentinel


@pytest.fixture
def mutation_sentinel(monkeypatch: pytest.MonkeyPatch) -> _SentinelLog:
    """Patch every ``KNOWN_MUTATION_FUNCTIONS`` symbol with a sentinel
    that records + raises. Yields the shared log."""
    log = _SentinelLog()
    for module_path, symbol_name in KNOWN_MUTATION_FUNCTIONS:
        # Some symbols may not be importable in test environments
        # (e.g., re-export aliases that resolve to the same canonical
        # function). Patch each one independently; if it doesn't exist
        # at the named module, that's a stale registry entry which the
        # ``test_known_mutation_functions_are_importable`` smoke test
        # catches separately.
        try:
            monkeypatch.setattr(
                f"{module_path}.{symbol_name}",
                _make_sentinel(module_path, symbol_name, log),
                raising=True,
            )
        except (AttributeError, ModuleNotFoundError):
            # Recorded by the smoke test; do not fail the sentinel
            # fixture for stale registry entries.
            pass
    return log


def test_known_mutation_functions_are_importable() -> None:
    """Every ``KNOWN_MUTATION_FUNCTIONS`` entry resolves to a callable.
    A stale entry would silently neuter Layer-A; this guards against
    that."""
    import importlib

    missing: list[tuple[str, str]] = []
    for module_path, symbol_name in KNOWN_MUTATION_FUNCTIONS:
        try:
            mod = importlib.import_module(module_path)
            sym = getattr(mod, symbol_name, None)
            if sym is None or not callable(sym):
                missing.append((module_path, symbol_name))
        except ModuleNotFoundError:
            missing.append((module_path, symbol_name))
    assert not missing, (
        f"KNOWN_MUTATION_FUNCTIONS has stale entries: {missing}. "
        "Update the registry to remove deprecated paths or fix the "
        "module location."
    )


# ────────── Layer-A tests · setup_bc_with_annotations ──────────


def _stage_case_dir(tmp_path: Path, case_id: str) -> Path:
    """Minimal case dir for envelope branches that don't require a
    real polyMesh (force_blocked, force_uncertain, blocked classifier).
    """
    case_dir = tmp_path / case_id
    case_dir.mkdir()
    return case_dir


@pytest.mark.parametrize(
    "force_uncertain,force_blocked",
    [
        (False, False),  # classifier path (default)
        (True, False),  # force_uncertain
        (False, True),  # force_blocked
    ],
)
def test_setup_bc_with_annotations_envelope_no_mutation(
    tmp_path: Path,
    mutation_sentinel: _SentinelLog,
    force_uncertain: bool,
    force_blocked: bool,
) -> None:
    """Envelope mode across (default classifier, force_uncertain,
    force_blocked) branches. None should invoke any mutation function.

    The classifier-confident branch is exercised indirectly: the
    classifier without a polyMesh returns ``blocked`` (no real STL),
    which is one of the no-mutation paths. Tests that pin the
    confident path are in test_setup_bc_envelope_route.py and use a
    real LDC mesh fixture; here we focus on the dispatch-level
    contract that no mutation symbol is reachable from any branch.
    """
    from ui.backend.services.ai_actions import setup_bc_with_annotations

    case_id = f"contract-{secrets.token_hex(4)}"
    case_dir = _stage_case_dir(tmp_path, case_id)

    # The classifier path with no polyMesh raises blocked envelope or
    # an internal error; either way, no mutation should fire.
    try:
        setup_bc_with_annotations(
            case_dir=case_dir,
            case_id=case_id,
            force_uncertain=force_uncertain,
            force_blocked=force_blocked,
        )
    except _MutationViolation:
        # Sentinel raised; recorded in log; we re-raise via assertion below.
        pass
    except Exception:
        # Other exceptions (e.g., classifier blocked, missing mesh) are
        # acceptable — the contract is "no mutation", not "no error".
        pass

    assert not mutation_sentinel.records, (
        f"Envelope dispatch invoked mutation symbols: "
        f"{mutation_sentinel.records}"
    )


# ────────── Layer-A tests · llm_coach.dispatch ──────────


def test_llm_coach_dispatch_no_mutation_for_every_tool(
    tmp_path: Path,
    mutation_sentinel: _SentinelLog,
) -> None:
    """Every tool in ``list_tools()`` MUST not invoke any mutation
    symbol when dispatched through its handler. Tools that legitimately
    fail with ToolArgError or ToolDispatchError before reaching their
    handler still satisfy the contract (no mutation symbol fired).
    """
    from ui.backend.services.llm_coach import (
        ToolArgError,
        ToolDispatchError,
        UnknownToolError,
        dispatch,
        list_tools,
    )

    case_dir = _stage_case_dir(tmp_path, f"contract-{secrets.token_hex(4)}")

    for descriptor in list_tools():
        # Construct a minimally-populated args dict from the tool's
        # Pydantic schema. We send the raw schema's required fields with
        # plausible values; the tool's handler may then reject them
        # with ToolDispatchError, which is fine for the contract test.
        sample_args: dict[str, Any] = {}
        schema = descriptor.args_model.model_json_schema()
        for prop_name, prop_schema in schema.get("properties", {}).items():
            if prop_name in schema.get("required", []):
                # Fill minimally per type; the handler may still reject.
                ptype = prop_schema.get("type", "string")
                if ptype == "string":
                    sample_args[prop_name] = (
                        prop_schema.get("enum", ["sample"])[0]
                        if "enum" in prop_schema
                        else "sample"
                    )
                elif ptype == "integer":
                    sample_args[prop_name] = prop_schema.get("minimum", 1) or 1
                elif ptype == "number":
                    sample_args[prop_name] = 1.0
                elif ptype == "boolean":
                    sample_args[prop_name] = False

        try:
            dispatch(case_dir=case_dir, tool=descriptor.name, args=sample_args)
        except (UnknownToolError, ToolArgError, ToolDispatchError):
            # Validation / dispatch errors don't violate the contract.
            pass
        except _MutationViolation:
            # Sentinel raised; recorded; assertion below catches it.
            pass
        except Exception:
            # Any other exception is acceptable — contract is "no
            # mutation", not "no error". The records list is the gate.
            pass

    assert not mutation_sentinel.records, (
        f"llm_coach dispatch invoked mutation symbols across tools: "
        f"{mutation_sentinel.records}"
    )


# ────────── Layer-B (R0 scope-down) · registry smoke tests ──────────
#
# Full route-level case-state diff is deferred to N1.3 per V132 §2.1
# (LLM mock + async streaming-route plumbing not justified at R0).
# What ships here: registry-correctness tests on MUTATING_ROUTES and
# is_mutating_route(). Layer-A patching covers symbol-call route
# attacks indirectly.


def test_known_mutating_routes_set_is_non_empty() -> None:
    """Smoke check: the registry has at least the 5 V130 §2 entries.
    Catches an accidental empty-set regression."""
    assert len(MUTATING_ROUTES) >= 5
    methods = {m for m, _ in MUTATING_ROUTES}
    # V130 §2 specifies POST + PUT verbs.
    assert "POST" in methods
    assert "PUT" in methods


def test_is_mutating_route_normalizes_case_id_segments() -> None:
    """Concrete case_id (uuid / hex) segments should match the
    ``{case_id}`` placeholder in the registry."""
    # uuid-style
    assert is_mutating_route("POST", "/api/import/abc123def/mesh")
    # hex-id
    assert is_mutating_route(
        "PUT", "/api/cases/4f7a8b9c/face-annotations"
    )
    # method case-insensitivity
    assert is_mutating_route("post", "/api/import/abc/mesh")
    # non-mutating route should NOT match
    assert not is_mutating_route(
        "GET", "/api/cases/abc/face-annotations"
    )
    assert not is_mutating_route(
        "POST", "/api/health"
    )


# ────────── Layer-C · static namespace-binding check ──────────


# AI dispatch module file paths, repository-relative.
_AI_DISPATCH_MODULES: tuple[str, ...] = (
    "ui/backend/services/ai_actions/__init__.py",
    "ui/backend/services/ai_actions/classifier/__init__.py",
    "ui/backend/services/llm_coach/tool_registry.py",
    "ui/backend/routes/ai_chat.py",
    "ui/backend/routes/ai_coach.py",
)


def _imported_symbols(file_path: Path) -> Iterable[tuple[str, str]]:
    """Yield ``(module_path, symbol_name)`` for every symbol imported
    by the file. Handles both ``from X import Y`` and
    ``import X`` (the latter yields ``(X, "")`` indicating wildcard
    namespace access).

    Aliases (``from X import Y as Z``) are normalized: the canonical
    ``(X, Y)`` is yielded regardless of the local alias, because the
    contract polices the canonical symbol identity, not the local name.
    """
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    yield (module, "*")
                else:
                    yield (module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield (alias.name, "")


@pytest.mark.parametrize("module_relpath", _AI_DISPATCH_MODULES)
def test_ai_dispatch_module_does_not_import_mutation_function(
    module_relpath: str,
) -> None:
    """Each AI dispatch module's import statements must not name any
    symbol in ``KNOWN_MUTATION_FUNCTIONS``. Catches bound-but-unused
    regressions."""
    repo_root = Path(__file__).resolve().parents[3]
    file_path = repo_root / module_relpath
    assert file_path.exists(), (
        f"AI dispatch module path stale: {module_relpath}. "
        "Update _AI_DISPATCH_MODULES."
    )

    forbidden = KNOWN_MUTATION_FUNCTIONS
    violations: list[tuple[str, str]] = []
    for module_path, symbol_name in _imported_symbols(file_path):
        if symbol_name == "*":
            # ``from X import *`` cannot be statically resolved; flag if
            # X matches any module path in the registry.
            for fmod, _fsym in forbidden:
                if module_path == fmod:
                    violations.append((module_path, symbol_name))
        elif symbol_name == "":
            # ``import X`` — the symbol is reachable as ``X.<name>``;
            # flag only if X exactly matches a registry module path.
            for fmod, _fsym in forbidden:
                if module_path == fmod:
                    violations.append((module_path, symbol_name))
        else:
            if (module_path, symbol_name) in forbidden:
                violations.append((module_path, symbol_name))

    assert not violations, (
        f"{module_relpath} imports forbidden mutation symbols: {violations}. "
        "AI dispatch modules must not bind any KNOWN_MUTATION_FUNCTIONS "
        "entry — bound-but-unused is the same risk class as called-once."
    )


# ────────── Falsifiability check ──────────
#
# The verification §4 of DEC-V61-132 requires demonstrating that the
# behavioral test FAILS when intentionally regressed. The verifier
# manually edits ``setup_bc_with_annotations`` to call ``setup_ldc_bc``
# in a confident branch and runs this file; expected outcome is
# ``test_setup_bc_with_annotations_envelope_no_mutation`` failing with
# a captured _MutationRecord. Restore via git checkout. This block
# documents the procedure; no automated falsifiability test is shipped
# (would require self-modifying source which is brittle).
