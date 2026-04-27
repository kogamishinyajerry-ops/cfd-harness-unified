"""Pydantic schemas for ``POST /api/import/{case_id}/mesh`` (M6.0)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MeshMode = Literal["beginner", "power"]
FailingCheck = Literal[
    "case_not_found",
    "source_not_imported",
    "gmsh_diverged",
    "cell_cap_exceeded",
    "gmshToFoam_failed",
]


class MeshRequest(BaseModel):
    mesh_mode: MeshMode = Field(
        default="beginner",
        description="Mesh sizing tier. beginner is the default; power "
        "opts in to the finer characteristic length (D6).",
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
