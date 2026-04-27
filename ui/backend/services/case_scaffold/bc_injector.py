"""Write the canonical STL into ``triSurface/`` and emit a minimal
``snappyHexMeshDict`` stub naming the detected patches.

The stub is consumed by M7 — it is NOT a runnable sHM dict on its own.
Stored as ``snappyHexMeshDict.stub`` to make the "M7 still owes the rest"
status visible in the case directory listing.
"""
from __future__ import annotations

from pathlib import Path

from ui.backend.services.geometry_ingest import IngestReport

from .manifest_writer import SOURCE_ORIGIN_IMPORTED_USER


def write_triSurface(
    *,
    case_dir: Path,
    origin_filename: str,
    canonical_bytes: bytes,
) -> Path:
    """Write the canonicalized STL under ``case_dir/triSurface/``."""
    out = case_dir / "triSurface" / origin_filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_bytes)
    return out


def _format_patches_block(report: IngestReport, indent: str = "    ") -> str:
    """Render detected patches as snappyHexMeshDict region entries.

    All-default-faces uploads still produce a single ``defaultFaces``
    entry so M7 has a non-empty patch list to bind sHM regions to.
    """
    lines = []
    for p in report.patches:
        lines.append(f"{indent}{p.name}")
        lines.append(f"{indent}{{")
        lines.append(f"{indent}    name {p.name};")
        lines.append(f"{indent}}}")
    return "\n".join(lines)


def write_shm_stub(
    *,
    case_dir: Path,
    origin_filename: str,
    report: IngestReport,
) -> Path:
    """Emit ``system/snappyHexMeshDict.stub`` referring to the imported STL.

    The ``.stub`` suffix is intentional: M7 reads this, fills in
    castellatedMeshControls / snapControls / addLayersControls / mesh
    quality controls based on user mesh-mode (beginner/power per D6),
    and writes the runnable ``snappyHexMeshDict``.
    """
    patches_block = _format_patches_block(report)
    body = f"""\
/*--------------------------------*- C++ -*----------------------------------*\\
| M5.0 imported case · snappyHexMeshDict STUB                                  |
| Source: {SOURCE_ORIGIN_IMPORTED_USER} · Origin: {origin_filename}                            |
| Patches detected: {len(report.patches)} · all_default_faces={report.all_default_faces} |
| Bbox extent: {report.bbox_extent} · unit_guess={report.unit_guess}           |
|                                                                              |
| Filled in by M7 (mesh wizard) — do NOT run snappyHexMesh against this stub.  |
\\*---------------------------------------------------------------------------*/

geometry
{{
    {origin_filename}
    {{
        type triSurfaceMesh;
        name imported_geometry;

        regions
        {{
{patches_block}
        }}
    }}
}}

// castellatedMeshControls / snapControls / addLayersControls / meshQualityControls
// are filled by M7 based on mesh_mode (D6: beginner cap 5M cells, power cap 50M).
// Until then this is a STUB — sHM run will fail by design.
"""
    out = case_dir / "system" / "snappyHexMeshDict.stub"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    return out
