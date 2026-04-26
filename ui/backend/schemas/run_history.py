"""Run history schemas · M3 · Workbench Closed-Loop main-line.

Pydantic models for the per-case run-history surface. Backed by the
filesystem layout
``reports/{case_id}/runs/{run_id}/{measurement.yaml,verdict.json,summary.json}``
written by ``RealSolverDriver`` after every real solver execution.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RunSummaryEntry(BaseModel):
    """One row in the per-case run history table."""

    case_id: str
    run_id: str = Field(description="Filesystem-safe ISO-like timestamp.")
    started_at: str = Field(description="ISO-8601 UTC timestamp string.")
    duration_s: float = Field(description="Wall-clock seconds, 0.0 if missing.")
    success: bool
    exit_code: int
    verdict_summary: str = Field(description="Short human-readable verdict.")
    # The most useful task-spec params at-a-glance — listed flat so the table
    # can render them without an extra fetch. Values copied verbatim from the
    # TaskSpec at run time.
    task_spec_excerpt: dict[str, Any] = Field(default_factory=dict)


class RunHistoryListResponse(BaseModel):
    """Body of GET /api/cases/{case_id}/runs."""

    case_id: str
    runs: list[RunSummaryEntry] = Field(default_factory=list)


class RunDetail(BaseModel):
    """Body of GET /api/cases/{case_id}/runs/{run_id}."""

    case_id: str
    run_id: str
    started_at: str
    ended_at: Optional[str] = None
    duration_s: float
    success: bool
    exit_code: int
    verdict_summary: str
    error_message: Optional[str] = None
    source_origin: str = Field(
        description="Where the case definition came from: 'draft' | 'whitelist'."
    )
    task_spec: dict[str, Any] = Field(default_factory=dict)
    key_quantities: dict[str, Any] = Field(default_factory=dict)
    residuals: dict[str, float] = Field(default_factory=dict)
