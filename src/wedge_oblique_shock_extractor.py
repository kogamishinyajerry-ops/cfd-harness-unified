"""P4 V71.A · supersonic-wedge oblique-shock QoI extractor (Execution Plane).

Parses OpenFOAM postProcessing artifacts from a solved supersonic-wedge case
(``rhoCentralFoam``, density-based shock-capturing) and computes the five
oblique-shock benchmark QoIs:

    shock_angle_beta_deg = atan2(y_shock_absolute, x_shock_station)  # from the density jump
    mach_downstream      = areaAverage(Ma) post-shock               # M2
    pressure_ratio       = p2 / p1
    density_ratio        = rho2 / rho1
    temperature_ratio    = T2 / T1

The pre/post-shock states (p, rho, T, Ma) are read from two area-averaged
``surfaceFieldValue`` probe regions (one multi-field ``.dat`` each, the natural
OpenFOAM function-object output — column order discovered from the header). The
shock angle ``beta`` is recovered from the LOCATION of the density jump along a
sampled line that crosses the shock, combined with the known sample-line geometry.

Probe / geometry names are taken from the gold's ``case_info.wedge_inputs`` so the
extractor honors the PUBLISHED contract rather than an unpublished private layout
(Codex DEC-V61-232 R0 P2).

ADR-001 plane assignment: **Execution Plane** (reads OpenFOAM artifacts; NO
Evaluation imports — the comparator wiring lives in ``src.wedge_oblique_shock_gate``,
Control Plane, same posture as ``src.cht_fin_extractor`` / ``src.cht_conjugate_extractor``).
This module imports only stdlib.

HONESTY (the load-bearing property of the downstream gate)
----------------------------------------------------------
Every QoI is computed from the solver's OWN field output:

  * ``beta`` is the angle to the point where DENSITY jumps in the solved field
    (max |d rho / d s| along the sampled line) — it is measured from WHERE the
    shock sits, then converted to an angle using only the KNOWN sample-line
    geometry (its absolute origin height + the streamwise station). It is NEVER
    computed from the theta-beta-M relation.
  * ``M2`` and the p/rho/T ratios are area-averages of the solved post-shock vs
    freestream regions.

The analytical closed form (theta-beta-M / normal-shock) is NEVER read or
evaluated here — it lives solely in the gold standard and is applied ONLY by the
comparator (``src.wedge_oblique_shock_gate``). Feed a wrong solver output and the
gate FAILS (see tests/p4/test_wedge_oblique_shock_gate.py, the doctored cases).
Missing / NaN / non-physical input -> raise, never a fabricated default
(fail-closed audit discipline).

GEOMETRY (Codex DEC-V61-232 R0 P1)
----------------------------------
The shock emanates from the wedge apex (taken as the origin) at angle ``beta``
above the freestream direction, so at streamwise station ``x`` its ABSOLUTE height
is ``x*tan(beta)``. A sampled line reports distance from ITS OWN origin, which need
not be the apex level: for a solid wedge the line is typically anchored on the
wedge WALL, whose height at the station is ``x*tan(theta)``. The extractor therefore
adds ``shock_line_origin_y`` (the absolute y of the line's distance-0 point, from
``wedge_inputs``) before taking the angle:

    y_shock_absolute = shock_line_origin_y + measured_distance
    beta = atan2(y_shock_absolute, x_shock_station)

For an apex-level line ``shock_line_origin_y = 0``; for a wall-anchored line the
live slice sets it to ``x_shock_station * tan(theta)``. Without this term a correct
solver shock would be mis-measured (e.g. theta=15deg, x=0.5: 45deg read as ~36deg).

Scope: validates a density-based shock-capturing solve against the EXACT inviscid
oblique-shock reference. Does NOT flip runnable-coverage 2->3 — that needs a LIVE
rhoCentralFoam solve on a provisioned ESI image (DEC-V61-224 fork wall, deferred).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# default probe / set names (overridable from case_info.wedge_inputs).
_DEFAULT_FREESTREAM_PROBE = "freestream"  # surfaceFieldValue region, area-averaged p,rho,T,Ma upstream
_DEFAULT_POSTSHOCK_PROBE = "postShock"    # surfaceFieldValue region, area-averaged p,rho,T,Ma post-shock
_DEFAULT_SHOCK_LINE = "shockLine"         # sampled rho(distance) line crossing the shock

# the four fields each region probe must area-average.
_REQUIRED_FIELDS = ("p", "rho", "T", "Ma")

# header column label like "areaAverage(p)" or "areaAverage(Ma)"
_AREA_AVG_LABEL = re.compile(r"areaAverage\(([^)]+)\)")


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
    y_shock_m: float         # absolute shock height at the sample station (origin + measured distance)
    x_station_m: float       # the sample-line streamwise station (geometry input)


# ---------------------------------------------------------------------------
# surfaceFieldValue.dat parsing  (multi-field, column order from the header)
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


def _read_area_average_fields(post_dir: Path, probe: str) -> Dict[str, float]:
    """Parse a multi-field surfaceFieldValue.dat into ``{field: last_value}``.

    Column order is discovered from the ``# ... areaAverage(<field>) ...`` header
    line (NOT assumed), so the probe may list its fields in any order. The data row
    used is the LAST one (converged tail). Fail-closed on a missing header / column
    count mismatch / non-finite value — never a silent default.
    """
    dat_path = _find_surface_field_dat(post_dir, probe)
    field_cols: Optional[List[str]] = None  # data-column index -> field name (col 0 = Time)
    last_row: Optional[List[str]] = None
    for line in dat_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            # a header line carrying areaAverage(...) labels defines the columns;
            # the LAST such line wins (OpenFOAM prints the column header last).
            labels = _AREA_AVG_LABEL.findall(s)
            if labels:
                field_cols = labels
            continue
        parts = s.split()
        if len(parts) >= 2:
            last_row = parts
    if field_cols is None:
        raise WedgeShockExtractorError(
            f"no 'areaAverage(<field>)' column header in {dat_path}; cannot map fields"
        )
    if last_row is None:
        raise WedgeShockExtractorError(f"no data rows in {dat_path}")
    # data columns are [time, <field_cols...>]; require one value per labelled field
    if len(last_row) != len(field_cols) + 1:
        raise WedgeShockExtractorError(
            f"column count mismatch in {dat_path}: header has {len(field_cols)} field(s) "
            f"{field_cols} but data row has {len(last_row) - 1} value(s)"
        )
    out: Dict[str, float] = {}
    for i, field in enumerate(field_cols):
        try:
            v = float(last_row[i + 1])
        except ValueError as exc:
            raise WedgeShockExtractorError(
                f"non-numeric value for {field!r} in {dat_path}: {last_row[i + 1]!r}"
            ) from exc
        if not math.isfinite(v):
            raise WedgeShockExtractorError(f"non-finite {field!r} in {dat_path}: {v}")
        out[field] = v
    return out


def _require_fields(values: Dict[str, float], probe: str) -> Tuple[float, float, float, float]:
    """Pull (p, rho, T, Ma) from a probe's parsed fields, fail-closed on any missing."""
    missing = [f for f in _REQUIRED_FIELDS if f not in values]
    if missing:
        raise WedgeShockExtractorError(
            f"probe {probe!r} is missing required area-averaged field(s) {missing} "
            f"(present: {sorted(values)})"
        )
    return values["p"], values["rho"], values["T"], values["Ma"]


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
    shock_line_origin_y: float = 0.0,
    freestream_probe: str = _DEFAULT_FREESTREAM_PROBE,
    postshock_probe: str = _DEFAULT_POSTSHOCK_PROBE,
    shock_line: str = _DEFAULT_SHOCK_LINE,
) -> WedgeShockQoIs:
    """Extract oblique-shock QoIs from a solved supersonic-wedge case directory.

    Args:
        case_dir: case root containing ``postProcessing/{<freestream>,<postShock>,
            <shockLine>}/<time>/...``.
        x_shock_station: streamwise distance (from the wedge apex) of the vertical
            density sample line [m] — geometry input from ``case_info.wedge_inputs``.
        shock_line_origin_y: absolute y [m] of the sample line's distance-0 point
            (0 for an apex-level line; ``x_shock_station*tan(theta)`` for a
            wall-anchored line). Added to the measured distance before taking the
            angle so beta is the ABSOLUTE shock angle, not the wall-relative one.
        freestream_probe / postshock_probe / shock_line: postProcessing region/set
            names (from ``wedge_inputs`` — honoring the published contract).

    The pre/post-shock states and the shock LOCATION come from the solver; the angle
    is geometry (``atan2(origin_y + measured_distance, x_station)``). Raises
    ``FileNotFoundError`` if probes are absent and ``WedgeShockExtractorError`` on
    non-physical values.
    """
    if not (math.isfinite(x_shock_station) and x_shock_station > 0.0):
        raise WedgeShockExtractorError(
            f"non-physical sample station x_shock_station={x_shock_station} (must be > 0)"
        )
    if not math.isfinite(shock_line_origin_y) or shock_line_origin_y < 0.0:
        raise WedgeShockExtractorError(
            f"non-physical shock_line_origin_y={shock_line_origin_y} (must be finite, >= 0)"
        )

    post_dir = case_dir / "postProcessing"

    p1, rho1, t1, m1 = _require_fields(
        _read_area_average_fields(post_dir, freestream_probe), freestream_probe
    )
    p2, rho2, t2, m2 = _require_fields(
        _read_area_average_fields(post_dir, postshock_probe), postshock_probe
    )

    for name, v in (
        ("p1", p1), ("rho1", rho1), ("T1", t1), ("M1", m1),
        ("p2", p2), ("rho2", rho2), ("T2", t2), ("M2", m2),
    ):
        if v <= 0.0:
            raise WedgeShockExtractorError(
                f"non-physical (<=0) area-averaged {name}={v} — cannot form a shock ratio"
            )

    rows = _read_distance_field(_find_xy(post_dir, shock_line))
    measured_distance = _locate_shock_distance(rows)
    y_shock_absolute = shock_line_origin_y + measured_distance
    if y_shock_absolute <= 0.0:
        raise WedgeShockExtractorError(
            f"non-physical absolute shock height y={y_shock_absolute} at station "
            f"x={x_shock_station} (origin_y={shock_line_origin_y}, dist={measured_distance})"
        )
    beta_deg = math.degrees(math.atan2(y_shock_absolute, x_shock_station))

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
        y_shock_m=y_shock_absolute,
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
