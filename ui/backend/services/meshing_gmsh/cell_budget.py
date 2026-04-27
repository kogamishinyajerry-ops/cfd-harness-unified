"""D6 mesh budget enforcement (M6.0 partial · 50M hard cap + 5M soft warn).

The numeric values here are deliberately not yet calibrated against
real-world STL geometries — the spec defers the beginner-cap calibration
to M6.0.1 once we have telemetry from N≥3 distinct STLs. Until then:

* 50M power-mode cap is a *verdict-grade* hard guard (resource safety,
  not a calibrated quality threshold). Exceeding it rejects the mesh.
* 5M beginner-mode cap is a *soft warning only*. The mesh still
  generates and the user can either keep it or switch to power mode.

See ``.planning/strategic/m6_kickoff/spec_v2_2026-04-27.md`` §"D6 cap
calibration" for the rationale.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# Verdict-grade resource cap. Increasing this requires explicit DEC.
POWER_HARD_CAP_CELLS = 50_000_000

# Soft sizing hint for beginner mode. Calibration follow-up: M6.0.1.
BEGINNER_SOFT_CAP_CELLS = 5_000_000


MeshMode = Literal["beginner", "power"]


@dataclass(frozen=True, slots=True)
class BudgetVerdict:
    """Outcome of a cell-count check against the configured caps.

    ``ok`` is the gate the route uses — False means the mesh must be
    rejected with HTTP 4xx. ``warning`` carries a non-blocking sizing
    note for the UI to surface inline (beginner-mode soft cap only).
    """

    ok: bool
    warning: str | None
    rejection_reason: str | None
    cell_count: int
    mesh_mode: MeshMode


def classify_cell_count(cell_count: int, mesh_mode: MeshMode) -> BudgetVerdict:
    """Apply the D6 cap rules to a freshly-generated mesh.

    Power mode: hard-reject above POWER_HARD_CAP_CELLS.
    Beginner mode: soft-warn above BEGINNER_SOFT_CAP_CELLS, hard-reject
    above POWER_HARD_CAP_CELLS (the resource ceiling still applies).
    """
    if cell_count > POWER_HARD_CAP_CELLS:
        return BudgetVerdict(
            ok=False,
            warning=None,
            rejection_reason=(
                f"mesh has {cell_count:,} cells — exceeds the "
                f"{POWER_HARD_CAP_CELLS:,}-cell hard cap. Coarsen the "
                "characteristic length and re-run."
            ),
            cell_count=cell_count,
            mesh_mode=mesh_mode,
        )

    warning: str | None = None
    if mesh_mode == "beginner" and cell_count > BEGINNER_SOFT_CAP_CELLS:
        # Power mode is the *finer* sizing tier — switching would make
        # the cell count larger, not smaller. The actionable advice for
        # a user who already overshot the beginner soft cap is to
        # coarsen the geometry (or accept the larger mesh).
        warning = (
            f"mesh has {cell_count:,} cells — larger than typical "
            f"beginner sizing ({BEGINNER_SOFT_CAP_CELLS:,}). Coarsen "
            "the input geometry (reduce CAD detail or remove small "
            "features) if a smaller mesh is required, or accept the "
            "larger mesh and proceed."
        )

    return BudgetVerdict(
        ok=True,
        warning=warning,
        rejection_reason=None,
        cell_count=cell_count,
        mesh_mode=mesh_mode,
    )
