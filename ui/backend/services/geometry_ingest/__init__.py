"""STL ingest service · M5.0 routine path.

Public entry: :func:`ingest_stl(data: bytes) -> IngestReport`.

Health checks are honest: watertight failure produces ``errors`` (route
will reject with 4xx). All-defaultFaces (no named solids) and unknown
unit-guess produce ``warnings`` (UI shows inline help; user can confirm).
"""
from __future__ import annotations

from .health_check import IngestReport, PatchInfo, run_health_checks
from .patch_detector import detect_patches
from .stl_loader import LoadedSTL, canonical_stl_bytes, load_stl_from_bytes


def ingest_stl(data: bytes) -> IngestReport:
    """Parse + sanity-check an uploaded STL byte stream.

    Steps:
        1. Parse via trimesh (ASCII or binary auto-detected by content).
        2. Detect patches (named solids → patch list; single-solid blob
           → ``all_default_faces=True``).
        3. Run health checks (watertight, bbox, unit-guess, single-shell).
        4. Return the assembled ``IngestReport``.

    A non-empty ``errors`` list means the route should reject the upload.
    Warnings are advisory only.
    """
    loaded, parse_errors = load_stl_from_bytes(data)
    if parse_errors:
        return IngestReport.from_parse_failure(parse_errors)

    patches, all_default_faces = detect_patches(loaded)
    return run_health_checks(
        loaded=loaded,
        patches=patches,
        all_default_faces=all_default_faces,
    )


__all__ = [
    "IngestReport",
    "LoadedSTL",
    "PatchInfo",
    "canonical_stl_bytes",
    "ingest_stl",
    "load_stl_from_bytes",
]
