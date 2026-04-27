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
    _classify_failure,
    failure_remediation,
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


# Prevent RealSolverDriver from writing real artifacts to `reports/` during
# tests (would pollute the working tree). Tests that explicitly need to
# assert artifact contents can opt out via the `write_artifacts_capture`
# fixture below.
@pytest.fixture(autouse=True)
def _stub_run_history_write():
    with patch(
        "ui.backend.services.run_history.write_run_artifacts",
        lambda **_kw: None,
    ):
        yield


@pytest.fixture
def write_artifacts_capture():
    """Yields a list that gets appended-to with every write_run_artifacts
    kwargs dict. Use when you want to assert the driver fed the
    run-history writer the right values."""
    captured: list[dict] = []

    def _record(**kw):
        captured.append(kw)
        return None

    with patch(
        "ui.backend.services.run_history.write_run_artifacts",
        _record,
    ):
        yield captured


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


def test_real_driver_honors_user_draft_override_over_whitelist(tmp_path, monkeypatch) -> None:
    """M2 contract: when ui/backend/user_drafts/{case_id}.yaml exists, the
    driver MUST honour it (this is what /workbench/case/{id}/edit produces)
    instead of falling back to the whitelist baseline. Verified by
    constructing a draft that pins Re=400 (vs whitelist Re=100 for LDC) and
    asserting the TaskSpec passed to FoamAgentExecutor.execute() carries
    Re=400."""
    from ui.backend.services import wizard_drivers as mod

    # Build a synthetic draft that overrides Re to 400.
    drafts_root = tmp_path / "ui" / "backend" / "user_drafts"
    drafts_root.mkdir(parents=True)
    (drafts_root / "lid_driven_cavity.yaml").write_text(
        "id: lid_driven_cavity\n"
        "name: Lid-Driven Cavity (M2 draft override)\n"
        "geometry_type: SIMPLE_GRID\n"
        "flow_type: INTERNAL\n"
        "compressibility: INCOMPRESSIBLE\n"
        "steady_state: STEADY\n"
        "parameters:\n"
        "  Re: 400\n"
        "boundary_conditions:\n"
        "  top_wall_u: 1.0\n",
        encoding="utf-8",
    )

    # Redirect repo_root by patching the Path resolution. The helper uses
    # `Path(__file__).resolve().parents[3]` which points at the actual repo —
    # we monkeypatch the user_drafts directory location by patching
    # _task_spec_from_case_id's repo_root computation indirectly: simplest
    # is to swap the function to use tmp_path as repo_root.
    real_func = mod._task_spec_from_case_id

    def _patched(case_id: str):
        # Lazy-imported names live inside the function — replicate the body
        # but use tmp_path as repo_root.
        import yaml
        from src.models import (
            Compressibility, FlowType, GeometryType, SteadyState, TaskSpec,
        )
        draft_path = tmp_path / "ui" / "backend" / "user_drafts" / f"{case_id}.yaml"
        if not draft_path.exists():
            raise KeyError(f"no draft for {case_id!r}")
        with draft_path.open() as fh:
            entry = yaml.safe_load(fh)
        params = entry.get("parameters") or {}
        bcs = entry.get("boundary_conditions") or {}
        return TaskSpec(
            name=entry["name"],
            geometry_type=GeometryType[entry["geometry_type"]],
            flow_type=FlowType[entry["flow_type"]],
            steady_state=SteadyState[entry.get("steady_state", "STEADY")],
            compressibility=Compressibility[entry.get("compressibility", "INCOMPRESSIBLE")],
            Re=params.get("Re"),
            boundary_conditions=dict(bcs),
            description="test patched",
        )

    monkeypatch.setattr(mod, "_task_spec_from_case_id", _patched)

    drv = RealSolverDriver()
    fake_result = _stub_execution_result(success=True)
    captured_spec = {}

    def _record(spec):
        captured_spec["it"] = spec
        return fake_result

    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.side_effect = _record
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    assert events[-1]["type"] == "run_done"
    assert events[-1]["exit_code"] == 0
    # The TaskSpec must carry the draft-override Re=400, not whitelist Re=100.
    assert captured_spec["it"].Re == 400, (
        f"draft override not honoured — got Re={captured_spec['it'].Re}"
    )

    # Restore (monkeypatch fixture handles teardown automatically).
    _ = real_func


