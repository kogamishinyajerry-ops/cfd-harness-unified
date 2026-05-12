"""POST /api/import/stl — STL upload → ingest → scaffold imported case.

M5.0 routine path. Consumes ``geometry_ingest`` + ``case_scaffold`` services.

Flow:
    1. Stream-read multipart upload, capped at 200 MB
    2. Parse STL via trimesh (4xx on parse failure)
    3. Run health checks (4xx on watertight failure; warnings allowed)
    4. Scaffold imported case (write triSurface + sHM stub + manifest +
       editor case YAML)
    5. Return ``{case_id, ingest_report, edit_url}``
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
import trimesh

from ui.backend.schemas.import_geometry import (
    ImportRejection,
    ImportSTLResponse,
    IngestReportPayload,
    PatchInfoPayload,
)
from ui.backend.services.case_scaffold import scaffold_imported_case
from ui.backend.services.geometry_ingest import (
    BodyAABB,
    IngestReport,
    LoadedSTL,
    combine,
    detect_patches,
    load_stl_from_bytes,
    run_health_checks,
    solid_count,
)


def _per_body_info(loaded: LoadedSTL) -> tuple[list[float], list[BodyAABB]]:
    """Per-body max bbox extents + full AABBs for a multi-solid Scene.

    Extents feed the unit-detector body-class filter (F-NEW-12, session 4).
    AABBs feed the F-NEW-26 defensive layer (session 11) inside
    :func:`run_health_checks` so the systematic-CAD-bug edge-overlap
    diagnostic surfaces through the route, not just at the
    :func:`ingest_stl` wrapper path. Single-Trimesh loads return empties
    (no per-body identity to filter on).
    """
    if not isinstance(loaded, trimesh.Scene):
        return [], []
    extents: list[float] = []
    aabbs: list[BodyAABB] = []
    for name, geom in loaded.geometry.items():
        if geom.faces.shape[0] == 0:
            continue
        b = geom.bounds
        extents.append(float(max(b[1][0] - b[0][0], b[1][1] - b[0][1], b[1][2] - b[0][2])))
        aabbs.append(
            BodyAABB(
                name=str(name),
                min_xyz=(float(b[0][0]), float(b[0][1]), float(b[0][2])),
                max_xyz=(float(b[1][0]), float(b[1][1]), float(b[1][2])),
            )
        )
    return extents, aabbs


MAX_STL_BYTES = 200 * 1024 * 1024  # 200 MB · raised from 50 MB (V198 substrate · case_003 Q3 airframe 87 MB · 2026-05-11)
_READ_CHUNK = 1 << 20  # 1 MB


router = APIRouter()


def _ingest_to_payload(report: IngestReport) -> IngestReportPayload:
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


def _classify_failing_check(report: IngestReport, parse_errors: list[str]) -> str:
    if parse_errors:
        return "stl_parse"
    if not report.is_watertight:
        return "watertight"
    if any("AABB" in e for e in report.errors):
        # F-NEW-26 defensive layer (session 11) — named-solid bodies have
        # systematic AABB overlap (≥3 edge_overlap pairs or a "significant"
        # pair). Surface as distinct failing_check so the UI can link the
        # cross-repo ticket instead of showing a generic "unknown".
        return "body_overlap"
    return "unknown"


def _select_primary_error(errors: list[str]) -> str:
    """Pick the most actionable error to show as the rejection ``reason``.

    F-NEW-26 (body AABB overlap) is preferred over downstream errors when
    present because it points at the source-CAD defect rather than a
    symptom. With the current 6-plate fixture (interpenetrating closed
    shells), watertight stays True and AABB error is the only error;
    this helper exists to keep behavior correct if a future fixture or
    real-world STL hits both.
    """
    aabb_errors = [e for e in errors if "AABB" in e]
    if aabb_errors:
        return aabb_errors[0]
    return errors[0]


async def _read_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    """Stream-read the upload, raising 413 if it exceeds ``max_bytes``."""
    buf = bytearray()
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail={
                    "reason": f"STL upload exceeds {max_bytes} bytes",
                    "failing_check": "size_limit",
                },
            )
    return bytes(buf)


@router.post("/import/stl", response_model=ImportSTLResponse)
async def import_stl_route(file: UploadFile = File(...)) -> ImportSTLResponse:
    contents = await _read_with_limit(file, MAX_STL_BYTES)

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
    body_extents_raw, body_aabbs = _per_body_info(loaded)
    report = run_health_checks(
        combined=combined,
        solid_count=solid_count(loaded),
        patches=patches,
        all_default_faces=all_default,
        body_extents_raw=body_extents_raw or None,
        body_aabbs=body_aabbs or None,
    )

    if report.errors:
        rejection = ImportRejection(
            reason=_select_primary_error(report.errors),
            failing_check=_classify_failing_check(report, []),
            ingest_report=_ingest_to_payload(report),
        )
        raise HTTPException(status_code=400, detail=rejection.model_dump())

    origin_filename = file.filename or "uploaded.stl"
    result = scaffold_imported_case(
        report=report,
        combined=combined,
        loaded=loaded,
        origin_filename=origin_filename,
    )

    return ImportSTLResponse(
        case_id=result.case_id,
        ingest_report=_ingest_to_payload(report),
        edit_url=f"/workbench/case/{result.case_id}/edit",
    )
