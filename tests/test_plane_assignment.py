"""Plane assignment defensive tests · per ADR-001 §2.7 AC-1 + AC-2.

These tests supplement `.importlinter` via AST-walk assertions that
remain authoritative even if the importlinter contract is accidentally
weakened. They catch plane-cross violations that a shallow dependency
graph analysis could miss (e.g. conditional imports under `if
TYPE_CHECKING`).

Opus 追签 AC-2 · 2026-04-25:
  Hard-assert `src.audit_package` does not import any module from the
  Evaluation Plane (§2.1). With .importlinter this is already covered,
  but we keep this AST test as a double-lock — if someone `git mv`-s
  a file between planes and forgets to update .importlinter
  source_modules, this test still fails.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"

# Authoritative plane assignment (mirrors ADR-001 §2.1 · 2026-04-25).
_EVALUATION_MODULES = {
    "src.comparator_gates",
    "src.convergence_attestor",
    "src.error_attributor",
    "src.result_comparator",
    "src.correction_recorder",
    "src.auto_verifier",
    "src.report_engine",
}
_EXECUTION_MODULES = {
    "src.foam_agent_adapter",
    "src.airfoil_surface_sampler",
    "src.cylinder_centerline_extractor",
    "src.cylinder_strouhal_fft",
    "src.plane_channel_uplus_emitter",
    "src.wall_gradient",
}


def _walk_imports(path: Path) -> set[str]:
    """Parse a .py file and return the set of `src.*` imports (incl. subpackages)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.") or alias.name == "src":
                    found.add(alias.name.split(".")[0:2] and ".".join(alias.name.split(".")[:2]) or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("src."):
                parts = node.module.split(".")
                # capture up to two levels (e.g. src.audit_package, src.report_engine)
                found.add(".".join(parts[:2]))
            # Also catch relative imports from within src/ — they resolve to src.*
    return found


def _src_submodule_imports(package_path: Path) -> set[str]:
    """Recursively walk a package, collect all `src.*` imports. Resolves both
    absolute (`from src.X import Y`) and relative (`from ..X import Y`) forms
    when the relative import crosses back into `src.*` territory.
    """
    found: set[str] = set()
    pkg_prefix = "src." + package_path.name  # e.g. "src.audit_package"
    for py in package_path.rglob("*.py"):
        absolute = _walk_imports(py)
        # Filter out self-references (imports from within same top-level package)
        found |= {m for m in absolute if m != pkg_prefix}
        # Relative imports: compute how far the `from ..X` climbs and resolve.
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level >= 2 and node.module:
                # level=2 from inside src/audit_package/ means src.<module>
                # parts of node.module are relative to that resolved base.
                resolved = "src." + node.module.split(".")[0]
                if resolved != pkg_prefix:
                    found.add(resolved)
    return found


def test_audit_package_no_reverse_import() -> None:
    """ADR-001 §2.7 AC-2: `src.audit_package` (Control) must NOT import from
    any Evaluation-Plane module.

    Complements .importlinter's knowledge-no-reverse-import contract with an
    AST-walk assertion that survives .importlinter config drift.
    """
    audit_pkg = SRC / "audit_package"
    assert audit_pkg.is_dir(), f"Expected {audit_pkg} to exist"
    imported = _src_submodule_imports(audit_pkg)
    violations = imported & _EVALUATION_MODULES
    assert not violations, (
        f"src.audit_package imports Evaluation-Plane modules: {sorted(violations)}. "
        f"Per ADR-001 §2.1 this is a HARD NO. Comparator / attestor / correction "
        f"artifacts should be caller-injected, not imported."
    )


def test_audit_package_no_execution_import() -> None:
    """Defense-in-depth sibling of the above: Control → Execution is allowed
    in general but `src.audit_package` specifically builds audit manifests
    from *caller-injected* data and should not reach into solver adapters.
    Fails if someone accidentally has audit_package importing foam_agent_adapter.
    """
    audit_pkg = SRC / "audit_package"
    imported = _src_submodule_imports(audit_pkg)
    violations = imported & _EXECUTION_MODULES
    assert not violations, (
        f"src.audit_package imports Execution-Plane modules: {sorted(violations)}. "
        f"audit manifest should receive solver output as caller-injected data."
    )


@pytest.mark.parametrize(
    "evaluation_module",
    [
        "comparator_gates",
        "convergence_attestor",
        "error_attributor",
        "result_comparator",
        "correction_recorder",
    ],
)
def test_evaluation_flat_modules_no_execution_import(evaluation_module: str) -> None:
    """ADR-001 HARD NO #2: Evaluation ↛ Execution.

    Already covered by .importlinter forbidden contract; AST test here is
    a second layer catching relative imports that grimp graph might miss.
    """
    module_path = SRC / f"{evaluation_module}.py"
    if not module_path.is_file():
        pytest.skip(f"{module_path.name} not present")
    imported = _walk_imports(module_path)
    violations = imported & _EXECUTION_MODULES
    assert not violations, (
        f"src.{evaluation_module} imports Execution-Plane modules: "
        f"{sorted(violations)}. Per ADR-001 §2.1 this is a HARD NO."
    )
