"""Tests for scripts/governance/check_corpus_sync.py (M-DRIFT milestone).

Isolated temp-git-repo fixtures verify 3 behaviors:
  1. Both methodology + runtime staged → exit 0
  2. Only methodology staged, no trailer → exit 1
  3. Only methodology staged, `Corpus-sync-defer:` trailer present → exit 0
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "governance" / "check_corpus_sync.py"

METHODOLOGY = ".planning/methodology/industrial_case_solver_findings.md"
RUNTIME_COPY = "docs/openfoam_corpus/industrial_solver_findings_v_series.md"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=cwd,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    ).strip()


def _make_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def _stage(repo: Path, rel: str, content: str = "x") -> None:
    full = repo / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    _git(repo, "add", rel)


def _run_hook(repo: Path, msg: str) -> tuple[int, str]:
    msg_file = repo / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text(msg)
    result = subprocess.run(
        ["python3", str(HOOK), str(msg_file)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


def test_both_staged_passes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _stage(repo, METHODOLOGY, "v-row content")
    _stage(repo, RUNTIME_COPY, "v-row content")
    rc, _ = _run_hook(repo, "docs(v-series): add V85")
    assert rc == 0


def test_methodology_only_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _stage(repo, METHODOLOGY, "v-row content")
    rc, stderr = _run_hook(repo, "docs(v-series): add V85")
    assert rc == 1
    assert "Corpus drift detected" in stderr
    assert RUNTIME_COPY in stderr


def test_methodology_only_with_defer_trailer_passes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _stage(repo, METHODOLOGY, "trailer-only edit")
    msg = (
        "docs(v-series): housekeeping trailer update\n\n"
        "Some explanation.\n\n"
        "Corpus-sync-defer: trailer-only · no new V-row\n"
    )
    rc, _ = _run_hook(repo, msg)
    assert rc == 0


def test_no_methodology_staged_passes(tmp_path: Path) -> None:
    """Unrelated commits should pass."""
    repo = _make_repo(tmp_path)
    _stage(repo, "src/foo.py", "print('hi')")
    rc, _ = _run_hook(repo, "feat(foo): unrelated change")
    assert rc == 0
