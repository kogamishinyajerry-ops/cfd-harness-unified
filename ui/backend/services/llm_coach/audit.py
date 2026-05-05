"""DEC-V61-121 · AI coach action audit log.

Append a record to ``<case_dir>/system/ai_audit/applied.yaml`` every
time a proposal is applied. Atomic via temp-then-rename so concurrent
applies don't corrupt the file mid-write.

V1 schema:

```yaml
schema_version: 1
entries:
  - applied_at: 2026-05-04T16:42:11Z
    audit_id: 7f3a2b91...
    tool: set_patch_bc_type
    args: {patch_name: walls, bc_class: no_slip_wall}
    model_used: deepseek-v4-pro
    conversation_turn_id: null
```

The `audit_id` is a UUIDv4 the route generates and includes in the
ApplyResult JSON so the UI can correlate.
"""
from __future__ import annotations

import errno
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ui.backend.services.case_manifest.locking import (
    CaseLockError,
    case_lock,
)


_SCHEMA_VERSION = 1
_AUDIT_DIR_NAME = "ai_audit"
_AUDIT_FILE_NAME = "applied.yaml"


class AuditWriteError(RuntimeError):
    """Audit write failed AFTER the underlying tool dispatch already
    succeeded. The route layer catches this and returns 200 with an
    `audit_warning` field — the change DID apply, the audit just
    didn't record. Operators can grep the FastAPI logs for the
    underlying error."""


