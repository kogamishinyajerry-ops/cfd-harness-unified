"""Agent Crew Observatory route (V93).

GET /api/agent-crew         → CrewSnapshot
GET /api/agent-crew/arc/{decision_id} → ArcDetail
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from ui.backend.services.agent_crew import (
    ArcDetail,
    CrewSnapshot,
    build_snapshot,
    get_arc_detail,
    DEC_ID_RE,
)

router = APIRouter()


def _snapshot_to_dict(snap: CrewSnapshot) -> dict:
    roles = [asdict(r) for r in snap.roles]
    arcs = []
    for arc in snap.arcs:
        arc_d = asdict(arc)
        arcs.append(arc_d)
    return {
        "roles": roles,
        "edges": snap.edges,
        "arcs": arcs,
        "stats": asdict(snap.stats),
    }


@router.get("/agent-crew")
def get_crew_snapshot() -> dict:
    snap = build_snapshot()
    return _snapshot_to_dict(snap)


@router.get("/agent-crew/arc/{decision_id}")
def get_crew_arc_detail(decision_id: str) -> dict:
    if not DEC_ID_RE.match(decision_id):
        raise HTTPException(status_code=422, detail="Invalid decision_id format")
    try:
        detail = get_arc_detail(decision_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid decision_id format")
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Arc not found: {decision_id}")
    return asdict(detail)
