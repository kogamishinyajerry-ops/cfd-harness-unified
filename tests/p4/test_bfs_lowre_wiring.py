"""P4 V71B-FOLLOWUP-1 · DEC-V61-236 — execute() dispatch + TaskRunner wiring for the
wall-RESOLVED low-Re backward_facing_step anchor.

Hermetic (NO Docker): the dispatch tests monkeypatch the dedicated runner + block
``docker.from_env``; the gate/verify tests run the real Control-plane gate against the
FROZEN V&V probe (``reports/showcase_aero/_v71b_bfs_lowre_probe/``). The full
``execute()→gate PASS`` on REAL solver output is locked by the opt-in live test
(``tests/p4/test_bfs_lowre_live.py``).

Honesty locks (the Codex DEC-V61-235 R0/R1 lessons this slice must not regress):
  - dispatch is keyed on CASE IDENTITY (name=='backward_facing_step_lowre'), NOT
    geometry_type (collides with high-Re BFS) — the high-Re sibling must NOT route here;
  - ``_verify_bfs_lowre`` reads the persistent ``raw_output_path`` and fails-closed on a
    missing path (never a fabricated pass);
  - the whitelist entry actually LOADS (a malformed enum would be silently dropped) and
    carries NO inline gold (``load_gold_standard`` → None → specialized gate path).
"""
from __future__ import annotations

from pathlib import Path

import src.foam_agent_adapter as faa
from src.foam_agent_adapter import DockerOpenFOAMSolverExecutor
from src.models import (
    Compressibility,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
    is_bfs_lowre_dispatch,
)
from src.task_runner import TaskRunner

_REPO = Path(__file__).resolve().parents[2]
_FROZEN_PROBE = _REPO / "reports" / "showcase_aero" / "_v71b_bfs_lowre_probe"


def _bfs_spec(name: str = "backward_facing_step_lowre") -> TaskSpec:
    return TaskSpec(
        name=name,
        geometry_type=GeometryType.BACKWARD_FACING_STEP,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=5000.0,
        boundary_conditions={"wall_treatment": "resolved", "turbulence_model": "kOmegaSST"},
    )


class _StubExecutor:
    """Returns a fixed success result at ``raw`` — stands in for the live backend so the
    TaskRunner wiring is exercised without Docker."""

    def __init__(self, raw, success: bool = True) -> None:
        self._raw = raw
        self._success = success

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:  # noqa: ARG002
        return ExecutionResult(
            success=self._success, is_mock=False, raw_output_path=self._raw, execution_time_s=1.0
        )


def _raise_no_daemon(*_a, **_k):
    raise RuntimeError("docker.from_env blocked in unit test")


# ---------------------------------------------------------------------------
# execute() dispatch (T3 · identity-keyed)
# ---------------------------------------------------------------------------


def test_execute_routes_lowre_to_dedicated_runner(tmp_path, monkeypatch):
    """A TaskSpec named 'backward_facing_step_lowre' short-circuits to the dedicated
    runner BEFORE the persistent-container connect (no real Docker touched)."""
    ex = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))
    sentinel = ExecutionResult(success=True, is_mock=False, raw_output_path="SENTINEL", execution_time_s=0.1)
    seen = {}

    def _recorder(spec, t0):
        seen["spec"] = spec
        return sentinel

    monkeypatch.setattr(ex, "_execute_backward_facing_step_lowre", _recorder)
    monkeypatch.setattr(faa.docker, "from_env", _raise_no_daemon)
    result = ex.execute(_bfs_spec())
    assert result is sentinel
    assert seen["spec"].name == "backward_facing_step_lowre"


def test_execute_does_not_route_high_re_bfs_to_lowre_runner(tmp_path, monkeypatch):
    """The high-Re sibling (name='backward_facing_step', SAME geometry_type) must NOT
    route to the low-Re runner — identity-keying, not geometry-keying (Codex R1).

    A GENUINE high-Re BFS uses a wall FUNCTION, never the resolved treatment, so it
    matches NEITHER disjunct (name!=slug AND wall_treatment!='resolved')."""
    ex = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))
    called = {"v": False}

    def _recorder(spec, t0):
        called["v"] = True
        return ExecutionResult(success=True, is_mock=False, raw_output_path="X", execution_time_s=0.1)

    high_re = TaskSpec(
        name="backward_facing_step",
        geometry_type=GeometryType.BACKWARD_FACING_STEP,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=7600.0,
        boundary_conditions={"wall_treatment": "wall_function", "turbulence_model": "kEpsilon"},
    )
    monkeypatch.setattr(ex, "_execute_backward_facing_step_lowre", _recorder)
    monkeypatch.setattr(faa.docker, "from_env", _raise_no_daemon)  # block the generic path
    result = ex.execute(high_re)
    assert called["v"] is False, "high-Re BFS must NOT route to the low-Re runner"
    assert result.success is False  # generic path blocked → honest fail, not a fabricated pass


