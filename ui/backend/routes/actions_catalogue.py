"""DEC-V61-169 / B.5.3 · GET /api/cases/{case_id}/actions.

Engineer-discoverable workflow catalogue. Returns the canonical 5-step
mutation routes + advisor routes + query routes with `{case_id}`
substituted to the requested case. One call, full taxonomy.

Surfaced by DOGFOOD_REPORT_LIVE F2: personas spent 20+ HTTP turns
guessing route names that don't exist because the workbench splits
queries (`/api/cases/{id}/...`) from mutations (`/api/import/{id}/...`)
in a non-obvious way.

V1 ships a STATIC catalogue (hand-curated below). V2 may introspect
FastAPI's openapi spec dynamically; V1's hand-written copy keeps
human-readable descriptions tight.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR

router = APIRouter()


class ActionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int | None = Field(
        default=None,
        description=(
            "Workflow step 1-5 for mutation entries; null for advisor / "
            "query entries that are not part of the linear workflow."
        ),
    )
    name: str
    method: str  # "GET" or "POST"
    url: str
    body: str | None = Field(
        default=None,
        description=(
            "Short hint about request body shape — multipart, JSON schema "
            "name, or null for GET routes."
        ),
    )
    example_body: dict | None = Field(
        default=None,
        description=(
            "Working JSON body example for POST routes. Copy-paste-ready "
            "with sensible defaults; persona may need to swap preset_id "
            "or BC patches based on the case. Null for GET routes. "
            "Added by DEC-V61-170 / B.5.5 to address F5 schema discoverability."
        ),
    )
    description: str


class ActionsCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    steps: list[ActionEntry]
    advisor: list[ActionEntry]
    query: list[ActionEntry]
    self_discovery_fallback: str = Field(
        default="/api/openapi.json",
        description=(
            "If a route 404s and you can't guess the right path, fetch "
            "this for the full live OpenAPI schema."
        ),
    )


def _build_catalogue(case_id: str) -> ActionsCatalogue:
    cases_prefix = f"/api/cases/{case_id}"
    import_prefix = f"/api/import/{case_id}"

    steps: list[ActionEntry] = [
        ActionEntry(
            step=1,
            name="import_geometry",
            method="POST",
            url="/api/import/stl",
            body="multipart STL upload (file=<.stl bytes>)",
            description=(
                "Step 1: Import STL geometry. Returns ImportSTLResponse "
                "with workbench-assigned case_id. Multipart upload, NOT "
                "JSON. After this, all subsequent mutations use the "
                "returned case_id under /api/import/{case_id}/..."
            ),
        ),
        ActionEntry(
            step=2,
            name="mesh",
            method="POST",
            url=f"{import_prefix}/mesh",
            body="JSON {sizing_strategy, refinement_level, ...}",
            example_body={
                "sizing_strategy": "moderate",
                "refinement_level": 2,
            },
            description=(
                "Step 2: Generate volume mesh from imported STL. "
                "snappyHexMesh / cfMesh backend selected by sizing_strategy. "
                "sizing_strategy ∈ {coarse, moderate, fine}; refinement_level "
                "is an integer 0-4."
            ),
        ),
        ActionEntry(
            step=3,
            name="physics",
            method="POST",
            url=f"{cases_prefix}/physics",
            body="JSON {material: MaterialContract, regime: RegimeContract}",
            example_body={
                "material": {
                    "kind": "preset",
                    "preset_id": "air_20c",
                    "fluid": {
                        "name": "air @ 20°C",
                        "density": 1.204,
                        "kinematic_viscosity": 1.516e-5,
                    },
                },
                "regime": {
                    "kind": "preset",
                    "preset_id": "rans_komegasst_default",
                    "regime": "RANS-kOmegaSST",
                },
            },
            description=(
                "Step 3: Commit physics. Writes constant/physicalProperties "
                "+ constant/momentumTransport. Pair this with GET /physics "
                "to query current state before committing. "
                "Material preset_ids: water_20c, air_20c, air_20c_isothermal, "
                "oil_iso_vg_46_40c. Regime preset_ids: laminar_internal_default, "
                "rans_ras_kepsilon_default, rans_komegasst_default."
            ),
        ),
        ActionEntry(
            step=4,
            name="setup_bc",
            method="POST",
            url=f"{import_prefix}/setup-bc",
            body="JSON {boundary_conditions: [{patch, type, value?}, ...]}",
            example_body={
                "boundary_conditions": [
                    {"patch": "inlet", "type": "fixed_velocity",
                     "value": [1.0, 0.0, 0.0]},
                    {"patch": "outlet", "type": "zero_gradient_pressure"},
                    {"patch": "wall", "type": "no_slip"},
                ],
            },
            description=(
                "Step 4: Set boundary conditions. Writes 0/U, 0/p, 0/k, "
                "0/omega based on detected patches and engineer-chosen BC types. "
                "**Prerequisite — patches must already be split**: query "
                "GET /patch-classification first. If only `defaultFaces` "
                "is reported (single-shell STL with no named solids), you "
                "MUST split it before Step 4: PUT /face-annotations to "
                "assign face IDs to named patches (inlet, outlet, wall) "
                "OR PUT /patch-classification with grouped face IDs. "
                "Use GET /face-index to list face IDs first."
            ),
        ),
        ActionEntry(
            step=5,
            name="solve",
            method="POST",
            url=f"{import_prefix}/solve",
            body="JSON {solver_name, urf_preset, n_iterations}",
            example_body={
                "solver_name": "simpleFoam",
                "urf_preset": "simpleFoam_robust",
                "n_iterations": 500,
            },
            description=(
                "Step 5: Run the solver. simpleFoam / pimpleFoam / icoFoam "
                "selected by solver_name. urf_preset ∈ {simpleFoam_robust, "
                "simpleFoam_balanced, simpleFoam_aggressive}. Use solve-stream "
                "for SSE residual monitoring."
            ),
        ),
    ]

    advisor: list[ActionEntry] = [
        ActionEntry(
            name="ai_review",
            method="GET",
            url=f"{cases_prefix}/ai-review",
            description=(
                "AI review (read-only / ADVISORY). Returns ReviewResponse "
                "with citation-grounded findings. The advisor cannot "
                "modify case state — engineer applies fixes manually."
            ),
        ),
        ActionEntry(
            name="ai_diagnose",
            method="GET",
            url=f"{cases_prefix}/ai-diagnose",
            description=(
                "AI diagnose (read-only / ADVISORY). Returns "
                "DiagnoseResponse with citation-grounded hypotheses. "
                "Optional ?problem=stalled_residuals|diverging_residuals|"
                "mesh_check_failed|... query param."
            ),
        ),
    ]

    query: list[ActionEntry] = [
        ActionEntry(
            name="state",
            method="GET",
            url=f"{cases_prefix}/state",
            description=(
                "Snapshot the case directory state. Engineer-friendly "
                "alias of /state-preview added by DEC-V61-168."
            ),
        ),
        ActionEntry(
            name="completeness",
            method="GET",
            url=f"{cases_prefix}/completeness",
            description="Step-by-step progress percentages.",
        ),
        ActionEntry(
            name="mesh_quality",
            method="GET",
            url=f"{cases_prefix}/mesh-quality",
            description=(
                "checkMesh metrics: skewness, non-orthogonality, aspect "
                "ratio, severe-face counts."
            ),
        ),
        ActionEntry(
            name="mesh_metrics",
            method="GET",
            url=f"{cases_prefix}/mesh-metrics",
            description="Raw mesh metric report (read-only).",
        ),
        ActionEntry(
            name="physics_state",
            method="GET",
            url=f"{cases_prefix}/physics",
            description=(
                "Current constant/physicalProperties + "
                "constant/momentumTransport text. Both null if Step 3 "
                "not yet committed. Added by DEC-V61-168."
            ),
        ),
        ActionEntry(
            name="dicts",
            method="GET",
            url=f"{cases_prefix}/dicts",
            description="List of all OpenFOAM dicts in the case.",
        ),
        ActionEntry(
            name="geometry_stl",
            method="GET",
            url=f"{cases_prefix}/geometry/stl",
            description="Download the imported STL bytes.",
        ),
        ActionEntry(
            name="results_summary",
            method="GET",
            url=f"{cases_prefix}/results-summary",
            description="Solver convergence + integrated quantities summary.",
        ),
        ActionEntry(
            name="residual_history",
            method="GET",
            url=f"{cases_prefix}/residual-history.png",
            description="PNG of residual history per equation.",
        ),
        ActionEntry(
            name="run_history",
            method="GET",
            url=f"{cases_prefix}/run-history",
            description="List of solver runs for this case.",
        ),
        ActionEntry(
            name="patch_classification",
            method="GET",
            url=f"{cases_prefix}/patch-classification",
            description=(
                "List current patch → face mapping. If only `defaultFaces` "
                "is shown, the STL had no named solids and you must split "
                "the single patch via PUT before Step 4 setup-bc. Added "
                "by DEC-V61-174 / B-ext.2 (F7)."
            ),
        ),
        ActionEntry(
            name="face_annotations",
            method="GET",
            url=f"{cases_prefix}/face-annotations",
            description=(
                "List current face → patch annotations (engineer's "
                "patch-split decisions). Pair with PUT to assign or "
                "rename. Useful for splitting `defaultFaces` into "
                "inlet/outlet/wall before Step 4."
            ),
        ),
        ActionEntry(
            name="face_index",
            method="GET",
            url=f"{cases_prefix}/face-index",
            description=(
                "List of all face IDs in the imported mesh. Use to "
                "discover available faces before assigning them to "
                "named patches via PUT /face-annotations."
            ),
        ),
    ]

    return ActionsCatalogue(
        case_id=case_id,
        steps=steps,
        advisor=advisor,
        query=query,
    )


@router.get(
    "/cases/{case_id}/actions",
    response_model=ActionsCatalogue,
    tags=["actions-catalogue"],
)
def get_actions_catalogue(case_id: str) -> ActionsCatalogue:
    """Return the canonical workflow catalogue with case_id substituted."""
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": case_id},
        )
    case_dir: Path = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "case_not_found", "case_id": case_id},
        )
    return _build_catalogue(case_id)


__all__ = ["ActionEntry", "ActionsCatalogue", "router"]
