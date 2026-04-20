"""Run Monitor routes (Phase 3).

    GET /api/runs/{case_id}/stream      → Server-Sent Events residual stream
    GET /api/runs/{case_id}/checkpoints → snapshot table (non-streaming)

SSE format: `data: {json}\\n\\n` per message. Clients use EventSource.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ui.backend.services.run_monitor import (
    snapshot_last_n_checkpoints,
    stream_run,
)

router = APIRouter()


@router.get("/runs/{case_id}/stream")
def run_stream(case_id: str) -> StreamingResponse:
    return StreamingResponse(
        stream_run(case_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx-like buffering
            "Connection": "keep-alive",
        },
    )


@router.get("/runs/{case_id}/checkpoints")
def run_checkpoints(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "source": "synthetic-phase-3",
        "checkpoints": snapshot_last_n_checkpoints(),
    }
