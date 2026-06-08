"""P4 V71.A · TaskRunner ⟷ specialized wedge-gate wiring (DEC-V61-234 R1 P1).

Codex R1 escalated R0's whitelist registration to P1: adding
``wedge_oblique_shock`` to ``knowledge/whitelist.yaml`` makes the case
SELECTABLE through ``KnowledgeDB.list_whitelist_cases()`` /
``_task_spec_from_case_id`` (``GeometryType.SUPERSONIC_WEDGE`` is a loadable
enum — unlike the CHT ``COMPLEX`` sentinel — because the adapter must dispatch
on it). But ``load_gold_standard`` returns None for the anchor (its verdict is
a SPECIALIZED physics gate, not the generic residual comparator), so the
pre-fix ``run_task`` skipped comparison entirely and ``run_batch`` reported
"No gold standard found for case 'wedge_oblique_shock'" even after a successful
solve — the benchmark was exposed but never verified.

These tests lock the fix: ``TaskRunner.run_task`` / ``run_batch`` now route a
SUPERSONIC_WEDGE run through ``_verify_supersonic_wedge`` →
``gate_wedge_against_gold``, translating the WedgeGateResult into the normal
ComparisonResult, so the exposed benchmark is genuinely verified.

Hermetic — no Docker: the gate runs against the FROZEN backend-e2e output
(``reports/showcase_aero/_w71a_wedge_backend_e2e/``), the same artifact whose
gate_verdict.json records PASS.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.models import (
    Compressibility,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)
from src.task_runner import TaskRunner

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FROZEN_E2E = _REPO_ROOT / "reports" / "showcase_aero" / "_w71a_wedge_backend_e2e"

_NO_GOLD_PHRASE = "No gold standard found"


class _StubExecutor:
    """CFDExecutor that returns a fixed success result pointing at a case dir.

    Stands in for the live ``foam_agent_adapter`` backend so the TaskRunner
    wiring is exercised without Docker — the gate then reads the real frozen
    backend output.
    """

    def __init__(self, raw_output_path: str | None, success: bool = True) -> None:
        self._raw = raw_output_path
        self._success = success

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:  # noqa: ARG002
        return ExecutionResult(
            success=self._success,
            is_mock=False,
            raw_output_path=self._raw,
            execution_time_s=1.0,
        )


def _wedge_spec() -> TaskSpec:
    return TaskSpec(
        name="wedge_oblique_shock",
        geometry_type=GeometryType.SUPERSONIC_WEDGE,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.COMPRESSIBLE,
        Ma=2.0,
    )


def test_run_task_verifies_wedge_via_specialized_gate() -> None:
    """A successful SUPERSONIC_WEDGE run is VERIFIED, not skipped: the
    comparison_result is populated (passed=True) from the real gate output."""
    runner = TaskRunner(executor=_StubExecutor(str(_FROZEN_E2E)))
    report = runner.run_task(_wedge_spec())

    assert report.comparison_result is not None, (
        "wedge comparison must be populated by the specialized gate, not skipped "
        "(the exposed-but-unverifiable gap Codex R1 P1 flagged)"
    )
    assert report.comparison_result.passed is True
    assert "wedge_oblique_shock gate" in report.comparison_result.summary
    assert report.comparison_result.gold_standard_id == "wedge_oblique_shock"
    # The TrustGate report now carries the comparison verdict (not None).
    assert report.trust_gate_report is not None


def test_run_task_wedge_gate_fail_is_honest_not_skipped() -> None:
    """A wedge run whose output can't be extracted is an honest FAIL with a
    real comparison_result — never a fabricated pass, never a silent skip."""
    bad_dir = _REPO_ROOT / "reports" / "showcase_aero"  # no postProcessing here
    runner = TaskRunner(executor=_StubExecutor(str(bad_dir)))
    report = runner.run_task(_wedge_spec())

    assert report.comparison_result is not None
    assert report.comparison_result.passed is False
    assert "wedge oblique-shock gate" in report.comparison_result.summary.lower()


def test_run_task_wedge_no_output_path_is_honest_fail() -> None:
    """No raw_output_path → honest skip-as-FAIL, no crash."""
    runner = TaskRunner(executor=_StubExecutor(None))
    report = runner.run_task(_wedge_spec())

    assert report.comparison_result is not None
    assert report.comparison_result.passed is False
    assert "no raw_output_path" in report.comparison_result.summary.lower()


def test_run_batch_wedge_reports_pass_not_no_gold_standard() -> None:
    """run_batch over the registered wedge anchor reports a real PASS — the
    exact 'No gold standard found' regression Codex R1 P1 flagged is gone."""
    runner = TaskRunner(executor=_StubExecutor(str(_FROZEN_E2E)))
    result = runner.run_batch(["wedge_oblique_shock"])

    assert result.total == 1
    assert result.passed == 1, f"expected 1 pass, got {result}"
    assert result.failed == 0
    for cmp in result.results:
        assert _NO_GOLD_PHRASE not in (cmp.summary or ""), (
            "run_batch must not fall back to 'No gold standard found' for the "
            "wedge anchor — the specialized gate now provides the verdict"
        )


def test_branch_does_not_fire_for_non_wedge_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    """The specialized path is geometry-gated: a non-wedge spec never calls
    _verify_supersonic_wedge (no blast radius on other case paths)."""
    runner = TaskRunner(executor=_StubExecutor(str(_FROZEN_E2E)))

    called = {"n": 0}
    orig = runner._verify_supersonic_wedge

    def _spy(exec_result):  # noqa: ANN001
        called["n"] += 1
        return orig(exec_result)

    monkeypatch.setattr(runner, "_verify_supersonic_wedge", _spy)

    non_wedge = TaskSpec(
        name="some_incompressible_case",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )
    runner.run_task(non_wedge)
    assert called["n"] == 0
