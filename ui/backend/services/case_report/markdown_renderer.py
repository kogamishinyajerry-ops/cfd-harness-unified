"""DEC-V61-152 (N5.1) · markdown renderer.

Templates :class:`BeginnerReport` into a 5-section markdown string.
Pure function — no AI prose, no LLM call. Each section's missing
fields surface as `(not yet set)` so the reader sees exactly what's
incomplete.

Output structure:

    # Case Report — <case_id>
    Generated 2026-05-07T12:00:00Z

    ## 1. Geometry
    - STL: <name>
    - Bounding box: ...

    ## 2. Mesh
    - Cells: N
    - ...

    ## 3. Physics
    - Fluid: ...

    ## 4. Solver
    - Derived: ...

    ## 5. Verdict
    **<literal>** — <reason>
"""
from __future__ import annotations

from ui.backend.schemas.beginner_report import BeginnerReport


_NOT_SET = "(not yet set)"


def render_beginner_report_markdown(report: BeginnerReport) -> str:
    """Render the report as a markdown string."""
    lines: list[str] = []
    lines.append(f"# Case Report — `{report.case_id}`")
    lines.append("")
    lines.append(f"_Generated {report.generated_at}_")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.extend(_render_geometry(report))
    lines.extend(_render_mesh(report))
    lines.extend(_render_physics(report))
    lines.extend(_render_solver(report))
    lines.extend(_render_verdict(report))
    return "\n".join(lines) + "\n"


def _render_geometry(report: BeginnerReport) -> list[str]:
    g = report.geometry
    lines = ["## 1. Geometry", ""]
    lines.append(f"- **STL file:** {g.stl_filename or _NOT_SET}")
    if g.bounding_box_min is not None and g.bounding_box_max is not None:
        lines.append(
            f"- **Bounding box (min):** "
            f"({g.bounding_box_min[0]:.4g}, "
            f"{g.bounding_box_min[1]:.4g}, "
            f"{g.bounding_box_min[2]:.4g})"
        )
        lines.append(
            f"- **Bounding box (max):** "
            f"({g.bounding_box_max[0]:.4g}, "
            f"{g.bounding_box_max[1]:.4g}, "
            f"{g.bounding_box_max[2]:.4g})"
        )
        if g.bounding_box_volume is not None:
            lines.append(
                f"- **Bounding box volume:** "
                f"{g.bounding_box_volume:.4g} m³"
            )
    else:
        lines.append(f"- **Bounding box:** {_NOT_SET}")
    if g.named_patches:
        lines.append(
            f"- **Named patches ({len(g.named_patches)}):** "
            + ", ".join(f"`{p}`" for p in g.named_patches)
        )
    else:
        lines.append(f"- **Named patches:** {_NOT_SET}")
    lines.append("")
    return lines


def _render_mesh(report: BeginnerReport) -> list[str]:
    m = report.mesh
    lines = ["## 2. Mesh", ""]
    if m.cell_count is None:
        lines.append(f"- **Cells:** {_NOT_SET}")
    else:
        lines.append(f"- **Cells:** {m.cell_count:,}")
    if m.point_count is not None:
        lines.append(f"- **Points:** {m.point_count:,}")
    if m.internal_face_count is not None or m.boundary_face_count is not None:
        lines.append(
            f"- **Faces:** {m.internal_face_count or 0:,} internal, "
            f"{m.boundary_face_count or 0:,} boundary"
        )
    if m.cells_per_unit_volume is not None:
        lines.append(
            f"- **Cells / unit volume:** {m.cells_per_unit_volume:,.0f}"
        )
    if m.checkmesh_ran:
        if m.checkmesh_ok is True:
            lines.append("- **checkMesh:** ✓ Mesh OK")
        elif m.checkmesh_ok is False:
            lines.append("- **checkMesh:** ✗ Mesh failed")
        if m.max_skewness is not None:
            lines.append(f"  - max skewness: `{m.max_skewness:.3f}`")
        if m.max_non_orthogonality_deg is not None:
            lines.append(
                f"  - max non-orthogonality: `{m.max_non_orthogonality_deg:.1f}°`"
            )
        if m.max_aspect_ratio is not None:
            lines.append(
                f"  - max aspect ratio: `{m.max_aspect_ratio:.0f}`"
            )
    else:
        lines.append("- **checkMesh:** skipped or not yet run")
    lines.append("")
    return lines


def _render_physics(report: BeginnerReport) -> list[str]:
    p = report.physics
    lines = ["## 3. Physics", ""]
    lines.append(f"- **Fluid:** {p.fluid_name or _NOT_SET}")
    if p.density is not None:
        lines.append(f"- **Density:** `{p.density:g}` kg/m³")
    if p.kinematic_viscosity is not None:
        lines.append(
            f"- **Kinematic viscosity:** `{p.kinematic_viscosity:.3e}` m²/s"
        )
    if p.prandtl is not None:
        lines.append(f"- **Prandtl:** `{p.prandtl:g}`")
    lines.append(
        "- **Energy equation:** "
        + ("yes" if p.has_thermal else "no (isothermal)")
    )
    lines.append(f"- **Turbulence regime:** {p.regime or _NOT_SET}")
    if p.material_citation:
        lines.append(f"- **Material citation:** {p.material_citation}")
    if p.regime_citation:
        lines.append(f"- **Regime citation:** {p.regime_citation}")
    lines.append("")
    return lines


def _render_solver(report: BeginnerReport) -> list[str]:
    s = report.solver
    lines = ["## 4. Solver", ""]
    lines.append(
        f"- **Derived solver:** `{s.derived_solver}`" if s.derived_solver
        else f"- **Derived solver:** {_NOT_SET}"
    )
    if s.derivation_rationale:
        lines.append(f"  - rationale: {s.derivation_rationale}")
    if s.tolerance_tier:
        lines.append(f"- **Tolerance tier:** `{s.tolerance_tier}`")
    if s.has_solver_overrides:
        lines.append(
            "- **Engineer overrides on solver dicts present** — see "
            "the diff section in the unified workbench"
        )
    if s.has_urf_overrides:
        lines.append(
            "- **Engineer overrides on URF present** — see the URF "
            "panel for the override list"
        )
    lines.append("")
    return lines


def _render_verdict(report: BeginnerReport) -> list[str]:
    v = report.verdict
    lines = ["## 5. Verdict", ""]
    badge = _verdict_badge(v.verdict)
    lines.append(f"**{badge}** — {v.reason}")
    lines.append("")
    return lines


_BADGES: dict[str, str] = {
    "ready_for_review": "✓ READY FOR REVIEW",
    "has_open_issues": "⚠ OPEN ISSUES",
    "physics_setup_incomplete": "✗ PHYSICS INCOMPLETE",
    "mesh_setup_incomplete": "✗ MESH INCOMPLETE",
    "geometry_setup_incomplete": "✗ GEOMETRY INCOMPLETE",
}


def _verdict_badge(verdict: str) -> str:
    return _BADGES.get(verdict, verdict.upper())


__all__ = ["render_beginner_report_markdown"]
