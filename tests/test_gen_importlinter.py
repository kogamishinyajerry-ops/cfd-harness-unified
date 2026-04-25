"""Tests for ``scripts/gen_importlinter.py`` (ADR-002 §2.2).

The generator is the bridge between ``src._plane_assignment.PLANE_OF``
(SSOT) and ``.importlinter`` (static enforcement). It must be:

  * **Byte-identical**: regenerating from current PLANE_OF reproduces
    the on-disk ``.importlinter`` byte-for-byte.
  * **--check correct**: zero diff returns exit code 0; any drift
    returns 1 with a unified diff on stderr.
  * **Self-rooted**: works whether invoked as a script or via
    ``python -m scripts.gen_importlinter``.

These tests run quickly and have no Docker / network dependencies, so
they belong in the default pytest path.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_SCRIPT = REPO_ROOT / "scripts" / "gen_importlinter.py"
IMPORTLINTER_PATH = REPO_ROOT / ".importlinter"


@pytest.fixture(scope="module")
def gen_module():
    """Import the generator as a module for unit-style assertions.

    The script lives outside ``src/`` and ``tests/``; we add ``scripts``
    to ``sys.path`` once and import.
    """
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    return importlib.import_module("gen_importlinter")


# ---------------------------------------------------------------------------
# Render correctness
# ---------------------------------------------------------------------------


def test_render_matches_on_disk_importlinter(gen_module):
    """ADR-002 §2.2 — running the generator produces the file currently on disk."""
    rendered = gen_module.render_importlinter()
    on_disk = IMPORTLINTER_PATH.read_text(encoding="utf-8")
    assert rendered == on_disk, (
        "Generator output drifted from .importlinter — run "
        "`python scripts/gen_importlinter.py` to regenerate, or update "
        "PLANE_OF if the drift is intentional."
    )


def test_rendered_contains_all_five_contracts(gen_module):
    """All four ADR-001 contracts plus the ADR-002 bootstrap-purity contract."""
    rendered = gen_module.render_importlinter()
    expected_contract_ids = [
        "execution-never-imports-evaluation",
        "evaluation-never-imports-execution",
        "knowledge-no-reverse-import",
        "models-stays-pure",
        "plane-guard-bootstrap-purity",
    ]
    for contract_id in expected_contract_ids:
        assert f"[importlinter:contract:{contract_id}]" in rendered


def test_rendered_starts_with_importlinter_header(gen_module):
    """Header section is fixed; tooling parses it before any contract block."""
    rendered = gen_module.render_importlinter()
    assert rendered.startswith("# import-linter contract for cfd-harness-unified")
    assert "[importlinter]\nroot_package = src\n" in rendered


# ---------------------------------------------------------------------------
# CLI behavior
# ---------------------------------------------------------------------------


def _run_generator(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run the generator as a subprocess (matches CI invocation)."""
    return subprocess.run(
        [sys.executable, str(GEN_SCRIPT), *args],
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_check_passes_on_current_main():
    """``--check`` exits 0 when ``.importlinter`` matches PLANE_OF."""
    result = _run_generator("--check")
    assert result.returncode == 0, (
        f"--check failed unexpectedly:\n"
        f"  stdout: {result.stdout}\n"
        f"  stderr: {result.stderr}"
    )


def test_check_fails_on_drift(tmp_path: Path):
    """``--check`` against a corrupted ``.importlinter`` exits 1 with a diff."""
    corrupted = tmp_path / ".importlinter"
    corrupted.write_text("# tampered\n[importlinter]\nroot_package = src\n", encoding="utf-8")
    result = _run_generator("--check", "--path", str(corrupted))
    assert result.returncode == 1
    assert "drifted" in result.stderr
    # Unified diff should appear in the output.
    assert "+++" in result.stderr or "---" in result.stderr


def test_check_fails_when_file_missing(tmp_path: Path):
    """``--check`` against a non-existent path exits 1 with a clear message."""
    nonexistent = tmp_path / "no_such_file"
    result = _run_generator("--check", "--path", str(nonexistent))
    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_default_invocation_writes_to_path(tmp_path: Path):
    """Without ``--check`` the generator overwrites the target path."""
    target = tmp_path / "regenerated.importlinter"
    # Pre-populate with garbage so the test proves overwrite, not append.
    target.write_text("garbage\n", encoding="utf-8")
    result = _run_generator("--path", str(target))
    assert result.returncode == 0
    written = target.read_text(encoding="utf-8")
    on_disk = IMPORTLINTER_PATH.read_text(encoding="utf-8")
    assert written == on_disk
