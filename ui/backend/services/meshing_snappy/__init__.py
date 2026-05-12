"""snappyHexMesh integration services (DEC-V61-137 · N2.3).

Companion to ``services/meshing_gmsh/``: where gmsh produces the
volumetric polyMesh, snappyHexMesh adds wall-normal prism layers
(addLayers stage) on top of the existing mesh.

v0 ships with a single-patch addLayers-only flow; castellatedMesh +
snap stages are intentionally OFF in the rendered dict so we operate
on the gmsh-produced polyMesh as-is.
"""
from __future__ import annotations

from .pipeline import PrismLayersPipelineError, apply_prism_layers
from .snappy_runner import (
    SnappyAddLayersError,
    SnappyContainerError,
    SnappyRunResult,
)

__all__ = [
    "PrismLayersPipelineError",
    "SnappyAddLayersError",
    "SnappyContainerError",
    "SnappyRunResult",
    "apply_prism_layers",
]
