"""Allocate a fresh imported-case_id and create the on-disk directory tree.

Layout:

    ui/backend/user_drafts/{case_id}.yaml          ← editor-facing case YAML
    ui/backend/user_drafts/imported/{case_id}/
        case_manifest.yaml                         ← M5 manifest
        triSurface/{origin_filename}               ← canonical STL bytes
        system/snappyHexMeshDict.stub              ← consumed by M7

The editor-facing ``user_drafts/{case_id}.yaml`` keeps M5.0 fully
compatible with the existing ``GET /api/cases/{case_id}/yaml`` route in
``case_editor.py`` — no schema migration required there.

There is no static OpenFOAM template directory in this repo; cases are
generated at runtime by ``src/foam_agent_adapter._generate_*`` (line-B
trust-core surface). M5.0 does NOT call into that surface — it borrows
LDC's default solver/materials choices into the editor YAML so the user
can iterate, and leaves real case generation to M7.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import trimesh

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.geometry_ingest import IngestReport, canonical_stl_bytes
from ui.backend.services.validation_report import REPO_ROOT

from .bc_injector import write_shm_stub, write_triSurface
from .manifest_writer import write_case_manifest, write_editor_case_yaml


DRAFTS_DIR = REPO_ROOT / "ui" / "backend" / "user_drafts"
IMPORTED_DIR = DRAFTS_DIR / "imported"


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    case_id: str
    imported_case_dir: Path     # user_drafts/imported/{case_id}/
    triSurface_path: Path       # imported_case_dir / triSurface / origin_filename
    shm_stub_path: Path         # imported_case_dir / system / snappyHexMeshDict.stub
    manifest_path: Path         # imported_case_dir / case_manifest.yaml
    case_yaml_path: Path        # user_drafts / {case_id}.yaml


def allocate_imported_case_id(
    now: datetime | None = None,
    rand_hex: str | None = None,
) -> str:
    """Generate a fresh case_id for an imported case.

    Format: ``imported_YYYY-MM-DDTHH-MM-SSZ_XXXXXXXX`` (UTC; ``-`` rather
    than ``:`` so it satisfies the alphanum + ``_`` + ``-`` traversal
    guard in ``case_drafts.is_safe_case_id``).

    The optional ``now`` and ``rand_hex`` arguments are present for test
    determinism only.
    """
    when = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H-%M-%SZ")
    rand = rand_hex if rand_hex is not None else secrets.token_hex(4)
    case_id = f"imported_{when}_{rand}"
    if not is_safe_case_id(case_id):
        raise ValueError(f"allocator produced unsafe case_id: {case_id!r}")
    return case_id


def create_imported_case_dir(case_id: str) -> Path:
    """Create ``imported/{case_id}/{triSurface,system}/`` and return root."""
    if not is_safe_case_id(case_id):
        raise ValueError(f"unsafe case_id: {case_id!r}")
    root = IMPORTED_DIR / case_id
    (root / "triSurface").mkdir(parents=True, exist_ok=True)
    (root / "system").mkdir(parents=True, exist_ok=True)
    return root


def _safe_origin_filename(origin_filename: str) -> str:
    """Strip path components and unsafe chars from a user-supplied filename."""
    name = Path(origin_filename).name
    if not name:
        raise ValueError("origin_filename is empty after path stripping")
    safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in name)
    if not safe.lower().endswith(".stl"):
        safe = f"{safe}.stl"
    return safe


def scaffold_imported_case(
    *,
    report: IngestReport,
    combined: trimesh.Trimesh,
    origin_filename: str,
    now: datetime | None = None,
    case_id: str | None = None,
    loaded: trimesh.Trimesh | trimesh.Scene | None = None,
) -> ScaffoldResult:
    """Top-level entry: allocate id, create dirs, write all M5 artifacts.

    The route invokes this AFTER ``report.errors`` has been confirmed empty.
    Re-asserted here as a defense in depth.
    """
    if report.errors:
        raise ValueError(
            "scaffold_imported_case called with non-empty report.errors: "
            f"{report.errors!r}"
        )

    cid = case_id or allocate_imported_case_id(now=now)
    safe_filename = _safe_origin_filename(origin_filename)
    root = create_imported_case_dir(cid)

    # Pass the original Scene (when available) + sanitized patch names so a
    # multi-solid STL preserves the inlet/outlet/wall regions the sHM stub
    # references. Falls back to single-mesh binary export when only the
    # combined mesh is available.
    canonical_bytes = canonical_stl_bytes(
        loaded if loaded is not None else combined,
        patch_names=[p.name for p in report.patches] if not report.all_default_faces else None,
    )
    triSurface_path = write_triSurface(
        case_dir=root, origin_filename=safe_filename, canonical_bytes=canonical_bytes
    )
    shm_path = write_shm_stub(case_dir=root, origin_filename=safe_filename, report=report)
    manifest_path = write_case_manifest(
        case_dir=root,
        case_id=cid,
        origin_filename=safe_filename,
        report=report,
        now=now,
    )
    case_yaml_path = write_editor_case_yaml(
        drafts_dir=DRAFTS_DIR,
        case_id=cid,
        origin_filename=safe_filename,
        imported_case_dir=root,
        report=report,
    )

    return ScaffoldResult(
        case_id=cid,
        imported_case_dir=root,
        triSurface_path=triSurface_path,
        shm_stub_path=shm_path,
        manifest_path=manifest_path,
        case_yaml_path=case_yaml_path,
    )
