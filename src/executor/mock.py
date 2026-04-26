"""MockExecutor · ExecutorMode.MOCK (P2-T1 skeleton).

Synthetic executor that bypasses Docker + OpenFOAM. Used for tests + UI
demos where the actual numerical truth doesn't matter, only that the
plumbing (TaskSpec → ExecutorAbc → RunReport → TrustGate routing)
works end-to-end.

Per EXECUTOR_ABSTRACTION.md §6.1 the `mock` mode's TrustGate verdict
ceiling is **`WARN`** (never `PASS`), with note
`mock_executor_no_truth_source`. The note is attached to the
`RunReport` here at executor time so downstream TrustGate routing
sees it without needing to special-case mock detection.

P2-T3 (DEC-V61-076) will re-tag the existing
`src.foam_agent_adapter.MockExecutor` (which predates the abstraction)
to use this `MockExecutor`. Until then both classes coexist; the new
one is the canonical `ExecutorMode.MOCK` surface.
"""

from __future__ import annotations

from typing import ClassVar, Dict

from src.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from src.models import ExecutionResult, FlowType, TaskSpec

__all__ = ["MockExecutor"]


# Per-flow-type synthetic presets. Mirrors the existing
# `src.foam_agent_adapter.MockExecutor._PRESET` shape so P2-T3's
# re-tag is mechanical. Values are deliberately non-physical — they
# signal "synthetic" in any audit report that compares them against
# gold standards (combined with `is_mock=True` and the
# `mock_executor_no_truth_source` note).
_PRESETS: Dict[str, Dict[str, object]] = {
    "INTERNAL": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0],
            "mock_preset_marker": True,
        },
    },
    "EXTERNAL": {
        "residuals": {"p": 1e-5, "U": 1e-5},
        "key_quantities": {
            "strouhal_number": 0.165,
            "cd_mean": 1.36,
            "cl_rms": 0.048,
            "mock_preset_marker": True,
        },
    },
    "NATURAL_CONVECTION": {
        "residuals": {"p": 1e-6, "T": 1e-7},
        "key_quantities": {
            "nusselt_number": 4.52,
            "mock_preset_marker": True,
        },
    },
}


class MockExecutor(ExecutorAbc):
    """ExecutorMode.MOCK — TrustGate verdict ceiling = WARN (never PASS).

    The `mock_executor_no_truth_source` note is attached to every
    RunReport this class produces, so downstream TrustGate routing per
    EXECUTOR_ABSTRACTION §6.1 can apply the WARN ceiling without
    special-casing.
    """

    MODE: ClassVar[ExecutorMode] = ExecutorMode.MOCK

    _CEILING_NOTE: ClassVar[str] = "mock_executor_no_truth_source"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        flow_key = task_spec.flow_type.value if isinstance(
            task_spec.flow_type, FlowType
        ) else str(task_spec.flow_type)
        preset = _PRESETS.get(flow_key, _PRESETS["INTERNAL"])
        execution = ExecutionResult(
            success=True,
            is_mock=True,
            residuals=dict(preset["residuals"]),  # type: ignore[arg-type]
            key_quantities=dict(preset["key_quantities"]),  # type: ignore[arg-type]
            execution_time_s=0.01,
            raw_output_path=None,
        )
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=execution,
            notes=(self._CEILING_NOTE,),
        )
