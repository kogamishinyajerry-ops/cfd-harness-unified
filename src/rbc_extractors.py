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

Stage B ships three public extractors:
  - ``extract_nu_asymmetry`` (B.1, NON_TYPE_HARD_INVARIANT): conservation
    invariant |Nu_top − Nu_bottom| / |Nu_bottom|; FAIL when > 0.05.
  - ``extract_w_max`` (B.2, PROVISIONAL_ADVISORY): peak |u_y| in cavity
    interior, nondim by free-fall velocity sqrt(g·β·ΔT·H).
  - ``extract_roll_count_x`` (B.3, PROVISIONAL_ADVISORY): counter-rotating
    roll count via mid-cavity u_y sign-change analysis.

DEC-V61-060 R3+R4 fail-closed contract: every extractor returns ``{}``
on shape error, malformed u_vecs (arity), or non-finite (NaN/Inf)
inputs in field arrays or in the BOUNDARY METADATA THAT THE EXTRACTOR
ACTUALLY CONSUMES — NOT every field on RBCBoundary. Per Codex R5
F1-LOW: each extractor validates only the bc.* scalars it reads, so
e.g. extract_nu_asymmetry tolerates NaN in bc.g (not consumed), while
extract_w_max rejects it. If a future extractor consumes a new bc.*
field, it MUST add the corresponding _is_finite guard.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.wall_gradient import BCContractViolation, extract_wall_gradient


# ---------------------------------------------------------------------------
# DEC-V61-060 Stage B-final fix (Codex R3 F1-HIGH): non-finite + arity guard
# ---------------------------------------------------------------------------

def _is_finite(value: Any) -> bool:
    """True iff value is a finite real number. Rejects NaN, ±Inf, None,
    str, complex, etc. Used as a fail-closed gate before computation."""
    return isinstance(value, (int, float)) and math.isfinite(value)


def _all_finite(seq: Sequence[Any]) -> bool:
    """True iff every element of seq is a finite real number."""
    for v in seq:
        if not _is_finite(v):
            return False
    return True


def _u_vecs_well_formed(u_vecs: Sequence[Any]) -> bool:
    """True iff every entry is a tuple/list of length ≥2 with a finite
    u_y at index 1.

    DEC-V61-060 R3 F1-HIGH: extract_w_max and extract_roll_count_x
    used to index ``u_vecs[i][1]`` blindly, raising IndexError on
    malformed inputs. This guard fails-closed instead.

    NOTE: only u_y (index 1) is currently consumed; u_x and u_z (if
    present) are not validated. Callers must NOT add extractors that
    consume u_x or u_z without extending this guard.
    """
    for v in u_vecs:
        if not (isinstance(v, (tuple, list)) and len(v) >= 2):
            return False
        if not _is_finite(v[1]):
            return False
    return True


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
        g: gravity magnitude (m/s²). Optional[float] = None — REQUIRED
            for B.2 extract_w_max (computes free-fall velocity
            U_ff = sqrt(g·β·dT·H)). Per DEC-V61-060 R3 F2-MED, no
            default is supplied (would silently bake the canonical
            AR=4 / Pr=10 case at 3.0e-4 m/s²); Stage C wiring MUST
            plumb case-derived gravity or extract_w_max fails-closed.
            extract_nu_asymmetry does NOT use g and runs without it.
        beta: thermal expansion coefficient (1/K). Optional[float] = None
            with the same contract as `g` — required for w_max,
            unused by nu_asymmetry. Canonical Boussinesq value at
            T_mean ≈ 300 K is 1/300 ≈ 0.00333.
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
    # DEC-V61-060 Stage B-final fix (Codex R3 F2-MED): `g` and `beta` were
    # previously defaulted to canonical AR=4 / Pr=10 values (3.0e-4 and
    # 1/300). That silently baked the current case into the contract —
    # Stage C wiring could omit case-derived gravity and still get a
    # plausible-looking w_max_nondim. Removing the defaults forces every
    # caller to plumb case-derived physics or fail-closed.
    g: Optional[float] = None
    beta: Optional[float] = None


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
    # DEC-V61-060 R3+R4 F1-HIGH: fail-closed on non-finite inputs.
    # R3 covered cxs/cys/t_vals + bc.dT/H. R4 added: bc.wall_coord_hot/cold,
    # bc.T_hot_wall/T_cold_wall, and bc.bc_gradient (when fixedGradient).
    if not (_all_finite(slice_.cxs) and _all_finite(slice_.cys) and _all_finite(slice_.t_vals)):
        return {}
    if not _is_finite(bc.dT) or bc.dT == 0:
        return {}
    if not _is_finite(bc.H):
        return {}
    if not (_is_finite(bc.wall_coord_hot) and _is_finite(bc.wall_coord_cold)
            and _is_finite(bc.T_hot_wall) and _is_finite(bc.T_cold_wall)):
        return {}
    if bc.bc_type == "fixedGradient" and not _is_finite(bc.bc_gradient):
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
    # DEC-V61-060 R4 F1-HIGH defense-in-depth: even with all inputs finite,
    # degenerate gradient computations can theoretically produce NaN/Inf.
    # Reject any non-finite final result rather than emit status=ok+nan.
    if not (_is_finite(nu_bottom) and _is_finite(nu_top) and _is_finite(asymmetry)):
        return {}
    return {
        "value": asymmetry,
        "nu_bottom": nu_bottom,
        "nu_top": nu_top,
        "column_count_bottom": len(grads_bottom),
        "column_count_top": len(grads_top),
        "status": "ok",
    }


