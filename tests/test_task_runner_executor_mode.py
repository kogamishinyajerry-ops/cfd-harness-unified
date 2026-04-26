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


# ---------------------------------------------------------------------------
# Codex T1.b.2 post-commit MED fix · short-circuit Notion write-back
# ---------------------------------------------------------------------------


class TestShortCircuitWritesBackToNotion:
    """Codex post-commit review (R1) MED finding: a refused
    ExecutorAbc run must surface to Notion through the same
    failure-handling contract as the legacy CFDExecutor failure path.
    `notion_client.write_execution_result` maps `success=False` to
    `Status=Review`; without this write-back the Notion task stays
    stuck in `Ready` even though the executor refused to run.
    """

    def _refused(self, mode, status, note):
        return ExecutorRunReport(
            mode=mode,
            status=status,
            contract_hash="cafef00d" * 8,
            version=SPEC_VERSION,
            execution_result=None,
            notes=(note,),
        )

    def test_hybrid_init_short_circuit_calls_notion_write_back(self):
        executor_abc = MagicMock(spec=HybridInitExecutor)
        executor_abc.execute.return_value = self._refused(
            ExecutorMode.HYBRID_INIT,
            ExecutorStatus.MODE_NOT_APPLICABLE,
            "hybrid_init_skeleton_no_surrogate",
        )
        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        # Short-circuit happened (comparator skipped) AND Notion write-
        # back fired exactly once with success=False payload — refusal
        # surfaces to operators through the standard Review channel.
        runner._comparator.compare.assert_not_called()
        runner._notion.write_execution_result.assert_called_once()
        (called_task, called_exec_result, called_summary), _ = (
            runner._notion.write_execution_result.call_args
        )
        assert called_task is _task_spec.__defaults__ or called_task.name == "lid_driven_cavity"
        assert called_exec_result.success is False
        assert "Short-circuit" in called_summary

    def test_future_remote_short_circuit_calls_notion_write_back(self):
        executor_abc = MagicMock(spec=FutureRemoteExecutor)
        executor_abc.execute.return_value = self._refused(
            ExecutorMode.FUTURE_REMOTE,
            ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            "future_remote_stub_only",
        )
        runner = _stub_runner(executor_abc)
        runner.run_task(_task_spec())

        runner._notion.write_execution_result.assert_called_once()

    def test_short_circuit_notion_unconfigured_does_not_kill_run(self):
        """When Notion is not configured (write_execution_result raises
        NotImplementedError — the legacy path's contract), the short-
        circuit must still return its report cleanly."""
        executor_abc = MagicMock(spec=HybridInitExecutor)
        executor_abc.execute.return_value = self._refused(
            ExecutorMode.HYBRID_INIT,
            ExecutorStatus.MODE_NOT_APPLICABLE,
            "hybrid_init_skeleton_no_surrogate",
        )
        runner = _stub_runner(executor_abc)
        runner._notion.write_execution_result.side_effect = NotImplementedError(
            "Notion not configured"
        )
        # Must not raise.
        result = runner.run_task(_task_spec())
        assert "Short-circuit" in result.summary


# ---------------------------------------------------------------------------
# DEC-V61-075 P2-T2.1 (Codex R3 P2) · OK-path executor-note propagation
# ---------------------------------------------------------------------------

