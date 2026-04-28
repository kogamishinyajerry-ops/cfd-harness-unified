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
    # Phase-1A (DEC-V61-097): which step in the panel this fixture can
    # actually advance through. The gmsh pipeline meshes the STL
    # interior, which is correct as a flow domain ONLY for closed
    # cavities (ldc_box). External-flow demos require a separate
    # blockMesh+sHM pipeline that is NOT in scope for Phase-1A.
    full_demo_capable: bool  # True if the fixture supports Steps 1→5 end-to-end
    capability_note: str  # human-readable explanation of the capability bound


# Static allowlist. Adding a fixture here is the only way to expose it
# through the demo route — keeps the surface tight and auditable.
_FIXTURES: dict[str, DemoFixture] = {
    "ldc_box": DemoFixture(
        name="ldc_box",
        filename="ldc_box.stl",
        title="Lid-driven cavity (cube) — full demo",
        description="The canonical CFD smoke-test cube · 12 triangles · 684 B. Walks Steps 1→5 end-to-end with icoFoam Re=100.",
        size_bytes=0,
        full_demo_capable=True,
        capability_note="Closed cavity → gmsh's interior tet-mesh IS the flow domain. icoFoam runs ~60s and produces a recirculating LDC vortex.",
    ),
    "cylinder": DemoFixture(
        name="cylinder",
        filename="cylinder.stl",
        title="Circular cylinder (Steps 1+2 only)",
        description="Curved-surface stress test for the meshing pipeline · 128 triangles · 6.3 KB. Stops at Step 2 — external-flow simulation needs Phase-2.",
        size_bytes=0,
        full_demo_capable=False,
        capability_note="External-flow geometry: gmsh would mesh the cylinder's interior, which is NOT a flow domain. Requires blockMesh+snappyHexMesh (Phase-2).",
    ),
    "naca0012": DemoFixture(
        name="naca0012",
        filename="naca0012.stl",
        title="NACA 0012 airfoil (Steps 1+2 only)",
        description="Thin-shell aerospace profile · 656 triangles · 31 KB. Stops at Step 2 — external-flow simulation needs Phase-3.",
        size_bytes=0,
        full_demo_capable=False,
        capability_note="External-flow geometry: same caveat as the cylinder, plus thinner wake refinement requirements.",
    ),
}


def _refresh_sizes() -> None:
    """Re-stat every catalogue entry's STL on disk and update ``size_bytes``.

    Codex Round 6 P2: previously this only WROTE size_bytes when the
    file existed, leaving stale non-zero values for fixtures that
    disappeared from disk. Always overwrite (size if present, 0
    otherwise) so the list reflects the live filesystem state.

    Codex Round 7 P3: collapse the ``exists()`` → ``stat()`` TOCTTOU
    window by stat-ing directly and treating ``FileNotFoundError`` as
    "missing". A concurrent deletion between the two syscalls would
    otherwise let a 500 escape from a route promising to just hide
    the fixture.
    """
    for fx in _FIXTURES.values():
        path = _FIXTURE_ROOT / fx.filename
        try:
            fx.size_bytes = path.stat().st_size
        except FileNotFoundError:
            fx.size_bytes = 0


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

    # Codex Round 7 P3: collapse the ``exists()`` → ``read_bytes()``
    # TOCTTOU window by attempting the read directly. FileNotFoundError
    # surfaces as the same missing-on-disk 500 the explicit check
    # produced before — same observable contract, no race window for
    # an external deletion to slip a 5xx escape past us.
    #
    # Codex Round 6 Q3 follow-up: parse / watertight failures on a
    # server-owned checked-in fixture are operator faults, not user-
    # upload faults. /api/import/stl returns 4xx because the user
    # supplied bad bytes; here the server supplied them. Surface as
    # 500 so operators see the breakage instead of users getting a
    # confusing "bad geometry" message about a fixture they didn't
    # author.
    path = _FIXTURE_ROOT / fx.filename
    try:
        contents = path.read_bytes()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"demo fixture {fx.filename!r} listed in catalogue but missing on disk "
                f"at {path}. The repo's examples/imports/ may be incomplete."
            ),
        ) from exc
    loaded, parse_errors = load_stl_from_bytes(contents)
    if parse_errors or loaded is None:
        raise HTTPException(
            status_code=500,
            detail=(
                f"demo fixture {fx.filename!r} failed STL parse: "
                f"{parse_errors[0] if parse_errors else 'no geometry'} — "
                f"the checked-in asset is corrupt and needs operator attention."
            ),
        )

    combined = combine(loaded)
    if combined is None:
        raise HTTPException(
            status_code=500,
            detail=(
                f"demo fixture {fx.filename!r} contained no usable geometry "
                f"after combine() — the checked-in asset is corrupt."
            ),
        )

    patches, all_default = detect_patches(loaded)
    report = run_health_checks(
        combined=combined,
        solid_count=solid_count(loaded),
        patches=patches,
        all_default_faces=all_default,
    )

    if report.errors:
        raise HTTPException(
            status_code=500,
            detail=(
                f"demo fixture {fx.filename!r} failed health checks: "
                f"{report.errors[0]} — the checked-in asset is corrupt."
            ),
        )

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
