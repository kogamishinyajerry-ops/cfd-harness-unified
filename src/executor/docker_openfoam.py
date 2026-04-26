"""DockerOpenFOAMExecutor · ExecutorMode.DOCKER_OPENFOAM (P2-T1 skeleton).

Wraps `src.foam_agent_adapter.FoamAgentExecutor` (real Docker + OpenFOAM
solver) without modifying it. P2-T2 (DEC-V61-075) will replace the
delegation with the formal docker-openfoam wrapping per the
EXECUTOR_ABSTRACTION compatibility-spike F-3 migration plan.

`src.foam_agent_adapter` is a trust-core module (see §10 trust-core 5).
This skeleton imports from it but does NOT modify it — read-only
consumption per the P2-T1.a sub-scope rationale in DEC-V61-074.
"""

from __future__ import annotations

from typing import ClassVar, Optional

from src.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from src.models import CFDExecutor, TaskSpec

__all__ = ["DockerOpenFOAMExecutor"]


class DockerOpenFOAMExecutor(ExecutorAbc):
    """ExecutorMode.DOCKER_OPENFOAM — full triad TrustGate verdict surface.

    Per EXECUTOR_ABSTRACTION.md §6.1:
      `docker_openfoam` → full triad `PASS / WARN / FAIL`. The
      case-profile `tolerance_policy` resolves the verdict via
      METRICS_AND_TRUST_GATES.

    This skeleton wraps an injectable `CFDExecutor` (production:
    `FoamAgentExecutor`; test: any Protocol-compliant stub). Wrapping
    keeps the skeleton testable without Docker, and lets P2-T2 swap in
    the real adapter cleanly.
    """

    MODE: ClassVar[ExecutorMode] = ExecutorMode.DOCKER_OPENFOAM

    def __init__(self, wrapped: Optional[CFDExecutor] = None) -> None:
        """Inject an optional `CFDExecutor` Protocol implementation.

        `wrapped=None` defers `FoamAgentExecutor()` construction until
        `execute()` is first called (lazy import to avoid pulling in
        `docker` at import time when callers may not have it
        installed). P2-T2 will revisit this lazy-init pattern.
        """
        self._wrapped = wrapped

    def _get_wrapped(self) -> CFDExecutor:
        if self._wrapped is None:
            from src.foam_agent_adapter import FoamAgentExecutor
            self._wrapped = FoamAgentExecutor()
        return self._wrapped

    def execute(self, task_spec: TaskSpec) -> RunReport:
        """Delegate to the wrapped CFDExecutor; package its
        ExecutionResult into a RunReport(status=OK) per
        EXECUTOR_ABSTRACTION §6.1."""
        result = self._get_wrapped().execute(task_spec)
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=result,
        )
