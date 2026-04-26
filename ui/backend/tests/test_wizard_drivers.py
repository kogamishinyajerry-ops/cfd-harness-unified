"""Tests for the SolverDriver abstraction.

Covers the contract `MockSolverDriver` and `RealSolverDriver` (M1) both
satisfy: same SSE wire shape, same termination, case_id attribution.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from ui.backend.services.wizard_drivers import (
    MockSolverDriver,
    RealSolverDriver,
    SolverDriver,
    get_driver,
)


# Speed-up: real driver run sleeps ~10s (per-log debounce). Tests don't
# need real-time pacing; patch `asyncio.sleep` to no-op so the suite
# completes in <1s instead of >40s.
@pytest.fixture(autouse=True)
def _no_sleep():
    async def _noop(*_args, **_kw):
        return None
    with patch("ui.backend.services.wizard_drivers.asyncio.sleep", _noop):
        yield


async def _collect_events(driver: SolverDriver, case_id: str) -> list[dict]:
    """Drain a driver's async iterator into a list of decoded JSON
    events (stripping the SSE `data: ...\\n\\n` framing)."""
    events: list[dict] = []
    async for raw in driver.run(case_id):
        # SSE format: each yield is "data: <json>\n\n"
        assert raw.startswith("data: ")
        assert raw.endswith("\n\n")
        body = raw[len("data: ") : -2]  # strip prefix + trailing \n\n
        events.append(json.loads(body))
    return events


def test_mock_driver_walks_five_phases_in_order() -> None:
    drv = MockSolverDriver()
    events = asyncio.run(_collect_events(drv, "test_case"))
    phase_starts = [e["phase"] for e in events if e["type"] == "phase_start"]
    phase_dones = [e["phase"] for e in events if e["type"] == "phase_done"]
    assert phase_starts == ["geometry", "mesh", "boundary", "solver", "compare"]
    assert phase_dones == ["geometry", "mesh", "boundary", "solver", "compare"]


def test_mock_driver_terminates_with_run_done() -> None:
    drv = MockSolverDriver()
    events = asyncio.run(_collect_events(drv, "test_case"))
    assert events[-1]["type"] == "run_done"
    assert "case_id=test_case" in events[-1]["summary"]


def test_mock_driver_emits_metric_events_on_solver_phase() -> None:
    drv = MockSolverDriver()
    events = asyncio.run(_collect_events(drv, "metric_test"))
    metrics = [e for e in events if e["type"] == "metric"]
    assert len(metrics) >= 1, "solver phase must emit residual metrics"
    assert all(m["phase"] == "solver" for m in metrics)
    assert all(m["metric_key"] == "residual_p" for m in metrics)


def test_mock_driver_includes_case_id_in_opening_log() -> None:
    """Audit/observability: case_id must appear in the early log so a
    multiplexed log stream from concurrent runs stays attributable."""
    drv = MockSolverDriver()
    events = asyncio.run(_collect_events(drv, "audit_id_42"))
    first_log = next(e for e in events if e["type"] == "log")
    assert "audit_id_42" in first_log["line"]


def test_get_driver_default_returns_mock() -> None:
    """Default env-unset state returns mock — Stage 8a regression guard."""
    os.environ.pop("CFD_HARNESS_WIZARD_SOLVER", None)
    drv = get_driver()
    assert isinstance(drv, MockSolverDriver)


def test_get_driver_unknown_name_falls_back_to_mock(capsys) -> None:
    """Round-3 hands-off failure mode: unknown driver name yields mock
    + stderr warning. Onboarding-tier surface should not 500 on a typo
    in the env var."""
    drv = get_driver("does_not_exist")
    assert isinstance(drv, MockSolverDriver)
    captured = capsys.readouterr()
    assert "unknown solver driver" in captured.err.lower()


def test_get_driver_explicit_mock_name() -> None:
    drv = get_driver("mock")
    assert isinstance(drv, MockSolverDriver)


@pytest.mark.parametrize("case_id", ["x", "abc_123", "demo-case-1"])
def test_mock_driver_works_with_various_case_ids(case_id: str) -> None:
    """Driver doesn't validate case_id — that's the route's job. Whatever
    the route lets through, the driver walks unchanged."""
    drv = MockSolverDriver()
    events = asyncio.run(_collect_events(drv, case_id))
    assert events[-1]["type"] == "run_done"


# --- RealSolverDriver (M1) -------------------------------------------------
# Mocks `FoamAgentExecutor.execute()` at the module-level import boundary
# inside `RealSolverDriver.run()`. The deferred-import pattern means we patch
# `src.foam_agent_adapter.FoamAgentExecutor` directly — that's the symbol the
# driver looks up at call time.


def _stub_execution_result(**overrides):
    """Build a synthetic ExecutionResult with sane defaults that all tests
    can override via kwargs. Returns the dataclass instance, not a Mock."""
    from src.models import ExecutionResult
    base = dict(
        success=True,
        is_mock=False,
        residuals={"Ux": 1.2e-5, "Uy": 3.4e-5, "p": 5.6e-4},
        key_quantities={"u_max": 0.61, "u_min": -0.21},
        execution_time_s=12.5,
        raw_output_path="/tmp/case-12345",
        exit_code=0,
        error_message=None,
    )
    base.update(overrides)
    return ExecutionResult(**base)


def test_get_driver_real_name_returns_real_driver() -> None:
    drv = get_driver("real")
    assert isinstance(drv, RealSolverDriver)


def test_real_driver_unknown_case_id_emits_run_done_with_exit_code_2() -> None:
    """Unknown case_id (not in whitelist) — graceful run_done, no executor invocation."""
    drv = RealSolverDriver()
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        events = asyncio.run(_collect_events(drv, "case_definitely_not_in_whitelist_xyz"))
    # executor must NOT have been instantiated/called for unknown case_id
    MockExec.assert_not_called()
    last = events[-1]
    assert last["type"] == "run_done"
    assert last["exit_code"] == 2
    assert last["level"] == "error"
    # Surface the error in a log line before run_done
    error_logs = [e for e in events if e.get("level") == "error" and e["type"] == "log"]
    assert any("whitelist" in e["line"] for e in error_logs)


def test_real_driver_happy_path_lid_driven_cavity() -> None:
    """LDC whitelist case → executor returns successful ExecutionResult →
    SSE sequence shape: opening log, resolved log, phase_start solver,
    (possibly) heartbeat log, metrics, phase_done ok, run_done exit 0."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(success=True)
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))
    MockExec.return_value.execute.assert_called_once()
    types = [e["type"] for e in events]
    assert types[0] == "log"  # opening line
    assert "phase_start" in types
    assert "phase_done" in types
    assert types[-1] == "run_done"
    # Last event success-class
    last = events[-1]
    assert last["exit_code"] == 0
    assert last["level"] == "info"
    # phase_done before run_done is OK
    phase_dones = [e for e in events if e["type"] == "phase_done"]
    assert phase_dones and phase_dones[-1]["status"] == "ok"
    # Residuals mapped to metric events with residual_ prefix
    metric_keys = {e["metric_key"] for e in events if e["type"] == "metric"}
    assert "residual_Ux" in metric_keys
    assert "u_max" in metric_keys  # numeric key_quantity → metric
    # case_id attribution in opening log
    first_log = next(e for e in events if e["type"] == "log")
    assert "lid_driven_cavity" in first_log["line"]


