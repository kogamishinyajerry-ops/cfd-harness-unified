"""Secure I/O for ``system/patch_classification.yaml`` (DEC-V61-108
Phase A · Codex R1 hardening).

Single source of truth for the per-patch BC classification override
sidecar. Used by:

  * ``routes/case_patch_classification`` for GET/PUT/DELETE.
  * ``services/case_solve/bc_setup_from_stl_patches`` for
    classification at solve time.

Hardening (Codex DEC-V61-108 R1):

* **P1-A (concurrency)**: PUT/DELETE wrap their read-modify-write in
  ``case_lock(case_dir)``. The same lock is held by
  ``setup_bc_from_stl_patches``'s critical section, so a PUT can't
  land between override-read and dict-author. Two concurrent PUTs
  for different patches serialize cleanly without losing each
  other's edits.

* **P1-B (symlink escape)**: write path resolves
  ``<case_dir>/system/patch_classification.yaml`` and asserts the
  resolved path stays under ``case_dir``. The temp file is created
  by ``tempfile.mkstemp`` (random per-call suffix → no pre-existing
  symlink can be followed) and rename-replaces the target via
  ``os.replace``.

* **P2 (stale-read)**: solve-time callers MUST invoke
  ``load_under_lock(case_dir)`` from inside their own
  ``case_lock(case_dir)`` block. The pre-existing
  ``load_patch_classification_overrides`` (lockless) is retained
  for read-only diagnostic paths (UI GET, tests) where a slightly
  stale read is acceptable.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from ui.backend.services.case_manifest.locking import (
    CaseLockError,
    case_lock,
)


# Importing the canonical relpath + schema version + BCClass from the
# bc_setup module keeps the file format owned by one place. The
# loader (``load_patch_classification_overrides``) also lives there
# for backwards-compatibility with existing imports.
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    BCClass,
    _PATCH_CLASSIFICATION_REL,
    _PATCH_CLASSIFICATION_SCHEMA_VERSION,
    load_patch_classification_overrides,
)


__all__ = [
    "PatchClassificationIOError",
    "load_under_lock",
    "upsert_override",
    "delete_override",
    "load_patch_classification_overrides",  # re-export
]


class PatchClassificationIOError(RuntimeError):
    """Raised when the sidecar cannot be safely read or written.

    ``failing_check`` is one of:
      * ``case_dir_missing`` — the case directory does not exist
      * ``symlink_escape`` — the resolved sidecar or its temp file
        would escape the case root, or a planted symlink/dir blocks
        the lock acquisition
      * ``write_failed`` — atomic write/rename failed for an unrelated
        OSError
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


def _resolve_sidecar_path(case_dir: Path) -> Path:
    """Resolve ``<case_dir>/system/patch_classification.yaml`` and
    assert NO path component (including the leaf) is a symlink.

    Codex DEC-V61-108 R2 P1 closure: the prior implementation only
    checked containment after ``resolve()``, which accepted in-tree
    symlinks like ``patch_classification.yaml -> system/controlDict``.
    A subsequent ``os.replace`` then silently overwrote the symlink
    target — the engineer's authored ``controlDict`` in this example.

    The fix walks each component from ``case_root`` down to the leaf
    and rejects any symlink, regardless of where it points. Combined
    with the existing containment check (kept as defense-in-depth),
    this denies both out-of-tree and in-tree symlink redirects.
    """
    if not case_dir.exists():
        raise PatchClassificationIOError(
            f"case directory does not exist: {case_dir}",
            failing_check="case_dir_missing",
        )
    try:
        case_root = case_dir.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PatchClassificationIOError(
            f"could not resolve case directory: {case_dir}: {exc}",
            failing_check="case_dir_missing",
        ) from exc

    # Walk every component from case_root → sidecar leaf. Reject if
    # any is a symlink, even if its target lands inside case_root.
    sidecar = case_root / _PATCH_CLASSIFICATION_REL
    rel_parts = Path(_PATCH_CLASSIFICATION_REL).parts
    cursor = case_root
    for part in rel_parts:
        cursor = cursor / part
        try:
            is_link = cursor.is_symlink()
        except OSError as exc:
            raise PatchClassificationIOError(
                f"could not stat sidecar component {cursor}: {exc}",
                failing_check="symlink_escape",
            ) from exc
        if is_link:
            raise PatchClassificationIOError(
                f"refusing symlinked sidecar component at {cursor} — "
                f"writes through symlinks (even in-tree) are denied",
                failing_check="symlink_escape",
            )

    # Defense-in-depth: even though the per-component check above
    # makes this redundant for the symlink-redirect class, the
    # containment check below still catches any future regression
    # (e.g. ``..`` in the relpath, hardlink-style escape).
    try:
        resolved = sidecar.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise PatchClassificationIOError(
            f"could not resolve sidecar path: {sidecar}: {exc}",
            failing_check="symlink_escape",
        ) from exc
    try:
        resolved.relative_to(case_root)
    except ValueError as exc:
        raise PatchClassificationIOError(
            f"sidecar path escapes case root: "
            f"resolved={resolved}, case_root={case_root}",
            failing_check="symlink_escape",
        ) from exc
    # Return the unresolved path: ``os.replace`` then operates on the
    # exact ``case_root/system/patch_classification.yaml`` we vetted
    # rather than a symlink-resolved alias of it.
    return sidecar


