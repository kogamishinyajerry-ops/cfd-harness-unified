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
# Codex W4 prep R1 finding 3 fix: log paths anchor to repo root, not cwd
# ---------------------------------------------------------------------------


def test_jsonl_paths_anchor_to_repo_root_regardless_of_cwd(tmp_path, monkeypatch):
    """Writer + evaluator must agree on log path even when cwd differs.

    Pre-fix: ``_resolve_jsonl_path`` returned cwd-relative path while
    ``scripts/plane_guard_rollback_eval.py`` always read REPO_ROOT/...
    → recorded incidents could be silently masked.

    Post-fix: both anchor to repo root (discovered via pyproject.toml /
    .git walk from this module's __file__).
    """
    monkeypatch.chdir(tmp_path)
    expected_root = guard_module._find_repo_root()  # noqa: SLF001
    assert expected_root is not None, "must discover repo root"
    pollution_path = guard_module._resolve_jsonl_path(  # noqa: SLF001
        guard_module._POLLUTION_LOG_FILENAME  # noqa: SLF001
    )
    confusion_path = guard_module._resolve_jsonl_path(  # noqa: SLF001
        guard_module._FIXTURE_CONFUSION_LOG_FILENAME  # noqa: SLF001
    )
    assert pollution_path.startswith(expected_root)
    assert confusion_path.startswith(expected_root)
    # Specifically NOT cwd-relative.
    assert not pollution_path.startswith(str(tmp_path))


# ---------------------------------------------------------------------------
# Codex W4 prep R1 finding 2 fix: A13 atexit hook auto-fires on process exit
# ---------------------------------------------------------------------------


def test_install_guard_registers_atexit_hook_once():
    """install_guard registers exactly one atexit callback per process."""
    import atexit as _atexit
    uninstall_guard()
    # Reset module-level flag so this test is order-independent.
    guard_module._ATEXIT_REGISTERED = False  # noqa: SLF001
    registered = []
    monkeypatched = lambda fn, *a, **kw: registered.append(fn)
    real_register = _atexit.register
    _atexit.register = monkeypatched  # type: ignore[assignment]
    try:
        install_guard(Mode.WARN)
        install_guard(Mode.WARN)  # Repeat call — must NOT re-register.
    finally:
        _atexit.register = real_register  # type: ignore[assignment]
        uninstall_guard()
    assert len(registered) == 1
    assert registered[0] is guard_module._atexit_pollution_check  # noqa: SLF001


def test_atexit_pollution_check_runs_diff_when_snapshot_active(tmp_path, monkeypatch):
    """The atexit callback runs diff_pollution_snapshot when a snapshot is active.

    Test hygiene (RETRO-V61-006 MP-D): monkeypatch _find_repo_root so the
    writer anchors to tmp_path, not the real repo root. Without this the
    test would leak one sys_modules_pollution.jsonl line into reports/
    on every run, polluting CI dogfood artifacts.
    """
    uninstall_guard()
    import src.task_runner  # noqa: F401
    monkeypatch.setattr(guard_module, "_find_repo_root", lambda: str(tmp_path))
    install_guard(Mode.WARN)
    # Pollute one src.* key so the diff has something to log.
    polluted_key = "src.task_runner"
    saved = sys.modules.get(polluted_key)
    fake = ModuleType(polluted_key)
    fake.__file__ = "/tmp/atexit_polluted.py"
    sys.modules[polluted_key] = fake
    try:
        guard_module._atexit_pollution_check()  # noqa: SLF001
    finally:
        if saved is not None:
            sys.modules[polluted_key] = saved
        uninstall_guard(run_pollution_check=False)
    # diff_pollution_snapshot wrote to tmp_path-anchored path (not repo root).
    expected_log = tmp_path / "reports" / "plane_guard" / guard_module._POLLUTION_LOG_FILENAME  # noqa: SLF001
    assert expected_log.exists()


