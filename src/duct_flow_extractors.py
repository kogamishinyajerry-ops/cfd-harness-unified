"""Duct-flow Type II secondary observable extractors (DEC-V61-066 A.1).

Provides 4 functions that operate on the raw OpenFOAM emit data the
adapter has already gathered (cell centres + velocity vectors + wall
shear stress) and produce the headline + 3 secondary observables that
the V61-066 Type II contract gates require:

    extract_friction_factor(tau_w, U_bulk, rho)      → Darcy f
    extract_friction_velocity(tau_w, rho)            → u_τ
    extract_bulk_velocity_ratio(u_centroid, U_bulk)  → u_max / U_bulk
    extract_log_law_residual(u_line, u_tau, kappa, B) → mean |u+ - u+_log|

Reference: Jones 1976 / Jones & Launder 1973 (smooth square AR=1 duct
at Re_h=50000, Darcy f=0.0185); Pope 2000 Ch. 7 (universal log-law).

Caller responsibility: the adapter at
``foam_agent_adapter.py:_extract_duct_flow_*`` is the only intended
caller. It performs the wall-cell / centroid / line-sample aggregation
on cell-centred OpenFOAM data and hands the per-quantity scalar inputs
to these functions. This module does NOT touch OpenFOAM IO.

Failure mode: every public function raises ``DuctFlowExtractorError``
on degenerate input (non-positive scalars, NaN/Inf, empty profiles,
profile that never enters the log-law band, etc.). Caller decides
whether to fold into a ``duct_flow_*_error`` audit key or propagate.

Plane assignment: src/_plane_assignment.py marks this module as
``Plane.EXECUTION`` (peers: ``flat_plate_extractors``,
``airfoil_extractors``, ``dhc_extractors``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple


# ============================================================================
# Constants — Jones 1976 anchor + log-law universal
# ============================================================================

JONES_1976_F_AT_RE_50K: float = 0.0185
"""Jones 1976 smooth-square-duct Darcy friction factor at Re=50000.

Cross-validation: ~0.88·f_pipe(Re=5e4) where Colebrook smooth pipe
gives 0.0206; Jones gives 0.88·0.0206 = 0.0181, within the band that
contains 0.0185.
"""

LOG_LAW_KAPPA: float = 0.41
"""von Kármán constant (Pope 2000 Ch. 7)."""

LOG_LAW_B: float = 5.0
"""Log-law additive constant for smooth walls (Pope 2000 Ch. 7).

