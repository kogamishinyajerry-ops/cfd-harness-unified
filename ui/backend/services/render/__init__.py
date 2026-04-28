"""Server-side render-data services (M-RENDER-API · DEC-V61-095).

Tier-A scope:
    - geometry_glb · STL → glTF binary transcoding + cache (Step 3 · landed)
    - mesh_wireframe · polyMesh → wireframe glTF (Step 4 · landed)
    - field_sample · scalar field → glTF / binary stream (Step 5 · TODO)

All modules under this package are line-A · declared in ROADMAP commit
8fdb0a3 (Line-A/Line-B isolation contract extension PRE-M-VIZ).
"""
from __future__ import annotations

from .geometry_glb import GeometryRenderError, build_geometry_glb
from .mesh_wireframe import MeshRenderError, build_mesh_wireframe_glb


__all__ = [
    "GeometryRenderError",
    "MeshRenderError",
    "build_geometry_glb",
    "build_mesh_wireframe_glb",
]
