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


def _run_hook(
    cwd: Path,
    override: bool = False,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str]:
    env = {**os.environ}
    if override:
        env["CODEX_CADENCE_OVERRIDE"] = "1"
    else:
        env.pop("CODEX_CADENCE_OVERRIDE", None)
    # Round-2 Q6: env-driven override-reason. Tests that should pass under
    # the new gate pass extra_env={"CODEX_OVERRIDE_REASON": "..."}.
    env.pop("CODEX_OVERRIDE_REASON", None)
    if extra_env:
        env.update(extra_env)
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
    """CODEX_CADENCE_OVERRIDE=1 bypasses even past threshold. Round-2 Q6
    now also requires CODEX_OVERRIDE_REASON (or Override-reason: trailer)
    so the test fixture supplies one."""
    _commit(fresh_repo, "feat: x\n\nCodex-verified: CHANGES_REQUIRED then RESOLVED")
    for i in range(15):
        _commit(fresh_repo, f"chore: follow-up {i}")
    code, out = _run_hook(
        fresh_repo,
        override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "test fixture · cadence override"},
    )
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
    bootstrapping the hook's own merge or genuine emergencies. As of
    round-2 Q6 the override now requires an audit reason; the test
    fixture supplies one via env var so this case still passes."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo,
        "ui/backend/routes/risky.py",
        "# new route\n",
        "feat(routes): risky",
    )
    code, out = _run_hook(
        fresh_repo,
        override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "test fixture"},
    )
    assert code == 0
    assert "OVERRIDE active" in out


# --- Round-2 Q6: override double-trace (Override-reason + audit log) -------

def test_q6_override_without_reason_blocked(fresh_repo: Path) -> None:
    """Round-2 Q6: env var alone is no longer enough. Must supply
    Override-reason: in commit body OR CODEX_OVERRIDE_REASON env var."""
    _seed_verified_baseline(fresh_repo)
    code, out = _run_hook(fresh_repo, override=True)
    assert code == 1, f"override without reason must block: {out}"
    assert "OVERRIDE BLOCKED" in out
    assert "Override-reason" in out


def test_q6_override_with_env_reason_logs(fresh_repo: Path) -> None:
    """CODEX_OVERRIDE_REASON env var satisfies the audit requirement and
    the override is logged to .governance/codex_cadence_overrides.log."""
    _seed_verified_baseline(fresh_repo)
    code, out = _run_hook(
        fresh_repo,
        override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "emergency hotfix · ticket #999"},
    )
    assert code == 0
    log_path = fresh_repo / ".governance" / "codex_cadence_overrides.log"
    assert log_path.exists(), "audit log must be written"
    log_content = log_path.read_text(encoding="utf-8")
    assert "emergency hotfix" in log_content
    assert "ticket #999" in log_content


def test_q6_override_with_trailer_reason_logs(fresh_repo: Path) -> None:
    """`Override-reason: <text>` trailer in HEAD commit body satisfies
    the audit requirement and is preferred over env var (durable in git)."""
    _seed_verified_baseline(fresh_repo)
    _commit(
        fresh_repo,
        "chore: rollback v3 patch\n\nOverride-reason: revert botched migration",
    )
    code, out = _run_hook(fresh_repo, override=True)
    assert code == 0, f"trailer reason must satisfy: {out}"
    log_path = fresh_repo / ".governance" / "codex_cadence_overrides.log"
    assert log_path.exists()
    log_content = log_path.read_text(encoding="utf-8")
    assert "revert botched migration" in log_content


def test_q6_override_log_format_jsonl(fresh_repo: Path) -> None:
    """Round-3 F8 migration: audit log is now JSONL (one JSON object per
    line) instead of TSV. Round-2 TSV form was retired because tabs in
    `Override-reason:` text broke parse-back."""
    import json as _json

    _seed_verified_baseline(fresh_repo)
    _run_hook(
        fresh_repo,
        override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "format check"},
    )
    log_path = fresh_repo / ".governance" / "codex_cadence_overrides.log"
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    record = _json.loads(line)  # must parse as JSON
    assert record["ts"].startswith("20")  # ISO8601
    assert len(record["sha"]) == 12
    assert record["reason"] == "format check"
    assert isinstance(record["n_triggers"], int)
    assert isinstance(record["triggers"], list)