def extract_w_max(slice_: RBCFieldSlice, bc: RBCBoundary) -> Dict[str, Any]:
    """Peak vertical velocity nondim by free-fall velocity (B.2).

    Definition (DEC-V61-060 §3 in_scope w_max_nondim):
        U_ff = sqrt(g · β · dT · H)
        raw_w_max = max |u_y| over interior cells (excluding wall layers
                    to avoid the no-slip-zero contribution polluting the max)
        w_max_nondim = raw_w_max / U_ff

    Per intake A.0 BRANCH-B, w_max_nondim ref_value =
    "ADVISORY_NO_LITERATURE_LOCATOR" — comparator surfaces but does NOT
    enforce. This extractor still computes the value; the gate_status
    is PROVISIONAL_ADVISORY.

    "Interior" excludes cells within H/20 of either horizontal wall to
    avoid biasing the max by no-slip-zero values. Pandey & Schumacher
    Fig 4 shows peak |u_y| occurring well inside the cavity, not at the
    wall, so this trim is benign.

    Returns dict with:
        - ``value``: w_max_nondim (raw / U_ff)
        - ``raw_w_max``: max |u_y| in interior cells (m/s)
        - ``U_ff``: free-fall velocity (m/s)
        - ``interior_cell_count``: number of cells contributing to the max
        - ``status``: 'ok' on success
    Returns ``{}`` on missing u_vecs / shape error / U_ff = 0.
    """
    if slice_.u_vecs is None:
        return {}
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.u_vecs):
        return {}
    # DEC-V61-060 R3 F1-HIGH: arity + non-finite guards
    if not _u_vecs_well_formed(slice_.u_vecs):
        return {}
    if not (_all_finite(slice_.cxs) and _all_finite(slice_.cys)):
        return {}
    # DEC-V61-060 R3 F2-MED: g/beta now Optional[float]; fail-closed when
    # caller forgot to plumb case-derived physics.
    # R4 F1-HIGH: also validate wall_coord_hot/cold (used by interior trim).
    if not (_is_finite(bc.g) and _is_finite(bc.beta)
            and _is_finite(bc.dT) and _is_finite(bc.H)):
        return {}
    if not (_is_finite(bc.wall_coord_hot) and _is_finite(bc.wall_coord_cold)):
        return {}
    U_ff_sq = bc.g * bc.beta * bc.dT * bc.H
    if U_ff_sq <= 0:
        return {}
    U_ff = U_ff_sq ** 0.5
    if U_ff == 0:
        return {}
    # Trim no-slip wall layer (H/20 from y=0 and y=Ly) to avoid the
    # max being pinned by the literal zero of the no-slip BC.
    trim = bc.H / 20.0
    raw_w_max = 0.0
    counted = 0
    for i in range(len(slice_.cxs)):
        y = slice_.cys[i]
        if y < bc.wall_coord_hot + trim:
            continue
        if y > bc.wall_coord_cold - trim:
            continue
        u_y = slice_.u_vecs[i][1]  # (ux, uy, uz) tuple — index 1 is u_y
        au = abs(u_y)
        if au > raw_w_max:
            raw_w_max = au
        counted += 1
    if counted == 0:
        return {}
    return {
        "value": raw_w_max / U_ff,
        "raw_w_max": raw_w_max,
        "U_ff": U_ff,
        "interior_cell_count": counted,
        "status": "ok",
    }


