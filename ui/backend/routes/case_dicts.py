"""DEC-V61-102 Phase 1.2 · raw OpenFOAM dict GET/POST routes.

These two endpoints are the engineer's escape hatch when AI-authored
dicts need manual correction. The path allowlist
(:mod:`ui.backend.services.case_dicts.allowlist`) limits exposure to a
curated set of system/ + constant/ files; 0/ field files are
deliberately excluded since they're face_id-coupled and a structured
editor will land in M-RESCUE Phase 4.

Round-trip contract:

* ``GET /api/cases/{case_id}/dicts/{path:path}`` →
  ``{content, source, etag, edited_at}``. ``source`` is "ai" or "user"
  per the manifest. ``etag`` is SHA-256-truncated for race protection.
* ``POST /api/cases/{case_id}/dicts/{path:path}`` body
  ``{content, expected_etag?, force?}`` → 200 with new etag, 409 on
  etag mismatch, 422 on validation failure (unless force=true).

Every successful POST records a ``source: user`` override in the
manifest (see :mod:`ui.backend.services.case_manifest.overrides`).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ui.backend.services.case_dicts.allowlist import is_allowed
from ui.backend.services.case_dicts.validator import (
    has_errors,
    validate_raw_dict,
)
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_manifest import (
    CaseLockError,
    ManifestNotFoundError,
    case_lock,
    compute_etag,
    is_user_override,
    mark_user_override,
    read_case_manifest,
)
from ui.backend.services.case_scaffold import IMPORTED_DIR

router = APIRouter()


# ---------------------------------------------------------------------------
# Wire shapes
# ---------------------------------------------------------------------------


class RawDictGetResponse(BaseModel):
    case_id: str
    path: str
    content: str
    source: str  # "ai" | "user"
    etag: str
    edited_at: str | None = None  # ISO timestamp if known


class RawDictPostBody(BaseModel):
    content: str = Field(
        ..., description="Full new file content (UTF-8). Replaces existing file atomically."
    )
    expected_etag: str | None = Field(
        None,
        description=(
            "Etag from a prior GET. If set and the on-disk etag differs, the "
            "POST is rejected with 409 so the client can re-fetch and merge."
        ),
    )


class RawDictValidationIssue(BaseModel):
    severity: str
    message: str


class RawDictPostResponse(BaseModel):
    case_id: str
    path: str
    new_etag: str
    source: str = "user"
    warnings: list[RawDictValidationIssue] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------


def _resolve_case_dir(case_id: str) -> Path:
    """Translate a wire case_id into a vetted on-disk path. Identical
    shape to :mod:`ui.backend.routes.case_solve` — keep in sync."""
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


def _resolve_dict_path(case_dir: Path, relative_path: str) -> Path:
    """Allowlist + path-traversal guard. Returns the absolute path or
    raises HTTPException(404)."""
    if not is_allowed(relative_path):
        # Treat disallowed as 404 (not 403) so probing the allowlist
        # doesn't leak which other paths might exist.
        raise HTTPException(
            status_code=404,
            detail={
                "failing_check": "path_not_allowed",
                "path": relative_path,
                "allowed_paths_hint": "see ui.backend.services.case_dicts.allowlist",
            },
        )
    # Defense-in-depth: allowlist already pins the exact strings, but
    # resolve and confirm the resulting absolute path is still under
    # case_dir (guards against path traversal even if allowlist drift
    # ever introduces a relative ../ entry).
    abs_path = (case_dir / relative_path).resolve()
    if not str(abs_path).startswith(str(case_dir.resolve())):
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "path_escape"},
        )
    return abs_path


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


@router.get(
    "/cases/{case_id}/dicts/{relative_path:path}",
    response_model=RawDictGetResponse,
    tags=["case-dicts"],
)
def get_raw_dict(case_id: str, relative_path: str) -> RawDictGetResponse:
    """Read an OpenFOAM dict file from the case directory.

    The frontend RawDictEditor uses this to populate the Monaco editor
    on initial mount and after a successful POST (to advance its etag).
    """
    case_dir = _resolve_case_dir(case_id)
    abs_path = _resolve_dict_path(case_dir, relative_path)
    if not abs_path.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "failing_check": "dict_file_missing",
                "path": relative_path,
                "hint": (
                    "AI may not have authored this file yet — "
                    "run [AI 处理] on the relevant Step first"
                ),
            },
        )
    content_bytes = abs_path.read_bytes()
    etag = compute_etag(content_bytes)

    # Look up source + edited_at from manifest.
    source = "ai"
    edited_at: str | None = None
    try:
        manifest = read_case_manifest(case_dir)
        entry = manifest.overrides.raw_dict_files.get(relative_path)
        if entry is not None:
            source = entry.source
            edited_at = entry.edited_at.isoformat() if entry.edited_at else None
    except ManifestNotFoundError:
        # Pre-manifest cases: source defaults to "ai" (the file was
        # presumably authored by some setup_*_bc call before the
        # manifest schema upgrade landed).
        pass

    return RawDictGetResponse(
        case_id=case_id,
        path=relative_path,
        content=content_bytes.decode("utf-8", errors="replace"),
        source=source,
        etag=etag,
        edited_at=edited_at,
    )


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/dicts/{relative_path:path}",
    response_model=RawDictPostResponse,
    tags=["case-dicts"],
)
def post_raw_dict(
    case_id: str,
    relative_path: str,
    body: RawDictPostBody,
    force: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "When 1, bypass content validation (the 'I know what I'm doing' "
            "path). The edit still records source=user in manifest so the "
            "audit log shows the user opted to bypass."
        ),
    ),
) -> RawDictPostResponse:
    """Write new content to an OpenFOAM dict file. Records the edit in
    the manifest with source=user.

    Race protection: pass ``expected_etag`` from a recent GET. If the
    on-disk file changed in the interim (concurrent AI overwrite), the
    POST returns 409 so the client can re-fetch and merge.
    """
    case_dir = _resolve_case_dir(case_id)
    abs_path = _resolve_dict_path(case_dir, relative_path)

    # Validation runs before the lock — pure CPU, no shared state.
    issues = validate_raw_dict(
        relative_path=relative_path, content=body.content
    )
    if not force and has_errors(issues):
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": "validation_failed",
                "issues": [{"severity": i.severity, "message": i.message} for i in issues],
                "hint": "fix the errors above, or pass ?force=1 to bypass",
            },
        )

    # Codex round-2 P1-HIGH closure: serialize the etag re-check + write +
    # manifest record under the per-case lock. Without this, a setup_*_bc
    # call could write the AI version AFTER our etag check passed but
    # BEFORE our write lands, then mark_ai_authored runs first and ours
    # second — manifest ends up source=user but disk content reflects an
    # interleaved partial. Locking serializes mutations end-to-end.
    new_bytes = body.content.encode("utf-8")
    try:
        with case_lock(case_dir):
            if body.expected_etag is not None and abs_path.is_file():
                current_etag = compute_etag(abs_path.read_bytes())
                if current_etag != body.expected_etag:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "failing_check": "etag_mismatch",
                            "expected_etag": body.expected_etag,
                            "current_etag": current_etag,
                            "hint": (
                                "file changed since last GET; re-fetch and merge before retry"
                            ),
                        },
                    )

            # Write. Make parent dirs if missing (the system/ and constant/
            # directories are normally pre-created by setup_*_bc, but for a
            # bare freshly-imported case the user might want to seed
            # controlDict before any AI run — let them).
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_bytes(new_bytes)

            # Mark the override in the manifest.
            mark_user_override(
                case_dir,
                relative_path=relative_path,
                new_content=new_bytes,
                detail={
                    "force_bypass": bool(force),
                    "size": len(new_bytes),
                },
            )
    except CaseLockError as exc:
        # Codex round-3 MEDIUM: lock-acquisition failure (e.g. planted
        # symlink at .case_lock under O_NOFOLLOW) maps to 422 instead
        # of a 500 with raw OSError text. HTTPException raised inside
        # the with-block (etag mismatch 409) is NOT caught here — it
        # propagates as a normal FastAPI response.
        raise HTTPException(
            status_code=422,
            detail={
                "failing_check": exc.failing_check,
                "hint": (
                    "the case directory's .case_lock could not be opened "
                    "safely; remove any unexpected file/symlink at this path"
                ),
            },
        ) from exc

    # Surface advisories (severity != "error") to the caller so the
    # editor can show a yellow toast even on a successful save.
    warnings = [
        RawDictValidationIssue(severity=i.severity, message=i.message)
        for i in issues
        if i.severity != "error" or force
    ]

    return RawDictPostResponse(
        case_id=case_id,
        path=relative_path,
        new_etag=compute_etag(new_bytes),
        source="user",
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Convenience: list overridable paths
# ---------------------------------------------------------------------------


class RawDictAllowlistEntry(BaseModel):
    path: str
    exists: bool
    source: str
    etag: str | None = None


@router.get(
    "/cases/{case_id}/dicts",
    response_model=list[RawDictAllowlistEntry],
    tags=["case-dicts"],
)
def list_raw_dicts(case_id: str) -> list[RawDictAllowlistEntry]:
    """List every allowlisted dict path with its current existence +
    source state. Powers the Step-3/Step-4 'Advanced: edit raw dicts'
    section as a tab list."""
    from ui.backend.services.case_dicts.allowlist import ALLOWED_RAW_DICT_PATHS

    case_dir = _resolve_case_dir(case_id)
    try:
        manifest = read_case_manifest(case_dir)
        override_map = manifest.overrides.raw_dict_files
    except ManifestNotFoundError:
        override_map = {}

    entries: list[RawDictAllowlistEntry] = []
    for path in sorted(ALLOWED_RAW_DICT_PATHS):
        abs_path = case_dir / path
        exists = abs_path.is_file()
        etag = compute_etag(abs_path.read_bytes()) if exists else None
        source = "ai"
        if path in override_map:
            source = override_map[path].source
        entries.append(
            RawDictAllowlistEntry(
                path=path, exists=exists, source=source, etag=etag
            )
        )
    return entries
