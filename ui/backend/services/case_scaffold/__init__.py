"""Imported-case scaffold service · M5.0 routine path.

Public entry: :func:`scaffold_imported_case`. Given a clean ingest report
plus the canonicalized STL bytes, allocate a case_id, write the imported
case directory tree under ``ui/backend/user_drafts/imported/{case_id}/``
(triSurface + system/sHM stub + manifest), and write the editor-facing
case YAML at ``ui/backend/user_drafts/{case_id}.yaml`` so the existing
``/api/cases/{case_id}/yaml`` route works without modification.
"""
from __future__ import annotations

from .bc_injector import write_shm_stub, write_triSurface
from .manifest_writer import (
    SOURCE_ORIGIN_IMPORTED_USER,
    write_case_manifest,
    write_editor_case_yaml,
)
from .template_clone import (
    DRAFTS_DIR,
    IMPORTED_DIR,
    ScaffoldResult,
    allocate_imported_case_id,
    create_imported_case_dir,
    scaffold_imported_case,
)

__all__ = [
    "DRAFTS_DIR",
    "IMPORTED_DIR",
    "SOURCE_ORIGIN_IMPORTED_USER",
    "ScaffoldResult",
    "allocate_imported_case_id",
    "create_imported_case_dir",
    "scaffold_imported_case",
    "write_case_manifest",
    "write_editor_case_yaml",
    "write_shm_stub",
    "write_triSurface",
]
