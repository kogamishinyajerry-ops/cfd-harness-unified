"""Mesh prism-layer schemas (DEC-V61-137 · N2.3).

Engineer-driven boundary-layer prism configuration applied via
``snappyHexMesh`` addLayers stage on top of the gmsh-produced polyMesh.

Per N2.3 charter, v0 supports a single named patch (multi-patch is
deferred to a follow-up sub-DEC to keep the V132 registry surface
narrow on first introduction). The API takes a list shape so a
multi-patch extension lands as data, not API churn.

Pipeline:
    POST /api/import/{case_id}/mesh   → polyMesh (gmsh stage)
    POST /api/import/{case_id}/mesh/prism-layers  → polyMesh refreshed
                                                    with addLayers
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# Reasonable bounds. snappyHexMesh internally caps the layer count
# regardless, but anything > ~20 will explode the local cell count and
# fight the 50M cap layer; rejecting at schema gives an immediate
# 422 instead of a slow gmsh + sHM cycle ending in cell_cap_exceeded.
MAX_LAYER_COUNT = 20
# expansion_ratio < 1.0 inverts (cells get THINNER moving away from
# the wall, contradicting the physical intent), and > 2.0 is rarely
# useful. Match Fluent / starccm+ defaults.
EXPANSION_RATIO_MIN = 1.0
EXPANSION_RATIO_MAX = 2.0


class PatchPrismConfig(BaseModel):
    """Per-patch prism-layer configuration.

    Maps to snappyHexMesh ``addLayersControls.layers.<patch>`` block:
        nSurfaceLayers          ↔ num_layers
        firstLayerThickness     ↔ first_cell_height
        expansionRatio          ↔ expansion_ratio

    All three are required because their interaction (geometric
    progression closure) needs all of them simultaneously; defaulting
    any one to a sentinel would silently mis-mesh near the wall.
    """

    patch: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Patch name (must match a patch present on the "
        "case's existing polyMesh — verified at runtime against "
        "constant/polyMesh/boundary).",
    )
    first_cell_height: float = Field(
        ...,
        gt=0,
        description="Wall-normal thickness of the first layer "
        "(absolute, in case units). snappyHexMesh "
        "``firstLayerThickness``.",
    )
    expansion_ratio: float = Field(
        ...,
        ge=EXPANSION_RATIO_MIN,
        le=EXPANSION_RATIO_MAX,
        description="Geometric expansion ratio between successive "
        "layers (1.0 = uniform, 1.2 typical, 2.0 max sane).",
    )
    num_layers: int = Field(
        ...,
        ge=1,
        le=MAX_LAYER_COUNT,
        description=f"Number of prism layers (1-{MAX_LAYER_COUNT}). "
        "snappyHexMesh ``nSurfaceLayers``.",
    )

    @field_validator("patch")
    @classmethod
    def _patch_name_charset(cls, v: str) -> str:
        # Refuse non-printable / shell-injection-friendly characters.
        # OpenFOAM patch names are alpha/digit/underscore by convention;
        # accept hyphen and dot to match real-world conventions.
        for ch in v:
            if not (ch.isalnum() or ch in ("_", "-", ".")):
                raise ValueError(
                    f"patch name {v!r} has disallowed character {ch!r}; "
                    "expected [A-Za-z0-9_.-]+"
                )
        return v


class MeshPrismLayersRequest(BaseModel):
    """Request body for ``POST /api/import/{case_id}/mesh/prism-layers``.

    v0 (N2.3 initial): list shape but enforces single-element only.
    Multi-patch ships in N2.3-extend; the schema allows the data
    shape to evolve without API churn.
    """

    patches: list[PatchPrismConfig] = Field(
        ...,
        min_length=1,
        description="Per-patch prism configuration. v0 supports "
        "exactly one entry; multi-patch deferred to N2.3-extend.",
    )

    @field_validator("patches")
    @classmethod
    def _v0_single_patch_only(
        cls, v: list[PatchPrismConfig]
    ) -> list[PatchPrismConfig]:
        if len(v) != 1:
            raise ValueError(
                "N2.3 v0 supports exactly one patch; got "
                f"{len(v)} entries. Multi-patch deferred to N2.3-extend."
            )
        # Reject duplicate-patch payloads early (defensive — len==1
        # makes this branch dead today but keeps the invariant
        # intact when N2.3-extend lifts the count limit).
        names = [p.patch for p in v]
        if len(set(names)) != len(names):
            raise ValueError(
                f"duplicate patch names in patches list: {names}"
            )
        return v


PrismFailingCheck = Literal[
    "case_not_found",
    "polyMesh_not_ready",
    "patch_not_found",
    "snappy_diverged",
    "snappy_addlayers_did_not_converge",
    "snappy_container_failed",
]


class PrismLayersSummary(BaseModel):
    """Successful addLayers run summary.

    Cell-count delta reflects the layer addition; layer-coverage is
    the snappyHexMesh-reported fraction of patch faces that received
    the requested number of layers (read from the addLayers log).
    """

    cell_count: int
    face_count: int
    layers_added: int  # nSurfaceLayers actually achieved (may be < requested)
    coverage_fraction: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of patch faces with the full layer "
        "stack (None when log parsing failed).",
    )
    polyMesh_path: str
    log_path: str
    generation_time_s: float


class PrismLayersSuccessResponse(BaseModel):
    case_id: str
    prism_summary: PrismLayersSummary


class PrismLayersRejection(BaseModel):
    reason: str
    failing_check: PrismFailingCheck
