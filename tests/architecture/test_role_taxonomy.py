# -*- coding: utf-8 -*-
"""Machine-checked honesty invariant for the multi-agent role taxonomy.

Positioning SSOT: docs/architecture/AGENT_ROLES.md.

This test fills a verified gap (audited 2026-06-06): the project's existing
structural enforcement — src/_plane_assignment.py (PLANE_OF SSOT), src/_plane_guard.py
(runtime sys.meta_path guard), and the 5 .importlinter contracts — enforces the
*intra-src inter-plane* import boundaries (EXECUTION ↛ EVALUATION, etc.), but **none of
them assert that the solve/verdict plane never imports an LLM**. That is the precise
"advisor-not-driver" honesty fence this test adds.

The invariant (advisor-not-driver, enforced — not just documented):

    No module in the SOLVE / VERDICT plane may import any LLM client / AI-advisor
    surface. AI in this project is a *read-only advisor*; the deterministic pipeline
    that EXECUTES the case and DECIDES the verdict (worst-wins trust gate) + SIGNS the
    audit bundle must contain zero LLM reasoning. The LLM lives only in the advisor
    plane (ui/backend/services/{ai_advisor,llm_provider,...}) and the dogfood agentic
    test harness (scripts/dogfood/, --live opt-in) — both structurally fenced off.

Implementation honesty (per pre-impl red-team):
  * Match on the resolved AST import *target* (ast.Import / ast.ImportFrom node names),
    NOT a raw source-line substring — so string literals like the 'com.anthropic...'
    token in src/report_engine/visual_acceptance.py and the dynamic
    importlib.import_module('notion_client') in src/notion_sync are correctly ignored.
  * A CONTROL assertion verifies the boundary is REAL (non-vacuous): the advisor plane
    ui/backend/services DOES import LLM surfaces — so a PASS here means the solve plane
    is genuinely LLM-free, not that the token set is wrong.

Audited current state (2026-06-06): 92 solve-plane files, 0 LLM imports → PASS.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

# The solve / verdict plane: code that EXECUTES the case + DECIDES the verdict + SIGNS.
SOLVE_PLANE_ROOTS = (
    "src",
    "ui/backend/audit/cfdtrust",
    "ui/backend/audit/tools",
)
# The advisor plane: read-only AI advisor surface — LLM is ALLOWED here (control group).
ADVISOR_PLANE_ROOT = "ui/backend/services"

# LLM client / AI-advisor module-name tokens that must never be imported by the solve plane.
FORBIDDEN_LLM_TOKENS = (
    "llm_provider", "llm_coach",
    "ai_advisor", "ai_chat", "ai_coach", "ai_review", "ai_diagnose", "ai_actions",
    "openai", "anthropic", "deepseek",
)

# Documented exceptions (none required today — the invariant holds cleanly).
# Format: "<relative_path>::<imported_module>". Kept empty + asserted-empty-or-justified.
ALLOWLIST: frozenset[str] = frozenset()

_EXCLUDE_PARTS = ("__pycache__", ".egg-info")


def _py_files(root: str) -> list[pathlib.Path]:
    base = REPO / root
    if not base.exists():
        return []
    out = []
    for p in base.rglob("*.py"):
        if any(part.startswith(".venv") or part in _EXCLUDE_PARTS for part in p.parts):
            continue
        out.append(p)
    return out


def _imported_modules(path: pathlib.Path) -> list[str]:
    """Return the dotted module targets of every static import in *path* (AST-resolved)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:  # pragma: no cover - solve plane must parse
        pytest.fail(f"solve-plane file failed to parse: {path}")
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.append(node.module)
    return mods


def _llm_hits(path: pathlib.Path) -> list[str]:
    hits = []
    for mod in _imported_modules(path):
        if any(tok in mod for tok in FORBIDDEN_LLM_TOKENS):
            hits.append(mod)
    return hits


def _all_solve_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for root in SOLVE_PLANE_ROOTS:
        files.extend(_py_files(root))
    return files


def test_solve_plane_roots_exist_and_are_populated():
    """Guard against a glob/layout change silently emptying the scan (vacuous PASS)."""
    for root in SOLVE_PLANE_ROOTS:
        assert (REPO / root).is_dir(), f"solve-plane root missing: {root}"
    total = len(_all_solve_files())
    # Audited at 92 (65 + 22 + 5) on 2026-06-06; floor well below to tolerate churn,
    # but high enough to catch a broken glob.
    assert total >= 70, f"expected ~92 solve-plane files, found only {total} (glob broken?)"


def test_solve_plane_has_zero_llm_imports():
    """advisor-not-driver: the deterministic execute→decide→sign plane imports no LLM."""
    violations: list[str] = []
    for path in _all_solve_files():
        rel = path.relative_to(REPO).as_posix()
        for mod in _llm_hits(path):
            key = f"{rel}::{mod}"
            if key not in ALLOWLIST:
                violations.append(key)
    assert not violations, (
        "Solve/verdict plane must contain ZERO LLM imports (advisor-not-driver). "
        "Found LLM imports in the deterministic execute→decide→sign plane:\n  "
        + "\n  ".join(sorted(violations))
        + "\nIf an import is legitimate, justify it in ALLOWLIST with a comment."
    )


def test_boundary_is_real_advisor_plane_does_use_llm():
    """CONTROL (anti-vacuous): the advisor plane DOES import LLM surfaces.

    If this fails, FORBIDDEN_LLM_TOKENS no longer matches reality and the
    zero-imports test above would be passing vacuously.
    """
    advisor_files = _py_files(ADVISOR_PLANE_ROOT)
    assert advisor_files, f"advisor plane not found: {ADVISOR_PLANE_ROOT}"
    llm_using = [p for p in advisor_files if _llm_hits(p)]
    assert llm_using, (
        "Expected the advisor plane (ui/backend/services) to import LLM surfaces "
        "(llm_provider / ai_advisor). None found — the token set is likely stale, "
        "which would make test_solve_plane_has_zero_llm_imports vacuous."
    )


# --- Agentic tier confinement: the genuine autonomous LLM agents (dogfood personas)
#     must stay off the production import graph. Non-test code under src/ and ui/backend
#     may never import scripts.dogfood. (grep-proven 0 in src/, ui/backend hits = tests only.)
_AGENTIC_HARNESS = "scripts.dogfood"
_CONFINEMENT_ROOTS = ("src", "ui/backend")


def _is_test_path(path: pathlib.Path) -> bool:
    parts = path.parts
    return "tests" in parts or path.name.startswith("test_") or path.name == "conftest.py"


def test_agentic_dogfood_harness_not_imported_by_production():
    """The dogfood LLM-agent harness is a test fixture, not on the production path."""
    offenders: list[str] = []
    for root in _CONFINEMENT_ROOTS:
        for path in _py_files(root):
            if _is_test_path(path):
                continue
            for mod in _imported_modules(path):
                if mod == _AGENTIC_HARNESS or mod.startswith(_AGENTIC_HARNESS + "."):
                    offenders.append(f"{path.relative_to(REPO).as_posix()}::{mod}")
    assert not offenders, (
        "Production code (non-test src/ + ui/backend) must not import the dogfood "
        "agentic harness (scripts.dogfood). Found:\n  " + "\n  ".join(sorted(offenders))
    )