def _now_iso_utc() -> str:
    """ISO-8601 timestamp with Z suffix, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit_dir(case_dir: Path) -> Path:
    return case_dir / "system" / _AUDIT_DIR_NAME


def _audit_path(case_dir: Path) -> Path:
    return _audit_dir(case_dir) / _AUDIT_FILE_NAME


def write_audit(
    case_dir: Path,
    *,
    tool: str,
    args: dict[str, Any],
    model_used: str | None,
    conversation_turn_id: str | None,
) -> str:
    """Append one entry; return the generated ``audit_id``.

    Atomic per writer: writes to a temp file in the same directory
    then renames over the audit file. Cross-writer concurrency
    (Codex R1 P2): two simultaneous applies for the same case would
    each read+modify their own in-memory copy and the later writer's
    rename would clobber the earlier writer's entry, silently
    dropping an audit row even though each rename is itself atomic.
    The fix: take the V108 ``case_lock`` for the read-modify-write
    window so concurrent writers serialize on a per-case basis. The
    same lock the underlying tool dispatch already uses.

    If anything goes wrong AFTER the underlying dispatch succeeded,
    raise AuditWriteError so the route returns a warning rather than
    reporting failure (compensation pattern · DEC-V61-121 risk
    register #4).
    """
    audit_id = uuid.uuid4().hex
    entry = {
        "applied_at": _now_iso_utc(),
        "audit_id": audit_id,
        "tool": tool,
        "args": args,
        "model_used": model_used,
        "conversation_turn_id": conversation_turn_id,
    }
    # Codex base-review-4 P2: pre-lock missing-case check. case_lock
    # unconditionally calls case_dir.mkdir(parents=True, exist_ok=True)
    # — if the case dir was deleted between dispatch_tool succeeding
    # and audit logging starting, the lock would silently RECREATE an
    # empty dir and we'd write applied.yaml into a ghost tree
    # detached from the case the engineer actually modified. Refuse
    # to log audit rows against a vanished case.
    if not os.path.lexists(case_dir):
        raise AuditWriteError(
            f"case_dir {case_dir} no longer exists — refusing to "
            f"recreate via case_lock and write detached audit row"
        )

    # Codex base-review-2 P2 + R1 P2: full fd-relative write path so
    # the symlink-escape and TOCTTOU contract matches the rest of the
    # repo (services/case_solve/patch_classification_store.py is the
    # canonical pattern). Path-based mkdir/write/replace re-resolves
    # path strings on every call — a late symlink swap on `system/`
    # or `system/ai_audit/` after the lstat precheck would still
    # redirect the write outside the case root. Pinning case_dir's
    # inode via O_NOFOLLOW|O_DIRECTORY and traversing children with
    # dir_fd= closes that gap: the fd references the inode, not the
    # path, so mid-write symlink swaps cannot retarget the write.
    try:
        with case_lock(case_dir):
            try:
                fd_case = os.open(
                    str(case_dir),
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                )
            except OSError as exc:
                raise AuditWriteError(
                    f"refusing to open case_dir {case_dir} "
                    f"(errno {exc.errno}: {exc.strerror}) — possible "
                    f"symlink escape or missing dir"
                ) from exc
            try:
                fd_system = _mkdir_and_open_no_follow(
                    fd_case, "system", "system"
                )
                try:
                    fd_audit = _mkdir_and_open_no_follow(
                        fd_system, _AUDIT_DIR_NAME, "system/ai_audit"
                    )
                    try:
                        _write_audit_under_fd(fd_audit, audit_id, entry)
                    finally:
                        os.close(fd_audit)
                finally:
                    os.close(fd_system)
            finally:
                os.close(fd_case)
    except CaseLockError as exc:
        raise AuditWriteError(
            f"could not acquire case lock for audit write: {exc.failing_check}"
        ) from exc
    return audit_id


def _mkdir_and_open_no_follow(parent_fd: int, name: str, label: str) -> int:
    """``mkdir -p`` + ``open(O_NOFOLLOW|O_DIRECTORY)`` under ``parent_fd``.

    Both the mkdir and the open are dir_fd-relative to ``parent_fd``,
    so a symlink swap on the parent's path can't redirect them
    (parent_fd references the inode, not the name). Mirrors
    ``services/case_solve/patch_classification_store._open_system_under_case``.
    """
    try:
        os.mkdir(name, mode=0o755, dir_fd=parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise AuditWriteError(
            f"could not mkdir {label}: {type(exc).__name__}"
        ) from exc
    try:
        return os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise AuditWriteError(
                f"refused to follow symlink at {label}"
            ) from exc
        raise AuditWriteError(
            f"could not open {label}: errno={exc.errno}"
        ) from exc


def _write_audit_under_fd(
    fd_audit: int, audit_id: str, entry: dict[str, Any]
) -> None:
    """Read existing applied.yaml under ``fd_audit``, append ``entry``,
    atomically replace via dir_fd-relative temp file. All path ops
    here are fd-relative (no path strings re-resolved by the kernel)."""
    # Read existing — fd-relative, refusing symlinked leaf.
    existing_text = ""
    try:
        fd_read = os.open(
            _AUDIT_FILE_NAME,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=fd_audit,
        )
    except FileNotFoundError:
        pass
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise AuditWriteError(
                f"refused pre-existing symlink at audit leaf "
                f"{_AUDIT_FILE_NAME!r}"
            ) from exc
        raise AuditWriteError(
            f"could not open audit leaf for read: errno={exc.errno}"
        ) from exc
    else:
        try:
            with os.fdopen(fd_read, "r", encoding="utf-8") as fp:
                existing_text = fp.read()
        except OSError as exc:
            raise AuditWriteError(
                f"could not read existing audit: {type(exc).__name__}"
            ) from exc

    if existing_text.strip():
        try:
            loaded = yaml.safe_load(existing_text)
        except yaml.YAMLError as exc:
            raise AuditWriteError(
                f"existing audit doc is unreadable YAML: {type(exc).__name__}"
            ) from exc
        if not isinstance(loaded, dict):
            raise AuditWriteError("existing audit file is not a YAML mapping")
        if loaded.get("schema_version") != _SCHEMA_VERSION:
            raise AuditWriteError(
                f"audit schema version mismatch: expected {_SCHEMA_VERSION}, "
                f"got {loaded.get('schema_version')!r}"
            )
        entries = loaded.get("entries")
        if not isinstance(entries, list):
            raise AuditWriteError("existing audit has non-list 'entries'")
        doc = loaded
    else:
        doc = {"schema_version": _SCHEMA_VERSION, "entries": []}
    doc["entries"].append(entry)
    serialized = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)

    # Write temp file fd-relative, then atomically replace.
    temp_name = f".applied.{os.getpid()}.{audit_id}.yaml.tmp"
    try:
        fd_temp = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
            0o644,
            dir_fd=fd_audit,
        )
    except OSError as exc:
        raise AuditWriteError(
            f"could not create audit temp file: errno={exc.errno}"
        ) from exc
    try:
        with os.fdopen(fd_temp, "w", encoding="utf-8") as fp:
            fp.write(serialized)
    except OSError as exc:
        # Best-effort cleanup of the temp before re-raising.
        try:
            os.unlink(temp_name, dir_fd=fd_audit)
        except OSError:
            pass
        raise AuditWriteError(
            f"could not write audit temp: {type(exc).__name__}"
        ) from exc
    try:
        os.replace(
            temp_name,
            _AUDIT_FILE_NAME,
            src_dir_fd=fd_audit,
            dst_dir_fd=fd_audit,
        )
    except OSError as exc:
        try:
            os.unlink(temp_name, dir_fd=fd_audit)
        except OSError:
            pass
        raise AuditWriteError(
            f"audit replace failed: {type(exc).__name__}"
        ) from exc
