"""P4 V71.A · supersonic-wedge oblique-shock QoI extractor (Execution Plane).

Parses OpenFOAM postProcessing artifacts from a solved supersonic-wedge case
(``rhoCentralFoam``, density-based shock-capturing) and computes the five
oblique-shock benchmark QoIs:

    shock_angle_beta_deg = atan2(y_shock, x_shock_station)   # from the density jump
    mach_downstream      = areaAverage(Ma) post-shock        # M2
    pressure_ratio       = p2 / p1
    density_ratio        = rho2 / rho1
    temperature_ratio    = T2 / T1

The post/pre-shock states (p, rho, T, Ma) are area-averaged surfaceFieldValue
reductions; the shock angle ``beta`` is recovered from the LOCATION of the
density jump along a sampled line that crosses the shock, combined with the
known sample-line streamwise station — geometry, never the shock relations.

ADR-001 plane assignment: **Execution Plane** (reads OpenFOAM artifacts; NO
Evaluation imports — the comparator wiring lives in ``src.wedge_oblique_shock_gate``,
Control Plane, same posture as ``src.cht_fin_extractor`` / ``src.cht_conjugate_extractor``).
This module imports only stdlib.

HONESTY (the load-bearing property of the downstream gate)
----------------------------------------------------------
Every QoI is computed from the solver's OWN field output:

  * ``beta`` is the angle to the point where DENSITY jumps in the solved field
    (max |d rho / d s| along the sampled line) — it is measured from WHERE the
    shock sits, not computed from the theta-beta-M relation.
  * ``M2`` and the p/rho/T ratios are area-averages of the solved post-shock vs
    freestream regions.

The analytical closed form (theta-beta-M / normal-shock) is NEVER read or
evaluated here — it lives solely in the gold standard and is applied ONLY by the
comparator (``src.wedge_oblique_shock_gate``). Feed a wrong solver output and the
gate FAILS (see tests/p4/test_wedge_oblique_shock_gate.py, the doctored cases).
Missing / NaN / non-physical input -> raise, never a fabricated default
(fail-closed audit discipline).

Scope: validates a density-based shock-capturing solve against the EXACT inviscid
oblique-shock reference. Does NOT flip runnable-coverage 2->3 — that needs a LIVE
rhoCentralFoam solve on a provisioned ESI image (DEC-V61-224 fork wall, deferred).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# surfaceFieldValue probes: area-averaged state upstream (freestream) and behind
# the oblique shock (post-shock). One scalar field per probe dir (mirrors the fin
# extractor's single-value-per-probe convention).
_FREESTREAM_P = "freestream_p"      # areaAverage(p)   upstream   -> p1
_FREESTREAM_RHO = "freestream_rho"  # areaAverage(rho) upstream   -> rho1
_FREESTREAM_T = "freestream_T"      # areaAverage(T)   upstream   -> T1
_FREESTREAM_MA = "freestream_Ma"    # areaAverage(Ma)  upstream   -> M1 (measured)
_POSTSHOCK_P = "postShock_p"        # areaAverage(p)   post-shock -> p2
_POSTSHOCK_RHO = "postShock_rho"    # areaAverage(rho) post-shock -> rho2
_POSTSHOCK_T = "postShock_T"        # areaAverage(T)   post-shock -> T2
_POSTSHOCK_MA = "postShock_Ma"      # areaAverage(Ma)  post-shock -> M2

# sampled line (set) that crosses the oblique shock; columns: distance, rho.
_SHOCK_LINE = "shockLine"


class WedgeShockExtractorError(Exception):
    """Raised when wedge QoIs cannot be honestly extracted (missing/NaN/non-physical)."""


@dataclass(frozen=True)
class WedgeShockQoIs:
    """Solver-derived oblique-shock QoIs plus the raw channels they were built from.

    The raw fields are kept so callers / tests can audit that the dimensionless QoIs
    were genuinely assembled from solver output (not echoed from the gold) and check
    physical/thermodynamic consistency.
    """

    shock_angle_beta_deg: float
    mach_downstream: float
    pressure_ratio: float
    density_ratio: float
    temperature_ratio: float
    # raw channels
    p1: float
    rho1: float
    t1: float
    mach_freestream: float   # measured freestream Ma (used by the gate's supersonic-inflow check)
    p2: float
    rho2: float
    t2: float
    y_shock_m: float         # measured shock height at the sample station
    x_station_m: float       # the sample-line streamwise station (geometry input)


# ---------------------------------------------------------------------------
# surfaceFieldValue.dat parsing  (mirrors src/cht_fin_extractor.py)
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


def _read_last_scalar(dat_path: Path) -> float:
    """Return the value column of the LAST data row of a surfaceFieldValue.dat.

    Skips ``#``-comment lines. Raises ``WedgeShockExtractorError`` on an empty /
    non-finite / malformed file — fail-closed, never a silent default.
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
            raise WedgeShockExtractorError(
                f"non-scalar / unparseable value column in {dat_path}: {parts[1]!r}"
            ) from exc
    if last_value is None:
        raise WedgeShockExtractorError(f"no data rows in {dat_path}")
    if not math.isfinite(last_value):
        raise WedgeShockExtractorError(f"non-finite value in {dat_path}: {last_value}")
    return last_value


