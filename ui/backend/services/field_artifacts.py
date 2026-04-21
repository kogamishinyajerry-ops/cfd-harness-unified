"""Phase 7a — field artifact service.

Reads the per-run manifest at reports/phase5_fields/{case_id}/runs/{run_label}.json
(written by scripts/phase5_audit_run.py::_write_field_artifacts_run_manifest),
enumerates files in the pointed-to timestamp directory, and serves them via
the FastAPI route in ui/backend/routes/field_artifacts.py.

File-serve pattern mirrors ui/backend/routes/audit_package.py:284-342
(FileResponse + traversal-safe _resolve_bundle_file) per user ratification #1.

Artifact ordering: sort by (kind_order, filename) with kind_order
vtk=0 < csv=1 < residual_log=2 per user ratification #6.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from ui.backend.schemas.validation import (
    FieldArtifact,
    FieldArtifactKind,
    FieldArtifactsResponse,
)
from ui.backend.services.run_ids import parse_run_id

# Repo root: 3 levels up from this file (ui/backend/services/field_artifacts.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"

_FIELDS_ROOT_OVERRIDE: Optional[Path] = None


def _current_fields_root() -> Path:
    return _FIELDS_ROOT_OVERRIDE or _FIELDS_ROOT


def set_fields_root_for_testing(path: Optional[Path]) -> None:
    """Override the reports/phase5_fields/ root (test-only hook)."""
    global _FIELDS_ROOT_OVERRIDE
    _FIELDS_ROOT_OVERRIDE = path
    # Invalidate sha cache when root changes.
    _sha_cache.clear()


_KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}

# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
_sha_cache: dict[tuple[str, float, int], str] = {}


def sha256_of(path: Path) -> str:
    """Compute (or return cached) SHA256 hex digest for `path`.

    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
    return a stale hash — MVP-accepted risk per 07a-RESEARCH.md §2.6.
    """
    st = path.stat()
    key = (str(path.resolve()), st.st_mtime, st.st_size)
    cached = _sha_cache.get(key)
    if cached is not None:
        return cached
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    _sha_cache[key] = digest
    return digest


def _classify(filename: str) -> Optional[FieldArtifactKind]:
    """Map a filename suffix to its kind. Returns None for files we don't surface."""
    low = filename.lower()
    if low.endswith(".vtk") or low.endswith(".vtu") or low.endswith(".vtp"):
        return "vtk"
    if low.endswith(".csv") or low.endswith(".xy") or low.endswith(".dat"):
        # residuals.csv (or anything with 'residual' in the name) is a residual_log.
        if low == "residuals.csv" or "residual" in low:
            return "residual_log"
        return "csv"
    if low.startswith("log.") or low.endswith(".log"):
        return "residual_log"
    return None


def _read_run_manifest(case_id: str, run_label: str) -> Optional[dict]:
    root = _current_fields_root()
    manifest_path = root / case_id / "runs" / f"{run_label}.json"
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
    """Build the JSON manifest for a run_id. Returns None if no data exists."""
    case_id, run_label = parse_run_id(run_id)
    manifest = _read_run_manifest(case_id, run_label)
    if manifest is None:
        return None
    timestamp = manifest.get("timestamp", "")
    if not timestamp:
        return None
    root = _current_fields_root()
    artifact_dir = root / case_id / timestamp
    if not artifact_dir.is_dir():
        return None

    items: list[FieldArtifact] = []
    # Walk the whole tree — kind-classify leaves; skip directories.
    for p in sorted(artifact_dir.rglob("*")):
        if not p.is_file():
            continue
        kind = _classify(p.name)
        if kind is None:
            continue
        # Use basename only in the URL (traversal via URL blocked by route).
        items.append(
            FieldArtifact(
                kind=kind,
                filename=p.name,
                url=f"/api/runs/{run_id}/field-artifacts/{p.name}",
                sha256=sha256_of(p),
                size_bytes=p.stat().st_size,
            )
        )
    items.sort(key=lambda a: (_KIND_ORDER.get(a.kind, 99), a.filename))

    return FieldArtifactsResponse(
        run_id=run_id,
        case_id=case_id,
        run_label=run_label,
        timestamp=timestamp,
        artifacts=items,
    )


def resolve_artifact_path(run_id: str, filename: str) -> Path:
    """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.

    Traversal defense: reject any filename with path separators or '..';
    additionally verify `resolved.relative_to(artifact_dir.resolve())`.
    """
    # Reject anything with path structure or traversal markers.
    if filename in ("", ".", ".."):
        raise HTTPException(status_code=404, detail="artifact not found")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=404, detail="artifact not found")

    case_id, run_label = parse_run_id(run_id)
    manifest = _read_run_manifest(case_id, run_label)
    if manifest is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    timestamp = manifest.get("timestamp", "")
    if not timestamp:
        raise HTTPException(status_code=404, detail="artifact not found")

    root = _current_fields_root()
    artifact_dir = root / case_id / timestamp
    if not artifact_dir.is_dir():
        raise HTTPException(status_code=404, detail="artifact not found")

    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
    # This mirrors audit_package.py's traversal defense.
    for p in artifact_dir.rglob(filename):
        try:
            resolved = p.resolve()
            resolved.relative_to(artifact_dir.resolve())
        except (ValueError, OSError):
            continue
        if resolved.is_file() and resolved.name == filename:
            return resolved
    raise HTTPException(status_code=404, detail="artifact not found")
