"""Pydantic schemas for Dashboard (Phase 4)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ui.backend.schemas.decisions import GateQueueItem
from ui.backend.schemas.validation import CaseIndexEntry


class DashboardTimelineEvent(BaseModel):
    date: str
    decision_id: str
    title: str
    column: str
    autonomous: bool
    github_pr_url: str | None = None
    notion_url: str | None = None


class DashboardResponse(BaseModel):
    cases: list[CaseIndexEntry] = Field(default_factory=list)
    gate_queue: list[GateQueueItem] = Field(default_factory=list)
    timeline: list[DashboardTimelineEvent] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    current_phase: str = ""
    autonomous_governance_counter: int | None = None
