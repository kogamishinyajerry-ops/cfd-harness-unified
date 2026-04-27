"""STL ingest service · M5.0 routine path.

Public entry: :func:`ingest_stl(data: bytes) -> IngestReport`.

Health checks are honest: watertight failure produces ``errors`` (route
will reject with 4xx). All-defaultFaces (no named solids) and unknown
unit-guess produce ``warnings`` (UI shows inline help; user can confirm).
"""
from __future__ import annotations

from .health_check import IngestReport, PatchInfo, run_health_checks
from .patch_detector import detect_patches
from .stl_loader import (
    LoadedSTL,
    canonical_stl_bytes,
    combine,
    load_stl_from_bytes,
    solid_count,
)


def ingest_stl(data: bytes) -> IngestReport:
    """Parse + sanity-check an uploaded STL byte stream.

    Single-pass: load → combine → detect patches → health checks. The
    combined mesh is computed once and discarded; callers needing it for
    canonicalization (e.g. the route) should drive the lower-level
    helpers directly so they can pass the same combined mesh to
    :func:`canonical_stl_bytes`.
    """
    loaded, parse_errors = load_stl_from_bytes(data)
    if parse_errors or loaded is None:
        return IngestReport.from_parse_failure(parse_errors)
    combined = combine(loaded)
    if combined is None:
        return IngestReport.from_parse_failure(["STL contained no geometry"])
    patches, all_default_faces = detect_patches(loaded)
    return run_health_checks(
        combined=combined,
        solid_count=solid_count(loaded),
        patches=patches,
        all_default_faces=all_default_faces,
    )


__all__ = [
    "IngestReport",
    "LoadedSTL",
    "PatchInfo",
    "canonical_stl_bytes",
    "combine",
    "detect_patches",
    "ingest_stl",
    "load_stl_from_bytes",
    "run_health_checks",
    "solid_count",
]
