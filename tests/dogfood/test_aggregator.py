"""Tests for scripts/dogfood/aggregator.py — severity classification + report rendering."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dogfood.aggregator import (
    BacklogItem,
    RunSummary,
    _scan_v130_violations,
    aggregate,
    render_report,
)
from scripts.dogfood.friction_log import FrictionLog


def _make_run_dir(
    tmp_path: Path,
    *,
    run_id: str,
    case_id: str = "naca0012",
    persona: str = "novice",
    model_id: str = "claude-sonnet-4-6",
) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_minimal(
    run_dir: Path,
    *,
    events: list[dict] | None = None,
    result: dict | None = None,
    spec: dict | None = None,
) -> None:
    log_path = run_dir / "friction_log.jsonl"
    log = FrictionLog(
        path=log_path,
        run_id=run_dir.name,
        case_id=(spec or {}).get("case_id", "naca0012"),
        persona=(spec or {}).get("persona", "novice"),
        model_id=(spec or {}).get("model_id", "claude-sonnet-4-6"),
    )
    for ev in events or []:
        log.emit(ev.pop("event_type"), **ev)
    log.close()
    (run_dir / "result.json").write_text(json.dumps(result or {}), encoding="utf-8")
    (run_dir / "spec.json").write_text(json.dumps(spec or {}), encoding="utf-8")


# ---------------------------------------------------------------------------
# V130 violation scanner
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rationale",
    [
        "Applying because the AI told me to",
        "the advisor said so, applying now",
        "auto-apply per advisor",
        "Because the AI advisor recommended",
        "Because the advisor said it was right",
    ],
)
def test_v130_scanner_catches_violation_patterns(rationale: str) -> None:
    events = [
        {
            "ts": 1.0,
            "event_type": "tool_use",
            "run_id": "r1",
            "rationale": rationale,
        }
    ]
    items = _scan_v130_violations(events)
    assert len(items) == 1
    assert items[0].severity == "critical"
    assert items[0].category == "v130_violation"


@pytest.mark.parametrize(
    "rationale",
    [
        "k-omega-SST RANS converged; matches my Fluent prior",
        "engineer-driven mesh refinement based on checkMesh threshold",
        "applying because the residuals indicate convergence",
    ],
)
def test_v130_scanner_clean_rationale_passes(rationale: str) -> None:
    events = [{"ts": 1.0, "event_type": "tool_use", "run_id": "r1", "rationale": rationale}]
    assert _scan_v130_violations(events) == []


# ---------------------------------------------------------------------------
# Per-run classification
# ---------------------------------------------------------------------------


def test_clean_run_yields_info_entry(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, run_id="r_clean")
    _write_minimal(
        run_dir,
        events=[
            {"event_type": "api_call", "url": "/api/cases/x/state", "status": 200, "ok": True},
            {"event_type": "tool_use", "tool_name": "submit_verdict", "rationale": "engineer judgment"},
            {"event_type": "verdict", "observed": 0.44, "passed": True, "detail": "ok"},
        ],
        result={
            "run_id": "r_clean",
            "case_id": "naca0012",
            "persona": "novice",
            "model_id": "claude-sonnet-4-6",
            "steps": 3,
            "verdict": {"passed": True, "observed": 0.44, "reference": 0.44, "tolerance": 0.05},
            "dropped": False,
            "drop_reason": None,
            "error": None,
        },
        spec={"case_id": "naca0012", "persona": "novice", "elapsed_s": 1.2},
    )
    summaries = aggregate(tmp_path)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.verdict_passed is True
    assert s.dropped is False
    assert any(i.severity == "info" and i.category == "clean_run" for i in s.backlog)
    assert all(i.severity != "critical" for i in s.backlog)


def test_failed_verdict_yields_warning(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, run_id="r_fail")
    _write_minimal(
        run_dir,
        events=[
            {"event_type": "tool_use", "tool_name": "submit_verdict", "rationale": "engineer call"},
            {"event_type": "verdict", "observed": 0.30, "passed": False, "detail": "off"},
        ],
        result={
            "run_id": "r_fail",
            "verdict": {
                "passed": False,
                "observed": 0.30,
                "reference": 0.44,
                "tolerance": 0.05,
            },
            "steps": 2,
            "dropped": False,
        },
        spec={"case_id": "naca0012", "persona": "novice"},
    )
    summaries = aggregate(tmp_path)
    s = summaries[0]
    assert any(
        i.severity == "warning" and i.category == "verdict_failed" for i in s.backlog
    )


def test_drop_no_tool_call_is_critical(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, run_id="r_drop")
    _write_minimal(
        run_dir,
        events=[{"event_type": "decision", "step": 1, "detail": "no tools"}],
        result={
            "run_id": "r_drop",
            "verdict": None,
            "steps": 1,
            "dropped": True,
            "drop_reason": "no_tool_call",
        },
        spec={"case_id": "backward_step", "persona": "debug"},
    )
    summaries = aggregate(tmp_path)
    assert any(
        i.severity == "critical" and i.category == "dropped_no_tool_call"
        for i in summaries[0].backlog
    )


def test_max_steps_reached_is_critical(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, run_id="r_max")
    _write_minimal(
        run_dir,
        events=[],
        result={
            "run_id": "r_max",
            "verdict": None,
            "steps": 30,
            "dropped": False,
            "error": "max_steps_reached",
        },
        spec={"case_id": "pipe_expansion", "persona": "novice"},
    )
    summaries = aggregate(tmp_path)
    assert any(
        i.severity == "critical" and i.category == "max_steps_reached"
        for i in summaries[0].backlog
    )


def test_advisor_overuse_is_warning(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, run_id="r_overuse")
    events = [
        {
            "event_type": "api_call",
            "url": f"/api/cases/x/ai-review",
            "status": 200,
            "ok": True,
        }
        for _ in range(11)
    ]
    events.append(
        {
            "event_type": "verdict",
            "observed": 0.44,
            "passed": True,
            "detail": "ok",
        }
    )
    _write_minimal(
        run_dir,
        events=events,
        result={
            "run_id": "r_overuse",
            "verdict": {"passed": True, "observed": 0.44, "reference": 0.44, "tolerance": 0.05},
            "steps": 12,
            "dropped": False,
        },
        spec={"case_id": "naca0012", "persona": "novice"},
    )
    summaries = aggregate(tmp_path)
    assert any(
        i.severity == "warning" and i.category == "advisor_overuse"
        for i in summaries[0].backlog
    )


def test_v130_violation_in_friction_log_yields_critical(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, run_id="r_v130")
    _write_minimal(
        run_dir,
        events=[
            {
                "event_type": "tool_use",
                "tool_name": "http_post",
                "rationale": "applying because the AI told me to",
            },
            {
                "event_type": "verdict",
                "observed": 0.44,
                "passed": True,
                "detail": "ok",
            },
        ],
        result={
            "run_id": "r_v130",
            "verdict": {"passed": True, "observed": 0.44, "reference": 0.44, "tolerance": 0.05},
            "steps": 2,
            "dropped": False,
        },
        spec={"case_id": "naca0012", "persona": "novice"},
    )
    summaries = aggregate(tmp_path)
    assert any(
        i.severity == "critical" and i.category == "v130_violation"
        for i in summaries[0].backlog
    )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def test_render_report_includes_required_sections() -> None:
    summary = RunSummary(
        run_id="r1",
        case_id="naca0012",
        persona="novice",
        model_id="claude-sonnet-4-6",
        n_steps=3,
        n_advisor_queries=2,
        n_tool_uses=4,
        verdict_passed=True,
        dropped=False,
        drop_reason=None,
        error=None,
        elapsed_s=1.2,
        backlog=[
            BacklogItem(
                severity="info",
                category="clean_run",
                run_id="r1",
                case_id="naca0012",
                persona="novice",
                detail="passed",
            ),
        ],
    )
    text = render_report([summary], dry_run=True)
    assert "DOGFOOD REPORT" in text
    assert "Run roster" in text
    assert "Aggregate counts" in text
    assert "Critical backlog" in text
    assert "Warning backlog" in text
    assert "Info entries" in text
    assert "DRY RUN" in text
    assert "naca0012" in text


def test_render_report_marks_live_when_not_dry_run() -> None:
    text = render_report([], dry_run=False)
    assert "LIVE" in text
    assert "DRY RUN" not in text
