"""Dashboard route (Phase 4).

    GET /api/dashboard  → aggregated Screen 1 payload
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from ui.backend.schemas.dashboard import (
    DashboardResponse,
    DashboardTimelineEvent,
)
from ui.backend.schemas.decisions import GateQueueItem
from ui.backend.services.dashboard import build_dashboard

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard() -> DashboardResponse:
    snap = build_dashboard()
    return DashboardResponse(
        cases=snap.cases,
        gate_queue=[GateQueueItem(**asdict(g)) for g in snap.gate_queue],
        timeline=[DashboardTimelineEvent(**asdict(t)) for t in snap.timeline],
        summary=snap.summary,
        current_phase=snap.current_phase,
        autonomous_governance_counter=snap.autonomous_governance_counter,
    )
