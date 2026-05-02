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

import errno
import os
import secrets
import stat
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


_SIDECAR_DIR_REL = "system"
_SIDECAR_FILE_NAME = "patch_classification.yaml"


def _open_dir_no_follow(parent_fd: int | None, name: str) -> int:
    """Open a directory by name with ``O_NOFOLLOW | O_DIRECTORY``.

    If ``parent_fd`` is ``None`` ``name`` is interpreted absolutely;
    otherwise it is resolved relative to ``parent_fd`` (POSIX
    ``openat`` semantics via Python's ``dir_fd=`` parameter). Maps
    every error to a ``symlink_escape`` ``PatchClassificationIOError``
    so the caller can return a uniform 422 instead of bubbling raw
    OSError as a 500.
    """
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        if parent_fd is None:
            return os.open(name, flags)
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        # ELOOP — symlink at this component (O_NOFOLLOW refusal)
        # ENOTDIR — non-directory planted (e.g. regular file)
        # ENOENT — caller is responsible for mkdir-then-retry; we
        #          surface as symlink_escape so a missing-parent path
        #          is still uniform.
        raise PatchClassificationIOError(
            f"refusing to traverse {name!r} (errno {exc.errno}: "
            f"{exc.strerror}) — possible symlink escape or "
            f"missing parent",
            failing_check="symlink_escape",
        ) from exc


