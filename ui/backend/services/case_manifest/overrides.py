"""DEC-V61-102 Phase 1.1 · override marking helpers.

A small focused module for the two state mutations that all dict-author
code paths need to perform on the manifest:

1. ``mark_ai_authored(...)``: AI generated dict X — record source=ai
2. ``mark_user_override(...)``: engineer manually edited dict X — record
   source=user, edited_at=now, etag=sha256(content)

Both helpers are read-modify-write on the manifest YAML and append a
``HistoryEntry`` so the audit log captures the action. They never delete
existing override entries — once a file is marked source=user, only an
explicit ``reset_to_ai_default(...)`` can flip it back.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import (
    ManifestNotFoundError,
    compute_etag,
    read_case_manifest,
    write_case_manifest,
)
from .schema import CaseManifest, RawDictOverride


def mark_ai_authored(
    case_dir: Path,
    *,
    relative_paths: list[str],
    action: str,
    detail: dict[str, Any] | None = None,
) -> CaseManifest:
    """Record that AI just authored each path in ``relative_paths``.

    If a path already has a ``source: user`` entry, **do not overwrite
    it** — the user-override invariant must hold (DEC §Default behaviors).
    The caller is responsible for skipping the actual file write in that
    case (this helper only updates the manifest).

    Returns the updated manifest (also persisted to disk).
    """
    try:
        manifest = read_case_manifest(case_dir)
    except ManifestNotFoundError:
        # Allow the helper to be called on a freshly-staged case dir
        # that hasn't had its v1 manifest written yet — caller will
        # have authored it (e.g. import flow). We synthesize a minimal
        # one so subsequent setup_*_bc calls don't crash.
        manifest = CaseManifest(case_id=case_dir.name)

    for rel_path in relative_paths:
        existing = manifest.overrides.raw_dict_files.get(rel_path)
        if existing and existing.source == "user":
            # Honor the user override; do NOT overwrite. The bc_setup
            # caller separately decides whether to actually skip the
            # file write or surface a confirm-overwrite prompt.
            continue
        manifest.overrides.raw_dict_files[rel_path] = RawDictOverride(source="ai")

    manifest.append_history(
        action=action,
        source="ai",
        detail=detail or {"paths": list(relative_paths)},
    )
    write_case_manifest(case_dir, manifest)
    return manifest


def mark_user_override(
    case_dir: Path,
    *,
    relative_path: str,
    new_content: bytes,
    detail: dict[str, Any] | None = None,
) -> CaseManifest:
    """Record that the engineer manually edited ``relative_path``.

    ``new_content`` is the exact bytes written to disk (the caller has
    already done the file write). We compute its etag so a subsequent
    GET → POST round-trip can detect interleaving AI overwrites.

    Returns the updated manifest (also persisted to disk).
    """
    try:
        manifest = read_case_manifest(case_dir)
    except ManifestNotFoundError:
        manifest = CaseManifest(case_id=case_dir.name)

    manifest.overrides.raw_dict_files[relative_path] = RawDictOverride(
        source="user",
        edited_at=datetime.now(timezone.utc),
        etag=compute_etag(new_content),
    )
    # Codex 8b4e602 review P3: callers (post_raw_dict in particular)
    # pass custom detail with extra fields like force_bypass. We MERGE
    # rather than replace so the path identifier is always present —
    # otherwise a multi-edit history can't tell you which file each
    # edit was about.
    history_detail: dict[str, Any] = {
        "path": relative_path,
        "size": len(new_content),
    }
    if detail:
        history_detail.update(detail)
    manifest.append_history(
        action="edit_dict",
        source="user",
        detail=history_detail,
    )
    write_case_manifest(case_dir, manifest)
    return manifest


def reset_to_ai_default(
    case_dir: Path,
    *,
    relative_path: str,
) -> CaseManifest:
    """Flip a path's source back to ai. Used when the user explicitly
    discards their manual edit ("Reset to AI default" button in the UI).
    The actual file regeneration is the caller's responsibility (this
    helper only flips the manifest flag).
    """
    manifest = read_case_manifest(case_dir)
    if relative_path in manifest.overrides.raw_dict_files:
        manifest.overrides.raw_dict_files[relative_path] = RawDictOverride(source="ai")
    manifest.append_history(
        action="reset_dict_to_ai",
        source="user",
        detail={"path": relative_path},
    )
    write_case_manifest(case_dir, manifest)
    return manifest


def is_user_override(case_dir: Path, *, relative_path: str) -> bool:
    """Convenience predicate: does ``relative_path`` carry a user
    override? Returns False if no manifest exists yet (fresh case).
    """
    try:
        manifest = read_case_manifest(case_dir)
    except ManifestNotFoundError:
        return False
    entry = manifest.overrides.raw_dict_files.get(relative_path)
    return bool(entry and entry.source == "user")


__all__ = [
    "mark_ai_authored",
    "mark_user_override",
    "reset_to_ai_default",
    "is_user_override",
]
