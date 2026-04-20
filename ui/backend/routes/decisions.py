"""Decisions Queue route (Phase 2)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from ui.backend.schemas.decisions import (
    DecisionCard,
    DecisionsQueueResponse,
    GateQueueItem,
)
from ui.backend.services.decisions import list_decisions

router = APIRouter()


@router.get("/decisions", response_model=DecisionsQueueResponse)
def get_decisions() -> DecisionsQueueResponse:
    snap = list_decisions()
    return DecisionsQueueResponse(
        cards=[DecisionCard(**asdict(c)) for c in snap.cards],
        gate_queue=[GateQueueItem(**asdict(g)) for g in snap.gate_queue],
        counts=snap.counts,
    )
