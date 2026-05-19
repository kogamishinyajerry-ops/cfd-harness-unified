"""Residual series for the V4 Post mode chart (R6 · Codex-driven).

Returns a structured JSON-friendly payload the frontend can render as
a log-decay chart with stable colors, instead of the server-rendered
PNG used by ``residual-history.png``.

Two source modes (best-first):
    log      — parse log.simpleFoam / log.icoFoam (true iteration series)
    runs     — fall back to RunSummary final residuals across run-history
               (point-per-run series; the only thing available for curated
               cases like LDC that don't carry an OpenFOAM log on disk)
    empty    — case has no runs at all

The frontend distinguishes via the ``source`` field and renders different
x-axis labels (iteration count vs run timestamp) but the same chart shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ui.backend.services.case_scaffold.template_clone import IMPORTED_DIR
from ui.backend.services.case_visualize.residual_chart import (
    ResidualChartError,
    _parse_log,
)
from ui.backend.services.run_history import (
    RUNS_ROOT,
    get_run_detail,
    list_runs,
)


@dataclass
class ResidualSeriesPoint:
    x: float
    y: float


@dataclass
class ResidualSeriesPayload:
    case_id: str
    source: Literal["log", "runs", "empty"]
    series: dict[str, list[ResidualSeriesPoint]]
    sample_count: int
    latest_run_id: str | None
    target_floor: float = 1.0e-6
    achieved: bool = False
    note: str = ""


_TARGET_FLOOR = 1.0e-6


# Order matters: solver_runner.py always writes log.icoFoam (see
# solver_runner.py:580); putting it first short-circuits the common
# case. The other entries cover forward-compat for future solvers.
_LOG_NAMES: tuple[str, ...] = (
    "log.icoFoam",
    "log.simpleFoam",
    "log.pimpleFoam",
    "log.rhoSimpleFoam",
    "log.buoyantSimpleFoam",
)


def _parse_log_file(log_path: Path) -> dict[str, list[ResidualSeriesPoint]] | None:
    """Read + parse a single solver log file. Returns the structured
    series, or None when the file can't be opened / has no parseable
    residual lines."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        parsed = _parse_log(text)
    except ResidualChartError:
        return None
    out: dict[str, list[ResidualSeriesPoint]] = {}
    for name, points in parsed.items():
        if not points:
            continue
        out[name] = [
            ResidualSeriesPoint(x=float(step), y=float(res))
            for step, res in points
        ]
    return out or None


def _try_log(
    case_id: str,
    runs_root: Path | None,
    imported_root: Path | None = None,
) -> dict[str, list[ResidualSeriesPoint]] | None:
    """Look for a solver log file and parse it. Returns None when none
    found; the caller falls through to the run-history series.

    Codex R6 finding M-2: real solver runs persist the log in the
    case host directory (``imported/{case_id}/log.{solver}``), not
    inside the per-run report dir. We search BOTH locations:

      1. ``imported/{case_id}/log.*``       — newest persistent log
      2. ``reports/{case_id}/runs/{run_id}/log.*`` — when a future
         pipeline starts archiving logs to the run dir, this path
         picks them up newest-first automatically.

    Order: imported root first (covers the current solver_runner
    contract); reports root as fallback for forward-compat.
    """
    # 1. Per-case imported log (current solver_runner behaviour).
    imported = (imported_root or IMPORTED_DIR) / case_id
    if imported.is_dir():
        for log_name in _LOG_NAMES:
            log_path = imported / log_name
            if log_path.is_file():
                parsed = _parse_log_file(log_path)
                if parsed:
                    return parsed

    # 2. Per-run report log (future forward-compat).
    root = runs_root or RUNS_ROOT
    case_runs = root / case_id / "runs"
    if case_runs.is_dir():
        for run_dir in sorted(case_runs.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            for log_name in _LOG_NAMES:
                log_path = run_dir / log_name
                if log_path.is_file():
                    parsed = _parse_log_file(log_path)
                    if parsed:
                        return parsed

    return None


def _from_runs(case_id: str, runs_root: Path | None = None) -> tuple[
    dict[str, list[ResidualSeriesPoint]], str | None
]:
    """Build series from the final residual at each run in run-history.
    Newest-first index becomes the x axis (run 1 = oldest, run N = newest)
    so the chart reads left→right as time-progression."""
    try:
        runs = list_runs(case_id, root=runs_root)
    except ValueError:
        return {}, None
    if not runs:
        return {}, None
    # Sort oldest → newest by started_at so x grows monotonically.
    ordered = sorted(runs, key=lambda r: r.started_at)
    series: dict[str, list[ResidualSeriesPoint]] = {}
    for idx, run in enumerate(ordered, start=1):
        try:
            detail = get_run_detail(case_id, run.run_id, root=runs_root)
        except (FileNotFoundError, ValueError):
            continue
        res = getattr(detail, "residuals", None) or {}
        for name, val in res.items():
            if not isinstance(val, (int, float)):
                continue
            if val <= 0 or not (val == val):  # NaN guard
                continue
            series.setdefault(name, []).append(
                ResidualSeriesPoint(x=float(idx), y=float(val))
            )
    latest_run_id = ordered[-1].run_id if ordered else None
    return series, latest_run_id


def build_residual_series(
    case_id: str,
    *,
    runs_root: Path | None = None,
    imported_root: Path | None = None,
) -> ResidualSeriesPayload:
    """Resolve the best-available residual series for ``case_id``."""
    # Best: log file
    log_series = _try_log(case_id, runs_root, imported_root)
    if log_series:
        sample_count = max(len(s) for s in log_series.values())
        latest_residuals = {
            name: pts[-1].y for name, pts in log_series.items() if pts
        }
        achieved = bool(latest_residuals) and all(
            v <= _TARGET_FLOOR for v in latest_residuals.values()
        )
        return ResidualSeriesPayload(
            case_id=case_id,
            source="log",
            series=log_series,
            sample_count=sample_count,
            latest_run_id=None,  # log is run-agnostic
            target_floor=_TARGET_FLOOR,
            achieved=achieved,
            note=(
                f"Parsed solver log · {sample_count} time-step samples · "
                f"target {_TARGET_FLOOR:.0e}"
            ),
        )

    # Fallback: run-history multi-point
    runs_series, latest_run = _from_runs(case_id, runs_root)
    if runs_series:
        sample_count = max(len(s) for s in runs_series.values())
        latest_residuals = {
            name: pts[-1].y for name, pts in runs_series.items() if pts
        }
        achieved = bool(latest_residuals) and all(
            v <= _TARGET_FLOOR for v in latest_residuals.values()
        )
        return ResidualSeriesPayload(
            case_id=case_id,
            source="runs",
            series=runs_series,
            sample_count=sample_count,
            latest_run_id=latest_run,
            target_floor=_TARGET_FLOOR,
            achieved=achieved,
            note=(
                f"Multi-run final residuals · {sample_count} runs · "
                f"no solver log on disk · target {_TARGET_FLOOR:.0e}"
            ),
        )

    # Empty
    return ResidualSeriesPayload(
        case_id=case_id,
        source="empty",
        series={},
        sample_count=0,
        latest_run_id=None,
        target_floor=_TARGET_FLOOR,
        achieved=False,
        note="No runs and no solver log on disk yet.",
    )
