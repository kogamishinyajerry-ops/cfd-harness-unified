"""Top-level orchestration for the snappyHexMesh addLayers stage.

Sequence:
    1. Resolve imported case_id → on-disk path (mirror gmsh pipeline)
    2. Verify gmsh stage produced a polyMesh
    3. Run snappyHexMesh addLayers in cfd-openfoam container
    4. Return :class:`PrismLayersResult`

Errors map to ``failing_check`` enum values matching
``schemas/mesh_prism_layers.py::PrismFailingCheck``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ui.backend.schemas.mesh_prism_layers import PatchPrismConfig
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR

from .snappy_runner import (
    SnappyAddLayersError,
    SnappyContainerError,
    SnappyRunResult,
    run_snappy_addlayers,
)


PrismFailingCheck = Literal[
    "case_not_found",
    "polyMesh_not_ready",
    "patch_not_found",
    "snappy_diverged",
    "snappy_addlayers_did_not_converge",
    "snappy_container_failed",
]


class PrismLayersPipelineError(RuntimeError):
    """Pipeline-level failure with a stable ``failing_check`` tag."""

    def __init__(self, message: str, failing_check: PrismFailingCheck) -> None:
        super().__init__(message)
        self.failing_check: PrismFailingCheck = failing_check


@dataclass(frozen=True, slots=True)
class PrismLayersResult:
    case_id: str
    polyMesh_path: Path
    log_path: Path
    layers_added: int
    coverage_fraction: float | None
    generation_time_s: float


def _resolve_imported_case(case_id: str) -> Path:
    """Return the absolute path to the imported case dir or raise."""
    if not is_safe_case_id(case_id):
        raise PrismLayersPipelineError(
            f"unsafe case_id: {case_id!r}", "case_not_found"
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise PrismLayersPipelineError(
            f"imported case {case_id!r} not found at {case_dir}",
            "case_not_found",
        )
    return case_dir


def apply_prism_layers(
    case_id: str,
    *,
    patches: list[PatchPrismConfig],
    container_name: str | None = None,
) -> PrismLayersResult:
    """Run snappyHexMesh addLayers on the existing polyMesh.

    Raises :class:`PrismLayersPipelineError` whose ``failing_check``
    is one of :data:`PrismFailingCheck`. The route maps each value to
    an HTTP 4xx / 5xx response.
    """
    case_dir = _resolve_imported_case(case_id)

    try:
        if container_name:
            result: SnappyRunResult = run_snappy_addlayers(
                case_host_dir=case_dir,
                patches=patches,
                container_name=container_name,
            )
        else:
            result = run_snappy_addlayers(
                case_host_dir=case_dir,
                patches=patches,
            )
    except SnappyAddLayersError as exc:
        # Discriminate among three user-visible add-layers failure
        # modes via message inspection (the runner uses distinct
        # phrasing per branch). Defaulting to the most general
        # ``snappy_diverged`` is safe — the route returns 422 for all
        # three, only the failing_check label changes.
        msg = str(exc)
        if "polyMesh not ready" in msg:
            check: PrismFailingCheck = "polyMesh_not_ready"
        elif "not present in" in msg:
            check = "patch_not_found"
        elif "no layers were actually added" in msg:
            check = "snappy_addlayers_did_not_converge"
        else:
            check = "snappy_diverged"
        raise PrismLayersPipelineError(msg, check) from exc
    except SnappyContainerError as exc:
        raise PrismLayersPipelineError(
            str(exc), "snappy_container_failed"
        ) from exc

    return PrismLayersResult(
        case_id=case_id,
        polyMesh_path=result.polyMesh_dir,
        log_path=result.log_path,
        layers_added=result.layers_added,
        coverage_fraction=result.coverage_fraction,
        generation_time_s=result.generation_time_s,
    )
