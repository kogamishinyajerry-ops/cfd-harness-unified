"""Phase 7a — run_id parsing helper.

Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
We use rpartition on the last "__" so case_ids with internal underscores
(e.g. 'lid_driven_cavity') still parse correctly (07a-RESEARCH.md §2.7).
"""
from __future__ import annotations

import re
from urllib.parse import unquote

from fastapi import HTTPException

# Identifier pattern for case_id and run_label segments.
# Allow alphanumerics, underscore, hyphen, dot. Explicitly REJECT path
# separators, '..', leading dots, and percent/url-encoded traversal markers.
# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
# '..__pwn' AND '%2e%2e__pwn' — guard both decoded and raw forms.
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")


def _validate_segment(name: str, kind: str) -> None:
    """Reject traversal markers before building filesystem paths.

    Rejects: empty, '.', '..', anything containing '/', '\\', '%', or not
    matching the strict identifier pattern. Also rejects URL-decoded forms
    (in case middleware forgot to decode) so '%2e%2e' → '..' is caught.
    """
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    decoded = unquote(name)
    if decoded != name or decoded in (".", ".."):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    if not _SEGMENT_RE.match(name):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")


def parse_run_id(run_id: str) -> tuple[str, str]:
    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').

    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
    internal underscores. Labels today are simple identifiers without '__';
    rpartition is resilient if that changes.

    Both case_id and run_label are validated against a strict identifier
    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).

    Raises HTTPException(400) on malformed input.
    """
    if "__" not in run_id:
        raise HTTPException(
            status_code=400,
            detail=f"run_id must match '{{case}}__{{label}}': got {run_id!r}",
        )
    case_id, _, run_label = run_id.rpartition("__")
    if not case_id or not run_label:
        raise HTTPException(
            status_code=400,
            detail=f"run_id has empty case_id or label: {run_id!r}",
        )
    _validate_segment(case_id, "case_id")
    _validate_segment(run_label, "run_label")
    return case_id, run_label
