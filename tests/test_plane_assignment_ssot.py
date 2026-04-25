"""SSOT round-trip + orphan tests for ``src._plane_assignment.PLANE_OF``.

Companion to ``tests/test_plane_assignment.py`` (which AST-walks
``src/`` for plane-cross violations per ADR-001 §2.7 AC-1+AC-2). These
tests instead validate the single-source-of-truth table consumed by
both ``scripts/gen_importlinter.py`` (static layer) and the future
``src._plane_guard`` (runtime layer per ADR-002 §2.2).

Coverage targets:
  * ADR-001 §2.7 AC-2 coverage (every top-level ``src.*`` module is in
    PLANE_OF — no orphans).
  * ADR-002 AC-A5 (orphan check, same condition).
  * ADR-002 AC-A12 (bootstrap module imports stdlib only — lexical grep
    catches additions even when import-linter is misconfigured).
  * Round-trip: ``modules_in(plane)`` and ``plane_of(name)`` agree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src._plane_assignment import PLANE_OF, Plane, modules_in, plane_of


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

# Filesystem entries under ``src/`` that are not Python modules/packages
# and should NOT be listed in PLANE_OF.
_NON_MODULE_ENTRIES = {"__init__.py", "__pycache__", "cfd_harness_unified.egg-info"}


def _top_level_src_modules() -> set[str]:
    """Walk ``src/`` to enumerate top-level module / package names."""
    names: set[str] = set()
    for child in SRC_ROOT.iterdir():
        if child.name in _NON_MODULE_ENTRIES:
            continue
        if child.is_dir():
            if (child / "__init__.py").exists():
                names.add(f"src.{child.name}")
            elif any(child.iterdir()):
                names.add(f"src.{child.name}")
        elif child.suffix == ".py":
            names.add(f"src.{child.stem}")
    return names


def test_every_src_module_has_plane_of_entry():
    """ADR-001 §2.7 AC-2 · ADR-002 AC-A5 — no orphan ``src.*`` modules."""
    discovered = _top_level_src_modules()
    mapped = set(PLANE_OF)
    orphans = discovered - mapped
    assert not orphans, (
        f"Top-level src.* modules missing from PLANE_OF: {sorted(orphans)}. "
        "Add them to src/_plane_assignment.py::PLANE_OF and re-run "
        "`python scripts/gen_importlinter.py` to refresh .importlinter."
    )


def test_plane_of_has_no_ghost_entries():
    """Reverse direction: PLANE_OF should not reference removed modules."""
    discovered = _top_level_src_modules()
    mapped = set(PLANE_OF)
    ghosts = mapped - discovered
    assert not ghosts, (
        f"PLANE_OF entries without a corresponding src.* module: {sorted(ghosts)}. "
        "Remove the stale entries or restore the modules."
    )


def test_plane_enum_has_expected_members():
    """Explicit enumeration — Plane membership is an ADR-level decision."""
    assert {p.name for p in Plane} == {
        "CONTROL",
        "EXECUTION",
        "EVALUATION",
        "KNOWLEDGE",
        "SHARED",
        "BOOTSTRAP",
    }


def test_plane_of_unknown_module_returns_none():
    """Unmapped callers must not raise — runtime guard treats None as <external>."""
    assert plane_of("some.external.package") is None
    assert plane_of("src.nonexistent_module") is None


def test_modules_in_round_trips_with_plane_of():
    """Every module listed under a plane via ``modules_in`` maps back via ``plane_of``."""
    for plane in Plane:
        for name in modules_in(plane):
            assert plane_of(name) is plane


def test_modules_in_preserves_declaration_order():
    """Byte-identical CI check (ADR-002 §2.2) requires deterministic order."""
    control = modules_in(Plane.CONTROL)
    assert control[0] == "src.task_runner"
    assert control[-1] == "src.audit_package"


def test_every_plane_has_at_least_one_module():
    """Empty planes would produce malformed ``.importlinter`` contracts."""
    for plane in Plane:
        assert modules_in(plane), f"Plane {plane.name} has no modules assigned"


def test_bootstrap_plane_is_stdlib_only():
    """ADR-002 §4.1 A12 — bootstrap module must import zero ``src.*`` packages.

    This is a lexical grep rather than an import trace because the
    purpose of the check is to catch additions at source-edit time. A
    ``from src.foo import bar`` line gated behind ``if TYPE_CHECKING:``
    is still a bootstrap-purity violation per A12 framing.
    """
    bootstrap_modules = modules_in(Plane.BOOTSTRAP)
    assert bootstrap_modules == ("src._plane_assignment",), (
        "Bootstrap plane membership changed — ADR-002 A12 expects a single "
        "module today (src._plane_assignment). Multi-module decomposition "
        "is deferred to ADR-002 v1.1 per Draft-rev4 R-new-3."
    )
    source_path = SRC_ROOT / "_plane_assignment.py"
    text = source_path.read_text(encoding="utf-8")
    forbidden_patterns = [
        re.compile(r"^\s*import\s+src(\.|\s|$)", re.MULTILINE),
        re.compile(r"^\s*from\s+src(\.|\s)", re.MULTILINE),
    ]
    violations: list[str] = []
    for pattern in forbidden_patterns:
        violations.extend(m.group(0).strip() for m in pattern.finditer(text))
    assert not violations, (
        f"src/_plane_assignment.py imports src.* — bootstrap-purity violation:\n"
        f"  {violations}"
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        ("src.task_runner", Plane.CONTROL),
        ("src.foam_agent_adapter", Plane.EXECUTION),
        ("src.result_comparator", Plane.EVALUATION),
        ("src.metrics", Plane.EVALUATION),
        ("src.knowledge_db", Plane.KNOWLEDGE),
        ("src.models", Plane.SHARED),
        ("src._plane_assignment", Plane.BOOTSTRAP),
    ],
)
def test_canonical_assignments_match_adr_001(name: str, expected: Plane):
    """Spot-check the canonical planes remain as ADR-001 §2.1 prescribes."""
    assert plane_of(name) is expected
