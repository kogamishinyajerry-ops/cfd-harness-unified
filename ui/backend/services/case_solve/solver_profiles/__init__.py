"""DEC-V61-112 · Solver-profile YAML migration.

YAML-driven solver-specific dict authoring. Each profile defines
the controlDict / fvSchemes / fvSolution OpenFOAM templates for a
specific solver (simpleFoam steady-state, pimpleFoam transient,
etc.); BC-setup call sites load + render the profile rather than
inlining the template strings.

Public API:

* :class:`SolverProfile` — schema dataclass
* :func:`load_profile` — YAML → SolverProfile loader
* :exc:`ProfileNotFoundError` — unknown solver name
* :exc:`ProfileSchemaError` — malformed YAML

Phase 1 ships the simpleFoam profile only (extracts V61-111 inline
templates from ``bc_setup_from_stl_patches``). Phases 2-4 follow:
pimpleFoam (V61-107.5 + V61-111 channel/STL paths), icoFoam (LDC
``setup_ldc_bc``), then setup_channel_bc rewire.
"""
from __future__ import annotations

from .registry import (
    ProfileNotFoundError,
    ProfileSchemaError,
    list_profile_names,
    load_profile,
)
from .schema import SolverProfile

__all__ = [
    "ProfileNotFoundError",
    "ProfileSchemaError",
    "SolverProfile",
    "list_profile_names",
    "load_profile",
]
