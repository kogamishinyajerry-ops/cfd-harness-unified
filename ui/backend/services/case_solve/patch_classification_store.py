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
from typing import Callable

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


def _cleanup_case_lock_orphan_stub(case_dir: Path) -> None:
    """Remove the empty ``case_dir`` + ``.case_lock`` that
    ``case_lock`` re-created on a deleted case path.

    Codex DEC-V61-108 R6 P2 + R7 P1+P2 + R9 closure: this helper
    handles ONLY the ``case_dir_missing`` drift class (case_dir
    was deleted then case_lock recreated it as a stub at the
    same path with a NEW inode).

    The ``symlink_escape`` drift class — case_dir swapped to a
    symlink — is no longer reachable here as of DEC-V61-109:
    case_lock now opens case_dir itself with ``O_NOFOLLOW |
    O_DIRECTORY`` BEFORE opening its lockfile, so a swapped
    case_dir is refused with ``CaseLockError(failing_check=
    "symlink_escape")`` before any artifact is created. The
    historical R6→R8→R9 demonstration (path-based cleanup of the
    leaked artifact is racy / unprovably-ours) is preserved in
    the V108-A R9 chain report for context, but the underlying
    leak no longer occurs. The post-lock
    ``_assert_fd_still_matches_path`` check below remains as
    belt-and-braces for now — DEC-V61-110 candidate is queued to
    drop it once that simplification is reviewed.

    Race-safety rules (case_dir_missing branch):
      * R7 P1 — use fd-based ops via ``O_NOFOLLOW | O_DIRECTORY``
        so a late symlink swap can't redirect listing/unlink.
      * R7 P2 — refuse removal unless ``.case_lock`` is one of
        the children. Empty-but-no-lockfile means we're not
        authoritative for this dir.
      * Refuse removal unless ``.case_lock`` is the ONLY child
        (no real content has been written into the stub).
    """
    # Race-safe directory listing: open the path with O_NOFOLLOW
    # so a symlink that races us can't redirect ``iterdir``.
    try:
        fd_dir = os.open(
            str(case_dir),
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except OSError:
        # Not a directory (e.g. symlink swap raced us), or gone,
        # or perms — nothing safe to clean up.
        return
    try:
        try:
            children = set(os.listdir(fd_dir))
        except OSError:
            return
        if ".case_lock" not in children:
            return  # R7 P2: not our authority
        if children - {".case_lock"}:
            return  # not a stub state
        try:
            os.unlink(".case_lock", dir_fd=fd_dir)
        except OSError:
            return
    finally:
        try:
            os.close(fd_dir)
        except OSError:
            pass
    try:
        case_dir.rmdir()
    except OSError:
        return


def _assert_fd_still_matches_path(fd_case: int, case_dir: Path) -> None:
    """Raise if ``fd_case`` no longer references the inode currently
    visible at ``case_dir``.

    Codex DEC-V61-108 R5 P1 + R6 P3: closes the swap-between-open-
    and-lock race. ``case_lock`` cannot be the synchronization
    boundary on its own because its ``mkdir(exist_ok=True)`` will
    re-create a deleted case dir and lock the NEW inode, leaving
    our fd_case pointing at an orphaned old inode. Comparing
    ``fstat(fd_case)`` to ``lstat(case_dir)`` after lock acquisition
    detects every such drift: delete-recreate, rename-swap,
    symlink-replacement.

    R6 P3 refinement: distinguish symlink-replacement (return
    ``symlink_escape`` so the route maps to 422) from plain
    delete-recreate (``case_dir_missing`` → 404). Misclassifying
    the symlink case as 404 made containment violations harder to
    diagnose than they should be.

    DEC-V61-110 (this DEC) post-mortem: the V61-109 framing that
    "case_lock's V109 O_NOFOLLOW open makes the symlink branch
    unreachable" was wrong. V109 protects only the case_lock OPEN
    moment; once case_lock yields with the dir_fd pinned, an
    attacker can still rename case_dir away and plant a symlink at
    the path BEFORE this assert runs. Codex caught this on the
    V61-110 "drop the dead branch" attempt — the branch is NOT
    dead. V61-110 narrowed to docstring-only correction so future
    readers don't mis-trust the branch as defensive-only.
    """
    try:
        path_st = os.stat(str(case_dir), follow_symlinks=False)
    except FileNotFoundError as exc:
        raise PatchClassificationIOError(
            f"case_dir disappeared between open and lock acquisition: "
            f"{case_dir}",
            failing_check="case_dir_missing",
        ) from exc
    except OSError as exc:
        raise PatchClassificationIOError(
            f"could not lstat case_dir post-lock: {case_dir}: {exc}",
            failing_check="case_dir_missing",
        ) from exc
    # R6 P3: a symlink at the case_dir path is a containment
    # violation regardless of whether the inode also changed. V109
    # only protects case_lock's OPEN moment; post-lock-yield swap
    # to symlink is still reachable here (Codex V61-110 finding).
    if stat.S_ISLNK(path_st.st_mode):
        raise PatchClassificationIOError(
            f"case_dir replaced by a symlink between pre-lock open "
            f"and lock acquisition: {case_dir} — refusing the "
            f"mutation (containment violation)",
            failing_check="symlink_escape",
        )
    try:
        fd_st = os.fstat(fd_case)
    except OSError as exc:
        raise PatchClassificationIOError(
            f"could not fstat case fd: {exc}",
            failing_check="case_dir_missing",
        ) from exc
    if (path_st.st_ino, path_st.st_dev) != (fd_st.st_ino, fd_st.st_dev):
        raise PatchClassificationIOError(
            f"case_dir inode/dev changed between pre-lock open and "
            f"lock acquisition (path now (ino={path_st.st_ino}, "
            f"dev={path_st.st_dev}); fd was (ino={fd_st.st_ino}, "
            f"dev={fd_st.st_dev})) — likely concurrent delete/recreate "
            f"or rename-swap; refusing the mutation",
            failing_check="case_dir_missing",
        )


def _open_case_no_follow(case_dir: Path) -> int:
    """Open ``case_dir`` with ``O_NOFOLLOW | O_DIRECTORY``.

    Codex DEC-V61-108 R4 P2 closure: this is the FIRST operation in
    every read-modify-write so we surface ``case_dir_missing`` and
    ``symlink_escape`` cases BEFORE acquiring ``case_lock`` (whose
    auto-mkdir would otherwise re-create a deleted case dir).

    Returns an open fd; caller must close it in a finally block.
    """
    try:
        return os.open(
            str(case_dir),
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except FileNotFoundError as exc:
        raise PatchClassificationIOError(
            f"case directory does not exist: {case_dir}",
            failing_check="case_dir_missing",
        ) from exc
    except OSError as exc:
        # ELOOP — case_dir is a symlink (O_NOFOLLOW refusal)
        # ENOTDIR — case_dir is a regular file
        # EACCES — bad perms
        raise PatchClassificationIOError(
            f"refusing to open {case_dir} (errno {exc.errno}: "
            f"{exc.strerror}) — possible symlink escape",
            failing_check="symlink_escape",
        ) from exc


def _open_system_under_case(fd_case: int) -> int:
    """Open ``system/`` under ``fd_case`` with ``O_NOFOLLOW |
    O_DIRECTORY``, mkdir-ing it first if missing.

    Both the mkdir and the open are dir_fd-relative to fd_case, so
    they can't be redirected by a symlink swap on case_dir's path
    (case_dir's inode is what fd_case references, not its name).
    """
    try:
        os.mkdir(_SIDECAR_DIR_REL, mode=0o755, dir_fd=fd_case)
    except FileExistsError:
        pass
    except OSError as exc:
        raise PatchClassificationIOError(
            f"could not mkdir {_SIDECAR_DIR_REL}: {exc}",
            failing_check="write_failed",
        ) from exc
    return _open_dir_no_follow(fd_case, _SIDECAR_DIR_REL)


def _read_overrides_via_fd(fd_system: int) -> dict[str, BCClass]:
    """Read + parse the sidecar via fd-relative open. Refuses a
    symlinked leaf. Missing file → empty dict.

    This is the "load half" of the read-modify-write cycle. Codex
    R4 P1: the prior implementation called the path-based loader
    BEFORE the fd-based write, leaving a TOCTOU where attacker
    could plant symlink / read happens / swap back / write.
    Reading via fd_system + O_RDONLY + O_NOFOLLOW closes that gap:
    once fd_system is open, every subsequent op is on the vetted
    inode, not on a path.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        fd = os.open(
            _SIDECAR_FILE_NAME, flags, dir_fd=fd_system
        )
    except FileNotFoundError:
        return {}
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PatchClassificationIOError(
                f"refusing pre-existing symlink at sidecar "
                f"leaf {_SIDECAR_FILE_NAME!r}",
                failing_check="symlink_escape",
            ) from exc
        raise PatchClassificationIOError(
            f"could not open sidecar leaf for read: {exc}",
            failing_check="write_failed",
        ) from exc
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as fp:
            text = fp.read()
    except OSError as exc:
        raise PatchClassificationIOError(
            f"could not read sidecar: {exc}",
            failing_check="write_failed",
        ) from exc
    # Parse with the same tolerance as the lockless loader: empty/
    # malformed yields {} so the caller continues with a clean
    # mutation. The mutation result is what gets written back.
    try:
        data = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    raw = data.get("overrides")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, BCClass] = {}
    for patch_name, cls_str in raw.items():
        if not isinstance(patch_name, str) or not isinstance(cls_str, str):
            continue
        try:
            out[patch_name] = BCClass(cls_str)
        except ValueError:
            continue
    return out


def _write_overrides_via_fd(
    fd_system: int, *, overrides: dict[str, BCClass]
) -> None:
    """Write the sidecar atomically via fd_system. The write half of
    the read-modify-write cycle; assumes the caller already
    refused a symlinked leaf via ``_read_overrides_via_fd``.
    """
    text = yaml.safe_dump(_payload(overrides), sort_keys=True,
                           default_flow_style=False)

    # Defense-in-depth: if a symlink got planted at the leaf
    # between the read open and now (very narrow window inside the
    # case_lock), refuse before writing. fd-relative lstat is
    # follow_symlinks=False so it can't be tricked.
    try:
        leaf_st = os.stat(
            _SIDECAR_FILE_NAME, dir_fd=fd_system, follow_symlinks=False
        )
    except FileNotFoundError:
        pass
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

    tmp_name = _atomic_create_tmp_file(fd_system, text=text)
    try:
        os.replace(
            tmp_name,
            _SIDECAR_FILE_NAME,
            src_dir_fd=fd_system,
            dst_dir_fd=fd_system,
        )
    except OSError as exc:
        try:
            os.unlink(tmp_name, dir_fd=fd_system)
        except OSError:
            pass
        raise PatchClassificationIOError(
            f"could not replace {_SIDECAR_FILE_NAME} via "
            f"fd-relative rename: {exc}",
            failing_check="write_failed",
        ) from exc


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


def _apply_under_case(
    case_dir: Path,
    *,
    mutate: "Callable[[dict[str, BCClass]], None]",
) -> dict[str, BCClass]:
    """Single-fd-pair read-modify-write of the sidecar.

    Codex DEC-V61-108 R4 P1+P2 closure: the load and write halves
    now share one fd_case + fd_system pair. No pathname
    re-resolution happens between read and write, so a symlink
    that's planted between the two phases can't redirect either.
    The case_dir existence + symlink check happens BEFORE
    ``case_lock`` is acquired, so a deleted-then-recreated case
    surfaces ``case_dir_missing`` instead of being auto-recreated
    by ``case_lock``'s ``mkdir(exist_ok=True)``.

    This is the canonical mutation entry point — both
    ``upsert_override`` and ``delete_override`` delegate here with
    different ``mutate`` callables.
    """
    # Probe case_dir existence + symlink-safety BEFORE case_lock so
    # a deleted/swapped case is rejected without case_lock's
    # auto-mkdir kicking in to silently recreate it.
    fd_case = _open_case_no_follow(case_dir)
    try:
        try:
            with case_lock(case_dir):
                # Codex DEC-V61-108 R5 P1 closure: re-validate that
                # fd_case still corresponds to the inode at the
                # case_dir path. If the directory was deleted-and-
                # recreated, renamed-and-swapped, or replaced with a
                # symlink between ``_open_case_no_follow`` and
                # ``case_lock`` (whose mkdir(exist_ok=True) would
                # silently re-create + lock the NEW inode while our
                # fd still references the orphaned OLD inode),
                # writes through fd_case would land in the orphaned
                # tree while the visible case is locked elsewhere —
                # losing the serialization guarantee. The fstat-vs-
                # lstat compare catches every such race.
                try:
                    _assert_fd_still_matches_path(fd_case, case_dir)
                except PatchClassificationIOError as drift_exc:
                    # Codex DEC-V61-108 R6 P2 + R9 closure: cleanup
                    # is invoked ONLY for ``case_dir_missing`` (the
                    # real-dir-was-deleted-and-recreated branch).
                    #
                    # The ``symlink_escape`` branch is intentionally
                    # NOT cleaned up at this layer: R6→R8→R9
                    # demonstrated that any path-based attempt to
                    # remove the .case_lock case_lock leaked into
                    # the symlink target is racy or unprovably-ours.
                    # The proper fix is at the case_lock layer (open
                    # case_dir with O_NOFOLLOW before opening the
                    # lockfile) and is tracked as future work — see
                    # ``_cleanup_case_lock_orphan_stub`` docstring.
                    if drift_exc.failing_check == "case_dir_missing":
                        _cleanup_case_lock_orphan_stub(case_dir)
                    raise
                # We're now serialized against setup_bc and other
                # PUT/DELETEs on this case. Open system/ via the
                # already-vetted fd_case (mkdir if needed).
                fd_system = _open_system_under_case(fd_case)
                try:
                    overrides = _read_overrides_via_fd(fd_system)
                    mutate(overrides)
                    _write_overrides_via_fd(
                        fd_system, overrides=overrides
                    )
                    return overrides
                finally:
                    try:
                        os.close(fd_system)
                    except OSError:
                        pass
        except CaseLockError as exc:
            raise PatchClassificationIOError(
                f"could not acquire case_lock: {exc}",
                failing_check=exc.failing_check,
            ) from exc
    finally:
        try:
            os.close(fd_case)
        except OSError:
            pass


def upsert_override(
    case_dir: Path, *, patch_name: str, bc_class: BCClass
) -> dict[str, BCClass]:
    """Atomically set or replace one override and return the merged
    state. See ``_apply_under_case`` for the underlying I/O model."""

    def _mut(overrides: dict[str, BCClass]) -> None:
        overrides[patch_name] = bc_class

    return _apply_under_case(case_dir, mutate=_mut)


def delete_override(
    case_dir: Path, *, patch_name: str
) -> dict[str, BCClass]:
    """Atomically remove one override (no-op if absent) and return
    the merged state. See ``_apply_under_case`` for the underlying
    I/O model."""

    def _mut(overrides: dict[str, BCClass]) -> None:
        overrides.pop(patch_name, None)

    return _apply_under_case(case_dir, mutate=_mut)
