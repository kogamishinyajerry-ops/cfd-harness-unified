"""Tests for scripts/dogfood/friction_log.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dogfood.friction_log import (
    EVENT_TYPES,
    FrictionLog,
    grep_events,
    read_log,
)


def test_friction_log_writes_run_start_run_end(tmp_path: Path) -> None:
    log_path = tmp_path / "friction_log.jsonl"
    with FrictionLog(
        path=log_path,
        run_id="abc",
        case_id="case1",
        persona="novice",
        model_id="claude-sonnet-4-6",
    ) as log:
        log.emit("decision", step=1, detail="hello")
    events = read_log(log_path)
    assert events[0]["event_type"] == "run_start"
    assert events[0]["case_id"] == "case1"
    assert events[1]["event_type"] == "decision"
    assert events[-1]["event_type"] == "run_end"
    assert events[-1]["final_status"] == "complete"


def test_friction_log_marks_error_status_on_exception(tmp_path: Path) -> None:
    log_path = tmp_path / "fl.jsonl"
    with pytest.raises(RuntimeError):
        with FrictionLog(
            path=log_path, run_id="r", case_id="c", persona="p", model_id="m"
        ) as log:
            log.emit("api_call", url="/api/x", status=500, ok=False)
            raise RuntimeError("boom")
    events = read_log(log_path)
    assert events[-1]["event_type"] == "run_end"
    assert events[-1]["final_status"] == "error:RuntimeError"


def test_friction_log_rejects_unknown_event_type(tmp_path: Path) -> None:
    with FrictionLog(
        path=tmp_path / "fl.jsonl", run_id="r", case_id="c", persona="p", model_id="m"
    ) as log:
        with pytest.raises(ValueError):
            log.emit("invented_type", x=1)


def test_grep_events_filters_by_type(tmp_path: Path) -> None:
    log_path = tmp_path / "fl.jsonl"
    with FrictionLog(
        path=log_path, run_id="r", case_id="c", persona="p", model_id="m"
    ) as log:
        log.emit("api_call", url="/api/a", status=200, ok=True)
        log.emit("decision", step=1, detail="d")
        log.emit("api_call", url="/api/b", status=200, ok=True)
    events = read_log(log_path)
    api = grep_events(events, "api_call")
    assert len(api) == 2
    assert all(e["event_type"] == "api_call" for e in api)


def test_friction_log_flushes_each_event_for_crash_recovery(tmp_path: Path) -> None:
    log_path = tmp_path / "fl.jsonl"
    log = FrictionLog(
        path=log_path, run_id="r", case_id="c", persona="p", model_id="m"
    )
    log.emit("decision", step=1, detail="halfway")
    # Simulate crash: read the file before .close() is called
    raw = log_path.read_text(encoding="utf-8")
    assert raw.count("\n") >= 2  # run_start + decision lines both flushed
    log.close()


def test_event_types_constant_includes_charter_required_kinds() -> None:
    required = {
        "api_call",
        "advisor_query",
        "decision",
        "drop",
        "verdict",
        "error",
        "tool_use",
        "budget_check",
    }
    assert required.issubset(set(EVENT_TYPES))