def _read_area_average(post_dir: Path, probe: str) -> float:
    return _read_last_scalar(_find_surface_field_dat(post_dir, probe))


# ---------------------------------------------------------------------------
# sampled-line (.xy) parsing + shock-location detection
# ---------------------------------------------------------------------------


def _find_xy(post_dir: Path, set_name: str) -> Path:
    """Locate ``postProcessing/<set>/<time>/*.xy`` (latest time)."""
    matches = sorted(
        (post_dir / set_name).glob("*/*.xy"),
        key=lambda p: _time_dir_key(p.parent.name),
    )
    if not matches:
        raise FileNotFoundError(
            f"no *.xy under {post_dir / set_name} (expected {set_name}/<time>/*.xy)"
        )
    return matches[-1]


def _read_distance_field(xy_path: Path) -> List[Tuple[float, float]]:
    """Parse a 2-column ``distance value`` sampled-line file. Fail-closed on garbage."""
    rows: List[Tuple[float, float]] = []
    for line in xy_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        try:
            d, v = float(parts[0]), float(parts[1])
        except ValueError as exc:
            raise WedgeShockExtractorError(
                f"unparseable row in {xy_path}: {s!r}"
            ) from exc
        if not (math.isfinite(d) and math.isfinite(v)):
            raise WedgeShockExtractorError(f"non-finite row in {xy_path}: {s!r}")
        rows.append((d, v))
    if len(rows) < 2:
        raise WedgeShockExtractorError(
            f"need >=2 sampled points to locate a shock in {xy_path} (got {len(rows)})"
        )
    return rows


def _locate_shock_distance(rows: List[Tuple[float, float]]) -> float:
    """Return the distance-along-line of the steepest density change (the shock).

    The shock is the row interval with the largest ``|d rho / d s|``; the crossing
    distance is the interval midpoint. Fail-closed if the field is essentially flat
    (no shock present) — a flat profile must NOT yield a fabricated angle.
    """
    rho_min = min(v for _, v in rows)
    rho_max = max(v for _, v in rows)
    total_var = rho_max - rho_min
    if total_var <= 1e-9 * max(abs(rho_max), 1.0):
        raise WedgeShockExtractorError(
            "no density jump along the sample line (flat field) — cannot locate a shock"
        )
    best_grad = -1.0
    best_mid = float("nan")
    best_jump = 0.0
    for (d0, v0), (d1, v1) in zip(rows, rows[1:]):
        ds = d1 - d0
        if ds <= 0.0:
            raise WedgeShockExtractorError(
                f"sample-line distance not strictly increasing ({d0} -> {d1})"
            )
        grad = abs(v1 - v0) / ds
        if grad > best_grad:
            best_grad = grad
            best_mid = 0.5 * (d0 + d1)
            best_jump = abs(v1 - v0)
    # the steepest step must carry a meaningful fraction of the total variation;
    # otherwise the "shock" is just discretisation noise on a smooth field.
    if best_jump < 0.25 * total_var:
        raise WedgeShockExtractorError(
            "no sharp density jump (steepest step carries <25% of the total density "
            "variation) — refusing to fabricate a shock angle"
        )
    return best_mid


