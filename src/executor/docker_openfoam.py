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
        """Delegate to the wrapped CFDExecutor; package the result into a
        RunReport per EXECUTOR_ABSTRACTION §6.1.

        DEC-V61-075 P2-T2.1 (Codex R2 P2 fix): when the wrapped instance
        is a substantialized ``FoamAgentExecutor`` (post-T2.1) it
        exposes ``execute_with_run_report`` which produces the canonical
        RunReport with the ``docker_openfoam_preflight_failed`` note on
        environment failures. Calling that bridge here propagates the
        pre-flight signal to ``TaskRunner(executor_mode=DOCKER_OPENFOAM)``
        and any other ABC-path consumer — without it the note's
        documented branch-point would be invisible to real callers.

        DEC-V61-075 P2-T2.1 (Codex R3 P3 fix): the dispatch uses an
        ``isinstance`` check against the trust-core ``FoamAgentExecutor``
        class rather than ``hasattr``. ``hasattr`` is unsafe here because
        a bare ``MagicMock()`` (no ``spec``) reports every attribute as
        present via its ``__getattr__`` — the bridge branch would fire
        on every test double and skip the legacy ``execute()`` path. The
        ``isinstance`` check correctly recognizes plain ``CFDExecutor``
        Protocol stubs (``MagicMock(spec=["execute"])``, custom
        plug-ins) and falls back to the legacy ``execute()`` + manual
        wrap path. Plug-in adapters that want the bridge inherit
        ``FoamAgentExecutor`` (or a future common base) per
        EXECUTOR_ABSTRACTION §6.4 trust-core boundary.
        """
        wrapped = self._get_wrapped()
        # Lazy import — see _get_wrapped() docstring for the symmetric-lazy
        # rationale; this avoids module-init time circularity with
        # src.foam_agent_adapter (also Plane.EXECUTION).
        from src.foam_agent_adapter import FoamAgentExecutor  # noqa: PLC0415

        if isinstance(wrapped, FoamAgentExecutor):
            return wrapped.execute_with_run_report(task_spec)
        result = wrapped.execute(task_spec)
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=result,
        )
