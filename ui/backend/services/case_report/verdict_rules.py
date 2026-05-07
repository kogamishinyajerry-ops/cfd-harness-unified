"""DEC-V61-152 (N5.1) · verdict rule engine.

Pure function deriving the report's `verdict` literal from the
populated geometry / mesh / physics / solver sections. NO AI prose;
NO LLM call. The reason text is produced from a fixed library of
short phrases keyed on the section state.

Verdict precedence (most-blocking first):

  1. geometry_setup_incomplete  — STL / boundingbox missing
  2. mesh_setup_incomplete      — cell_count missing OR 0
  3. physics_setup_incomplete   — fluid name OR regime missing
  4. has_open_issues            — checkMesh failed OR derived_solver
                                  missing despite everything else set
  5. ready_for_review           — all sections populated AND
                                  checkmesh_ok=True (or unavailable)
"""
from __future__ import annotations

from ui.backend.schemas.beginner_report import (
    GeometrySection,
    MeshSection,
    PhysicsSection,
    SolverSection,
    VerdictSection,
)


def derive_verdict(
    *,
    geometry: GeometrySection,
    mesh: MeshSection,
    physics: PhysicsSection,
    solver: SolverSection,
) -> VerdictSection:
    if (
        geometry.stl_filename is None
        or geometry.bounding_box_min is None
        or geometry.bounding_box_max is None
    ):
        return VerdictSection(
            verdict="geometry_setup_incomplete",
            reason=(
                "Step 1 (Import) not yet completed — STL filename or "
                "bounding box missing."
            ),
        )

    if mesh.cell_count is None or mesh.cell_count == 0:
        return VerdictSection(
            verdict="mesh_setup_incomplete",
            reason=(
                "Step 2 (Mesh) not yet completed — polyMesh missing or "
                "cell count is 0."
            ),
        )

    if physics.fluid_name is None or physics.regime is None:
        return VerdictSection(
            verdict="physics_setup_incomplete",
            reason=(
                "Step 3 (Physics setup) not yet completed — material or "
                "turbulence regime missing."
            ),
        )

    if mesh.checkmesh_ran and mesh.checkmesh_ok is False:
        return VerdictSection(
            verdict="has_open_issues",
            reason=(
                "checkMesh reported mesh quality failures — see the "
                "honest issue list (N5.2) for specifics."
            ),
        )

    if solver.derived_solver is None:
        return VerdictSection(
            verdict="has_open_issues",
            reason=(
                "Solver derivation missing — typically because regime "
                "literal didn't resolve to a known mapping."
            ),
        )

    return VerdictSection(
        verdict="ready_for_review",
        reason=(
            "Geometry, mesh, physics, and solver setup all populated; "
            "no blocking issues detected by rule engine. Engineer "
            "should still inspect the honest issue list before merging."
        ),
    )


__all__ = ["derive_verdict"]
