"""gmsh-based meshing service for imported user cases (M6.0 routine path).

Public entry: :func:`mesh_imported_case`. Given an imported case_id (one
already scaffolded by M5.0's ``scaffold_imported_case``), generate a 3D
unstructured tetrahedral mesh with gmsh, convert it to OpenFOAM
``polyMesh`` format with ``gmshToFoam``, and return a summary suitable
for the workbench UI.

M6 scope (per ``.planning/strategic/m6_kickoff/spec_v2_2026-04-27.md``):

* M6.0 = gmsh path on imported geometry (this module)
* M7   = fill-in M5.0's ``snappyHexMeshDict.stub`` + execute snappyHexMesh

The two engines are deliberately not unified behind a ``mesh_engine``
selector at M6-close — there is only one valid engine right now, so the
selector would be premature.
"""
from __future__ import annotations

from .cell_budget import (
    BEGINNER_SOFT_CAP_CELLS,
    POWER_HARD_CAP_CELLS,
    BudgetVerdict,
    classify_cell_count,
)
from .gmsh_runner import GmshRunResult, run_gmsh_on_imported_case
from .pipeline import MeshResult, mesh_imported_case
from .to_foam import GmshToFoamError, run_gmsh_to_foam

__all__ = [
    "BEGINNER_SOFT_CAP_CELLS",
    "BudgetVerdict",
    "GmshRunResult",
    "GmshToFoamError",
    "MeshResult",
    "POWER_HARD_CAP_CELLS",
    "classify_cell_count",
    "mesh_imported_case",
    "run_gmsh_on_imported_case",
    "run_gmsh_to_foam",
]
