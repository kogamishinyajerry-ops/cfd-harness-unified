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

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


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


def _read_existing(audit_path: Path) -> dict[str, Any]:
    """Read the prior audit doc. Empty / missing → fresh document."""
    if not audit_path.is_file():
        return {"schema_version": _SCHEMA_VERSION, "entries": []}
    try:
        loaded = yaml.safe_load(audit_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AuditWriteError(
            f"existing audit file at {audit_path} is unreadable: {type(exc).__name__}"
        ) from exc
    if not isinstance(loaded, dict):
        raise AuditWriteError(
            f"existing audit file at {audit_path} is not a YAML mapping"
        )
    if loaded.get("schema_version") != _SCHEMA_VERSION:
        raise AuditWriteError(
            f"audit schema version mismatch at {audit_path}: "
            f"expected {_SCHEMA_VERSION}, got {loaded.get('schema_version')!r}"
        )
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        raise AuditWriteError(
            f"audit file at {audit_path} has non-list 'entries'"
        )
    return loaded


def write_audit(
    case_dir: Path,
    *,
    tool: str,
    args: dict[str, Any],
    model_used: str | None,
    conversation_turn_id: str | None,
) -> str:
    """Append one entry; return the generated ``audit_id``.

    Atomic: writes to a temp file in the same directory then renames
    over the audit file. If anything goes wrong AFTER the underlying
    dispatch succeeded, raise AuditWriteError so the route returns
    a warning rather than reporting failure.
    """
    audit_dir = _audit_dir(case_dir)
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AuditWriteError(
            f"could not create audit dir {audit_dir}: {type(exc).__name__}"
        ) from exc
    audit_path = _audit_path(case_dir)
    doc = _read_existing(audit_path)
    audit_id = uuid.uuid4().hex
    entry = {
        "applied_at": _now_iso_utc(),
        "audit_id": audit_id,
        "tool": tool,
        "args": args,
        "model_used": model_used,
        "conversation_turn_id": conversation_turn_id,
    }
    doc["entries"].append(entry)
    # Atomic temp-then-rename. Per-process unique temp filename so
    # concurrent writers (unusual but possible) don't clobber each
    # other's temp file.
    temp_path = audit_dir / f".applied.{os.getpid()}.{audit_id}.yaml.tmp"
    try:
        temp_path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        os.replace(temp_path, audit_path)
    except OSError as exc:
        # Clean up the temp file if rename failed.
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise AuditWriteError(
            f"audit write failed at {audit_path}: {type(exc).__name__}"
        ) from exc
    return audit_id
