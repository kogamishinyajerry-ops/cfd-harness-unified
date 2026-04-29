"""YAML I/O for face_annotations.yaml with symlink containment.

Mirrors the ``_bc_source_files()`` symlink-containment pattern from
``ui/backend/services/render/bc_glb.py`` (V61-097 Codex round 1
HIGH-3 closure). Every read/write resolves the case dir with
``Path.resolve(strict=True)`` and asserts the annotations file path
is contained within the case root.

This is a byte-reproducibility-sensitive path per CLAUDE.md
(audit-package canonical bytes), so all serialization uses
``yaml.safe_dump`` with ``sort_keys=True`` and explicit ``default_flow_style``
to keep the output deterministic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "ANNOTATIONS_FILENAME",
    "AnnotationsIOError",
    "AnnotationsRevisionConflict",
    "load_annotations",
    "save_annotations",
]


ANNOTATIONS_FILENAME = "face_annotations.yaml"


class AnnotationsIOError(Exception):
    """Raised on any IO error: missing case dir, parse error, symlink
    escape, schema-version mismatch.

    Attributes:
        failing_check: short tag suitable for HTTP 4xx error mapping
            (``case_dir_missing`` · ``parse_error`` · ``symlink_escape``
            · ``schema_version_mismatch``).
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


class AnnotationsRevisionConflict(Exception):
    """Raised when a save attempt's ``if_match_revision`` doesn't match
    the on-disk revision (concurrent edit detection).
    """

    def __init__(
        self,
        *,
        attempted_revision: int,
        current_revision: int,
    ) -> None:
        self.attempted_revision = attempted_revision
        self.current_revision = current_revision
        super().__init__(
            f"revision mismatch: attempted if_match_revision="
            f"{attempted_revision}, current on-disk revision="
            f"{current_revision}. Re-fetch and retry."
        )


def _resolve_annotations_path(case_dir: Path) -> Path:
    """Resolve the annotations path under ``case_dir``, asserting
    it stays within the case root after symlink resolution.

    Mirrors ``_bc_source_files()`` from ``bc_glb.py``.

    Raises:
        AnnotationsIOError: with ``failing_check="case_dir_missing"``
            if the case dir doesn't exist; ``failing_check="symlink_escape"``
            if the resolved annotations path escapes the case root.
    """
    if not case_dir.exists():
        raise AnnotationsIOError(
            f"case directory does not exist: {case_dir}",
            failing_check="case_dir_missing",
        )

    try:
        case_root = case_dir.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AnnotationsIOError(
            f"could not resolve case directory: {case_dir}: {exc}",
            failing_check="case_dir_missing",
        ) from exc

    annotations_file = case_root / ANNOTATIONS_FILENAME
    # Resolve WITHOUT strict=True because the file may not exist yet
    # on first save. We still want to follow any symlinks in the path.
    try:
        resolved_file = annotations_file.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise AnnotationsIOError(
            f"could not resolve annotations path: {annotations_file}: {exc}",
            failing_check="symlink_escape",
        ) from exc

    # Containment check: resolved file must be under case_root.
    try:
        resolved_file.relative_to(case_root)
    except ValueError as exc:
        raise AnnotationsIOError(
            f"annotations path escapes case root: "
            f"resolved={resolved_file}, case_root={case_root}",
            failing_check="symlink_escape",
        ) from exc

    return resolved_file