def extract_roll_count_x(slice_: RBCFieldSlice, bc: RBCBoundary) -> Dict[str, Any]:
    """Count counter-rotating rolls along x via u_y sign changes at
    mid-cavity (y ≈ H/2) (B.3).

    Definition (DEC-V61-060 §3 in_scope roll_count_x):
        Sample u_y at the y-layer closest to H/2; sort by x; count the
        number of times u_y crosses zero (with a noise floor of
        max(0.10·|u_y|_peak, 1e-9) to reject side-wall noise per intake
        atomicity_guard).
        roll_count = (sign_changes // 2) + 1 — for the canonical AR=4
        2-roll case, u_y(x) at mid-cavity is + (rising plume left roll)
        → 0 → − (descending plume between rolls) → 0 → + (rising plume
        right roll), giving 2 sign changes → 2 rolls.

    Per intake A.0, ref_value=2 (canonical AR=4 2-roll structure per
    Pandey & Schumacher Fig 4b + Fig 5). gate_status PROVISIONAL_ADVISORY
    because steady SIMPLE can land in metastable basins (1, 2, or 3
    rolls of unequal width) and the count is sensitive to IC.

    Returns dict with:
        - ``value``: roll count (integer ≥ 0)
        - ``sign_changes``: number of u_y zero crossings detected
        - ``y_layer_used``: actual y of the sampling layer
        - ``noise_floor``: threshold used for sign-change detection
        - ``cell_count``: number of x-samples
        - ``status``: 'ok' on success
    Returns ``{}`` on missing u_vecs / shape error / empty mid-layer.
    """
    if slice_.u_vecs is None:
        return {}
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.u_vecs):
        return {}
    # DEC-V61-060 R3 F1-HIGH: arity + non-finite guards
    if not _u_vecs_well_formed(slice_.u_vecs):
        return {}
    if not (_all_finite(slice_.cxs) and _all_finite(slice_.cys)):
        return {}
    if not (_is_finite(bc.wall_coord_hot) and _is_finite(bc.wall_coord_cold)
            and _is_finite(bc.Lx)):
        return {}
    y_target = 0.5 * (bc.wall_coord_hot + bc.wall_coord_cold)
    # Find the y-layer closest to mid-cavity
    unique_y = sorted({round(y, 6) for y in slice_.cys})
    if not unique_y:
        return {}
    y_layer = min(unique_y, key=lambda y: abs(y - y_target))
    y_tol = (
        0.6 * max(unique_y[i + 1] - unique_y[i] for i in range(len(unique_y) - 1))
        if len(unique_y) >= 2 else 1e-3
    )
    samples: List[Tuple[float, float]] = []
    for i in range(len(slice_.cxs)):
        if abs(slice_.cys[i] - y_layer) <= y_tol:
            samples.append((slice_.cxs[i], slice_.u_vecs[i][1]))
    if len(samples) < 3:
        return {}
    samples.sort(key=lambda s: s[0])
    # Reject side-wall noise: ignore samples within 5% of either side wall
    side_trim = 0.05 * bc.Lx
    interior = [(x, u) for x, u in samples if side_trim < x < bc.Lx - side_trim]
    if len(interior) < 3:
        return {}
    u_peak = max(abs(u) for _, u in interior)
    noise_floor = max(0.10 * u_peak, 1e-9)

    sign_changes = 0
    prev_sign = 0  # 0 = below noise floor (treat as zero)
    for _, u in interior:
        if abs(u) < noise_floor:
            cur_sign = 0
        else:
            cur_sign = 1 if u > 0 else -1
        if prev_sign != 0 and cur_sign != 0 and cur_sign != prev_sign:
            sign_changes += 1
        if cur_sign != 0:
            prev_sign = cur_sign
    # Roll count from sign changes (mid-height u_y signature):
    #   N=0 → 1 roll  (degenerate single vortex / no rotation detected)
    #   N=1 → 1 roll  (one pair of opposite-sign zones, single asymmetric roll)
    #   N=2 → 2 rolls (canonical 2-roll: + − + with descending plume at center)
    #   N=4 → 3 rolls
    # Formula: (N // 2) + 1; N=0 special-cased to 1.
    if sign_changes == 0:
        roll_count = 1
    else:
        roll_count = (sign_changes // 2) + 1
    return {
        "value": roll_count,
        "sign_changes": sign_changes,
        "y_layer_used": y_layer,
        "noise_floor": noise_floor,
        "cell_count": len(interior),
        "status": "ok",
    }
