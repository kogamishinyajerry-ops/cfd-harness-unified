"""DEC-V61-202-SUB-M30-CYCLE6 · decide() provenance audit log.

Writes one JSONL line per decide() call to:
    ui/backend/user_drafts/audit_v2/<case_id>/decisions.jsonl

Each line captures the input state (case_id, step, focus_patch,
state_sha, manifest_state_sha) plus the rail/topbar/card choices the
decide() function made. Enables post-hoc retro of "what did the
workbench show engineer Y at time T".

Fire-and-forget by design: a logging failure (disk full, permission,
encoding) must never break the frame the engineer is waiting on.
The audit log is best-effort durability.

Gated by env var `WORKBENCH_PROVENANCE_DISABLED=1` so tests / CI runs
that don't want sidecar files can disable the log entirely.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from ui.backend.schemas.workbench_frame import (
    CaseStateSnapshot,
    WorkbenchFrame,
)
# Push-review R2 P2 #1 fix: import DRAFTS_DIR from the trimesh-free
# `case_drafts` module instead of `case_scaffold.template_clone` which
# transitively pulls in trimesh via the geometry stack. The
# `[ui]`-minimal install (without geometry deps) raised
# ModuleNotFoundError here, decide()'s try/except swallowed it, and the
# audit log silently never wrote. Both modules export the identical
# `REPO_ROOT / "ui" / "backend" / "user_drafts"` path.
from ui.backend.services.case_drafts import DRAFTS_DIR

logger = logging.getLogger(__name__)

# Sibling of DRAFTS_DIR so the path travels with the same case-data
# lifecycle (cleared by cleanup scripts, archived by export, etc.).
AUDIT_V2_DIR: Path = DRAFTS_DIR / "audit_v2"

# Env-var gate. The string check is case-insensitive on the value.
_DISABLED_ENV_VAR = "WORKBENCH_PROVENANCE_DISABLED"

# Push-review P2 #1 fix: dedup log writes by (case_id, state_sha).
# React Query default behaviour (remount, window-focus refetch, stale
# revalidation) hits GET /workbench_frame multiple times on the same
# state — without dedup the log becomes a record of UI fetches, not
# engineer-driven decisions. Cache last state_sha per case in-process;
# on restart the existing log persists but the cache resets (at most
# one duplicate first-frame entry — acceptable noise).
_LAST_STATE_SHA_PER_CASE: dict[str, str] = {}

# M3.1 spike-1: serialize the cache read-check-write under per-case
# locks so overlapping `GET /workbench_frame` requests (two tabs on the
# same case, or a fast refetch racing a PATCH-triggered refetch) can't
# both pass the dedup check before either writes. Bounded scope: lock
# is per-case (not global) so unrelated cases don't contend; the lock
# is held only for the file-write critical section, so latency on the
# fire-and-forget path stays microsecond-class. Closes M3.0 push-review
# R2 P2 #2 (deferred to retro queue at the time per v2.3 cap=3).
_LOCK_REGISTRY_LOCK = threading.Lock()
_PER_CASE_LOCKS: dict[str, threading.Lock] = {}


def _lock_for_case(safe: str) -> threading.Lock:
    """Get-or-create a per-case lock. The registry mutex is held only
    long enough to insert a missing entry; lock acquisition itself
    happens outside the mutex so unrelated cases never block each
    other."""
    with _LOCK_REGISTRY_LOCK:
        lock = _PER_CASE_LOCKS.get(safe)
        if lock is None:
            lock = threading.Lock()
            _PER_CASE_LOCKS[safe] = lock
        return lock

# M3.2 cycle-1 R0 P2: severity parser removed. Provenance scraping was
# the old (M3.0 cycle 6) way to surface WARN-vs-FAIL in the log row;
# `RailPrimary` now has a first-class `severity` field
# (DEC-V61-202-SUB-M32-CYCLE1), so the log writer reads it directly
# below. Keeps API and audit_v2 vocabulary in sync — no risk of
# logging raw "critical" while the API returns normalized "fail".


def _safe_case_id(case_id: str) -> str:
    """Allow only filesystem-safe characters; reject anything that
    could escape the audit_v2 dir (matches manifest_patch's safety
    posture).

    Pure-dot names ``.`` / ``..`` / ``...`` are coerced to underscore-
    prefixed safe names so AUDIT_V2_DIR/<safe> can never resolve to a
    parent directory.
    """
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "_", case_id)
    # Pure dot strings would resolve to ./.. relative segments.
    if safe in {"", ".", ".."} or set(safe) == {"."}:
        # Codex R0 P3 fix: Python's built-in hash() is salted per process
        # (PYTHONHASHSEED), so the writer and the replay reader would
        # compute different paths in separate runs. Use a stable SHA-256
        # digest of the raw case_id (first 12 hex chars is plenty for
        # disambiguation; this is a routing key, not a security token).
        digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:12]
        return "_invalid_" + digest
    return safe


def _is_disabled() -> bool:
    """True iff the env-var gate is set. The string check accepts the
    common truthy values ("1", "true", "yes"). Anything else, including
    unset, means the log writer is active."""
    value = os.environ.get(_DISABLED_ENV_VAR, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def log_decision(state: CaseStateSnapshot, frame: WorkbenchFrame) -> None:
    """Append one JSONL line for the (state, frame) pair.

    Never raises. On any error, logs a warning and returns. The
    caller (decide()) wraps this in its own try/except as defense in
    depth, but the contract is "this function never propagates".
    """
    if _is_disabled():
        return

    try:
        safe = _safe_case_id(state.case_id)
        # Push-review R0 P2 #1 fix: same state_sha as last logged for this
        # case → passive refetch, skip.
        #
        # Push-review R1 P2 #2 fix: only update the cache AFTER a
        # successful write (post-fsync).
        #
        # M3.1 spike-1: serialize the entire read-check-write under a
        # per-case lock so overlapping requests can't both pass the
        # dedup check before either writes. Detection is per-process;
        # restart may add one duplicate (accepted).
        with _lock_for_case(safe):
            last = _LAST_STATE_SHA_PER_CASE.get(safe)
            if last is not None and last == frame.state_sha:
                return

            case_dir = AUDIT_V2_DIR / safe
            case_dir.mkdir(parents=True, exist_ok=True)
            log_path = case_dir / "decisions.jsonl"

            # bottom_card severities for at-a-glance grep
            bc_severities = [
                getattr(c, "severity", None) for c in (frame.bottom_cards or [])
            ]

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "case_id": state.case_id,
                "step": state.step,
                "focus_patch": state.focus_patch,
                "state_sha": frame.state_sha,
                "manifest_state_sha": frame.manifest_state_sha,
                "rail_primary": {
                    "kind": frame.rail_primary.kind,
                    "title": frame.rail_primary.title,
                    "field_path": frame.rail_primary.field_path,
                    # M3.2 cycle 1 (R0 P2): use the first-class
                    # `severity` field added in DEC-V61-202-SUB-M32-CYCLE1
                    # rather than scraping the provenance string. The
                    # provenance-scraping path (a) returned None for
                    # step_default rails (no severity= token), and (b)
                    # could log raw source vocabulary like "critical"
                    # instead of the API-canonical "fail" when the
                    # provenance carried source severity rather than
                    # the normalized form. Reading the schema field
                    # ensures the JSONL record matches /workbench_frame.
                    "severity": frame.rail_primary.severity,
                },
                "topbar_cta": {
                    "kind": frame.topbar_cta.kind,
                    "target_step": frame.topbar_cta.target_step,
                    "enabled": frame.topbar_cta.enabled,
                },
                "bottom_card_count": len(frame.bottom_cards or []),
                "bottom_card_severities": bc_severities,
                "viewport_overlay_count": len(frame.viewport_overlays or []),
            }

            # Single-write semantics: serialize, then write the whole
            # line in one call so partial writes can't corrupt the log.
            line = json.dumps(record, ensure_ascii=False) + "\n"
            with open(log_path, "a", encoding="utf-8") as fp:
                fp.write(line)
                fp.flush()
                os.fsync(fp.fileno())
            # Push-review R1 P2 #2 fix: cache update AFTER the file
            # write closes cleanly. A failed write raises out of the
            # inner with → cache is NOT poisoned → next call retries
            # the same state. Update still inside the per-case lock so
            # an overlapping caller sees the new value before its check.
            _LAST_STATE_SHA_PER_CASE[safe] = frame.state_sha
    except Exception as exc:  # noqa: BLE001 — fire-and-forget by contract
        logger.warning(
            "decide() provenance log failed (case=%s): %s",
            state.case_id,
            exc,
        )