def test_q6_override_log_appends_not_overwrites(fresh_repo: Path) -> None:
    """Two overrides → two lines. Append semantics, not overwrite."""
    _seed_verified_baseline(fresh_repo)
    _run_hook(
        fresh_repo, override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "first"},
    )
    _run_hook(
        fresh_repo, override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "second"},
    )
    log_path = fresh_repo / ".governance" / "codex_cadence_overrides.log"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert "first" in lines[0]
    assert "second" in lines[1]


# --- Round-3 F8: JSONL log format ------------------------------------------

def test_f8_log_is_jsonl_not_tsv(fresh_repo: Path) -> None:
    """Round-3 F8: each log line is a JSON object, not TSV. Tab/quote/
    newline characters in reason no longer break the format."""
    import json as _json

    _seed_verified_baseline(fresh_repo)
    _run_hook(
        fresh_repo, override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "ticket\twith\ttabs and \"quotes\""},
    )
    log_path = fresh_repo / ".governance" / "codex_cadence_overrides.log"
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    record = _json.loads(line)  # must parse as JSON
    assert record["reason"] == 'ticket\twith\ttabs and "quotes"', (
        "tabs and quotes must round-trip through JSONL"
    )
    assert "ts" in record and "sha" in record
    assert "n_triggers" in record and "triggers" in record


# --- Round-3 F10: CI override refusal --------------------------------------