class TestOkPathExecutorNotePropagation:
    """When ``ExecutorAbc`` returns OK with a note in the
    ``_OK_PATH_PROPAGATED_NOTES`` set, ``TaskRunner.run_task`` MUST
    surface it on ``RunReport.summary`` so Notion + log consumers can
    branch on operational-environment failures (e.g., Docker SDK
    missing, container down). Trust/manifest annotations like
    ``mock_executor_no_truth_source`` MUST NOT be propagated — those
    live on the AuditPackage manifest's ``executor`` section.
    """

    def _ok_with_notes(
        self, mode: ExecutorMode, notes: tuple[str, ...]
    ) -> ExecutorRunReport:
        return ExecutorRunReport(
            mode=mode,
            status=ExecutorStatus.OK,
            contract_hash="deadbeef" * 8,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(
                success=False,  # pre-flight failure scenario
                is_mock=False,
                error_message="Docker SDK not installed",
                execution_time_s=0.0,
                raw_output_path=None,
            ),
            notes=notes,
        )

    def test_docker_openfoam_preflight_note_surfaces_in_summary(self):
        """A docker_openfoam_preflight_failed note MUST appear in
        ``run_task`` summary so operators see the environment signal
        instead of a generic '❌ Failed' line."""
        run_report = self._ok_with_notes(
            ExecutorMode.DOCKER_OPENFOAM,
            ("docker_openfoam_preflight_failed",),
        )
        executor_abc = MagicMock(spec=DockerOpenFOAMExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        assert "docker_openfoam_preflight_failed" in result.summary
        assert "Executor notes" in result.summary

    def test_mock_truth_source_note_does_NOT_surface_in_summary(self):
        """``mock_executor_no_truth_source`` is a manifest-tier note
        (per T1.b.1), NOT a TaskRunner-summary signal. Surfacing it
        would double-display alongside the §6.1 routing-imposed WARN
        and confuse log readers."""
        run_report = ExecutorRunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.OK,
            contract_hash="deadbeef" * 8,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(
                success=True,
                is_mock=True,
                residuals={"p": 1e-6, "U": 1e-6},
                execution_time_s=0.01,
            ),
            notes=("mock_executor_no_truth_source",),
        )
        executor_abc = MagicMock(spec=MockExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        assert "mock_executor_no_truth_source" not in result.summary
        assert "Executor notes" not in result.summary

    def test_mixed_notes_only_propagates_whitelisted_subset(self):
        """When the ExecutorRunReport carries both whitelisted and
        non-whitelisted notes, only the whitelisted ones reach summary.
        Future-proofs the propagation contract: adding new producers
        cannot accidentally leak unrelated annotations to operators."""
        run_report = self._ok_with_notes(
            ExecutorMode.DOCKER_OPENFOAM,
            ("docker_openfoam_preflight_failed", "mock_executor_no_truth_source"),
        )
        executor_abc = MagicMock(spec=DockerOpenFOAMExecutor)
        executor_abc.execute.return_value = run_report

        runner = _stub_runner(executor_abc)
        result = runner.run_task(_task_spec())

        assert "docker_openfoam_preflight_failed" in result.summary
        assert "mock_executor_no_truth_source" not in result.summary

    def test_legacy_path_no_executor_notes_for_plain_cfdexecutor(self):
        """When ``executor_abc`` is None and ``self._executor`` is a
        plain ``CFDExecutor`` (not FoamAgentExecutor), no ``Executor
        notes`` segment appears — propagation only fires for adapters
        that produce the documented note vocabulary."""
        legacy_executor = MagicMock(spec=["execute"])
        legacy_executor.execute.return_value = ExecutionResult(
            success=True,
            is_mock=False,
            residuals={"p": 1e-6, "U": 1e-6},
            execution_time_s=0.01,
        )
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
            executor=legacy_executor,
            notion_client=notion,
            knowledge_db=db,
        )
        runner._comparator = MagicMock()
        runner._comparator.compare.return_value = MagicMock(passed=True, deviations=[])
        runner._compute_attestation = MagicMock(  # type: ignore[method-assign]
            return_value=MagicMock(overall="ATTEST_NOT_APPLICABLE", checks=[])
        )
        result = runner.run_task(_task_spec())

        assert "Executor notes" not in result.summary

    def test_legacy_foam_agent_executor_path_emits_preflight_note(self):
        """Codex R4 P2-A fix: the legacy ``executor=FoamAgentExecutor()``
        path (used by scripts/p2_acceptance_run.py,
        scripts/phase5_audit_run.py, ui/backend/services/wizard_drivers.py)
        must surface ``docker_openfoam_preflight_failed`` symmetrically
        with the ABC dispatch path. Without this, Docker SDK / container /
        case-dir failures in the production scripts collapse into the
        same generic ``❌ Failed`` summary as a diverged solver."""
        from unittest.mock import patch

        from src.foam_agent_adapter import FoamAgentExecutor

        legacy_executor = FoamAgentExecutor()
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
            executor=legacy_executor,
            notion_client=notion,
            knowledge_db=db,
        )
        runner._comparator = MagicMock()
        runner._comparator.compare.return_value = MagicMock(passed=True, deviations=[])
        runner._compute_attestation = MagicMock(  # type: ignore[method-assign]
            return_value=MagicMock(overall="ATTEST_NOT_APPLICABLE", checks=[])
        )

        # Simulate Docker pre-flight failure: success=False with raw_output_path=None
        preflight_fail = ExecutionResult(
            success=False,
            is_mock=False,
            error_message="Docker SDK not installed",
            execution_time_s=0.0,
            raw_output_path=None,
        )
        with patch.object(FoamAgentExecutor, "execute", return_value=preflight_fail):
            result = runner.run_task(_task_spec())

        assert "docker_openfoam_preflight_failed" in result.summary
        assert "Executor notes" in result.summary

    def test_legacy_foam_agent_runtime_failure_does_NOT_emit_preflight_note(self):
        """A solver-runtime failure (raw_output_path populated) must
        NOT trigger the preflight note on the legacy path — same
        discrimination as the bridge."""
        from unittest.mock import patch

        from src.foam_agent_adapter import FoamAgentExecutor

        legacy_executor = FoamAgentExecutor()
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
            executor=legacy_executor,
            notion_client=notion,
            knowledge_db=db,
        )
        runner._comparator = MagicMock()
        runner._comparator.compare.return_value = MagicMock(passed=True, deviations=[])
        runner._compute_attestation = MagicMock(  # type: ignore[method-assign]
            return_value=MagicMock(overall="ATTEST_NOT_APPLICABLE", checks=[])
        )

        runtime_fail = ExecutionResult(
            success=False,
            is_mock=False,
            error_message="solver diverged",
            execution_time_s=42.1,
            raw_output_path="/tmp/cases/divergent_run",
        )
        with patch.object(FoamAgentExecutor, "execute", return_value=runtime_fail):
            result = runner.run_task(_task_spec())

        assert "docker_openfoam_preflight_failed" not in result.summary
        assert "Executor notes" not in result.summary
