"""Tests for scripts/check_codex_cadence.py — Opus 4.7 governance hook.

Uses isolated temp git repos so we don't depend on the host repo's commit
history. Verifies:
  1. Empty / fresh repo → bootstrap mode, exit 0
  2. Trailer with non-canonical verdict ("pending") → still bootstrap mode
  3. Last verified <10 commits ago → exit 0 with within-threshold message
  4. Last verified >=10 commits ago → exit 1 with cadence violation
  5. CODEX_CADENCE_OVERRIDE=1 → exit 0 even past threshold
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "scripts" / "check_codex_cadence.py"


def _run_git(cwd: Path, *args: str) -> str:
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


def _commit(cwd: Path, message: str, fname: str = "f.txt") -> None:
    (cwd / fname).write_text((cwd / fname).read_text() + "x" if (cwd / fname).exists() else "x")
    _run_git(cwd, "add", fname)
    _run_git(cwd, "commit", "-m", message, "--no-verify")


def _run_hook(cwd: Path, override: bool = False) -> tuple[int, str]:
    env = {**os.environ}
    if override:
        env["CODEX_CADENCE_OVERRIDE"] = "1"
    else:
        env.pop("CODEX_CADENCE_OVERRIDE", None)
    res = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=cwd, env=env,
        capture_output=True, text=True,
    )
    return res.returncode, (res.stdout + res.stderr)


@pytest.fixture
def fresh_repo(tmp_path: Path) -> Path:
    _run_git(tmp_path, "init", "-q")
    _run_git(tmp_path, "checkout", "-q", "-b", "main")
    _commit(tmp_path, "init")
    return tmp_path


def test_bootstrap_mode_no_trailer(fresh_repo: Path) -> None:
    """Empty repo (no Codex-verified) — should exit 0 with bootstrap notice."""
    code, out = _run_hook(fresh_repo)
    assert code == 0
    assert "bootstrap mode" in out


def test_pending_trailer_does_not_count(fresh_repo: Path) -> None:
    """'Codex-verified: pending' is NOT a canonical verdict — must still
    be bootstrap mode."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: pending")
    code, out = _run_hook(fresh_repo)
    assert code == 0
    assert "bootstrap mode" in out


def test_canonical_verdict_within_threshold(fresh_repo: Path) -> None:
    """One canonical-verdict commit + 5 follow-up commits → within threshold."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: APPROVE all good")
    for i in range(5):
        _commit(fresh_repo, f"chore: follow-up {i}")
    code, out = _run_hook(fresh_repo)
    assert code == 0
    assert "within threshold" in out


def test_canonical_verdict_at_threshold_blocks(fresh_repo: Path) -> None:
    """Last verified 10 commits ago → blocked."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: APPROVE_WITH_COMMENTS ok")
    for i in range(10):
        _commit(fresh_repo, f"chore: follow-up {i}")
    code, out = _run_hook(fresh_repo)
    assert code == 1
    assert "10 commits since last Codex-verified" in out
    assert "Required action" in out


def test_override_env_var_skips(fresh_repo: Path) -> None:
    """CODEX_CADENCE_OVERRIDE=1 bypasses even past threshold."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: CHANGES_REQUIRED then RESOLVED")
    for i in range(15):
        _commit(fresh_repo, f"chore: follow-up {i}")
    code, out = _run_hook(fresh_repo, override=True)
    assert code == 0
    assert "OVERRIDE active" in out


def test_resolved_verdict_counts(fresh_repo: Path) -> None:
    """RESOLVED is a canonical verdict (CHANGES_REQUIRED → RESOLVED is the
    common after-fix pattern)."""
    _commit(fresh_repo, "fix: round-2\n\nCodex-verified: RESOLVED round-1 LOWs cleared")
    for i in range(3):
        _commit(fresh_repo, f"chore: follow-up {i}")
    code, out = _run_hook(fresh_repo)
    assert code == 0
    assert "within threshold" in out
