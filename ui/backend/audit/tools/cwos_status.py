#!/usr/bin/env python3
"""Aggregate .cwos/ + cases/ + tests/ into docs/status/project_status.json."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
CWOS = REPO_ROOT / ".cwos"
DOCS_STATUS = REPO_ROOT / "docs" / "status"
CASES_DIR = REPO_ROOT / "cases"

# Shared path-safety contract — single source of truth for evidence checks.
_PATHS_SPEC = importlib.util.spec_from_file_location(
    "cwos_paths", str(Path(__file__).resolve().parent / "cwos_paths.py")
)
cwos_paths = importlib.util.module_from_spec(_PATHS_SPEC)
_PATHS_SPEC.loader.exec_module(cwos_paths)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r") as f:
        return yaml.safe_load(f) or {}


def _safe_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r") as f:
        return json.load(f)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except FileNotFoundError:
        return None


def discover_trust_reports(
    cases_dir: Path | None = None,
    repo_root: Path | None = None,
) -> List[Dict[str, Any]]:
    cases = cases_dir if cases_dir is not None else CASES_DIR
    root = repo_root if repo_root is not None else REPO_ROOT
    found = []
    if not cases.exists():
        return found
    for case_dir in cases.iterdir():
        if not case_dir.is_dir():
            continue
        report_path = case_dir / "artifacts" / "trust_report.json"
        if report_path.exists():
            try:
                data = json.loads(report_path.read_text())
            except json.JSONDecodeError:
                continue
            try:
                rel = str(report_path.relative_to(root))
            except ValueError:
                rel = str(report_path)
            found.append({
                "case_id": data.get("case_id", case_dir.name),
                "path": rel,
                "overall_status": data.get("overall_status"),
                "solver_execution": data.get("solver_execution"),
                "validation_status": data.get("validation_status"),
            })
    return found


def compute_overall_status(
    *,
    real_reports: int,
    mocked_reports: int,
    pass_no_evidence: int,
    phantom_count: int,
    has_reports: bool,
) -> str:
    """
    Pure conditional ladder for the cockpit's overall_status.

    Extracted from main() so the RED-override semantics can be unit-tested
    directly (Red Team R4-F-01). The override rule is:
      - phantom_count > 0 OR pass_no_evidence > 0  =>  RED
      - real_reports > 0 and mocked_reports == 0   =>  GREEN
      - has no trust_reports yet                   =>  AMBER
      - otherwise                                  =>  AMBER

    Precedence is intentional: integrity failures (RED) trump everything,
    so a green-looking project with a single phantom event flips RED.
    """
    overall = "AMBER"
    if mocked_reports > 0 and real_reports == 0:
        overall = "AMBER"
    if real_reports > 0 and mocked_reports == 0:
        overall = "GREEN"
    if pass_no_evidence > 0:
        overall = "RED"
    if phantom_count > 0:
        overall = "RED"
    if not has_reports:
        overall = "AMBER"
        # Integrity overrides still win even when no reports exist.
        if pass_no_evidence > 0 or phantom_count > 0:
            overall = "RED"
    return overall


def latest_status_per_task(events: List[Dict[str, Any]]) -> Dict[str, str]:
    """Return {task_id: latest_event_status}. Later events in the log win."""
    out: Dict[str, str] = {}
    for e in events:
        tid = e.get("task_id")
        if not tid:
            continue
        st = e.get("status")
        if not st:
            continue
        out[tid] = st
    return out


# Phase name lookup: derived from latest PASS event task_id prefix.
# Order: longest prefix first so e.g. "M91" beats "M9".
_PHASE_PREFIXES = (
    ("M10",  "Phase 1 — Trust Harness + Three Validated Canonical Cases (M10 template advisor)"),
    ("M92",  "Phase 1 — Trust Harness + Three Validated Canonical Cases (M9.2 channel converged)"),
    ("M91",  "Phase 1 — Trust Harness + Three Validated Canonical Cases (M9.1 NASA reference wired)"),
    ("M9",   "Phase 1 — Trust Harness + Three Validated Canonical Cases (M9 channel scaffolded)"),
    ("M8",   "Phase 1 — Trust Harness Audit Layer (M8 derived consistency)"),
    ("M7",   "Phase 1 — Trust Harness Audit Layer (M7 BC value validation)"),
    ("M6",   "Phase 1 — Trust Harness Audit Layer (M6 real BC contract)"),
    ("M5",   "Phase 1 — Trust Harness Audit Layer (M5 real geometry contract)"),
    ("M4",   "Phase 1 — Trust Harness Audit Layer (M4 real mesh contract)"),
    ("PH1",  "Phase 1 — Trust Harness + Canonical Cases"),
    ("PH0",  "Phase 0 — Project Operating System + Trust Harness Scaffold"),
)


def derive_phase(events: List[Dict[str, Any]]) -> str:
    """Derive the cockpit phase label from the latest PASS event.

    Pre-fix the cockpit hard-coded "Phase 0 — ...", so even after M9.2
    landed and validated the channel against NASA DNS the dashboard
    still said Phase 0. Now it walks events backwards and picks the
    first PASS event whose task_id matches a known phase prefix.

    Falls back to Phase 0 only if no PASS events exist at all.
    """
    for e in reversed(events or []):
        if e.get("status") != "PASS":
            continue
        tid = (e.get("task_id") or "").upper()
        if not tid:
            continue
        for prefix, label in _PHASE_PREFIXES:
            if tid.startswith(prefix):
                return label
    return "Phase 0 — Project Operating System + Trust Harness Scaffold"


def task_summary(
    tasks_yaml: Dict[str, Any] | None,
    events: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Derive per-task status from the event log, not from tasks.yaml itself.

    tasks.yaml declares the task registry (intent + acceptance). Truth lives
    in .cwos/agent_events.jsonl. A task with no matching event defaults to
    QUEUED.
    """
    if not tasks_yaml:
        return {"total": 0, "by_status": {}, "tasks": []}
    tasks = tasks_yaml.get("tasks", [])
    latest = latest_status_per_task(events or [])
    by_status: Dict[str, int] = {}
    enriched = []
    for t in tasks:
        tid = t.get("task_id")
        derived = latest.get(tid, "QUEUED")
        by_status[derived] = by_status.get(derived, 0) + 1
        enriched.append({**t, "derived_status": derived})
    return {"total": len(tasks), "by_status": by_status, "tasks": enriched}


