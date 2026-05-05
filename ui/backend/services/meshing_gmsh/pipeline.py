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


MeshMode = Literal["beginner", "power", "target"]
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


def _resolve_imported_case(
    case_id: str, *, case_dir_override: Path | None = None
) -> tuple[Path, Path]:
    """Return ``(case_dir, stl_path)`` or raise pipeline error.

    Codex base-review-4 P1: callers that have already pinned the
    case directory (via case_lock, dir_fd, or otherwise validated
    its inode) can pass ``case_dir_override`` to bypass the
    ``IMPORTED_DIR / case_id`` re-resolution, ensuring the meshing
    pipeline operates on the SAME inode the caller's lock pins. The
    AI-coach regenerate_mesh path uses this so a rename/recreate
    race between case_lock(case_dir) acquisition and pipeline entry
    cannot redirect the write to a different (replacement) inode
    while the lock still references the original.
    """
    if not is_safe_case_id(case_id):
        raise MeshPipelineError(
            f"unsafe case_id: {case_id!r}", "case_not_found"
        )
    case_dir = case_dir_override if case_dir_override is not None else IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise MeshPipelineError(
            f"imported case {case_id!r} not found at {case_dir}",
            "case_not_found",
        )
    triSurface = case_dir / "triSurface"
    # Codex R9 Finding 3: collapse the is_dir()→iterdir() TOCTTOU
    # window. If the directory disappears between the two syscalls
    # (concurrent cleanup, fs error after moment-of-check), the
    # raised FileNotFoundError used to escape as a raw 500 instead
    # of the structured source_not_imported MeshPipelineError. Try
    # iterdir() directly and treat NotADirectoryError /
    # FileNotFoundError as the same "case lost its triSurface dir"
    # signal the explicit check produced.
    try:
        stls = sorted(
            p for p in triSurface.iterdir() if p.suffix.lower() == ".stl"
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise MeshPipelineError(
            f"case {case_id!r} has no triSurface/ directory — was it "
            "scaffolded by M5.0?",
            "source_not_imported",
        ) from exc
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
    target_cell_count: int | None = None,
    characteristic_length_override: float | None = None,
    container_name: str | None = None,
    case_dir_override: Path | None = None,
) -> MeshResult:
    """Run the full M6.0 pipeline for the given imported case_id.

    DEC-V61-124: ``target_cell_count`` is the AI-coach-friendly knob —
    when set it overrides ``mesh_mode``-derived sizing with a cube-
    derived characteristic length (see gmsh_runner._lc_from_cell_count).
    Real cell counts may differ from target by up to +/-50% on
    non-cube geometries. The V61-105 cell-budget guard still bounds
    the result.

    DEC-V61-125: ``characteristic_length_override`` is the engineer
    escape hatch — supplies gmsh's characteristic length directly,
    bypassing both ``mesh_mode`` presets and the V124 cube formula.
    Cell-budget hard cap (50M) still applies. Mutual exclusion with
    ``target_cell_count`` is enforced one layer up at the
    ``RegenerateMeshArgs`` validator.

    Raises :class:`MeshPipelineError` whose ``failing_check`` attribute
    is one of :data:`FailingCheck`. The route maps each value to an
    HTTP 4xx response.
    """
    case_dir, stl_path = _resolve_imported_case(
        case_id, case_dir_override=case_dir_override
    )
    msh_path = case_dir / "imported.msh"

    try:
        gmsh_result: GmshRunResult = run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=msh_path,
            mesh_mode=mesh_mode,
            target_cell_count=target_cell_count,
            characteristic_length_override=characteristic_length_override,
        )
    except GmshMeshGenerationError as exc:
        raise MeshPipelineError(str(exc), "gmsh_diverged") from exc
    # Other exception types (ModuleNotFoundError when [workbench] isn't
    # installed, OSError on disk failure) are backend / configuration
    # faults — let those bubble as 5xx instead of misattributing them
    # as user-geometry rejections. gmsh_runner is responsible for
    # converting raw gmsh-binding errors into GmshMeshGenerationError.

    # V124 R1 P2 + V125: when EITHER target_cell_count OR
    # characteristic_length_override is set, classify under the
    # "target" mode so (a) the beginner soft warning doesn't fire on
    # successful engineer-supplied-sizing runs (engineer asked
    # explicitly), and (b) MeshResult.mesh_mode reports "target"
    # instead of mislabeling as "beginner" (the mesh_mode default
    # kwarg). The hard 50M cap still applies for resource safety.
    # V125 reuses V124's "target" label rather than introducing a 4th
    # MeshMode literal — both are semantically "engineer-supplied
    # sizing"; consumers that need to distinguish the two paths can
    # back-reference the request that triggered the run.
    effective_mode: MeshMode = (
        "target"
        if (
            target_cell_count is not None
            or characteristic_length_override is not None
        )
        else mesh_mode
    )
    verdict: BudgetVerdict = classify_cell_count(
        gmsh_result.cell_count, effective_mode
    )
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
        mesh_mode=effective_mode,
        cell_count=gmsh_result.cell_count,
        face_count=gmsh_result.face_count,
        point_count=gmsh_result.point_count,
        polyMesh_path=foam_result.polyMesh_dir,
        msh_path=msh_path,
        generation_time_s=gmsh_result.generation_time_s,
        warning=verdict.warning,
    )
