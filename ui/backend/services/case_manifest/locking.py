"""DEC-V61-102 Phase 1 round-3 P1-HIGH closure · per-case file lock.

Codex round-3 (commit 4361ef7) flagged two issues with the round-2 lock:

1. ``open(..., "a+")`` follows symlinks. An attacker who can plant a
   symlink at ``case_dir/.case_lock`` pointing outside the case dir
   gets the backend to create/open that arbitrary path. Same class of
   bug previously fixed in ``case_annotations/_yaml_io.py`` (round-2
   SECURITY finding) via ``os.open(..., O_NOFOLLOW)``. We use the
   same pattern.

2. Reentrancy claim was wrong. ``fcntl.flock(LOCK_EX)`` on a freshly
   opened fd blocks even within the same process, so nested
   ``case_lock(case_dir)`` calls **deadlock**. Documented as such.

DEC-V61-109 closes the residual that DEC-V61-108 Phase A R9 documented:
the lockfile path was already O_NOFOLLOW-protected at its FINAL
component (``.case_lock``), but the case directory itself was opened
by name. A planted or swapped ``case_dir`` symlink would redirect the
lockfile creation through the symlink target, leaking ``.case_lock``
artifacts outside the case root and breaking the per-case
serialization invariant.

The fix: open ``case_dir`` itself with ``O_NOFOLLOW | O_DIRECTORY``
BEFORE opening the lockfile, then open ``.case_lock`` relative to
the now-pinned fd via ``dir_fd=fd_case``. A swapped case-dir symlink
between mkdir and open is detected at fd open time and raised as
``symlink_escape``.

The lock semantics (otherwise unchanged):

* Two paths mutate dict files + manifest in tandem and acquire this
  lock first:
    - ``bc_setup._author_dicts`` / ``_author_channel_dicts``: the
      is_user_override → write → mark_ai_authored sequence.
    - ``routes/case_dicts.post_raw_dict``: the etag re-check → write
      → mark_user_override sequence.
    - ``services/case_solve/patch_classification_store``: the
      upsert/delete override sequence (per DEC-V61-108 Phase A).

* The lock is **not** reentrant. Do not nest ``case_lock(case_dir)``
  blocks within the same call chain — the inner acquire blocks
  forever. If a future caller has reason to nest, refactor the
  inner code to drop the lock first or split into two phases.

* Symlink-escape protection: ``O_NOFOLLOW`` refuses to follow a
  symlink at the final path component, raising ``ELOOP``. Hostile
  symlinks at either ``case_dir`` itself or ``case_dir/.case_lock``
  raise :class:`CaseLockError` with ``failing_check="symlink_escape"``
  rather than silent redirection.
"""
from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_LOCK_FILENAME = ".case_lock"


class CaseLockError(RuntimeError):
    """Raised when the lock file cannot be opened safely (symlink
    escape, missing parent dir, permission denied, etc.). Carries a
    ``failing_check`` string for the route layer to translate into a
    structured 422/500."""

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


def _open_or_create_lock_fd(fd_case: int) -> int:
    """Atomically open or create ``.case_lock`` relative to ``fd_case``,
    surviving the Darwin openat race (see ``case_lock`` docstring).

    Returns an O_RDWR fd on the lockfile. Both branches preserve the
    ``O_NOFOLLOW`` symlink-escape contract: if a symlink is planted at
    the lockfile path, both branches refuse to follow it.

    Raises ``OSError`` (as the underlying ``os.open`` would) on any
    non-race failure mode — caller translates to ``CaseLockError``.
    """
    while True:
        try:
            return os.open(
                _LOCK_FILENAME,
                os.O_RDWR | os.O_NOFOLLOW,
                dir_fd=fd_case,
            )
        except FileNotFoundError:
            try:
                return os.open(
                    _LOCK_FILENAME,
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=fd_case,
                )
            except FileExistsError:
                # Concurrent thread won the create race — retry the
                # existing-file open path. Loop is bounded by the
                # underlying file actually existing now.
                continue


