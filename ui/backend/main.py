"""FastAPI application entrypoint for the CFD Harness UI.

Run locally:
    uv pip install -e ".[ui]"
    uvicorn ui.backend.main:app --reload --host 127.0.0.1 --port 8000

Routes (Phase 0..4 — Path B MVP, per DEC-V61-002 + DEC-V61-003):

    Phase 0 — baseline read surfaces
        GET    /api/health                         → liveness probe
        GET    /api/cases                          → whitelist.yaml case index
        GET    /api/cases/{id}                     → single case definition
        GET    /api/validation-report/{id}         → Screen 4 payload

    Phase 1 — Case Editor
        GET    /api/cases/{id}/yaml                → source YAML + origin
        PUT    /api/cases/{id}/yaml                → save draft + lint
        POST   /api/cases/{id}/yaml/lint           → lint without saving
        DELETE /api/cases/{id}/yaml                → revert (delete draft)

    Phase 2 — Decisions Queue
        GET    /api/decisions                      → Kanban snapshot + gate queue

    Phase 3 — Run Monitor
        GET    /api/runs/{id}/stream               → SSE residual stream
        GET    /api/runs/{id}/checkpoints          → checkpoint snapshot

    Phase 4 — Dashboard
        GET    /api/dashboard                      → Screen 1 aggregate

    Phase 5 — Audit Package Builder (Screen 6)
        POST   /api/cases/{id}/runs/{rid}/audit-package/build
                                                    → build + sign a bundle
        GET    /api/audit-packages/{bundle_id}/manifest.json
        GET    /api/audit-packages/{bundle_id}/bundle.zip
        GET    /api/audit-packages/{bundle_id}/bundle.html
        GET    /api/audit-packages/{bundle_id}/bundle.pdf
        GET    /api/audit-packages/{bundle_id}/bundle.sig
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ui.backend.routes import (
    audit_package,
    case_editor,
    case_export,
    cases,
    comparison_report,
    dashboard,
    decisions,
    field_artifacts,
    health,
    run_monitor,
    validation,
)

app = FastAPI(
    title="CFD Harness UI Backend",
    version="0.5.0-phase-5",
    description=(
        "Path-B UI MVP — Agentic V&V-first workbench. "
        "Phase 0..5 surfaces: Validation Report, Case Editor, Decisions "
        "Queue, Run Monitor, Dashboard, Audit Package Builder. "
        "See docs/product_thesis.md + .planning/phase5_audit_package_builder_kickoff.md."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS: local dev (Vite @ 5173) allowed; tightened / origin-bound in Phase 5.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router,       prefix="/api", tags=["health"])
app.include_router(cases.router,        prefix="/api", tags=["cases"])
app.include_router(case_editor.router,  prefix="/api", tags=["case-editor"])
app.include_router(validation.router,   prefix="/api", tags=["validation"])
app.include_router(decisions.router,    prefix="/api", tags=["decisions"])
app.include_router(run_monitor.router,  prefix="/api", tags=["runs"])
app.include_router(dashboard.router,    prefix="/api", tags=["dashboard"])
app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
app.include_router(case_export.router,  prefix="/api", tags=["case-export"])
app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
app.include_router(comparison_report.router, prefix="/api", tags=["comparison-report"])
