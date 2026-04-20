"""Pydantic schemas for Decisions Queue (Phase 2) + Dashboard (Phase 4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DecisionColumn = Literal["Accepted", "Closed", "Open", "Superseded"]
GateState = Literal["OPEN", "CLOSED"]


class DecisionCard(BaseModel):
    decision_id: str
    title: str
    timestamp: str
    scope: str
    autonomous: bool
    reversibility: str
    notion_sync_status: str
    notion_url: str | None = None
    github_pr_url: str | None = None
    relative_path: str
    column: DecisionColumn
    superseded_by: str | None = None
    supersedes: str | None = None


class GateQueueItem(BaseModel):
    qid: str
    title: str
    state: GateState
    summary: str


class DecisionsQueueResponse(BaseModel):
    cards: list[DecisionCard] = Field(default_factory=list)
    gate_queue: list[GateQueueItem] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
