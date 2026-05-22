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
from datetime import datetime, timezone
from pathlib import Path

from ui.backend.schemas.workbench_frame import (
    CaseStateSnapshot,
    WorkbenchFrame,
)
from ui.backend.services.case_scaffold.template_clone import DRAFTS_DIR

logger = logging.getLogger(__name__)

# Sibling of DRAFTS_DIR so the path travels with the same case-data
# lifecycle (cleared by cleanup scripts, archived by export, etc.).
AUDIT_V2_DIR: Path = DRAFTS_DIR / "audit_v2"

# Env-var gate. The string check is case-insensitive on the value.
_DISABLED_ENV_VAR = "WORKBENCH_PROVENANCE_DISABLED"

# Parse `severity=X` out of a RailPrimary.provenance line.
# decide() builders write traces like
#     "step=4 · problem_fix · severity=fail"
# Surfacing severity in the log row preserves the WARN-vs-FAIL signal that
# rail.kind/title alone collapse (Codex R0 P2 #2 fix).
_SEVERITY_TOKEN_RE = re.compile(r"\bseverity=([A-Za-z_]+)\b")


def _rail_severity(provenance: list[str] | None) -> str | None:
    """Best-effort extract of severity from RailPrimary.provenance.
    Returns None when no token is found (e.g., step_default rails)."""
    if not provenance:
        return None
    for line in provenance:
        match = _SEVERITY_TOKEN_RE.search(str(line))
        if match:
            return match.group(1)
    return None


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
                # severity is parsed out of provenance traces (RailPrimary
                # itself has no severity field — the upstream finding/gap
                # severity is only encoded in the provenance strings).
                # Codex R0 P2 #2 fix: surface WARN-vs-FAIL in the log row.
                "severity": _rail_severity(frame.rail_primary.provenance),
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

        # Single-write semantics: serialize, then write the whole line
        # in one call so partial writes can't corrupt the log under
        # concurrent decide() invocations.
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(log_path, "a", encoding="utf-8") as fp:
            fp.write(line)
            fp.flush()
            os.fsync(fp.fileno())
    except Exception as exc:  # noqa: BLE001 — fire-and-forget by contract
        logger.warning(
            "decide() provenance log failed (case=%s): %s",
            state.case_id,
            exc,
        )
