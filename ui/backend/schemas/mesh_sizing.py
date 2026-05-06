"""Mesh sizing-field schema (DEC-V61-135 · N2.1).

Engineer-driven sizing surface that overrides the single-global-lc paths
(beginner/power preset · target_cell_count · characteristic_length_override)
with a per-job structured field. Maps onto gmsh's
``Mesh.CharacteristicLengthMin/Max`` options plus the curvature-driven
and proximity-driven sizing knobs.

Precedence (when sizing_field is set):
    sizing_field > target_cell_count > characteristic_length_override > preset

The cell-budget guard (cell_budget.py · 50M hard cap) still applies.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MeshSizingField(BaseModel):
    """Per-job sizing-field control. All fields are optional; setting any
    one switches the gmsh sizing path away from preset/target derivation.

    Bounds chosen for safety:
    * ``base_lc / min_lc / max_lc / curvature_target_size`` are positive
      (lt=0 is geometrically nonsense; ==0 disables the corresponding
      gmsh option, but we use ``None`` for that case)
    * ``proximity_layers`` is a small positive integer (gmsh internally
      caps the proximity walk; runaway values just slow meshing)
    """

    base_lc: float | None = Field(
        default=None,
        gt=0,
        description="Nominal characteristic length (gmsh "
        "Mesh.CharacteristicLengthMax baseline). When set, replaces "
        "preset/target_cell_count derivation.",
    )
    min_lc: float | None = Field(
        default=None,
        gt=0,
        description="Lower clamp for gmsh sizing field. Maps to "
        "Mesh.CharacteristicLengthMin.",
    )
    max_lc: float | None = Field(
        default=None,
        gt=0,
        description="Upper clamp for gmsh sizing field. Maps to "
        "Mesh.CharacteristicLengthMax (overrides the base_lc-derived "
        "default if both are set).",
    )
    curvature_target_size: float | None = Field(
        default=None,
        gt=0,
        description="Target element count per 2π of curvature radius. "
        "When set, enables Mesh.MeshSizeFromCurvature and writes "
        "Mesh.MeshSizeFromCurvature value.",
    )
    proximity_layers: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Number of mesh layers gmsh should fit between "
        "neighboring boundary surfaces. When set, enables "
        "Mesh.MeshSizeFromBoundary + Mesh.MeshSizeExtendFromBoundary.",
    )

    @model_validator(mode="after")
    def _check_bounds_consistency(self) -> "MeshSizingField":
        """min_lc ≤ base_lc ≤ max_lc when any pair is set.

        We only validate ordering on values the engineer actually
        supplied — leaving min/max untouched while setting base_lc is
        a valid call shape (gmsh derives sensible bounds from base).
        """
        if self.min_lc is not None and self.max_lc is not None:
            if self.min_lc > self.max_lc:
                raise ValueError(
                    f"min_lc ({self.min_lc}) must be <= max_lc ({self.max_lc})"
                )
        if self.min_lc is not None and self.base_lc is not None:
            if self.min_lc > self.base_lc:
                raise ValueError(
                    f"min_lc ({self.min_lc}) must be <= base_lc ({self.base_lc})"
                )
        if self.base_lc is not None and self.max_lc is not None:
            if self.base_lc > self.max_lc:
                raise ValueError(
                    f"base_lc ({self.base_lc}) must be <= max_lc ({self.max_lc})"
                )
        return self

    def is_active(self) -> bool:
        """True if any field is set — the gmsh runner branches on this."""
        return any(
            v is not None
            for v in (
                self.base_lc,
                self.min_lc,
                self.max_lc,
                self.curvature_target_size,
                self.proximity_layers,
            )
        )
