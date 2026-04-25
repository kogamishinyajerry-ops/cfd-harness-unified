"""RBC multi-dimensional extractors · DEC-V61-060 Batch B.

Pure-helper extractors operating on pre-loaded cell-center field arrays from
a 2D Rayleigh-Bénard simulation snapshot. Designed for the Pandey &
Schumacher 2018 TU Ilmenau benchmark (Ra=1e6, Pr=10, AR=4, bottom-heated
horizontal walls, insulated sidewalls).

Each extractor:
  - takes an ``RBCFieldSlice`` + ``RBCBoundary`` pair (pre-loaded
    cell-center fields and BC metadata),
  - returns ``{value, ...diagnostics}`` so the comparator/UI can decide
    FAIL/PASS/ADVISORY based on the gate_status declared in the gold YAML
    (HARD_GATED / NON_TYPE_HARD_INVARIANT / PROVISIONAL_ADVISORY),
  - fails closed (returns ``{}``) on input shape errors instead of raising,
    so an invalid input degrades to MISSING_TARGET_QUANTITY at the gate.

Module is Execution-plane (registered in ``src._plane_assignment``) — must
NOT import from ``src.auto_verifier``, ``src.metrics``,
``src.report_engine``, or any other Evaluation-plane module per ADR-001.

Mirrors the dhc_extractors.py pattern from V61-057 — duplicates the
x-layer (transposed) grouping logic from
``foam_agent_adapter._extract_nc_nusselt`` rather than coupling to it.
RBC's hot wall is HORIZONTAL (y=0), so the grouping axis is y (across
layers) and the profile axis within each layer is x (which we then
collapse to a single Nu per x-column or average across all x).

For RBC the only B.1 extractor is ``extract_nu_asymmetry`` — the
NON_TYPE_HARD_INVARIANT defined as |Nu_top − Nu_bottom| / |Nu_bottom|.
B.2 (w_max) and B.3 (roll_count) land in subsequent commits.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.wall_gradient import BCContractViolation, extract_wall_gradient


# ---------------------------------------------------------------------------
# Input dataclasses (frozen; pure value objects)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RBCFieldSlice:
    """Cell-center field arrays from a 2D RBC simulation snapshot.

    All sequences MUST have identical length (one entry per cell). Empty
    sequences are tolerated — extractors return ``{}`` ("missing" signal).

    Attributes:
        cxs: cell-center x coordinates (m). Range [0, Lx].
        cys: cell-center y coordinates (m). Range [0, Ly].
        t_vals: temperature scalar field (K). Required for Nu extractors.
        u_vecs: velocity vector field as list of (ux, uy, uz) tuples (m/s).
            Required for w_max / roll_count extractors (B.2, B.3). Optional
            for nu_asymmetry (B.1).
    """
    cxs: Sequence[float]
    cys: Sequence[float]
    t_vals: Sequence[float] = field(default_factory=tuple)
    u_vecs: Optional[Sequence[Tuple[float, float, float]]] = None


@dataclass(frozen=True)
class RBCBoundary:
    """Boundary-condition + reference-scale metadata.

    Attributes:
        Lx: cavity x-direction length (m). 4.0 for the canonical AR=4
            benchmark.
        Ly: cavity y-direction length (m). 1.0 (= H) for the canonical
            benchmark (cavity height = reference length).
        H: cavity height = reference length (m). Same as Ly for 2D RBC.
        dT: temperature difference T_hot - T_cold (K). 10.0 K matches
            adapter buoyantFoam settings.
        wall_coord_hot: y coordinate of the bottom hot wall (m). 0.0 for
            canonical RBC.
        wall_coord_cold: y coordinate of the top cold wall (m). Equal to
            Ly for canonical RBC.
        T_hot_wall: bottom hot-wall temperature (K).
        T_cold_wall: top cold-wall temperature (K).
        bc_type: ``'fixedValue'`` or ``'fixedGradient'``. Selects stencil
            mode in ``src.wall_gradient.extract_wall_gradient``.
        bc_gradient: required iff ``bc_type='fixedGradient'``; ignored
            otherwise.
    """
    Lx: float
    Ly: float
    H: float
    dT: float
    wall_coord_hot: float
    wall_coord_cold: float
    T_hot_wall: float
    T_cold_wall: float
    bc_type: str = "fixedValue"
    bc_gradient: Optional[float] = None


# ---------------------------------------------------------------------------
# Internal helpers (mirror dhc_extractors.py)
# ---------------------------------------------------------------------------

def _input_lengths_consistent(*arrays: Optional[Sequence[Any]]) -> bool:
    """Return True iff all non-None inputs have the same length.

    Empty arrays are also rejected — an extractor with no cells to
    operate on returns ``{}`` rather than spurious zero values.
    """
    lens = [len(a) for a in arrays if a is not None]
    if not lens:
        return False
    if any(L == 0 for L in lens):
        return False
    return len(set(lens)) == 1


def _column_gradient_at_horizontal_wall(
    cxs: Sequence[float],
    cys: Sequence[float],
    t_vals: Sequence[float],
    wall_y: float,
    wall_T: float,
    cells_above_wall: bool,
    bc_type: str = "fixedValue",
    bc_gradient: Optional[float] = None,
) -> List[float]:
    """Compute |∂T/∂y| at a horizontal wall (y=wall_y), one value per
    x-column.

    Groups cells by x; within each x-column applies the O(h²) 3-point
    one-sided wall_gradient stencil from src.wall_gradient. Returns the
    list of |grad| values across all x-columns (caller averages).

    Args:
        cells_above_wall: True for the BOTTOM hot wall (y=0; cells at
            y > 0). False for the TOP cold wall (y=Ly; cells at y < Ly).
            For the top-wall case the stencil's contract requires
            cells_above_wall, so we apply a coordinate reflection
            (wall' = -wall, y' = -y) which preserves |∂T/∂y| since
            d/d(-y) = -d/dy and we take the magnitude.

    Returns empty list on input-shape error or insufficient cells per
    column (<2 interior cells).
    """
    if not _input_lengths_consistent(cxs, cys, t_vals):
        return []
    columns: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
    for i in range(len(cxs)):
        columns[round(cxs[i], 4)].append((cys[i], t_vals[i]))
    grads: List[float] = []
    for x_key, pairs in columns.items():
        if len(pairs) < 2:
            continue
        if cells_above_wall:
            wall_for_stencil = wall_y
            coords_for_stencil = [p[0] for p in pairs]
        else:
            # Reflect both wall and coords so cells appear above the
            # virtual wall — gradient magnitude is invariant.
            wall_for_stencil = -wall_y
            coords_for_stencil = [-p[0] for p in pairs]
        try:
            g = extract_wall_gradient(
                wall_coord=wall_for_stencil,
                wall_value=wall_T,
                coords=coords_for_stencil,
                values=[p[1] for p in pairs],
                bc_type=bc_type,
                bc_gradient=bc_gradient,
            )
        except BCContractViolation:
            continue
        grads.append(abs(g))
    return grads


# ---------------------------------------------------------------------------
# Public extractors
# ---------------------------------------------------------------------------

def extract_nu_asymmetry(slice_: RBCFieldSlice, bc: RBCBoundary) -> Dict[str, Any]:
    """Conservation invariant: |Nu_top − Nu_bottom| / |Nu_bottom|.

    Definition (DEC-V61-060 §3 in_scope nusselt_top_asymmetry):
        Nu_bottom = ⟨|∂T/∂y|⟩_x_at_y=0 · H / dT
        Nu_top    = ⟨|∂T/∂y|⟩_x_at_y=Ly · H / dT
        asymmetry = |Nu_top - Nu_bottom| / |Nu_bottom|

    By mass + energy conservation in steady state, Nu_top should equal
    Nu_bottom within numerical noise. Asymmetry above the gate threshold
    (5% per intake §3 tolerance) indicates BL under-resolution or solver
    imbalance.

    Returns dict with:
        - ``value``: asymmetry magnitude (dimensionless, ≥ 0)
        - ``nu_bottom``: Nu_bottom value
        - ``nu_top``: Nu_top value
        - ``column_count_bottom``: number of x-columns contributing to Nu_bottom
        - ``column_count_top``: number of x-columns contributing to Nu_top
        - ``status``: 'ok' on success
    Returns ``{}`` on input-shape error or extraction failure (degrades
    to MISSING_TARGET_QUANTITY at the comparator).
    """
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.t_vals):
        return {}
    if bc.dT == 0:
        return {}

    grads_bottom = _column_gradient_at_horizontal_wall(
        slice_.cxs, slice_.cys, slice_.t_vals,
        wall_y=bc.wall_coord_hot,
        wall_T=bc.T_hot_wall,
        cells_above_wall=True,    # bottom wall: cells are at y > 0
        bc_type=bc.bc_type,
        bc_gradient=bc.bc_gradient,
    )
    grads_top = _column_gradient_at_horizontal_wall(
        slice_.cxs, slice_.cys, slice_.t_vals,
        wall_y=bc.wall_coord_cold,
        wall_T=bc.T_cold_wall,
        cells_above_wall=False,   # top wall: cells are at y < Ly
        bc_type=bc.bc_type,
        bc_gradient=bc.bc_gradient,
    )
    if not grads_bottom or not grads_top:
        return {}

    nu_bottom = (sum(grads_bottom) / len(grads_bottom)) * bc.H / bc.dT
    nu_top = (sum(grads_top) / len(grads_top)) * bc.H / bc.dT
    if nu_bottom == 0:
        return {}
    asymmetry = abs(nu_top - nu_bottom) / abs(nu_bottom)
    return {
        "value": asymmetry,
        "nu_bottom": nu_bottom,
        "nu_top": nu_top,
        "column_count_bottom": len(grads_bottom),
        "column_count_top": len(grads_top),
        "status": "ok",
    }
