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
    batch_matrix,
    case_editor,
    case_export,
    cases,
    comparison_report,
    dashboard,
    decisions,
    exports,
    field_artifacts,
    health,
    mesh_metrics,
    preflight,
    run_history,
    validation,
    wizard,
    workbench_basics,
)

# M5.0 STL import + M6.0 gmsh meshing both require the [workbench]
# extra (trimesh, scipy, python-multipart, gmsh). The base [ui] install
# must still boot without them, so the routers are loaded conditionally.
try:
    from ui.backend.routes import import_geometry  # noqa: F401
except ModuleNotFoundError:
    import_geometry = None  # type: ignore[assignment]

try:
    from ui.backend.routes import mesh_imported  # noqa: F401
except ModuleNotFoundError:
    mesh_imported = None  # type: ignore[assignment]

try:
    from ui.backend.routes import geometry_render  # noqa: F401
except ModuleNotFoundError:
    geometry_render = None  # type: ignore[assignment]

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

# CORS: local dev (Vite @ 5180) allowed; tightened / origin-bound in Phase 5.
# 5180 chosen over the Vite default 5173 to avoid collision with other React
# projects on the same dev box (see 2026-04-22 convergence round).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5180", "http://localhost:5180"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router,       prefix="/api", tags=["health"])
app.include_router(cases.router,        prefix="/api", tags=["cases"])
app.include_router(case_editor.router,  prefix="/api", tags=["case-editor"])
app.include_router(validation.router,   prefix="/api", tags=["validation"])
app.include_router(decisions.router,    prefix="/api", tags=["decisions"])
app.include_router(dashboard.router,    prefix="/api", tags=["dashboard"])
app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
app.include_router(case_export.router,  prefix="/api", tags=["case-export"])
app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
app.include_router(comparison_report.router, prefix="/api", tags=["comparison-report"])
app.include_router(workbench_basics.router, prefix="/api", tags=["workbench-basics"])
app.include_router(mesh_metrics.router, prefix="/api", tags=["mesh-metrics"])
app.include_router(preflight.router, prefix="/api", tags=["preflight"])
app.include_router(batch_matrix.router, prefix="/api", tags=["batch-matrix"])
app.include_router(exports.router, prefix="/api", tags=["exports"])
app.include_router(wizard.router, prefix="/api", tags=["wizard"])
app.include_router(run_history.router, prefix="/api", tags=["run-history"])
if import_geometry is not None:
    app.include_router(import_geometry.router, prefix="/api", tags=["import-geometry"])
if mesh_imported is not None:
    app.include_router(mesh_imported.router, prefix="/api", tags=["mesh-imported"])
if geometry_render is not None:
    app.include_router(geometry_render.router, prefix="/api", tags=["geometry-render"])
