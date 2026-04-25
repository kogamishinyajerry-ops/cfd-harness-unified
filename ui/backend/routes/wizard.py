"""Onboarding-wizard routes · Stage 8a.

    GET  /api/wizard/templates              → 3 starter templates
    POST /api/wizard/draft                  → render YAML + write user draft
    GET  /api/wizard/run/{case_id}/stream   → phase-tagged SSE timeline (8a-2)

Strict additive surface — no shared code with foam_agent_adapter, no
fixture-format changes, no schema collision with line-B branches.
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse

from ui.backend.schemas.wizard import (
    DraftCreateRequest,
    DraftCreateResponse,
    TemplateListResponse,
    WizardPreviewResponse,
)
from ui.backend.services.wizard import create_draft, list_templates, render_yaml


router = APIRouter()


def _validate_case_id(case_id: str) -> None:
    """Mirrors case_drafts._draft_path's safety check upfront so the
    wizard returns a clean 400 instead of a generic ValueError."""
    safe = "".join(c for c in case_id if c.isalnum() or c in ("_", "-"))
    if safe != case_id or not case_id:
        raise HTTPException(
            status_code=400,
            detail=(
                f"case_id {case_id!r} must be non-empty alphanumeric / "
                "underscore / hyphen only."
            ),
        )


@router.get("/wizard/templates", response_model=TemplateListResponse)
def list_templates_route() -> TemplateListResponse:
    return TemplateListResponse(templates=list_templates())


@router.post("/wizard/preview", response_model=WizardPreviewResponse)
def preview_yaml_route(
    payload: DraftCreateRequest = Body(...),
) -> WizardPreviewResponse:
    """Render the same YAML body `POST /api/wizard/draft` would write,
    but without the file-write side effect. Frontend renders this text
    verbatim — closes Opus round-2 Q11 (preview-vs-create drift).

    `case_id` validation runs but is non-fatal: the preview is still
    useful while the user is still typing the id. We surface a 400 only
    when the *template* or *params* are wrong; an in-progress case_id
    just gets echoed back. (The /draft route still rejects unsafe ids.)
    """
    try:
        yaml_text = render_yaml(
            template_id=payload.template_id,
            case_id=payload.case_id or "<your-case-id>",
            name_display=payload.name_display,
            params=payload.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WizardPreviewResponse(yaml_text=yaml_text)


@router.post("/wizard/draft", response_model=DraftCreateResponse)
def create_draft_route(
    payload: DraftCreateRequest = Body(...),
) -> DraftCreateResponse:
    _validate_case_id(payload.case_id)
    try:
        return create_draft(
            template_id=payload.template_id,
            case_id=payload.case_id,
            name_display=payload.name_display,
            params=payload.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Phase-tagged SSE stream (8a-2) ----------------------------------------
# Mock execution: we walk a fixed 5-phase script with realistic per-phase
# log lines and phase-end summaries. The timing is paced (asyncio.sleep)
# so the UI animates naturally. When Stage 8b lands real solver wiring,
# only the inner generator changes — the SSE schema stays stable.

_PHASE_SCRIPT: list[dict] = [
    {
        "phase": "geometry",
        "open_msg": "正在生成几何与边界标记...",
        "logs": [
            "解析模板几何参数",
            "构造 blockMeshDict 拓扑骨架",
            "标记边界 patch (top / walls)",
        ],
        "summary_template": "geometry OK · {patch_count} patches · domain bounds 1×1 m",
        "patch_count": 4,
        "delay_per_log": 0.25,
    },
    {
        "phase": "mesh",
        "open_msg": "运行 blockMesh 生成结构化网格...",
        "logs": [
            "Reading blockMeshDict",
            "Creating block 0 (40 40 1)",
            "Creating mesh from blocks",
            "Writing polyMesh",
            "Mesh non-orthogonality Max: 0.0  average: 0.0",
            "Max skewness = 1.4e-15 OK.",
        ],
        "summary_template": "mesh OK · 1600 cells · skew 1e-15 · non-orth 0°",
        "delay_per_log": 0.15,
    },
    {
        "phase": "boundary",
        "open_msg": "写入 0/ 文件夹边界条件...",
        "logs": [
            "U  : top=fixedValue (1,0,0); walls=noSlip",
            "p  : zeroGradient on all walls; reference cell at (0,0,0)",
            "nu : 1.0e-2 (Re=100 with U=1, L=1)",
        ],
        "summary_template": "BCs OK · 3 fields written · ν=1e-2",
        "delay_per_log": 0.2,
    },
    {
        "phase": "solver",
        "open_msg": "icoFoam 求解器迭代中...",
        "logs": [
            "Time = 0.01s    Ux residual 1.2e-2    p residual 5.6e-3",
            "Time = 0.05s    Ux residual 4.1e-3    p residual 2.0e-3",
            "Time = 0.10s    Ux residual 1.3e-3    p residual 6.4e-4",
            "Time = 0.20s    Ux residual 3.8e-4    p residual 1.7e-4",
            "Time = 0.30s    Ux residual 1.1e-4    p residual 4.9e-5",
            "Time = 0.50s    Ux residual 2.3e-5    p residual 9.8e-6 (converged)",
        ],
        "summary_template": "converged · 6 timesteps · final p res 9.8e-6",
        "delay_per_log": 0.3,
        "metrics": [
            ("residual_p", 5.6e-3),
            ("residual_p", 2.0e-3),
            ("residual_p", 6.4e-4),
            ("residual_p", 1.7e-4),
            ("residual_p", 4.9e-5),
            ("residual_p", 9.8e-6),
        ],
    },
    {
        "phase": "compare",
        "open_msg": "采样观测量并对照 gold standard...",
        "logs": [
            "Sample u_centerline along x=0.5",
            "Compare to Ghia 1982 Table I (17 points)",
            "Max deviation: 4.2% at y=0.4375",
        ],
        "summary_template": "compare HAZARD · max deviation 4.2% (within 5% tolerance)",
        "delay_per_log": 0.4,
    },
]


async def _run_phase_script(case_id: str):
    """Yield SSE-formatted event lines walking the 5-phase mock script.

    Each `data: ...\\n\\n` is one RunPhaseEvent JSON object. Frontend
    EventSource gets typed events keyed off `type`.
    """

    def _ev(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    # Open
    yield _ev({"type": "log", "phase": None, "t": time.time(),
               "line": f"[wizard] case_id={case_id} starting mock pipeline (Stage 8a)"})

    for stage in _PHASE_SCRIPT:
        phase = stage["phase"]
        yield _ev({
            "type": "phase_start", "phase": phase, "t": time.time(),
            "message": stage["open_msg"],
        })
        await asyncio.sleep(0.1)

        metrics = stage.get("metrics") or []
        for i, line in enumerate(stage["logs"]):
            yield _ev({
                "type": "log", "phase": phase, "t": time.time(), "line": line,
            })
            if i < len(metrics):
                key, val = metrics[i]
                yield _ev({
                    "type": "metric", "phase": phase, "t": time.time(),
                    "metric_key": key, "metric_value": val,
                })
            await asyncio.sleep(stage["delay_per_log"])

        summary = stage["summary_template"].format(**stage)
        yield _ev({
            "type": "phase_done", "phase": phase, "t": time.time(),
            "status": "ok", "summary": summary,
        })
        await asyncio.sleep(0.05)

    yield _ev({
        "type": "run_done", "phase": None, "t": time.time(),
        "summary": (
            f"run complete · case_id={case_id} · 5 phases OK · "
            "mock execution (Stage 8a — real solver lands in 8b)"
        ),
    })


@router.get("/wizard/run/{case_id}/stream")
async def wizard_run_stream(case_id: str) -> StreamingResponse:
    _validate_case_id(case_id)
    return StreamingResponse(
        _run_phase_script(case_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
