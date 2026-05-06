"""Pydantic schemas for ``POST /api/import/{case_id}/mesh`` (M6.0)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ui.backend.schemas.mesh_sizing import MeshSizingField


# Input modes accepted by the /api/import/{case_id}/mesh request.
# "target" is intentionally NOT in this enum — the import-mesh POST
# route does not yet accept target_cell_count; that path is currently
# only reachable via the V124 AI-coach regenerate_mesh tool, which
# uses its own RegenerateMeshArgs schema (see tool_registry.py).
MeshRequestMode = Literal["beginner", "power"]

# Output modes the /api/import/{case_id}/mesh response can report.
# Includes "target" (DEC-V61-124) because mesh_imported_case's
# pipeline labels target_cell_count runs honestly. R2 P1 fix:
# without this expansion, a future caller plumbing target_cell_count
# through to this route would 500 on response-model validation.
# DEC-V61-135 (N2.1) adds "custom" — runs where the request supplied
# a sizing_field rather than (or in addition to) mesh_mode preset.
MeshMode = Literal["beginner", "power", "target", "custom"]

FailingCheck = Literal[
    "case_not_found",
    "source_not_imported",
    "gmsh_diverged",
    "cell_cap_exceeded",
    "gmshToFoam_failed",
]


class MeshRequest(BaseModel):
    mesh_mode: MeshRequestMode = Field(
        default="beginner",
        description="Mesh sizing tier. beginner is the default; power "
        "opts in to the finer characteristic length (D6).",
    )
    sizing_field: MeshSizingField | None = Field(
        default=None,
        description="Engineer-supplied per-job sizing field (DEC-V61-135 · "
        "N2.1). When present, overrides the mesh_mode preset path and "
        "uses base_lc/min_lc/max_lc plus curvature/proximity gmsh "
        "options. Cell-budget hard cap (50M) still applies.",
    )


class MeshSummary(BaseModel):
    cell_count: int
    face_count: int
    point_count: int
    mesh_mode_used: MeshMode
    polyMesh_path: str
    msh_path: str
    generation_time_s: float
    warning: str | None = None


class MeshSuccessResponse(BaseModel):
    case_id: str
    mesh_summary: MeshSummary


class MeshRejection(BaseModel):
    reason: str
    failing_check: FailingCheck
