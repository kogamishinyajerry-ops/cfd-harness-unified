"""DEC-V61-122 · mesh-quality adviser foundation.

Pure-Python parser for `<case_dir>/constant/polyMesh/{points, owner,
neighbour, boundary}` that produces a structured
:class:`MeshQualityReport`. Consumed by:

  * GET /api/cases/{case_id}/mesh-quality (route layer)
  * services.llm_coach.prompts (system-prompt extension)

V1 explicit scope: ASCII polyMesh format only. Binary format support,
Docker checkMesh integration, per-cell volume/skewness/orthogonality
metrics, and frontend cards land in V61-123 / V61-124.

Public entry point:
    analyze_mesh_quality(case_dir) -> MeshQualityReport

Raises :class:`MeshQualityNotAvailableError` when polyMesh is missing
(404-equivalent for the route) and :class:`MeshQualityParseError` for
corrupt files (500-equivalent — V122 surfaces a stable failing_check
detail rather than an opaque traceback).
"""
from __future__ import annotations

from ui.backend.services.mesh_quality.analyzer import (
    MeshQualityNotAvailableError,
    MeshQualityParseError,
    analyze_mesh_quality,
)
from ui.backend.services.mesh_quality.checkmesh_runner import (
    CheckMeshError,
    CheckMeshResult,
    run_checkmesh,
)
from ui.backend.services.mesh_quality.schemas import (
    MeshQualityReport,
    MeshQualityReportResponse,
    MeshQualityReportV126,
    MeshSeverity,
    MeshWarning,
)

__all__ = [
    "CheckMeshError",
    "CheckMeshResult",
    "MeshQualityNotAvailableError",
    "MeshQualityParseError",
    "MeshQualityReport",
    "MeshQualityReportResponse",
    "MeshQualityReportV126",
    "MeshSeverity",
    "MeshWarning",
    "analyze_mesh_quality",
    "run_checkmesh",
]
