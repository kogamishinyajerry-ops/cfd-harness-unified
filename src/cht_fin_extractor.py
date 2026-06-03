"""P3 W3.3a · CHT straight-fin QoI extractor (Execution Plane).

Parses OpenFOAM postProcessing ``surfaceFieldValue.dat`` files from a solved
straight-fin solid-conduction case (``foamRun -solver solid``, OF11) and computes
the two analytical-benchmark QoIs:

    fin_efficiency             = Q_base / (h * P * L * theta_b)
    fin_tip_temperature_ratio  = (T_tip - T_inf) / (T_base - T_inf)

with ``P = 2*(w + t)`` (perimeter), ``A_fin = P*L`` (lateral area), and
``theta_b = T_base - T_inf``.

ADR-001 plane assignment: **Execution Plane** (reads OpenFOAM artifacts; NO
Evaluation imports — the comparator wiring lives in ``src.cht_fin_gate``, Control
Plane, mirroring the airfoil_extractors "comparator wiring lives in Stage C"
precedent). This module imports only stdlib + ``src.models`` (Shared).

HONESTY (the load-bearing property of the downstream gate)
----------------------------------------------------------
The QoIs are computed from the solver's OWN integrated output —
``Q_base = areaIntegrate(wallHeatFlux)`` on the base patch and
``T_tip / T_base = areaAverage(T)`` — combined with the case's geometric/BC
INPUTS only (h, w, t, L, T_inf). They are NEVER derived from the closed form
``eta = tanh(mL)/mL`` / ``tip = 1/cosh(mL)``. The analytical reference value
lives solely in the gold standard and is applied ONLY by the comparator
(``src.cht_fin_gate``). Feed a wrong solver output and the gate FAILS (see
tests/p3/test_cht_fin_gate.py, the doctored-.dat case). Missing/NaN input →
raise, never a fabricated default (fail-closed audit discipline).

Scope: validates the SOLID conduction + imposed-h (Robin) BC against the exact
adiabatic-tip fin. Does NOT flip runnable-coverage 1->2 — that needs W3.3b
(full two-region conjugate vs Gnielinski, fluid-produced h).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

# The four postProcessing surfaceFieldValue probes the fin case emits.
_BASE_POWER = "basePower"   # areaIntegrate(wallHeatFlux) on the base patch  -> Q_base
_FIN_POWER = "finPower"     # areaIntegrate(wallHeatFlux) on the fin surface -> Q_fin
_BASE_T = "baseT"           # areaAverage(T) on the base patch               -> T_base
_TIP_T = "tipT"             # areaAverage(T) on the (adiabatic) tip patch    -> T_tip


class FinExtractorError(Exception):
    """Raised when fin QoIs cannot be honestly extracted (missing/NaN inputs)."""


@dataclass(frozen=True)
class FinConductionQoIs:
    """Solver-derived fin QoIs plus the raw channels they were built from.

    The raw fields (q_base_w, q_fin_w, t_base_k, t_tip_k) are kept so callers /
    tests can audit that the dimensionless QoIs were genuinely assembled from
    integrated solver output, and check energy closure.
    """

    fin_efficiency: float
    fin_tip_temperature_ratio: float
    q_base_w: float
    q_fin_w: float
    t_base_k: float
    t_tip_k: float
    q_max_w: float          # ideal h*A_fin*theta_b (uses inputs only)
    theta_b_k: float        # T_base - T_inf (driving temperature difference)
    energy_residual_w: float  # |Q_base + Q_fin| — adiabatic-tip energy closure


# ---------------------------------------------------------------------------
# surfaceFieldValue.dat parsing
# ---------------------------------------------------------------------------


def _find_surface_field_dat(post_dir: Path, probe: str) -> Path:
    """Locate ``postProcessing/<probe>/<time>/surfaceFieldValue.dat``.

    OpenFOAM writes the function-object output under its *start* time dir
    (here ``0/``) even though the converged value is the last data row. We
    glob the time subdir so the extractor is robust to a non-zero start time;
    if several exist we take the numerically-largest one.
    """
    matches = sorted(
        ((post_dir / probe).glob("*/surfaceFieldValue.dat")),
        key=lambda p: _time_dir_key(p.parent.name),
    )
    if not matches:
        raise FileNotFoundError(
            f"no surfaceFieldValue.dat under {post_dir / probe} "
            f"(expected {probe}/<time>/surfaceFieldValue.dat)"
        )
    return matches[-1]


def _time_dir_key(name: str) -> float:
    try:
        return float(name)
    except ValueError:
        return float("-inf")


def _read_last_scalar(dat_path: Path) -> float:
    """Return the value column of the LAST data row of a surfaceFieldValue.dat.

    Skips ``#``-comment / header lines. The data rows are
    ``<time>\\t<value>`` (a single scalar field reduction: areaIntegrate of a
    scalar, or areaAverage of a scalar). Raises ``FinExtractorError`` on an
    empty / non-finite / malformed file — fail-closed, never a silent default.
    """
    import math

    last_value: Optional[float] = None
    for line in dat_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        # column 1 is the field reduction (column 0 is the time value)
        try:
            last_value = float(parts[1])
        except ValueError as exc:
            raise FinExtractorError(
                f"non-scalar / unparseable value column in {dat_path}: {parts[1]!r}"
            ) from exc
    if last_value is None:
        raise FinExtractorError(f"no data rows in {dat_path}")
    if not math.isfinite(last_value):
        raise FinExtractorError(f"non-finite value in {dat_path}: {last_value}")
    return last_value


# ---------------------------------------------------------------------------
# QoI extraction
# ---------------------------------------------------------------------------


def extract_fin_qois(
    case_dir: Path,
    *,
    h_conv: float,
    w: float,
    t: float,
    L: float,
    T_inf: float,
) -> FinConductionQoIs:
    """Extract fin QoIs from a solved case directory.

    Args:
        case_dir: case root containing ``postProcessing/{basePower,finPower,
            baseT,tipT}/<time>/surfaceFieldValue.dat``.
        h_conv: imposed surface convection coefficient [W/m^2/K] (BC input).
        w, t, L: fin width, thickness, length [m] (geometry inputs).
        T_inf: convection sink temperature [K] (Robin BC input).

    Q_base / T_tip / T_base come from the solver; everything else is an input.
    Raises ``FileNotFoundError`` if probes are absent and ``FinExtractorError``
    on non-physical / unparseable values.
    """
    post_dir = case_dir / "postProcessing"
    q_base = _read_last_scalar(_find_surface_field_dat(post_dir, _BASE_POWER))
    q_fin = _read_last_scalar(_find_surface_field_dat(post_dir, _FIN_POWER))
    t_base = _read_last_scalar(_find_surface_field_dat(post_dir, _BASE_T))
    t_tip = _read_last_scalar(_find_surface_field_dat(post_dir, _TIP_T))

    theta_b = t_base - T_inf
    if theta_b <= 0.0:
        raise FinExtractorError(
            f"non-physical driving temperature: T_base={t_base} <= T_inf={T_inf}; "
            "cannot normalise fin QoIs"
        )

    perimeter = 2.0 * (w + t)
    a_fin = perimeter * L
    q_max = h_conv * a_fin * theta_b
    if q_max <= 0.0:
        raise FinExtractorError(
            f"non-physical ideal heat rate q_max={q_max} (h={h_conv}, A_fin={a_fin}, "
            f"theta_b={theta_b})"
        )

    fin_efficiency = q_base / q_max
    tip_ratio = (t_tip - T_inf) / theta_b

    return FinConductionQoIs(
        fin_efficiency=fin_efficiency,
        fin_tip_temperature_ratio=tip_ratio,
        q_base_w=q_base,
        q_fin_w=q_fin,
        t_base_k=t_base,
        t_tip_k=t_tip,
        q_max_w=q_max,
        theta_b_k=theta_b,
        energy_residual_w=abs(q_base + q_fin),
    )


def to_key_quantities(qois: FinConductionQoIs) -> Dict[str, float]:
    """Map QoIs to the comparator's ``key_quantities`` dict (gold ``quantity`` keys).

    Keys MUST equal the gold ``quantity`` strings verbatim — there is no
    CANONICAL_ALIASES entry for the fin, so a mismatch would make the comparator
    report the quantity as missing rather than silently pass.
    """
    return {
        "fin_efficiency": qois.fin_efficiency,
        "fin_tip_temperature_ratio": qois.fin_tip_temperature_ratio,
    }
