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

from ui.backend.schemas.mesh_refinement import MeshRefinementZone
from ui.backend.schemas.mesh_sizing import MeshSizingField
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR

from .cell_budget import BudgetVerdict, classify_cell_count
from .gmsh_runner import (
    GmshMeshGenerationError,
    GmshRunResult,
    RefinementZoneError,
    run_gmsh_on_imported_case,
)
from .to_foam import GmshToFoamError, run_gmsh_to_foam


MeshMode = Literal["beginner", "power", "target", "custom"]
FailingCheck = Literal[
    "case_not_found",
    "source_not_imported",
    "gmsh_diverged",
    "cell_cap_exceeded",
    "gmshToFoam_failed",
    "refinement_zone_invalid",
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
    sizing_field: MeshSizingField | None = None,
    refinement_zones: list[MeshRefinementZone] | None = None,
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

    DEC-V61-135 (N2.1): ``sizing_field`` is the structured per-job
    sizing surface (base/min/max/curvature/proximity). When active
    (``MeshSizingField.is_active() == True``), it takes precedence
    over both ``target_cell_count`` and
    ``characteristic_length_override``; the resulting MeshResult is
    labeled ``mesh_mode="custom"``. Cell-budget hard cap still
    applies.

    DEC-V61-136 (N2.2): ``refinement_zones`` are engineer-supplied
    box / sphere zones layered on top of the sizing path via gmsh's
    Min field combinator. Empty list / None preserves N2.1 behavior
    exactly. Out-of-domain zones (no AABB overlap with the geometry)
    are rejected with ``failing_check=refinement_zone_invalid``.
    Setting ``refinement_zones`` does NOT alone trigger the "custom"
    mode label — the label still tracks ``sizing_field`` activeness so
    UI consumers do not need to disambiguate "preset+zones" from
    "preset+sizing+zones".

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
            sizing_field=sizing_field,
            refinement_zones=refinement_zones,
        )
    except RefinementZoneError as exc:
        # V136 (N2.2): structured user-input rejection — the engineer
        # supplied a zone with no spatial overlap with the case AABB.
        # Distinct failing_check so the UI can surface the offending
        # zone index + AABB without conflating with mesh-divergence.
        raise MeshPipelineError(str(exc), "refinement_zone_invalid") from exc
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
    # V135 (N2.1): "custom" labels the structured-sizing-field path so
    # the UI can distinguish single-knob (target/lc-override) runs from
    # full per-job sizing-field runs. Precedence in the labeling
    # reflects the gmsh_runner precedence: sizing_field takes priority.
    sizing_field_active = sizing_field is not None and sizing_field.is_active()
    if sizing_field_active:
        effective_mode = "custom"
    elif target_cell_count is not None or characteristic_length_override is not None:
        effective_mode = "target"
    else:
        effective_mode = mesh_mode
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

    # B-ext-3 F10 fix (DEC-V61-182): the mesh has been regenerated, so
    # any pre-existing 0/<field> BC files reference patches the new
    # mesh might not have. Invalidate the BC-time directory + clear
    # manifest user-overrides for those files, forcing the engineer
    # to re-run setup-bc against the fresh mesh. This prevents the
    # /mesh-after-/setup-bc-then-/solve crash class observed in R6
    # (FOAM FATAL IO ERROR: Cannot find patchField entry for patch0).
    _invalidate_stale_bc_after_mesh_regen(case_dir)

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


def _invalidate_stale_bc_after_mesh_regen(case_dir: Path) -> None:
    """Remove ``0/`` and ``0.orig/`` directories and clear manifest
    user-overrides on those files. Idempotent: missing dirs / missing
    manifest are silently OK.

    Called from mesh_imported_case after a successful gmshToFoam to
    invalidate stale BC field files (``0/p``, ``0/U``, etc.) whose
    patch-name keys no longer match the freshly regenerated polyMesh.

    Engineer-facing contract: after /mesh, the engineer must re-run
    /setup-bc; this is documented in setup-bc descriptions and the
    actions catalogue (DEC-V61-182).
    """
    import shutil

    for stale_dir_name in ("0", "0.orig"):
        stale = case_dir / stale_dir_name
        if stale.is_dir():
            try:
                shutil.rmtree(stale)
            except OSError:
                # Best-effort; if rmtree fails the pre-flight check in
                # solver_runner._check_mesh_bc_consistency will still
                # surface the inconsistency to the caller.
                pass

    # Clear 0/* user-override entries in the manifest so the next
    # setup-bc run authors fresh BC files from AI defaults instead of
    # respecting stale source=user entries that no longer have backing
    # disk files. Best-effort: if the manifest is missing or unreadable
    # we silently skip — solver_runner pre-flight is the load-bearing
    # check.
    try:
        from ui.backend.services.case_manifest.io import (
            ManifestNotFoundError,
            ManifestParseError,
            read_case_manifest,
            write_case_manifest,
        )

        manifest = read_case_manifest(case_dir)
    except (ManifestNotFoundError, ManifestParseError):
        return
    overrides = manifest.overrides
    raw = overrides.raw_dict_files
    stale_keys = [k for k in raw if k.startswith("0/")]
    if not stale_keys:
        return
    for k in stale_keys:
        del raw[k]
    write_case_manifest(case_dir, manifest)