Some references use 5.2 or 5.5; 5.0 is the textbook midpoint and the
value Schlichting Ch. 18 reports for the Nikuradse fit.
"""

LOG_LAW_BAND_Y_PLUS_MIN: float = 30.0
"""Lower edge of the log-law fit band (above the buffer-layer transition)."""

LOG_LAW_BAND_Y_PLUS_MAX: float = 200.0
"""Upper edge of the log-law fit band (below the wake region for typical
high-Re duct flows; for Re_h=50000 the duct half-width is ~y+≈1500 so
this band sits well within the inner layer)."""


# ============================================================================
# Errors + result containers
# ============================================================================

class DuctFlowExtractorError(ValueError):
    """Raised on any degenerate input to a duct_flow extractor.

    Inherits ValueError so existing code that catches ValueError to
    fold into ``duct_flow_*_error`` audit keys keeps working without
    needing a new except clause.
    """


@dataclass(frozen=True)
class LogLawResidualResult:
    """Output of :func:`extract_log_law_residual`.

    Attributes:
        mean_residual: mean |u+_measured - u+_log| over the fit band
        n_points_in_band: how many sample points fell in [y+_min, y+_max]
        y_plus_min: lowest y+ observed in the band (for diagnostics)
        y_plus_max: highest y+ observed in the band
        kappa: κ used in the log-law (echo of input)
        B: B used in the log-law (echo of input)
    """

    mean_residual: float
    n_points_in_band: int
    y_plus_min: float
    y_plus_max: float
    kappa: float
    B: float


# ============================================================================
# Internal validation helpers
# ============================================================================

def _validate_positive(name: str, value: float) -> float:
    """Validate ``value`` is finite + > 0; raise on degenerate input."""
    if not isinstance(value, (int, float)):
        raise DuctFlowExtractorError(
            f"{name} must be a real number, got {type(value).__name__}: {value!r}"
        )
    v = float(value)
    if not math.isfinite(v):
        raise DuctFlowExtractorError(
            f"{name} must be finite, got {v}"
        )
    if v <= 0.0:
        raise DuctFlowExtractorError(
            f"{name} must be > 0, got {v}"
        )
    return v


def _validate_finite(name: str, value: float) -> float:
    """Validate ``value`` is finite (any sign); raise on NaN/Inf."""
    if not isinstance(value, (int, float)):
        raise DuctFlowExtractorError(
            f"{name} must be a real number, got {type(value).__name__}: {value!r}"
        )
    v = float(value)
    if not math.isfinite(v):
        raise DuctFlowExtractorError(
            f"{name} must be finite, got {v}"
        )
    return v


# ============================================================================
# Public extraction functions
# ============================================================================

def extract_friction_factor(
    tau_w: float,
    U_bulk: float,
    rho: float = 1.0,
) -> float:
    """Compute the Darcy friction factor f from wall shear + bulk velocity.

    f = 8·τ_w / (ρ·U_bulk²)

    Args:
        tau_w: wall shear stress magnitude projected onto the
            streamwise direction (Pa, or normalized units consistent
            with ρ and U_bulk). Must be > 0.
        U_bulk: face-area-weighted mean streamwise velocity through
            the duct cross-section (m/s, or normalized). Must be > 0.
        rho: fluid density (kg/m³). Defaults to 1.0 for normalized
            incompressible adapter runs (nu = 1/Re convention).

    Returns:
        Darcy friction factor (dimensionless). For Jones 1976 anchor
        at Re=50000, expected 0.0185 ± 10%.

    Raises:
        DuctFlowExtractorError: if any input is non-finite or non-positive.
    """
    tau_w = _validate_positive("tau_w", tau_w)
    U_bulk = _validate_positive("U_bulk", U_bulk)
    rho = _validate_positive("rho", rho)
    return 8.0 * tau_w / (rho * U_bulk ** 2)


def extract_friction_velocity(
    tau_w: float,
    rho: float = 1.0,
) -> float:
    """Compute friction velocity u_τ = √(τ_w / ρ).

    This is the SAME_RUN_CROSS_CHECK observable: extracted from the
    same wall-cell stencil as :func:`extract_friction_factor`, but
    reported in velocity units. It must agree with ``U_bulk · √(f/8)``
    to within solver round-off — divergence indicates an extractor-
    side bug, NOT a physics issue.

    Codex F1-class trap (V61-063 R1 precedent): if a downstream gate
    naïvely re-derives u_τ via √(f/8) using the just-extracted f, it
    becomes a tautological gate (always agrees with itself). The gate
    contract MUST keep these two extractions independent — derive
    u_τ DIRECTLY from τ_w (this function), not via f.

    Args:
        tau_w: wall shear stress magnitude (Pa, or normalized).
            Must be > 0.
        rho: fluid density. Defaults to 1.0 for normalized adapter runs.

    Returns:
        Friction velocity u_τ (m/s, or normalized). Jones 1976 anchor
        at Re=50000, U_bulk=1: expected 0.04811.

    Raises:
        DuctFlowExtractorError: if τ_w or ρ is non-finite or non-positive.
    """
    tau_w = _validate_positive("tau_w", tau_w)
    rho = _validate_positive("rho", rho)
    return math.sqrt(tau_w / rho)


def extract_bulk_velocity_ratio(
    u_centroid: float,
    U_bulk: float,
) -> float:
    """Compute u_max / U_bulk.

    This probes the cross-section momentum redistribution caused by
    Prandtl's secondary flow. For fully-developed AR=1 smooth duct
    turbulent flow at Re~5e4, classical correlations (Hartnett 1962 /
    Nikuradse 1932) give u_max/U_bulk ≈ 1.19-1.21. Independent of
    wall shear — a working primary friction_factor gate does NOT
    automatically imply this ratio is correct.

    Args:
        u_centroid: streamwise velocity at the duct cross-section
            centroid (y=0, z=0), interpolated if no cell sits on
            the geometric centre. Must be > 0 and finite.
        U_bulk: face-area-averaged bulk velocity, same units as
            u_centroid. Must be > 0.

    Returns:
        Ratio u_centroid / U_bulk (dimensionless). Jones / Hartnett
        anchor: ≈ 1.20 ± 0.01.

    Raises:
        DuctFlowExtractorError: if either input is non-finite or
            non-positive.
    """
    u_centroid = _validate_positive("u_centroid", u_centroid)
    U_bulk = _validate_positive("U_bulk", U_bulk)
    return u_centroid / U_bulk


def extract_log_law_residual(
    u_line: Sequence[Tuple[float, float]],
    u_tau: float,
    nu: float,
    *,
    kappa: float = LOG_LAW_KAPPA,
    B: float = LOG_LAW_B,
    y_plus_min: float = LOG_LAW_BAND_Y_PLUS_MIN,
    y_plus_max: float = LOG_LAW_BAND_Y_PLUS_MAX,
) -> LogLawResidualResult:
    """Fit log-law to wall-normal profile and return mean residual.

    Args:
        u_line: sequence of (y, u_x) pairs sampled along the duct
            symmetry plane (z=0, varying y from wall to centre).
            Wall sample (y=0, u_x=0) is allowed but skipped — log-law
            is undefined at y+=0.
        u_tau: friction velocity (from :func:`extract_friction_velocity`
            on the same case). Must be > 0.
        nu: kinematic viscosity (m²/s, or 1/Re for normalized adapter
            runs). Must be > 0.
        kappa: von Kármán constant. Defaults to LOG_LAW_KAPPA = 0.41.
        B: log-law additive constant. Defaults to LOG_LAW_B = 5.0.
        y_plus_min: lower edge of the fit band. Defaults to 30.0.
        y_plus_max: upper edge of the fit band. Defaults to 200.0.

    Returns:
        :class:`LogLawResidualResult` with mean_residual + diagnostics.
        A residual of 0.0 is log-law-perfect; ±0.5 is the V61-066
        gate tolerance (absolute mode, generous for asymptotic fits).

    Raises:
        DuctFlowExtractorError: if profile is empty, all wall, no
            samples in the [y+_min, y+_max] band, or any value is
            non-finite.
    """
    u_tau = _validate_positive("u_tau", u_tau)
    nu = _validate_positive("nu", nu)
    kappa = _validate_positive("kappa", kappa)
    B = _validate_finite("B", B)
    y_plus_min = _validate_positive("y_plus_min", y_plus_min)
    y_plus_max = _validate_positive("y_plus_max", y_plus_max)
    if y_plus_max <= y_plus_min:
        raise DuctFlowExtractorError(
            f"y_plus_max ({y_plus_max}) must be > y_plus_min ({y_plus_min})"
        )

    if not u_line:
        raise DuctFlowExtractorError("u_line is empty")

    in_band: list[Tuple[float, float]] = []  # (y+, u+)
    for raw in u_line:
        if not isinstance(raw, (tuple, list)) or len(raw) != 2:
            raise DuctFlowExtractorError(
                f"u_line entries must be (y, u_x) tuples, got {raw!r}"
            )
        y = _validate_finite("y", float(raw[0]))
        u = _validate_finite("u_x", float(raw[1]))
        if y <= 0.0:
            # Wall sample (y=0) or below-wall — skip; log-law undefined at y+=0.
            continue
        y_plus = y * u_tau / nu
        u_plus = u / u_tau
        if y_plus_min <= y_plus <= y_plus_max:
            in_band.append((y_plus, u_plus))

    n = len(in_band)
    if n < 2:
        raise DuctFlowExtractorError(
            f"need ≥2 samples in y+ band [{y_plus_min}, {y_plus_max}], "
            f"got {n} (from {len(u_line)} input points; check mesh "
            f"resolution near the wall and the u_tau magnitude)"
        )

    residuals = [
        abs(u_plus - ((1.0 / kappa) * math.log(y_plus) + B))
        for y_plus, u_plus in in_band
    ]
    mean_residual = sum(residuals) / n
    return LogLawResidualResult(
        mean_residual=mean_residual,
        n_points_in_band=n,
        y_plus_min=min(yp for yp, _ in in_band),
        y_plus_max=max(yp for yp, _ in in_band),
        kappa=kappa,
        B=B,
    )
