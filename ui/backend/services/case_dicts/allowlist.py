"""DEC-V61-102 Phase 1.2 · raw-edit allowlist.

Security boundary: only paths in :data:`ALLOWED_RAW_DICT_PATHS` can be
read or written by the case_dicts route. Anything else (notably the 0/
field directory whose contents are face_id-coupled, and any path
outside the case_dir) is 404-rejected before any filesystem touch.

Adding to this set requires a follow-up DEC because each new path
carries its own validation expectations and crash modes.
"""
from __future__ import annotations

ALLOWED_RAW_DICT_PATHS: frozenset[str] = frozenset(
    {
        # Time controls + global solver knobs.
        "system/controlDict",
        # Discretization schemes (gradient, divergence, Laplacian, etc.).
        "system/fvSchemes",
        # Linear solver settings + solution-control blocks (PISO/PIMPLE/SIMPLE).
        "system/fvSolution",
        # Optional parallel decomposition.
        "system/decomposeParDict",
        # Turbulence model selection (laminar / k-ω SST / Spalart-Allmaras / ...).
        "constant/momentumTransport",
        # Material properties (kinematic viscosity, density for
        # compressible). The actual file is ``physicalProperties`` —
        # both setup_ldc_bc and setup_channel_bc author that path
        # (verified against bc_setup.py:313 + :655). The legacy name
        # ``transportProperties`` is what older OpenFOAM tutorials use;
        # we follow what's actually written.
        "constant/physicalProperties",
        # Gravity vector (buoyant solvers).
        "constant/g",
        # NB: 0/{U, p, T, k, ...} are intentionally EXCLUDED.
        # Editing those by hand silently breaks the face_id → patch invariant
        # that bc_setup maintains. They get a structured BC editor in
        # M-RESCUE Phase 4 (DEC-V61-103+) instead of free-text raw edits.
    }
)


def is_allowed(relative_path: str) -> bool:
    """Membership test. The route layer should treat False as 404
    (not 403) so probing the allowlist doesn't leak which other paths
    might exist on disk."""
    return relative_path in ALLOWED_RAW_DICT_PATHS


__all__ = ["ALLOWED_RAW_DICT_PATHS", "is_allowed"]
