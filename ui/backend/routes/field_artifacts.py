"""Phase 7a — field artifacts route.

GET /api/runs/{run_id}/field-artifacts              → JSON manifest
GET /api/runs/{run_id}/field-artifacts/{filename}   → FileResponse

Pattern mirrors ui/backend/routes/audit_package.py:284-342 (FileResponse +
path-resolver) per user ratification #1. No StaticFiles.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ui.backend.schemas.validation import FieldArtifactsResponse
from ui.backend.services.field_artifacts import (
    list_artifacts,
    resolve_artifact_path,
)

router = APIRouter()


# MIME map — explicit per user ratification #1 rationale (no StaticFiles guessing).
_MEDIA_TYPES: dict[str, str] = {
    ".vtk": "application/octet-stream",
    ".vtu": "application/octet-stream",
    ".vtp": "application/octet-stream",
    ".csv": "text/csv",
    ".xy":  "text/plain; charset=utf-8",
    ".dat": "text/plain; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
}


def _media_type_for(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


@router.get(
    "/runs/{run_id}/field-artifacts",
    response_model=FieldArtifactsResponse,
    tags=["field-artifacts"],
)
def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
    """List field artifacts for a given run_id = '{case}__{run_label}'."""
    resp = list_artifacts(run_id)
    if resp is None:
        raise HTTPException(
            status_code=404,
            detail=f"no field artifacts for run_id={run_id!r}",
        )
    return resp


@router.get(
    "/runs/{run_id}/field-artifacts/{filename:path}",
    tags=["field-artifacts"],
)
def download_field_artifact(run_id: str, filename: str) -> FileResponse:
    """Serve a single field artifact file. Traversal-safe.

    The `{filename:path}` converter allows POSIX sub-paths like
    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
    iteration dirs had basename collision). Traversal is defended in
    resolve_artifact_path.
    """
    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
    return FileResponse(
        path,
        media_type=_media_type_for(path),
        filename=path.name,
    )