def _atomic_write(path: Path, payload: dict) -> None:
    """Serialize ``payload`` to YAML and atomically replace ``path``.

    Uses ``tempfile.mkstemp`` so the temp file name is random per
    call (immune to symlink planting at the legacy fixed name) and
    ``os.replace`` for the atomic rename. The destination
    containment was already enforced by ``_resolve_sidecar_path``;
    here we only need to ensure the temp lives next to the target
    so the replace is on the same filesystem (atomic on POSIX).
    """
    text = yaml.safe_dump(payload, sort_keys=True, default_flow_style=False)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp_str = tempfile.mkstemp(
            prefix="patch_classification.",
            suffix=".tmp",
            dir=str(parent),
        )
    except OSError as exc:
        raise PatchClassificationIOError(
            f"could not create temp file in {parent}: {exc}",
            failing_check="write_failed",
        ) from exc
    tmp = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            fp.write(text)
    except OSError as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise PatchClassificationIOError(
            f"could not write temp {tmp}: {exc}",
            failing_check="write_failed",
        ) from exc
    try:
        os.replace(str(tmp), str(path))
    except OSError as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise PatchClassificationIOError(
            f"could not replace {path}: {exc}",
            failing_check="write_failed",
        ) from exc


def _payload(overrides: dict[str, BCClass]) -> dict:
    return {
        "schema_version": _PATCH_CLASSIFICATION_SCHEMA_VERSION,
        "overrides": {name: cls.value for name, cls in overrides.items()},
    }


def load_under_lock(case_dir: Path) -> dict[str, BCClass]:
    """Load the override map, asserting the caller holds
    ``case_lock(case_dir)``.

    This is the entry point for ``setup_bc_from_stl_patches`` and any
    other writer-adjacent reader. It deliberately does NOT take the
    lock itself; the caller is expected to already be inside their
    own critical section so the read happens under the same lock as
    the subsequent dict author/commit.
    """
    return load_patch_classification_overrides(case_dir)


def upsert_override(
    case_dir: Path, *, patch_name: str, bc_class: BCClass
) -> dict[str, BCClass]:
    """Atomically set or replace one override and return the merged
    state.

    Acquires ``case_lock`` (same lock as setup_bc, so concurrent
    setup-bc cannot interleave with this update) and uses the
    symlink-safe write path.
    """
    sidecar = _resolve_sidecar_path(case_dir)
    try:
        with case_lock(case_dir):
            overrides = load_patch_classification_overrides(case_dir)
            overrides[patch_name] = bc_class
            _atomic_write(sidecar, _payload(overrides))
            return overrides
    except CaseLockError as exc:
        raise PatchClassificationIOError(
            f"could not acquire case_lock for upsert: {exc}",
            failing_check=exc.failing_check,
        ) from exc


def delete_override(
    case_dir: Path, *, patch_name: str
) -> dict[str, BCClass]:
    """Atomically remove one override (no-op if absent) and return
    the merged state. Same lock semantics as ``upsert_override``."""
    sidecar = _resolve_sidecar_path(case_dir)
    try:
        with case_lock(case_dir):
            overrides = load_patch_classification_overrides(case_dir)
            overrides.pop(patch_name, None)
            _atomic_write(sidecar, _payload(overrides))
            return overrides
    except CaseLockError as exc:
        raise PatchClassificationIOError(
            f"could not acquire case_lock for delete: {exc}",
            failing_check=exc.failing_check,
        ) from exc
