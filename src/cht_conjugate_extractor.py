"""P3 W3.3b · CHT conjugate-channel Nusselt extractor (Execution Plane).

Parses OpenFOAM ``postProcessing/.../surfaceFieldValue.dat`` files from a solved
TWO-REGION conjugate channel (``foamMultiRun`` fluid[kOmegaSST] + solid,
``coupledTemperature`` interface, OF11) and computes the fluid-produced
heat-transfer coefficient and Nusselt number:

    h  = q_wall / (T_wall - T_bulk)            # fluid-PRODUCED coefficient
    Nu = h * D_h / k_fluid                      # compared vs Gnielinski

evaluated in the FULLY-DEVELOPED downstream window so it matches the
fully-developed Gnielinski correlation (entrance enhancement excluded).

ADR-001 plane assignment: **Execution Plane** (reads OpenFOAM artifacts; NO
Evaluation imports — the comparator wiring lives in ``src.cht_conjugate_gate``,
Control Plane, mirroring ``src.cht_fin_extractor`` / ``src.cht_fin_gate``).
Imports only stdlib + ``src.models`` is NOT needed here (pure dataclass).

HONESTY (the load-bearing property of the downstream gate)
----------------------------------------------------------
Nu is assembled from the solver's OWN integrated output —
``q_wall = areaAverage(wallHeatFlux)``, ``T_wall = areaAverage(T)``,
``T_bulk`` from the flux-weighted (cup-mixing) outlet temperature and the wall
heat integral — combined with case INPUTS only (D_h, k_fluid, cp). It is NEVER
derived from the Gnielinski closed form ``Nu=(f/8)(Re-1000)Pr/...``
(anti-tautology). The reference lives solely in the gold standard and is applied
ONLY by the comparator. Feed a doctored solver output and the gate FAILS.
Missing / NaN / non-physical input -> raise, never a fabricated default.

The window-averaged bulk temperature is reconstructed from the wall-heat
integral via a cumulative energy balance (no interpolated internal cut-plane):

    T_bulk_window = T_in + (Q_total - 0.5 * Q_window) / (mdot * cp)

which is the mean bulk over the window [x1, L] (Q_total heats the fluid from
T_in to the outlet; half the window's own heat is added by the window midpoint).
A separate cup-mixing outlet temperature is measured independently and used by
the gate's energy-balance hard check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

# postProcessing probe directory names emitted by the extraction FO set
# (system/extractConjugate; see reports/showcase_aero/_w33b_pipe_probe/channel).
_Q_WINDOW_AVG = "qWindowAvg"    # areaAverage(wallHeatFlux) over fully-developed window [W/m^2]
_Q_WINDOW_INT = "qWindowInt"    # areaIntegrate(wallHeatFlux) over the window          [W]
_T_WALL_WINDOW = "TwallWindow"  # areaAverage(T) over the window interface             [K]
_Q_IFACE_TOTAL = "QifaceTotal"  # areaIntegrate(wallHeatFlux) over the FULL interface  [W]
_T_BULK_OUT = "TbulkOut"        # weightedAverage(phi) of T at the outlet (cup-mixing) [K]
_T_IN = "Tin"                   # areaAverage(T) at the inlet                          [K]
_MDOT_IN = "mdotIn"             # sum(phi) at the inlet (mass flux)                    [kg/s]


class ConjugateExtractorError(Exception):
    """Raised when conjugate Nu cannot be honestly extracted (missing/NaN/non-physical)."""


@dataclass(frozen=True)
class ConjugateQoIs:
    """Solver-derived conjugate QoIs plus the raw channels they were built from.

    Raw channels are retained so callers / tests can audit that Nu was genuinely
    assembled from integrated solver output and verify the energy balance.
    """

    nusselt_number: float
    h_w_m2k: float                # fluid-produced heat transfer coefficient
    q_wall_window_w_m2: float     # areaAverage(wallHeatFlux), window  (magnitude)
    t_wall_window_k: float        # areaAverage(T), window
    t_bulk_window_k: float        # cumulative-energy bulk T over the window
    t_bulk_out_k: float           # measured cup-mixing outlet T
    t_in_k: float                 # measured inlet T
    mdot_kg_s: float              # measured inlet mass flux (magnitude)
    inlet_area_m2: float          # inlet patch area (from the probe header)
    reynolds_solved: float        # Re recovered from the SOLVED case: mdot*D_h/(A_in*mu)
    q_iface_total_w: float        # areaIntegrate(wallHeatFlux), full interface (magnitude)
    q_window_w: float             # areaIntegrate(wallHeatFlux), window (magnitude)
    energy_balance_residual_w: float  # |Q_total - mdot*cp*(T_out - T_in)|
    delta_t_window_k: float       # T_wall_window - T_bulk_window (driving dT for h)


# ---------------------------------------------------------------------------
# surfaceFieldValue.dat parsing  (mirrors src.cht_fin_extractor)
# ---------------------------------------------------------------------------


def _time_dir_key(name: str) -> float:
    try:
        return float(name)
    except ValueError:
        return float("-inf")


def _find_surface_field_dat(post_dir: Path, probe: str) -> Path:
    """Locate ``postProcessing/<probe>/<time>/surfaceFieldValue.dat`` (latest time)."""
    matches = sorted(
        (post_dir / probe).glob("*/surfaceFieldValue.dat"),
        key=lambda p: _time_dir_key(p.parent.name),
    )
    if not matches:
        raise FileNotFoundError(
            f"no surfaceFieldValue.dat under {post_dir / probe} "
            f"(expected {probe}/<time>/surfaceFieldValue.dat)"
        )
    return matches[-1]


def _read_area_header(dat_path: Path) -> float:
    """Return the ``# Area : <value>`` from a surfaceFieldValue.dat header.

    surfaceFieldValue always emits the selection area in the comment header
    (even with ``writeArea false``). Used to recover the SOLVED Reynolds number
    from the measured inlet mass flux, so the Re validity gate verifies the
    actual flow rate of the replayed case rather than trusting the gold YAML.
    Fail-closed if the header line is absent / non-finite / non-positive.
    """
    for line in dat_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("#"):
            continue
        # "# Area   :      1.25000000e-04"
        if "Area" in s and ":" in s:
            tail = s.split(":", 1)[1].strip()
            try:
                area = float(tail.split()[0])
            except (ValueError, IndexError) as exc:
                raise ConjugateExtractorError(
                    f"unparseable Area header in {dat_path}: {tail!r}"
                ) from exc
            if not math.isfinite(area) or area <= 0.0:
                raise ConjugateExtractorError(
                    f"non-physical inlet area in {dat_path}: {area}"
                )
            return area
    raise ConjugateExtractorError(f"no '# Area' header in {dat_path}")


def _read_last_scalar(dat_path: Path) -> float:
    """Return the value column of the LAST data row of a surfaceFieldValue.dat.

    Skips ``#``-comment / header lines; the data rows are ``<time>\\t<value>``.
    Fail-closed on empty / non-finite / malformed file (never a silent default).
    """
    last_value: Optional[float] = None
    for line in dat_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        try:
            last_value = float(parts[1])
        except ValueError as exc:
            raise ConjugateExtractorError(
                f"non-scalar / unparseable value column in {dat_path}: {parts[1]!r}"
            ) from exc
    if last_value is None:
        raise ConjugateExtractorError(f"no data rows in {dat_path}")
    if not math.isfinite(last_value):
        raise ConjugateExtractorError(f"non-finite value in {dat_path}: {last_value}")
    return last_value


# ---------------------------------------------------------------------------
# QoI extraction
# ---------------------------------------------------------------------------


def extract_conjugate_qois(
    case_dir: Path,
    *,
    D_h: float,
    k_fluid: float,
    cp: float,
    mu: float,
) -> ConjugateQoIs:
    """Extract the fully-developed conjugate Nusselt number from a solved case.

    Args:
        case_dir: case root containing ``postProcessing/{qWindowAvg,qWindowInt,
            TwallWindow,QifaceTotal,TbulkOut,Tin,mdotIn}/<time>/surfaceFieldValue.dat``.
        D_h: hydraulic diameter [m]            (gold input; = 2*gap for parallel plates)
        k_fluid: fluid thermal conductivity [W/m/K] (gold input)
        cp: fluid specific heat [J/kg/K]       (gold input)
        mu: dynamic viscosity [Pa.s]           (gold input; used to recover solved Re)

    q_wall / T_wall / T_bulk / mdot / inlet-area come from the solver; D_h,
    k_fluid, cp, mu are inputs. Nu is built from those — never from the
    Gnielinski formula. The SOLVED Reynolds number is recovered from the measured
    inlet mass flux and patch area (Re = mdot*D_h/(A_in*mu)) so the gate can
    verify the replayed case's actual flow rate, not the gold's claimed Re.
    Raises ``FileNotFoundError`` if probes are absent and
    ``ConjugateExtractorError`` on non-physical / unparseable values.
    """
    post = case_dir / "postProcessing"
    # wall heat flux integrals/averages are sign-conventioned by patch normal;
    # the physics (hot wall -> fluid) is unambiguous, so use magnitudes.
    q_wall_window = abs(_read_last_scalar(_find_surface_field_dat(post, _Q_WINDOW_AVG)))
    q_window = abs(_read_last_scalar(_find_surface_field_dat(post, _Q_WINDOW_INT)))
    t_wall_window = _read_last_scalar(_find_surface_field_dat(post, _T_WALL_WINDOW))
    q_total = abs(_read_last_scalar(_find_surface_field_dat(post, _Q_IFACE_TOTAL)))
    t_bulk_out = _read_last_scalar(_find_surface_field_dat(post, _T_BULK_OUT))
    t_in = _read_last_scalar(_find_surface_field_dat(post, _T_IN))
    mdot_dat = _find_surface_field_dat(post, _MDOT_IN)
    mdot = abs(_read_last_scalar(mdot_dat))
    inlet_area = _read_area_header(mdot_dat)  # inlet patch area for the Re recovery

    if D_h <= 0.0 or k_fluid <= 0.0 or cp <= 0.0 or mu <= 0.0:
        raise ConjugateExtractorError(
            f"non-physical inputs: D_h={D_h}, k_fluid={k_fluid}, cp={cp}, mu={mu}"
        )
    if mdot <= 0.0:
        raise ConjugateExtractorError(f"non-physical mass flux mdot={mdot}")

    # Re from the SOLVED case: mass flux per unit area is rho*U, so
    # Re_Dh = (mdot/A_in)*D_h/mu = mdot*D_h/(A_in*mu)  (rho cancels).
    reynolds_solved = mdot * D_h / (inlet_area * mu)

    # window-mean bulk temperature from a cumulative energy balance (no internal
    # cut-plane): the fluid heats from T_in to the outlet by Q_total; the window
    # [x1, L] sees the bulk rise to (Q_total - 0.5*Q_window) by its midpoint.
    t_bulk_window = t_in + (q_total - 0.5 * q_window) / (mdot * cp)

    delta_t = t_wall_window - t_bulk_window
    if delta_t <= 0.0:
        raise ConjugateExtractorError(
            f"non-physical driving dT: T_wall_window={t_wall_window} <= "
            f"T_bulk_window={t_bulk_window}; cannot form h"
        )

    h = q_wall_window / delta_t
    nusselt = h * D_h / k_fluid

    energy_residual = abs(q_total - mdot * cp * (t_bulk_out - t_in))

    return ConjugateQoIs(
        nusselt_number=nusselt,
        h_w_m2k=h,
        q_wall_window_w_m2=q_wall_window,
        t_wall_window_k=t_wall_window,
        t_bulk_window_k=t_bulk_window,
        t_bulk_out_k=t_bulk_out,
        t_in_k=t_in,
        mdot_kg_s=mdot,
        inlet_area_m2=inlet_area,
        reynolds_solved=reynolds_solved,
        q_iface_total_w=q_total,
        q_window_w=q_window,
        energy_balance_residual_w=energy_residual,
        delta_t_window_k=delta_t,
    )


def to_key_quantities(qois: ConjugateQoIs) -> Dict[str, float]:
    """Map QoIs to the comparator's ``key_quantities`` dict (gold ``quantity`` key).

    The key equals the gold ``quantity`` string ``nusselt_number`` verbatim (also
    a canonical name in ResultComparator.CANONICAL_ALIASES), so a mismatch makes
    the comparator report the quantity missing rather than silently pass.
    """
    return {"nusselt_number": qois.nusselt_number}
