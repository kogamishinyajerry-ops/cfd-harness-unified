"""Tests for §10.5 sampling-audit budget gate (PC-3 · DEC-V61-073 H3).

Covers:
  (a) under-cap path returns OK + exit 0
  (b) over-cap path returns EXCEEDS_BUDGET_CAP=<used>/<cap> + exit 2
  (c) all 7 §10.5.4a audit-required surfaces are detected by the grep list
      (smoke audit verifying surfaces 6+7 — correction_spec/ and
      .planning/case_profiles/ — both fire, per DEC-V61-073 PC-4 acceptance).

The script lives at `scripts/methodology/sampling_audit.py`. We import via
the `scripts.methodology.sampling_audit` namespace path.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest import mock

import pytest

# Ensure repo root on sys.path so `scripts.methodology.sampling_audit` imports.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.methodology import sampling_audit as sa  # noqa: E402


# -----------------------------------------------------------------------------
# (c) Surface detection — smoke audit covering all 7 §10.5.4a surfaces.
# -----------------------------------------------------------------------------


SURFACE_FIXTURES: dict[str, str] = {
    "1.FoamAgentExecutor_call_sites": (
        # Adapter caller in a non-trust-core module.
        "diff --git a/ui/backend/services/runner.py b/ui/backend/services/runner.py\n"
        "+++ b/ui/backend/services/runner.py\n"
        "+    result = FoamAgentExecutor.execute(spec, mode='real')\n"
    ),
    "2.Docker_subprocess_reachability": (
        "diff --git a/scripts/runner.py b/scripts/runner.py\n"
        "+++ b/scripts/runner.py\n"
        "+    subprocess.run(['docker', 'run', 'foam-agent', '--mount', src])\n"
    ),
    "3.api_route_registration": (
        "diff --git a/ui/backend/routes/cases.py b/ui/backend/routes/cases.py\n"
        "+++ b/ui/backend/routes/cases.py\n"
        "+@router.post('/api/cases/{case_id}/runs')\n"
        "+def trigger_run(case_id: str): ...\n"
    ),
    "4.reports_durable_persistence": (
        "diff --git a/src/persistence.py b/src/persistence.py\n"
        "+++ b/reports/new_case/run_history.json\n"
        "+    Path('reports/{case_id}/runs.json').write_text(payload)\n"
    ),
    "5.user_drafts_to_TaskSpec": (
        "diff --git a/src/draft_loader.py b/src/draft_loader.py\n"
        "+++ b/src/draft_loader.py\n"
        "+    spec = TaskSpec.from_yaml(load(user_drafts/draft_001.yaml))\n"
    ),
    "6.correction_spec_write_paths": (
        "diff --git a/src/recorder.py b/src/recorder.py\n"
        "+++ b/reports/elbow_duct/correction_specs/spec_v1.json\n"
        "+    Path('reports/elbow_duct/correction_specs/spec_v1.json').write_text(j)\n"
    ),
    "7.case_profiles_write_paths": (
        "diff --git a/.planning/case_profiles/turbulent_flat_plate.yaml "
        "b/.planning/case_profiles/turbulent_flat_plate.yaml\n"
        "+++ b/.planning/case_profiles/turbulent_flat_plate.yaml\n"
        "+tolerance_policy:\n"
        "+  observables: [Cf, U_plus]\n"
    ),
}


def test_detect_surfaces_covers_all_seven_audit_required_surfaces():
    """Smoke audit · DEC-V61-073 PC-4 acceptance.

    Every fixture diff must trigger exactly the surface it represents.
    Surfaces 6+7 are the new ones added by DEC-V61-073 A4; this test
    is the smoke audit verifying they fire.
    """
    expected_labels = {label for label, _ in sa.AUDIT_REQUIRED_SURFACES}
    assert len(expected_labels) == 7, (
        f"§10.5.4a must enumerate exactly 7 surfaces post-DEC-V61-073, "
        f"got {len(expected_labels)}"
    )

    # Each fixture must trigger at least its named surface.
    for label, diff in SURFACE_FIXTURES.items():
        matched = sa.detect_surfaces(diff)
        assert label in matched, (
            f"Surface '{label}' fixture failed to trigger; matched={matched}"
        )

    # New surfaces 6+7 must be reachable specifically.
    new_six = sa.detect_surfaces(SURFACE_FIXTURES["6.correction_spec_write_paths"])
    assert "6.correction_spec_write_paths" in new_six

    new_seven = sa.detect_surfaces(SURFACE_FIXTURES["7.case_profiles_write_paths"])
    assert "7.case_profiles_write_paths" in new_seven


def test_quiet_diff_flags_no_surfaces():
    """Sanity inverse: a doc-only diff touching no audit surfaces returns []."""
    quiet = (
        "diff --git a/README.md b/README.md\n"
        "+++ b/README.md\n"
        "+## new heading\n"
        "+some prose update\n"
    )
    assert sa.detect_surfaces(quiet) == []


# -----------------------------------------------------------------------------
# (a) + (b) Budget cap: under-cap OK, over-cap EXCEEDS_BUDGET_CAP=<u>/<c>.
# -----------------------------------------------------------------------------


def _make_window(estimated: int, cap: int = sa.DEFAULT_CAP_TOKENS) -> sa.AuditWindow:
    return sa.AuditWindow(
        git_range="abc..HEAD",
        commits=["abc1234"],
        non_trust_core_commits=["abc1234"],
        diff_chars=estimated * 4,
        estimated_tokens=estimated,
        cap=cap,
    )


def test_under_cap_window_returns_ok_verdict():
    """(a) Estimate ≤ cap → verdict OK, no abort."""
    window = _make_window(estimated=50_000, cap=100_000)
    assert window.verdict == "OK"
    assert window.message == "OK=50000/100000"


def test_over_cap_window_emits_exceeds_budget_cap_message():
    """(b) Estimate > cap → verdict EXCEEDS_BUDGET_CAP and exact format
    `EXCEEDS_BUDGET_CAP=<used>/<cap>` per DEC-V61-073 H3 contract."""
    window = _make_window(estimated=120_000, cap=100_000)
    assert window.verdict == "EXCEEDS_BUDGET_CAP"
    assert window.message == "EXCEEDS_BUDGET_CAP=120000/100000"


def test_main_exits_2_when_over_cap(monkeypatch, capsys):
    """End-to-end: main() returns exit code 2 when build_audit_window
    returns an EXCEEDS_BUDGET_CAP verdict, and prints the contract message."""
    over_cap_window = _make_window(estimated=200_000, cap=100_000)
    monkeypatch.setattr(sa, "build_audit_window", lambda **_: over_cap_window)

    rc = sa.main(["--cap", "100000"])

    captured = capsys.readouterr().out
    assert rc == 2
    assert "EXCEEDS_BUDGET_CAP=200000/100000" in captured


def test_main_exits_0_when_under_cap(monkeypatch, capsys):
    """End-to-end: main() returns exit code 0 when verdict is OK."""
    under_cap_window = _make_window(estimated=42_000, cap=100_000)
    monkeypatch.setattr(sa, "build_audit_window", lambda **_: under_cap_window)

    rc = sa.main(["--cap", "100000"])

    captured = capsys.readouterr().out
    assert rc == 0
    assert "OK=42000/100000" in captured
    assert "verdict=OK" in captured


def test_estimate_tokens_handles_empty_input():
    """Boundary: empty text estimates 0 tokens (no crash from char-fallback)."""
    assert sa.estimate_tokens("") == 0


def test_estimate_tokens_grows_monotonically_with_input_size():
    """Boundary: longer text estimates more tokens (regression guard against
    a fallback bug that would silently truncate)."""
    short_estimate = sa.estimate_tokens("hello world")
    long_estimate = sa.estimate_tokens("hello world " * 1000)
    assert long_estimate > short_estimate


# -----------------------------------------------------------------------------
# Codex PC-3 R1 follow-ups: mixed commits, JSON contract, cap raise-only,
# auto-range robustness, regex tightening (false-pos / false-neg).
# -----------------------------------------------------------------------------


def test_subprocess_check_call_triggers_surface_2():
    """Codex R1 false-negative: subprocess.check_call must trigger surface 2."""
    diff = (
        "diff --git a/scripts/foo.py b/scripts/foo.py\n"
        "+++ b/scripts/foo.py\n"
        "+    subprocess.check_call(['echo', 'hi'])\n"
    )
    assert "2.Docker_subprocess_reachability" in sa.detect_surfaces(diff)


def test_doc_only_routes_diff_does_not_trigger_surface_3():
    """Codex R1 false-positive: a doc-only edit in ui/backend/routes/ MUST NOT
    flag surface 3 by diff-header alone. Only body-level route signals trigger."""
    doc_only_diff = (
        "diff --git a/ui/backend/routes/README.md b/ui/backend/routes/README.md\n"
        "+++ b/ui/backend/routes/README.md\n"
        "+## Updated routing notes\n"
        "+(no code change)\n"
    )
    matched = sa.detect_surfaces(doc_only_diff)
    assert "3.api_route_registration" not in matched


def test_real_route_decorator_still_triggers_surface_3():
    """Inverse of the false-positive guard: a real route decorator must
    still trigger surface 3 even without the diff-header signal."""
    code_diff = (
        "diff --git a/src/server/api.py b/src/server/api.py\n"
        "+++ b/src/server/api.py\n"
        "+@router.post('/api/things')\n"
        "+def create_thing(): ...\n"
    )
    assert "3.api_route_registration" in sa.detect_surfaces(code_diff)


# --- mixed-commit handling (R1 HIGH finding) ---


def test_mixed_commit_classification_returns_both_flags():
    """Mixed commit (touches both layers) returns (True, True), not
    a per-commit drop. Codex PC-3 R1 HIGH fix."""

    def fake_files(sha, cwd=None):
        return [
            "src/audit_package/manifest.py",  # trust-core
            "ui/backend/services/runner.py",   # non-trust-core
        ]

    with mock.patch.object(sa, "_commit_touched_files", side_effect=fake_files):
        touches_ntc, touches_tc = sa._commit_classification("abc1234")
    assert touches_ntc is True
    assert touches_tc is True


def test_pure_trust_core_commit_excluded_from_audit():
    """Pure trust-core commit: classification returns (False, True);
    build_audit_window must skip it entirely."""

    def fake_files(sha, cwd=None):
        return ["src/audit_package/manifest.py", "src/auto_verifier/runner.py"]

    with mock.patch.object(sa, "_commit_touched_files", side_effect=fake_files):
        touches_ntc, touches_tc = sa._commit_classification("trust1")
    assert touches_ntc is False
    assert touches_tc is True


def test_is_trust_core_path_recognizes_all_five_modules():
    """Trust-core file detection must cover all 5 paths from §10."""
    assert sa._is_trust_core_path("src/gold_standards/foo.yaml")
    assert sa._is_trust_core_path("src/auto_verifier/x.py")
    assert sa._is_trust_core_path("src/convergence_attestor.py")
    assert sa._is_trust_core_path("src/audit_package/manifest.py")
    assert sa._is_trust_core_path("src/foam_agent_adapter.py")
    # Negative: similar-but-not paths must not match.
    assert not sa._is_trust_core_path("src/audit_package_helper.py")
    assert not sa._is_trust_core_path("docs/specs/EXECUTOR_ABSTRACTION.md")


# --- JSON contract: EXCEEDS_BUDGET_CAP must reach a grepable surface ---


def test_main_json_mode_emits_contract_message_to_stderr_when_over_cap(
    monkeypatch, capsys
):
    """Codex R1 MED-3: in --json mode, the literal
    'EXCEEDS_BUDGET_CAP=<used>/<cap>' contract message must appear on stderr
    so log scrapers / CI gates can grep it without parsing JSON."""
    over_cap_window = _make_window(estimated=180_000, cap=100_000)
    monkeypatch.setattr(sa, "build_audit_window", lambda **_: over_cap_window)

    rc = sa.main(["--json"])

    captured = capsys.readouterr()
    assert rc == 2
    assert "EXCEEDS_BUDGET_CAP=180000/100000" in captured.err
    # JSON payload still on stdout, parseable.
    import json as _json

    payload = _json.loads(captured.out)
    assert payload["verdict"] == "EXCEEDS_BUDGET_CAP"
    assert payload["message"] == "EXCEEDS_BUDGET_CAP=180000/100000"


def test_main_json_mode_under_cap_does_not_emit_to_stderr(monkeypatch, capsys):
    """Inverse: under-cap JSON mode keeps stderr clean."""
    under_cap_window = _make_window(estimated=42_000, cap=100_000)
    monkeypatch.setattr(sa, "build_audit_window", lambda **_: under_cap_window)

    rc = sa.main(["--json"])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""


# --- cap raise-only enforcement (R1 LOW finding) ---


def test_cli_cap_below_default_is_rejected():
    """Codex R1 LOW: --cap below DEFAULT_CAP_TOKENS must be rejected."""
    cap, err = sa._resolve_and_validate_cap(50_000)
    assert err is not None
    assert "raise-only" in err
    # Default returned so the caller has a sane value if it ignores the error.
    assert cap == sa.DEFAULT_CAP_TOKENS


def test_env_cap_below_default_is_rejected(monkeypatch):
    """Codex R1 LOW: env var SAMPLING_AUDIT_CAP below default also rejected."""
    monkeypatch.setenv("SAMPLING_AUDIT_CAP", "10000")
    _, err = sa._resolve_and_validate_cap(None)
    assert err is not None
    assert "SAMPLING_AUDIT_CAP" in err


def test_cap_at_default_is_accepted():
    """The default itself is fine."""
    cap, err = sa._resolve_and_validate_cap(sa.DEFAULT_CAP_TOKENS)
    assert err is None
    assert cap == sa.DEFAULT_CAP_TOKENS


def test_cap_above_default_is_accepted():
    """Raising the cap is permitted."""
    cap, err = sa._resolve_and_validate_cap(250_000)
    assert err is None
    assert cap == 250_000


def test_main_exits_3_when_cap_is_lowered_below_default(capsys):
    """End-to-end: main exits with CAP_LOWER_REJECTED_EXIT (3) when --cap
    is below DEFAULT_CAP_TOKENS, and writes a clear error to stderr."""
    rc = sa.main(["--cap", "50000"])
    captured = capsys.readouterr()
    assert rc == sa.CAP_LOWER_REJECTED_EXIT == 3
    assert "raise-only" in captured.err


# --- auto-range robustness (R1 MED finding) ---


def test_resolve_default_range_falls_back_when_main_branch_absent(
    monkeypatch,
):
    """Codex R1 MED-1: if `git log ... main` raises (e.g. detached HEAD,
    worktree with no main ref), the resolver must fall back to HEAD walk
    and ultimately to a HEAD~N..HEAD or HEAD-only window — never crash."""
    import subprocess as _sp

    main_attempts: list[str] = []

    def fake_git(*args, cwd=None):
        # Simulate `git log <flags> main` failing; HEAD path succeeds with
        # no matches; rev-list HEAD reports 3 commits.
        if "log" in args and "main" in args:
            main_attempts.append("main")
            raise _sp.CalledProcessError(returncode=128, cmd=list(args))
        if "log" in args and "HEAD" in args:
            return ""  # no sampling-audit DEC ever recorded
        if args[:2] == ("rev-list", "--count"):
            return "3\n"
        return ""

    monkeypatch.setattr(sa, "_git", fake_git)

    git_range = sa._resolve_default_range()
    assert main_attempts == ["main"]
    # 3 commits total → HEAD~min(50, 2)..HEAD = HEAD~2..HEAD
    assert git_range == "HEAD~2..HEAD"


def test_resolve_default_range_uses_head_only_for_short_history(monkeypatch):
    """Codex R1 MED-1: shallow / single-commit repo doesn't crash; falls
    back to plain 'HEAD'."""
    import subprocess as _sp

    def fake_git(*args, cwd=None):
        if "log" in args:
            return ""
        if args[:2] == ("rev-list", "--count"):
            return "1\n"
        return ""

    monkeypatch.setattr(sa, "_git", fake_git)
    assert sa._resolve_default_range() == "HEAD"


def test_resolve_default_range_uses_dec_anchor_when_present(monkeypatch):
    """When a previous DEC-V61-*sampling.audit* commit exists, the resolver
    must pin the lower bound to that SHA."""

    def fake_last(cwd=None):
        return "deadbeefcafe"

    monkeypatch.setattr(sa, "_last_sampling_audit_sha", fake_last)
    assert sa._resolve_default_range() == "deadbeefcafe..HEAD"
