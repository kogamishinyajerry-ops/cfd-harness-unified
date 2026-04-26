"""ExecutorMode abstraction (P2-T1 · DEC-V61-074 skeleton).

Public surface re-exported from this package:

  - `ExecutorMode` — the 4-mode StrEnum (mock / docker_openfoam /
    hybrid_init / future_remote). Stable over P2 milestone — adding a
    new mode requires a §4 contract-surface row + §6.1 routing-table
    row in `docs/specs/EXECUTOR_ABSTRACTION.md`.
  - `ExecutorStatus` — outcome enum (OK / MODE_NOT_APPLICABLE /
    MODE_NOT_YET_IMPLEMENTED). MODE_NOT_APPLICABLE is the §5.2
    invariant-refusal escape; MODE_NOT_YET_IMPLEMENTED is the
    `future_remote` stub-only refusal.
  - `RunReport` — frozen dataclass returned by every
    `ExecutorAbc.execute(...)`. Carries mode + status + execution_result
    + version + contract_hash + notes; the manifest-tagging integration
    (P2-T1.b) will copy these fields into the AuditPackage manifest's
    additive `executor` top-level field.
  - `ExecutorAbc` — abstract base class. Subclass MUST set `MODE`
    classvar + implement `execute(task_spec) -> RunReport`.
  - `MockExecutor` / `DockerOpenFOAMExecutor` / `HybridInitExecutor` /
    `FutureRemoteExecutor` — the 4 concrete subclasses (skeleton
    behavior; P2-T2..T5 fill in real behavior per the migration plan
    in `.planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md`).
  - `SPEC_VERSION` — string constant pinned to the canonical spec
    frontmatter version (currently `"0.2"`).

Plane assignment: `src.executor` → `Plane.EXECUTION` per ADR-001
four-plane contract. This package MUST NOT import from `src.metrics`
(EVALUATION) or other higher planes; downstream consumers (TaskRunner,
TrustGate) import FROM here, not vice versa.
"""

from src.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
    SPEC_VERSION,
)
from src.executor.docker_openfoam import DockerOpenFOAMExecutor
from src.executor.future_remote import FutureRemoteExecutor
from src.executor.hybrid_init import HybridInitExecutor
from src.executor.mock import MockExecutor

__all__ = [
    # Enums + types
    "ExecutorMode",
    "ExecutorStatus",
    "RunReport",
    "ExecutorAbc",
    "SPEC_VERSION",
    # Concrete subclasses (skeleton)
    "DockerOpenFOAMExecutor",
    "MockExecutor",
    "HybridInitExecutor",
    "FutureRemoteExecutor",
]
