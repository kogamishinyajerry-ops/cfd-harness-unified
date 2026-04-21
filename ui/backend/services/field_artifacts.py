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
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
# untrusted input (adversary could write an adjacent file with
# timestamp='../../outside'). Require the exact YYYYMMDDTHHMMSSZ format the
# driver emits; reject everything else on both LIST and DOWNLOAD paths.
_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")

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

# SHA256 cache keyed on (abs_path, st_mtime_ns, st_size).
# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
# so rapid-write timestamp collisions within a float's precision are avoided.
_sha_cache: dict[tuple[str, int, int], str] = {}


def sha256_of(path: Path) -> str:
    """Compute (or return cached) SHA256 hex digest for `path`.

    Cache key: (absolute_path, st_mtime_ns, st_size). Nanosecond-precision
    mtime catches rapid-write edge cases that float st_mtime would miss.
    """
    st = path.stat()
    key = (str(path.resolve()), st.st_mtime_ns, st.st_size)
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


def _resolve_artifact_dir(case_id: str, run_label: str) -> Optional[Path]:
    """Validated artifact-dir resolver shared by LIST and DOWNLOAD.

    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
    `timestamp` from the manifest and composed a path without validation,
    letting a malicious manifest `timestamp='../../outside'` cause the
    endpoint to enumerate + hash files outside reports/phase5_fields/.
    Both endpoints now go through this resolver.

    Returns the resolved absolute Path on success, or None if:
    - manifest missing / unreadable
    - timestamp missing, wrong shape, or contains traversal markers
    - artifact_dir does not exist
    - artifact_dir.resolve() escapes reports/phase5_fields/{case_id}/
    """
    manifest = _read_run_manifest(case_id, run_label)
    if manifest is None:
        return None
    # Codex round 3 non-blocking #1: manifest must be a dict. Valid-JSON
    # non-objects (list, string, number) would AttributeError on .get() → 500.
    if not isinstance(manifest, dict):
        return None
    timestamp = manifest.get("timestamp", "")
    # Shape gate: accept only YYYYMMDDTHHMMSSZ. Rejects '..', '/', '\\', '.',
    # url-encoded forms, and any other adversary-supplied value.
    if not isinstance(timestamp, str) or not _TIMESTAMP_RE.match(timestamp):
        return None
    root = _current_fields_root()
    try:
        root_resolved = root.resolve()
    except (OSError, RuntimeError):
        return None
    artifact_dir = root / case_id / timestamp
    if not artifact_dir.is_dir():
        return None
    try:
        artifact_dir_resolved = artifact_dir.resolve()
        # Must stay under root/case_id — additional containment check.
        artifact_dir_resolved.relative_to(root_resolved)
    except (ValueError, OSError):
        return None
    return artifact_dir_resolved


def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
    """Build the JSON manifest for a run_id. Returns None if no data exists
    OR if the manifest's `timestamp` fails the shape/traversal gate."""
    case_id, run_label = parse_run_id(run_id)
    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
    if artifact_dir_resolved is None:
        return None
    manifest = _read_run_manifest(case_id, run_label)
    if manifest is None:  # pragma: no cover — resolver already checked
        return None
    timestamp = manifest["timestamp"]  # guaranteed valid by resolver

    items: list[FieldArtifact] = []
    # Walk the whole tree — kind-classify leaves; skip directories.
    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
    # so sample/0/uCenterline.xy, sample/500/uCenterline.xy, sample/1000/... are
    # unique URLs (previously all collapsed to basename and hashes lied).
    for p in sorted(artifact_dir_resolved.rglob("*")):
        if not p.is_file():
            continue
        kind = _classify(p.name)
        if kind is None:
            continue
        # Codex round 3 non-blocking #2: an out-of-dir symlink inside the
        # artifact tree would let .resolve().relative_to(...) raise ValueError.
        # Skip any entry that escapes the artifact dir — fail closed.
        try:
            rel = p.resolve().relative_to(artifact_dir_resolved).as_posix()
        except (ValueError, OSError):
            continue
        items.append(
            FieldArtifact(
                kind=kind,
                filename=rel,
                url=f"/api/runs/{run_id}/field-artifacts/{rel}",
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

    `filename` may be a POSIX relative path (e.g. `sample/500/uCenterline.xy`)
    after Codex round 1 HIGH #1 fix. Traversal defense:
    - reject empty, '.', '..', backslash, url-encoded '..'
    - reject absolute paths (leading '/')
    - reject any '..' segment
    - verify `resolved.relative_to(artifact_dir.resolve())`
    """
    from urllib.parse import unquote as _unquote

    if not filename or filename in (".", ".."):
        raise HTTPException(status_code=404, detail="artifact not found")
    decoded = _unquote(filename)
    if decoded != filename:
        # Double-encoding attempt — be strict.
        raise HTTPException(status_code=404, detail="artifact not found")
    if "\\" in filename or filename.startswith("/"):
        raise HTTPException(status_code=404, detail="artifact not found")
    parts = filename.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise HTTPException(status_code=404, detail="artifact not found")

    case_id, run_label = parse_run_id(run_id)
    # Codex round 2 HIGH: both LIST and DOWNLOAD go through the shared
    # timestamp-validated resolver. Download previously had its own checks;
    # this consolidation removes divergence.
    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
    if artifact_dir_resolved is None:
        raise HTTPException(status_code=404, detail="artifact not found")

    # Compose target and verify it stays inside artifact_dir.
    target = artifact_dir_resolved / filename
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(artifact_dir_resolved)
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="artifact not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    return resolved
