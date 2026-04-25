"""Reverse-test asserting the §2.4 test-allowlist has no escape paths.

ADR-002 §4.1 AC-A17: the test-allowlist regex ``^tests($|\\.)`` accepts
modules whose dotted name starts with ``tests``. Two physical-layout
escape risks were called out in §2.4 negative analysis:

  (i) production code in a ``_test.py`` / ``test_*.py`` file under
      ``src/`` would bypass the guard.
  (ii) production code under a nested ``src/**/tests/`` directory would
       likewise bypass.

This test asserts via ``glob`` that neither escape exists in the
current repo. Per Draft-rev3 minor #2 the scope explicitly excludes
``ui/backend/**`` and ``scripts/**`` (out of ADR-001 v1.0 contract
scope per ADR-001 §3.2). When ADR-001 §2.7 trigger fires for either
of those trees (single PR net >500 LOC), the glob scope amends along
with the plane-assignment audit.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"


@pytest.mark.parametrize(
    "pattern,description",
    [
        ("src/**/*_test.py", "files matching *_test.py under src/"),
        ("src/**/test_*.py", "files matching test_*.py under src/"),
        ("src/**/tests", "nested tests/ directories under src/"),
        ("src/**/tests/**", "anything under nested src/**/tests/"),
    ],
)
def test_no_test_files_or_dirs_under_src(pattern: str, description: str):
    """Asserts ``glob`` finds nothing under ``src/`` matching test conventions."""
    matches = glob.glob(str(REPO_ROOT / pattern), recursive=True)
    # Exclude ``__pycache__`` artifacts which can incidentally appear.
    matches = [m for m in matches if "__pycache__" not in m]
    assert not matches, (
        f"§2.4 reverse-test failure — found {description}: {matches}\n"
        "These would bypass the runtime plane guard's test-allowlist. "
        "Move under tests/ or rename."
    )


def test_src_remains_regular_package():
    """ADR-002 §2.9 (Draft-rev3 minor #3) — src/ MUST be a regular package.

    Namespace-package mode breaks §2.9 sys.modules watchdog anchoring
    and Pattern 9 closure. If this fails, an ``__init__.py`` was
    deleted from ``src/``.
    """
    init_path = SRC_ROOT / "__init__.py"
    assert init_path.is_file(), (
        f"src/__init__.py missing — src/ has degraded to a PEP 420 "
        f"namespace package. ADR-002 §2.9 strong constraint forbids this. "
        f"Restore the file or supersede ADR-002 with a follow-up ADR."
    )