def event_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    pass_no_evidence = [
        e for e in events
        if e.get("status") == "PASS" and not e.get("evidence")
    ]
    return {
        "count": len(events),
        "latest": events[-5:] if events else [],
        "pass_without_evidence": pass_no_evidence,
    }


def main(
    argv: list[str] | None = None,
    *,
    cwos_dir: Path | None = None,
    cases_dir: Path | None = None,
    output_path: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    """Aggregate state into a project_status.json file.

    All path arguments default to module-level constants for the production
    no-arg call (`python tools/cwos_status.py`). Tests inject tmp paths to
    exercise the overall_status RED override and similar policy.
    """
    cwos = cwos_dir if cwos_dir is not None else CWOS
    cases = cases_dir if cases_dir is not None else CASES_DIR
    out = output_path if output_path is not None else (DOCS_STATUS / "project_status.json")
    root = repo_root if repo_root is not None else REPO_ROOT

    tasks = _safe_yaml(cwos / "tasks.yaml")
    events = _read_jsonl(cwos / "agent_events.jsonl")
    decisions = _safe_yaml(cwos / "decisions.yaml")
    blockers = _safe_yaml(cwos / "blockers.yaml")
    metrics_in = _safe_json(cwos / "metrics.json") or {}

    reports = discover_trust_reports(cases_dir=cases, repo_root=root)
    mocked = sum(1 for r in reports if r.get("solver_execution") == "mocked")
    real = sum(1 for r in reports if r.get("solver_execution") == "real")

    task_sum = task_summary(tasks, events)
    ev_sum = event_summary(events)

    phantom_count = cwos_paths.count_phantom_pass_events(
        cwos / "agent_events.jsonl", root
    )

    blocked_count = len((blockers or {}).get("blockers", []))
    completed = task_sum["by_status"].get("PASS", 0)

    overall = compute_overall_status(
        real_reports=real,
        mocked_reports=mocked,
        pass_no_evidence=len(ev_sum["pass_without_evidence"]),
        phantom_count=phantom_count,
        has_reports=bool(reports),
    )

    status = {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "repo_root": str(REPO_ROOT),
        "git": {
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "head": _git("rev-parse", "HEAD"),
            "dirty": _git("status", "--porcelain") not in (None, ""),
        },
        "overall_status": overall,
        "phase": derive_phase(events),
        "tasks": task_sum,
        "events": ev_sum,
        "decisions": (decisions or {}).get("decisions", []),
        "blockers": (blockers or {}).get("blockers", []),
        "trust_reports": reports,
        "metrics": {
            **metrics_in,
            "generated_at": utc_now_iso(),
            "total_tasks": task_sum["total"],
            "completed_tasks": completed,
            "blocked_tasks": blocked_count,
            "trust_reports_found": len(reports),
            "mocked_solver_reports": mocked,
            "real_solver_reports": real,
            "phantom_evidence_pass_events": phantom_count,
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, indent=2))
    try:
        display = out.relative_to(root)
    except ValueError:
        display = out
    print(f"[cwos_status] wrote {display} (overall={overall})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
