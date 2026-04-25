"""DHC multi-dimensional extractors · DEC-V61-057 Batch B.

Pure-helper extractors operating on pre-loaded cell-center field arrays from
a 2D differential-heated-cavity simulation snapshot. Designed for the de Vahl
Davis 1983 benchmark (Ra=1e6, Pr=0.71, AR=1.0).

Each extractor:
  - takes a ``DHCFieldSlice`` + ``DHCBoundary`` pair (pre-loaded cell-center
    fields and BC metadata; see dataclass docstrings),
  - returns ``{value, ...diagnostics}`` so the comparator/UI can decide
    whether to FAIL/PASS/ADVISORY based on SNR per RETRO-V61-050,
  - fails closed (returns ``{}``) on input shape errors instead of raising,
    so an invalid input degrades to MISSING_TARGET_QUANTITY at the gate
    rather than crashing the audit pipeline.

Module is Execution-plane (registered in ``src._plane_assignment``) — it
must not import from ``src.auto_verifier``, ``src.metrics``,
``src.report_engine``, or any other Evaluation-plane module per ADR-001.

This module deliberately re-implements the y-layer grouping logic from
``foam_agent_adapter._extract_nc_nusselt`` rather than calling into the
adapter, because: (a) the adapter method is private to the FoamAgentAdapter
class, (b) DEC-V61-057 §7 batch A.5 froze adapter modifications to
``_generate_natural_convection_cavity`` only, (c) duplication is preferable
to coupling an Execution-plane helper to a class method whose call-site
contract may evolve.
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
class DHCFieldSlice:
    """Cell-center field arrays from a 2D DHC simulation snapshot.

    All sequences MUST have identical length (one entry per cell). Empty
    sequences are tolerated — extractors return ``{}`` ("missing" signal).

    Attributes:
        cxs: cell-center x coordinates (m).
        cys: cell-center y coordinates (m).
        t_vals: temperature scalar field (K). Required for Nu extractors.
        u_vecs: velocity vector field as list of (ux, uy, uz) tuples (m/s).
            Required for u_max / v_max / psi_max extractors. Optional for
            Nu-only extraction.
    """
    cxs: Sequence[float]
    cys: Sequence[float]
    t_vals: Sequence[float] = field(default_factory=tuple)
    u_vecs: Optional[Sequence[Tuple[float, float, float]]] = None


@dataclass(frozen=True)
class DHCBoundary:
    """Boundary-condition + reference-scale metadata for non-dim conversion.

    Attributes:
        L: cavity side length (m). Square cavity assumed (AR=1.0).
        dT: temperature difference T_hot - T_cold (K).
        wall_coord_hot: x coordinate of the hot wall (m). Conventionally 0.0.
        T_hot_wall: hot-wall temperature value (K). For ``fixedValue`` BC.
        bc_type: ``'fixedValue'`` or ``'fixedGradient'``. Selects stencil mode
            in ``src.wall_gradient.extract_wall_gradient``.
        bc_gradient: required iff ``bc_type='fixedGradient'``; ignored
            otherwise.
        alpha: thermal diffusivity α = ν/Pr (m²/s). Default 1.408e-5 matches
            air at ~300 K with the buoyantFoam DHC tutorial settings
            (ν=1e-5, Pr=0.71). Used to non-dim u, v, ψ per de Vahl Davis 1983
            convention (ψ_nondim = ψ_raw / α; u_nondim = u·L/α).
    """
    L: float
    dT: float
    wall_coord_hot: float
    T_hot_wall: float
    bc_type: str
    bc_gradient: Optional[float] = None
    alpha: float = 1.408e-5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _y_layer_resolution(cys: Sequence[float]) -> float:
    """Compute the y-tolerance used for layer grouping.

    Mirrors ``foam_agent_adapter._extract_nc_nusselt`` semantics: pick the
    largest adjacent dy among unique y values (so wall-packed graded meshes
    don't collapse the coarse mid-plane cells), with a 0.6× safety factor.
    Falls back to 0.015 when fewer than 2 distinct y values are present
    (the input is then degenerate; downstream caller will return ``{}``).
    """
    unique_y = sorted({round(y, 6) for y in cys})
    if len(unique_y) < 2:
        return 0.015
    dy_cell = max(unique_y[i + 1] - unique_y[i] for i in range(len(unique_y) - 1))
    return max(0.6 * dy_cell, 1e-6)


def _wall_gradients_per_layer(
    slice_: DHCFieldSlice,
    bc: DHCBoundary,
) -> List[Tuple[float, float]]:
    """Return [(y, |dT/dx|_wall)] one entry per y-layer with ≥2 x-cells.

    Empty list when the input has no cells, no temperature data, or no
    layer with enough x-cells to form a 3-point stencil.
    """
    cxs, cys, t_vals = slice_.cxs, slice_.cys, slice_.t_vals
    if not cxs or not cys or not t_vals:
        return []
    n = min(len(cxs), len(cys), len(t_vals))

    y_layers: Dict[float, Dict[float, List[float]]] = defaultdict(lambda: defaultdict(list))
    for i in range(n):
        y_layers[round(cys[i], 6)][round(cxs[i], 4)].append(t_vals[i])

    out: List[Tuple[float, float]] = []
    for yr, x_groups in y_layers.items():
        x_t_pairs = [(xr, sum(ts) / len(ts)) for xr, ts in sorted(x_groups.items())]
        if len(x_t_pairs) < 2:
            continue
        try:
            grad = extract_wall_gradient(
                wall_coord=float(bc.wall_coord_hot),
                wall_value=float(bc.T_hot_wall),
                coords=[x for x, _ in x_t_pairs],
                values=[T for _, T in x_t_pairs],
                bc_type=bc.bc_type,  # type: ignore[arg-type]
                bc_gradient=bc.bc_gradient,
            )
        except BCContractViolation:
            continue
        out.append((yr, abs(grad)))
    return out


def _interior_layer_stdev(values: Sequence[float], trim_frac: float = 0.10) -> float:
    """Sample stdev of the interior fraction of ``values`` (sorted-tail trim).

    Trims ``trim_frac`` from each end of the sorted sequence to drop the
    near-corner singular layers (Nu spikes at top/bottom corners on the
    hot wall are geometric, not part of the BL physics we want SNR over).
    Returns 0.0 for sequences with fewer than 4 retained samples.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = max(1, int(len(sorted_vals) * trim_frac))
    interior = sorted_vals[k:-k] if len(sorted_vals) > 2 * k else sorted_vals
    n = len(interior)
    if n < 4:
        return 0.0
    mean = sum(interior) / n
    var = sum((v - mean) ** 2 for v in interior) / (n - 1)
    return var ** 0.5


# ---------------------------------------------------------------------------
# B.1 · Nu_max extractor
# ---------------------------------------------------------------------------

def extract_nu_max(slice_: DHCFieldSlice, bc: DHCBoundary) -> Dict[str, Any]:
    """Peak local Nusselt number along the hot wall.

    Mirrors the y-layer wall-gradient computation in
    ``FoamAgentAdapter._extract_nc_nusselt`` but reduces by ``max`` rather
    than ``mean``. Per de Vahl Davis 1983 Table III, gold value at
    Ra=1e6 / Pr=0.71 / AR=1 is ``Nu_max = 17.925`` at ``y/L ≈ 0.0378``.

    Returns
    -------
    dict
        Empty dict on missing inputs (callers should treat as
        MISSING_TARGET_QUANTITY). On success::

            {
              "value": float,            # Nu_max (dimensionless)
              "y_at_max": float,         # y location of max (m)
              "y_at_max_over_L": float,  # normalized y/L
              "num_layers_used": int,    # how many y-layers contributed
              "noise_floor": float,      # interior-layer stdev of Nu_local
              "snr": float | None,       # value / noise_floor (None if floor==0)
              "source": "wall_gradient_stencil_3pt_max",
            }
    """
    if bc.dT == 0.0 or bc.L == 0.0:
        return {}
    pairs = _wall_gradients_per_layer(slice_, bc)
    if not pairs:
        return {}

    # Local Nu_y = |dT/dx|_wall * L / dT
    nu_pairs = [(y, g * bc.L / bc.dT) for (y, g) in pairs]
    y_at_max, nu_max = max(nu_pairs, key=lambda p: p[1])
    nu_values = [n for (_, n) in nu_pairs]
    noise_floor = _interior_layer_stdev(nu_values)
    snr: Optional[float] = (nu_max / noise_floor) if noise_floor > 0.0 else None

    return {
        "value": float(nu_max),
        "y_at_max": float(y_at_max),
        "y_at_max_over_L": float(y_at_max) / float(bc.L),
        "num_layers_used": len(nu_pairs),
        "noise_floor": float(noise_floor),
        "snr": float(snr) if snr is not None else None,
        "source": "wall_gradient_stencil_3pt_max",
    }


# ---------------------------------------------------------------------------
# Stage B.2 / B.3 extractors land in subsequent commits.
# ---------------------------------------------------------------------------
