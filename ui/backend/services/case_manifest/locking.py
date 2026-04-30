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

The lock semantics (otherwise unchanged):

* Two paths mutate dict files + manifest in tandem and acquire this
  lock first:
    - ``bc_setup._author_dicts`` / ``_author_channel_dicts``: the
      is_user_override → write → mark_ai_authored sequence.
    - ``routes/case_dicts.post_raw_dict``: the etag re-check → write
      → mark_user_override sequence.

* The lock is **not** reentrant. Do not nest ``case_lock(case_dir)``
  blocks within the same call chain — the inner acquire blocks
  forever. If a future caller has reason to nest, refactor the
  inner code to drop the lock first or split into two phases.

* Symlink-escape protection: ``O_NOFOLLOW`` refuses to follow a
  symlink at the final path component, raising ``ELOOP``. Hostile
  symlinks under ``case_dir/.case_lock`` cause :class:`CaseLockError`
  with ``failing_check="symlink_escape"`` rather than silent
  redirection.
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


@contextmanager
def case_lock(case_dir: Path) -> Iterator[None]:
    """Acquire an exclusive advisory lock on the case directory.

    Creates ``case_dir/.case_lock`` if missing using ``O_NOFOLLOW``
    so a planted symlink can't redirect the open. The flock is
    released when this context exits (success OR exception).

    Not reentrant — nesting on the same case_dir within one process
    deadlocks.

    Raises :class:`CaseLockError` if the lock file cannot be opened
    safely (e.g. ELOOP from a planted symlink, ENOTDIR from a planted
    directory, EACCES from bad perms). The flock itself can also
    fail on some filesystems; that maps to the same exception.
    """
    case_dir.mkdir(parents=True, exist_ok=True)
    lock_path = case_dir / _LOCK_FILENAME

    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
    try:
        fd = os.open(str(lock_path), flags, 0o600)
    except OSError as exc:
        # ELOOP when a symlink is planted at .case_lock with O_NOFOLLOW;
        # EISDIR/ENOTDIR when something else is planted; EACCES on
        # bad perms. All collapse to a uniform symlink_escape error
        # so the route layer doesn't bubble raw errno strings as 500.
        raise CaseLockError(
            f"refusing to use {lock_path} as a lock file (errno "
            f"{exc.errno}: {exc.strerror}) — possible symlink escape",
            failing_check="symlink_escape",
        ) from exc

    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
        except OSError as exc:
            raise CaseLockError(
                f"could not acquire exclusive lock on {lock_path}: {exc}",
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


__all__ = ["case_lock", "CaseLockError"]