def test_real_driver_emits_run_id_on_every_event_after_resolve() -> None:
    """M3 contract: every SSE event after run_id is generated must carry it
    as a top-level field. Frontend uses run_id on `run_done` to auto-redirect
    to /workbench/case/{id}/run/{run_id} — also useful for log multiplexing
    when multiple runs are in flight."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result()
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    # Find the first event (opening log) — must have run_id.
    assert "run_id" in events[0], "opening log must carry run_id"
    expected_run_id = events[0]["run_id"]
    # All subsequent events must carry the SAME run_id.
    for i, e in enumerate(events):
        assert e.get("run_id") == expected_run_id, (
            f"event {i} ({e.get('type')}) missing/mismatched run_id: {e}"
        )
    # Final run_done summary must include run_id text for human-readable logs.
    assert expected_run_id in events[-1]["summary"]


def test_real_driver_writes_run_history_on_success(write_artifacts_capture) -> None:
    """Happy path → write_run_artifacts called once with success=True,
    correct exit_code, key_quantities + residuals copied through."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(
        success=True,
        residuals={"Ux": 1e-5, "p": 5e-4},
        key_quantities={"u_max": 0.61},
        execution_time_s=12.5,
    )
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    assert len(write_artifacts_capture) == 1
    kw = write_artifacts_capture[0]
    assert kw["case_id"] == "lid_driven_cavity"
    assert kw["success"] is True
    assert kw["exit_code"] == 0
    assert kw["key_quantities"] == {"u_max": 0.61}
    assert kw["residuals"] == {"Ux": 1e-5, "p": 5e-4}
    assert kw["duration_s"] == 12.5
    # run_id must match what the SSE events advertised.
    assert kw["run_id"] == events[0]["run_id"]
    # source_origin must be one of the two known values.
    assert kw["source_origin"] in {"draft", "whitelist"}


def test_real_driver_writes_run_history_on_executor_exception(write_artifacts_capture) -> None:
    """Failure-by-exception path → write_run_artifacts called with
    success=False, exit_code=1, error_message populated."""
    drv = RealSolverDriver()
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.side_effect = RuntimeError("Docker daemon offline")
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    assert len(write_artifacts_capture) == 1
    kw = write_artifacts_capture[0]
    assert kw["success"] is False
    assert kw["exit_code"] == 1
    assert kw["error_message"] is not None
    assert "Docker daemon offline" in kw["error_message"]
    assert kw["run_id"] == events[0]["run_id"]


