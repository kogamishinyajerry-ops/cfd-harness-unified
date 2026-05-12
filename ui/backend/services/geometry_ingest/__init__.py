"""STL ingest service · M5.0 routine path.

Public entry: :func:`ingest_stl(data: bytes) -> IngestReport`.

Health checks are honest: watertight failure produces ``errors`` (route
will reject with 4xx). All-defaultFaces (no named solids) and unknown
unit-guess produce ``warnings`` (UI shows inline help; user can confirm).
"""
from __future__ import annotations

from .health_check import (
    BodyAABB,
    BodyPairOverlap,
    IngestReport,
    PatchInfo,
    detect_body_pair_overlaps,
    run_health_checks,
)
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
    import trimesh

    loaded, parse_errors = load_stl_from_bytes(data)
    if parse_errors or loaded is None:
        return IngestReport.from_parse_failure(parse_errors)
    combined = combine(loaded)
    if combined is None:
        return IngestReport.from_parse_failure(["STL contained no geometry"])
    patches, all_default_faces = detect_patches(loaded)
    body_extents_raw: list[float] | None = None
    body_aabbs: list[BodyAABB] | None = None
    if isinstance(loaded, trimesh.Scene):
        body_extents_raw = []
        body_aabbs = []
        for name, geom in loaded.geometry.items():
            if geom.faces.shape[0] == 0:
                continue
            b = geom.bounds
            body_extents_raw.append(
                float(max(b[1][0] - b[0][0], b[1][1] - b[0][1], b[1][2] - b[0][2]))
            )
            body_aabbs.append(
                BodyAABB(
                    name=str(name),
                    min_xyz=(float(b[0][0]), float(b[0][1]), float(b[0][2])),
                    max_xyz=(float(b[1][0]), float(b[1][1]), float(b[1][2])),
                )
            )
        body_extents_raw = body_extents_raw or None
        body_aabbs = body_aabbs or None
    return run_health_checks(
        combined=combined,
        solid_count=solid_count(loaded),
        patches=patches,
        all_default_faces=all_default_faces,
        body_extents_raw=body_extents_raw,
        body_aabbs=body_aabbs,
    )


__all__ = [
    "BodyAABB",
    "BodyPairOverlap",
    "IngestReport",
    "LoadedSTL",
    "PatchInfo",
    "canonical_stl_bytes",
    "combine",
    "detect_body_pair_overlaps",
    "detect_patches",
    "ingest_stl",
    "load_stl_from_bytes",
    "run_health_checks",
    "solid_count",
]
