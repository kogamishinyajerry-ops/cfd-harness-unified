"""Top-level orchestration for the gmsh-based meshing pipeline.

Sequence (all on the host except the gmshToFoam call):

    1. Resolve the imported case_id → on-disk paths
    2. Run gmsh on the canonical STL → ``imported.msh``
    3. Apply D6 cell-budget rules — reject early if hard cap exceeded
    4. Run gmshToFoam in the cfd-openfoam container → polyMesh
    5. Return :class:`MeshResult`

Failures at each stage are mapped to a ``failing_check`` enum value so
the route can attach a stable, machine-readable rejection code.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR

from .cell_budget import BudgetVerdict, classify_cell_count
from .gmsh_runner import (
    GmshMeshGenerationError,
    GmshRunResult,
    run_gmsh_on_imported_case,
)
from .to_foam import GmshToFoamError, run_gmsh_to_foam


MeshMode = Literal["beginner", "power"]
FailingCheck = Literal[
    "case_not_found",
    "source_not_imported",
    "gmsh_diverged",
    "cell_cap_exceeded",
    "gmshToFoam_failed",
]


class MeshPipelineError(RuntimeError):
    """Pipeline-level failure with a stable ``failing_check`` tag."""

    def __init__(self, message: str, failing_check: FailingCheck) -> None:
        super().__init__(message)
        self.failing_check: FailingCheck = failing_check


@dataclass(frozen=True, slots=True)
class MeshResult:
    case_id: str
    mesh_mode: MeshMode
    cell_count: int
    face_count: int
    point_count: int
    polyMesh_path: Path
    msh_path: Path
    generation_time_s: float
    warning: str | None  # populated when beginner soft cap is exceeded


def _resolve_imported_case(case_id: str) -> tuple[Path, Path]:
    """Return ``(case_dir, stl_path)`` or raise pipeline error."""
    if not is_safe_case_id(case_id):
        raise MeshPipelineError(
            f"unsafe case_id: {case_id!r}", "case_not_found"
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise MeshPipelineError(
            f"imported case {case_id!r} not found at {case_dir}",
            "case_not_found",
        )
    triSurface = case_dir / "triSurface"
    if not triSurface.is_dir():
        raise MeshPipelineError(
            f"case {case_id!r} has no triSurface/ directory — was it "
            "scaffolded by M5.0?",
            "source_not_imported",
        )
    stls = sorted(p for p in triSurface.iterdir() if p.suffix.lower() == ".stl")
    if not stls:
        raise MeshPipelineError(
            f"no STL found under {triSurface}",
            "source_not_imported",
        )
    return case_dir, stls[0]


def mesh_imported_case(
    case_id: str,
    *,
    mesh_mode: MeshMode = "beginner",
    container_name: str | None = None,
) -> MeshResult:
    """Run the full M6.0 pipeline for the given imported case_id.

    Raises :class:`MeshPipelineError` whose ``failing_check`` attribute
    is one of :data:`FailingCheck`. The route maps each value to an
    HTTP 4xx response.
    """
    case_dir, stl_path = _resolve_imported_case(case_id)
    msh_path = case_dir / "imported.msh"

    try:
        gmsh_result: GmshRunResult = run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=msh_path,
            mesh_mode=mesh_mode,
        )
    except GmshMeshGenerationError as exc:
        raise MeshPipelineError(str(exc), "gmsh_diverged") from exc
    # Other exception types (ModuleNotFoundError when [workbench] isn't
    # installed, OSError on disk failure) are backend / configuration
    # faults — let those bubble as 5xx instead of misattributing them
    # as user-geometry rejections. gmsh_runner is responsible for
    # converting raw gmsh-binding errors into GmshMeshGenerationError.

    verdict: BudgetVerdict = classify_cell_count(gmsh_result.cell_count, mesh_mode)
    if not verdict.ok:
        # Drop the stale .msh so the next attempt is not confused by a
        # leftover oversized mesh file. Codex Round 8 Finding 2: collapse
        # the exists()→unlink() TOCTTOU window via missing_ok=True so a
        # concurrent deletion can't leak a raw FileNotFoundError 500
        # ahead of the structured cap_exceeded rejection.
        msh_path.unlink(missing_ok=True)
        raise MeshPipelineError(
            verdict.rejection_reason or "cell budget exceeded",
            "cell_cap_exceeded",
        )

    try:
        if container_name:
            foam_result = run_gmsh_to_foam(
                case_host_dir=case_dir,
                container_name=container_name,
            )
        else:
            foam_result = run_gmsh_to_foam(case_host_dir=case_dir)
    except GmshToFoamError as exc:
        raise MeshPipelineError(str(exc), "gmshToFoam_failed") from exc
    # Host-side failures escaping run_gmsh_to_foam (tarfile errors,
    # PermissionError, disk full) are not docker / container faults —
    # surface them as 5xx so diagnosis is not misdirected. to_foam.py
    # is responsible for wrapping all docker SDK calls itself.

    return MeshResult(
        case_id=case_id,
        mesh_mode=mesh_mode,
        cell_count=gmsh_result.cell_count,
        face_count=gmsh_result.face_count,
        point_count=gmsh_result.point_count,
        polyMesh_path=foam_result.polyMesh_dir,
        msh_path=msh_path,
        generation_time_s=gmsh_result.generation_time_s,
        warning=verdict.warning,
    )
