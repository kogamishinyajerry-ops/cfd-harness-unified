"""DEC-V61-122 · MeshQualityReport response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MeshSeverity = Literal["critical", "warning", "info"]


class MeshWarning(BaseModel):
    """One entry in the mesh-quality warnings list.

    `code` is a stable enum so consumers (frontend, AI prompts) can
    pattern-match without parsing free-form text. `message` is human-
    readable — the AI coach surfaces it verbatim in chat.
    """

    severity: MeshSeverity = Field(...)
    code: str = Field(
        ...,
        description=(
            "Stable enum. V1 codes: cell_count_low, bb_collapsed_dim, "
            "patch_zero_faces, dense_mesh, very_high_aspect_ratio_estimate."
        ),
    )
    message: str = Field(...)


class MeshQualityReport(BaseModel):
    """The mesh-quality analyzer's structured output.

    Lightweight V1 — derived purely from polyMesh file parsing. No
    Docker checkMesh metrics (V61-123). Bounding box is the axis-
    aligned BB of the points file; ``cells_per_unit_volume`` is None
    when the BB has a collapsed axis (2D mesh).
    """

    case_id: str
    polymesh_present: bool = Field(
        ...,
        description=(
            "True when polyMesh/{points,owner,boundary} all readable. "
            "False would be a 404 from the route — the report shape is "
            "carried for forward compatibility (V123 may surface "
            "partial reports for in-progress meshing)."
        ),
    )
    cell_count: int = Field(..., ge=0)
    point_count: int = Field(..., ge=0)
    internal_face_count: int = Field(
        ...,
        ge=0,
        description="Face count from polyMesh/neighbour — internal faces only.",
    )
    boundary_face_count: int = Field(
        ...,
        ge=0,
        description=(
            "owner.count − neighbour.count. Boundary faces have no "
            "neighbour cell."
        ),
    )
    bounding_box_min: tuple[float, float, float] = Field(...)
    bounding_box_max: tuple[float, float, float] = Field(...)
    bounding_box_volume: float = Field(
        ...,
        ge=0.0,
        description=(
            "Product of (max − min) per axis. 0.0 when any axis is "
            "collapsed (2D mesh) — a `bb_collapsed_dim` warning is "
            "emitted in that case."
        ),
    )
    cells_per_unit_volume: float | None = Field(
        default=None,
        description=(
            "cell_count / bounding_box_volume. None when BB volume is 0 "
            "(2D mesh) so consumers don't divide by zero."
        ),
    )
    patch_face_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Map from patch name to nFaces from polyMesh/boundary.",
    )
    warnings: list[MeshWarning] = Field(default_factory=list)

    # ────────── DEC-V61-126 · Optional Docker checkMesh fields ──────────
    # All None when the analyzer is invoked without run_checkmesh=True OR
    # when the cfd-openfoam container is unavailable (graceful degradation).
    # When present, sourced directly from `checkMesh` stdout via
    # services/mesh_quality/checkmesh_runner.py. The fields parallel
    # what an experienced engineer expects from Fluent's mesh quality
    # panel — max non-orthogonality, max skewness, max aspect ratio.
    checkmesh_max_non_orthogonality_deg: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Max mesh non-orthogonality in degrees from checkMesh. "
            "Fluent's reject threshold is typically 70°; OpenFOAM "
            "schemes with non-orthogonal corrections handle up to ~75°. "
            "None when checkMesh was not requested or container unavailable."
        ),
    )
    checkmesh_max_skewness: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Max cell skewness from checkMesh (dimensionless). Fluent's "
            "default reject threshold is 0.95; for k-omega SST anything "
            "over 0.7 risks convergence issues. None when not requested."
        ),
    )
    checkmesh_max_aspect_ratio: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Max cell aspect ratio from checkMesh. Boundary-layer prism "
            "stacks legitimately reach ~100; cell counts above 1000 "
            "indicate a problem. None when not requested."
        ),
    )
    checkmesh_mesh_ok: bool | None = Field(
        default=None,
        description=(
            "True when checkMesh reports 'Mesh OK', False when 'Failed N "
            "mesh checks'. None when not requested."
        ),
    )
    checkmesh_n_severe_non_ortho_faces: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Number of faces with non-orthogonality > 70° per checkMesh. "
            "Zero is ideal; any nonzero count typically warrants mesh "
            "smoothing or refinement. None when not requested."
        ),
    )
    checkmesh_failed_checks: list[str] | None = Field(
        default=None,
        description=(
            "List of checkMesh failure messages when mesh_ok=False. "
            "None when not requested OR mesh_ok=True (no failures)."
        ),
    )
