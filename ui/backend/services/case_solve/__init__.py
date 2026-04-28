"""LDC case solve pipeline (M-PANELS Phase-C demo wiring).

Three stages, each backed by its own module:

* ``bc_setup``       — split gmshToFoam's single patch into ``lid`` +
                       ``fixedWalls``, author OpenFOAM-10 dicts
                       (icoFoam, Re=100, U_lid=1).
* ``solver_runner``  — invoke ``icoFoam`` inside the cfd-openfoam
                       container, stream the log, parse final residuals.
* ``results_extractor`` — read the final ``U`` volVectorField, extract a
                       midplane slice + summary statistics.

Scope is intentionally LDC-only for this milestone (DEC-V61-097): the
gmsh pipeline meshes the STL interior, which is correct for an
internal-flow cavity but useless for external flow. Cylinder /
NACA0012 demos require a separate blockMesh+snappyHexMesh pipeline
(out of scope for Phase-1A).
"""
from .bc_setup import (
    BCSetupError,
    BCSetupResult,
    setup_ldc_bc,
)
from .results_extractor import (
    ResultsExtractError,
    ResultsSummary,
    extract_results_summary,
)
from .solver_runner import (
    SolverRunError,
    SolverRunResult,
    run_icofoam,
)

__all__ = [
    "BCSetupError",
    "BCSetupResult",
    "ResultsExtractError",
    "ResultsSummary",
    "SolverRunError",
    "SolverRunResult",
    "extract_results_summary",
    "run_icofoam",
    "setup_ldc_bc",
]
