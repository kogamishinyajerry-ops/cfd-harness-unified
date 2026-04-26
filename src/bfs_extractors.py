"""BFS Type II secondary observable extractors (DEC-V61-067 A.1).

Provides 3 functions that operate on pre-aggregated OpenFOAM data the
adapter has already gathered (face-centre tau_x, cell-centre p / U) and
produce the secondary observables that the V61-067 Type II contract
gates require:

    extract_pressure_recovery(p_inlet, p_outlet, U_bulk, rho, p_ref)
        → {"inlet": Cp_inlet, "outlet": Cp_outlet, "delta": ΔCp}
    extract_velocity_profile_at_x(cells, x_target, y_targets, U_bulk, H)
        → list[{"x_H": .., "y_H": .., "u_Ubulk": ..}]
    extract_cd_mean(tau_x_floor_data, U_bulk, rho)
        → mean |Cf| over the downstream floor

Reference: Le, Moin & Kim 1997 (DNS at Re_H=5100); Driver & Seegmiller
1985 (experiment at Re_H≈37500); blended Xr/H=6.26 anchor at the
adapter's Re_H=7600 transitional/turbulent plateau (DEC-V61-046).

Caller responsibility: the adapter at
``foam_agent_adapter.py`` BFS dispatch site is the only intended caller.
It performs pre-aggregation (inlet/outlet face averaging, x-column
snapping, downstream-floor filtering) and hands the per-quantity
inputs to these functions. This module does NOT touch OpenFOAM IO.

Plane assignment: src/_plane_assignment.py marks this module as
``Plane.EXECUTION`` (peers: ``flat_plate_extractors``,
``duct_flow_extractors``, ``airfoil_extractors``, ``dhc_extractors``).

V61-066 lessons applied:
  - Conservative input validation per V61-063 R2 F4 + V61-066 A.1 patterns
  - Each extractor accepts pre-aggregated scalars or simple lists; the
    adapter retains responsibility for cell-vs-face data wrangling
  - cd_mean is intentionally minimal (mean |Cf|) to avoid the partial-
    tautology with reattachment_length flagged in the intake §3
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple


# ============================================================================
# Constants — Le/Moin/Kim 1997 + Driver 1985 anchors at Re_H=7600
# ============================================================================

LE_MOIN_KIM_1997_XR_OVER_H_AT_RE_5100: float = 6.28
"""Le, Moin & Kim 1997 DNS reattachment length at Re_H=5100, ER=1.2."""

DRIVER_SEEGMILLER_1985_XR_OVER_H_AT_RE_37500: float = 6.26
"""Driver & Seegmiller 1985 experimental reattachment length at Re_H≈37500."""

LE_MOIN_KIM_1997_CP_INLET: float = -0.90
"""Le/Moin/Kim 1997 Cp at inlet (x/H ≈ -10), reference convention from
their Fig. 4. This is the canonical anchor value used in the gold YAML."""

LE_MOIN_KIM_1997_CP_OUTLET: float = 0.10
"""Le/Moin/Kim 1997 Cp at outlet (x/H ≈ 30)."""

LE_MOIN_KIM_1997_CP_DELTA: float = 1.00
"""Le/Moin/Kim 1997 streamwise pressure rise: Cp_outlet - Cp_inlet."""


# ============================================================================
# Errors + result containers
# ============================================================================

class BfsExtractorError(ValueError):
    """Raised on any degenerate input to a BFS extractor.

    Inherits ValueError so existing code that catches ValueError to fold
    into ``bfs_*_error`` audit keys keeps working without needing a new
    except clause.
    """


# ============================================================================
# Internal validation helpers
# ============================================================================

def _validate_positive(name: str, value: float) -> float:
    """Validate ``value`` is finite + > 0; raise on degenerate input."""
    if not isinstance(value, (int, float)):
        raise BfsExtractorError(
            f"{name} must be a real number, got {type(value).__name__}: {value!r}"
        )
    v = float(value)
    if not math.isfinite(v):
        raise BfsExtractorError(f"{name} must be finite, got {v}")
    if v <= 0.0:
        raise BfsExtractorError(f"{name} must be > 0, got {v}")
    return v


def _validate_finite(name: str, value: float) -> float:
    """Validate ``value`` is finite (any sign); raise on NaN/Inf."""
    if not isinstance(value, (int, float)):
        raise BfsExtractorError(
            f"{name} must be a real number, got {type(value).__name__}: {value!r}"
        )
    v = float(value)
    if not math.isfinite(v):
        raise BfsExtractorError(f"{name} must be finite, got {v}")
    return v


# ============================================================================
# Public extraction functions
# ============================================================================

def extract_pressure_recovery(
    p_inlet: float,
    p_outlet: float,
    U_bulk: float,
    rho: float = 1.0,
    p_ref: float = 0.0,
) -> Dict[str, float]:
    """Compute Cp at inlet/outlet plus the streamwise pressure rise.

    Cp(x) = (p(x) - p_ref) / (0.5·ρ·U_bulk²)

    Args:
        p_inlet: area-averaged static pressure at the inlet face
            (x/H ≈ -10 in Le/Moin/Kim convention). Caller must
            pre-aggregate cell-centre data into a single scalar.
        p_outlet: area-averaged static pressure at the outlet face
            (x/H ≈ 30).
        U_bulk: bulk velocity for normalization. Must be > 0.
        rho: fluid density. Defaults to 1.0 for normalized adapter runs.
        p_ref: reference pressure for Cp normalization. Defaults to 0.0
            (consistent with OpenFOAM's kinematic-pressure incompressible
            convention where outlet zeroGradient typically anchors p ≈ 0).

    Returns:
        Dict with keys "inlet" (Cp_inlet), "outlet" (Cp_outlet), and
        "delta" (Cp_outlet - Cp_inlet). Le/Moin/Kim 1997 anchor at
        Re_H=5100: {-0.90, 0.10, 1.00}.

    Raises:
        BfsExtractorError: if U_bulk or rho is non-positive / non-finite,
            or if p_inlet / p_outlet / p_ref is non-finite.
    """
    p_inlet = _validate_finite("p_inlet", p_inlet)
    p_outlet = _validate_finite("p_outlet", p_outlet)
    p_ref = _validate_finite("p_ref", p_ref)
    U_bulk = _validate_positive("U_bulk", U_bulk)
    rho = _validate_positive("rho", rho)

    norm = 0.5 * rho * U_bulk ** 2
    cp_inlet = (p_inlet - p_ref) / norm
    cp_outlet = (p_outlet - p_ref) / norm
    return {
        "inlet": cp_inlet,
        "outlet": cp_outlet,
        "delta": cp_outlet - cp_inlet,
    }


def extract_velocity_profile_at_x(
    cells: Sequence[Tuple[float, float, float]],
    x_target_physical: float,
    y_targets_physical: Sequence[float],
    U_bulk: float,
    step_height: float = 1.0,
    x_tol: float = 0.0,
    y_target_max_distance: float = 0.0,
) -> List[Dict[str, float]]:
    """Sample u_x at (x_target, y_targets) and return gold-YAML-shape dicts.

    For each y_target, find the cell at (x ≈ x_target, y = nearest cell
    centre to y_target) and return u_x normalized by U_bulk. Output
    keys match the gold YAML schema exactly: {"x_H", "y_H", "u_Ubulk"}.

    DEC-V61-067 R1 F#2 conservative validation:
      - Every cells entry validated as (x, y, u_x) of finite floats;
        BfsExtractorError raised on malformed tuples or non-finite data.
      - Each y_target requires a nearest cell within
        ``y_target_max_distance``; if the nearest cell is farther,
        BfsExtractorError raised (prevents 1-cell column from
        fabricating a 3-point profile).
      - Tie-break is explicit: when two cells are equidistant from a
        y_target, the LOWER-y cell wins (sort key (|Δy|, y)).

    Args:
        cells: list of (cx, cy, u_x) tuples in PHYSICAL units. Each
            tuple must have exactly 3 numeric finite entries; otherwise
            BfsExtractorError raised. The adapter should pre-filter to
            a band near x_target if needed (or pass all cells and let
            this function snap to the single nearest x column — V61-066
            post-R3 #1 lesson).
        x_target_physical: target x position (m). For BFS at Re_H=7600
            with H=1, the canonical near-reattachment station is x = 6.0.
        y_targets_physical: list of target y positions (m). For BFS,
            canonical {0.5, 1.0, 2.0} step-heights.
        U_bulk: bulk velocity for u_x normalization. Must be > 0.
        step_height: step height H, used to convert physical x/y back
            to gold-YAML normalized x/H, y/H. Defaults to 1.0.
        x_tol: tolerance for the x-column snap. If 0.0 (default), this
            function snaps to the SINGLE nearest unique x column to
            avoid x-tol-aliasing duplicates (V61-066 R1 post-R3 #1
            precedent). If > 0, picks all cells within ±x_tol.
        y_target_max_distance: maximum admissible distance |cy - y_target|
            in physical units. If 0.0 (default), no coverage guard
            (legacy behaviour for unit tests that don't gate on coverage).
            If > 0, any y_target whose nearest column cell exceeds this
            distance triggers BfsExtractorError. Adapter passes 0.4·H
            for V61-067 BFS to fail-close on undersampled columns.

    Returns:
        List of dicts, one per y_target, with keys "x_H", "y_H",
        "u_Ubulk". Order matches y_targets_physical input order.
        Le/Moin/Kim 1997 anchor at x/H=6: [(0.5, 0.40), (1.0, 0.85),
        (2.0, 1.05)].

    Raises:
        BfsExtractorError: if cells is empty, malformed, contains
            non-finite values, U_bulk/step_height non-positive, no cells
            within the x-target band, or any y_target has no cell within
            y_target_max_distance.
    """
    if not cells:
        raise BfsExtractorError("cells is empty")
    U_bulk = _validate_positive("U_bulk", U_bulk)
    step_height = _validate_positive("step_height", step_height)
    x_target_physical = _validate_finite("x_target_physical", x_target_physical)
    if not y_targets_physical:
        raise BfsExtractorError("y_targets_physical is empty")
    if y_target_max_distance != 0.0:
        y_target_max_distance = _validate_positive(
            "y_target_max_distance", y_target_max_distance,
        )

    # DEC-V61-067 R1 F#2: validate every cells entry up front.
    # Wrap float() in try/except so non-numeric types raise the typed
    # BfsExtractorError, not a raw ValueError leak.
    validated_cells: List[Tuple[float, float, float]] = []
    for idx, entry in enumerate(cells):
        if not isinstance(entry, (tuple, list)) or len(entry) != 3:
            raise BfsExtractorError(
                f"cells[{idx}] must be a (cx, cy, u_x) 3-tuple, got {entry!r}"
            )
        try:
            cx_raw = float(entry[0])
            cy_raw = float(entry[1])
            ux_raw = float(entry[2])
        except (TypeError, ValueError) as exc:
            raise BfsExtractorError(
                f"cells[{idx}] contains non-numeric data: {entry!r} ({exc})"
            ) from exc
        cx_v = _validate_finite(f"cells[{idx}].cx", cx_raw)
        cy_v = _validate_finite(f"cells[{idx}].cy", cy_raw)
        ux_v = _validate_finite(f"cells[{idx}].u_x", ux_raw)
        validated_cells.append((cx_v, cy_v, ux_v))

    # V61-066 post-R3 #1 lesson: snap to single nearest unique x column
    # to avoid duplicate-column aliasing.
    if x_tol == 0.0:
        unique_x = sorted({round(c[0], 6) for c in validated_cells})
        if not unique_x:
            raise BfsExtractorError("no x-coordinates in cells")
        x_chosen = min(unique_x, key=lambda x: abs(x - x_target_physical))
        column = [
            (cx, cy, ux)
            for cx, cy, ux in validated_cells
            if abs(round(cx, 6) - x_chosen) < 1e-6
        ]
    else:
        x_tol = _validate_positive("x_tol", x_tol)
        column = [
            (cx, cy, ux)
            for cx, cy, ux in validated_cells
            if abs(cx - x_target_physical) <= x_tol
        ]

    if not column:
        raise BfsExtractorError(
            f"no cells found near x_target={x_target_physical} "
            f"(unique x values: {sorted({c[0] for c in validated_cells})[:5]}...)"
        )

    out: List[Dict[str, float]] = []
    x_H_actual = column[0][0] / step_height  # all column cells share x
    for y_target in y_targets_physical:
        y_target_v = _validate_finite("y_target", y_target)
        # DEC-V61-067 R1 F#2 explicit tie-break: sort key (|Δy|, y) so
        # equidistant cells resolve deterministically by lower-y wins.
        nearest = min(
            column,
            key=lambda cell: (abs(cell[1] - y_target_v), cell[1]),
        )
        nearest_distance = abs(nearest[1] - y_target_v)
        # DEC-V61-067 R1 F#2 coverage guard: reject undersampled columns.
        if (y_target_max_distance > 0.0
                and nearest_distance > y_target_max_distance):
            raise BfsExtractorError(
                f"no cell within y_target_max_distance={y_target_max_distance} "
                f"of y_target={y_target_v}; nearest cell at y={nearest[1]} "
                f"(distance {nearest_distance})"
            )
        out.append({
            "x_H": x_H_actual,
            "y_H": nearest[1] / step_height,
            "u_Ubulk": nearest[2] / U_bulk,
        })
    return out


def extract_cd_mean(
    tau_x_floor_data: Sequence[Tuple[float, float]],
    U_bulk: float,
    rho: float = 1.0,
) -> float:
    """Compute mean |Cf| over the downstream floor (PROVISIONAL_ADVISORY).

    cd_mean = mean(|τ_x|) / (0.5·ρ·U_bulk²)

    where the mean is taken over face-centre wall-shear samples on the
    downstream lower_wall (x > 0). This is intentionally a MINIMAL
    cross-check on the same wall-shear field that drives reattachment_
    length — V61-067 intake §3 downgrades cd_mean to PROVISIONAL_ADVISORY
    because it is a SAME_RUN_CROSS_CHECK on the wall-shear signal already
    consumed by the primary reattachment_length gate (V61-066 R1 F#3
    precedent).

    Args:
        tau_x_floor_data: list of (x, tau_x) tuples on the downstream
            floor (x > 0, y ≈ 0). Caller must pre-filter from the
            wallShearStress field. tau_x may be either sign — the mean
            |·| is what's reported.
        U_bulk: bulk velocity for normalization. Must be > 0.
        rho: fluid density. Defaults to 1.0.

    Returns:
        Mean |Cf| (dimensionless). Order of magnitude for BFS at Re=7600
        with kOmegaSST: ~10⁻³ to 10⁻². Note that the gold YAML's
        cd_mean=2.08 reference is a placeholder from the legacy multi-
        doc YAML and NOT an actual integration over the same surface
        this extractor measures — divergence is expected and absorbed
        by the PROVISIONAL_ADVISORY gate-status downgrade.

    Raises:
        BfsExtractorError: if tau_x_floor_data is empty, or if any
            tau_x value is non-finite, or if U_bulk/rho is non-positive.
    """
    if not tau_x_floor_data:
        raise BfsExtractorError("tau_x_floor_data is empty")
    U_bulk = _validate_positive("U_bulk", U_bulk)
    rho = _validate_positive("rho", rho)

    tau_xs: List[float] = []
    for entry in tau_x_floor_data:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise BfsExtractorError(
                f"tau_x_floor_data entries must be (x, tau_x) tuples, got {entry!r}"
            )
        _ = _validate_finite("x_floor", float(entry[0]))
        tau_x = _validate_finite("tau_x", float(entry[1]))
        tau_xs.append(abs(tau_x))

    mean_abs_tau = sum(tau_xs) / len(tau_xs)
    return mean_abs_tau / (0.5 * rho * U_bulk ** 2)
