"""Tests for ExecutorMode + ExecutorAbc + RunReport contract (P2-T1 skeleton).

Covers DEC-V61-074 acceptance criteria 1 + 5: enum membership, ABC
contract enforcement, RunReport invariants, contract_hash determinism.
"""

from __future__ import annotations

import pytest

from src.executor import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
    SPEC_VERSION,
)
from src.executor import (
    DockerOpenFOAMExecutor,
    FutureRemoteExecutor,
    HybridInitExecutor,
    MockExecutor,
)
# -----------------------------------------------------------------------------
# ExecutorMode enum surface
# -----------------------------------------------------------------------------


def test_executor_mode_has_exactly_four_values():
    """EXECUTOR_ABSTRACTION.md §2 specifies 4 modes; adding a 5th
    requires a §4 contract-surface row + §6.1 routing-table row first."""
    assert {m.value for m in ExecutorMode} == {
        "mock",
        "docker_openfoam",
        "hybrid_init",
        "future_remote",
    }


def test_executor_mode_string_values_match_spec_table():
    """Spec §6.1 routing table uses the lowercase-snake-case form."""
    assert ExecutorMode.MOCK.value == "mock"
    assert ExecutorMode.DOCKER_OPENFOAM.value == "docker_openfoam"
    assert ExecutorMode.HYBRID_INIT.value == "hybrid_init"
    assert ExecutorMode.FUTURE_REMOTE.value == "future_remote"


def test_executor_mode_inherits_str_for_byte_determinism():
    """Per spike F-3, the mode is serialized as a plain string in the
    AuditPackage manifest's `executor.mode` field."""
    assert isinstance(ExecutorMode.MOCK, str)
    assert ExecutorMode.MOCK == "mock"


# -----------------------------------------------------------------------------
# ExecutorStatus enum surface
# -----------------------------------------------------------------------------


def test_executor_status_has_exactly_three_values():
    """OK / MODE_NOT_APPLICABLE / MODE_NOT_YET_IMPLEMENTED — adding a
    fourth status requires a §5/§6 spec amendment."""
    assert {s.value for s in ExecutorStatus} == {
        "ok",
        "mode_not_applicable",
        "mode_not_yet_implemented",
    }


# -----------------------------------------------------------------------------
# ExecutorAbc subclass enforcement
# -----------------------------------------------------------------------------


def test_subclass_without_mode_classvar_raises_typeerror():
    """ExecutorAbc.__init_subclass__ enforces MODE: ClassVar[ExecutorMode]."""
    with pytest.raises(TypeError, match=r"must declare a"):

        class BadSubclassNoMode(ExecutorAbc):  # type: ignore[abstract]
            def execute(self, task_spec):  # noqa: ARG002
                raise NotImplementedError


def test_subclass_with_wrong_mode_type_raises_typeerror():
    """MODE must be an ExecutorMode enum value, not a bare string."""
    with pytest.raises(TypeError, match="must be an ExecutorMode value"):

        class BadSubclassStringMode(ExecutorAbc):  # type: ignore[abstract]
            MODE = "mock"  # type: ignore[assignment]

            def execute(self, task_spec):  # noqa: ARG002
                raise NotImplementedError


def test_subclass_must_implement_execute():
    """ABC enforces abstract `execute(task_spec) -> RunReport`."""

    class IncompleteSubclass(ExecutorAbc):
        MODE = ExecutorMode.MOCK

    with pytest.raises(TypeError, match="abstract"):
        IncompleteSubclass()  # type: ignore[abstract]


def test_all_four_concrete_subclasses_have_correct_mode():
    """Each concrete skeleton class wires MODE to the right enum value."""
    assert MockExecutor.MODE == ExecutorMode.MOCK
    assert DockerOpenFOAMExecutor.MODE == ExecutorMode.DOCKER_OPENFOAM
    assert HybridInitExecutor.MODE == ExecutorMode.HYBRID_INIT
    assert FutureRemoteExecutor.MODE == ExecutorMode.FUTURE_REMOTE


def test_all_four_concrete_subclasses_inherit_spec_version():
    """Per base.py default, VERSION = SPEC_VERSION unless a subclass
    explicitly overrides. The skeleton does not override."""
    assert MockExecutor.VERSION == SPEC_VERSION
    assert DockerOpenFOAMExecutor.VERSION == SPEC_VERSION
    assert HybridInitExecutor.VERSION == SPEC_VERSION
    assert FutureRemoteExecutor.VERSION == SPEC_VERSION
    assert SPEC_VERSION == "0.2"


# -----------------------------------------------------------------------------
# contract_hash determinism (per base.py docstring contract)
# -----------------------------------------------------------------------------


def test_contract_hash_same_subclass_same_hash():
    """Two instances of the same ExecutorAbc subclass produce the same
    contract_hash — required for byte-determinism of the manifest's
    `executor.contract_hash` field."""
    h1 = MockExecutor().contract_hash
    h2 = MockExecutor().contract_hash
    assert h1 == h2


def test_contract_hash_differs_across_subclasses():
    """Different ExecutorAbc subclasses MUST produce different
    contract_hash values — otherwise a TrustGate routing decision
    could mistake one mode for another."""
    seen = {
        MockExecutor().contract_hash,
        DockerOpenFOAMExecutor().contract_hash,
        HybridInitExecutor().contract_hash,
        FutureRemoteExecutor().contract_hash,
    }
    assert len(seen) == 4, (
        f"All 4 mode classes must hash distinctly; got {len(seen)} unique hashes"
    )


