"""DEC-V61-122 · MeshQualityReport response schemas."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


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

    # V126 R3 P2: forbid extra keys so OpenAPI emits
    # additionalProperties=false. Combined with the report_kind
    # discriminator below (V126 R4 P2), this makes the route's union
    # response_model `MeshQualityReportV126 | MeshQualityReport`
    # discriminable for schema-driven tooling (openapi-typescript,
    # validators).
    model_config = ConfigDict(extra="forbid")

    # V126 R4+R5 P2: required discriminator. R4 added the field with
    # default="v122"; R5 removed the default so OpenAPI marks the
    # discriminator as required (Pydantic emits it in the `required`
    # array only when there's no default). Schema-driven clients now
    # see report_kind as a required, reliably-discriminating literal.
    # Construction sites (analyze_mesh_quality, tests) must pass
    # report_kind explicitly.
    report_kind: Literal["v122"] = Field(
        ...,
        description=(
            "Schema discriminator. 'v122' = base shape (no checkMesh "
            "fields). MeshQualityReportV126 overrides this to 'v126'."
        ),
    )

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


class MeshQualityReportV126(MeshQualityReport):
    """V126 extension of :class:`MeshQualityReport` that adds
    Docker checkMesh-derived fields. Returned by the route ONLY
    when ``?run_checkmesh=true`` is passed; default V122 callers
    continue to receive the base shape without null checkMesh
    fields (V126 R1 P2 backward-compat contract).

    All checkmesh_* fields can be None when the cfd-openfoam
    container is unavailable (graceful degradation) — the engineer
    still gets the V122 fields plus the explicit
    ``checkmesh_unavailable_reason`` so the UI can surface "checkMesh
    skipped" without conflating it with a real failure.
    """

    # Override the discriminator — see MeshQualityReport.report_kind.
    # Required (no default) per R5 P2 so OpenAPI marks it required.
    report_kind: Literal["v126"] = Field(  # type: ignore[assignment]
        ...,
        description=(
            "Schema discriminator. 'v126' = base shape PLUS checkMesh "
            "fields populated when checkMesh ran successfully (or all "
            "None when the cfd-openfoam container was unavailable)."
        ),
    )

    checkmesh_max_non_orthogonality_deg: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Max mesh non-orthogonality in degrees from checkMesh. "
            "Fluent's reject threshold is typically 70°; OpenFOAM "
            "schemes with non-orthogonal corrections handle up to ~75°. "
            "None when container unavailable / graceful degradation."
        ),
    )
    checkmesh_max_skewness: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Max cell skewness from checkMesh (dimensionless). Fluent's "
            "default reject threshold is 0.95; for k-omega SST anything "
            "over 0.7 risks convergence issues."
        ),
    )
    checkmesh_max_aspect_ratio: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Max cell aspect ratio from checkMesh. Boundary-layer prism "
            "stacks legitimately reach ~100; counts above 1000 indicate "
            "a problem."
        ),
    )
    checkmesh_mesh_ok: bool | None = Field(
        default=None,
        description=(
            "True when checkMesh reports 'Mesh OK', False when 'Failed N "
            "mesh checks'. None when container unavailable."
        ),
    )
    checkmesh_n_severe_non_ortho_faces: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Number of faces with non-orthogonality > 70° per checkMesh. "
            "Zero is ideal; nonzero typically warrants mesh smoothing or "
            "refinement."
        ),
    )
    checkmesh_failed_checks: list[str] | None = Field(
        default=None,
        description=(
            "List of checkMesh failure messages when mesh_ok=False. "
            "None when container unavailable OR mesh_ok=True."
        ),
    )
    checkmesh_n_severe_non_ortho_faces_per_patch: dict[str, int] | None = Field(
        default=None,
        description=(
            "V129a: per-patch breakdown of severely non-orthogonal "
            "faces (>70°) parsed from checkMesh's nonOrthoFaces faceSet "
            "(constant/polyMesh/sets/nonOrthoFaces). Each entry maps a "
            "patch name to the count of severe boundary faces touching "
            "it. Internal faces (id below all patch startFaces) are "
            "dropped — they have no named patch home. None when the "
            "container was unavailable OR no severe faces were found "
            "(matches the existing `n_severe_non_ortho_faces=0` path)."
        ),
    )


# V126 R4 P2: discriminated union for the GET /mesh-quality 200 body.
# Pydantic emits OpenAPI's `discriminator: {propertyName: "report_kind"}`
# so schema-driven tooling (openapi-typescript, validators) cleanly
# selects the correct branch on the wire `report_kind` literal. The
# extended type is listed first so it wins when both literals could
# match (defensive — discriminator already disambiguates).
MeshQualityReportResponse = Annotated[
    Union[MeshQualityReportV126, MeshQualityReport],
    Field(discriminator="report_kind"),
]
