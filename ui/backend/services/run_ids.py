"""Phase 7a — run_id parsing helper.

Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
We use rpartition on the last "__" so case_ids with internal underscores
(e.g. 'lid_driven_cavity') still parse correctly (07a-RESEARCH.md §2.7).
"""
from __future__ import annotations

from fastapi import HTTPException


def parse_run_id(run_id: str) -> tuple[str, str]:
    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').

    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
    internal underscores. Labels today are simple identifiers without '__';
    rpartition is resilient if that changes.

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
    return case_id, run_label