# ---------------------------------------------------------------------------
# QoI extraction
# ---------------------------------------------------------------------------


def extract_wedge_qois(
    case_dir: Path,
    *,
    x_shock_station: float,
) -> WedgeShockQoIs:
    """Extract oblique-shock QoIs from a solved supersonic-wedge case directory.

    Args:
        case_dir: case root containing ``postProcessing/{freestream_*,postShock_*,
            shockLine}/<time>/...``.
        x_shock_station: streamwise distance (from the wedge apex) of the vertical
            density sample line [m] — geometry input from ``case_info.wedge_inputs``.

    The pre/post-shock states and the shock LOCATION come from the solver; the angle
    is geometry (``atan2(y_shock, x_station)``). Raises ``FileNotFoundError`` if
    probes are absent and ``WedgeShockExtractorError`` on non-physical values.
    """
    if not (math.isfinite(x_shock_station) and x_shock_station > 0.0):
        raise WedgeShockExtractorError(
            f"non-physical sample station x_shock_station={x_shock_station} (must be > 0)"
        )

    post_dir = case_dir / "postProcessing"

    p1 = _read_area_average(post_dir, _FREESTREAM_P)
    rho1 = _read_area_average(post_dir, _FREESTREAM_RHO)
    t1 = _read_area_average(post_dir, _FREESTREAM_T)
    m1 = _read_area_average(post_dir, _FREESTREAM_MA)
    p2 = _read_area_average(post_dir, _POSTSHOCK_P)
    rho2 = _read_area_average(post_dir, _POSTSHOCK_RHO)
    t2 = _read_area_average(post_dir, _POSTSHOCK_T)
    m2 = _read_area_average(post_dir, _POSTSHOCK_MA)

    for name, v in (
        ("p1", p1), ("rho1", rho1), ("T1", t1), ("M1", m1),
        ("p2", p2), ("rho2", rho2), ("T2", t2), ("M2", m2),
    ):
        if v <= 0.0:
            raise WedgeShockExtractorError(
                f"non-physical (<=0) area-averaged {name}={v} — cannot form a shock ratio"
            )

    rows = _read_distance_field(_find_xy(post_dir, _SHOCK_LINE))
    y_shock = _locate_shock_distance(rows)
    if y_shock <= 0.0:
        raise WedgeShockExtractorError(
            f"non-physical shock height y_shock={y_shock} at station x={x_shock_station}"
        )
    beta_deg = math.degrees(math.atan2(y_shock, x_shock_station))

    return WedgeShockQoIs(
        shock_angle_beta_deg=beta_deg,
        mach_downstream=m2,
        pressure_ratio=p2 / p1,
        density_ratio=rho2 / rho1,
        temperature_ratio=t2 / t1,
        p1=p1,
        rho1=rho1,
        t1=t1,
        mach_freestream=m1,
        p2=p2,
        rho2=rho2,
        t2=t2,
        y_shock_m=y_shock,
        x_station_m=x_shock_station,
    )


def to_key_quantities(qois: WedgeShockQoIs) -> Dict[str, float]:
    """Map QoIs to the comparator's ``key_quantities`` dict (gold ``quantity`` keys).

    Keys MUST equal the gold ``quantity`` strings verbatim — there is no
    CANONICAL_ALIASES entry for the wedge, so a mismatch would make the comparator
    report the quantity as missing rather than silently pass.
    """
    return {
        "shock_angle_beta_deg": qois.shock_angle_beta_deg,
        "mach_downstream": qois.mach_downstream,
        "pressure_ratio": qois.pressure_ratio,
        "density_ratio": qois.density_ratio,
        "temperature_ratio": qois.temperature_ratio,
    }
