"""DEC-V61-102 Phase 1 round-2 P1-HIGH closure · per-case file lock.

Codex round-2 (commit 1818ad2) flagged the user-override invariant as
fixed only for SERIAL re-runs: two concurrent requests racing between
``is_user_override()`` and the AI write can still let the AI clobber a
just-landed manual edit, leaving the manifest stuck at ``source=user``
while the on-disk content is the AI re-author. Manifest+disk divergence.

This module exposes :func:`case_lock`, an exclusive POSIX advisory lock
on ``case_dir/.case_lock``. Both code paths that mutate dict files +
manifest in tandem acquire this before doing any read-modify-write:

1. ``bc_setup._author_dicts`` / ``_author_channel_dicts``: the
   is_user_override check + write + mark_ai_authored sequence runs
   inside the lock so ``post_raw_dict`` can't slip in mid-helper.
2. ``routes/case_dicts.post_raw_dict``: the etag re-check + write +
   mark_user_override sequence runs inside the lock so a parallel
   ``setup_ldc_bc`` call can't author OVER the user content while
   we're computing the new etag.

The lock is reentrant via fcntl.flock semantics (same process, same
fd → same lock), so nested ``case_lock(case_dir)`` blocks are safe
within one call chain. Different threads / processes on the same
case serialize.

Trade-off: this is a coarse per-case lock. We accept the throughput
cost (a single engineer can only do one mutation at a time per case)
because the alternative — fine-grained per-path locks plus a manifest
mutex — adds three lock-ordering rules and a deadlock-detection
obligation. Phase-1 demo workload is one engineer per case at most.
"""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_LOCK_FILENAME = ".case_lock"


@contextmanager
def case_lock(case_dir: Path) -> Iterator[None]:
    """Acquire an exclusive advisory lock on the case directory.

    Creates ``case_dir/.case_lock`` if missing. Blocks if another
    holder of the same lock is mid-write. The lock is released on
    context exit (success OR exception) — fcntl.flock semantics
    guarantee the kernel drops it when the fd closes.
    """
    case_dir.mkdir(parents=True, exist_ok=True)
    lock_path = case_dir / _LOCK_FILENAME
    # 'a+' opens for read+write, creating if missing, without
    # truncating any prior content (the file is just a lock target,
    # we never write into it).
    with open(lock_path, "a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            # Release explicitly. The `with` would close the fd which
            # also drops the lock, but explicit release lets a slow
            # finalizer in the same process not hold the lock while
            # the GC walks.
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


__all__ = ["case_lock"]
