"""DEC-V61-152 (N5.1) · beginner report schema.

5-section structured report capturing the case at a snapshot. The
builder walks case state (geometry / mesh / physics / solver) and
populates each section; the markdown renderer templates the result
into a human-readable file the engineer hands off to a reviewer.

Sections:
  * geometry  — STL file ref, bounding box, named patches
  * mesh      — cell + face counts, mesh-quality summary if available
  * physics   — material name, fluid properties, regime, citations
  * solver    — derived solver name, tolerance tier, URF / scheme
                overrides if any
  * verdict   — rule-based literal: ready_for_review /
                has_open_issues / physics_setup_incomplete /
                mesh_setup_incomplete / geometry_setup_incomplete

Every field on every section is optional: the builder fills what
it can, leaves None when state is absent. The renderer surfaces
None as "(not yet set)" so the reader sees what's missing.

V130 / V132: schema only — no disk write, no AI generation. The
verdict literal is derived by a pure rule function consuming the
populated sections; no LLM call.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


VerdictLiteral = Literal[
    "ready_for_review",
    "has_open_issues",
    "physics_setup_incomplete",
    "mesh_setup_incomplete",
    "geometry_setup_incomplete",
]


class GeometrySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stl_filename: str | None = Field(
        default=None,
        description="Source STL file imported in Step 1.",
    )
    bounding_box_min: tuple[float, float, float] | None = Field(default=None)
    bounding_box_max: tuple[float, float, float] | None = Field(default=None)
    bounding_box_volume: float | None = Field(default=None, ge=0.0)
    named_patches: list[str] = Field(
        default_factory=list,
        description=(
            "Patch names extracted from constant/polyMesh/boundary. "
            "Empty list when mesh hasn't been generated yet."
        ),
    )


class MeshSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_count: int | None = Field(default=None, ge=0)
    point_count: int | None = Field(default=None, ge=0)
    internal_face_count: int | None = Field(default=None, ge=0)
    boundary_face_count: int | None = Field(default=None, ge=0)
    cells_per_unit_volume: float | None = Field(default=None)
    checkmesh_ran: bool = Field(
        default=False,
        description=(
            "True when checkMesh metrics were available at report-build "
            "time. False when checkMesh was skipped (V126 graceful-"
            "degradation path)."
        ),
    )
    checkmesh_ok: bool | None = Field(default=None)
    max_skewness: float | None = Field(default=None, ge=0.0)
    max_non_orthogonality_deg: float | None = Field(default=None, ge=0.0)
    max_aspect_ratio: float | None = Field(default=None, ge=0.0)


class PhysicsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fluid_name: str | None = Field(default=None)
    density: float | None = Field(default=None, gt=0.0)
    kinematic_viscosity: float | None = Field(default=None, gt=0.0)
    prandtl: float | None = Field(default=None, gt=0.0)
    has_thermal: bool = Field(
        default=False,
        description="True when MaterialContract.thermal block is set.",
    )
    regime: str | None = Field(
        default=None,
        description=(
            "RegimeKind literal as a string. None when regime not yet "
            "committed."
        ),
    )
    material_citation: str | None = Field(default=None)
    regime_citation: str | None = Field(default=None)


class SolverSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    derived_solver: str | None = Field(
        default=None,
        description=(
            "N3.4-derived solver name (e.g., 'simpleFoam'). None when "
            "regime not yet committed."
        ),
    )
    derivation_rationale: str | None = Field(default=None)
    tolerance_tier: str | None = Field(
        default=None,
        description=(
            "N3.5-derived tier ('engineering' / 'lab_quality' / "
            "'fast_survey'). None when regime not yet committed."
        ),
    )
    has_solver_overrides: bool = Field(
        default=False,
        description=(
            "True when N4.2 SolverDictsOverride has any non-None field. "
            "Hint for the reader to look at the override diff section."
        ),
    )
    has_urf_overrides: bool = Field(
        default=False,
        description="True when N4.3 URFOverride has any entry.",
    )


class VerdictSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: VerdictLiteral
    reason: str = Field(
        ...,
        description=(
            "Short human-readable reason — derived purely from rule "
            "engine, never AI prose."
        ),
    )


class BeginnerReport(BaseModel):
    """Top-level report container. The markdown renderer templates
    each section in fixed order: geometry → mesh → physics → solver
    → verdict."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    geometry: GeometrySection
    mesh: MeshSection
    physics: PhysicsSection
    solver: SolverSection
    verdict: VerdictSection
    generated_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp the report was built.",
    )


__all__ = [
    "BeginnerReport",
    "GeometrySection",
    "MeshSection",
    "PhysicsSection",
    "SolverSection",
    "VerdictLiteral",
    "VerdictSection",
]
