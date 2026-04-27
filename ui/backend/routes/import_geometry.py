"""POST /api/import/stl — STL upload → ingest → scaffold imported case.

M5.0 routine path. Consumes ``geometry_ingest`` + ``case_scaffold`` services.

Flow:
    1. Stream-read multipart upload, capped at 50 MB
    2. Parse STL via trimesh (4xx on parse failure)
    3. Run health checks (4xx on watertight failure; warnings allowed)
    4. Scaffold imported case (write triSurface + sHM stub + manifest +
       editor case YAML)
    5. Return ``{case_id, ingest_report, edit_url}``
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ui.backend.schemas.import_geometry import (
    ImportRejection,
    ImportSTLResponse,
    IngestReportPayload,
    PatchInfoPayload,
)
from ui.backend.services.case_scaffold import scaffold_imported_case
from ui.backend.services.geometry_ingest import (
    IngestReport,
    detect_patches,
    load_stl_from_bytes,
    run_health_checks,
)


MAX_STL_BYTES = 50 * 1024 * 1024  # 50 MB · spec D-route limit
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
    return "unknown"


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

    patches, all_default = detect_patches(loaded)
    report = run_health_checks(loaded=loaded, patches=patches, all_default_faces=all_default)

    if report.errors:
        rejection = ImportRejection(
            reason=report.errors[0],
            failing_check=_classify_failing_check(report, []),
            ingest_report=_ingest_to_payload(report),
        )
        raise HTTPException(status_code=400, detail=rejection.model_dump())

    origin_filename = file.filename or "uploaded.stl"
    result = scaffold_imported_case(
        report=report,
        loaded=loaded,
        origin_filename=origin_filename,
    )

    return ImportSTLResponse(
        case_id=result.case_id,
        ingest_report=_ingest_to_payload(report),
        edit_url=f"/workbench/case/{result.case_id}/edit",
    )
