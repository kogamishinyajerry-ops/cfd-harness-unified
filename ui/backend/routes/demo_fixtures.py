"""Demo-fixtures route — one-click STL import for the M-PANELS visual demo.

CFDJerry-driven UX: the Import page exposes 3 buttons (one per fixture
in ``examples/imports/``) so the engineer can experience the full
M-PANELS flow without dragging a file. Each click POSTs to
``/api/demo-fixtures/<name>/import``, which reads the corresponding
checked-in STL and runs it through the same import_geometry pipeline
(``scaffold_imported_case``) the regular drag-drop path uses.

Why a dedicated route instead of having the frontend fetch the STL
bytes and re-POST to /api/import/stl: cuts an HTTP round-trip and
keeps the demo-fixture allowlist server-side (no risk of the frontend
asking the backend to scaffold an arbitrary path).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ui.backend.schemas.import_geometry import (
    ImportRejection,
    ImportSTLResponse,
    IngestReportPayload,
    PatchInfoPayload,
)
from ui.backend.services.case_scaffold import scaffold_imported_case
from ui.backend.services.geometry_ingest import (
    IngestReport,
    combine,
    detect_patches,
    load_stl_from_bytes,
    run_health_checks,
    solid_count,
)


if TYPE_CHECKING:
    from ui.backend.services.geometry_ingest import IngestReport as _IngestReport


router = APIRouter()


_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_ROOT = _REPO_ROOT / "examples" / "imports"


class DemoFixture(BaseModel):
    """Catalogue entry for one demo STL."""

    name: str  # short id used in the URL: "ldc_box" / "cylinder" / "naca0012"
    filename: str  # filename on disk (also the suggested case name)
    title: str  # human-readable label for the button
    description: str  # one-sentence body text under the button
    size_bytes: int  # for the UI to show "(6.3 KB)" next to the title


# Static allowlist. Adding a fixture here is the only way to expose it
# through the demo route — keeps the surface tight and auditable.
_FIXTURES: dict[str, DemoFixture] = {
    "ldc_box": DemoFixture(
        name="ldc_box",
        filename="ldc_box.stl",
        title="Lid-driven cavity (cube)",
        description="The canonical CFD smoke-test cube · 12 triangles · 684 B.",
        size_bytes=0,  # filled in at module load
    ),
    "cylinder": DemoFixture(
        name="cylinder",
        filename="cylinder.stl",
        title="Circular cylinder",
        description="Curved-surface stress test for the meshing pipeline · 128 triangles · 6.3 KB.",
        size_bytes=0,
    ),
    "naca0012": DemoFixture(
        name="naca0012",
        filename="naca0012.stl",
        title="NACA 0012 airfoil",
        description="Thin-shell aerospace profile · 656 triangles · 31 KB.",
        size_bytes=0,
    ),
}


def _refresh_sizes() -> None:
    """Populate size_bytes from the actual on-disk STLs."""
    for fx in _FIXTURES.values():
        path = _FIXTURE_ROOT / fx.filename
        if path.exists():
            fx.size_bytes = path.stat().st_size


_refresh_sizes()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/demo-fixtures", response_model=list[DemoFixture])
def list_demo_fixtures() -> list[DemoFixture]:
    """Return the demo-fixture catalogue. Static allowlist + on-disk size."""
    _refresh_sizes()
    return [fx for fx in _FIXTURES.values() if fx.size_bytes > 0]


def _ingest_to_payload(report: "_IngestReport") -> IngestReportPayload:
    return IngestReportPayload(
        is_watertight=report.is_watertight,
        bbox_min=report.bbox_min,
        bbox_max=report.bbox_max,
        bbox_extent=report.bbox_extent,
        unit_guess=report.unit_guess,
        solid_count=report.solid_count,
        face_count=report.face_count,
        is_single_shell=report.is_single_shell,
        patches=[PatchInfoPayload(name=p.name, face_count=p.face_count) for p in report.patches],
        all_default_faces=report.all_default_faces,
        warnings=list(report.warnings),
        errors=list(report.errors),
    )


@router.post("/demo-fixtures/{fixture_name}/import", response_model=ImportSTLResponse)
def import_demo_fixture(fixture_name: str) -> ImportSTLResponse:
    """Import the named demo STL, returning the same shape as
    ``POST /api/import/stl``. The frontend can therefore land on
    ``/workbench/case/<id>?step=1`` exactly as it does for a drag-drop.
    """
    fx = _FIXTURES.get(fixture_name)
    if fx is None:
        raise HTTPException(
            status_code=404,
            detail=f"unknown demo fixture: {fixture_name!r} (allowed: {sorted(_FIXTURES)})",
        )

    path = _FIXTURE_ROOT / fx.filename
    if not path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                f"demo fixture {fx.filename!r} listed in catalogue but missing on disk "
                f"at {path}. The repo's examples/imports/ may be incomplete."
            ),
        )

    contents = path.read_bytes()
    loaded, parse_errors = load_stl_from_bytes(contents)
    if parse_errors or loaded is None:
        rejection = ImportRejection(
            reason=parse_errors[0] if parse_errors else "STL load returned no geometry",
            failing_check="stl_parse",
            ingest_report=_ingest_to_payload(IngestReport.from_parse_failure(parse_errors)),
        )
        raise HTTPException(status_code=400, detail=rejection.model_dump())

    combined = combine(loaded)
    if combined is None:
        rejection = ImportRejection(
            reason="STL contained no geometry",
            failing_check="stl_parse",
            ingest_report=_ingest_to_payload(
                IngestReport.from_parse_failure(["STL contained no geometry"])
            ),
        )
        raise HTTPException(status_code=400, detail=rejection.model_dump())

    patches, all_default = detect_patches(loaded)
    report = run_health_checks(
        combined=combined,
        solid_count=solid_count(loaded),
        patches=patches,
        all_default_faces=all_default,
    )

    if report.errors:
        rejection = ImportRejection(
            reason=report.errors[0],
            failing_check="watertight" if not report.is_watertight else "unknown",
            ingest_report=_ingest_to_payload(report),
        )
        raise HTTPException(status_code=400, detail=rejection.model_dump())

    result = scaffold_imported_case(
        report=report,
        combined=combined,
        loaded=loaded,
        origin_filename=fx.filename,
    )

    return ImportSTLResponse(
        case_id=result.case_id,
        ingest_report=_ingest_to_payload(report),
        edit_url=f"/workbench/case/{result.case_id}/edit",
    )
