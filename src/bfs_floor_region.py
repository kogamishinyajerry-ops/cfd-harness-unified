"""Shared downstream-reattachment-floor face mask for the backward-facing step.

SINGLE SOURCE OF TRUTH for the geometric filter that selects the downstream
reattachment-floor faces (y≈0, x>0, before the outlet) of a backward-facing-step
``lower_wall`` patch from face-centre coordinates.

Why this module exists (DEC-V61-235 · cfd-vv-director condition)
----------------------------------------------------------------
Two consumers MUST mask the SAME floor faces, or the V71.B y+<1 resolved-wall
precondition would gate a *different* face set than the one the reattachment QoI
is measured on (a silently-lying gate):

  1. The LIVE reattachment extractor in ``src.foam_agent_adapter`` (Path-1a,
     wall-shear tau_x zero-crossing on the allPatches VTK).
  2. The V71.B ``src.bfs_lowre_extractor`` / ``src.bfs_lowre_gate`` (which gates
     the first-cell y+ over the reattachment floor AND re-measures reattachment).

Both import ``bfs_floor_mask`` here so the QoI floor faces and the gated-y+ floor
faces are byte-identical — no mask drift (re-typing the literal in two places is
the structurally-decaying anti-pattern the V&V review flagged).

Filter rationale (DEC-V61-052 round 3, the established BFS floor filter):
  - ``y < 0.05``   → excludes the inlet floor at y=1 and the bulk of the step face.
  - ``x > 0.05``   → excludes the vertical step face at x=0 (spans y∈[0,1]).
  - ``x < 29.5``   → excludes the B1 outlet faces at x=30 (L_down = 30·H).

The bounds work independently of patchID ordering (which varies across OpenFOAM
builds), so the same mask is valid on the high-Re (wall-function) mesh and the
V71.B resolved (y+<1) mesh.

ADR-001 plane assignment: **Execution Plane** (a pure geometric helper over solver
face-centre coordinates; no Evaluation/Control imports; stdlib-only).
"""
from __future__ import annotations

from typing import Any

# Downstream reattachment-floor bounds (see module docstring + DEC-V61-052 r3).
BFS_FLOOR_Y_MAX: float = 0.05
BFS_FLOOR_X_MIN: float = 0.05
BFS_FLOOR_X_MAX: float = 29.5


def bfs_floor_mask(centres: Any) -> Any:
    """Boolean mask selecting downstream reattachment-floor faces.

    ``centres`` is an ``(N, 3)`` array-like of face-centre coordinates (a numpy
    array, the natural shape of ``pyvista`` ``cell_centers().points``). Returns a
    boolean array of length ``N`` (``True`` where the face is a reattachment-floor
    face). Uses only numpy column indexing — this module imports no numpy itself,
    so it stays import-light and stdlib-only.
    """
    return (
        (centres[:, 1] < BFS_FLOOR_Y_MAX)
        & (centres[:, 0] > BFS_FLOOR_X_MIN)
        & (centres[:, 0] < BFS_FLOOR_X_MAX)
    )


def is_floor_face(x: float, y: float) -> bool:
    """Scalar form of :func:`bfs_floor_mask` for one ``(x, y)`` face centre.

    Used by the stdlib CSV reader path (``src.bfs_lowre_extractor``) so the frozen
    ``floor_faces.csv`` is filtered with the IDENTICAL bounds as the live VTK path.
    """
    return (y < BFS_FLOOR_Y_MAX) and (x > BFS_FLOOR_X_MIN) and (x < BFS_FLOOR_X_MAX)
