"""Workflow Monitor API (DEC-V61-226).

Serves the real-data WorkflowRun assembled by ``services/workflow_monitor`` —
the backend the WorkflowMonitor page consumes in place of its design-preview
fixture.

  GET /api/workflow-runs                 → list available real runs (summaries)
  GET /api/workflow-runs/{run_key}        → the assembled WorkflowRun (camelCase)
  GET /api/workflow-runs/{run_key}/events → SSE replay of stage transitions

run_key is resolved ONLY against the discovered run set (services layer), so no
filesystem path is built from arbitrary client input (no traversal surface).
All responses carry is_mock=False — every stage state is derived from real
on-disk artifacts.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ui.backend.schemas.workflow import WorkflowRun, WorkflowRunSummary
from ui.backend.services.workflow_monitor import (
    assemble_workflow_run,
    list_workflow_runs,
)

router = APIRouter()


def _format_sse(payload: dict) -> bytes:
    """Format a JSON payload as a single SSE 'data:' line + blank (matches solver_stream)."""
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


@router.get("/workflow-runs", response_model=List[WorkflowRunSummary])
def get_workflow_runs() -> List[WorkflowRunSummary]:
    return list_workflow_runs()


@router.get("/workflow-runs/{run_key}", response_model=WorkflowRun)
def get_workflow_run(run_key: str) -> WorkflowRun:
    run = assemble_workflow_run(run_key)
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown workflow run: {run_key}")
    return run


@router.get("/workflow-runs/{run_key}/events")
async def stream_workflow_run_events(run_key: str, request: Request) -> StreamingResponse:
    """Replay the assembled run as SSE: one `run` event, then per-stage `stage`
    events in pipeline order, then `done`. For a completed run this drives the
    page's live feel from real data; a future live runner emits the same shape."""
    run = assemble_workflow_run(run_key)
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown workflow run: {run_key}")

    async def _gen() -> AsyncIterator[bytes]:
        yield _format_sse(
            {
                "type": "run",
                "run": run.model_dump(by_alias=True),
            }
        )
        for stage in run.stages:
            if await request.is_disconnected():
                return
            yield _format_sse(
                {
                    "type": "stage",
                    "stage": stage.model_dump(by_alias=True),
                }
            )
        yield _format_sse({"type": "done", "currentStage": run.current_stage})

    return StreamingResponse(_gen(), media_type="text/event-stream")
