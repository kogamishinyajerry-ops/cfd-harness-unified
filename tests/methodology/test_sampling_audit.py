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