@contextmanager
def case_lock(case_dir: Path) -> Iterator[None]:
    """Acquire an exclusive advisory lock on the case directory.

    Opens ``case_dir`` with ``O_NOFOLLOW | O_DIRECTORY`` (DEC-V61-109)
    so a planted or swapped case-dir symlink can't redirect the
    lockfile path. Then creates ``case_dir/.case_lock`` if missing
    via ``dir_fd=fd_case`` so the lockfile is opened RELATIVE to the
    pinned case-dir fd, not by re-resolving the path. The flock is
    released when this context exits (success OR exception).

    Not reentrant — nesting on the same case_dir within one process
    deadlocks.

    Raises :class:`CaseLockError` if either the case directory or
    the lock file cannot be opened safely (e.g. ELOOP from a planted
    symlink, ENOTDIR from a planted regular file, EACCES from bad
    perms). The flock itself can also fail on some filesystems; that
    maps to the same exception.

    Notes:
    * The auto-mkdir is preserved for the historical caller contract
      (bc_setup, raw_dict editor) but uses ``Path.mkdir(parents=True,
      exist_ok=True)``. If a symlink is planted at the case_dir path
      *after* mkdir but *before* the O_NOFOLLOW open, the open fails
      with ELOOP and we raise ``symlink_escape``. The mkdir itself
      can still create intermediate dirs through a symlinked PARENT
      path; that residual is documented and out of scope for V109
      (full fd-relative path creation would require restructuring
      the caller contract — multi-tenant fix, not single-tenant
      threat model).
    """
    # DEC-V61-109: the auto-mkdir is preserved for the historical
    # caller contract, but a planted regular file at case_dir would
    # raise a raw FileExistsError here that the route layer can't
    # translate uniformly. Catch it and let the O_NOFOLLOW open below
    # produce the same symlink_escape surface other planted-content
    # cases produce.
    try:
        case_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        # case_dir exists but isn't a directory (e.g. planted regular
        # file). Don't fail here — the O_NOFOLLOW | O_DIRECTORY open
        # below will raise ENOTDIR and translate to symlink_escape.
        pass

    # DEC-V61-109: open the case directory fd with O_NOFOLLOW first.
    # This pins the case_dir to a real directory inode (not a symlink),
    # closing the V108-A documented residual where a swapped case_dir
    # symlink would redirect the lockfile creation path.
    try:
        fd_case = os.open(
            str(case_dir),
            os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY,
        )
    except OSError as exc:
        # ELOOP when case_dir is a symlink (planted or swapped after
        # mkdir); ENOTDIR when something else (regular file) is planted;
        # EACCES on bad perms; ENOENT if the dir was unlinked between
        # mkdir and open (rare local-filesystem race). All collapse
        # to symlink_escape so the route layer surfaces a uniform
        # 422 rather than bubbling raw errno strings.
        raise CaseLockError(
            f"refusing to use {case_dir} as a case directory (errno "
            f"{exc.errno}: {exc.strerror}) — possible symlink escape",
            failing_check="symlink_escape",
        ) from exc

    try:
        try:
            # dir_fd= makes the path resolution relative to fd_case,
            # so the lock filename is opened in the inode we just
            # pinned. A swap of case_dir to a symlink AFTER fd_case
            # is open has no effect — the kernel resolves _LOCK_FILENAME
            # against fd_case's referent, not against the path string.
            #
            # We use the portable atomic open-or-create pattern (RDWR
            # then CREAT|EXCL on ENOENT then retry on EEXIST) because
            # Darwin's openat with `O_CREAT | O_NOFOLLOW` exhibits a
            # kernel race under concurrent contention: parallel openat
            # callers can spuriously receive ENOENT despite O_CREAT,
            # which Linux's openat does not. Splitting the open into
            # two phases — try-existing then exclusive-create — is
            # the standard portable workaround and preserves the
            # symlink-escape contract because both phases carry
            # O_NOFOLLOW.
            fd = _open_or_create_lock_fd(fd_case)
        except OSError as exc:
            raise CaseLockError(
                f"refusing to use {case_dir / _LOCK_FILENAME} as a lock "
                f"file (errno {exc.errno}: {exc.strerror}) — possible "
                f"symlink escape",
                failing_check="symlink_escape",
            ) from exc

        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
            except OSError as exc:
                raise CaseLockError(
                    f"could not acquire exclusive lock on "
                    f"{case_dir / _LOCK_FILENAME}: {exc}",
                    failing_check="lock_acquire_failed",
                ) from exc
            try:
                yield
            finally:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    # LOCK_UN failure is benign — fd close below releases
                    # the advisory lock anyway. Don't mask any in-flight
                    # exception from the critical section.
                    pass
        finally:
            try:
                os.close(fd)
            except OSError:
                # Close failure is unrecoverable and not actionable;
                # advisory lock is released by process-end at worst.
                pass
    finally:
        try:
            os.close(fd_case)
        except OSError:
            pass


__all__ = ["case_lock", "CaseLockError"]
