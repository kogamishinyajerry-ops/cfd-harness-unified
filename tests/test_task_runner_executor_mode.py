"""DEC-V61-074 P2-T1.b · TaskRunner ExecutorMode dispatch.

Tests the new ``executor_mode`` / ``executor_abc`` kwargs on
``TaskRunner.__init__`` and the dispatch path in
:meth:`TaskRunner.run_task` per EXECUTOR_ABSTRACTION.md §6.1:

* ``DOCKER_OPENFOAM`` / ``MOCK`` (status=OK) → normal flow continues
  with the wrapped ``ExecutionResult`` and downstream comparator /
  attestor pipeline runs.
* ``HYBRID_INIT`` (status=MODE_NOT_APPLICABLE per §5.2) and
  ``FUTURE_REMOTE`` (status=MODE_NOT_YET_IMPLEMENTED per §6.1) →
  short-circuit before comparator; the runner returns a
  ``RunReport`` whose summary surfaces the mode + status + notes.

Tests use ``MagicMock`` to substitute the concrete ``ExecutorAbc``
subclasses so we can exercise the dispatch contract without booting
Docker / OpenFOAM / a real surrogate model.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.executor import (
    DockerOpenFOAMExecutor,
    ExecutorMode,
    ExecutorStatus,
    FutureRemoteExecutor,
    HybridInitExecutor,
    MockExecutor,
    RunReport as ExecutorRunReport,
    SPEC_VERSION,
)
from src.models import (
    Compressibility,
    ExecutionResult,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)
from src.task_runner import TaskRunner


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _task_spec() -> TaskSpec:
    return TaskSpec(
        name="lid_driven_cavity",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
        notion_task_id="task-mode-dispatch",
    )


def _stub_runner(executor_abc) -> TaskRunner:
    """TaskRunner with Notion + DB + comparator stubbed and an explicit
    ``executor_abc`` injected. Comparator is also mocked away — these
    tests assert dispatch behavior, not comparison correctness."""
    notion = MagicMock()
    notion.write_execution_result.side_effect = NotImplementedError(
        "Notion not configured"
    )
    notion.list_pending_tasks.side_effect = NotImplementedError(
        "Notion not configured"
    )
    db = MagicMock()
    db.get_execution_chain.side_effect = lambda _: None
    db.load_gold_standard.side_effect = lambda _: None

    runner = TaskRunner(
        notion_client=notion,
        knowledge_db=db,
        executor_abc=executor_abc,
    )
    # Comparator + attestor are not under test here.
    runner._comparator = MagicMock()
    runner._comparator.compare.return_value = MagicMock(passed=True, deviations=[])
    runner._compute_attestation = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(overall="ATTEST_NOT_APPLICABLE", checks=[])
    )
    return runner


# ---------------------------------------------------------------------------
# Constructor wiring + resolver
# ---------------------------------------------------------------------------

class TestExecutorModeWiring:
    def test_default_construction_keeps_legacy_path(self):
        """No ``executor_mode`` / ``executor_abc`` kwargs → legacy
        ``self._executor`` (CFDExecutor) path is preserved; the new
        ``self._executor_abc`` slot is None."""
        runner = TaskRunner(notion_client=MagicMock(), knowledge_db=MagicMock())
        assert runner._executor_abc is None

    def test_executor_mode_resolves_each_subclass(self):
        """Every ExecutorMode value maps to its canonical skeleton class.
        Catches enum-extension drift (a new mode added without a row in
        the resolver dispatch table)."""
        cases = {
            ExecutorMode.DOCKER_OPENFOAM: DockerOpenFOAMExecutor,
            ExecutorMode.MOCK: MockExecutor,
            ExecutorMode.HYBRID_INIT: HybridInitExecutor,
            ExecutorMode.FUTURE_REMOTE: FutureRemoteExecutor,
        }
        for mode, expected_cls in cases.items():
            instance = TaskRunner._resolve_executor_abc(mode)
            assert isinstance(instance, expected_cls), (
                f"ExecutorMode={mode!r} resolved to {type(instance).__name__}, "
                f"expected {expected_cls.__name__}"
            )
            assert instance.MODE is mode

    def test_executor_mode_and_executor_abc_are_mutually_exclusive(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            TaskRunner(
                notion_client=MagicMock(),
                knowledge_db=MagicMock(),
                executor_mode=ExecutorMode.MOCK,
                executor_abc=MagicMock(spec=DockerOpenFOAMExecutor),
            )


# ---------------------------------------------------------------------------
# Dispatch — each mode
# ---------------------------------------------------------------------------

class TestRunTaskDispatchPerMode:
    """One test per ExecutorMode. ExecutorAbc subclasses are MagicMock'd
    so the dispatch path is the only thing under test."""

    def _ok_run_report(self, mode: ExecutorMode) -> ExecutorRunReport:
        return ExecutorRunReport(
            mode=mode,
            status=ExecutorStatus.OK,
            contract_hash="deadbeef" * 8,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(
                success=True,
                is_mock=(mode is ExecutorMode.MOCK),
                residuals={"p": 1e-6, "U": 1e-6},
                key_quantities={"u_centerline": 0.0},
                execution_time_s=0.01,
            ),
            notes=("mock_executor_no_truth_source",) if mode is ExecutorMode.MOCK else (),
        )

    def _refusal_run_report(
        self, mode: ExecutorMode, status: ExecutorStatus, note: str
    ) -> ExecutorRunReport:
        return ExecutorRunReport(
            mode=mode,
            status=status,
            contract_hash="cafef00d" * 8,
            version=SPEC_VERSION,
            execution_result=None,
            notes=(note,),
        )

    def test_docker_openfoam_status_ok_normal_flow(self):
        run_report = self._ok_run_report(ExecutorMode.DOCKER_OPENFOAM)
        executor_abc = MagicMock(spec=DockerOpenFOAMExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        executor_abc.execute.assert_called_once()
        assert result.execution_result is run_report.execution_result
        # Normal flow path: comparator was called (gold=None → no comparison
        # produced, but the attestation+summary path ran).
        assert "Short-circuit" not in result.summary

    def test_mock_status_ok_normal_flow_carries_truth_source_note(self):
        run_report = self._ok_run_report(ExecutorMode.MOCK)
        executor_abc = MagicMock(spec=MockExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        executor_abc.execute.assert_called_once()
        assert result.execution_result is run_report.execution_result
        assert result.execution_result.is_mock is True
        # The mock-truth-source note lives on the ExecutorRunReport, which
        # is forwarded to the manifest builder by callers (see T1.b.1) —
        # not on TaskRunner.RunReport directly. Dispatch contract:
        # OK → normal flow, no short-circuit.
        assert "Short-circuit" not in result.summary

    def test_hybrid_init_mode_not_applicable_short_circuits(self):
        run_report = self._refusal_run_report(
            ExecutorMode.HYBRID_INIT,
            ExecutorStatus.MODE_NOT_APPLICABLE,
            "hybrid_init_skeleton_no_surrogate",
        )
        executor_abc = MagicMock(spec=HybridInitExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        executor_abc.execute.assert_called_once()
        # Comparator MUST NOT see a refusal — short-circuit before it.
        runner._comparator.compare.assert_not_called()
        assert result.comparison_result is None
        assert result.correction_spec is None
        assert result.attestation is None
        assert "Short-circuit" in result.summary
        assert "hybrid_init" in result.summary
        assert "mode_not_applicable" in result.summary
        assert "hybrid_init_skeleton_no_surrogate" in result.summary
        # Synthetic ExecutionResult carries the refusal envelope.
        assert result.execution_result.success is False
        assert "mode_not_applicable" in (result.execution_result.error_message or "")

    def test_future_remote_mode_not_yet_implemented_short_circuits(self):
        run_report = self._refusal_run_report(
            ExecutorMode.FUTURE_REMOTE,
            ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            "future_remote_stub_only",
        )
        executor_abc = MagicMock(spec=FutureRemoteExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        executor_abc.execute.assert_called_once()
        runner._comparator.compare.assert_not_called()
        assert "Short-circuit" in result.summary
        assert "future_remote" in result.summary
        assert "mode_not_yet_implemented" in result.summary
        assert "future_remote_stub_only" in result.summary
        assert result.trust_gate_report is None  # nothing fed to trust-gate
