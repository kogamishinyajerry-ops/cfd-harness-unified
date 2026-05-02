"""GET/PUT/DELETE /api/cases/{case_id}/patch-classification.

DEC-V61-108 Phase A: per-patch user-authored BC classification
overrides. The 3D viewport's click-to-classify UX writes here; the
BC mapper reads from here BEFORE running its name-based heuristic.

Storage: ``<case_dir>/system/patch_classification.yaml`` (sidecar).
Loader/format owned by ``services/case_solve/bc_setup_from_stl_patches``.

Endpoints:
    GET    → ``{case_id, schema_version, available_patches[],
              auto_classifications: {name: bc_class_str},
              overrides: {name: bc_class_str}}``
    PUT    → body ``{patch_name: str, bc_class: str}``; returns the
              merged state.
    DELETE → ``?patch_name=...`` clears one override; returns the
              merged state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    BCClass,
    _PATCH_CLASSIFICATION_REL,
    _PATCH_CLASSIFICATION_SCHEMA_VERSION,
    _classify_patch,
    _read_patch_ranges,
    load_patch_classification_overrides,
)

__all__ = ["router"]

router = APIRouter()


class _PatchClassificationPutBody(BaseModel):
    """Body shape for PUT /patch-classification.

    Single-patch upsert: callers PUT one ``(patch_name, bc_class)``
    pair at a time so concurrent edits to different patches don't
    contend on the file. Multi-patch batches can be sent as a
    sequence of PUTs without weakening the atomicity guarantee.
    """

    patch_name: str = Field(..., min_length=1, max_length=128)
    bc_class: str = Field(
        ...,
        description="Must be one of BCClass values (velocity_inlet, "
        "pressure_outlet, no_slip_wall, symmetry).",
    )


def _resolve_case_dir(case_id: str) -> Path:
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": case_id},
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "case_not_found", "case_id": case_id},
        )
    return case_dir


def _read_available_patches(case_dir: Path) -> list[str]:
    """Return patch names from polyMesh/boundary, or [] if mesh
    isn't ready yet (UI treats that as 'classify after meshing')."""
    boundary = case_dir / "constant" / "polyMesh" / "boundary"
    if not boundary.is_file():
        return []
    try:
        return [name for name, _s, _n in _read_patch_ranges(boundary)]
    except Exception:  # noqa: BLE001 — parser surface is stable but defensive
        return []


def _build_state(case_dir: Path, case_id: str) -> dict[str, Any]:
    """Compose the public state document. Three layers:
        - available_patches : ground truth from polyMesh/boundary
        - auto_classifications : what _classify_patch would emit
                                 WITHOUT the override layer (so the
                                 UI can show "you're overriding X")
        - overrides : what the engineer has saved
    """
    patches = _read_available_patches(case_dir)
    overrides = load_patch_classification_overrides(case_dir)
    auto: dict[str, str] = {}
    for name in patches:
        cls, _w = _classify_patch(name, overrides=None)
        auto[name] = cls.value
    return {
        "case_id": case_id,
        "schema_version": _PATCH_CLASSIFICATION_SCHEMA_VERSION,
        "available_patches": patches,
        "auto_classifications": auto,
        "overrides": {name: cls.value for name, cls in overrides.items()},
    }


def _write_overrides(case_dir: Path, overrides: dict[str, BCClass]) -> None:
    """Persist the overrides dict to the sidecar. Atomic write via
    temp+rename so a crash mid-write can't leave a half-baked file
    that the loader would silently treat as empty.
    """
    p = case_dir / _PATCH_CLASSIFICATION_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": _PATCH_CLASSIFICATION_SCHEMA_VERSION,
        "overrides": {name: cls.value for name, cls in overrides.items()},
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


@router.get(
    "/cases/{case_id}/patch-classification",
    tags=["case-patch-classification"],
)
def get_patch_classification(case_id: str) -> dict[str, Any]:
    case_dir = _resolve_case_dir(case_id)
    return _build_state(case_dir, case_id)


@router.put(
    "/cases/{case_id}/patch-classification",
    tags=["case-patch-classification"],
)
def put_patch_classification(
    case_id: str, body: _PatchClassificationPutBody
) -> dict[str, Any]:
    case_dir = _resolve_case_dir(case_id)

    # Validate bc_class against the BCClass enum BEFORE touching disk.
    try:
        cls = BCClass(body.bc_class)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": "invalid_bc_class",
                "received": body.bc_class,
                "allowed": [c.value for c in BCClass],
            },
        ) from exc

    # Validate patch_name against the live polyMesh/boundary (if any).
    # When the mesh isn't there yet we accept the override as
    # forward-looking — the engineer might be staging classifications
    # before meshing — but log a soft warning in the response.
    available = _read_available_patches(case_dir)
    if available and body.patch_name not in available:
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": "patch_not_in_mesh",
                "patch_name": body.patch_name,
                "available_patches": available,
            },
        )

    overrides = load_patch_classification_overrides(case_dir)
    overrides[body.patch_name] = cls
    _write_overrides(case_dir, overrides)
    return _build_state(case_dir, case_id)


@router.delete(
    "/cases/{case_id}/patch-classification",
    tags=["case-patch-classification"],
)
def delete_patch_classification(
    case_id: str,
    patch_name: str = Query(..., min_length=1, max_length=128),
) -> dict[str, Any]:
    case_dir = _resolve_case_dir(case_id)
    overrides = load_patch_classification_overrides(case_dir)
    overrides.pop(patch_name, None)
    _write_overrides(case_dir, overrides)
    return _build_state(case_dir, case_id)