def load_annotations(case_dir: Path, *, case_id: str) -> dict[str, Any]:
    """Load the annotations document for a case.

    Returns an empty annotations doc (revision 0, no faces) if the file
    doesn't exist. Caller can ``save_annotations`` it to materialize.

    Args:
        case_dir: the host case directory.
        case_id: the case identifier (used to seed the empty doc and
            verified against the loaded ``case_id`` field).

    Raises:
        AnnotationsIOError: on parse error, schema-version mismatch,
            symlink escape, or case_id mismatch.
    """
    # Lazy import to avoid circular dependency: empty_annotations is
    # in the package __init__ which imports from this module.
    from ui.backend.services.case_annotations import (
        SCHEMA_VERSION,
        empty_annotations,
    )

    path = _resolve_annotations_path(case_dir)

    if not path.exists():
        return empty_annotations(case_id)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AnnotationsIOError(
            f"could not read annotations file: {path}: {exc}",
            failing_check="parse_error",
        ) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AnnotationsIOError(
            f"YAML parse error in {path}: {exc}",
            failing_check="parse_error",
        ) from exc

    if not isinstance(data, dict):
        raise AnnotationsIOError(
            f"annotations file root must be a mapping, got {type(data).__name__}",
            failing_check="parse_error",
        )

    schema_v = data.get("schema_version")
    if schema_v != SCHEMA_VERSION:
        raise AnnotationsIOError(
            f"unsupported schema_version {schema_v!r} in {path}; "
            f"this build expects {SCHEMA_VERSION}",
            failing_check="schema_version_mismatch",
        )

    file_case_id = data.get("case_id")
    if file_case_id != case_id:
        raise AnnotationsIOError(
            f"annotations file case_id={file_case_id!r} does not match "
            f"requested case_id={case_id!r}",
            failing_check="parse_error",
        )

    if not isinstance(data.get("faces"), list):
        raise AnnotationsIOError(
            f"annotations 'faces' field must be a list, got "
            f"{type(data.get('faces')).__name__}",
            failing_check="parse_error",
        )

    if not isinstance(data.get("revision"), int):
        raise AnnotationsIOError(
            f"annotations 'revision' must be an int, got "
            f"{type(data.get('revision')).__name__}",
            failing_check="parse_error",
        )

    return data


def save_annotations(
    case_dir: Path,
    annotations: dict[str, Any],
    *,
    if_match_revision: int | None = None,
) -> dict[str, Any]:
    """Persist the annotations document to disk, bumping ``revision``.

    Concurrency: if ``if_match_revision`` is provided, it is compared
    against the on-disk revision (NOT the in-memory ``annotations``
    revision). If they don't match, ``AnnotationsRevisionConflict`` is
    raised — this is the route's 409 path.

    Args:
        case_dir: the host case directory.
        annotations: the annotations document to write. Its ``revision``
            field is IGNORED for the bump (we read fresh from disk and
            bump from there); ``last_modified`` is overwritten.
        if_match_revision: caller's expected current revision. ``None``
            disables the check (used for the very first save when the
            file does not exist yet).

    Returns:
        The persisted annotations document with the new ``revision``.

    Raises:
        AnnotationsRevisionConflict: if ``if_match_revision`` doesn't
            match the current on-disk revision.
        AnnotationsIOError: on serialization or write failure.
    """
    path = _resolve_annotations_path(case_dir)

    # Determine current on-disk revision. If file missing, treat as 0.
    if path.exists():
        from ui.backend.services.case_annotations import SCHEMA_VERSION

        try:
            existing = yaml.safe_load(path.read_text(encoding="utf-8"))
            current_revision = int(existing.get("revision", 0))
            existing_schema = existing.get("schema_version")
            if existing_schema != SCHEMA_VERSION:
                raise AnnotationsIOError(
                    f"on-disk schema_version {existing_schema!r} does not "
                    f"match runtime {SCHEMA_VERSION}; refusing to overwrite",
                    failing_check="schema_version_mismatch",
                )
        except (OSError, yaml.YAMLError, ValueError, TypeError) as exc:
            raise AnnotationsIOError(
                f"could not read existing annotations to validate "
                f"revision: {path}: {exc}",
                failing_check="parse_error",
            ) from exc
    else:
        current_revision = 0

    if if_match_revision is not None and if_match_revision != current_revision:
        raise AnnotationsRevisionConflict(
            attempted_revision=if_match_revision,
            current_revision=current_revision,
        )

    new_doc = {
        **annotations,
        "revision": current_revision + 1,
        "last_modified": datetime.now(timezone.utc).isoformat(),
    }

    try:
        text = yaml.safe_dump(
            new_doc,
            sort_keys=True,
            default_flow_style=False,
            allow_unicode=True,
        )
    except yaml.YAMLError as exc:
        raise AnnotationsIOError(
            f"could not serialize annotations: {exc}",
            failing_check="parse_error",
        ) from exc

    try:
        # Write atomically: write to .tmp then rename.
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        raise AnnotationsIOError(
            f"could not write annotations to {path}: {exc}",
            failing_check="parse_error",
        ) from exc

    return new_doc
