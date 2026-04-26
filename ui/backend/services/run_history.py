"""Run history service · M3 · Workbench Closed-Loop main-line.

Filesystem layout (written by ``RealSolverDriver``):

    reports/
      {case_id}/
        runs/
          {run_id}/
            measurement.yaml   — key_quantities + residuals (numeric only)
            verdict.json       — pass/fail + exit_code + summary
            summary.json       — task spec excerpt + start/end timestamps

Public:
    write_run_artifacts(...)   → called by RealSolverDriver post-execute
    list_runs(case_id)         → newest-first list of RunSummaryEntry
    get_run_detail(case_id, run_id) → full RunDetail or raises FileNotFoundError
    new_run_id()               → filesystem-safe ISO-like timestamp string
    run_dir(case_id, run_id)   → Path resolver for callers that need to
                                 stage extra artifacts under the same dir
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from ui.backend.schemas.run_history import RunDetail, RunSummaryEntry


# Repo root resolution: this file lives at
# ui/backend/services/run_history.py — parents[3] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_ROOT = REPO_ROOT / "reports"


# Filesystem-safe segment guard. Same alphabet case_drafts / wizard accept.
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_\-:T.Z]+$")


def _safe_segment(s: str, kind: str) -> str:
    if not _SAFE_SEGMENT_RE.match(s):
        raise ValueError(f"unsafe {kind}: {s!r}")
    return s


def new_run_id() -> str:
    """ISO-8601 UTC timestamp with colons replaced by dashes (filesystem-safe).

    Example: ``2026-04-26T03-12-45Z``. Microseconds dropped — second-level
    granularity is plenty for wall-clock human-distinguishable runs."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z").replace(":", "-")


def run_dir(case_id: str, run_id: str, *, root: Path | None = None) -> Path:
    """Return the canonical artifact dir for a (case_id, run_id) pair.

    `root` override exists primarily for tests that want to write into
    tmp_path. In production, the default `RUNS_ROOT` is used.
    """
    base = (root or RUNS_ROOT) / _safe_segment(case_id, "case_id")
    return base / "runs" / _safe_segment(run_id, "run_id")


def _task_spec_to_excerpt(task_spec: Any) -> dict[str, Any]:
    """Pluck just the params + identifiers from a TaskSpec so we can show
    them in a row of the run-history table without re-reading the source
    YAML. Stays defensive: if task_spec is None or missing fields we
    return what we can. Numeric Re/Ra/Re_tau/Ma get top billing."""
    if task_spec is None:
        return {}
    excerpt: dict[str, Any] = {}
    for key in ("name", "Re", "Ra", "Re_tau", "Ma"):
        if hasattr(task_spec, key):
            value = getattr(task_spec, key)
            if value is not None:
                excerpt[key] = value
    # Enums → strings so JSON-friendly downstream.
    for key in ("geometry_type", "flow_type", "steady_state", "compressibility"):
        if hasattr(task_spec, key):
            value = getattr(task_spec, key)
            if value is None:
                continue
            excerpt[key] = getattr(value, "value", str(value))
    return excerpt


def _coerce_float_dict(d: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in (d or {}).items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def write_run_artifacts(
    *,
    case_id: str,
    run_id: str,
    started_at: datetime,
    task_spec: Any,
    source_origin: str,
    success: bool,
    exit_code: int,
    verdict_summary: str,
    duration_s: float,
    key_quantities: dict[str, Any] | None,
    residuals: dict[str, Any] | None,
    error_message: str | None = None,
    root: Path | None = None,
) -> Path:
    """Write the three per-run artifact files. Idempotent: overwrites any
    existing files for the same (case_id, run_id). Returns the directory
    path. Caller (RealSolverDriver) is responsible for picking a unique
    run_id via ``new_run_id()`` so collisions don't happen in practice."""
    target = run_dir(case_id, run_id, root=root)
    target.mkdir(parents=True, exist_ok=True)

    ended_at = started_at + timedelta(seconds=max(duration_s, 0.0))

    measurement_doc = {
        "case_id": case_id,
        "run_id": run_id,
        "key_quantities": dict(key_quantities or {}),
        "residuals": _coerce_float_dict(residuals),
    }
    (target / "measurement.yaml").write_text(
        yaml.safe_dump(measurement_doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    verdict_doc = {
        "case_id": case_id,
        "run_id": run_id,
        "success": success,
        "exit_code": exit_code,
        "execution_time_s": duration_s,
        "verdict_summary": verdict_summary,
        "error_message": error_message,
    }
    (target / "verdict.json").write_text(
        json.dumps(verdict_doc, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_doc = {
        "case_id": case_id,
        "run_id": run_id,
        "started_at": started_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_at": ended_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "duration_s": duration_s,
        "source_origin": source_origin,
        "task_spec": _task_spec_to_excerpt(task_spec),
    }
    (target / "summary.json").write_text(
        json.dumps(summary_doc, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def list_runs(case_id: str, *, root: Path | None = None) -> list[RunSummaryEntry]:
    """Newest-first list of runs for a case_id. Silently skips dirs that
    are missing summary.json or verdict.json (partial / in-progress
    runs)."""
    case_runs_root = (root or RUNS_ROOT) / _safe_segment(case_id, "case_id") / "runs"
    if not case_runs_root.exists():
        return []
    entries: list[RunSummaryEntry] = []
    for run_dir_path in sorted(case_runs_root.iterdir(), reverse=True):
        if not run_dir_path.is_dir():
            continue
        summary_path = run_dir_path / "summary.json"
        verdict_path = run_dir_path / "verdict.json"
        if not (summary_path.exists() and verdict_path.exists()):
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        entries.append(
            RunSummaryEntry(
                case_id=case_id,
                run_id=run_dir_path.name,
                started_at=summary.get("started_at", ""),
                duration_s=float(summary.get("duration_s", 0.0)),
                success=bool(verdict.get("success", False)),
                exit_code=int(verdict.get("exit_code", -1)),
                verdict_summary=str(verdict.get("verdict_summary", "")),
                task_spec_excerpt=summary.get("task_spec", {}) or {},
            )
        )
    return entries


def get_run_detail(case_id: str, run_id: str, *, root: Path | None = None) -> RunDetail:
    """Read the three artifacts and return a fully-populated RunDetail.

    Raises FileNotFoundError if the run dir doesn't exist or is missing
    any of the three required artifact files."""
    target = run_dir(case_id, run_id, root=root)
    if not target.exists():
        raise FileNotFoundError(f"no run dir at {target}")

    measurement_path = target / "measurement.yaml"
    verdict_path = target / "verdict.json"
    summary_path = target / "summary.json"
    if not (measurement_path.exists() and verdict_path.exists() and summary_path.exists()):
        raise FileNotFoundError(f"run dir at {target} missing one of measurement/verdict/summary")

    measurement = yaml.safe_load(measurement_path.read_text(encoding="utf-8")) or {}
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    return RunDetail(
        case_id=case_id,
        run_id=run_id,
        started_at=summary.get("started_at", ""),
        ended_at=summary.get("ended_at"),
        duration_s=float(summary.get("duration_s", 0.0)),
        success=bool(verdict.get("success", False)),
        exit_code=int(verdict.get("exit_code", -1)),
        verdict_summary=str(verdict.get("verdict_summary", "")),
        error_message=verdict.get("error_message"),
        source_origin=str(summary.get("source_origin", "unknown")),
        task_spec=summary.get("task_spec", {}) or {},
        key_quantities=measurement.get("key_quantities", {}) or {},
        residuals=measurement.get("residuals", {}) or {},
    )
