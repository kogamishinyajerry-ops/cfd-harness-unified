"""Tests for tools/cwos_event.py + tools/cwos_status.py."""
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


def test_cwos_event_rejects_pass_without_evidence(repo_root: Path, repo_env, tmp_path: Path):
    """PASS without evidence must be refused."""
    # point EVENTS at a temp path so we do not pollute the real log
    script = repo_root / "tools" / "cwos_event.py"
    code = (
        "import sys, importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('cwos_event', r'{script}')\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "m.EVENTS_PATH = __import__('pathlib').Path(r'%s')\n"
        "sys.argv = ['cwos_event.py', '--agent', 'tester', '--task-id', 'X', '--status', 'PASS', '--summary', 'nope']\n"
        "raise SystemExit(m.main())\n"
    ) % str(tmp_path / "ev.jsonl")
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=repo_env)
    assert res.returncode != 0, "PASS without --evidence must fail"


def test_cwos_status_writes_project_status_json(repo_root: Path, repo_env):
    res = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "cwos_status.py")],
        capture_output=True, text=True, env=repo_env, cwd=str(repo_root),
    )
    assert res.returncode == 0, res.stderr
    out = repo_root / "docs" / "status" / "project_status.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert "overall_status" in data
    assert "phase" in data
    assert "tasks" in data
    assert "trust_reports" in data


def test_cwos_status_counts_mocked_solver_report(repo_root: Path, repo_env):
    # generate sample trust_report
    from cfdtrust.cli import cmd_report
    case = repo_root / "cases" / "flat_plate_rans_sst"
    assert cmd_report(str(case)) == 0
    # re-run aggregator
    res = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "cwos_status.py")],
        capture_output=True, text=True, env=repo_env, cwd=str(repo_root),
    )
    assert res.returncode == 0, res.stderr
    data = json.loads((repo_root / "docs" / "status" / "project_status.json").read_text())
    metrics = data["metrics"]
    assert metrics["trust_reports_found"] >= 1
    assert metrics["mocked_solver_reports"] >= 1


def test_cwos_status_flags_pass_without_evidence(repo_root: Path, repo_env, tmp_path: Path):
    """If an event marks PASS without evidence (legacy / hand-edited log), cwos_status must surface it."""
    # write a temp events file with a bogus PASS-no-evidence event,
    # then call the aggregator's event_summary via import.
    import importlib.util

    spec = importlib.util.spec_from_file_location("cwos_status", str(repo_root / "tools" / "cwos_status.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    bogus = [{"agent": "x", "task_id": "Y", "status": "PASS", "summary": "no evidence", "evidence": []}]
    summary = mod.event_summary(bogus)
    assert len(summary["pass_without_evidence"]) == 1


def test_derive_phase_picks_latest_pass_task_id_prefix(repo_root: Path):
    """Cockpit fix (project-governor R25): phase must auto-derive from
    the latest PASS event task_id, not be hard-coded to 'Phase 0 — ...'.
    Otherwise the dashboard lies — a project that has shipped M9.2 still
    shows Phase 0 + the M9.2-completed banner would have to be hand-written.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("cwos_status", str(repo_root / "tools" / "cwos_status.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

    # 1. Empty events → Phase 0 (default)
    assert mod.derive_phase([]) == "Phase 0 — Project Operating System + Trust Harness Scaffold"

    # 2. Only FAIL events → still Phase 0 (PASS is required to advance)
    only_fail = [{"task_id": "M92-X", "status": "FAIL"}]
    assert "Phase 0" in mod.derive_phase(only_fail)

    # 3. Latest PASS is M9.2 → Phase 1 (M9.2 banner)
    m92_pass = [
        {"task_id": "M4-MESH-CONTRACT", "status": "PASS"},
        {"task_id": "M92-CHANNEL-CONVERGE", "status": "PASS"},
    ]
    label = mod.derive_phase(m92_pass)
    assert "Phase 1" in label and "M9.2" in label, label

    # 4. Latest PASS is M9.1 → Phase 1 with M9.1 banner (not M9.2 since M91 < M92 in event log)
    m91_pass = [
        {"task_id": "M91-CHANNEL-NASA-REFERENCE", "status": "PASS"},
    ]
    assert "Phase 1" in mod.derive_phase(m91_pass)
    assert "M9.1" in mod.derive_phase(m91_pass)

    # 5. Latest PASS prefix order matters: M92 must beat M9 (longer prefix first)
    m9_then_m92 = [
        {"task_id": "M9-CHANNEL-SCAFFOLD", "status": "PASS"},
        {"task_id": "M92-CHANNEL-CONVERGE", "status": "PASS"},
    ]
    assert "M9.2" in mod.derive_phase(m9_then_m92), "M92 must win over M9 prefix"


def test_derive_phase_used_by_main_aggregator(repo_root: Path, repo_env):
    """Integration: the production cwos_status.py CLI must write the
    derived phase into project_status.json, not the legacy hard-coded value.
    """
    res = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "cwos_status.py")],
        capture_output=True, text=True, env=repo_env, cwd=str(repo_root),
    )
    assert res.returncode == 0, res.stderr
    data = json.loads((repo_root / "docs" / "status" / "project_status.json").read_text())
    phase = data.get("phase", "")
    # Repo has M9.2 PASS event landed → must NOT be raw 'Phase 0 — ...'
    assert phase != "Phase 0 — Project Operating System + Trust Harness Scaffold", (
        f"phase still hard-coded; got {phase!r}"
    )
    assert "Phase 1" in phase, f"expected Phase 1 once M9.x PASS exists; got {phase!r}"
