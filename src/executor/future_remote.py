"""FutureRemoteExecutor · ExecutorMode.FUTURE_REMOTE (P2-T1 skeleton).

Per EXECUTOR_ABSTRACTION.md §6.1 the `future_remote` mode is stub-only
this milestone:

    `future_remote` | (stub-only this milestone) | TrustGate refuses
    to score a `future_remote` manifest. The CLI/UI surfaces
    `mode_not_yet_implemented`. DEC-V61-078 sets the real contract.

This skeleton therefore returns `MODE_NOT_YET_IMPLEMENTED` for every
`task_spec`. P2-T5 (DEC-V61-078) will document the HPC contract; no
real implementation lands this milestone — the §6.1 routing-table
guarantee is "TrustGate refuses to score", not "executor produces a
verdict".
"""

from __future__ import annotations

from typing import ClassVar

from src.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from src.models import TaskSpec

__all__ = ["FutureRemoteExecutor"]


class FutureRemoteExecutor(ExecutorAbc):
    """ExecutorMode.FUTURE_REMOTE — TrustGate refuses to score (§6.1)."""

    MODE: ClassVar[ExecutorMode] = ExecutorMode.FUTURE_REMOTE

    _STUB_NOTE: ClassVar[str] = "future_remote_stub_only"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._STUB_NOTE,),
        )
