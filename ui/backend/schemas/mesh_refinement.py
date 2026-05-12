"""Mesh refinement-zone schema (DEC-V61-136 · N2.2).

Engineer-driven volume refinement zones that locally tighten gmsh's
characteristic length inside a bounding shape (box or sphere). Each
zone supplies a ``level`` (1-3); the gmsh backend translates this to
a scaled ``VIn`` based on whatever the effective base lc is for the
job, then combines all zones with the global CharacteristicLength
sizing via gmsh's ``Min`` field.

Discriminated union (Pydantic) on ``geometry``:

    refinement_zones:
      - {geometry: box, bbox: [xmin, ymin, zmin, xmax, ymax, zmax], level: 2}
      - {geometry: sphere, center: [x, y, z], radius: 0.10, level: 3}

Empty list (or None) = behavior identical to N2.1; back-compat preserved.

Level → lc scale (gmsh field VIn):
    level=1 → effective_lc / 2     (mild refinement)
    level=2 → effective_lc / 4     (medium)
    level=3 → effective_lc / 8     (aggressive)

Cell-budget hard cap (50M) still applies regardless of zones.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator

# Refinement level cap. Higher levels would over-refine to the point
# where gmsh's tetrahedral mesher fights the cell budget cap on every
# call; 3 is industry-customary (Fluent / OpenFOAM blockMesh refinement
# tools cap similarly). Keep ``LEVEL_MAX`` importable for tests.
LEVEL_MIN = 1
LEVEL_MAX = 3


class _ZoneBase(BaseModel):
    """Common fields for all refinement zones."""

    level: int = Field(
        ...,
        ge=LEVEL_MIN,
        le=LEVEL_MAX,
        description="Refinement intensity (1-3). Each level halves "
        "gmsh's characteristic length inside the zone (VIn = "
        "effective_lc * 2**(-level)).",
    )


class BoxRefinementZone(_ZoneBase):
    """Axis-aligned box. ``bbox`` is [xmin, ymin, zmin, xmax, ymax, zmax].

    Validated for non-zero extent on every axis — a zero-volume box
    would produce a no-op gmsh field (silent failure).
    """

    geometry: Literal["box"] = "box"
    bbox: list[float] = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Axis-aligned box extents: "
        "[xmin, ymin, zmin, xmax, ymax, zmax].",
    )

    @model_validator(mode="after")
    def _check_bbox_extent(self) -> "BoxRefinementZone":
        xmin, ymin, zmin, xmax, ymax, zmax = self.bbox
        if not (xmin < xmax and ymin < ymax and zmin < zmax):
            raise ValueError(
                f"box bbox must have positive extent on every axis, got "
                f"x:[{xmin},{xmax}] y:[{ymin},{ymax}] z:[{zmin},{zmax}]"
            )
        return self


class SphereRefinementZone(_ZoneBase):
    """Sphere. ``center`` is [x, y, z], ``radius`` is positive."""

    geometry: Literal["sphere"] = "sphere"
    center: list[float] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Sphere center [x, y, z].",
    )
    radius: float = Field(
        ...,
        gt=0,
        description="Sphere radius (positive).",
    )


# Discriminated union — Pydantic will dispatch on the ``geometry`` field.
MeshRefinementZone = Annotated[
    Union[BoxRefinementZone, SphereRefinementZone],
    Field(discriminator="geometry"),
]


def lc_scale_for_level(level: int) -> float:
    """Map refinement level → gmsh field VIn scale factor.

    Pure helper, importable for tests + frontend tooling parity.
    """
    if not (LEVEL_MIN <= level <= LEVEL_MAX):
        raise ValueError(
            f"refinement level {level} out of range [{LEVEL_MIN},{LEVEL_MAX}]"
        )
    return 2.0 ** (-level)
