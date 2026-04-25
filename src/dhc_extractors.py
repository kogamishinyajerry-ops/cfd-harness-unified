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

def _input_lengths_consistent(*arrays: Optional[Sequence[Any]]) -> bool:
    """Return True iff all non-None inputs have identical length.

    DEC-V61-057 Codex round-2 F1-HIGH: previously the extractors silently
    clipped to ``min(len(...))`` and produced apparently-valid measurements
    from corrupt inputs (4-cell coordinate array + 3-cell field would emit
    a benchmark number from 3 cells, hiding the lost cell). Callers MUST
    early-return ``{}`` when this guard returns False so the comparator's
    MISSING_TARGET_QUANTITY path fires instead of a silent truncation.
    """
    lens = [len(a) for a in arrays if a is not None]
    return not lens or all(n == lens[0] for n in lens)


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
    if not _input_lengths_consistent(cxs, cys, t_vals):
        return []
    n = len(cxs)

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


def _interior_profile_spread(values: Sequence[float], trim_frac: float = 0.10) -> float:
    """Sample stdev of the interior fraction of ``values`` (sorted-tail trim).

    DEC-V61-057 Codex round-2 F2-MED rename: previously called
    ``_interior_layer_stdev`` and surfaced as ``noise_floor`` / ``snr``.
    For Nu_max, u_max, v_max the profile spread is mostly *real physics*
    variation (e.g. v_max@y=L/2 is close to 0 in the cavity middle and
    peaks at the rising plume) — labeling it as numerical noise floor was
    misleading. Renamed to ``profile_spread`` and the derived ratio to
    ``peak_to_profile_spread``; both surface as non-gating diagnostics.

    Trims ``trim_frac`` from each end of the sorted sequence to drop the
    near-corner singular samples. Returns 0.0 for fewer than 4 retained.
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
    profile_spread = _interior_profile_spread(nu_values)
    spread_ratio: Optional[float] = (
        nu_max / profile_spread if profile_spread > 0.0 else None
    )

    return {
        "value": float(nu_max),
        "y_at_max": float(y_at_max),
        "y_at_max_over_L": float(y_at_max) / float(bc.L),
        "num_layers_used": len(nu_pairs),
        "profile_spread": float(profile_spread),
        "peak_to_profile_spread": (
            float(spread_ratio) if spread_ratio is not None else None
        ),
        "source": "wall_gradient_stencil_3pt_max",
    }


# ---------------------------------------------------------------------------
# B.2 · u_max + v_max sampleSet extractors
# ---------------------------------------------------------------------------

def _cells_near_coord(
    coords_along: Sequence[float],
    coords_across: Sequence[float],
    components: Sequence[float],
    target_across: float,
    tol: float,
) -> List[Tuple[float, float]]:
    """Return [(coord_along, component)] for cells within ``tol`` of ``target_across``.

    Used to extract a sample line through the cavity at a fixed x or y. The
    "along" direction is the coordinate that varies along the line; the
    "across" direction is the one we constrain. For u_max @ x=L/2, "along" is
    y and "across" is x.

    When multiple cells share the same along-coordinate (a column on a graded
    mesh can have several cells at the same y but different x within tol),
    the across-distance-weighted (1/dx)-weighted mean is used so the closest
    cell to the target plane dominates. This avoids splitting peak near the
    plane when graded meshes pack two cells just to either side of it.
    """
    if not coords_along or not coords_across or not components:
        return []
    n = min(len(coords_along), len(coords_across), len(components))
    raw: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
    for i in range(n):
        d = abs(coords_across[i] - target_across)
        if d <= tol:
            raw[round(coords_along[i], 6)].append((d, components[i]))
    out: List[Tuple[float, float]] = []
    for c_along, dc_pairs in raw.items():
        # Distance-inverse-weighted mean (clip d→0 with floor 1e-12).
        weights = [1.0 / max(d, 1e-12) for d, _ in dc_pairs]
        total_w = sum(weights)
        if total_w == 0.0:
            continue
        v = sum(w * c for w, (_, c) in zip(weights, dc_pairs)) / total_w
        out.append((c_along, v))
    out.sort(key=lambda p: p[0])
    return out


def _across_tolerance(coords: Sequence[float]) -> float:
    """Mid-plane cell-pick tolerance: 0.6× the largest adjacent gap among unique
    coordinates, with a 1e-6 floor. Mirrors ``_y_layer_resolution`` semantics
    so wall-packed graded meshes still find the coarse mid-plane cells.
    """
    unique = sorted({round(c, 6) for c in coords})
    if len(unique) < 2:
        return 0.015
    gap = max(unique[i + 1] - unique[i] for i in range(len(unique) - 1))
    return max(0.6 * gap, 1e-6)


def extract_u_max_vertical(slice_: DHCFieldSlice, bc: DHCBoundary) -> Dict[str, Any]:
    """Peak |u_x| sampled along the x=L/2 vertical mid-plane.

    Returns the nondim value u_nondim = max|u_x| · L / α per de Vahl Davis
    1983 Table II convention. Gold value at Ra=1e6: u_nondim = 64.63 at
    y/L ≈ 0.85 (top half of cavity, returning flow).

    Returns {} when ``u_vecs`` is missing or no cells fall within tolerance
    of the vertical mid-plane.
    """
    if slice_.u_vecs is None or not slice_.cxs or not slice_.cys:
        return {}
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.u_vecs):
        return {}
    if bc.alpha == 0.0 or bc.L == 0.0:
        return {}
    # u_x is the first component of each velocity tuple.
    ux = [v[0] for v in slice_.u_vecs]
    target_x = 0.5 * bc.L
    tol_x = _across_tolerance(slice_.cxs)
    samples = _cells_near_coord(
        coords_along=slice_.cys,
        coords_across=slice_.cxs,
        components=ux,
        target_across=target_x,
        tol=tol_x,
    )
    if not samples:
        return {}

    abs_pairs = [(y, abs(u)) for (y, u) in samples]
    y_at_max, u_max_abs = max(abs_pairs, key=lambda p: p[1])
    u_nondim = u_max_abs * bc.L / bc.alpha
    nondim_values = [a * bc.L / bc.alpha for (_, a) in abs_pairs]
    profile_spread = _interior_profile_spread(nondim_values)
    spread_ratio: Optional[float] = (
        u_nondim / profile_spread if profile_spread > 0.0 else None
    )

    return {
        "value": float(u_nondim),
        "value_raw": float(u_max_abs),
        "y_at_max": float(y_at_max),
        "y_at_max_over_L": float(y_at_max) / float(bc.L),
        "num_samples_used": len(samples),
        "across_tolerance": float(tol_x),
        "profile_spread": float(profile_spread),
        "peak_to_profile_spread": (
            float(spread_ratio) if spread_ratio is not None else None
        ),
        "source": "vertical_midplane_sample_max_abs",
    }


def extract_v_max_horizontal(slice_: DHCFieldSlice, bc: DHCBoundary) -> Dict[str, Any]:
    """Peak |u_y| sampled along the y=L/2 horizontal mid-plane.

    Returns the nondim value v_nondim = max|u_y| · L / α per de Vahl Davis
    1983 Table II convention. Gold value at Ra=1e6: v_nondim = 219.36 at
    x/L ≈ 0.038 (close to the hot wall, where the rising plume peaks).

    Returns {} when ``u_vecs`` is missing or no cells fall within tolerance
    of the horizontal mid-plane.
    """
    if slice_.u_vecs is None or not slice_.cxs or not slice_.cys:
        return {}
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.u_vecs):
        return {}
    if bc.alpha == 0.0 or bc.L == 0.0:
        return {}
    # u_y is the second component of each velocity tuple.
    uy = [v[1] for v in slice_.u_vecs]
    target_y = 0.5 * bc.L
    tol_y = _across_tolerance(slice_.cys)
    samples = _cells_near_coord(
        coords_along=slice_.cxs,
        coords_across=slice_.cys,
        components=uy,
        target_across=target_y,
        tol=tol_y,
    )
    if not samples:
        return {}

    abs_pairs = [(x, abs(v)) for (x, v) in samples]
    x_at_max, v_max_abs = max(abs_pairs, key=lambda p: p[1])
    v_nondim = v_max_abs * bc.L / bc.alpha
    nondim_values = [a * bc.L / bc.alpha for (_, a) in abs_pairs]
    profile_spread = _interior_profile_spread(nondim_values)
    spread_ratio: Optional[float] = (
        v_nondim / profile_spread if profile_spread > 0.0 else None
    )

    return {
        "value": float(v_nondim),
        "value_raw": float(v_max_abs),
        "x_at_max": float(x_at_max),
        "x_at_max_over_L": float(x_at_max) / float(bc.L),
        "num_samples_used": len(samples),
        "across_tolerance": float(tol_y),
        "profile_spread": float(profile_spread),
        "peak_to_profile_spread": (
            float(spread_ratio) if spread_ratio is not None else None
        ),
        "source": "horizontal_midplane_sample_max_abs",
    }


# ---------------------------------------------------------------------------
# B.3 · ψ_max trapezoidal reconstruction (PROVISIONAL_ADVISORY status)
# ---------------------------------------------------------------------------

# Gold reference for closure-residual SNR check (de Vahl Davis 1983 Table I).
# Used to express the cumulative trapezoidal closure error as a fraction of
# the expected peak. If the fraction exceeds 1 % the extractor demotes the
# result to PROVISIONAL_ADVISORY per RETRO-V61-050 / DEC-V61-057 §B.3.
PSI_MAX_GOLD_NONDIM = 16.750
PSI_CLOSURE_FRACTION_THRESHOLD = 0.01


def extract_psi_max(slice_: DHCFieldSlice, bc: DHCBoundary) -> Dict[str, Any]:
    """Reconstruct stream function via trapezoidal ∫ u_x dy and return peak.

    Per the standard 2-D incompressible definition, ψ satisfies ∂ψ/∂y = u_x
    and ∂ψ/∂x = -u_y. Integrating u_x along y at fixed x with ψ(y=0)=0 (no
    through-flow at the bottom wall) yields ψ(x, y). Cumulative trapezoidal
    rule is used because the input is cell-center field data (uniform or
    graded mesh tolerated).

    Top-wall closure
    ----------------
    Re-integrating to y=L with the no-slip BC u_x(y=L)=0 gives ψ(x, L). For
    a strictly incompressible discrete solution this equals 0; the residual
    is the SNR floor for ψ_max. If the worst-column closure residual (when
    expressed as a fraction of ``PSI_MAX_GOLD_NONDIM``) exceeds
    ``PSI_CLOSURE_FRACTION_THRESHOLD`` the extractor labels the value
    PROVISIONAL_ADVISORY and Stage C comparator does not hard-gate on it.

    Returns
    -------
    dict
        Empty when ``u_vecs`` missing or no x-column has ≥2 cells. Otherwise::

            {
              "value": float,                   # ψ_max nondim (ψ_raw / α)
              "value_raw": float,               # ψ_max raw (m²/s)
              "x_at_max": float, "y_at_max": float,
              "x_at_max_over_L": float, "y_at_max_over_L": float,
              "num_columns_used": int,
              "closure_residual_max_nondim": float,
              "closure_fraction_of_gold": float,
              "advisory_status": "HARD_GATED" | "PROVISIONAL_ADVISORY",
              "snr_pass": bool,
              "source": "trapezoidal_y_integration_of_ux",
            }
    """
    if slice_.u_vecs is None or not slice_.cxs or not slice_.cys:
        return {}
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.u_vecs):
        return {}
    if bc.alpha == 0.0 or bc.L == 0.0:
        return {}
    n = len(slice_.cxs)
    if n == 0:
        return {}

    # Group cells by x-column. Sister cells at the same x but slightly
    # different rounding land on the same key thanks to the 6-decimal round.
    cells_by_x: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
    for i in range(n):
        cells_by_x[round(slice_.cxs[i], 6)].append(
            (slice_.cys[i], slice_.u_vecs[i][0])
        )

    psi_max_abs = 0.0
    psi_max_x = 0.0
    psi_max_y = 0.0
    closure_residuals: List[float] = []
    columns_used = 0

    for xc, y_u_pairs in cells_by_x.items():
        y_u_pairs.sort(key=lambda p: p[0])
        if len(y_u_pairs) < 2:
            continue
        # Trapezoidal cumulative integral starting from ψ(y=0)=0 with the
        # no-slip BC u_x(y=0)=0 implicit in y_prev=0, u_prev=0.
        psi = 0.0
        y_prev = 0.0
        u_prev = 0.0
        for (y_k, u_k) in y_u_pairs:
            psi += 0.5 * (u_prev + u_k) * (y_k - y_prev)
            y_prev = y_k
            u_prev = u_k
            if abs(psi) > psi_max_abs:
                psi_max_abs = abs(psi)
                psi_max_x = xc
                psi_max_y = y_k
        # Close to top wall using the no-slip BC u_x(y=L)=0.
        psi += 0.5 * (u_prev + 0.0) * (bc.L - y_prev)
        closure_residuals.append(abs(psi))
        columns_used += 1

    if columns_used == 0 or psi_max_abs == 0.0:
        return {}

    psi_nondim = psi_max_abs / bc.alpha
    closure_max_raw = max(closure_residuals)
    closure_max_nondim = closure_max_raw / bc.alpha
    closure_fraction = closure_max_nondim / PSI_MAX_GOLD_NONDIM
    snr_pass = closure_fraction < PSI_CLOSURE_FRACTION_THRESHOLD
    status = "HARD_GATED" if snr_pass else "PROVISIONAL_ADVISORY"

    return {
        "value": float(psi_nondim),
        "value_raw": float(psi_max_abs),
        "x_at_max": float(psi_max_x),
        "y_at_max": float(psi_max_y),
        "x_at_max_over_L": float(psi_max_x) / float(bc.L),
        "y_at_max_over_L": float(psi_max_y) / float(bc.L),
        "num_columns_used": int(columns_used),
        "closure_residual_max_nondim": float(closure_max_nondim),
        "closure_fraction_of_gold": float(closure_fraction),
        "advisory_status": status,
        "snr_pass": bool(snr_pass),
        "source": "trapezoidal_y_integration_of_ux",
    }
