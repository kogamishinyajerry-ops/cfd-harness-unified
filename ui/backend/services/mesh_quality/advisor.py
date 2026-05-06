"""DEC-V61-138 (N2.4) · checkMesh advisor — rule-based suggestion engine.

Pure function over a populated :class:`MeshQualityReportV126`. Maps
checkMesh metric thresholds to human-readable fix advice the engineer
reads + decides. Output is **read-only metadata** — UI must render
``recommended_change`` as displayed text, NOT an apply-button payload.

V130 Principle B (AI advises, engineer applies) + V132 contract
(advisory surfaces NEVER call mutating routes). This module returns
data; it does not POST anything.

Threshold rationale (matches MeshQualityCard gauges):
  * non_orthogonality_deg: >75° = OpenFOAM corrector limit
  * skewness: >0.7 = warning band, >0.95 = Fluent reject
  * aspect_ratio: >1000 = boundary-layer prism territory or defect
  * n_severe_non_ortho_faces > 0 = sizing field / refinement zone hint

When V126 was returned with checkMesh skipped (graceful degradation
where every checkmesh_* metric is None), the advisor returns ``[]``
— there's nothing to advise on. The empty list is also returned for
clean meshes (a single ``mesh_ok`` info entry would be noise).
"""
from __future__ import annotations

from ui.backend.services.mesh_quality.schemas import (
    MeshFixSuggestion,
    MeshQualityReportV126,
)


# Threshold constants — keep in sync with MeshQualityCard band ladders.
_NON_ORTHO_REJECT_DEG = 75.0
_NON_ORTHO_WARNING_DEG = 65.0
_SKEWNESS_REJECT = 0.95
_SKEWNESS_WARNING = 0.7
_ASPECT_RATIO_DEFECT = 1000.0
_ASPECT_RATIO_WARNING = 100.0