def test_real_driver_writeback_failure_does_not_block_run_done(
    write_artifacts_capture,
    capsys,
) -> None:
    """Defense: if write_run_artifacts raises (disk full, perm denied, ...)
    the user must still see run_done. Per BUG-1 fix (2026-04-27),
    persistence runs in an exec_task done_callback decoupled from the
    SSE coroutine. Per Codex r1 P1, the callback emits a stderr log on
    failure so the operator sees it in backend logs even when the SSE
    consumer is gone (pre-fix behavior emitted via SSE; post-fix emits
    via stderr — both routes guarantee operator visibility)."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result()

    def _raise(**_kw):
        raise OSError("read-only filesystem")

    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        with patch(
            "ui.backend.services.run_history.write_run_artifacts",
            _raise,
        ):
            events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    # Run completed despite writeback failure (the SSE stream did not crash).
    assert events[-1]["type"] == "run_done"
    assert events[-1]["exit_code"] == 0
    # stderr must show the writeback failure so backend logs preserve
    # the signal even when SSE consumer is gone.
    captured = capsys.readouterr()
    assert "writeback failed" in captured.err
    assert "OSError" in captured.err
    assert "read-only filesystem" in captured.err


def test_real_driver_consumer_disconnect_still_persists(write_artifacts_capture) -> None:
    """BUG-1 (2026-04-27 cylinder dogfood incident): if the SSE consumer
    aborts mid-run (curl killed, browser tab closed, Monitor timeout),
    the executor task's done_callback must still write run history. Pre-fix
    the persistence call lived inside the SSE generator coroutine, so a
    consumer disconnect cancelled it after the executor had already
    completed — burning ~2.5h of cylinder compute with no verdict trace.
    """
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(success=True)

    async def _drain_then_abort():
        with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
            MockExec.return_value.execute.return_value = fake_result
            agen = drv.run("lid_driven_cavity")
            # Drain a few events past phase_start so the coroutine has
            # actually created exec_task and registered the
            # done_callback. The to_thread executor returns instantly
            # in tests (MagicMock value), so a couple of heartbeat /
            # metric yields land before we abort.
            drained = 0
            while drained < 5:
                try:
                    await agen.__anext__()
                except StopAsyncIteration:
                    break
                drained += 1
            # Abandon mid-run — same shape as a curl client closing
            # the connection or a Monitor timeout killing curl.
            await agen.aclose()
        # Yield repeatedly so the to_thread executor finishes in its
        # thread pool, then the done_callback fires on this loop.
        for _ in range(50):
            await asyncio.sleep(0)

    asyncio.run(_drain_then_abort())

    # Persistence happened despite the consumer hanging up partway through.
    assert len(write_artifacts_capture) == 1, (
        "expected exactly one persistence call from the done_callback even "
        "after consumer aborted; got "
        f"{len(write_artifacts_capture)}"
    )
    kw = write_artifacts_capture[0]
    assert kw["success"] is True
    assert kw["case_id"] == "lid_driven_cavity"


# Note: P2 (Codex r1) cancelled-exec_task handling is exercised in
# production-side code only. A unit test for it is brittle (depends on
# asyncio.cancel + asyncio.to_thread + thread-pool teardown ordering
# inside asyncio.run, all of which are loop-internal mechanics). The
# defensive callback branch is small + has a rationale comment;
# regression of the broader done_callback wiring is caught by
# `test_real_driver_consumer_disconnect_still_persists` above.


# --- M4 · failure classifier ----------------------------------------------


@pytest.mark.parametrize(
    "haystack,expected",
    [
        # Docker daemon down
        ("Cannot connect to the Docker daemon at unix:///var/run/docker.sock",
         "docker_missing"),
        ("docker.errors.DockerException: ...", "docker_missing"),
        ("error response from daemon: ...", "docker_missing"),
        # Container missing (cascades)
        ("Error: No such container: cfd-openfoam", "openfoam_missing"),
        # OpenFOAM binary missing — "command not found" wins over a bare
        # blockmesh marker, so "blockMesh: command not found" is correctly
        # classified as openfoam_missing rather than mesh_failed.
        ("blockMesh: command not found", "openfoam_missing"),
        ("simpleFoam: command not found", "openfoam_missing"),
        # Mesh failure (FOAM FATAL + blockMesh marker → mesh_failed)
        ("FOAM FATAL ERROR: blockMesh non-orthogonality 92.4 deg",
         "mesh_failed"),
        ("negative cell volume detected during snappyHexMesh",
         "mesh_failed"),
        # Solver divergence
        ("Time = 4.2s  continuity error = 1.2e62", "solver_diverged"),
        ("Floating point exception (core dumped)", "solver_diverged"),
        ("Time = 0.5  max(Co) = 98.7", "solver_diverged"),
        ("FOAM FATAL ERROR: simpleFoam diverged", "solver_diverged"),
        # Post-process
        ("foamToVTK: error converting time 0.5", "postprocess_failed"),
        # Empty / no info
        ("", "unknown_error"),
        (None, "unknown_error"),
        # Garbage that matches nothing
        ("some random unrelated garbage text", "unknown_error"),
    ],
)
def test_classify_failure_categorises_known_patterns(haystack, expected) -> None:
    assert _classify_failure(haystack) == expected


def test_failure_remediation_known_for_every_category() -> None:
    """Every closed-set category must have a non-empty remediation hint —
    so the frontend banner never shows an empty body."""
    for cat in (
        "docker_missing", "openfoam_missing", "mesh_failed",
        "solver_diverged", "postprocess_failed", "unknown_error",
    ):
        hint = failure_remediation(cat)
        assert hint and len(hint) > 5
    # Unknown category falls back to unknown_error's hint.
    assert failure_remediation("not_a_real_category") == failure_remediation("unknown_error")


def test_real_driver_failure_emits_classified_category(write_artifacts_capture) -> None:
    """RealSolverDriver MUST attach failure_category to phase_done/run_done
    on the failure path, AND pass it to write_run_artifacts."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(
        success=False,
        exit_code=1,
        error_message="FOAM FATAL ERROR continuity error 1e62 max(Co)=98.7",
    )
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    # SSE-side: phase_done and run_done both carry failure_category.
    phase_done = next(e for e in events if e["type"] == "phase_done")
    run_done = events[-1]
    assert phase_done.get("failure_category") == "solver_diverged"
    assert run_done.get("failure_category") == "solver_diverged"

    # Writeback-side: the artifact persists the same category.
    assert len(write_artifacts_capture) == 1
    assert write_artifacts_capture[0]["failure_category"] == "solver_diverged"


def test_real_driver_executor_exception_classified_as_docker_missing(
    write_artifacts_capture,
) -> None:
    """A RuntimeError mentioning 'docker daemon' should classify as
    docker_missing, not bubble up as unknown_error."""
    drv = RealSolverDriver()
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.side_effect = RuntimeError(
            "Cannot connect to the Docker daemon at unix:///var/run/docker.sock"
        )
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    run_done = events[-1]
    assert run_done["exit_code"] == 1
    assert run_done.get("failure_category") == "docker_missing"
    assert write_artifacts_capture[0]["failure_category"] == "docker_missing"


def test_real_driver_success_omits_failure_category(write_artifacts_capture) -> None:
    """Success path must NOT attach a failure_category — None is the
    semantic 'this is a healthy run' signal for the run-history table."""
    drv = RealSolverDriver()
    fake_result = _stub_execution_result(success=True)
    with patch("src.foam_agent_adapter.FoamAgentExecutor") as MockExec:
        MockExec.return_value.execute.return_value = fake_result
        events = asyncio.run(_collect_events(drv, "lid_driven_cavity"))

    run_done = events[-1]
    assert run_done["exit_code"] == 0
    assert "failure_category" not in run_done
    # Writeback gets None.
    assert write_artifacts_capture[0]["failure_category"] is None


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
