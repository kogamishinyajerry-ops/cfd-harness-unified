"""DEC-V61-102 Phase 1.1 · case_manifest read/write/migrate.

Reading is migration-aware: any v1 manifest auto-upgrades in memory to
v2 (legacy fields preserved, new sections initialized empty with
``source: ai`` defaults). The on-disk file is NOT rewritten on read —
that would create churn from passive route handlers. The next explicit
write (e.g. after a setup_bc call or a raw-dict edit) flushes v2 shape.

Writing always emits v2 with ``schema_version: 2`` set explicitly.
Field order follows the Pydantic model declaration so YAML diffs stay
human-readable.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    BCPatch,
    BCSection,
    CaseManifest,
    HistoryEntry,
    NumericsSection,
    OverridesSection,
    PhysicsSection,
    RawDictOverride,
)

MANIFEST_FILENAME = "case_manifest.yaml"


class ManifestNotFoundError(FileNotFoundError):
    """Raised when the case directory has no case_manifest.yaml."""


class ManifestParseError(ValueError):
    """Raised when YAML parses but doesn't match either v1 or v2 shape."""


# ---------------------------------------------------------------------------
# Migration v1 → v2
# ---------------------------------------------------------------------------


def _migrate_v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
    """Lossless v1 → v2 migration. Every legacy field is preserved verbatim;
    the new structured sections are added as empty defaults. The migration
    runs in memory only — the on-disk v1 file is untouched until the next
    explicit write.

    v1 detection: ``schema_version`` field absent (or set to 1). v1
    manifests carry top-level keys: ``source``, ``source_origin``,
    ``case_id``, ``origin_filename``, ``ingest_report_summary``,
    ``created_at``, ``solver_version_compat``. All those keys are
    Optional in v2 so they survive the migration unchanged.
    """
    out = dict(raw)
    out["schema_version"] = 2
    # Initialize the new sections as empty if not already present.
    out.setdefault("physics", {})
    out.setdefault("bc", {"patches": {}})
    out.setdefault("numerics", {})
    out.setdefault("overrides", {"raw_dict_files": {}})
    out.setdefault("history", [])
    return out


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def read_case_manifest(case_dir: Path) -> CaseManifest:
    """Load and (if necessary) migrate the manifest at
    ``case_dir / case_manifest.yaml``.

    Raises:
        ManifestNotFoundError: file missing.
        ManifestParseError: YAML parses but fails Pydantic validation.
    """
    path = case_dir / MANIFEST_FILENAME
    if not path.is_file():
        raise ManifestNotFoundError(f"no manifest at {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ManifestParseError(f"YAML parse failed at {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestParseError(
            f"manifest at {path} is not a YAML mapping (got {type(raw).__name__})"
        )
    schema_v = raw.get("schema_version")
    if schema_v is None or schema_v == 1:
        raw = _migrate_v1_to_v2(raw)
    elif schema_v != 2:
        raise ManifestParseError(
            f"unsupported manifest schema_version={schema_v} at {path} "
            f"(this build supports v1 + v2)"
        )
    try:
        return CaseManifest.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — pydantic ValidationError shape is wide
        raise ManifestParseError(
            f"manifest at {path} failed v2 validation: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_case_manifest(case_dir: Path, manifest: CaseManifest) -> Path:
    """Serialize the manifest to YAML at ``case_dir / case_manifest.yaml``.
    Always emits ``schema_version: 2``. Field order follows the Pydantic
    model declaration; ``sort_keys=False`` preserves it for human-readable
    diffs.
    """
    path = case_dir / MANIFEST_FILENAME
    payload = manifest.model_dump(mode="json", exclude_none=False)
    # Drop fields that are still at their factory defaults to keep the
    # YAML compact. Specifically: empty bc.patches / overrides / history
    # are silently OK but writing {} for every section every time is
    # noise. Keep all top-level keys though — schema_version, case_id
    # always there.
    if not payload.get("history"):
        payload.pop("history", None)
    if payload.get("overrides", {}).get("raw_dict_files") == {}:
        payload.pop("overrides", None)
    if payload.get("bc", {}).get("patches") == {}:
        payload.pop("bc", None)

    # Codex round-4 MED #2 closure: atomic write via tempfile + os.replace.
    # Direct path.write_text leaves a torn manifest visible to any
    # concurrent reader if the process crashes mid-write (or the kernel
    # decides to flush only the first half). os.replace on the same
    # filesystem is atomic on POSIX, so readers always see either the
    # old content or the new — never a half-written YAML that
    # ManifestParseError would crash on.
    #
    # Codex round-5 LOW closure: clean up the .tmp file on os.replace
    # failure so we don't leave ``case_manifest.yaml.tmp`` orphaned
    # in the case directory (visible to subsequent operations / exports).
    serialized = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(serialized, encoding="utf-8")
    try:
        os.replace(tmp_path, path)
    except OSError:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
    return path


# ---------------------------------------------------------------------------
# Etag helper
# ---------------------------------------------------------------------------


def compute_etag(content: bytes) -> str:
    """SHA-256-truncated etag for a file's bytes. Used by the
    case_dicts route's GET to advertise the current revision so a
    subsequent POST can race-detect concurrent AI overwrites.
    """
    return hashlib.sha256(content).hexdigest()[:16]


__all__ = [
    "MANIFEST_FILENAME",
    "ManifestNotFoundError",
    "ManifestParseError",
    "read_case_manifest",
    "write_case_manifest",
    "compute_etag",
]
