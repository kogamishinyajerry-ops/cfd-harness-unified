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
    # Round-2 reformat: success line says "cadence=bootstrap (no trailer in repo history)"
    assert "cadence=bootstrap" in out


def test_pending_trailer_does_not_count(fresh_repo: Path) -> None:
    """'Codex-verified: pending' is NOT a canonical verdict — must still
    be bootstrap mode."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: pending")
    code, out = _run_hook(fresh_repo)
    assert code == 0
    assert "cadence=bootstrap" in out


def test_canonical_verdict_within_threshold(fresh_repo: Path) -> None:
    """One canonical-verdict commit + 5 follow-up commits → within threshold."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: APPROVE all good")
    for i in range(5):
        _commit(fresh_repo, f"chore: follow-up {i}")
    code, out = _run_hook(fresh_repo)
    assert code == 0
    # Round-2: "cadence=5/10 since <sha>"
    assert "cadence=5/10" in out


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
    # Round-2 reformat: success line says "OK · cadence=N/THRESHOLD ..."
    assert "cadence=" in out


# --- Round-2 Q5: bootstrap-cliff fix (full-history scan) -------------------

def test_q5_bootstrap_cliff_closed(fresh_repo: Path) -> None:
    """Round-2 Q5 fix: when a verified commit exists 51+ commits back,
    the old LOOKBACK=50 hook would exit 0 (mistaking it for bootstrap
    mode). The full-history scan must find it and BLOCK because the
    cadence count is ≥ THRESHOLD=10."""
    _commit(fresh_repo, "feat: ancient verify\n\nCodex-verified: APPROVE legacy")
    # Push it past the old LOOKBACK boundary
    for i in range(60):
        _commit(fresh_repo, f"chore: filler {i}")
    code, out = _run_hook(fresh_repo)
    assert code == 1, "must block — verified commit exists but is far away"
    assert "CADENCE BLOCK" in out
    # The hook must not be in 'bootstrap' mode; it found the trailer.
    assert "bootstrap" not in out.lower() or "BLOCK" in out


def test_q5_genuinely_never_verified_still_bootstrap(fresh_repo: Path) -> None:
    """Bootstrap mode is still correct when the trailer has truly never
    existed in the repo — even if there are 100 commits."""
    for i in range(20):
        _commit(fresh_repo, f"chore: filler {i}")
    code, out = _run_hook(fresh_repo)
    assert code == 0
    assert "bootstrap" in out.lower()


# --- Round-2 Q14: risk-class trigger table ---------------------------------

def _seed_verified_baseline(repo: Path) -> None:
    """Many risk-class tests need an existing verified commit so the
    cadence gate is satisfied — leaving only the risk-class gate to
    actually probe. We fake `origin/main` by tagging the verified
    commit; the hook's fallback uses `origin/main..HEAD` as diff range."""
    _commit(repo, "feat: baseline\n\nCodex-verified: APPROVE baseline")
    _run_git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")


def _add_file_and_commit(repo: Path, relpath: str, content: str, msg: str) -> None:
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _run_git(repo, "add", str(target.relative_to(repo)))
    _run_git(repo, "commit", "-m", msg, "--no-verify")


def test_q14_new_route_file_blocks_without_trailer(fresh_repo: Path) -> None:
    """A new file under ui/backend/routes/ is risk-class even if cadence
    count is well under threshold."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo,
        "ui/backend/routes/new_endpoint.py",
        "# new HTTP route\n",
        "feat(routes): add new endpoint",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 1, "new route file must trigger risk-class block"
    assert "RISK-CLASS BLOCK" in out
    assert "new_endpoint.py" in out


def test_q14_new_page_file_blocks_without_trailer(fresh_repo: Path) -> None:
    """New nested page (frontend) — same risk class as new route."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo,
        "ui/frontend/src/pages/workbench/SomeNewPage.tsx",
        "export function SomeNewPage() { return null; }\n",
        "feat(workbench): add some new page",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 1
    assert "RISK-CLASS BLOCK" in out
    assert "SomeNewPage.tsx" in out


def test_q14_loc_threshold_blocks(fresh_repo: Path) -> None:
    """LOC > 500 in a single push triggers risk-class."""
    _seed_verified_baseline(fresh_repo)
    big_blob = "\n".join(f"line {i}" for i in range(600))
    _add_file_and_commit(
        fresh_repo, "src/big_module.py", big_blob, "feat: big module"
    )
    code, out = _run_hook(fresh_repo)
    assert code == 1
    assert "RISK-CLASS BLOCK" in out
    assert "diff adds" in out


def test_q14_security_pattern_in_added_lines_blocks(fresh_repo: Path) -> None:
    """Adding a `_validate_*` function or `StreamingResponse` triggers."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo,
        "src/some_helper.py",
        "def _validate_foo(x): return x\n",
        "feat: add security helper",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 1
    assert "RISK-CLASS BLOCK" in out
    assert "_validate_" in out


def test_q14_head_trailer_overrides_risk_class(fresh_repo: Path) -> None:
    """If HEAD itself carries a canonical trailer, risk-class is satisfied
    (the work was Codex-reviewed; pushing it is the whole point)."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo,
        "ui/backend/routes/blessed_endpoint.py",
        "# blessed\n",
        "feat(routes): add blessed endpoint\n\nCodex-verified: APPROVE reviewed",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 0, f"HEAD trailer must satisfy risk gate; got: {out}"


def test_q14_unrelated_change_passes(fresh_repo: Path) -> None:
    """Editing an existing non-risk file (small) passes both gates."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo, "docs/readme.md", "small doc edit", "docs: tweak"
    )
    code, out = _run_hook(fresh_repo)
    assert code == 0, f"benign change must pass; got: {out}"


def test_override_still_works_with_risk_triggers(fresh_repo: Path) -> None:
    """CODEX_CADENCE_OVERRIDE=1 still bypasses both gates — for
    bootstrapping the hook's own merge or genuine emergencies."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo,
        "ui/backend/routes/risky.py",
        "# new route\n",
        "feat(routes): risky",
    )
    code, out = _run_hook(fresh_repo, override=True)
    assert code == 0
    assert "OVERRIDE active" in out