def test_f10_ci_env_blocks_override_even_with_reason(fresh_repo: Path) -> None:
    """Round-3 F10: CI=true forbids override even if reason supplied.
    Policy: humans-only override; CI must use a Codex-verified trailer."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo, "ui/backend/routes/risky.py", "# new\n",
        "feat(routes): risky in CI",
    )
    code, out = _run_hook(
        fresh_repo,
        override=True,
        extra_env={
            "CI": "true",
            "CODEX_OVERRIDE_REASON": "test should still block",
        },
    )
    assert code == 1, f"CI override must be refused; got: {out}"
    assert "CI OVERRIDE REFUSED" in out


def test_f10_non_ci_override_still_works(fresh_repo: Path) -> None:
    """Sanity check: outside CI, the existing override path still works."""
    _seed_verified_baseline(fresh_repo)
    code, out = _run_hook(
        fresh_repo,
        override=True,
        extra_env={
            "CI": "",  # explicitly clear CI
            "CODEX_OVERRIDE_REASON": "human override",
        },
    )
    assert code == 0
    assert "OVERRIDE active" in out


# --- Round-3 F11: whitespace-only reason rejected --------------------------

def test_f11_override_reason_whitespace_only_blocks(fresh_repo: Path) -> None:
    """Round-3 F11: ' ' / '\t' / '\\n' as reason must be rejected.
    Defense-in-depth: even though the existing `or None` chain falls
    through to BLOCK on empty-after-strip, the explicit `if not reason`
    check now makes the intent loud and lint-checkable."""
    _seed_verified_baseline(fresh_repo)
    code, out = _run_hook(
        fresh_repo,
        override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "   "},
    )
    assert code == 1, f"whitespace-only reason must block; got: {out}"
    assert "OVERRIDE BLOCKED" in out


def test_f11_override_reason_tab_only_blocks(fresh_repo: Path) -> None:
    """Tabs alone count as whitespace and must also be rejected."""
    _seed_verified_baseline(fresh_repo)
    code, _ = _run_hook(
        fresh_repo,
        override=True,
        extra_env={"CODEX_OVERRIDE_REASON": "\t\t\t"},
    )
    assert code == 1


# --- Round-3 F5: risk-class detection on modifications ---------------------

def _modify_file_and_commit(
    repo: Path, relpath: str, content: str, msg: str
) -> None:
    target = repo / relpath
    target.write_text(content)
    _run_git(repo, "add", str(target.relative_to(repo)))
    _run_git(repo, "commit", "-m", msg, "--no-verify")


def test_f5_existing_risk_file_large_mod_blocks(fresh_repo: Path) -> None:
    """Round-3 F5: large modification of an existing routes/**.py file
    triggers risk-class even when no NEW file is added. Closes round-3
    finding 5: routes/wizard.py would be silently bypassed under round-2
    rule because round-2 only saw additions."""
    _seed_verified_baseline(fresh_repo)
    # First land a routes/wizard.py as a baseline (so it exists in HEAD).
    # We commit it as part of baseline so it's NOT new in the next push.
    _add_file_and_commit(
        fresh_repo, "ui/backend/routes/wizard.py",
        "# initial\n",
        "feat(routes): seed wizard route\n\nCodex-verified: APPROVE seed",
    )
    _run_git(fresh_repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    # Now add 200 LOC to the SAME existing file (no new file)
    big_blob = "# initial\n" + "\n".join(f"def fn_{i}(): pass" for i in range(200))
    _modify_file_and_commit(
        fresh_repo, "ui/backend/routes/wizard.py", big_blob,
        "feat(routes): big mod to wizard",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 1, f"large mod of risk-class file must block; got: {out}"
    assert "large modification" in out
    assert "wizard.py" in out


def test_f5_existing_risk_file_small_mod_passes(fresh_repo: Path) -> None:
    """Small mods (<150 LOC) of risk-class files must NOT trigger.
    A typo-fix PR shouldn't ring the governance bell."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo, "ui/backend/routes/wizard.py",
        "# initial\n" + "\n".join(f"line {i}" for i in range(50)),
        "feat(routes): seed wizard route\n\nCodex-verified: APPROVE seed",
    )
    _run_git(fresh_repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    # Modify ~30 LOC — well under the 150 threshold
    _modify_file_and_commit(
        fresh_repo, "ui/backend/routes/wizard.py",
        "# initial\n" + "\n".join(f"line {i}" for i in range(80)),
        "fix(routes): minor patch",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 0, f"small mod must pass; got: {out}"


def test_f5_added_risk_file_still_triggers(fresh_repo: Path) -> None:
    """Regression guard: F5 doesn't break the round-2 A-only behavior.
    A new file under routes/** still triggers regardless of LOC."""
    _seed_verified_baseline(fresh_repo)
    _add_file_and_commit(
        fresh_repo, "ui/backend/routes/brand_new.py",
        "# tiny new file\n",
        "feat(routes): brand new",
    )
    code, out = _run_hook(fresh_repo)
    assert code == 1
    assert "new file matches" in out


# --- Round-3 F4: full-history cap safety valve -----------------------------

def test_f4_full_history_cap_constant_set(fresh_repo: Path) -> None:
    """F4 safety valve: the FULL_HISTORY_CAP constant exists and bounds
    the git log scan. Sanity check on the constant rather than
    constructing a 2000+-commit fixture (too slow for CI).

    The actual scan-bound behavior is verified indirectly: F4 closure
    doc note in .governance/README.md + readability of the constant
    in the script. If a future change unbounds the scan, this test
    would still pass — it's a wired-up signal, not a behavioral guard.
    Behavioral coverage of the cap would require a 2000+ commit
    fixture, deferred."""
    import importlib
    import scripts.check_codex_cadence as cadence_mod  # noqa: WPS433
    importlib.reload(cadence_mod)
    assert hasattr(cadence_mod, "FULL_HISTORY_CAP")
    assert cadence_mod.FULL_HISTORY_CAP >= 100  # any reasonable bound
    assert cadence_mod.FULL_HISTORY_CAP <= 100000