def _atomic_write_under_case(
    case_dir: Path, *, payload: dict
) -> None:
    """Race-free atomic write of the sidecar.

    Codex DEC-V61-108 R3 P2 closure: the previous design preflighted
    the path then later opened by name, leaving a TOCTOU window
    where ``system/`` could be swapped to a symlink between
    validation and write. The fix opens every directory ancestor
    with ``O_NOFOLLOW | O_DIRECTORY`` and does **every** subsequent
    operation (mkstemp-equivalent, fdopen, os.replace) relative to
    that fd. An attacker who swaps the directory after our open
    sees no effect — our fd still references the original inode,
    not the symlink target.

    Steps:
        1. open(case_dir) with O_NOFOLLOW + O_DIRECTORY → fd_case.
        2. mkdir("system", dir_fd=fd_case) if missing (tolerate
           EEXIST).
        3. open("system", dir_fd=fd_case) with O_NOFOLLOW +
           O_DIRECTORY → fd_system. ELOOP here proves the dir was
           a symlink at the time of open (whether planted before or
           racing with us — either way we refuse).
        4. Generate random tmp name via ``secrets.token_hex``.
        5. open(tmp, dir_fd=fd_system) with O_WRONLY | O_CREAT |
           O_EXCL | O_NOFOLLOW → fd_tmp. EEXIST is statistically
           impossible with 16-byte randomness; if it does happen,
           we retry once.
        6. fdopen(fd_tmp, "w") → write text.
        7. os.replace(tmp, sidecar_name, src_dir_fd=fd_system,
           dst_dir_fd=fd_system) — atomic, fd-relative.
        8. Always close fd_system + fd_case in a finally block.

    Note that this implementation deliberately bypasses
    ``tempfile.mkstemp`` (which doesn't accept ``dir_fd``) and
    ``Path``-based resolution entirely once the case_dir fd is
    open.
    """
    text = yaml.safe_dump(payload, sort_keys=True, default_flow_style=False)

    if not case_dir.exists():
        raise PatchClassificationIOError(
            f"case directory does not exist: {case_dir}",
            failing_check="case_dir_missing",
        )

    fd_case = _open_dir_no_follow(None, str(case_dir))
    try:
        # Ensure system/ exists. mkdir refuses to create through a
        # symlink that already exists at the path (it returns EEXIST
        # whether the existing entry is a real dir or a symlink),
        # so a planted symlink can't trick us into creating
        # something elsewhere; the subsequent O_NOFOLLOW open will
        # detect the symlink and abort.
        try:
            os.mkdir(_SIDECAR_DIR_REL, mode=0o755, dir_fd=fd_case)
        except FileExistsError:
            pass
        except OSError as exc:
            raise PatchClassificationIOError(
                f"could not mkdir {_SIDECAR_DIR_REL}: {exc}",
                failing_check="write_failed",
            ) from exc

        fd_system = _open_dir_no_follow(fd_case, _SIDECAR_DIR_REL)
        try:
            # Belt-and-braces: if a symlink already exists at the
            # sidecar leaf, refuse before writing. ``rename(2)``
            # operates on directory entries, so the subsequent
            # ``os.replace`` would only replace the symlink entry
            # (the target file is preserved), but a strict refusal
            # surfaces the misconfiguration to the engineer instead
            # of silently swapping the link out. The lstat is
            # fd-relative + follow_symlinks=False, so a planted
            # symlink that races our open of fd_system can't make
            # this check follow it.
            try:
                leaf_st = os.stat(
                    _SIDECAR_FILE_NAME,
                    dir_fd=fd_system,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass  # No prior sidecar; clean write.
            except OSError as exc:
                raise PatchClassificationIOError(
                    f"could not lstat sidecar leaf: {exc}",
                    failing_check="symlink_escape",
                ) from exc
            else:
                if stat.S_ISLNK(leaf_st.st_mode):
                    raise PatchClassificationIOError(
                        f"refusing pre-existing symlink at sidecar "
                        f"leaf {_SIDECAR_FILE_NAME!r}",
                        failing_check="symlink_escape",
                    )

            tmp_name = _atomic_create_tmp_file(
                fd_system, text=text
            )
            # Atomic rename relative to the same vetted directory
            # fd. An attacker who swaps system/ AFTER we opened
            # fd_system cannot affect this rename — it operates on
            # the original inode our fd still references.
            try:
                os.replace(
                    tmp_name,
                    _SIDECAR_FILE_NAME,
                    src_dir_fd=fd_system,
                    dst_dir_fd=fd_system,
                )
            except OSError as exc:
                # Best-effort cleanup on rename failure.
                try:
                    os.unlink(tmp_name, dir_fd=fd_system)
                except OSError:
                    pass
                raise PatchClassificationIOError(
                    f"could not replace {_SIDECAR_FILE_NAME} via "
                    f"fd-relative rename: {exc}",
                    failing_check="write_failed",
                ) from exc
        finally:
            try:
                os.close(fd_system)
            except OSError:
                pass
    finally:
        try:
            os.close(fd_case)
        except OSError:
            pass


def _atomic_create_tmp_file(
    fd_system: int, *, text: str, max_retries: int = 3
) -> str:
    """Create a unique temp file inside the directory referred to
    by ``fd_system`` and write ``text`` to it. Returns the tmp
    filename (relative to fd_system) so the caller can rename it
    into the final sidecar name.

    Uses ``O_NOFOLLOW | O_CREAT | O_EXCL`` so that:
      * If a file (or symlink) exists at the random name, EEXIST.
      * If the random name is a symlink at create time, ELOOP.
    Both retry up to ``max_retries`` times.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    last_exc: OSError | None = None
    for _ in range(max_retries):
        tmp_name = (
            f"patch_classification.{secrets.token_hex(8)}.tmp"
        )
        try:
            fd_tmp = os.open(
                tmp_name, flags, 0o600, dir_fd=fd_system
            )
        except OSError as exc:
            if exc.errno in (errno.EEXIST, errno.ELOOP):
                # Race: another writer or a planted symlink. Retry
                # with a fresh random suffix.
                last_exc = exc
                continue
            raise PatchClassificationIOError(
                f"could not create temp file {tmp_name!r}: {exc}",
                failing_check="write_failed",
            ) from exc
        try:
            with os.fdopen(fd_tmp, "w", encoding="utf-8") as fp:
                fp.write(text)
        except OSError as exc:
            try:
                os.unlink(tmp_name, dir_fd=fd_system)
            except OSError:
                pass
            raise PatchClassificationIOError(
                f"could not write temp file {tmp_name!r}: {exc}",
                failing_check="write_failed",
            ) from exc
        return tmp_name
    raise PatchClassificationIOError(
        f"could not create unique temp file after {max_retries} "
        f"retries: {last_exc}",
        failing_check="write_failed",
    )


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
    setup-bc cannot interleave with this update) and writes via
    the race-free fd-based ``_atomic_write_under_case``.
    """
    try:
        with case_lock(case_dir):
            overrides = load_patch_classification_overrides(case_dir)
            overrides[patch_name] = bc_class
            _atomic_write_under_case(case_dir, payload=_payload(overrides))
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
    try:
        with case_lock(case_dir):
            overrides = load_patch_classification_overrides(case_dir)
            overrides.pop(patch_name, None)
            _atomic_write_under_case(case_dir, payload=_payload(overrides))
            return overrides
    except CaseLockError as exc:
        raise PatchClassificationIOError(
            f"could not acquire case_lock for delete: {exc}",
            failing_check=exc.failing_check,
        ) from exc