def test_atexit_pollution_check_noops_when_no_snapshot():
    """The atexit callback is a no-op when the snapshot is None (idempotent + safe)."""
    uninstall_guard()
    assert guard_module._POLLUTION_SNAPSHOT is None  # noqa: SLF001
    # Must not raise even with no snapshot active.
    guard_module._atexit_pollution_check()  # noqa: SLF001


# ---------------------------------------------------------------------------
# Codex W4 prep R1 finding 1 fix: A18 wired into find_spec bypass path
# ---------------------------------------------------------------------------


def test_a18_records_incident_when_fixture_frame_masks_forbidden_transition(
    tmp_path, monkeypatch
):
    """Fixture-frame bypass of forbidden transition records A18 incident.

    Test hygiene (RETRO-V61-006 MP-D): monkeypatch _find_repo_root so the
    A18 writer anchors to tmp_path, not the real repo root. Without this
    the test would leak one fixture_frame_confusion.jsonl line into reports/
    on every CI run, which IS the file the rollback evaluator reads —
    leak would inject false-positive incidents toward the §2.4 trigger.
    """
    from src._plane_guard import PlaneGuardFinder

    uninstall_guard()
    monkeypatch.setattr(guard_module, "_find_repo_root", lambda: str(tmp_path))

    finder = PlaneGuardFinder(mode=Mode.WARN)

    class FakeFrame:
        def __init__(self, mod_name, back=None):
            self.f_globals = {"__name__": mod_name}
            self.f_back = back

    # Fixture chain: tests.conftest → src.foam_agent_adapter (Execution)
    # → import src.result_comparator (Evaluation) — would be forbidden
    # without the allowlist.
    src_frame = FakeFrame("src.foam_agent_adapter")
    test_frame = FakeFrame("tests.conftest", back=src_frame)

    monkeypatch.setattr(
        guard_module.sys, "_getframe", lambda depth=0: test_frame
    )

    expected_log = tmp_path / "reports" / "plane_guard" / guard_module._FIXTURE_CONFUSION_LOG_FILENAME  # noqa: SLF001

    # Calling find_spec on src.result_comparator from this fake stack
    # → Evaluation target + Execution source via tests.* bypass = A18 hit.
    finder.find_spec("src.result_comparator", None, None)

    assert expected_log.exists(), "A18 incident must be recorded to fixture_frame_confusion.jsonl"
    line = expected_log.read_text(encoding="utf-8").splitlines()[-1]
    parsed = json.loads(line)
    assert parsed["test_path"] == "tests.conftest"
    assert parsed["source_module"] == "src.foam_agent_adapter"
    assert parsed["target_module"] == "src.result_comparator"
    assert parsed["contract_name"]


def test_a18_does_not_record_when_no_forbidden_transition_masked(
    tmp_path, monkeypatch
):
    """If the bypassed transition would have been allowed anyway, no A18 record.

    Test hygiene (RETRO-V61-006 MP-D): monkeypatch _find_repo_root for
    same isolation reason as the positive case above.
    """
    from src._plane_guard import PlaneGuardFinder

    uninstall_guard()
    monkeypatch.setattr(guard_module, "_find_repo_root", lambda: str(tmp_path))
    finder = PlaneGuardFinder(mode=Mode.WARN)

    class FakeFrame:
        def __init__(self, mod_name, back=None):
            self.f_globals = {"__name__": mod_name}
            self.f_back = back

    # tests.something → src.task_runner (Control) → import src.foam_agent_adapter
    # (Execution): Control → Execution is ALLOWED, so no incident even though
    # bypass occurred.
    src_frame = FakeFrame("src.task_runner")
    test_frame = FakeFrame("tests.something", back=src_frame)
    monkeypatch.setattr(
        guard_module.sys, "_getframe", lambda depth=0: test_frame
    )

    expected_log = tmp_path / "reports" / "plane_guard" / guard_module._FIXTURE_CONFUSION_LOG_FILENAME  # noqa: SLF001

    finder.find_spec("src.foam_agent_adapter", None, None)

    assert not expected_log.exists(), "no A18 record when bypassed transition was allowed"


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