def test_contract_hash_is_sha256_hex():
    """SHA-256 hex digest = 64 hex chars."""
    h = MockExecutor().contract_hash
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# -----------------------------------------------------------------------------
# RunReport invariants
# -----------------------------------------------------------------------------


def test_run_report_is_frozen():
    """frozen=True ensures byte-determinism: cannot mutate post-construction."""
    report = MockExecutor().execute(_make_minimal_task_spec("INTERNAL"))
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        report.mode = ExecutorMode.DOCKER_OPENFOAM  # type: ignore[misc]


def test_run_report_status_ok_requires_execution_result():
    """Per __post_init__: status=OK + execution_result=None is invalid."""
    with pytest.raises(ValueError, match="status=OK.*requires.*execution_result"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.OK,
            contract_hash="0" * 64,
            version=SPEC_VERSION,
            execution_result=None,
        )


def test_run_report_non_ok_status_forbids_execution_result():
    """Per __post_init__: non-OK + execution_result populated is invalid."""
    from src.models import ExecutionResult

    bogus_result = ExecutionResult(success=True, is_mock=True)
    with pytest.raises(ValueError, match="must have execution_result=None"):
        RunReport(
            mode=ExecutorMode.HYBRID_INIT,
            status=ExecutorStatus.MODE_NOT_APPLICABLE,
            contract_hash="0" * 64,
            version=SPEC_VERSION,
            execution_result=bogus_result,
        )


def test_run_report_default_notes_is_empty_tuple():
    """Default notes = empty tuple (not None) for forward-compat."""
    from src.models import ExecutionResult

    report = RunReport(
        mode=ExecutorMode.MOCK,
        status=ExecutorStatus.OK,
        contract_hash="0" * 64,
        version=SPEC_VERSION,
        execution_result=ExecutionResult(success=True, is_mock=True),
    )
    assert report.notes == ()


def test_run_report_normalizes_list_notes_to_tuple():
    """Codex PC-3-style hardening: callers may pass a list, but the
    contract is "immutable tuple". __post_init__ normalizes."""
    from src.models import ExecutionResult

    report = RunReport(
        mode=ExecutorMode.MOCK,
        status=ExecutorStatus.OK,
        contract_hash="0" * 64,
        version=SPEC_VERSION,
        execution_result=ExecutionResult(success=True, is_mock=True),
        notes=["alpha", "beta"],  # type: ignore[arg-type]
    )
    assert isinstance(report.notes, tuple)
    assert report.notes == ("alpha", "beta")


def test_run_report_rejects_non_str_notes():
    """Notes must be string entries — type-check enforced."""
    from src.models import ExecutionResult

    with pytest.raises(TypeError, match="notes entries must be str"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.OK,
            contract_hash="0" * 64,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(success=True, is_mock=True),
            notes=("ok", 123),  # type: ignore[arg-type]
        )


def test_run_report_rejects_bare_string_notes_to_avoid_char_explosion():
    """Codex P2-T1.a R2 finding: a bare-string notes value would be
    silently char-exploded by `tuple("alpha")` → ('a','l','p','h','a').
    __post_init__ must reject the bare-string form explicitly."""
    from src.models import ExecutionResult

    with pytest.raises(TypeError, match="not a bare str"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.OK,
            contract_hash="0" * 64,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(success=True, is_mock=True),
            notes="alpha",  # type: ignore[arg-type]
        )


def test_run_report_rejects_raw_string_status():
    """Per Codex finding #2: status must be ExecutorStatus, not str.
    Without this guard, downstream comparisons that use enum identity
    (`status == ExecutorStatus.OK`) silently fail under str inputs."""
    from src.models import ExecutionResult

    with pytest.raises(TypeError, match="status must be an ExecutorStatus"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status="ok",  # type: ignore[arg-type]
            contract_hash="0" * 64,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(success=True, is_mock=True),
        )


def test_run_report_rejects_raw_string_mode():
    """Per Codex finding #2: mode must be ExecutorMode, not str."""
    from src.models import ExecutionResult

    with pytest.raises(TypeError, match="mode must be an ExecutorMode"):
        RunReport(
            mode="mock",  # type: ignore[arg-type]
            status=ExecutorStatus.OK,
            contract_hash="0" * 64,
            version=SPEC_VERSION,
            execution_result=ExecutionResult(success=True, is_mock=True),
        )


def test_run_report_str_mode_yields_value_not_classname():
    """Codex finding #1 verification: str(ExecutorMode.MOCK) == 'mock'
    (StrEnum behavior), not 'ExecutorMode.MOCK' (plain Enum behavior)."""
    assert str(ExecutorMode.MOCK) == "mock"
    assert str(ExecutorMode.DOCKER_OPENFOAM) == "docker_openfoam"
    assert str(ExecutorMode.HYBRID_INIT) == "hybrid_init"
    assert str(ExecutorMode.FUTURE_REMOTE) == "future_remote"


def test_run_report_str_status_yields_value_not_classname():
    """Same StrEnum behavior for ExecutorStatus."""
    assert str(ExecutorStatus.OK) == "ok"
    assert str(ExecutorStatus.MODE_NOT_APPLICABLE) == "mode_not_applicable"
    assert str(ExecutorStatus.MODE_NOT_YET_IMPLEMENTED) == "mode_not_yet_implemented"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_minimal_task_spec(flow_type_value: str):
    """Build a minimal TaskSpec for executor smoke tests.

    Uses the existing src.models.TaskSpec dataclass shape; values are
    deliberately non-physical — these tests only care that the skeleton
    plumbing returns RunReport objects with the right shape.
    """
    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )

    return TaskSpec(
        name="test_minimal",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=FlowType[flow_type_value],
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
    )
