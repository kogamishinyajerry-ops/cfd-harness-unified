"""Tests for the SolverDriver abstraction (Stage 8b prep refactor).

Covers the contract `MockSolverDriver` is expected to satisfy. Stage
8b's RealSolverDriver gets the same test scaffold as a regression
guard — same SSE output shape, same phase ordering, same termination.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch

import pytest

from ui.backend.services.wizard_drivers import (
    MockSolverDriver,
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
