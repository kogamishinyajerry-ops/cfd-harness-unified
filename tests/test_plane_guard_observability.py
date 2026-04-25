"""Tests for ADR-002 §2.9 A13 sys.modules pollution watchdog +
§2.4 A18 fixture-frame confusion rollback counter (Opus G-9 binding 2,
target ≤ 2026-05-11).

Coverage:
  * snapshot_src_modules / diff_pollution_snapshot:
      - clean install → no pollution
      - id mismatch + __file__ mismatch → pollution event (incl. JSON line)
      - id mismatch + same __file__ → legitimate reload (no event)
      - either side __file__ missing → conservative fallback fires
        pollution (R-new-1)
  * record_fixture_frame_confusion: writes JSON line with all required
    fields
  * scripts/plane_guard_rollback_eval evaluator:
      - empty / sparse log → not triggered
      - ≥3 incidents within 14 days → triggered
      - ≥3 incidents but >14 days old → not triggered (rolling window)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from importlib import util
from pathlib import Path
from types import ModuleType

import pytest

import src._plane_guard as guard_module
from src._plane_guard import (
    Mode,
    diff_pollution_snapshot,
    install_guard,
    record_fixture_frame_confusion,
    snapshot_src_modules,
    uninstall_guard,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_SCRIPT = REPO_ROOT / "scripts" / "plane_guard_rollback_eval.py"


# ---------------------------------------------------------------------------
# A13 sys.modules pollution watchdog
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_install():
    uninstall_guard()
    # Ensure a non-bootstrap src.* module is in sys.modules so the
    # baseline snapshot captures something we can pollute.
    import src.task_runner  # noqa: F401
    install_guard(Mode.WARN)
    try:
        yield
    finally:
        uninstall_guard()


def test_a13_clean_install_no_pollution(fresh_install, tmp_path):
    """A fresh snapshot diffed against unchanged sys.modules → empty."""
    log_path = tmp_path / "pollution.jsonl"
    events = diff_pollution_snapshot(write_jsonl=True, log_path=str(log_path))
    assert events == []
    assert not log_path.exists()


def test_a13_pollution_id_and_file_mismatch_fires(fresh_install, tmp_path, caplog):
    """Stub a src.* module with both new id AND new __file__ → pollution event."""
    import logging

    caplog.set_level(logging.WARNING, logger="src._plane_guard.pollution")
    # Pollute one src.* key by replacing it with a fresh ModuleType
    # whose __file__ differs.
    polluted_key = "src.task_runner"
    saved = sys.modules.get(polluted_key)
    fake = ModuleType(polluted_key)
    fake.__file__ = "/tmp/fake_polluted_task_runner.py"
    sys.modules[polluted_key] = fake
    try:
        log_path = tmp_path / "pollution.jsonl"
        events = diff_pollution_snapshot(
            write_jsonl=True, log_path=str(log_path)
        )
    finally:
        if saved is not None:
            sys.modules[polluted_key] = saved
        else:
            sys.modules.pop(polluted_key, None)

    assert len(events) == 1
    event = events[0]
    assert event["module"] == polluted_key
    assert event["new_file"] == "/tmp/fake_polluted_task_runner.py"
    assert event["criterion"] == "id_mismatch_and_file_mismatch_or_missing"
    # JSON line written.
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(line) == event


def test_a13_legitimate_reload_same_file_does_not_fire(fresh_install, tmp_path):
    """Replace module with new id but same __file__ → no pollution event."""
    polluted_key = "src.task_runner"
    saved = sys.modules.get(polluted_key)
    assert saved is not None
    same_file = saved.__file__
    fake = ModuleType(polluted_key)
    fake.__file__ = same_file  # Same file path → legitimate reload semantics.
    sys.modules[polluted_key] = fake
    try:
        log_path = tmp_path / "pollution.jsonl"
        events = diff_pollution_snapshot(
            write_jsonl=True, log_path=str(log_path)
        )
    finally:
        sys.modules[polluted_key] = saved

    assert events == []
    assert not log_path.exists()


def test_a13_file_missing_conservative_fallback_fires(fresh_install, tmp_path):
    """One side __file__ missing → conservative id-only fires pollution (R-new-1)."""
    polluted_key = "src.task_runner"
    saved = sys.modules.get(polluted_key)
    assert saved is not None
    fake = ModuleType(polluted_key)
    # Do NOT set __file__ on fake — getattr returns None.
    sys.modules[polluted_key] = fake
    try:
        log_path = tmp_path / "pollution.jsonl"
        events = diff_pollution_snapshot(
            write_jsonl=True, log_path=str(log_path)
        )
    finally:
        sys.modules[polluted_key] = saved

    assert len(events) == 1
    assert events[0]["module"] == polluted_key
    assert events[0]["new_file"] is None


def test_a13_install_guard_takes_baseline_snapshot():
    """install_guard sets _POLLUTION_SNAPSHOT for current src.* state."""
    uninstall_guard()
    import src.task_runner  # noqa: F401
    assert guard_module._POLLUTION_SNAPSHOT is None  # noqa: SLF001
    install_guard(Mode.WARN)
    try:
        assert guard_module._POLLUTION_SNAPSHOT is not None  # noqa: SLF001
        assert "src.task_runner" in guard_module._POLLUTION_SNAPSHOT  # noqa: SLF001
    finally:
        uninstall_guard()
    # After uninstall, snapshot reset.
    assert guard_module._POLLUTION_SNAPSHOT is None  # noqa: SLF001


# ---------------------------------------------------------------------------
# A18 fixture-frame confusion .jsonl writer
# ---------------------------------------------------------------------------


def test_a18_record_writes_required_fields(tmp_path):
    """record_fixture_frame_confusion writes one JSON line with all fields."""
    log_path = tmp_path / "fixture_confusion.jsonl"
    event = record_fixture_frame_confusion(
        test_path="tests.test_example",
        source_module="src.foam_agent_adapter",
        target_module="src.result_comparator",
        contract_name="execution-never-imports-evaluation",
        stack_snippet="(synthetic)",
        log_path=str(log_path),
    )
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").splitlines()[0]
    parsed = json.loads(line)
    required = {
        "timestamp",
        "incident_id",
        "test_path",
        "source_module",
        "target_module",
        "contract_name",
        "stack_snippet",
    }
    missing = required - set(parsed)
    assert not missing
    assert parsed == event


def test_a18_record_appends_multiple_events(tmp_path):
    """Subsequent calls append, do not overwrite."""
    log_path = tmp_path / "fixture_confusion.jsonl"
    record_fixture_frame_confusion(
        test_path="tests.test_a",
        source_module="src.foam_agent_adapter",
        target_module="src.result_comparator",
        contract_name="execution-never-imports-evaluation",
        log_path=str(log_path),
    )
    record_fixture_frame_confusion(
        test_path="tests.test_b",
        source_module="src.result_comparator",
        target_module="src.foam_agent_adapter",
        contract_name="evaluation-never-imports-execution",
        log_path=str(log_path),
    )
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# scripts/plane_guard_rollback_eval rolling-window evaluator
# ---------------------------------------------------------------------------


def _load_eval_module():
    spec = util.spec_from_file_location(
        "plane_guard_rollback_eval", str(EVAL_SCRIPT)
    )
    assert spec is not None
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_log(path: Path, timestamps: list[datetime]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ts in timestamps:
            event = {
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "incident_id": "synthetic",
                "test_path": "tests.synthetic",
                "source_module": "src.x",
                "target_module": "src.y",
                "contract_name": "execution-never-imports-evaluation",
                "stack_snippet": "",
            }
            f.write(json.dumps(event) + "\n")


def test_rollback_eval_empty_log_not_triggered(tmp_path):
    eval_mod = _load_eval_module()
    log_path = tmp_path / "empty.jsonl"
    log_path.touch()
    triggered, count, _ = eval_mod.evaluate(log_path=log_path)
    assert not triggered
    assert count == 0


def test_rollback_eval_three_recent_triggers(tmp_path):
    eval_mod = _load_eval_module()
    log_path = tmp_path / "log.jsonl"
    now = datetime.now(timezone.utc)
    _write_log(
        log_path,
        [
            now - timedelta(days=1),
            now - timedelta(days=3),
            now - timedelta(days=5),
        ],
    )
    triggered, count, _ = eval_mod.evaluate(log_path=log_path, now=now)
    assert triggered
    assert count == 3


def test_rollback_eval_old_incidents_outside_window(tmp_path):
    """3 incidents but all >14 days old → not triggered."""
    eval_mod = _load_eval_module()
    log_path = tmp_path / "log.jsonl"
    now = datetime.now(timezone.utc)
    _write_log(
        log_path,
        [
            now - timedelta(days=20),
            now - timedelta(days=25),
            now - timedelta(days=30),
        ],
    )
    triggered, count, _ = eval_mod.evaluate(log_path=log_path, now=now)
    assert not triggered
    assert count == 0


def test_rollback_eval_cli_exit_codes(tmp_path):
    """CLI exits 0 on no-trigger, 1 on trigger."""
    log_path = tmp_path / "log.jsonl"
    now = datetime.now(timezone.utc)
    _write_log(
        log_path,
        [now - timedelta(days=1), now - timedelta(days=2)],  # only 2
    )
    result = subprocess.run(
        [sys.executable, str(EVAL_SCRIPT), "--log-path", str(log_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "OK:" in result.stdout

    _write_log(
        log_path,
        [
            now - timedelta(days=1),
            now - timedelta(days=2),
            now - timedelta(days=3),
            now - timedelta(days=4),
        ],
    )
    result = subprocess.run(
        [sys.executable, str(EVAL_SCRIPT), "--log-path", str(log_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "ROLLBACK_TRIGGERED" in result.stdout
