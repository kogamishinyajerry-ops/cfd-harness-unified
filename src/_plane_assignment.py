"""Four-plane SSOT for cfd-harness-unified.

This module is the authoritative source for every top-level ``src.*``
module's plane assignment. Both the static ``.importlinter`` contract
(generated from this table via ``scripts/gen_importlinter.py``) and the
future runtime guard (``src._plane_guard``, ADR-002 W2 Impl Mid) read
from here. Keeping the assignment in one place closes ADR-001 AC-A7
(hand-enumerated brittleness) and ADR-002 §2.2 (shared-SSOT requirement).

Authority: ADR-001 §2.1 (plane assignment) + ADR-002 §2.2 (PLANE_OF
SSOT + byte-identical CI check).

Bootstrap constraint (ADR-002 §4.1 A12): this module imports **only from
stdlib**. Any ``from src.*`` import here would chain-load through a
future ``sys.meta_path`` guard and cause self-recursion. A dedicated
``.importlinter`` contract (``plane-guard-bootstrap-purity``) enforces
the constraint statically; a reverse grep test enforces it in CI.
"""

from __future__ import annotations

from enum import Enum
from typing import Mapping, Optional


class Plane(Enum):
    """Four-plane architecture + shared contracts + runtime-guard bootstrap."""

    CONTROL = "control"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    KNOWLEDGE = "knowledge"
    SHARED = "shared"
    BOOTSTRAP = "bootstrap"


# Ordered SSOT mapping.
#
# Insertion order is preserved (Python 3.7+ dict guarantee) and the
# ``scripts/gen_importlinter.py`` generator iterates in this order to
# produce deterministic, byte-identical ``.importlinter`` output. When
# adding a new top-level ``src.*`` module, insert it into the group that
# reflects its plane and regenerate ``.importlinter``.
PLANE_OF: Mapping[str, Plane] = {
    # ----- Control Plane -----
    "src.task_runner": Plane.CONTROL,
    "src.orchestrator": Plane.CONTROL,
    "src.notion_client": Plane.CONTROL,
    "src.notion_sync": Plane.CONTROL,
    "src.audit_package": Plane.CONTROL,
    # ----- Execution Plane -----
    "src.foam_agent_adapter": Plane.EXECUTION,
    "src.airfoil_surface_sampler": Plane.EXECUTION,
    "src.cylinder_centerline_extractor": Plane.EXECUTION,
    "src.cylinder_strouhal_fft": Plane.EXECUTION,
    "src.airfoil_extractors": Plane.EXECUTION,  # DEC-V61-058 B2
    "src.flat_plate_extractors": Plane.EXECUTION,  # DEC-V61-063 A.1
    "src.plane_channel_uplus_emitter": Plane.EXECUTION,
    "src.wall_gradient": Plane.EXECUTION,
    "src.dhc_extractors": Plane.EXECUTION,
    # ----- Evaluation Plane -----
    "src.comparator_gates": Plane.EVALUATION,
    "src.convergence_attestor": Plane.EVALUATION,
    "src.error_attributor": Plane.EVALUATION,
    "src.result_comparator": Plane.EVALUATION,
    "src.correction_recorder": Plane.EVALUATION,
    "src.auto_verifier": Plane.EVALUATION,
    "src.report_engine": Plane.EVALUATION,
    "src.metrics": Plane.EVALUATION,
    # ----- Knowledge Plane -----
    "src.knowledge_db": Plane.KNOWLEDGE,
    # ----- Shared contracts (type-only, zero src.* deps) -----
    "src.models": Plane.SHARED,
    # ----- Bootstrap (runtime-guard self-hosting, stdlib-only) -----
    "src._plane_assignment": Plane.BOOTSTRAP,
    "src._plane_guard": Plane.BOOTSTRAP,
}


def plane_of(module_name: str) -> Optional[Plane]:
    """Return the ``Plane`` for ``module_name`` or ``None`` if unmapped.

    ``module_name`` is the fully-qualified dotted form (e.g.
    ``"src.task_runner"``). Unmapped names return ``None`` — callers
    (runtime guard, static generator) MUST treat ``None`` as
    ``<external>`` and fall back to a permissive default rather than
    raising.
    """

    return PLANE_OF.get(module_name)


def modules_in(plane: Plane) -> tuple[str, ...]:
    """Return all ``src.*`` modules assigned to ``plane`` in declaration order.

    Used by ``scripts/gen_importlinter.py`` to build contract
    ``source_modules`` / ``forbidden_modules`` lists. Order stability is
    part of the byte-identical CI-check contract; do not change iteration
    order without updating the generator and the reference
    ``.importlinter`` in the same commit.
    """

    return tuple(name for name, p in PLANE_OF.items() if p is plane)