def derive_suggestions(report: MeshQualityReportV126) -> list[MeshFixSuggestion]:
    """Map checkMesh metrics on ``report`` to fix suggestions.

    Returns empty list when:
      * checkMesh was skipped (all checkmesh_* fields None — graceful
        degradation path)
      * mesh is clean (mesh_ok=True with all metrics under warning
        thresholds)

    Each emitted suggestion carries metadata only — the frontend
    renders ``recommended_change`` as copy-paste text, not as an
    apply-button payload (V132 contract).
    """
    out: list[MeshFixSuggestion] = []

    # Severe non-orthogonal faces — most actionable signal because the
    # per-patch breakdown localizes the problem to specific geometry.
    severe = report.checkmesh_n_severe_non_ortho_faces
    if severe is not None and severe > 0:
        per_patch = report.checkmesh_n_severe_non_ortho_faces_per_patch or {}
        worst_patches = sorted(
            ((name, n) for name, n in per_patch.items() if n > 0),
            key=lambda kv: kv[1],
            reverse=True,
        )[:3]
        if worst_patches:
            patch_hint = ", ".join(f"{name} ({n})" for name, n in worst_patches)
            text = (
                f"{severe} severely non-orthogonal face"
                f"{'' if severe == 1 else 's'} (>70°) detected, "
                f"concentrated on: {patch_hint}. Consider tightening "
                "the sizing field near these patches (Step 2 → sizing) "
                "or adding a refinement zone (Step 2 → region refinement) "
                "around the affected geometry."
            )
        else:
            text = (
                f"{severe} severely non-orthogonal face"
                f"{'' if severe == 1 else 's'} (>70°) detected. "
                "Consider tightening the sizing field (Step 2 → sizing) "
                "or adding a refinement zone (Step 2 → region refinement) "
                "near sharp geometric features."
            )
        out.append(
            MeshFixSuggestion(
                metric="n_severe_non_ortho_faces",
                severity="warning",
                suggestion_text=text,
                recommended_change={
                    "step": "Step 2 · sizing or region refinement",
                    "patches_affected": [name for name, _ in worst_patches],
                    "hint": (
                        "halve the sizing-field characteristic length OR "
                        "add a box/sphere refinement zone level=2 around "
                        "the listed patches"
                    ),
                },
            )
        )

    # Max non-orthogonality magnitude — independent gauge even when
    # severe-face count is low.
    nod = report.checkmesh_max_non_orthogonality_deg
    if nod is not None:
        if nod > _NON_ORTHO_REJECT_DEG:
            out.append(
                MeshFixSuggestion(
                    metric="max_non_orthogonality",
                    severity="critical",
                    suggestion_text=(
                        f"max non-orthogonality {nod:.1f}° exceeds OpenFOAM's "
                        "non-orthogonal corrector limit (~75°). The solver may "
                        "diverge or require nNonOrthogonalCorrectors >= 2. "
                        "Consider re-meshing with a finer sizing field or "
                        "refining around the offending feature."
                    ),
                    recommended_change={
                        "step": "Step 2 · sizing",
                        "hint": "halve the global characteristic length",
                    },
                )
            )
        elif nod > _NON_ORTHO_WARNING_DEG:
            out.append(
                MeshFixSuggestion(
                    metric="max_non_orthogonality",
                    severity="warning",
                    suggestion_text=(
                        f"max non-orthogonality {nod:.1f}° is in the marginal "
                        "band (65°-75°). Solver should converge but may need "
                        "nNonOrthogonalCorrectors=1 in fvSolution."
                    ),
                    recommended_change=None,
                )
            )

    # Max skewness.
    skew = report.checkmesh_max_skewness
    if skew is not None:
        if skew > _SKEWNESS_REJECT:
            out.append(
                MeshFixSuggestion(
                    metric="max_skewness",
                    severity="critical",
                    suggestion_text=(
                        f"max skewness {skew:.2f} exceeds Fluent's reject "
                        "threshold (0.95). Highly skewed cells will degrade "
                        "interpolation accuracy and may stall convergence. "
                        "Consider re-meshing with curvature-aware sizing."
                    ),
                    recommended_change={
                        "step": "Step 2 · sizing or region refinement",
                        "hint": (
                            "use curvature-based sizing (smaller characteristic "
                            "length on curved patches) or add a refinement zone "
                            "around sharp features"
                        ),
                    },
                )
            )
        elif skew > _SKEWNESS_WARNING:
            out.append(
                MeshFixSuggestion(
                    metric="max_skewness",
                    severity="warning",
                    suggestion_text=(
                        f"max skewness {skew:.2f} is in the marginal band "
                        "(0.7-0.95). k-omega SST and other turbulence models "
                        "may show slow convergence near these cells."
                    ),
                    recommended_change=None,
                )
            )

    # Aspect ratio — high values often legitimate for prism stacks but
    # >1000 typically signals a defect or missing prism layer.
    ar = report.checkmesh_max_aspect_ratio
    if ar is not None:
        if ar > _ASPECT_RATIO_DEFECT:
            out.append(
                MeshFixSuggestion(
                    metric="max_aspect_ratio",
                    severity="warning",
                    suggestion_text=(
                        f"max aspect ratio {ar:.0f} is very high (>1000). "
                        "If wall resolution is intentional, configure a "
                        "structured prism layer (Step 2 → prism layers) "
                        "with a controlled expansion ratio instead of "
                        "letting tetrahedra stretch. Otherwise the "
                        "anisotropy likely indicates a meshing defect."
                    ),
                    recommended_change={
                        "step": "Step 2 · prism layers",
                        "hint": (
                            "first_cell_height ≈ y+ target / 2, "
                            "expansion_ratio 1.2-1.3, num_layers 5-10"
                        ),
                    },
                )
            )
        elif ar > _ASPECT_RATIO_WARNING:
            out.append(
                MeshFixSuggestion(
                    metric="max_aspect_ratio",
                    severity="info",
                    suggestion_text=(
                        f"max aspect ratio {ar:.0f} is elevated (>100). "
                        "Acceptable for boundary-layer prism stacks; "
                        "investigate if no prism layer is configured."
                    ),
                    recommended_change=None,
                )
            )

    # mesh_ok=False without any specific metric breach — surface a
    # generic hint pointing the engineer at the failed-checks list.
    if (
        report.checkmesh_mesh_ok is False
        and not out
        and report.checkmesh_failed_checks
    ):
        out.append(
            MeshFixSuggestion(
                metric="mesh_ok",
                severity="warning",
                suggestion_text=(
                    "checkMesh reported failures but no specific metric "
                    "exceeded its threshold. Review the listed failed "
                    "checks above and inspect the case STL near the "
                    "affected patches."
                ),
                recommended_change=None,
            )
        )

    return out