def test_execute_routes_display_title_with_resolved_bc(tmp_path, monkeypatch):
    """A direct / display-title caller that names the case ANYTHING but explicitly sets
    boundary_conditions.wall_treatment='resolved' STILL routes to the low-Re runner —
    the second dispatch disjunct (Codex DEC-V61-236 R0 P2). Robustness beyond the
    whitelist-slug name (the retired Notion path used a page title, not the slug)."""
    ex = DockerOpenFOAMSolverExecutor(work_dir=str(tmp_path))
    sentinel = ExecutionResult(success=True, is_mock=False, raw_output_path="SENTINEL", execution_time_s=0.1)
    seen = {}

    def _recorder(spec, t0):
        seen["spec"] = spec
        return sentinel

    display_title = TaskSpec(
        name="Low-Re BFS validation run",  # NOT the slug — a human display title
        geometry_type=GeometryType.BACKWARD_FACING_STEP,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=5000.0,
        boundary_conditions={"wall_treatment": "resolved", "turbulence_model": "kOmegaSST"},
    )
    monkeypatch.setattr(ex, "_execute_backward_facing_step_lowre", _recorder)
    monkeypatch.setattr(faa.docker, "from_env", _raise_no_daemon)
    result = ex.execute(display_title)
    assert result is sentinel, "resolved-treatment BFS must route to the low-Re runner"
    assert seen["spec"].name == "Low-Re BFS validation run"


# ---------------------------------------------------------------------------
# TaskRunner verification (T4 method · against the frozen V&V probe)
# ---------------------------------------------------------------------------


def test_verify_bfs_lowre_passes_on_frozen_probe():
    """_verify_bfs_lowre runs the Control gate on a real case dir → PASS."""
    runner = TaskRunner(executor=_StubExecutor(str(_FROZEN_PROBE)))
    cr = runner._verify_bfs_lowre(
        ExecutionResult(success=True, is_mock=False, raw_output_path=str(_FROZEN_PROBE))
    )
    assert cr.passed is True
    assert "backward_facing_step_lowre gate" in cr.summary
    assert cr.gold_standard_id == "backward_facing_step_lowre"


def test_verify_bfs_lowre_fail_closed_on_no_raw_output():
    """No raw_output_path → honest fail-closed (never a fabricated pass)."""
    runner = TaskRunner(executor=_StubExecutor(None))
    cr = runner._verify_bfs_lowre(
        ExecutionResult(success=True, is_mock=False, raw_output_path=None)
    )
    assert cr.passed is False
    assert "no raw_output_path" in cr.summary
    assert cr.gold_standard_id == "backward_facing_step_lowre"


# ---------------------------------------------------------------------------
# whitelist registration (T5 · atomic with the branch)
# ---------------------------------------------------------------------------


def test_whitelist_entry_loads_and_gold_is_none():
    """The re-added entry actually loads (not silently dropped) and carries NO inline
    gold (specialized_gate_anchor → load_gold_standard None → the gate runs)."""
    from src.knowledge_db import KnowledgeDB

    db = KnowledgeDB()
    specs = db.list_whitelist_cases()
    by_name = {s.name: s for s in specs}
    assert "backward_facing_step_lowre" in by_name, "entry silently dropped (malformed?)"
    spec = by_name["backward_facing_step_lowre"]
    assert spec.geometry_type is GeometryType.BACKWARD_FACING_STEP
    assert spec.Re == 5000
    assert spec.boundary_conditions.get("wall_treatment") == "resolved"
    assert db.load_gold_standard("backward_facing_step_lowre") is None


# ---------------------------------------------------------------------------
# shared dispatch predicate + verify/execute symmetry (R2 · Codex DEC-V61-236 R1 P1)
# ---------------------------------------------------------------------------


def test_is_bfs_lowre_dispatch_shared_predicate():
    """The SSOT predicate both planes key on: slug-name OR resolved-treatment routes;
    the high-Re wall-function sibling and non-BFS geometries do NOT."""
    # (a) whitelist slug name → routes
    assert is_bfs_lowre_dispatch(_bfs_spec(name="backward_facing_step_lowre")) is True
    # (b) display-title name BUT resolved treatment → routes (the second disjunct)
    assert is_bfs_lowre_dispatch(
        TaskSpec(
            name="Low-Re BFS validation run",
            geometry_type=GeometryType.BACKWARD_FACING_STEP,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=5000.0,
            boundary_conditions={"wall_treatment": "resolved"},
        )
    ) is True
    # (c) genuine high-Re sibling (wall_function) → does NOT route (no false-positive)
    assert is_bfs_lowre_dispatch(
        TaskSpec(
            name="backward_facing_step",
            geometry_type=GeometryType.BACKWARD_FACING_STEP,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=7600.0,
            boundary_conditions={"wall_treatment": "wall_function"},
        )
    ) is False
    # (d) different geometry → never routes
    assert is_bfs_lowre_dispatch(
        TaskSpec(
            name="backward_facing_step_lowre",  # name alone must not override geometry
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
        )
    ) is False


def test_run_task_verifies_display_title_resolved_bc_lowre():
    """Codex DEC-V61-236 R1 P1 regression: a display-title spec with resolved BC that
    EXECUTES via the low-Re runner MUST also be VERIFIED — the y+<1 gate cannot be
    silently skipped (comparison_result is populated, not None). execute() dispatch and
    the TaskRunner verify branch share ONE predicate, so they cannot drift."""
    display_title = TaskSpec(
        name="Low-Re BFS validation run",  # NOT the slug
        geometry_type=GeometryType.BACKWARD_FACING_STEP,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=5000.0,
        boundary_conditions={"wall_treatment": "resolved", "turbulence_model": "kOmegaSST"},
    )
    runner = TaskRunner(executor=_StubExecutor(str(_FROZEN_PROBE)))
    report = runner.run_task(display_title)
    assert report.comparison_result is not None, (
        "resolved-BC display-title low-Re run executed but the gate was SKIPPED "
        "(the execute/verify asymmetry Codex R1 P1 flagged)"
    )
    assert report.comparison_result.passed is True
    assert report.comparison_result.gold_standard_id == "backward_facing_step_lowre"
