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
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Optional, Tuple

from src.models import ExecutionResult, TaskSpec

__all__ = [
    "ExecutorMode",
    "ExecutorStatus",
    "RunReport",
    "ExecutorAbc",
    "SPEC_VERSION",
    "SPEC_FILE_UNAVAILABLE_SENTINEL",
]

# Canonical version string pinned in the spec frontmatter at
# docs/specs/EXECUTOR_ABSTRACTION.md `version: 0.2`. Bumping the spec
# version requires bumping this constant in lockstep.
SPEC_VERSION = "0.2"

# DEC-V61-074 P2-T1.b · spec-file-derived contract_hash
#
# Per EXECUTOR_ABSTRACTION.md §2 + §3 + spike F-3, the manifest's
# `executor.contract_hash` is derived from the FROZEN contract spec
# file — not from the executor class identity. This means a class
# rename / module move does NOT churn signed-manifest bytes, but a
# spec change does (intended — contract evolves, hash advances in
# lockstep).
#
# `_SPEC_FILE` resolves from this module's location. `_executor_spec_sha256`
# is `lru_cache`d so two `contract_hash` calls within the same process
# read the spec file once. The cache key is empty (no args) so we get
# a stable per-process hash; the lifetime is the process lifetime,
# matching the byte-determinism requirement from §3.
_SPEC_FILE: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "specs"
    / "EXECUTOR_ABSTRACTION.md"
)

# Sentinel used when the spec file cannot be read (e.g., installed
# wheel sans docs/). Stable across processes so audit pipelines can
# detect the absence rather than seeing a moving target.
SPEC_FILE_UNAVAILABLE_SENTINEL = "spec_file_unavailable"


@lru_cache(maxsize=1)
def _executor_spec_sha256() -> str:
    """SHA-256 hex of the canonical EXECUTOR_ABSTRACTION.md content
    bytes (process-cached). Returns ``SPEC_FILE_UNAVAILABLE_SENTINEL``
    when the file cannot be read — that branch is reachable in
    deployments that ship without ``docs/`` and is itself stable so
    auditors can detect the absent source without seeing churn.
    """
    try:
        return hashlib.sha256(_SPEC_FILE.read_bytes()).hexdigest()
    except OSError:
        return SPEC_FILE_UNAVAILABLE_SENTINEL


class ExecutorMode(StrEnum):
    """The 4 ExecutorModes per EXECUTOR_ABSTRACTION.md §2.

    `StrEnum` (Python 3.11+) — `str(ExecutorMode.MOCK)` yields `'mock'`
    rather than `'ExecutorMode.MOCK'`. This matches the spec's
    representation: the manifest's `executor.mode` field stores the
    string value verbatim under spike F-3 byte-determinism.
    """

    MOCK = "mock"
    DOCKER_OPENFOAM = "docker_openfoam"
    HYBRID_INIT = "hybrid_init"
    FUTURE_REMOTE = "future_remote"


class ExecutorStatus(StrEnum):
    """Outcome of an `ExecutorAbc.execute(...)` call.

    `OK` is the only status that produces a populated `execution_result`.
    `MODE_NOT_APPLICABLE` and `MODE_NOT_YET_IMPLEMENTED` indicate the
    executor refused to run; `RunReport.execution_result` is None and
    downstream TrustGate routing per §6.1 must handle the refusal
    explicitly (e.g. surface `mode_not_yet_implemented` in the UI for
    `FUTURE_REMOTE`).

    `StrEnum` keeps `str(...)` aligned with the spec value, same
    rationale as `ExecutorMode` above.
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
        # Type guards — frozen dataclass cannot stop callers from passing
        # raw strings ("ok") or list-typed notes; we normalize/reject here
        # so the public contract matches what the docstring + spec promise.
        if not isinstance(self.mode, ExecutorMode):
            raise TypeError(
                f"RunReport.mode must be an ExecutorMode value, "
                f"got {type(self.mode).__name__}={self.mode!r}"
            )
        if not isinstance(self.status, ExecutorStatus):
            raise TypeError(
                f"RunReport.status must be an ExecutorStatus value, "
                f"got {type(self.status).__name__}={self.status!r}"
            )

        # Normalize notes to an immutable tuple. The dataclass field
        # default is already () but callers can pass a list/iterator;
        # frozen=True prevents direct reassignment, so we use the
        # documented `object.__setattr__` escape inside __post_init__.
        #
        # Reject a bare string explicitly *before* iterating: `tuple("hi")`
        # silently char-explodes to `('h', 'i')`, which would corrupt
        # note metadata. Callers passing a single note must wrap it
        # themselves: `notes=("hi",)`.
        if isinstance(self.notes, str):
            raise TypeError(
                f"RunReport.notes must be a tuple of str entries, not a "
                f"bare str. Wrap a single note with a trailing comma: "
                f"got notes={self.notes!r}, expected notes=({self.notes!r},)"
            )
        if not isinstance(self.notes, tuple):
            object.__setattr__(self, "notes", tuple(self.notes))
        for note in self.notes:
            if not isinstance(note, str):
                raise TypeError(
                    f"RunReport.notes entries must be str, "
                    f"got {type(note).__name__}={note!r}"
                )

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
    (mode value + spec version + spec-file SHA-256). Per
    EXECUTOR_ABSTRACTION.md §2 + §3 + spike F-3, the hash is anchored
    to the FROZEN contract spec source (`docs/specs/EXECUTOR_ABSTRACTION.md`),
    not to the executor class identity — class renames / module moves
    do NOT churn signed-manifest bytes; only spec changes do.

    Different `ExecutorMode` values still produce different hashes
    (mode is part of the identity tuple) so §6.3 reference-run
    identity remains falsifiable per-mode.

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
        """SHA-256 hex digest of ``(spec_file_sha256 | MODE | VERSION)``.

        The first component anchors the hash to the canonical
        EXECUTOR_ABSTRACTION.md spec file content (see
        :func:`_executor_spec_sha256`). The second + third differentiate
        modes within the same spec revision so §6.3 reference identity
        is per-mode, per-spec-version.

        Implications (DEC-V61-074 P2-T1.b):

        - Class rename / module move: hash UNCHANGED. Audit-package
          manifests signed before such a refactor still verify; §6.3
          reference-run lookups continue to resolve the same row.
        - Spec amendment (any byte-level change to
          ``docs/specs/EXECUTOR_ABSTRACTION.md``): hash CHANGES for ALL
          modes simultaneously — the contract has moved, every
          previously-signed manifest is now from a prior contract
          revision, which is exactly the audit signal §3/F-3 requires.
        - Different ``MODE`` values: hash DIFFERS (so a hybrid_init
          run can never spuriously satisfy §6.3 against a
          docker_openfoam reference).
        """
        identity = f"{_executor_spec_sha256()}|{self.MODE.value}|{self.VERSION}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @abstractmethod
    def execute(self, task_spec: TaskSpec) -> RunReport:
        """Run the executor against `task_spec` and return a `RunReport`.

        Skeleton subclasses (HybridInit, FutureRemote) return
        `MODE_NOT_APPLICABLE` / `MODE_NOT_YET_IMPLEMENTED` reports
        without performing real work. P2-T2..T5 fill in real behavior.
        """
        raise NotImplementedError
