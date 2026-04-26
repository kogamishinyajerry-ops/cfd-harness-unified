"""ExecutorMode abstraction · base contract (P2-T1 skeleton · DEC-V61-074).

This module is the canonical implementation of the
`docs/specs/EXECUTOR_ABSTRACTION.md` v0.2 contract surface — specifically:

- §2 `ExecutorMode` enum (4 modes)
- §X.Y / §5 hybrid-init invariant escape: `ExecutorStatus.MODE_NOT_APPLICABLE`
- §X.Z / §6.1 routing inputs: `RunReport.mode` + `RunReport.contract_hash`
  let downstream TrustGate (Plane.EVALUATION) dispatch per-mode without
  knowing about specific executor classes.

Plane assignment: `src.executor` → `Plane.EXECUTION`
(see `src/_plane_assignment.py`). This module MUST NOT import from
`src.metrics`, `src.knowledge_db`, `src.report_engine`, etc. — that
direction would cross plane boundaries (per ADR-001 four-plane
contract).

Trust-core 5 modules (`src.gold_standards`, `src.auto_verifier`,
`src.convergence_attestor`, `src.audit_package`, `src.foam_agent_adapter`)
are read-only consumers from this package's perspective: P2-T1 wraps
them, never modifies them. P2-T1.b (next DEC) will land the additive
`executor` field on `src.audit_package.manifest.SCHEMA_VERSION = 1`
under separate Codex pre-merge review.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Optional, Tuple

from src.models import ExecutionResult, TaskSpec

__all__ = [
    "ExecutorMode",
    "ExecutorStatus",
    "RunReport",
    "ExecutorAbc",
    "SPEC_VERSION",
]

# Canonical version string pinned in the spec frontmatter at
# docs/specs/EXECUTOR_ABSTRACTION.md `version: 0.2`. Bumping the spec
# version requires bumping this constant in lockstep.
SPEC_VERSION = "0.2"


class ExecutorMode(str, Enum):
    """The 4 ExecutorModes per EXECUTOR_ABSTRACTION.md §2.

    Inherits from `str` so that the value can be embedded directly in
    serialized manifests (per spike F-3 byte-determinism: `mode` is an
    enum, serialized as its string value).
    """

    MOCK = "mock"
    DOCKER_OPENFOAM = "docker_openfoam"
    HYBRID_INIT = "hybrid_init"
    FUTURE_REMOTE = "future_remote"


class ExecutorStatus(str, Enum):
    """Outcome of an `ExecutorAbc.execute(...)` call.

    `OK` is the only status that produces a populated `execution_result`.
    `MODE_NOT_APPLICABLE` and `MODE_NOT_YET_IMPLEMENTED` indicate the
    executor refused to run; `RunReport.execution_result` is None and
    downstream TrustGate routing per §6.1 must handle the refusal
    explicitly (e.g. surface `mode_not_yet_implemented` in the UI for
    `FUTURE_REMOTE`).
    """

    OK = "ok"
    MODE_NOT_APPLICABLE = "mode_not_applicable"  # §5.2 escape path
    MODE_NOT_YET_IMPLEMENTED = "mode_not_yet_implemented"  # §6.1 stub


@dataclass(frozen=True)
class RunReport:
    """The canonical return type of `ExecutorAbc.execute(...)`.

    Wraps an optional `ExecutionResult` (the existing solver-output
    dataclass from `src.models`) with the mode-routing metadata that
    P2-T1.b will copy into the AuditPackage manifest's additive
    `executor` field.

    `notes` is a tuple (immutable) of operator-visible strings carrying
    routing/audit metadata, e.g.:
      - `("hybrid_init_invariant_unverified",)` when no reference
        docker_openfoam run anchors the case yet (per §6.3).
      - `("mock_executor_no_truth_source",)` for any `MockExecutor`
        result (per §6.1 ceiling).
      - `("future_remote_stub_only",)` for `FutureRemoteExecutor`
        until DEC-V61-078 lands.

    `frozen=True` ensures byte-determinism: a `RunReport` cannot be
    mutated post-construction, so any TrustGate-side logic that hashes
    or serializes it sees a stable shape.
    """

    mode: ExecutorMode
    status: ExecutorStatus
    contract_hash: str
    version: str
    execution_result: Optional[ExecutionResult] = None
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status == ExecutorStatus.OK and self.execution_result is None:
            raise ValueError(
                f"RunReport(mode={self.mode!r}, status=OK) requires a populated "
                "execution_result; got None"
            )
        if self.status != ExecutorStatus.OK and self.execution_result is not None:
            raise ValueError(
                f"RunReport(mode={self.mode!r}, status={self.status!r}) must have "
                "execution_result=None; got a populated ExecutionResult"
            )


class ExecutorAbc(ABC):
    """Abstract base for the 4 ExecutorMode implementations.

    Subclass contract:
      - Set `MODE` ClassVar to one of `ExecutorMode` values.
      - Implement `execute(task_spec) -> RunReport`.

    `contract_hash` is computed from a stable identity tuple
    (mode value + spec version + class qualname). For P2-T1 skeleton
    this is *not* the SHA-256 of a frozen spec file (per §3 ideal);
    that integration lands in P2-T1.b together with manifest tagging.
    The current implementation is identity-stable (same subclass →
    same hash; different subclass → different hash) which is enough
    for the skeleton's tests + downstream routing.

    `VERSION` defaults to `SPEC_VERSION` so all 4 mode classes report
    the same version string in their `RunReport`s. Subclasses MAY
    override to bump independently if a future spec amendment makes
    one mode evolve faster than the others.
    """

    MODE: ClassVar[ExecutorMode]
    VERSION: ClassVar[str] = SPEC_VERSION

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "MODE", None) is None:
            raise TypeError(
                f"{cls.__qualname__} must declare a `MODE: ClassVar[ExecutorMode]`"
            )
        if not isinstance(cls.MODE, ExecutorMode):
            raise TypeError(
                f"{cls.__qualname__}.MODE must be an ExecutorMode value, "
                f"got {type(cls.MODE).__name__}"
            )

    @property
    def contract_hash(self) -> str:
        """SHA-256 hex digest of the executor's identity tuple.

        Same subclass + same spec version → same hash. Different
        subclass → different hash. P2-T1.b will replace this with the
        SHA of the frozen spec file once manifest tagging integrates.
        """
        identity = f"{type(self).__qualname__}|{self.MODE.value}|{self.VERSION}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @abstractmethod
    def execute(self, task_spec: TaskSpec) -> RunReport:
        """Run the executor against `task_spec` and return a `RunReport`.

        Skeleton subclasses (HybridInit, FutureRemote) return
        `MODE_NOT_APPLICABLE` / `MODE_NOT_YET_IMPLEMENTED` reports
        without performing real work. P2-T2..T5 fill in real behavior.
        """
        raise NotImplementedError