def test_real_driver_executor_raises_emits_fail_run_done() -> None:
    """If FoamAgentExecutor.execute() raises (Docker missing, container
    crash, etc.), driver must catch and emit phase_done fail + run_done
    with exit_code=1, level=error, summarising the exception type."""
    drv = RealSolverDriver()
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.side_effect = RuntimeError("docker daemon not reachable")
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))
    last = events[-1]
    assert last["type"] == "run_done"
    assert last["exit_code"] == 1
    assert last["level"] == "error"
    assert "RuntimeError" in last["summary"] or "docker daemon" in last["summary"]
    phase_dones = [e for e in events if e["type"] == "phase_done"]
    assert phase_dones and phase_dones[-1]["status"] == "fail"


def test_real_driver_execution_result_failure_uses_result_exit_code() -> None:
    """ExecutionResult.success=False with explicit exit_code=137 (OOM kill)
    must be mirrored into run_done.exit_code rather than coerced to 1."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(
        success=False,
        exit_code=137,  # OOM kill convention
        error_message="solver diverged at t=4.2s, max(Co)=98.7",
    )
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))
    last = events[-1]
    assert last["exit_code"] == 137
    assert last["level"] == "error"
    phase_done = next(e for e in events if e["type"] == "phase_done")
    assert phase_done["status"] == "fail"
    assert "diverged" in phase_done["summary"]


def test_real_driver_non_numeric_key_quantity_falls_through_as_log() -> None:
    """Non-float key_quantities (e.g. lists, dicts) must be surfaced as log
    lines rather than crashing the driver — float() raise path."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(
        key_quantities={
            "u_centerline": [-0.21, -0.18, -0.05, 0.61],  # list, not numeric
            "u_max": 0.61,  # numeric, should still emit metric
        },
    )
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))
    metric_keys = {e["metric_key"] for e in events if e["type"] == "metric"}
    assert "u_max" in metric_keys
    assert "u_centerline" not in metric_keys  # rejected as non-numeric
    # Should appear as a log line
    log_lines = [e["line"] for e in events if e["type"] == "log"]
    assert any("u_centerline" in line for line in log_lines)


def test_real_driver_terminates_with_run_done_for_all_paths() -> None:
    """Regression: every code path must emit exactly one run_done event."""
    drv = RealSolverDriver()
    # Happy path
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = _stub_execution_result()
        events_ok = asyncio.run(_collect_events(drv, "lid_driven_cavity"))
    # Fail-from-exception path
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.side_effect = OSError("Cannot connect to Docker")
        events_exc = asyncio.run(_collect_events(drv, "lid_driven_cavity"))
    # Unknown case path
    events_unknown = asyncio.run(_collect_events(drv, "definitely_not_a_case"))

    for events in (events_ok, events_exc, events_unknown):
        run_dones = [e for e in events if e["type"] == "run_done"]
        assert len(run_dones) == 1, f"expected exactly one run_done, got {len(run_dones)}"
        assert events[-1]["type"] == "run_done"
