"""Tests for tools/cwos_render_dashboard.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def repo_env(repo_root: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    return env


def _refresh_status(repo_root: Path, env) -> None:
    res = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "cwos_status.py")],
        capture_output=True, text=True, env=env, cwd=str(repo_root),
    )
    assert res.returncode == 0, res.stderr


def _render(repo_root: Path, env) -> None:
    res = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "cwos_render_dashboard.py")],
        capture_output=True, text=True, env=env, cwd=str(repo_root),
    )
    assert res.returncode == 0, res.stderr


REQUIRED_SECTIONS = (
    "## Overall Status:",
    "## Phase Progress",
    "## Trust Loop Status",
    "## Agent Matrix",
    "## Blockers",
    "## Bright Spots",
    "## Decisions Needed",
    "## Integrity Checks",
    "## Next Best Actions",
)


def test_cockpit_files_are_generated(repo_root: Path, repo_env):
    _refresh_status(repo_root, repo_env)
    _render(repo_root, repo_env)
    md = (repo_root / "docs" / "status" / "COCKPIT.md").read_text()
    html = (repo_root / "docs" / "status" / "COCKPIT.html").read_text()
    assert md.startswith("# AI-CFD-V2")
    assert "<html" in html.lower()


def test_cockpit_contains_required_sections(repo_root: Path, repo_env):
    _refresh_status(repo_root, repo_env)
    _render(repo_root, repo_env)
    md = (repo_root / "docs" / "status" / "COCKPIT.md").read_text()
    missing = [s for s in REQUIRED_SECTIONS if s not in md]
    assert not missing, f"Cockpit missing sections: {missing}"


def test_cockpit_shows_mocked_when_report_is_mocked(repo_root: Path, repo_env):
    # ensure a mocked trust_report exists
    from cfdtrust.cli import cmd_report
    case = repo_root / "cases" / "flat_plate_rans_sst"
    assert cmd_report(str(case)) == 0
    _refresh_status(repo_root, repo_env)
    _render(repo_root, repo_env)
    md = (repo_root / "docs" / "status" / "COCKPIT.md").read_text()
    assert "mocked" in md.lower(), "MOCKED status must be visible in the cockpit"


def test_status_json_has_zero_pass_without_evidence_after_bootstrap(repo_root: Path, repo_env):
    """The bootstrap event log must not contain PASS events without evidence by accident."""
    _refresh_status(repo_root, repo_env)
    data = json.loads((repo_root / "docs" / "status" / "project_status.json").read_text())
    assert data["events"]["pass_without_evidence"] == [], (
        "Bootstrap log has PASS-without-evidence events. Each must be removed or have evidence."
    )
