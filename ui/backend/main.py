"""FastAPI application entrypoint for the CFD Harness UI.

Run locally:
    uv pip install -e ".[ui]"
    uvicorn ui.backend.main:app --reload --host 127.0.0.1 --port 8000

Phase 0 routes:
    GET  /api/health                         → liveness probe
    GET  /api/cases                          → whitelist.yaml case index
    GET  /api/cases/{case_id}                → single case definition
    GET  /api/validation-report/{case_id}    → Screen 4 payload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ui.backend.routes import cases, health, validation

app = FastAPI(
    title="CFD Harness UI Backend",
    version="0.1.0-phase0",
    description=(
        "Path-B UI MVP — Agentic V&V-first workbench. "
        "See docs/product_thesis.md for product context."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Phase 0 CORS: permissive for local dev, tightened in Phase 4.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(cases.router, prefix="/api", tags=["cases"])
app.include_router(validation.router, prefix="/api", tags=["validation"])
