"""HybridInitExecutor · ExecutorMode.HYBRID_INIT (P2-T1 skeleton).

Real hybrid-init implementation lands in P2-T4 (DEC-V61-077) — it
requires the SBPS (Surrogate-Backed Pre-Solver) §1 ratification before
the surrogate model can be exercised against real OpenFOAM cases.

Until P2-T4 lands, this skeleton **uniformly** returns
`MODE_NOT_APPLICABLE` per EXECUTOR_ABSTRACTION.md §5.2:

    The invariant requires that the surrogate's contribution is
    washed out by the OpenFOAM solver's convergence. If it isn't, the
    case is malformed for hybrid-init use and the executor MUST return
    a MODE_NOT_APPLICABLE status [...] instead of producing a
    divergent canonical artifact set.

The skeleton's posture: no surrogate exists yet, so no case can satisfy
the §5.1 byte-equality invariant — therefore every case is "malformed
for hybrid-init use" by the strict reading of §5.2. The
`hybrid_init_skeleton_no_surrogate` note distinguishes this skeleton
refusal from a P2-T4-era case-specific refusal.
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

__all__ = ["HybridInitExecutor"]


class HybridInitExecutor(ExecutorAbc):
    """ExecutorMode.HYBRID_INIT — skeleton always returns MODE_NOT_APPLICABLE.

    Per EXECUTOR_ABSTRACTION.md §6.1 + §6.3, when a hybrid-init RunReport
    reaches TrustGate, the gate checks the §5.1 byte-equality invariant
    against a reference docker_openfoam run. The skeleton never
    produces a populated `execution_result`, so TrustGate routing for
    this RunReport is the §6.1 "stub-only" / refusal branch — DEC-V61-074
    sub-scope leaves the routing implementation to P2-T1.b in
    `src/metrics/trust_gate.py`.
    """

    MODE: ClassVar[ExecutorMode] = ExecutorMode.HYBRID_INIT

    _SKELETON_NOTE: ClassVar[str] = "hybrid_init_skeleton_no_surrogate"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_APPLICABLE,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._SKELETON_NOTE,),
        )
